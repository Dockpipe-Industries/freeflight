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
    replace('        await Refresh(token, requestedFile, method == "rename");', '        await Refresh(token, requestedFile, method == "rename");\n        using var semanticScope = BenchProfile.Scope("semantic");')
    refresh_start = '        var recoveryStarted = Environment.TickCount64;' if 'var recoveryStarted =' in s else '        // Admission-only sharing within this trusted refresh.'
    replace(refresh_start, '        var profileStart = Stopwatch.GetTimestamp();\n        var bytesBefore = bytesRead; var reusedBefore = reusedSnapshots;\n' + refresh_start)
    sort = next(line for line in s.splitlines() if 'files.Sort(' in line)
    replace(sort,'        var bookkeepingStart = Stopwatch.GetTimestamp();\n'+sort)
    loop = '        foreach (var info in files)\n        {' if 'foreach (var info in files)' in s else '        foreach (var file in files)\n        {'
    if 'var parallelAdmission =' in s:
        replace('        var parallelAdmission =', '        BenchProfile.Add("bookkeeping", bookkeepingStart);\n        var parallelAdmission =')
        replace('        var admissionFailure = parallelAdmission ? ValidateSnapshotInputs(files, token) : null;', '        var parallelStart=Stopwatch.GetTimestamp();\n        var admissionFailure = parallelAdmission ? ValidateSnapshotInputs(files, token) : null;\n        BenchProfile.Add("parallelAdmissionWall",parallelStart);')
    else:
        replace(loop,'        BenchProfile.Add("bookkeeping", bookkeepingStart);\n'+loop)
    admission = '            var file = info.FullName;' if 'foreach (var info in files)' in s else '            var info = new FileInfo(file);'
    assert admission in s
    s=s.replace(admission,'            var admissionStart = Stopwatch.GetTimestamp();\n'+admission,1)
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
    native_attributes = 'DarwinPathAttributes.ReadReparseFlag(current)' in s
    if native_attributes:
        replace('leafInfo.Attributes : DarwinPathAttributes.ReadReparseFlag(current)', 'BenchProfile.Leaf(leafInfo) : BenchProfile.NativeAttributes(current)')
    else:
        replace('leafInfo.Attributes : File.GetAttributes(current)', 'BenchProfile.Leaf(leafInfo) : BenchProfile.Attributes(current)')
    if ' CheckSnapshotPath(' in s:
        parent = '        var parent = knownParent ?? Path.GetDirectoryName(file)!;' if 'var parent = knownParent' in s else '        var parent = Path.GetDirectoryName(file)!;'
        replace(parent, '        using var scope = BenchProfile.Scope("snapshotPath");\n'+parent)
        replace('\n        if ((info.Attributes & FileAttributes.ReparsePoint)', '\n        if ((BenchProfile.Leaf(info) & FileAttributes.ReparsePoint)')
    open_call = '            using var stream = OpenCompilerInput(file, recover);' if 'OpenCompilerInput(file, recover)' in s else '            using var stream = OpenCompilerInput(file);'
    replace(open_call, '            var openStart = Stopwatch.GetTimestamp();\n'+open_call+'\n            BenchProfile.Add("open", openStart);')
    buffered_hash = 'SHA256.HashData(\n                memory.GetBuffer().AsSpan(0, checked((int)memory.Length)))'
    if buffered_hash in s:
        replace(buffered_hash, 'BenchProfile.HashBuffer(memory)')
    else:
        replace('IncrementalHash.CreateHash(HashAlgorithmName.SHA256)', 'BenchProfile.CreateHash()')
    if 'await ReadCompilerBytes(' in s:
        replace('await ReadCompilerBytes(stream, buffer, token, OperatingSystem.IsMacOS() && !externalCompilerInputs.Contains(file))', 'await BenchProfile.ReadSelected(stream, buffer, token, OperatingSystem.IsMacOS() && !externalCompilerInputs.Contains(file))')
    else:
        replace('await stream.ReadAsync(buffer.AsMemory(), token)', 'await BenchProfile.Read(stream, buffer, token)')
    if 'batch.TryGet(file, parent, token, out var metadata)' in s:
        replace('batch.TryGet(file, parent, token, out var metadata)', 'BenchProfile.Batch(batch, file, parent, token, out var metadata)')
    if 'hash.AppendData(buffer, 0, count);' in s:
        replace('hash.AppendData(buffer, 0, count);', 'BenchProfile.Append(hash, buffer, count);')
    replace('await memory.WriteAsync(buffer.AsMemory(0, count), token);', 'await BenchProfile.Write(memory, buffer, count, token);')
    if 'hash.GetHashAndReset()' in s:
        replace('Convert.ToHexString(hash.GetHashAndReset()).ToLowerInvariant()', 'BenchProfile.FinishHash(hash)')
    if 'trustedValidationParents.TryGetValue(path' in s:
        replace('        foreach (var parent in parents)', '        using var lexicalScope = BenchProfile.Scope("path");\n        foreach (var parent in parents)')
        replace('File.GetAttributes(parent) & FileAttributes.ReparsePoint', 'BenchProfile.Attributes(parent) & FileAttributes.ReparsePoint')
        replace('File.GetAttributes(path) & FileAttributes.ReparsePoint', 'BenchProfile.Attributes(path) & FileAttributes.ReparsePoint')
    s=s.replace('info.Refresh();', 'BenchProfile.RefreshMetadata(info);')
    s+='''
// Diagnostic build only: process-wide allocations/GC and runtime event observations.
internal sealed class BenchProfile : EventListener
{
    private static readonly BenchProfile Listener = new();
    private static readonly ConcurrentDictionary<string, long> Events = new();
    private static readonly ThreadLocal<Dictionary<string, double>> Stages = new(() => new(), trackAllValues: true);
    private static readonly Process ObservedProcess = Process.GetCurrentProcess();
    private static long Alloc, Pause, G0, G1, G2, Cpu, Completed;
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
        _ = Listener; foreach (var stages in Stages.Values) stages.Clear(); Reads=Expired=Dirty=Invalidated=Bytes=Reused=Attrs=0;
        Alloc=GC.GetTotalAllocatedBytes(true); Pause=GC.GetTotalPauseDuration().Ticks;
        G0=GC.CollectionCount(0); G1=GC.CollectionCount(1); G2=GC.CollectionCount(2);
        EventStart = new(Events);
        ObservedProcess.Refresh(); Cpu=ObservedProcess.TotalProcessorTime.Ticks; Completed=ThreadPool.CompletedWorkItemCount;
    }
    public static void Add(string stage, long start) { var stages=Stages.Value!; stages[stage] = stages.GetValueOrDefault(stage) + Stopwatch.GetElapsedTime(start).TotalMilliseconds; }
    public static IDisposable Scope(string stage) => new Timed(stage);
    private sealed class Timed(string stage) : IDisposable { private readonly long start=Stopwatch.GetTimestamp(); public void Dispose()=>Add(stage,start); }
    public static bool Batch(DarwinMetadataBatch batch, string file, string parent, CancellationToken token, out DarwinMetadataBatch.Metadata metadata)
    { var start=Stopwatch.GetTimestamp(); try{return batch.TryGet(file,parent,token,out metadata);} finally{Add("bulkMetadata",start);} }
    public static byte[] HashBuffer(MemoryStream memory) { var start=Stopwatch.GetTimestamp(); try{return SHA256.HashData(memory.GetBuffer().AsSpan(0,checked((int)memory.Length)));} finally{Add("hashBuffer",start);} }
    public static IncrementalHash CreateHash() { var start=Stopwatch.GetTimestamp(); try{return IncrementalHash.CreateHash(HashAlgorithmName.SHA256);} finally{Add("hashCreate",start);} }
    public static async ValueTask<int> ReadSelected(FileStream stream, byte[] buffer, CancellationToken token, bool inline)
    { var start=Stopwatch.GetTimestamp(); try { if(!inline)return await stream.ReadAsync(buffer.AsMemory(),token); token.ThrowIfCancellationRequested();return stream.Read(buffer,0,buffer.Length); } finally{Add("readIo",start);} }
    public static async ValueTask<int> Read(FileStream stream, byte[] buffer, CancellationToken token) { var start=Stopwatch.GetTimestamp(); try{return await stream.ReadAsync(buffer.AsMemory(),token);} finally{Add("readIo",start);} }
    public static void Append(IncrementalHash hash, byte[] buffer, int count) { var start=Stopwatch.GetTimestamp(); try{hash.AppendData(buffer,0,count);} finally{Add("hashAppend",start);} }
    public static async ValueTask Write(MemoryStream memory, byte[] buffer, int count, CancellationToken token) { var start=Stopwatch.GetTimestamp(); try{await memory.WriteAsync(buffer.AsMemory(0,count),token);} finally{Add("bufferWrite",start);} }
    public static string FinishHash(IncrementalHash hash) { var start=Stopwatch.GetTimestamp(); try{return Convert.ToHexString(hash.GetHashAndReset()).ToLowerInvariant();} finally{Add("hashFinish",start);} }
    public static void RefreshMetadata(FileInfo info) { var start=Stopwatch.GetTimestamp(); try{info.Refresh();} finally{Add("metadataRefresh",start);} }
    public static FileAttributes Leaf(FileInfo info) { var start=Stopwatch.GetTimestamp(); Interlocked.Increment(ref Attrs); try{return info.Attributes;} finally{Add("attributes",start);} }
    public static FileAttributes Attributes(string path) { var start=Stopwatch.GetTimestamp(); Interlocked.Increment(ref Attrs); try{return File.GetAttributes(path);} finally{Add("attributes",start);} }
    public static void End(JsonElement id, string method, double invokeMs, double replyMs)
    {
        var stages = new Dictionary<string,double>();
        foreach (var local in Stages.Values) foreach (var pair in local) stages[pair.Key]=stages.GetValueOrDefault(pair.Key)+pair.Value;
        ObservedProcess.Refresh(); var cpuMs=(ObservedProcess.TotalProcessorTime.Ticks-Cpu)/10000.0;
        var events = Events.ToDictionary(e=>e.Key,e=>e.Value-EventStart.GetValueOrDefault(e.Key));
        Console.Error.WriteLine("BENCH_PROFILE " + JsonSerializer.Serialize(new { id, method, invokeMs, replyMs, stages,
            allocationPrecision="precise", allocatedBytes=GC.GetTotalAllocatedBytes(true)-Alloc, gcPauseMs=(GC.GetTotalPauseDuration().Ticks-Pause)/10000.0,
            gen0=GC.CollectionCount(0)-G0, gen1=GC.CollectionCount(1)-G1, gen2=GC.CollectionCount(2)-G2,
            Reads, Expired, Dirty, Invalidated, Bytes, Reused, Attrs, cpuMs, processorCount=Environment.ProcessorCount,
            poolThreads=ThreadPool.ThreadCount, poolPending=ThreadPool.PendingWorkItemCount, poolCompleted=ThreadPool.CompletedWorkItemCount-Completed, runtimeEvents=events }));
    }
}
'''
    if native_attributes:
        old = '    public static FileAttributes Attributes(string path)'
        added = '    public static FileAttributes NativeAttributes(string path) { var start=Stopwatch.GetTimestamp(); Interlocked.Increment(ref Attrs); try{return DarwinPathAttributes.ReadReparseFlag(path);} finally{Add("attributes",start);} }\n'
        assert s.count(old)==1
        s=s.replace(old,added+old)
    if 'class DarwinMetadataBatch' not in '\n'.join(p.read_text() for p in path.parent.glob('*.cs')):
        start=s.index('    public static bool Batch(')
        end=s.index('    public static IncrementalHash CreateHash()',start)
        s=s[:start]+s[end:]
    path.write_text(s)

    semantic_path = path.with_name('SemanticQueries.cs')
    semantic = semantic_path.read_text()
    declaration = ('        var symbols = await FindProjectDeclarations(solution, query, token);'
                   if 'FindProjectDeclarations(' in semantic else
                   '        var symbols = await FindCompilationDeclarations(solution, query, token);'
                   if 'FindCompilationDeclarations(' in semantic else
                   '        var symbols = await SymbolFinder.FindSourceDeclarationsAsync(solution,')
    returned = '        return Ordered(symbols, token).Where(symbol => !symbol.IsImplicitlyDeclared).Select(Item).ToArray();'
    assert semantic.count(declaration) == semantic.count(returned) == 1
    semantic = 'using System.Diagnostics;\n' + semantic
    semantic = semantic.replace(declaration, '        var findStarted = Stopwatch.GetTimestamp();\n' + declaration)
    semantic = semantic.replace(returned, '\n'.join([
        '        BenchProfile.Add("findDeclarations", findStarted);',
        '        var orderStarted = Stopwatch.GetTimestamp();',
        '        var ordered = Ordered(symbols, token);',
        '        BenchProfile.Add("orderSymbols", orderStarted);',
        '        var renderStarted = Stopwatch.GetTimestamp();',
        '        var result = ordered.Where(symbol => !symbol.IsImplicitlyDeclared).Select(Item).ToArray();',
        '        BenchProfile.Add("renderSymbols", renderStarted);',
        '        return result;']))
    semantic_path.write_text(semantic)
