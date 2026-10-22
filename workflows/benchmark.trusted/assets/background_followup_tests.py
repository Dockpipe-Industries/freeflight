# SPDX-License-Identifier: Apache-2.0
"""Generated fault seams for serialized opt-in maintenance; no timing claims."""
import hashlib,json,os,pathlib,queue,shutil,subprocess,sys,threading,time
if len(sys.argv)>1:
 dotnet,source,destination,fixture=sys.argv[1:]
else:
 receipt=pathlib.Path.cwd()/'bin/.local/benchmarks/trusted'/os.environ['FREEFLIGHT_BACKGROUND_RECEIPT']
 config=json.loads((receipt/'provenance.json').read_text())
 size=os.environ.get('FREEFLIGHT_BACKGROUND_SIZE','433');assert size in ('433','5845')
 dotnet=config['dotnet'];source=str(receipt/'candidate/source');fixture=config['fixtures'][size]['root']
 destination=str(receipt/('background-adversarial-'+size))
out=pathlib.Path(destination);out.mkdir(exist_ok=False)
copy=out/'source';shutil.copytree(source,copy)
program=copy/'workers/roslyn/Program.cs';s=program.read_text()
s=s.replace('    private long backgroundAttempts;', '    private bool testOverflow, testCancel, testHold, testSwap;\n    private string? testDirty;\n    private long backgroundAttempts;')
s=s.replace('        backgroundAttempts++;', '''        backgroundAttempts++;
        if (testHold)
        {
            testHold = false;
            File.WriteAllText(Path.Combine(root!, ".background-entered"), "test-only");
            await Task.Delay(1000, token);
        }''')
anchor='        if (method != "open" && new[]';pos=s.index(anchor)
s=s[:pos]+'''        if (method == "test.background")
        {
            var action = args.GetProperty("action").GetString();
            if (action == "quiet") watcher!.EnableRaisingEvents = false;
            if (action == "due") recoveredAt -= 5001;
            if (action == "overflow") testOverflow = true;
            if (action == "cancel") testCancel = true;
            if (action == "hold") { testHold = true; recoveredAt -= 5001; }
            if (action == "swap") testSwap = true;
            if (action == "dirty") testDirty = args.GetProperty("file").GetString();
            if (action == "sweep") { recoveredAt -= 5001; await RecoverInBackground(token); }
            return new { recoveredAt, recoveredGeneration, committedBytes, backgroundAttempts,
                backgroundFailures, backgroundLastError, bytesRead, readFiles,
                cpuMs = System.Diagnostics.Process.GetCurrentProcess().TotalProcessorTime.TotalMilliseconds,
                fingerprints = fingerprints.OrderBy(x => x.Key).ToArray(),
                snapshots = snapshots.OrderBy(x => x.Key).ToArray(),
                dirty = dirtyFiles.OrderBy(x => x.Key).ToArray() };
        }
''' + s[pos:]
anchor='        token.ThrowIfCancellationRequested();\n        if (incrementalValidation && startGeneration'
assert s.count(anchor)==1
s=s.replace(anchor,'''        if (testOverflow) { testOverflow=false; Interlocked.Increment(ref invalidationGeneration); }
        if (testDirty is not null)
        {
            File.WriteAllText(testDirty, File.ReadAllText(testDirty).Replace("=> 0", "=> 6"));
            MarkDirty(testDirty); testDirty=null;
        }
        if (testCancel) { testCancel=false; throw new OperationCanceledException(); }
'''+anchor)
program.write_text(s)
from transaction import instrument
instrument(program)
s=program.read_text();anchor='            // Cached ancestor checks authorize snapshot admission, never a read.'
assert s.count(anchor)==1
s=s.replace(anchor,'''            if (testSwap)
            {
                testSwap=false;
                var parent=Path.GetDirectoryName(file)!;
                Directory.Move(parent, Path.Combine(root!, ".background-saved"));
                Directory.CreateSymbolicLink(parent, Path.Combine(Path.GetDirectoryName(root!)!, "outside"));
            }
'''+anchor);program.write_text(s)
with (out/'build.log').open('w') as log:
 subprocess.run([dotnet,'build',str(copy/'workers/roslyn/FreeFlight.Roslyn.csproj'),'-c','Release','--disable-build-servers','--artifacts-path',str(out/'build')],check=True,stdout=log,stderr=subprocess.STDOUT)
root=out/'fixture';shutil.copytree(fixture,root)
with (out/'restore.log').open('w') as log:
 project=sorted((root/'source').glob('P*/P*.csproj'))[-1]
 subprocess.run([dotnet,'restore',str(project)],check=True,stdout=log,stderr=subprocess.STDOUT)
dll=out/'build/bin/FreeFlight.Roslyn/release/FreeFlight.Roslyn.dll'
log=(out/'worker.stderr').open('w');p=subprocess.Popen([dotnet,str(dll),'--trusted-msbuild','--incremental-validation','--background-recovery'],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=log,text=True)
q=queue.Queue()
def read():
 for line in p.stdout:q.put(json.loads(line))
threading.Thread(target=read,daemon=True).start();seq=0;checks=[]
def call(method,**params):
 global seq
 seq+=1;p.stdin.write(json.dumps(dict(id=seq,method=method,params=params))+'\n');p.stdin.flush()
 r=q.get(timeout=60);assert r['id']==seq,r;return r
