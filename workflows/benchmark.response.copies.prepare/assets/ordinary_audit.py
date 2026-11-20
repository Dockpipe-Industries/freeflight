# SPDX-License-Identifier: Apache-2.0
"""Replay the predefined ordinary matched comparison; never select favorable cells."""
import collections,hashlib,json,os,statistics,sys
from pathlib import Path
repo=Path.cwd();sys.path.insert(0,str(repo/'workflows/benchmark.trusted/assets'));from run import stats
receipt=repo/'bin/.local/benchmarks/response-copies/json-moves-v2'
out=receipt/os.environ['FREEFLIGHT_ORDINARY_LABEL']
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
m=json.loads((out/'run-manifest.json').read_text());c=json.loads((out/'collection.json').read_text());rows=json.loads((out/'samples.json').read_text())
assert c['status']=='passed' and len(rows)==c['processes']==16
assert sha(receipt/'manifest.json')==m['preparedManifestSha256']
assert sha(Path(m['workerCommand'][1]))==m['workerSha256']
for e in m['cores'].values():assert sha(Path(e['path']))==e['sha256']
for name,h in m['driverHashes'].items():assert sha(out/name)==h
assert sha(out/'ordinary_audit.py')==sha(Path(__file__))
for name,h in m['fixture']['hashes'].items():assert sha(Path(m['fixture']['root'])/name)==h
assert len({r['index'] for r in rows})==16
assert {r['configurationSha256'] for r in rows}=={c['configurationSha256']}
measured=[];warmups=0
for row,plan in zip(rows,m['plan']):
 assert all(row[k]==v for k,v in plan.items())
 if row['cohort']=='sham':assert row['actualCore']=='baseline'
 else:assert row['actualCore']==row['variant']
 directory=out/f"{row['index']}-{row['cohort']}-{row['variant']}"
 assert sha(directory/'freeflight.json')==c['configurationSha256']
 assert row['initialOracleChecks']==4
 a=row['samples'];assert len({s['id'] for s in a})==len(a)
 assert len({(s['phase'],s['round'],s['ordinal']) for s in a})==len(a)
 previous=None
 for x in a:
  assert x['phase'] in ['warmup','measured'] and x['verificationMs']>=0 and x['gapMs']>=0
  assert abs(x['ms']-(x['clientReturnNs']-x['requestStartNs'])/1e6)<1e-9
  if previous is not None:
   assert x['id']==previous['id']+1 and x['previousMethod']==previous['method']
   assert abs(x['gapMs']-(x['requestStartNs']-previous['clientReturnNs'])/1e6)<1e-9
   assert x['gapMs']+1e-6>=previous['verificationMs']
  previous=x
  if x['phase']=='measured':measured.append(dict(process=row['index'],cohort=row['cohort'],variant=row['variant'],pair=row['pair'],**x))
  else:warmups+=1
 q=[x for x in a if x['phase']=='measured'];assert len(q)==192
 assert {x['round'] for x in q}==set(range(48))
 counts=collections.Counter((x['method'],x['ordinal']) for x in q)
 assert len(counts)==16 and set(counts.values())=={12}
 predecessors=collections.Counter()
 for phase in ['warmup','measured']:
  samples=[x for x in a if x['phase']==phase];rounds=[x for x in row['rounds'] if x['phase']==phase]
  assert [x['round'] for x in rounds]==list(range(len(rounds))) and len(samples)==4*len(rounds)
  for rd in rounds:
   ordered=[x for x in samples if x['round']==rd['round']]
   assert [x['ordinal'] for x in ordered]==list(range(4))
   assert [x['method'] for x in ordered]==[m['methods'][(i+rd['round'])%4] for i in m['design']]
   assert all(rd[k]>=0 for k in ['activeMs','requestedSleepMs','actualSleepMs'])
   assert abs(rd['requestedSleepMs']-max(0,100-rd['activeMs']))<1e-6
   if phase=='measured':predecessors.update((x['method'],y['method']) for x,y in zip(ordered,ordered[1:]))
 assert len(predecessors)==12 and set(predecessors.values())=={12}
assert len(measured)==c['measuredChecks']==m['expectedMeasuredChecks']==3072
assert warmups==c['warmupChecks'] and c['initialOracleChecks']==64
metrics=['ms','gapMs','verificationMs']
def summarize(a):return {k:stats([x[k] for x in a]) for k in metrics}
def contrast(cohort,method,ordinal=None):
 a=[x for x in measured if x['cohort']==cohort and x['method']==method and (ordinal is None or x['ordinal']==ordinal)]
 sessions={v:[dict(process=r['index'],pair=r['pair'],metrics=summarize([x for x in a if x['process']==r['index']])) for r in rows if r['cohort']==cohort and r['variant']==v] for v in ['baseline','candidate']}
 assert all(len(s)==4 for s in sessions.values())
 pairs=[]
 for pair in range(4):
  b=next(s for s in sessions['baseline'] if s['pair']==pair);d=next(s for s in sessions['candidate'] if s['pair']==pair)
  pairs.append(dict(pair=pair,baselineProcess=b['process'],candidateProcess=d['process'],ratios={k:{s:d['metrics'][k][s]/b['metrics'][k][s] for s in ['median','p90','mean']} for k in metrics}))
 ratios={k:{s:statistics.median(x['metrics'][k][s] for x in sessions['candidate'])/statistics.median(x['metrics'][k][s] for x in sessions['baseline']) for s in ['median','p90','mean']} for k in metrics}
 direction={s:dict(lower=sum(p['ratios']['ms'][s]<1 for p in pairs),equal=sum(p['ratios']['ms'][s]==1 for p in pairs),higher=sum(p['ratios']['ms'][s]>1 for p in pairs),minimum=min(p['ratios']['ms'][s] for p in pairs),maximum=max(p['ratios']['ms'][s] for p in pairs)) for s in ['median','p90','mean']}
 return dict(cohort=cohort,method=method,ordinal=ordinal,sessions=sessions,pairs=pairs,ratioOfSessionMetrics=ratios,medianPairedRatios={k:{s:statistics.median(p['ratios'][k][s] for p in pairs) for s in ['median','p90','mean']} for k in metrics},pairDirections=direction,pooled={v:summarize([x for x in a if x['variant']==v]) for v in sessions})
contrasts=[contrast(c,method) for c in ['sham','source'] for method in m['methods']]
positions=[contrast(c,method,i) for c in ['sham','source'] for method in m['methods'] for i in range(4)]
result=dict(status='passed',processes=16,measuredChecks=3072,warmupChecks=warmups,initialOracleChecks=64,contrasts=contrasts,positions=positions,rawSha256=sha(out/'samples.json'),scope='Audit correctness and plan conformance only. All four chronological pairs and all four positions retained for each cohort/method; distinct aggregate estimands, actual gaps and verification costs are descriptive. No gap normalization, exclusions, performance acceptance threshold, causal attribution or overall win.')
for name,value in [('result.json',(json.dumps(result,indent=2)+'\n').encode()),('audit-adapter.py',Path(__file__).read_bytes())]:
 p=out/name
 if p.exists():assert p.read_bytes()==value,'Refuse to replace different derived data'
 else:p.write_bytes(value)
print('Ordinary audit passed: 16 processes, 3072 measured checks, all pairs/positions/predecessors and actual gaps.')
for x in contrasts:print(x['cohort'],x['method'],'session median/p90',*[round(x['ratioOfSessionMetrics']['ms'][s],3) for s in ['median','p90']],'paired directions',x['pairDirections']['median'])
