# SPDX-License-Identifier: Apache-2.0
"""Fail-closed, diagnostic-only source instrumentation. Never shipped or timed as plain."""
def instrument(path):
    s=path.read_text()
    def replace(old,new):
        nonlocal s
        assert s.count(old)==1, 'Profile anchor drift: '+old[:90]
        s=s.replace(old,new)
    replace('using System.Collections.Concurrent;', 'using System.Collections.Concurrent;\nusing System.Diagnostics;\nusing System.Diagnostics.Tracing;')
    replace('try { Reply(new { id, result = await engine.Invoke(method, args, cts.Token) }); }', '''try {
                            BenchProfile.Begin();
                            var started = Stopwatch.GetTimestamp();
                            var result = await engine.Invoke(method, args, cts.Token);
                            var invokeMs = Stopwatch.GetElapsedTime(started).TotalMilliseconds;
                            var reply = Stopwatch.GetTimestamp();
                            Reply(new { id, result });
                            BenchProfile.End(id, method, invokeMs, Stopwatch.GetElapsedTime(reply).TotalMilliseconds);
                        }''')
    replace('        // Admission-only sharing within this trusted refresh.', '        var profileStart = Stopwatch.GetTimestamp();\n        var bytesBefore = bytesRead; var reusedBefore = reusedSnapshots;\n        // Admission-only sharing within this trusted refresh.')
    sort = next(line for line in s.splitlines() if 'files.Sort(' in line)
    replace(sort,'        var bookkeepingStart = Stopwatch.GetTimestamp();\n'+sort)
    loop = '        foreach (var info in files)\n        {' if 'foreach (var info in files)' in s else '        foreach (var file in files)\n        {'
    replace(loop,'        BenchProfile.Add("bookkeeping", bookkeepingStart);\n'+loop)
    admission = '            var file = info.FullName;' if 'foreach (var info in files)' in s else '            var info = new FileInfo(file);'
    replace(admission,'            var admissionStart = Stopwatch.GetTimestamp();\n'+admission)
    replace('            var generation = Interlocked.Read(ref invalidationGeneration);','            BenchProfile.Add("admission", admissionStart);\n            var generation = Interlocked.Read(ref invalidationGeneration);')
    replace('            // Cached ancestor checks authorize snapshot admission, never a read.', '''            BenchProfile.Reads++;
            if (snapshots.TryGetValue(file, out var prior)) {
                if (now - prior.ValidatedAt >= 5000) BenchProfile.Expired++;
                if (prior.Dirty != dirty) BenchProfile.Dirty++;
                if (prior.Generation != generation) BenchProfile.Invalidated++;
            }
            var readStart = Stopwatch.GetTimestamp();
            // Cached ancestor checks authorize snapshot admission, never a read.''')
    if 'previousHash == nextFingerprints[file]' in s:
        replace('                previousHash == nextFingerprints[file] && documents.ContainsKey(file))\n                continue;', '                previousHash == nextFingerprints[file] && documents.ContainsKey(file))\n            { BenchProfile.Add("readHashDecode", readStart); continue; }')
    replace('            var source = SourceText.From(memory, encoding: Encoding.UTF8);','            var source = SourceText.From(memory, encoding: Encoding.UTF8);\n            BenchProfile.Add("readHashDecode", readStart);')
    apply = '        if (!ReferenceEquals(solution, workspace.CurrentSolution) && !workspace.TryApplyChanges(solution))' if 'if (!ReferenceEquals(solution, workspace.CurrentSolution)' in s else '        if (!workspace.TryApplyChanges(solution))'
    replace(apply, '        var applyStart = Stopwatch.GetTimestamp();\n'+apply)
    commit = '        foreach (var entry in nextFingerprints) fingerprints[entry.Key] = entry.Value;' if 'fingerprints[entry.Key] = entry.Value;' in s else '        foreach (var entry in nextFingerprints) fingerprints.Add(entry.Key, entry.Value);'
    replace(commit,commit+'''
        BenchProfile.Add("applyRebuild", applyStart);
        BenchProfile.Add("refresh", profileStart);
        BenchProfile.Bytes = bytesRead - bytesBefore; BenchProfile.Reused = reusedSnapshots - reusedBefore;''')
    # Time the whole normalization/check operation and the leaf attribute call separately.
    replace('        var full = Path.GetFullPath(Path.IsPathRooted(path) ? path : Path.Combine(root!, path));','        using var scope = BenchProfile.Scope("path");\n        var full = Path.GetFullPath(Path.IsPathRooted(path) ? path : Path.Combine(root!, path));')
    replace('leafInfo.Attributes : File.GetAttributes(current)', 'BenchProfile.Leaf(leafInfo) : BenchProfile.Attributes(current)')
    if 'private void CheckSnapshotPath' in s:
        parent = '        var parent = knownParent ?? Path.GetDirectoryName(file)!;' if 'var parent = knownParent' in s else '        var parent = Path.GetDirectoryName(file)!;'
        replace(parent, '        using var scope = BenchProfile.Scope("snapshotPath");\n'+parent)
        replace('\n        if ((info.Attributes & FileAttributes.ReparsePoint)', '\n        if ((BenchProfile.Leaf(info) & FileAttributes.ReparsePoint)')
    s=s.replace('info.Refresh();', 'BenchProfile.RefreshMetadata(info);')
    s+='''
// Diagnostic build only: process-wide allocations/GC and runtime event observations.
internal sealed class BenchProfile : EventListener
{
    private static readonly BenchProfile Listener = new();
    private static readonly ConcurrentDictionary<string, long> Events = new();
    private static readonly Dictionary<string, double> Stages = new();
    private static long Alloc, Pause, G0, G1, G2;
    private static Dictionary<string,long> EventStart = new();
    public static long Reads, Expired, Dirty, Invalidated, Bytes, Reused, Attrs;
    protected override void OnEventSourceCreated(EventSource source)
    {
        if (source.Name == "Microsoft-Windows-DotNETRuntime")
            EnableEvents(source, EventLevel.Verbose, (EventKeywords)0x11); // GC + JIT
    }
    protected override void OnEventWritten(EventWrittenEventArgs e)
    {
        if (Events is not null && e.EventName is not null) Events.AddOrUpdate(e.EventName, 1, (_, n) => n+1);
    }
    public static void Begin()
    {
        _ = Listener; Stages.Clear(); Reads=Expired=Dirty=Invalidated=Bytes=Reused=Attrs=0;
        Alloc=GC.GetTotalAllocatedBytes(false); Pause=GC.GetTotalPauseDuration().Ticks;
        G0=GC.CollectionCount(0); G1=GC.CollectionCount(1); G2=GC.CollectionCount(2);
        EventStart = new(Events);
    }
    public static void Add(string stage, long start) => Stages[stage] = Stages.GetValueOrDefault(stage) + Stopwatch.GetElapsedTime(start).TotalMilliseconds;
    public static IDisposable Scope(string stage) => new Timed(stage);
    private sealed class Timed(string stage) : IDisposable { private readonly long start=Stopwatch.GetTimestamp(); public void Dispose()=>Add(stage,start); }
    public static void RefreshMetadata(FileInfo info) { var start=Stopwatch.GetTimestamp(); try{info.Refresh();} finally{Add("metadataRefresh",start);} }
    public static FileAttributes Leaf(FileInfo info) { var start=Stopwatch.GetTimestamp(); Attrs++; try{return info.Attributes;} finally{Add("attributes",start);} }
    public static FileAttributes Attributes(string path) { var start=Stopwatch.GetTimestamp(); Attrs++; try{return File.GetAttributes(path);} finally{Add("attributes",start);} }
    public static void End(JsonElement id, string method, double invokeMs, double replyMs)
    {
        var events = Events.ToDictionary(e=>e.Key,e=>e.Value-EventStart.GetValueOrDefault(e.Key));
        Console.Error.WriteLine("BENCH_PROFILE " + JsonSerializer.Serialize(new { id, method, invokeMs, replyMs, stages=Stages,
            allocatedBytes=GC.GetTotalAllocatedBytes(false)-Alloc, gcPauseMs=(GC.GetTotalPauseDuration().Ticks-Pause)/10000.0,
            gen0=GC.CollectionCount(0)-G0, gen1=GC.CollectionCount(1)-G1, gen2=GC.CollectionCount(2)-G2,
            Reads, Expired, Dirty, Invalidated, Bytes, Reused, Attrs, runtimeEvents=events }));
    }
}
'''
    path.write_text(s)
