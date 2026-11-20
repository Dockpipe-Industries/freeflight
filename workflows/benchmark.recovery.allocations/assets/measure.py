# SPDX-License-Identifier: Apache-2.0
"""EventPipe sampling only inside successful synthetic background sweeps."""
import hashlib,json,os,queue,shutil,subprocess,threading,time
from pathlib import Path
repo=Path.cwd();assets=Path(__file__).parent
receipt=repo/'bin/.local/benchmarks/trusted/background-cooperative-v4'
config=json.loads((receipt/'provenance.json').read_text());label=os.environ['FREEFLIGHT_ALLOCATION_LABEL']
assert label and all(c.isalnum() or c in '-_' for c in label)
out=repo/'bin/.local/benchmarks/allocations'/label;out.mkdir(parents=True,exist_ok=False)
def save(p,d):p.write_text(json.dumps(d,indent=2)+'\n')
def command(args,name):
 with (out/name).open('w') as log:subprocess.run(args,stdout=log,stderr=subprocess.STDOUT,check=True)
source=out/'source';shutil.copytree(receipt/'candidate/source',source)
for name,digest in config['variants']['candidate']['sourceHashes'].items():assert hashlib.sha256((source/name).read_bytes()).hexdigest()==digest
p=source/'workers/roslyn/Program.cs';s=p.read_text()
anchor='            await Refresh(token, forceAll: true);'
assert s.count(anchor)==1
s=s.replace(anchor,'''            var sweepCpu=System.Diagnostics.Process.GetCurrentProcess().TotalProcessorTime.TotalMilliseconds;
            var sweepAlloc=GC.GetTotalAllocatedBytes(true); var sweepReads=readFiles;var sweepBytes=bytesRead;
            AllocationProbe.Log.Begin();
            await Refresh(token, forceAll: true);
            AllocationProbe.Log.Success(readFiles-sweepReads,bytesRead-sweepBytes,GC.GetTotalAllocatedBytes(true)-sweepAlloc,
                System.Diagnostics.Process.GetCurrentProcess().TotalProcessorTime.TotalMilliseconds-sweepCpu);
''')
s+='''
[System.Diagnostics.Tracing.EventSource(Name="FreeFlight-Allocation-Probe")]
internal sealed class AllocationProbe:System.Diagnostics.Tracing.EventSource
{
    public static readonly AllocationProbe Log=new();
    [System.Diagnostics.Tracing.Event(1)] public void Begin()=>WriteEvent(1);
    [System.Diagnostics.Tracing.Event(2)] public void Success(long files,long bytes,long allocated,double cpuMs)=>WriteEvent(2,files,bytes,allocated,cpuMs);
}
'''
p.write_text(s)
collector=out/'collector';collector.mkdir()
for name in ['Collector.csproj','Collector.cs','packages.lock.json']:shutil.copy2(assets/name,collector/name)
command([config['dotnet'],'build',str(collector/'Collector.csproj'),'-p:RestoreLockedMode=true','-c','Release','--disable-build-servers','--artifacts-path',str(out/'collector-build')],'collector-build.log')
command([config['dotnet'],'build',str(source/'workers/roslyn/FreeFlight.Roslyn.csproj'),'-c','Release','-p:RestoreLockedMode=true','--disable-build-servers','--artifacts-path',str(out/'worker-build')],'worker-build.log')
collectDll=out/'collector-build/bin/Collector/release/Collector.dll';worker=out/'worker-build/bin/FreeFlight.Roslyn/release/FreeFlight.Roslyn.dll'
f=dict(config['fixtures']['5845']);f['root']=str(Path(f['root']).resolve());target=str(Path(f['root'])/'source/P00/Nested/C0.cs')
results=[]
for session in range(2):
 directory=out/str(session);directory.mkdir();q=queue.Queue();log=(directory/'worker.stderr').open('w')
 p=subprocess.Popen([config['dotnet'],str(worker),'--trusted-msbuild','--incremental-validation','--background-recovery'],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=log,text=True)
 def read(process=p,replies=q):
  for line in process.stdout:replies.put(json.loads(line))
 threading.Thread(target=read,daemon=True).start();seq=0;collectorProcess=None
 def call(method,**params):
  global seq
  seq+=1;p.stdin.write(json.dumps(dict(id=seq,method=method,params=params))+'\n');p.stdin.flush();r=q.get(timeout=60);assert r['id']==seq and 'result' in r,r;return r['result']
 try:
  assert call('open',root=f['root'],project=f['project'])['files']==5845
  warm=time.monotonic()
  while time.monotonic()-warm<8:
   r=call('symbols',file=target);assert {x['name'] for x in r}=={'P00','C0','Value'}
  collectorLog=(directory/'collector.stderr').open('w')
  collectorProcess=subprocess.Popen([config['dotnet'],str(collectDll),'collect',str(p.pid),str(directory/'idle.nettrace')],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=collectorLog,text=True)
  ready=queue.Queue();threading.Thread(target=lambda:ready.put(collectorProcess.stdout.readline()),daemon=True).start();assert ready.get(timeout=30).strip()=='READY'
  time.sleep(12)
  collectorProcess.stdin.write('stop\n');collectorProcess.stdin.flush();collectorProcess.wait(timeout=40);assert collectorProcess.returncode==0;collectorLog.close()
 finally:
  if collectorProcess and collectorProcess.poll() is None:collectorProcess.kill();collectorProcess.wait()
  p.stdin.close()
  try:p.wait(timeout=15)
  except subprocess.TimeoutExpired:p.kill();p.wait();raise
  log.close()
 assert p.returncode==0
 command([config['dotnet'],str(collectDll),'analyze',str(directory/'idle.nettrace'),str(directory/'events.json')],str(session)+'-analysis.log')
 data=json.loads((directory/'events.json').read_text());assert data['eventsLost']==0
 sweeps=[];begin=None
 for event in data['events']:
  if event['kind']!='marker':continue
  if event['name']=='Begin':begin=event['ms']
  elif event['name']=='Success' and begin is not None:
   assert event['payload']['files']==5845 and event['payload']['bytes']==23941120,event
   samples=[e for e in data['events'] if e['kind']=='allocation' and begin<=e['ms']<=event['ms']]
   assert samples and any(e['frames'] for e in samples)
   sweeps.append(dict(beginMs=begin,endMs=event['ms'],actual=event['payload'],samples=samples));begin=None
 assert len(sweeps)>=2,('No two verified completed sweeps',data['events'][:3])
 results.append(dict(session=session,sweeps=sweeps));save(out/'observations.json',results);print('Allocation trace',session,'verified sweeps',len(sweeps),flush=True)
