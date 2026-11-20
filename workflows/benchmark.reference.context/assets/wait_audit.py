# SPDX-License-Identifier: Apache-2.0
"""Audit all fixed-cycle slots, overruns and matched wait-placement contrasts."""
import hashlib,json,os,statistics,sys
from pathlib import Path
repo=Path.cwd();sys.path.insert(0,str(repo/'workflows/benchmark.trusted/assets'));from run import stats
out=repo/'bin/.local/benchmarks/reference-context'/os.environ['FREEFLIGHT_REFERENCE_WAIT_LABEL']
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
m=json.loads((out/'run-manifest.json').read_text());c=json.loads((out/'collection.json').read_text());rows=json.loads((out/'samples.json').read_text())
assert c['status']=='passed' and len(rows)==c['processes']==4
assert sha(Path(m['core']['path']))==m['core']['sha256'] and sha(Path(m['workerCommand'][1]))==m['workerSha256']
assert sha(repo/'bin/.local/benchmarks/response-copies/json-moves-v2/manifest.json')==m['preparedManifestSha256']
source=repo/'bin/.local/benchmarks/reference-context/baseline-position-v1'
for name,h in m['sourceReceiptHashes'].items():assert sha(source/name)==h
assert sha(out/'causal-review.json')==m['sourceReceiptHashes']['causal-review.json']
assert sha(out/'oracle.json')==sha(Path(m['oracleSource']))==m['oracleSha256']
for name,h in m['driverHashes'].items():assert sha(out/name)==h
assert sha(out/'audit.py')==sha(Path(__file__))
for name,h in m['fixture']['hashes'].items():assert sha(Path(m['fixture']['root'])/name)==h
measured=[];overruns=[];cycles=[]
for row,plan in zip(rows,m['plan']):
 session=row['session'];assert session==plan['session'] and row['initialOracleChecks']==4
 assert sha(out/str(session)/'freeflight.json')==row['configurationSha256']==c['configurationSha256']
 a=row['samples'];assert len(a)==736 and len({x['id'] for x in a})==736
 assert {x['tick'] for x in a}==set(range(184))
 assert {phase:sum(x['phase']==phase for x in a) for phase in ['measured','acclimation','warmup']}=={'measured':512,'acclimation':128,'warmup':96}
 assert sum(b['arm']=='immediate' for b in plan['blocks'])==4
 for b in range(0,8,2):assert plan['blocks'][b]['arm']!=plan['blocks'][b+1]['arm']
 previous=None
 for x in a:
  assert x['anchorNs']==row['originNs']+x['tick']*250_000_000
  assert abs(x['ms']-(x['clientReturnNs']-x['requestStartNs'])/1e6)<1e-9
  assert abs(x['actualWaitMs']-(x['requestStartNs']-x['readyNs'])/1e6)<1e-9
  assert abs(x['wakeLatenessMs']-(x['requestStartNs']-x['targetStartNs'])/1e6)<1e-9
  assert abs(x['requestedSleepMs']-max(0,(x['targetStartNs']-x['readyNs'])/1e6))<1e-6
  assert x['verificationMs']>=0 and x['gapMs']>=0
  if previous is not None:
   assert x['id']==previous['id']+1 and x['previousMethod']==previous['method']
   assert abs(x['gapMs']-(x['requestStartNs']-previous['clientReturnNs'])/1e6)<1e-9
   assert (x['readyNs']-previous['clientReturnNs'])/1e6+1e-6>=previous['verificationMs']
  if x['method']=='references':
   assert not x['fixedSlot'] and x['previousMethod']=='symbols'
   if x['arm']=='immediate':assert x['targetStartNs']==x['readyNs'] and x['requestedSleepMs']==0
   else:assert x['targetStartNs']==previous['clientReturnNs']+25_000_000 and x['gapMs']>=25-1e-6
  else:
   assert x['fixedSlot'] and x['targetStartNs']==x['anchorNs']+m['fixedSlotsMs'][x['method']]*1_000_000
  expected=max(0,(x['readyNs']-x['targetStartNs'])/1e6) if x['fixedSlot'] else 0
  assert abs(x['fixedSlotOverrunMs']-expected)<1e-9
  if expected>0:overruns.append(dict(session=session,**x))
  x=dict(x,startOffsetMs=(x['requestStartNs']-x['anchorNs'])/1e6)
  if x['phase']=='measured':measured.append(dict(session=session,**x))
  previous=x
 for tick in range(184):
  xs=[x for x in a if x['tick']==tick];assert [x['ordinal'] for x in xs]==list(range(4)) and [x['method'] for x in xs]==[m['methods'][i] for i in m['order']]
  phase='warmup' if tick<24 else ('acclimation' if (tick-24)%20<4 else 'measured')
  block=-1 if tick<24 else (tick-24)//20;number=tick if tick<24 else ((tick-24)%20 if phase=='acclimation' else (tick-24)%20-4)
  arm='immediate' if tick<24 else plan['blocks'][block]['arm']
  assert all(x['phase']==phase and x['block']==block and x['cycle']==number and x['arm']==arm for x in xs)
  nxt=next((x for x in a if x['tick']==tick+1 and x['ordinal']==0),None)
  cycles.append(dict(session=session,tick=tick,phase=phase,block=block,arm=arm,actualSymbolStartPeriodMs=(nxt['requestStartNs']-xs[0]['requestStartNs'])/1e6 if nxt else None))
