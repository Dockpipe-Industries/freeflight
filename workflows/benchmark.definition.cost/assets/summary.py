# SPDX-License-Identifier: Apache-2.0
"""Stratify paired diagnostic requests; preserve every sample and process."""
import hashlib,json,os,statistics,sys
from pathlib import Path
sys.path.insert(0,str(Path.cwd()/'workflows/benchmark.trusted/assets'));from run import stats
out=Path.cwd()/'bin/.local/benchmarks/definition-cost'/os.environ['FREEFLIGHT_DEFINITION_LABEL']
records=json.loads((out/'observations.json').read_text());rows=[]
result=json.loads((out/'result.json').read_text());extended=result.get('extended',False);methods=result.get('methods',['definition','test.transport'])
for r in records:
 for x in r['samples']:
  x['position']=x['ordinal'] if extended else int((x['method']=='definition')!=(x['round']%2==0))
  assert x['outsideInvokeMs']>=0
for transport in ['direct','mcp']:
 for interval in result.get('intervals',[0,.1]):
  for method in methods:
   for position in (range(4) if extended else range(2)):
    a=[x for r in records if r['transport']==transport and r['interval']==interval for x in r['samples'] if x['method']==method and x['position']==position]
    metrics={k:stats([x['client'][k] for x in a]) for k in ['totalMs','readerQueueMs','parseMs']}
    for k in set().union(*(x['worker']['stages'] for x in a)):metrics['worker.'+k]=stats([x['worker']['stages'].get(k,0) for x in a])
    if extended:
     for k in ['readFiles','readBytes','fullRecoveries']:metrics['worker.counter.'+k]=stats([x['worker']['counters'].get(k,0) for x in a])
    metrics['outsideInvoke']=stats([x['outsideInvokeMs'] for x in a]);metrics['worker.previousLog']=stats([x['worker']['previousLogMs'] for x in a])
    if transport=='mcp':
     for k in set().union(*(x['core']['stages'] for x in a)):metrics['core.'+k]=stats([x['core']['stages'].get(k,0) for x in a])
     metrics['core.serverOutsideWorker']=stats([x['core']['stages']['serverCall']-x['core']['stages']['workerRoundTrip'] for x in a])
    rows.append(dict(transport=transport,interval=interval,method=method,position=position,n=len(a),metrics=metrics))
(out/'position-summary.json').write_text(json.dumps(dict(status='passed',rows=rows),indent=2)+'\n')
for r in rows:
 if r['interval']==.1:print(r['transport'],r['method'],r['position'],{k:round(r['metrics'].get(k,{'median':0})['median'],4) for k in ['totalMs','worker.invoke','worker.refresh','worker.queue','worker.gate','outsideInvoke']})
