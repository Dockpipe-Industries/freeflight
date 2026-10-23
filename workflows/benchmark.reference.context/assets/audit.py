# SPDX-License-Identifier: Apache-2.0
"""Independent complete-order checks and descriptive matched context summaries."""
import collections,hashlib,itertools,json,os,statistics,sys
from pathlib import Path
repo=Path.cwd();sys.path.insert(0,str(repo/'workflows/benchmark.trusted/assets'));from run import stats
out=repo/'bin/.local/benchmarks/reference-context'/os.environ['FREEFLIGHT_REFERENCE_CONTEXT_LABEL']
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
m=json.loads((out/'run-manifest.json').read_text());c=json.loads((out/'collection.json').read_text());rows=json.loads((out/'samples.json').read_text())
assert c['status']=='passed' and c['processes']==len(rows)==4
assert sha(Path(m['core']['path']))==m['core']['sha256'] and sha(Path(m['workerCommand'][1]))==m['workerSha256']
assert sha(repo/'bin/.local/benchmarks/response-copies/json-moves-v2/manifest.json')==m['preparedManifestSha256']
assert sha(out/'oracle.json')==sha(Path(m['oracleSource']))==m['oracleSha256']
assert sha(out/'design-review.json')==m['designReviewSha256']
for name,h in m['driverHashes'].items():assert sha(out/name)==h
assert sha(out/'audit.py')==sha(Path(__file__))
for name,h in m['fixture']['hashes'].items():assert sha(Path(m['fixture']['root'])/name)==h
allMeasured=[];warmups=0;acclimation=0;periods=[]
for row,plan in zip(rows,m['plan']):
 session=row['session'];assert session==plan['session'] and session in range(4)
 assert row['initialOracleChecks']==4
 assert sha(out/str(session)/'freeflight.json')==row['configurationSha256']==c['configurationSha256']
 a=row['samples'];assert len({s['id'] for s in a})==len(a)
 assert len({(s['phase'],s['block'],s['round'],s['ordinal']) for s in a})==len(a)
 previous=None
 for x in a:
  assert x['phase'] in ['warmup','acclimation','measured'] and x['policy'] in ['round','gap-floor']
  assert x['verificationMs']>=0 and x['gapMs']>=0 and x['actualGapWaitMs']>=0 and x['requestedGapSleepMs']>=0
  assert abs(x['ms']-(x['clientReturnNs']-x['requestStartNs'])/1e6)<1e-9
  if previous is not None:
   assert x['id']==previous['id']+1 and x['previousMethod']==previous['method']
   assert abs(x['gapMs']-(x['requestStartNs']-previous['clientReturnNs'])/1e6)<1e-9
   assert x['gapMs']+1e-6>=previous['verificationMs']
   gapBeforeWait=x['gapMs']-x['actualGapWaitMs']
   expected=max(0,25-gapBeforeWait) if x['policy']=='gap-floor' else 0
   assert abs(expected-x['requestedGapSleepMs'])<1e-6
  if x['policy']=='gap-floor':assert x['gapMs']>=25-1e-6
  if x['policy']=='round':assert x['requestedGapSleepMs']==0
  previous=x
  if x['phase']=='measured':allMeasured.append(dict(session=session,**x))
  elif x['phase']=='acclimation':acclimation+=1
  else:warmups+=1
 rounds=row['rounds'];assert len(rounds)*4==len(a)
 assert len({(r['phase'],r['block'],r['round']) for r in rounds})==len(rounds)
 for i,r in enumerate(rounds):
  assert r['activeMs']>=0 and r['actualRoundSleepMs']>=0
  assert abs(r['requestedRoundSleepMs']-max(0,100-r['activeMs']))<1e-6
  assert abs(r['periodMs']-r['activeMs']-r['actualRoundSleepMs'])<1e-6 and r['periodMs']>=100-1e-6
  startToStart=(rounds[i+1]['roundStartNs']-r['roundStartNs'])/1e6 if i+1<len(rounds) else None
  if startToStart is not None:assert startToStart+1e-6>=r['periodMs']
  periods.append(dict(session=session,**r,nextRoundStartPeriodMs=startToStart))
  xs=[s for s in a if s['phase']==r['phase'] and s['block']==r['block'] and s['round']==r['round']]
  assert [s['ordinal'] for s in xs]==list(range(4)) and len({s['method'] for s in xs})==4
  assert {s['policy'] for s in xs}=={r['policy']}
  if r['phase']=='warmup':expected=[(v+r['round'])%4 for v in [0,1,3,2]];assert r['block']==-1
  else:
   b=plan['blocks'][r['block']];assert r['policy']==b['policy']
   expected=b['orders' if r['phase']=='measured' else 'acclimationOrders'][r['round']]
  assert [s['method'] for s in xs]==[m['methods'][j] for j in expected]
 assert sum(x['phase']=='measured' for x in a)==768 and sum(x['phase']=='acclimation' for x in a)==128
 warm=[r for r in rounds if r['phase']=='warmup'];assert [r['round'] for r in warm]==list(range(len(warm))) and sum(r['periodMs'] for r in warm)>=5000
 assert collections.Counter(b['policy'] for b in plan['blocks'])=={'round':4,'gap-floor':4}
 expectedFirst='round' if session in [0,3] else 'gap-floor'
 for b in plan['blocks']:
  block=b['block'];assert b['policy']==(expectedFirst if block in [0,3,4,7] else ('gap-floor' if expectedFirst=='round' else 'round'))
  assert {tuple(o) for o in b['orders']}==set(itertools.permutations(range(4))) and len(b['orders'])==24
  if block%2==0:assert b['orders']==plan['blocks'][block+1]['orders'] and b['policy']!=plan['blocks'][block+1]['policy']
  q=[x for x in a if x['phase']=='measured' and x['block']==block]
  assert len(q)==96 and collections.Counter((x['method'],x['ordinal']) for x in q)=={(method,i):6 for method in m['methods'] for i in range(4)}
  for method in m['methods']:
   for ordinal in [1,2,3]:assert collections.Counter(x['previousMethod'] for x in q if x['method']==method and x['ordinal']==ordinal)=={pred:2 for pred in m['methods'] if pred!=method}
