# SPDX-License-Identifier: Apache-2.0
"""Validate the predetermined crossover and summarize per-process paired effects."""
import collections,hashlib,json,os,statistics,sys
from pathlib import Path
repo=Path.cwd();sys.path.insert(0,str(repo/'workflows/benchmark.trusted/assets'));from run import stats
out=repo/'bin/.local/benchmarks/response-copies/json-moves-v2'/os.environ['FREEFLIGHT_CONTEXT_LABEL'];m=json.loads((out/'run-manifest.json').read_text());r=json.loads((out/'collection.json').read_text());rows=json.loads((out/'samples.json').read_text())
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert r['status']=='passed' and len(rows)==len(m['plan'])
assert m['cpuObserver']['status']=='passed'
assert sha(out/'cpu-worker-source/workers/roslyn/Program.cs')==m['cpuObserver']['programSha256']
assert sha(out/'context.py')==m['adapterSha256']
for name,h in m['sourceReceiptHashes'].items():assert sha(Path(name))==h
assert sha(Path(m['workerCommand'][1]))==m['workerSha256']
for v,e in m['cores'].items():assert sha(Path(e['path']))==e['sha256']
assert {x['startupConfigSha256'] for x in rows}=={r['configurationSha256']}
measured=[];fresh=collections.defaultdict(collections.Counter)
for row,p in zip(rows,m['plan']):
 assert all(row[k]==p[k] for k in ['index','cohort']) and row['variant']==p['label'] and row['actualCore']==p['actualCore']
 if row['cohort']=='sham':assert row['actualCore']=='baseline'
 assert len({s['id'] for s in row['samples']})==len(row['samples'])
 assert sum(x['phase']=='measured' for x in row['samples'])==128
 assert sum(x['phase']=='acclimation' for x in row['samples'])==128
 previous=None
 for x in row['samples']:
  if previous is not None:assert abs(x['gapMs']-(x['requestStartNs']-previous['clientReturnNs'])/1e6)<1e-9
  previous=x
  assert abs(x['client']['totalMs']-(x['clientReturnNs']-x['requestStartNs'])/1e6)<1e-9
  assert str(x['core']['id'])==str(x['id']) and str(x['worker']['id'])==str(x['core']['workerIds'][0])
  assert x['worker']['method']==x['method'] and len(x['core']['workerIds'])==1
  assert abs(x['outsideInvokeMs']-(x['client']['totalMs']-x['worker']['stages']['invoke']))<1e-9
  c=x['worker']['counters'];assert c.get('readBytes',0)==4096*c.get('readFiles',0)
  if x['method']!='workspaceSymbols':assert c['readFiles']>=1
  if x['phase']=='measured':
   assert 4<=x['blockRound']<=7 and not x['blockBoundaryCarryover']
   assert x['policy']==(p['firstPolicy'] if x['block']%2==0 else ('equal-gap' if p['firstPolicy']=='round' else 'round'))
   if x['policy']=='equal-gap':assert x['gapMs']>=24.9
   measured.append(dict(process=row['index'],cohort=row['cohort'],variant=row['variant'],actualCore=row['actualCore'],**x))
   fresh[x['method']][(c.get('readFiles',0),c.get('readBytes',0),c.get('fullRecoveries',0))]+=1
 for policy in ['round','equal-gap']:
  a=[x for x in row['samples'] if x['phase']=='measured' and x['policy']==policy]
  counts=collections.Counter((x['method'],x['ordinal']) for x in a);assert len(counts)==16 and set(counts.values())=={4}
  pairs=collections.Counter()
  for b in range(8):
   for i in range(4,8):
    q=sorted((x for x in a if x['block']==b and x['blockRound']==i),key=lambda x:x['ordinal'])
    if q:pairs.update((x['method'],y['method']) for x,y in zip(q,q[1:]))
  assert len(pairs)==12 and set(pairs.values())=={4}
assert len(measured)==m['expectedMeasuredChecks']==r['measuredChecks']==128*len(rows)
assert sum(x['phase']=='acclimation' for row in rows for x in row['samples'])==m['expectedAcclimationChecks']==r['acclimationChecks']==128*len(rows)
keys=['worker.processCpuInvoke','client.totalMs','worker.invoke','worker.refresh','worker.pathCheck','worker.openHandle','worker.readHash','worker.findSymbol','worker.findReferences','worker.searchDeclarations','worker.queue','worker.gate','worker.serialize','worker.write','outsideInvokeMs','coreThreadCpu.coreTotal','core.workerResponseParse','core.responseConstruction','core.resultEnvelope','core.mcpSerialize','client.readerQueueMs','client.parseMs','client.gcPauseMs','client.gcCollections','gapMs','verificationMs']
def metric(x,k):
 if k in x:return x[k]
 group,name=k.split('.',1)
 if group=='worker':return x['worker']['stages'].get(name,0)
 if group=='core':return x['core']['stages'].get(name,0)
 if group=='coreThreadCpu':return x['core']['threadCpuStages'].get(name,0)
 return x[group][name]
