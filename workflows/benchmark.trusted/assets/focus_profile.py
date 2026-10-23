# SPDX-License-Identifier: Apache-2.0
"""Narrow generated semantic-stage profile of a frozen worker, not MCP timing."""
import hashlib
import json
import os
from pathlib import Path
import queue
import shutil
import statistics
import subprocess
import threading
import time
import run as trusted

repo = Path.cwd()
receipt = repo/'bin/.local/benchmarks/trusted'/os.environ.get('FREEFLIGHT_FOCUS_RECEIPT','background-cooperative-v4')
config = json.loads((receipt/'provenance.json').read_text())
label = os.environ['FREEFLIGHT_FOCUS_LABEL']
assert label and all(c.isalnum() or c in '-_' for c in label)
out = repo/'bin/.local/benchmarks/focus'/label
out.mkdir(parents=True, exist_ok=False)
source = out/'source'
shutil.copytree(receipt/'candidate/source', source)
for name, expected in config['variants']['candidate']['sourceHashes'].items():
    assert trusted.digest(source/name)==expected, name
program=source/'workers/roslyn/Program.cs'
s=program.read_text()
def replace(old,new):
    global s
    assert s.count(old)==1, old
    s=s.replace(old,new)
replace('try { Reply(new { id, result = await engine.Invoke(method, args, cts.Token) }); }',
        'try { FocusProfile.Begin(); using(FocusProfile.Scope("empty")) {} var value=await engine.Invoke(method,args,cts.Token); FocusProfile.End(id,method); Reply(new { id, result=value }); }')
replace('        await Refresh(token, requestedFile, method == "rename");',
        '        using (FocusProfile.Scope("refresh")) await Refresh(token, requestedFile, method == "rename");')
for old,new in [
 ('        var text = await document.GetTextAsync(token);','        SourceText text; using (FocusProfile.Scope("text")) text=await document.GetTextAsync(token);'),
 ('        var syntax = await document.GetSyntaxRootAsync(token) ?? throw new InvalidOperationException("Syntax unavailable");','        SyntaxNode syntax; using (FocusProfile.Scope("syntax")) syntax=await document.GetSyntaxRootAsync(token) ?? throw new InvalidOperationException("Syntax unavailable");'),
 ('        var model = await document.GetSemanticModelAsync(token) ?? throw new InvalidOperationException("Semantic model unavailable");','        SemanticModel model; using (FocusProfile.Scope("model")) model=await document.GetSemanticModelAsync(token) ?? throw new InvalidOperationException("Semantic model unavailable");'),
 ('        var symbolAt = await SymbolFinder.FindSymbolAtPositionAsync(document, position, token);','        ISymbol? symbolAt; using (FocusProfile.Scope("findSymbol")) symbolAt=await SymbolFinder.FindSymbolAtPositionAsync(document, position, token);'),
 ('                var sourceDefinition = await SymbolFinder.FindSourceDefinitionAsync(symbolAt, workspace.CurrentSolution, token) ?? symbolAt;','                ISymbol sourceDefinition; using (FocusProfile.Scope("sourceDefinition")) sourceDefinition=await SymbolFinder.FindSourceDefinitionAsync(symbolAt, workspace.CurrentSolution, token) ?? symbolAt;')]:replace(old,new)