assert len(allMeasured)==c['measuredChecks']==m['expectedMeasuredChecks']==3072
assert acclimation==c['acclimationChecks']==m['expectedAcclimationChecks']==512 and warmups==c['warmupChecks'] and c['initialOracleChecks']==16
metrics=['ms','gapMs','verificationMs']
def summarize(a):return {key:stats([x[key] for x in a]) for key in metrics}
def select(method,ordinal=None,pred=None):return [x for x in allMeasured if x['method']==method and (ordinal is None or x['ordinal']==ordinal) and (pred is None or x['previousMethod']==pred)]
def contrast(method,ordinal=None,pred=None):
 a=select(method,ordinal,pred);sessions=[]
 for session in range(4):
  xs=[x for x in a if x['session']==session]
  byPolicy={p:summarize([x for x in xs if x['policy']==p]) for p in ['round','gap-floor']}
  pairs=[]
  for pair in range(4):
   bs={b:summarize([x for x in xs if x['block']==b]) for b in [pair*2,pair*2+1]}
   ids={m['plan'][session]['blocks'][b]['policy']:b for b in bs}
   pairs.append(dict(pair=pair,blocks=bs,policyBlocks=ids,ratios={k:{s:bs[ids['gap-floor']][k][s]/bs[ids['round']][k][s] for s in ['median','p90','mean']} for k in metrics}))
  sessions.append(dict(session=session,policies=byPolicy,gapFloorRoundRatios={k:{s:byPolicy['gap-floor'][k][s]/byPolicy['round'][k][s] for s in ['median','p90','mean']} for k in metrics},blockPairs=pairs))
 ratios={k:{s:statistics.median(x['policies']['gap-floor'][k][s] for x in sessions)/statistics.median(x['policies']['round'][k][s] for x in sessions) for s in ['median','p90','mean']} for k in metrics}
 return dict(method=method,ordinal=ordinal,predecessor=pred,sessions=sessions,ratioOfSessionMetrics=ratios,medianPairedSessionRatios={k:{s:statistics.median(x['gapFloorRoundRatios'][k][s] for x in sessions) for s in ['median','p90','mean']} for k in metrics},directions={s:dict(lower=sum(x['gapFloorRoundRatios']['ms'][s]<1 for x in sessions),higher=sum(x['gapFloorRoundRatios']['ms'][s]>1 for x in sessions)) for s in ['median','p90','mean']},pooled={p:summarize([x for x in a if x['policy']==p]) for p in ['round','gap-floor']})
