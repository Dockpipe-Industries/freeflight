# SPDX-License-Identifier: Apache-2.0
"""Receipt-only expansion of nested request boundaries; no new observations."""
import hashlib,json,os,statistics,sys
from pathlib import Path
repo=Path.cwd();sys.path.insert(0,str(repo/'workflows/benchmark.trusted/assets'));from run import stats
out=repo/'bin/.local/benchmarks/reference-context'/os.environ['FREEFLIGHT_REFERENCE_ATTRIBUTION_LABEL']
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
rows=json.loads((out/'samples.json').read_text());audit=json.loads((out/'result.json').read_text())
assert audit['status']=='passed' and sha(out/'samples.json')==audit['rawSha256']
keys=['total','invoke','workerEnvelope','coreRouting','outerMcpClient','boundary']
def values(x):
 t=x['ms'];i=x['worker']['stages']['invoke'];r=x['core']['stages']['workerRoundTrip'];s=x['core']['stages']['serverCall']
 v=dict(total=t,invoke=i,workerEnvelope=r-i,coreRouting=s-r,outerMcpClient=t-s,boundary=t-i)
 identity(v);return v
def identity(v):
 assert abs(v['total']-v['invoke']-v['workerEnvelope']-v['coreRouting']-v['outerMcpClient'])<1e-9
 assert abs(v['boundary']-v['workerEnvelope']-v['coreRouting']-v['outerMcpClient'])<1e-9
partitions=[];negative=[];checked=0
for row in rows:
 if row['observer']!='probe':continue
 a=[]
 for x in row['samples']:
  if x['method']!='references':continue
  v=values(x);checked+=1
  if any(v[k]<0 for k in keys):negative.append(dict(session=row['session'],id=x['id'],phase=x['phase'],values=v))
  if x['phase']=='measured':a.append(dict(**x,boundaries=v))
 for scope,pair,xs in [('session',None,a)]+[('blockPair',pair,[x for x in a if x['block']//2==pair]) for pair in range(4)]:
  arms={arm:{k:stats([x['boundaries'][k] for x in xs if x['arm']==arm]) for k in keys} for arm in ['immediate','wait-before']}
  means={arm:{k:v['mean'] for k,v in d.items()} for arm,d in arms.items()}
  for v in means.values():identity(v)
  delta={k:means['wait-before'][k]-means['immediate'][k] for k in keys};identity(delta)
  partitions.append(dict(session=row['session'],scope=scope,pair=pair,arms=arms,arithmeticMeanDeltaMs=delta))
assert checked==368
result=dict(status='passed',rawSha256=sha(out/'samples.json'),parentResultSha256=sha(out/'result.json'),adapterSha256=sha(Path(__file__)),referenceRequestsAllPhases=checked,partitions=partitions,negativeResiduals=negative,analysisTiming='Receipt-only algebra added after collection. No new requests, sample selection or reproduction-gate changes.',definitions=dict(workerEnvelope='core workerRoundTrip minus worker invoke: request/reply handling, queueing/scheduling, parsing, serialization and transport; not pure pipe latency.',coreRouting='core serverCall minus workerRoundTrip: routing/authorization/path validation/native dispatch and observer work; not pure validation.',outerMcpClient='client total minus core serverCall: MCP/client envelope, dispatch/queueing/scheduling, serialization/parsing and observation; not pure transport.'),scope='Exact per-request and arithmetic-mean identities, all reference phases and every matched block pair. Signed residuals retained; independent medians are not additive. Cross-process clock origins are not compared; only durations with logical request containment are subtracted. No hardware or causal attribution.')
for name,value in [('boundary-result.json',(json.dumps(result,indent=2)+'\n').encode()),('boundary-audit.py',Path(__file__).read_bytes())]:
 p=out/name
 if p.exists():assert p.read_bytes()==value,'Refuse different derived data'
 else:p.write_bytes(value)
print('Boundary receipt-only audit passed:',checked,'reference records; negative residuals',len(negative))
for x in partitions:
 if x['scope']=='session':print('probe',x['session'],'boundary mean deltas',x['arithmeticMeanDeltaMs'])
