# SPDX-License-Identifier: Apache-2.0
"""Independent shape/accounting audit and per-session summaries; no new timings."""
import collections,hashlib,json,os,sys
from pathlib import Path
sys.path.insert(0,str(Path.cwd()/'workflows/benchmark.trusted/assets'))
from run import stats
repo=Path.cwd();out=repo/'bin/.local/benchmarks/definition-cost'/os.environ['FREEFLIGHT_DEFINITION_LABEL']
raw=out/'observations.json';records=json.loads(raw.read_text());manifest=json.loads((out/'run-manifest.json').read_text());result=json.loads((out/'result.json').read_text())
assert result['status']=='passed' and manifest['extended']
methods=manifest['methods'];intervals=manifest['intervals'];sessions=manifest['sessions']
assert len(records)==len(intervals)*sessions*2
assert len({(r['transport'],r['interval'],r['session']) for r in records})==len(records)
for filename in ['test_worker.py.log','test_trusted.py.log']:
 assert 'Unhandled exception' not in (out/filename).read_text()
assert '100% tests passed' in (out/'core-tests.log').read_text()
for name,digest in manifest['driverHashes'].items():
 p=(out/Path(name).name) if 'benchmark.definition.cost/assets' in name else out/'driver-source'/Path(name).name
 assert hashlib.sha256(p.read_bytes()).hexdigest()==digest,name
hashes=collections.defaultdict(set);counts=collections.defaultdict(collections.Counter)
for r in records:
 samples=r['samples'];assert len(samples)==160
 assert len({x['client']['id'] for x in samples})==160
 assert len({(x['measuredRound'],x['ordinal']) for x in samples})==160
 positions=collections.Counter((x['method'],x['ordinal']) for x in samples)
 assert len(positions)==16 and set(positions.values())=={10}
 pairs=collections.Counter()
 for i in range(40):
  row=sorted((x for x in samples if x['measuredRound']==i),key=lambda x:x['ordinal'])
  assert len(row)==4
  pairs.update((a['method'],b['method']) for a,b in zip(row,row[1:]))
 assert len(pairs)==12 and set(pairs.values())=={10}
 for x in samples:
  method=x['method'];assert x['worker']['method']==method
  assert x['outsideInvokeMs']>=0
  assert abs(x['outsideInvokeMs']-(x['client']['totalMs']-x['worker']['stages']['invoke']))<1e-9
  c=x['worker']['counters'];n=c.get('readFiles',0)
  assert c.get('readBytes',0)==4096*n
  if method in ('definition','references'):assert n>=1
  if method.startswith('test.'):assert c=={}
  if r['transport']=='mcp':
   assert str(x['core']['id'])==str(x['client']['id'])
   assert [str(x['worker']['id'])]==[str(v) for v in x['core']['workerIds']]
  else:assert str(x['worker']['id'])==str(x['client']['id'])
  hashes[method].add(x['resultSha256']);counts[method][(n,c.get('readBytes',0),c.get('fullRecoveries',0))]+=1
assert all(len(v)==1 for v in hashes.values())
if manifest.get('replaySearch'):assert hashes['test.replaySearch']==hashes['workspaceSymbols']

def summarize(samples):
 metrics={}
 for x in samples:
  row={**{'client.'+k:v for k,v in x['client'].items() if k!='id'},**{'worker.'+k:v for k,v in x['worker']['stages'].items()},'outsideInvokeMs':x['outsideInvokeMs'],'worker.previousLogMs':x['worker']['previousLogMs']}
  for k in ['readFiles','readBytes','fullRecoveries']:row['counter.'+k]=x['worker']['counters'].get(k,0)
  if 'core' in x:
   row.update({'core.'+k:v for k,v in x['core']['stages'].items()});row.update({'coreThreadCpu.'+k:v for k,v in x['core']['threadCpuStages'].items()})
  for k,v in row.items():metrics.setdefault(k,[]).append(v)
 return {k:stats(v) for k,v in metrics.items()}
rows=[]
for transport in ['direct','mcp']:
 for interval in intervals:
  for method in methods:
   selected=[r for r in records if r['transport']==transport and r['interval']==interval]
   perSession=[dict(name=r['name'],metrics=summarize([x for x in r['samples'] if x['method']==method])) for r in selected]
   pooled=summarize([x for r in selected for x in r['samples'] if x['method']==method])
   rows.append(dict(transport=transport,interval=interval,method=method,sessions=perSession,pooled=pooled))
data=dict(status='passed',rawSha256=hashlib.sha256(raw.read_bytes()).hexdigest(),processes=len(records),measuredChecks=sum(len(r['samples']) for r in records),balancedPositions=True,balancedPredecessors=True,stableExactResultHashes={k:sorted(v) for k,v in hashes.items()},freshReadAccounting={k:[dict(readFiles=a,readBytes=b,fullRecoveries=c,count=n) for (a,b,c),n in v.items()] for k,v in counts.items()},rows=rows,scope='Instrumented synthetic SDK11 diagnostics, not ordinary MCP/Glider acceptance timing. Pooled statistics and every session retained. Nested scopes overlap; do not add their medians. Per-request residuals include scheduling, serialization, pipes and client handling; they are not pure pipe time. Replay is a generated-only fixed-result control, not a validated production answer.')
for name,value in [('operation-analysis.json',(json.dumps(data,indent=2)+'\n').encode()),('analysis-adapter.py',Path(__file__).read_bytes())]:
 p=out/name
 if p.exists():assert p.read_bytes()==value,'Refuse to replace a different derived receipt: '+name
 else:p.write_bytes(value)
print('Boundary audit passed:',data['processes'],'processes;',data['measuredChecks'],'joined responses; balanced positions/predecessors; exact fresh-read and payload identities.')
