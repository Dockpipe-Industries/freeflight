# SPDX-License-Identifier: Apache-2.0
"""Finite external whole-block qualification, distinct from failed short brackets."""
import hashlib,json,os,platform,shutil,statistics,subprocess,sys,time,urllib.request
from pathlib import Path
from reader import Reader,delta,wait
repo=Path.cwd();assets=Path(__file__).parent;out=repo/'bin/.local/benchmarks/reference-context/aggregate-work-calibration-v3';out.mkdir(exist_ok=False)
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def save(n,v):(out/n).write_text(json.dumps(v,indent=2)+'\n')
def command(args,name):
 with (out/name).open('w') as f:subprocess.run(args,stdout=f,stderr=subprocess.STDOUT,check=True)
for p in assets.iterdir():
 if p.is_file():shutil.copy2(p,out/p.name)
plan=dict(date='2026-10-23',clock='Parent clock_gettime_ns(CLOCK_MONOTONIC), native clock_gettime(CLOCK_MONOTONIC); verified native call enclosed by parent samples',previousSetupFailure='v1 clock domains differ; v2 CPU windows differ. Both invalid setups retained; no scaling data qualified',completePathWarmupWindows=[1000000,2000000],cpuUnitCheck='Separate cumulative child CPU value enclosed by ordered external CPU snapshots; tolerance max2ms or5% of child total; bracket CPU width <=same tolerance',question='External whole-process work over four-second paced blocks, not stage work.',children=2,warmupJoinedCalls=1000,cycles=16,cycleNs=250000000,iterationsA=1000000,iterationsB=2000000,arms=['A','B','B','A','Z']*3+['Z'],ratioBand=[1.9,2.1],incrementTolerance=.05,expectedLoopInstructionsPerIteration=5,CPUCheckRelative=.05,CPUCheckAbsoluteNs=2000000,uncertainty='maximum zero-work instructions plus maximum within-child same-factor range; must be <1% of each eventual target process block count',failure='No unchanged retry, gate relaxation, outlier exclusion or target run after failure',targetBoundary='first measured anchor-20ms to same anchor+4s-20ms; ordered core then worker reads, all verification complete, no query crosses either boundary',targetSimilarity='Every paired uncertainty-expanded ratio within [0.95,1.05] per process or unresolved',sourceRevision='f6217f891ac0bb64f3d375211650a4c1ff8ca1ea',os=platform.platform(),assetHashes={p.name:sha(p) for p in assets.iterdir() if p.is_file()})
save('plan.json',plan)
# Pin complete primary-source evidence; raw counters are Mach times, not nanoseconds.
for name in ['osfmk/kern/task.c','osfmk/kern/bsd_kern.c','doc/observability/recount.md']:
 data=urllib.request.urlopen('https://raw.githubusercontent.com/apple-oss-distributions/xnu/'+plan['sourceRevision']+'/'+name).read();(out/Path(name).name).write_bytes(data)