operations=[contrast(method) for method in m['methods']]
positions=[contrast('references',i) for i in range(4)]
cells=[contrast('references',i,pred) for i in [1,2,3] for pred in m['methods'] if pred!='references']
# Position0 is deliberately only descriptive cross-round history: no matched predecessor ratios.
carryover=[dict(session=session,policy=policy,previousMethod=pred,metrics=summarize(a)) for session in range(4) for policy in ['round','gap-floor'] for pred in m['methods'] if (a:=[x for x in allMeasured if x['session']==session and x['policy']==policy and x['method']=='references' and x['ordinal']==0 and x['previousMethod']==pred])]
# Every position/predecessor contrast within a policy/session; no cherry-picked comparison.
referenceContext=[]
for session in range(4):
 for policy in ['round','gap-floor']:
  xs=[x for x in allMeasured if x['session']==session and x['policy']==policy and x['method']=='references']
  strata={i:summarize([x for x in xs if x['ordinal']==i]) for i in range(4)}
  preds={i:{pred:summarize([x for x in xs if x['ordinal']==i and x['previousMethod']==pred]) for pred in m['methods'] if pred!='references'} for i in [1,2,3]}
  referenceContext.append(dict(session=session,policy=policy,positionMetrics=strata,withinRoundPredecessorMetrics=preds,positionPairs=[dict(numerator=i,denominator=j,medianRatio=strata[i]['ms']['median']/strata[j]['ms']['median']) for i in range(4) for j in range(i)],predecessorPairs=[dict(ordinal=i,numerator=p,denominator=q,medianRatio=preds[i][p]['ms']['median']/preds[i][q]['ms']['median']) for i in [1,2,3] for pi,p in enumerate(preds[i]) for qi,q in enumerate(preds[i]) if pi>qi]))
result=dict(status='passed',processes=4,measuredChecks=3072,acclimationChecks=512,warmupChecks=warmups,initialOracleChecks=16,operations=operations,referencePositions=positions,referenceCells=cells,referenceWithinPolicyContexts=referenceContext,positionZeroCrossRoundHistory=carryover,rounds=periods,rawSha256=sha(out/'samples.json'),scope='Correctness/plan audit only. Full factorial order blocks; all sessions, block pairs, positions, predecessors and actual pacing retained. Marginal history associations, pacing/rate confounding and sparse cell p90 limits; no hardware mechanism, exclusions or performance acceptance claim.')
for name,value in [('result.json',(json.dumps(result,indent=2)+'\n').encode()),('audit-adapter.py',Path(__file__).read_bytes())]:
 p=out/name
 if p.exists():assert p.read_bytes()==value,'Refuse different derived data'
 else:p.write_bytes(value)
print('Baseline context audit passed: 4processes,3072 measured+512acclimation; complete orders, matched block pairs, actual gaps and all session/position/predecessor cells.')
for x in operations:print(x['method'],'gap-floor/round session medians',round(x['ratioOfSessionMetrics']['ms']['median'],3),'all sessions',[round(s['gapFloorRoundRatios']['ms']['median'],3) for s in x['sessions']])