assert len(measured)==m['expectedMeasuredChecks']==c['measuredChecks']==2048
assert c['acclimationChecks']==m['expectedAcclimationChecks']==512 and c['warmupChecks']==m['expectedWarmupChecks']==384 and c['initialOracleChecks']==16
assert len(overruns)==c['fixedSlotReadinessOverruns']
keys=['ms','gapMs','verificationMs','startOffsetMs','wakeLatenessMs']
def summarize(a):return {k:stats([x[k] for x in a]) for k in keys}
operations=[]
for method in m['methods']:
 sessions=[]
 for session in range(4):
  a=[x for x in measured if x['session']==session and x['method']==method]
  arms={arm:summarize([x for x in a if x['arm']==arm]) for arm in ['immediate','wait-before']}
  pairs=[]
  for pair in range(4):
   bs={b:summarize([x for x in a if x['block']==b]) for b in [pair*2,pair*2+1]};ids={m['plan'][session]['blocks'][b]['arm']:b for b in bs}
   pairs.append(dict(pair=pair,blocks=bs,armBlocks=ids,waitImmediateRatios={s:bs[ids['wait-before']]['ms'][s]/bs[ids['immediate']]['ms'][s] for s in ['median','p90','mean']}))
  sessions.append(dict(session=session,arms=arms,waitImmediateRatios={s:arms['wait-before']['ms'][s]/arms['immediate']['ms'][s] for s in ['median','p90','mean']},blockPairs=pairs))
 operations.append(dict(method=method,sessions=sessions,ratioOfSessionMetrics={s:statistics.median(x['arms']['wait-before']['ms'][s] for x in sessions)/statistics.median(x['arms']['immediate']['ms'][s] for x in sessions) for s in ['median','p90','mean']},medianPairedSessionRatios={s:statistics.median(x['waitImmediateRatios'][s] for x in sessions) for s in ['median','p90','mean']},pooled={arm:summarize([x for x in measured if x['method']==method and x['arm']==arm]) for arm in ['immediate','wait-before']}))
result=dict(status='passed',processes=4,measuredChecks=2048,acclimationChecks=512,warmupChecks=384,initialOracleChecks=16,fixedSlotReadinessOverruns=len(overruns),overruns=overruns,matchedCadenceInterpretation='inconclusive: fixed-slot overrun' if overruns else 'No fixed-slot readiness overruns; intended cadence preserved; actual wake jitter and periods retained for assessment.',operations=operations,cycles=cycles,rawSha256=sha(out/'samples.json'),scope='Correctness/plan audit only. One baseline order, fixed intended cycle/other operation starts, wait relocated around references. All phases/session/block pairs/actual lateness retained. No CPU/GC/cache/hardware attribution, performance exclusion or acceptance claim.')
for name,value in [('result.json',(json.dumps(result,indent=2)+'\n').encode()),('audit-adapter.py',Path(__file__).read_bytes())]:
 p=out/name
 if p.exists():assert p.read_bytes()==value,'Refuse different derived data'
 else:p.write_bytes(value)
print('Fixed-cycle audit passed:2048measured+512acclimation+384warmup+16oracles; deadline overruns',len(overruns))
for x in operations:print(x['method'],'wait/immediate median',round(x['ratioOfSessionMetrics']['median'],3),'sessions',[round(s['waitImmediateRatios']['median'],3) for s in x['sessions']])