s+='''
internal static class FocusProfile
{
    private static readonly AsyncLocal<Dictionary<string,(double ms,long bytes)>?> Current=new();
    private static readonly AsyncLocal<long> Allocated=new();
    public static void Begin() { Current.Value=new(); Allocated.Value=GC.GetTotalAllocatedBytes(true); }
    public static IDisposable Scope(string name)=>new Timed(name);
    private sealed class Timed(string name):IDisposable
    {
        private readonly long bytes=GC.GetTotalAllocatedBytes(true);
        private readonly long start=System.Diagnostics.Stopwatch.GetTimestamp();
        public void Dispose()
        {
            if(Current.Value is not {} metrics)return;
            var elapsed=System.Diagnostics.Stopwatch.GetElapsedTime(start).TotalMilliseconds;
            var old=metrics.GetValueOrDefault(name);
            metrics[name]=(old.ms+elapsed,
                           old.bytes+GC.GetTotalAllocatedBytes(true)-bytes);
        }
    }
    public static void End(JsonElement id,string method)
    {
        Console.Error.WriteLine("FOCUS_PROFILE "+JsonSerializer.Serialize(new { id,method,
            allocatedBytes=GC.GetTotalAllocatedBytes(true)-Allocated.Value,
            stages=Current.Value!.ToDictionary(x=>x.Key,x=>new {ms=x.Value.ms,bytes=x.Value.bytes}) }));
        Current.Value=null;
    }
}
'''
program.write_text(s)
semantic=source/'workers/roslyn/SemanticQueries.cs'
s=semantic.read_text()
old='        var symbols = await SymbolFinder.FindSourceDeclarationsAsync(solution,\n            name => name.Contains(query, StringComparison.OrdinalIgnoreCase), SymbolFilter.TypeAndMember, token);'
assert s.count(old)==1
s=s.replace(old,'        IEnumerable<ISymbol> symbols; using (FocusProfile.Scope("declarations"))\n            symbols = await SymbolFinder.FindSourceDeclarationsAsync(solution,\n            name => name.Contains(query, StringComparison.OrdinalIgnoreCase), SymbolFilter.TypeAndMember, token);')
old='        return Ordered(symbols, token).Where(symbol => !symbol.IsImplicitlyDeclared).Select(Item).ToArray();'
assert s.count(old)==1
s=s.replace(old,'        ISymbol[] ordered; using(FocusProfile.Scope("order")) ordered=Ordered(symbols,token);\n        using(FocusProfile.Scope("render")) return ordered.Where(symbol=>!symbol.IsImplicitlyDeclared).Select(Item).ToArray();')
semantic.write_text(s)
with (out/'build.log').open('w') as log:
    subprocess.run([config['dotnet'],'build',str(source/'workers/roslyn/FreeFlight.Roslyn.csproj'),'-c','Release',
        '-p:RestoreLockedMode=true','--disable-build-servers','--artifacts-path',str(out/'build')],stdout=log,stderr=subprocess.STDOUT,check=True)
dll=out/'build/bin/FreeFlight.Roslyn/release/FreeFlight.Roslyn.dll'
fixture=dict(config['fixtures']['5845']);fixture['root']=str(Path(fixture['root']).resolve())
queries,check=trusted.workload(fixture,5845)
records=[]
for session in range(2):
    log=(out/f'{session}.stderr').open('w')
    p=subprocess.Popen([config['dotnet'],str(dll),'--trusted-msbuild','--incremental-validation','--background-recovery'],
        stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=log,text=True)
    q=queue.Queue();seq=0
    def read(worker=p,output=q):
        for line in worker.stdout:output.put(json.loads(line))
    threading.Thread(target=read,daemon=True).start()
    def call(method,**params):
        global seq
        seq+=1;p.stdin.write(json.dumps(dict(id=seq,method=method,params=params))+'\n');p.stdin.flush()
        result=q.get(timeout=60);assert result['id']==seq and 'result' in result,result
        return result['result']
    try:
        opened=call('open',root=fixture['root'],project=fixture['project']);assert opened['files']==5845
        start=time.monotonic();round_index=0;measured_rounds=0
        while time.monotonic()-start<5 or measured_rounds<25:
            round_start=time.monotonic();steady=round_start-start>=5
            design=((0,1,3,2),(1,2,0,3),(2,3,1,0),(3,0,2,1))
            for i in design[round_index%4]:
                method,args=queries[i];result=call(method,**args);check(method,result)
                records.append(dict(session=session,round=round_index,requestId=seq,method=method,
                                    steady=steady))
            measured_rounds+=int(steady)
            round_index+=1;time.sleep(max(0,.1-(time.monotonic()-round_start)))
    finally:
        p.stdin.close()
        try:p.wait(timeout=15)
        except subprocess.TimeoutExpired:p.kill();p.wait();raise
        log.close()
    assert p.returncode==0
assert sum(record['steady'] for record in records)==200
profiles=[]
for session in range(2):
    for line in (out/f'{session}.stderr').read_text().splitlines():
        if line.startswith('FOCUS_PROFILE '):profiles.append(dict(session=session,**json.loads(line[len('FOCUS_PROFILE '):])))
joined=[]
for record in records:
    if not record['steady']:continue
    profile=next(x for x in profiles if x['session']==record['session'] and x['id']==record['requestId'])
    joined.append(dict(**record,profile=profile))
result=dict(status='passed',scope='Diagnostic direct-worker attribution; helper overhead and process-wide allocation included; not ordinary MCP/Glider timing.',
    originalSourceHashes=config['variants']['candidate']['sourceHashes'],adapterSha256=trusted.digest(Path(__file__)),samples=joined)
(out/'result.json').write_text(json.dumps(result,indent=2)+'\n')
shutil.copy2(__file__,out/'adapter-source.py')
for method in ('definition','workspaceSymbols'):
    chosen=[x['profile'] for x in joined if x['method']==method]
    stages={key:dict(ms=statistics.median(x['stages'][key]['ms'] for x in chosen),bytes=statistics.median(x['stages'][key]['bytes'] for x in chosen)) for key in chosen[0]['stages']}
    print(method,json.dumps(stages),flush=True)