def state(action='state',**params):
 r=call('test.background',action=action,**params);assert 'result' in r,r;return r['result']
target=root/'source/P00/Nested/C0.cs';late=sorted(p for p in (root/'source').rglob('*.cs') if p.parent.name=='Nested')[-1]
original=target.read_bytes();lateBytes=late.read_bytes();stamp=target.stat()
(out/'outside').mkdir();(out/'outside/C0.cs').write_bytes(original)
try:
 assert 'result' in call('open',root=str(root),project=str(project.relative_to(root)))
 state('quiet');before=state()
 target.write_bytes(original.replace(b'=> 0',b'=> 9'));__import__('os').utime(target,ns=(stamp.st_atime_ns,stamp.st_mtime_ns))
 # Real production timer, with no event notification and no semantic trigger.
 time.sleep(5.2);after=state()
 hashes={x['key']:x['value'] for x in after['fingerprints']}
 assert hashes[str(target)]==hashlib.sha256(target.read_bytes()).hexdigest()
 assert after['backgroundAttempts']>before['backgroundAttempts'] and after['bytesRead']>before['bytesRead']
 checks.append(dict(case='real idle timer recovers same-size restored-timestamp edit',idleCpuMs=after['cpuMs']-before['cpuMs'],idleBytes=after['bytesRead']-before['bytesRead']))
 # A late failure must not publish the earlier changed target.
 before=state();target.write_bytes(original);late.unlink();failed=state('sweep')
 assert failed['fingerprints']==before['fingerprints'] and failed['snapshots']==before['snapshots']
 assert failed['committedBytes']==before['committedBytes'] and failed['recoveredGeneration']==-1
 assert 'error' in call('symbols',file=str(target))
 late.write_bytes(lateBytes);assert 'result' in call('symbols',file=str(target))
 checks.append(dict(case='failed background sweep preserves state and forces foreground failure/recovery'))
 for action in ['overflow','cancel']:
  before=state();state(action);failed=state('sweep')
  assert failed['fingerprints']==before['fingerprints'] and failed['snapshots']==before['snapshots']
  assert failed['recoveredGeneration']==-1
  assert 'result' in call('symbols',file=str(target))
  checks.append(dict(case=action+' during background sweep rejects transaction'))
 state('dirty',file=str(target));after=state('sweep')
 assert any(x['key']==str(target) for x in after['dirty'])
 assert 'result' in call('symbols',file=str(late))
 hashes={x['key']:x['value'] for x in state()['fingerprints']}
 assert hashes[str(target)]==hashlib.sha256(target.read_bytes()).hexdigest()
 checks.append(dict(case='edit after background read remains pending and next non-target query refreshes it'))
 # Replace an admitted ancestor immediately before an uncached background read.
 before=state();state('swap');failed=state('sweep')
 assert target.parent.is_symlink() and failed['bytesRead']==before['bytesRead']
 assert failed['fingerprints']==before['fingerprints'] and failed['snapshots']==before['snapshots']
 target.parent.unlink();(root/'.background-saved').rename(target.parent)
 assert 'result' in call('symbols',file=str(target))
 checks.append(dict(case='background ancestor replacement rejected before content read'))
 # Foreground target still freshly read even between successful maintenance passes.
 target.write_bytes(original.replace(b'=> 0',b'=> 7'))
 r=call('rename',file=str(target),line=0,character=45,newName='Next');assert 'result' in r,r
 edit=next(x for x in r['result']['edits'] if x['file']==str(target))
 assert edit['expectedSha256']==hashlib.sha256(target.read_bytes()).hexdigest()
 checks.append(dict(case='fresh target and rename preview hash after idle recovery'))
 # Real timer holds the production gate; request cancellation must still reply.
 state('hold');deadline=time.monotonic()+5
 while not (root/'.background-entered').exists() and time.monotonic()<deadline:time.sleep(.01)
 assert (root/'.background-entered').exists(), 'timer did not enter controlled hold'
 seq+=1;cancelId=seq
 p.stdin.write(json.dumps(dict(id=cancelId,method='symbols',params=dict(file=str(target))))+'\n')
 p.stdin.write(json.dumps(dict(id='cancel-control',method='cancel',params=dict(id=cancelId)))+'\n');p.stdin.flush()
 r=q.get(timeout=.8);assert r['id']==cancelId and 'cancelled' in r['error']['message'].lower(),r
 checks.append(dict(case='request cancellation while queued behind maintenance'))
 # EOF cancels the timer while it owns the gate and joins before engine disposal.
 p.stdin.close();p.wait(timeout=15);assert p.returncode==0
 checks.append(dict(case='EOF cancels active maintenance and joins lifetime'))
finally:
 if p.poll() is None:p.kill();p.wait()
 log.close()
stderr=(out/'worker.stderr').read_text();assert 'Unhandled exception' not in stderr and 'BENCH_TRANSACTION_FAILURE' not in stderr
(out/'result.json').write_text(json.dumps(dict(status='passed',checks=checks,adapterSha256=hashlib.sha256(pathlib.Path(__file__).read_bytes()).hexdigest(),sourceSha256=hashlib.sha256((pathlib.Path(source)/'workers/roslyn/Program.cs').read_bytes()).hexdigest()),indent=2)+'\n')
print(json.dumps(checks,indent=2))