def summarize(a):return {k:stats([metric(x,k) for x in a]) for k in keys}
contrasts=[];strata=[];paired=[]
for cohort in sorted({row['cohort'] for row in rows}):
 for policy in ['round','equal-gap']:
  for method in m['methods']:
   byVariant={v:[x for x in measured if x['cohort']==cohort and x['variant']==v and x['policy']==policy and x['method']==method] for v in ['baseline','candidate']}
   sessions={v:[dict(process=i,metrics=summarize([x for x in a if x['process']==i])) for i in sorted({x['process'] for x in a})] for v,a in byVariant.items()}
   ratios={k:statistics.median(s['metrics'][k]['median'] for s in sessions['candidate'])/statistics.median(s['metrics'][k]['median'] for s in sessions['baseline']) for k in keys if statistics.median(s['metrics'][k]['median'] for s in sessions['baseline'])>0}
   means={v:{k:statistics.mean(metric(x,k) for x in a) for k in ['client.totalMs','worker.invoke','worker.processCpuInvoke','outsideInvokeMs','coreThreadCpu.coreTotal','gapMs','verificationMs']} for v,a in byVariant.items()}
   for v in means:assert abs(means[v]['client.totalMs']-means[v]['worker.invoke']-means[v]['outsideInvokeMs'])<1e-9
   delta={k:means['candidate'][k]-means['baseline'][k] for k in means['baseline']}
   assert abs(delta['client.totalMs']-delta['worker.invoke']-delta['outsideInvokeMs'])<1e-9
   contrasts.append(dict(cohort=cohort,policy=policy,method=method,ratioOfSessionMedians=ratios,sessions=sessions,pooled={v:summarize(a) for v,a in byVariant.items()},meanWallDecomposition=dict(labels=means,candidateMinusBaseline=delta,scope='Exact descriptive mean identity total=invoke+outside; no subtraction of independent medians, no causal assignment.')))
   for ordinal in range(4):strata.append(dict(cohort=cohort,policy=policy,method=method,ordinal=ordinal,metrics={v:summarize([x for x in a if x['ordinal']==ordinal]) for v,a in byVariant.items()}))
for row in rows:
 for method in m['methods']:
  byPolicy={p:[x for x in measured if x['process']==row['index'] and x['method']==method and x['policy']==p] for p in ['round','equal-gap']}
  med={p:{k:statistics.median(metric(x,k) for x in a) for k in keys} for p,a in byPolicy.items()}
  paired.append(dict(process=row['index'],cohort=row['cohort'],variant=row['variant'],method=method,medians=med,equalGapRoundRatios={k:med['equal-gap'][k]/med['round'][k] for k in keys if med['round'][k]>0}))
result=dict(status='passed',processes=len(rows),measuredChecks=128*len(rows),acclimationChecks=128*len(rows),warmupChecks=r['warmupChecks'],initialOracleChecks=4*len(rows),contrasts=contrasts,positionStrata=strata,withinProcessPolicyPairs=paired,freshReadAccounting={k:[dict(files=a,bytes=b,foregroundRecoveries=c,count=n) for (a,b,c),n in v.items()] for k,v in fresh.items()},rawSha256=sha(out/'samples.json'),scope='Predeclared diagnostic crossover, not acceptance timing. Same-binary sham and source contrasts are distinct. Paired within-process policy effects retained; medians/nested scopes cannot be added or independently subtracted to reconstruct costs. No hardware power/frequency or scheduler cause measured. All raw acclimation/warmup/transition records retained; measured window fixed before execution.')
for name,value in [('result.json',(json.dumps(result,indent=2)+'\n').encode()),('audit-adapter.py',Path(__file__).read_bytes())]:
 p=out/name
 if p.exists():assert p.read_bytes()==value,'Refuse to replace different derived data'
 else:p.write_bytes(value)
print('CPU context audit passed:',len(rows),'processes;',len(measured),'measured responses; clock calibration, fresh reads, gap/ID/balance checks passed.')
for x in contrasts:print(x['cohort'],x['policy'],x['method'],{k:round(x['ratioOfSessionMedians'][k],3) for k in ['client.totalMs','worker.invoke','worker.processCpuInvoke','outsideInvokeMs','coreThreadCpu.coreTotal']})
