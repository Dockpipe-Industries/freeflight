# SPDX-License-Identifier: Apache-2.0
"""Lightweight generated-source boundary timers; no allocation counters/listeners."""
def worker(path):
 s=path.read_text()
 def replace(old,new):
  nonlocal s
  assert s.count(old)==1,old
  s=s.replace(old,new)
 replace('using System.Collections.Concurrent;','using System.Collections.Concurrent;\nusing System.Diagnostics;')
 replace('                jobs.Add(Task.Run(async () =>','                var costQueued=Stopwatch.GetTimestamp();\n                jobs.Add(Task.Run(async () =>')
 replace('                        await gate.WaitAsync(cts.Token);','                        var costRunning=Stopwatch.GetTimestamp();\n                        await gate.WaitAsync(cts.Token);\n                        var costAdmitted=Stopwatch.GetTimestamp();')
 replace('try { Reply(new { id, result = await engine.Invoke(method, args, cts.Token) }); }','''try {
                            DefinitionCost.Begin();
                            DefinitionCost.Values.Value!["queue"]=Stopwatch.GetElapsedTime(costQueued,costRunning).TotalMilliseconds;
                            DefinitionCost.Values.Value!["gate"]=Stopwatch.GetElapsedTime(costRunning,costAdmitted).TotalMilliseconds;
                            var costInvoke=Stopwatch.GetTimestamp();
                            var result=await engine.Invoke(method,args,cts.Token);
                            DefinitionCost.Add("invoke",costInvoke);
                            Reply(new {id,result});
                            DefinitionCost.End(id,method);
                        }''')
 replace('            lock (outputGate) output.WriteLine(JsonSerializer.Serialize(value, Json));','''            lock(outputGate) {
                var start=Stopwatch.GetTimestamp();var serialized=JsonSerializer.Serialize(value,Json);
                DefinitionCost.Add("serialize",start);start=Stopwatch.GetTimestamp();output.WriteLine(serialized);
                DefinitionCost.Add("write",start);
            }''')
 replace('        if (method == "capabilities") return new','        if(method=="test.transport") return new {ok=true};\n        if (method == "capabilities") return new')
 replace('operations = new[] { "symbols",','operations = new[] { "test.transport", "symbols",')
 replace('        await Refresh(token, requestedFile, method == "rename");','        using(DefinitionCost.Scope("refresh")) await Refresh(token, requestedFile, method == "rename");')
 for name,old,new in [
 ('text','        var text = await document.GetTextAsync(token);','        SourceText text; using(DefinitionCost.Scope("text")) text=await document.GetTextAsync(token);'),
 ('syntax','        var syntax = await document.GetSyntaxRootAsync(token) ?? throw new InvalidOperationException("Syntax unavailable");','        SyntaxNode syntax; using(DefinitionCost.Scope("syntax")) syntax=await document.GetSyntaxRootAsync(token) ?? throw new InvalidOperationException("Syntax unavailable");'),
 ('model','        var model = await document.GetSemanticModelAsync(token) ?? throw new InvalidOperationException("Semantic model unavailable");','        SemanticModel model; using(DefinitionCost.Scope("model")) model=await document.GetSemanticModelAsync(token) ?? throw new InvalidOperationException("Semantic model unavailable");'),
 ('find','        var symbolAt = await SymbolFinder.FindSymbolAtPositionAsync(document, position, token);','        ISymbol? symbolAt;using(DefinitionCost.Scope("findSymbol")) symbolAt=await SymbolFinder.FindSymbolAtPositionAsync(document,position,token);'),
 ('source','                var sourceDefinition = await SymbolFinder.FindSourceDefinitionAsync(symbolAt, workspace.CurrentSolution, token) ?? symbolAt;','                ISymbol sourceDefinition;using(DefinitionCost.Scope("sourceDefinition")) sourceDefinition=await SymbolFinder.FindSourceDefinitionAsync(symbolAt,workspace.CurrentSolution,token) ?? symbolAt;')]:replace(old,new)
 s+='''
internal static class DefinitionCost
{
 public static readonly AsyncLocal<Dictionary<string,double>?> Values=new();
 private static double PreviousLogMs;
 public static void Begin()=>Values.Value=new();
 public static void Add(string stage,long start){if(Values.Value is {} v)v[stage]=v.GetValueOrDefault(stage)+Stopwatch.GetElapsedTime(start).TotalMilliseconds;}
 public static IDisposable Scope(string stage)=>new Timed(stage);
 private sealed class Timed(string stage):IDisposable {readonly long start=Stopwatch.GetTimestamp();public void Dispose()=>Add(stage,start);}
 [DllImport("libc",EntryPoint="write")] private static extern nint WriteRecord(int fd,byte[] buffer,nuint count);
 public static void End(JsonElement id,string method){var start=Stopwatch.GetTimestamp();var bytes=Encoding.UTF8.GetBytes("DEFINITION_COST "+JsonSerializer.Serialize(new {id,method,stages=Values.Value,previousLogMs=PreviousLogMs})+"\\n");if(WriteRecord(2,bytes,(nuint)bytes.Length)!=(nint)bytes.Length)throw new IOException("Diagnostic log write failed");PreviousLogMs=Stopwatch.GetElapsedTime(start).TotalMilliseconds;Values.Value=null;}
}
'''
 path.write_text(s)


