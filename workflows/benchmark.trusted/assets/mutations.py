# SPDX-License-Identifier: Apache-2.0
import pathlib, subprocess, json, os, queue, threading, time
import sys, shutil
# Reuse the deterministic two-project benchmark fixture; mutate only a private copy.
dotnet,dll,destination,fixture=sys.argv[1:]
B=pathlib.Path(destination);B.mkdir(parents=True)
root=B/'fixture';shutil.copytree(fixture,root)
subprocess.run([dotnet,'restore',str(root/'source/P01/P01.csproj'),'--ignore-failed-sources'],check=True,stdout=subprocess.DEVNULL)
p=subprocess.Popen([dotnet,dll,'--trusted-msbuild'],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=(B/'worker.stderr').open('w'),text=True,env=dict(os.environ,DOTNET_ROOT=str(pathlib.Path(dotnet).parent)))
q=queue.Queue()
def reader():
 for line in p.stdout:q.put(line)
threading.Thread(target=reader,daemon=True).start();seq=0
checks=[]
def call(method,**params):
 global seq
 seq+=1;p.stdin.write(json.dumps(dict(id=seq,method=method,params=params))+'\n');p.stdin.flush();r=json.loads(q.get(timeout=90));assert r['id']==seq;return r

def opened():
 r=call('open',root=str(root),project='source/P01/P01.csproj');assert 'result' in r,r;return r['result']
target=root/'source/P00/Nested/C0.cs'; original=target.read_bytes(); stamp=target.stat(); nested=target.parent; moved=nested.with_name('Nested-moved'); outside=B/'outside-ancestor';outside.mkdir(exist_ok=True);(outside/'C0.cs').write_bytes(original)
try:
 opened()
 target.write_bytes(original.replace(b'=> 0',b'=> 9'));os.utime(target,ns=(stamp.st_atime_ns,stamp.st_mtime_ns))
 r=call('rename',file=str(target),line=0,character=45,newName='Next');assert 'result' in r,r
 import hashlib
 edit=next(x for x in r['result']['edits'] if x['file']==str(target));assert edit['expectedSha256']==hashlib.sha256(target.read_bytes()).hexdigest()
 checks.append('fresh target and preview hash with preserved size/mtime')
 # Fail late after staging an earlier target update; the transaction-instrumented
 # qualification additionally asserts all committed maps/solution are unchanged.
 late=root/'source/P01/Nested/C431.cs'; late_bytes=late.read_bytes()
 target.write_bytes(original.replace(b'=> 0',b'=> 8'));late.unlink()
 try:
  failure=call('symbols',file=str(target));assert 'error' in failure and 'result' not in failure,failure
 finally:late.write_bytes(late_bytes)
 assert 'result' in call('symbols',file=str(target))
 checks.append('late missing input rejects whole refresh after earlier staged target update')
 nested.rename(moved);nested.symlink_to(outside,target_is_directory=True)
 r=call('symbols',file='source/P01/Nested/C1.cs');assert 'error' in r and 'Symlink' in str(r),r
 nested.unlink();moved.rename(nested);assert 'result' in call('symbols',file=str(target));checks.append('non-target ancestor replaced with escaping symlink rejects whole query; recovery')
 target.unlink();assert 'error' in call('symbols',file='source/P01/Nested/C1.cs');target.write_bytes(original);checks.append('deleted trusted member fails without silently omitting it')
 added=nested/'Added.cs';added.write_text('class Added {}')
 assert 'error' in call('symbols',file=str(added));assert opened()['files']==434;assert 'result' in call('symbols',file=str(added));added.unlink();assert opened()['files']==433;checks.append('trusted addition/removal adopts graph only on reopen')
 generation=call('capabilities')['result']['refreshStats']['invalidationGeneration']
 events=root/'events-combined';events.mkdir(exist_ok=True)
 for i in range(4200):(events/f'{i}.txt').write_text('event')
 deadline=time.monotonic()+10
 while time.monotonic()<deadline:
  stats=call('capabilities')['result']['refreshStats']
  if stats['invalidationGeneration']>generation:break
  time.sleep(.05)
 assert stats['invalidationGeneration']>generation,stats
 before=stats['bytesRead'];assert 'result' in call('symbols',file=str(target));after=call('capabilities')['result']['refreshStats']['bytesRead']
 assert after-before==sum(x.stat().st_size for x in (root/'source').rglob('*.cs')), (after-before)
 checks.append('trusted watcher bookkeeping overflow advances generation and rereads entire graph')
 print(json.dumps(dict(passed=checks),indent=2))
finally:
 if nested.is_symlink():nested.unlink()
 if moved.exists():moved.rename(nested)
 target.write_bytes(original)
 p.stdin.close();p.wait(timeout=15)