groups={}
for session in results:
 for sweep in session['sweeps']:
  for event in sweep['samples']:
   key=(event['type'],tuple(event['frames']));row=groups.setdefault(key,dict(type=event['type'],frames=event['frames'],sampledBytes=0,samples=0));row['sampledBytes']+=event['bytes'];row['samples']+=1
save(out/'result.json',dict(status='passed',scope='Sampled allocation stacks in marked successful idle sweeps; not exact per-stack counts or ordinary latency.',sourceHashes=config['variants']['candidate']['sourceHashes'],sessions=results,groups=sorted(groups.values(),key=lambda r:r['sampledBytes'],reverse=True)))
shutil.copy2(__file__,out/'adapter-source.py')
# Exclusive stack categories are sampled attribution, not exact object sizes.
categories={}
patterns=[('Compiler path/attribute validation','SourceEngine.CheckCompilerInput'),('MemoryStream growth','MemoryStream.set_Capacity'),('Darwin handle opening','DarwinSourceHandle.Open'),('Staged dictionaries','Dictionary`2'),('Hashing','Cryptography')]
for row in groups.values():
    frames='\n'.join(row['frames'])
    category=next((name for name,pattern in patterns if pattern in frames),'Other')
    current=categories.setdefault(category,dict(sampledBytes=0,samples=0))
    current['sampledBytes']+=row['sampledBytes'];current['samples']+=row['samples']
total=sum(row['sampledBytes'] for row in categories.values())
save(out/'allocation-categories.json',dict(sampledBytes=total,categories=[dict(category=name,percent=row['sampledBytes']/total*100,**row) for name,row in sorted(categories.items(),key=lambda item:item[1]['sampledBytes'],reverse=True)]))