def extended(path):
 """Additional generated-only scopes for the four-operation boundary probe."""
 s=path.read_text()
 def replace(old,new):
  nonlocal s
  assert s.count(old)==1,old
  s=s.replace(old,new)
 replace('                            var costInvoke=Stopwatch.GetTimestamp();','                            using(DefinitionCost.Scope("empty")) {}\n                            var costInvoke=Stopwatch.GetTimestamp();')
 replace('    private string CheckPath(string path, HashSet<string>? checkedAncestors, FileInfo? leafInfo)\n    {','    private string CheckPath(string path, HashSet<string>? checkedAncestors, FileInfo? leafInfo)\n    {\n        using var costPath=DefinitionCost.Scope("pathCheck");')
 replace('        var startRevision = refreshRevision;','        var costFiles=readFiles; var costBytes=bytesRead; var costRecoveries=fullRecoveries;\n        var startRevision = refreshRevision;')
 replace('            var file = info.FullName;','            var costMetadata=Stopwatch.GetTimestamp();\n            var file = info.FullName;')
 replace('            var length = batchMetadata?.Length ?? info.Length;','            DefinitionCost.Add("metadataAdmission",costMetadata);\n            var length = batchMetadata?.Length ?? info.Length;')
 replace('            using var stream = OpenCompilerInput(file);','            var costOpen=Stopwatch.GetTimestamp();\n            using var stream = OpenCompilerInput(file);\n            DefinitionCost.Add("openHandle",costOpen);\n            var costRead=Stopwatch.GetTimestamp();')
 replace('            memory.Position = 0;','            DefinitionCost.Add("readHash",costRead);\n            memory.Position = 0;')
 anchor='''                ((ICollection<KeyValuePair<string, long>>)dirtyFiles).Remove(change);
        }
    }
'''
 replace(anchor,anchor.replace('        }\n    }','        }\n        DefinitionCost.Counter("readFiles",readFiles-costFiles);\n        DefinitionCost.Counter("readBytes",bytesRead-costBytes);\n        DefinitionCost.Counter("fullRecoveries",fullRecoveries-costRecoveries);\n    }'))
 replace('                var references = await SymbolFinder.FindReferencesAsync(symbolAt, workspace.CurrentSolution, token);','                IEnumerable<ReferencedSymbol> references; using(DefinitionCost.Scope("findReferences")) references=await SymbolFinder.FindReferencesAsync(symbolAt,workspace.CurrentSolution,token);')
 replace('                return references.SelectMany(r => r.Locations).Select(r => Location(r.Location)).OrderBy(l => JsonSerializer.Serialize(l), StringComparer.Ordinal).ToArray();','                using(DefinitionCost.Scope("referenceRender")) return references.SelectMany(r => r.Locations).Select(r => Location(r.Location)).OrderBy(l => JsonSerializer.Serialize(l), StringComparer.Ordinal).ToArray();')
 replace(' public static void Begin()=>Values.Value=new();',' public static readonly AsyncLocal<Dictionary<string,long>?> Counters=new();\n public static void Begin(){Values.Value=new();Counters.Value=new();}\n public static void Counter(string name,long value){if(Counters.Value is {} c)c[name]=c.GetValueOrDefault(name)+value;}')
 replace('stages=Values.Value,previousLogMs=PreviousLogMs','stages=Values.Value,counters=Counters.Value,previousLogMs=PreviousLogMs')
 path.write_text(s)
 semantic=path.with_name('SemanticQueries.cs');s=semantic.read_text()
 replace('        var symbols = await SymbolFinder.FindSourceDeclarationsAsync(solution,\n            name => name.Contains(query, StringComparison.OrdinalIgnoreCase), SymbolFilter.TypeAndMember, token);','        IEnumerable<ISymbol> symbols; using(DefinitionCost.Scope("searchDeclarations")) symbols=await SymbolFinder.FindSourceDeclarationsAsync(solution,\n            name => name.Contains(query, StringComparison.OrdinalIgnoreCase), SymbolFilter.TypeAndMember, token);')
 replace('        return Ordered(symbols, token).Where(symbol => !symbol.IsImplicitlyDeclared).Select(Item).ToArray();','        ISymbol[] ordered; using(DefinitionCost.Scope("searchOrder")) ordered=Ordered(symbols,token);\n        using(DefinitionCost.Scope("searchRender")) return ordered.Where(symbol=>!symbol.IsImplicitlyDeclared).Select(Item).ToArray();')
 semantic.write_text(s)


def replay_search(path):
 """Generated-only fixed-payload control. Never used in production workers."""
 s=path.read_text()
 def replace(old,new):
  nonlocal s
  assert s.count(old)==1,old
  s=s.replace(old,new)
 replace('    private readonly AdhocWorkspace workspace = new();','    private object? costSearchReplay;\n    private readonly AdhocWorkspace workspace = new();')
 replace('        if(method=="test.transport") return new {ok=true};','        if(method=="test.replaySearch") return costSearchReplay ?? throw new InvalidOperationException("Prime search replay first");\n        if(method=="test.transport") return new {ok=true};')
 replace('operations = new[] { "test.transport", "symbols",','operations = new[] { "test.replaySearch", "test.transport", "symbols",')
 replace('''        if (method == "workspaceSymbols")
            return await SemanticQueries.WorkspaceSymbols(workspace.CurrentSolution,
                args.GetProperty("query").GetString() ?? "", token);''','''        if (method == "workspaceSymbols")
        {
            var costResult=await SemanticQueries.WorkspaceSymbols(workspace.CurrentSolution,
                args.GetProperty("query").GetString() ?? "", token);
            costSearchReplay=costResult;
            return costResult;
        }''')
 path.write_text(s)