lib=out/'libaggregate.dylib';command(['c++','-std=c++23','-O2','-dynamiclib',str(out/'counter.cpp'),'-install_name',str(lib),'-o',str(lib)],'native-build.log')
command(['otool','-tvV',str(lib)],'disassembly.txt')
# Read and freeze loop disassembly before collection; expected arm64 loop: three eor, subs, b.ne.
assembly=(out/'disassembly.txt').read_text().split('_ff_loop:')[1];loop=assembly.split('ret')[0];assert loop.count('eor')==3 and 'subs' in loop and 'b.ne' in loop
prepared=json.loads((repo/'bin/.local/benchmarks/response-copies/json-moves-v2/manifest.json').read_text());dotnet=prepared['dotnet']
child=out/'child';child.mkdir();(child/'Program.cs').write_text((out/'Child.cs').read_text().replace('LIBRARY',str(lib)));(child/'Child.csproj').write_text('<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup><OutputType>Exe</OutputType><TargetFramework>net11.0</TargetFramework><ImplicitUsings>enable</ImplicitUsings><Nullable>enable</Nullable></PropertyGroup></Project>')
command([dotnet,'build',str(child/'Child.csproj'),'-c','Release','--nologo'],'managed-build.log')
reader=Reader(lib);rows=[]
def expected(n):
 def f(n,x):
  for i in range(n):x^=(x<<13)&((1<<64)-1);x^=x>>7;x^=(x<<17)&((1<<64)-1)
  return x
 return f(n//2,3)^f(n//2,7)
checksums={n:expected(n) for n in [0,1000000,2000000]}
save('provenance.json',dict(helperSha256=sha(lib),childSha256=sha(child/'bin/Release/net11.0/Child.dll'),dotnet=dotnet,dotnetSha256=sha(Path(dotnet)),disassemblySha256=sha(out/'disassembly.txt'),sourceHashes={n:sha(out/n) for n in ['task.c','bsd_kern.c','recount.md']},checksums=checksums))
try:
 for session in range(2):
  p=subprocess.Popen([dotnet,str(child/'bin/Release/net11.0/Child.dll')],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=(out/f'{session}.stderr.log').open('w'),text=True)
  try:
   warm=[]
   while True:
    line=p.stdout.readline().strip();assert line
    if line=='READY':break
    warm.append(json.loads(line))
   save(f'{session}-warmup.json',warm)
   warmWindows=[]
   for n in plan['completePathWarmupWindows']:
    anchor=time.clock_gettime_ns(time.CLOCK_MONOTONIC)+150000000;p.stdin.write(json.dumps(dict(n=n,start=anchor))+'\n');p.stdin.flush();assert p.stdout.readline().strip()=='ARMED';warmWindows.append(json.loads(p.stdout.readline()));wait(anchor+4000000000)
   save(f'{session}-complete-path-warmup.json',warmWindows)
   for i in range(10):p.stdin.write('CPU\n');p.stdin.flush();int(p.stdout.readline())
   def cpuCheck(label):
    left=reader.read(p.pid);p.stdin.write('CPU\n');p.stdin.flush();own=int(p.stdout.readline());right=reader.read(p.pid)
    total=lambda v:(v['userMach']+v['systemMach'])*v['numer']//v['denom']
    lo,hi=total(left),total(right);tol=max(2000000,own*.05)
    proof=dict(left=left,right=right,own=own,lo=lo,hi=hi,tolerance=tol);save(f'{session}-cpu-{label}.json',proof)
    assert lo-tol<=own<=hi+tol and 0<=hi-lo<=tol
   cpuCheck('before')
   for block,arm in enumerate(plan['arms']):
    n={'A':1000000,'B':2000000,'Z':0}[arm];anchor=time.clock_gettime_ns(time.CLOCK_MONOTONIC)+150000000;p.stdin.write(json.dumps(dict(n=n,start=anchor))+'\n');p.stdin.flush();assert p.stdout.readline().strip()=='ARMED'
    wait(anchor-20000000);before=reader.pair([p.pid]);done=json.loads(p.stdout.readline());wait(anchor+4000000000-20000000);after=reader.pair([p.pid]);v=delta(before[0],after[0]);row=dict(session=session,block=block,arm=arm,anchor=anchor,before=before,after=after,done=done,delta=v);rows.append(row)
    with (out/'raw.jsonl').open('a') as f:f.write(json.dumps(row)+'\n')
    assert before[0]['end']<anchor and done['cycles'][-1]['end']<after[0]['begin'] and after[0]['end']<anchor+4000000000
    assert len(done['cycles'])==16 and all(c['result']==checksums[n] and c['target']<=c['begin']<c['target']+50000000 and c['end']<c['target']+230000000 for c in done['cycles'])
    print('aggregate calibration',session,block,arm,v['instructions'],flush=True)
   cpuCheck('after')
  finally:
   p.stdin.close();p.wait(timeout=20);assert p.returncode==0
 ratios=[]
 for session in range(2):
  cell=[x for x in rows if x['session']==session]
  for group in range(3):
   for ia,ib in [(group*5,group*5+1),(group*5+3,group*5+2)]:
    a=cell[ia]['delta']['instructions'];b=cell[ib]['delta']['instructions'];ratios.append(dict(session=session,a=ia,b=ib,ratio=b/a,increment=b-a,expectedIncrement=80000000))
 zeros=[x['delta']['instructions'] for x in rows if x['arm']=='Z'];ranges=[max(v)-min(v) for s in range(2) for arm in ['A','B'] for v in [[x['delta']['instructions'] for x in rows if x['session']==s and x['arm']==arm]]]
 valid=all(1.9<=x['ratio']<=2.1 and abs(x['increment']-80000000)<=4000000 for x in ratios)
 save('result.json',dict(status='passed' if valid else 'failed',ratios=ratios,zeroWorkInstructions=zeros,repeatRanges=ranges,empiricalUncertainty=max(zeros)+max(ranges),rawSha256=sha(out/'raw.jsonl'),newFreeFlightQueries=0,scope=plan['question']))
 assert valid,'External aggregate calibration failed; stop before target collection'
except Exception as e:
 save('decision.json',dict(status='stopped',error=repr(e),rawRecords=len(rows),newFreeFlightQueries=0,FreeFlightProbeBuilt=False));raise
print('Aggregate external calibration passed; target precision remains conditional on count size',flush=True)
