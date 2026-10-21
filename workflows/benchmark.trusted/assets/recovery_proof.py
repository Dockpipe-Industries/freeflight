# SPDX-License-Identifier: Apache-2.0
"""Negative gates before a recovery candidate can enter performance qualification.
Copies actual path/open methods; isolated children contain potentially blocking FIFO
opens. Only those children are killed. This is not a production MCP benchmark.
"""
import hashlib, itertools, json, os, pathlib, platform, shutil, subprocess, time
root = pathlib.Path.cwd()
label = os.environ.get('FREEFLIGHT_RECOVERY_PROOF_LABEL', 'ordered-open-v1')
assert label and all(c.isalnum() or c in '-_' for c in label)
assert platform.system() == 'Darwin', 'This receipt qualifies only the pinned M6 host'
out = root / 'bin/.local/benchmarks/recovery-proof' / label
out.mkdir(parents=True, exist_ok=False)
source = (root / 'workers/roslyn/Program.cs').read_text()
sdk = shutil.which('dotnet'); assert sdk

def method(start, end):
    return source[source.index(start):source.index(end, source.index(start))]
opening = method('    [DllImport("libc", EntryPoint = "open"', '    private string CheckEditableInput')
opening = opening.replace('private FileStream OpenCompilerInput', 'public FileStream OpenCompilerInput')
pathcheck = method('    private string CheckPath(string path, HashSet<string>?', '    private static string ResolveRoot')
# Probe only internal workspace branch, but copy external branch without alteration.
helper = '''using System.Runtime.InteropServices;
using Microsoft.Win32.SafeHandles;
sealed class Reader(string root) {
    private readonly HashSet<string> externalCompilerInputs = new();
    private const StringComparison PathComparison = StringComparison.Ordinal;
    private readonly string selectedProject = "proof";
    public long Admit(string file) { CheckPath(file, null, null); return new FileInfo(file).Length; }
''' + opening + pathcheck + '''}
sealed class ProjectLoadException(string code, string message, string project,
    string remediation, object[] detail):Exception(message) {}
'''
(out/'Reader.cs').write_text(helper)
(out/'Proof.csproj').write_text('<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup><TargetFramework>net11.0</TargetFramework><OutputType>Exe</OutputType><ImplicitUsings>enable</ImplicitUsings><Nullable>enable</Nullable></PropertyGroup></Project>')
(out/'global.json').write_bytes((root/'global.json').read_bytes())
(out/'Program.cs').write_text(r'''
var directory=args[1];var reader=new Reader(directory);
var first=Path.Combine(directory,"A.cs");var later=Path.Combine(directory,"B.cs");
using var cancellation=new CancellationTokenSource();
if(args[0]=="serial") {
    cancellation.Token.ThrowIfCancellationRequested();
    if(reader.Admit(first)>1) { Console.WriteLine("ordered-error:A:maxFileBytes:2:1"); return; }
    throw new Exception("Expected first-file resource error");
}
int width=int.Parse(args[0]);
using var admitted=new CountdownEvent(width-1);
var pending=Enumerable.Range(1,width-1).Select(i=>Task.Factory.StartNew(()=> {
    cancellation.Token.ThrowIfCancellationRequested();
    reader.Admit(later); // Fresh ancestor/leaf checks, as in production.
    Console.WriteLine("validated-before-open:"+i);Console.Out.Flush();admitted.Signal();
    using var stream=reader.OpenCompilerInput(later);
    Console.WriteLine("opened:"+i);
}, CancellationToken.None, TaskCreationOptions.LongRunning, TaskScheduler.Default)).ToArray();
// Barrier controls the ordering; timeout belongs only to the containing process.
admitted.Wait();
if(reader.Admit(first)!=2)throw new Exception("Fixture mismatch");
Console.WriteLine("ordered-error:A:maxFileBytes:2:1");
cancellation.Cancel();Console.WriteLine("cancelled;draining");Console.Out.Flush();
await Task.WhenAll(pending);
Console.WriteLine("drained");
''')
with (out/'build.log').open('w') as log:
    subprocess.run([sdk,'build',str(out/'Proof.csproj'),'-c','Release','--disable-build-servers'],cwd=out,stdout=log,stderr=subprocess.STDOUT,check=True,timeout=180)
fixture=out/'fixture';fixture.mkdir();(fixture/'A.cs').write_bytes(b'xx');os.mkfifo(fixture/'B.cs')
dll=out/'bin/Release/net11.0/Proof.dll'
results=[]
for mode in ['serial','2','4']:
    logpath=out/(mode+'.log')
    with logpath.open('w') as log:
        process=subprocess.Popen([sdk,str(dll),mode,str(fixture)],stdout=log,stderr=subprocess.STDOUT,cwd=out)
        try:
            code=process.wait(timeout=3)
            timed_out=False
        except subprocess.TimeoutExpired:
            timed_out=True;process.kill();code=process.wait(timeout=10)
    text=logpath.read_text()
    if mode=='serial': assert code==0 and not timed_out and 'ordered-error:A:maxFileBytes:2:1' in text
    else:
        assert timed_out and text.count('validated-before-open:')==int(mode)-1 and 'cancelled;draining' in text and 'opened:' not in text and '\ndrained' not in text, text
    results.append(dict(mode=mode,exitCode=code,timedOut=timed_out,output=text))
# Enumerate all chunk completion schedules respecting each file's own chunk order.
serial=[('A',8),('A',4),('B',8),('B',4)]
schedules=[]
for a_positions in itertools.combinations(range(4),2):
    a=iter([8,4]); b=iter([8,4]); schedule=[('A',next(a)) if i in a_positions else ('B',next(b)) for i in range(4)]
    total=0;failure=None
    for file,count in schedule:
        total+=count
        if total>20: failure=dict(path=file,observedKiB=total,limitKiB=20);break
    ordered_total=0;ordered_failure=None
    for file,count in serial:
        ordered_total+=count
        if ordered_total>20:ordered_failure=dict(path=file,observedKiB=ordered_total,limitKiB=20);break
    schedules.append(dict(completion=schedule,sharedCounterFailure=failure,orderedLedgerFailure=ordered_failure))
assert any(s['sharedCounterFailure']!=s['orderedLedgerFailure'] for s in schedules)
receipt=dict(status='negative-gates-reproduced',runtimeCandidateAccepted=False,
    sourceCommit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip(),
    sourceSha256=hashlib.sha256(source.encode()).hexdigest(),helperSha256=hashlib.sha256(helper.encode()).hexdigest(),
    sdk=subprocess.check_output([sdk,'--version'],text=True).strip(),host=platform.platform(),
    processCases=results,accountingSchedules=schedules,
    limitation='Generated isolated internal-input path/open probe, not an end-to-end worker or timed MCP candidate. Three-second timeout establishes non-draining observation, not an infinite-time claim. No external input behavior was changed or exercised.')
(out/'result.json').write_text(json.dumps(receipt,indent=2)+'\n')
print(json.dumps(dict(receipt=str(out/'result.json'),status=receipt['status'],runtimeCandidateAccepted=False)))
