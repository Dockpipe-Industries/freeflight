# SPDX-License-Identifier: Apache-2.0
"""Actual-worker idle EOF negative control, using only disposable task fixtures."""
import hashlib,json,os,pathlib,queue,shutil,subprocess,threading,time
root=pathlib.Path.cwd();receipt=root/'bin/.local/benchmarks/trusted'/os.environ['FREEFLIGHT_BACKGROUND_RECEIPT']
config=json.loads((receipt/'provenance.json').read_text());out=receipt/'background-fifo-proof';out.mkdir(exist_ok=False)
expectBlocked=os.environ.get('FREEFLIGHT_BACKGROUND_FIFO_EXPECT','blocked')=='blocked'
results=[]
for variant in ['baseline','candidate']:
 d=out/variant;d.mkdir();source=d/'source';shutil.copytree(receipt/variant/'source',source)
 program=source/'workers/roslyn/Program.cs';s=program.read_text()
 anchor='            using var stream = OpenCompilerInput(file);';assert s.count(anchor)==1
 s=s.replace(anchor,'''            if (File.Exists(Path.Combine(root!, ".fifo-probe")))
            { Console.Error.WriteLine("BENCH_FIFO_OPEN:" + file); Console.Error.Flush(); }
'''+anchor);program.write_text(s)
 with (d/'build.log').open('w') as log:
  subprocess.run([config['dotnet'],'build',str(source/'workers/roslyn/FreeFlight.Roslyn.csproj'),'-c','Release','--disable-build-servers','--artifacts-path',str(d/'build')],stdout=log,stderr=subprocess.STDOUT,check=True)
 fixture=d/'fixture';shutil.copytree(config['fixtures']['433']['root'],fixture)
 with (d/'restore.log').open('w') as log:
  subprocess.run([config['dotnet'],'restore',str(fixture/'source/P01/P01.csproj')],stdout=log,stderr=subprocess.STDOUT,check=True)
 dll=d/'build/bin/FreeFlight.Roslyn/release/FreeFlight.Roslyn.dll'
 p=subprocess.Popen([config['dotnet'],str(dll),'--trusted-msbuild','--incremental-validation',*(['--background-recovery'] if variant=='candidate' else [])],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
 replies=queue.Queue();markers=queue.Queue();lines=[]
 def stdout():
  for line in p.stdout:replies.put(json.loads(line))
 def stderr():
  for line in p.stderr:
   lines.append(line)
   if 'BENCH_FIFO_OPEN:' in line:markers.put(line.strip())
 threading.Thread(target=stdout,daemon=True).start();threading.Thread(target=stderr,daemon=True).start()
 try:
  p.stdin.write(json.dumps(dict(id=1,method='open',params=dict(root=str(fixture),project='source/P01/P01.csproj')))+'\n');p.stdin.flush()
  loaded=replies.get(timeout=60);assert 'result' in loaded,loaded
  target=fixture/'source/P00/Nested/C0.cs';target.unlink();os.mkfifo(target);(fixture/'.fifo-probe').write_text('test-only')
  marker=markers.get(timeout=8) if variant=='candidate' else None
  if marker:assert str(target) in marker,marker
  start=time.monotonic();p.stdin.close()
  try:code=p.wait(timeout=2);timedOut=False
  except subprocess.TimeoutExpired:timedOut=True;p.kill();code=p.wait(timeout=10)
  results.append(dict(variant=variant,marker=marker,eofSeconds=time.monotonic()-start,timedOut=timedOut,exitCode=code))
 finally:
  if p.poll() is None:p.kill();p.wait(timeout=10)
  (d/'worker.stderr').write_text(''.join(lines))
assert not results[0]['timedOut'] and results[0]['exitCode']==0,results
assert results[1]['timedOut']==expectBlocked,results
if not expectBlocked:assert results[1]['exitCode']==0,results
result=dict(status='negative-gate-reproduced' if expectBlocked else 'passed',runtimeCandidateAccepted=False,cases=results,adapterSha256=hashlib.sha256(pathlib.Path(__file__).read_bytes()).hexdigest(),candidateSourceHashes=config['variants']['candidate']['sourceHashes'],limitation='FIFO-specific two-second observation, not a general syscall-termination guarantee. Only task-owned probe children may be terminated.')
(out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result['cases'],indent=2))
