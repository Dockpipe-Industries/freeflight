# SPDX-License-Identifier: Apache-2.0
"""Receipt-only qualification audit; never executes helper/native code or queries."""
import hashlib,json
from pathlib import Path
repo=Path.cwd();root=repo/'bin/.local/benchmarks/reference-context';out=root/'aggregate-work-calibration-v3'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
load=lambda p:json.loads(p.read_text())
plan=load(out/'plan.json');provenance=load(out/'provenance.json');result=load(out/'result.json');rows=[json.loads(x) for x in (out/'raw.jsonl').read_text().splitlines()]
assert len(rows)==32 and plan['ratioBand']==[1.9,2.1] and plan['incrementTolerance']==.05
for name,h in plan['assetHashes'].items():assert sha(out/name)==h
assert sha(out/'libaggregate.dylib')==provenance['helperSha256'] and sha(out/'child/bin/Release/net11.0/Child.dll')==provenance['childSha256']
for name,h in provenance['sourceHashes'].items():assert sha(out/name)==h
ratios=[]
for session in range(2):
 cell=[x for x in rows if x['session']==session];assert [x['arm'] for x in cell]==plan['arms']
 for label in ['before','after']:
  c=load(out/f'{session}-cpu-{label}.json');total=lambda v:(v['userMach']+v['systemMach'])*v['numer']//v['denom']
  assert total(c['left'])==c['lo'] and total(c['right'])==c['hi'] and c['tolerance']==max(2000000,c['own']*.05)
  assert c['lo']-c['tolerance']<=c['own']<=c['hi']+c['tolerance'] and 0<=c['hi']-c['lo']<=c['tolerance']
 warm=load(out/f'{session}-complete-path-warmup.json');assert [x['n'] for x in warm]==[1000000,2000000] and all(len(x['cycles'])==16 for x in warm)
 identity=None
 for x in cell:
  a=x['before'][0];b=x['after'][0];d=x['delta'];anchor=x['anchor'];done=x['done'];ident=(a['pid'],a['start'])
  if identity is None:identity=ident
  assert ident==identity==(b['pid'],b['start']) and a['status']==b['status']==0
  assert a['numer']==b['numer'] and a['denom']==b['denom'] and a['begin']<=a['end']<anchor and b['begin']<=b['end']<anchor+4000000000
  for k in ['instructions','cycles','userMach','systemMach']:assert b[k]-a[k]==d[k]>=0
  assert d['cpuNs']==(d['userMach']+d['systemMach'])*a['numer']//a['denom']
  assert len(done['cycles'])==16 and done['cycles'][-1]['end']<b['begin']
  for i,c in enumerate(done['cycles']):assert c['i']==i and c['target']==anchor+i*250000000 and c['target']<=c['begin']<c['target']+50000000 and c['end']<c['target']+230000000 and c['result']==provenance['checksums'][str(done['n'])]
 for g in range(3):
  for ia,ib in [(g*5,g*5+1),(g*5+3,g*5+2)]:
   a=cell[ia]['delta']['instructions'];b=cell[ib]['delta']['instructions'];ratios.append(dict(session=session,a=ia,b=ib,ratio=b/a,increment=b-a,expectedIncrement=80000000))
assert ratios==result['ratios'];valid=all(1.9<=x['ratio']<=2.1 and abs(x['increment']-80000000)<=4000000 for x in ratios)
zeros=[x['delta']['instructions'] for x in rows if x['arm']=='Z'];ranges=[max(v)-min(v) for s in range(2) for arm in ['A','B'] for v in [[x['delta']['instructions'] for x in rows if x['session']==s and x['arm']==arm]]]
assert zeros==result['zeroWorkInstructions'] and ranges==result['repeatRanges'] and max(zeros)+max(ranges)==result['empiricalUncertainty']
assert result['status']==('passed' if valid else 'failed') and result['rawSha256']==sha(out/'raw.jsonl')
failed=root/'aggregate-work-calibration-v1';old=[json.loads(x) for x in (failed/'raw.jsonl').read_text().splitlines()];assert len(old)==1 and old[0]['before'][0]['end']>old[0]['anchor'] and load(failed/'diagnosis.json')['status']=='invalid_setup_clock_domain_mismatch'
second=root/'aggregate-work-calibration-v2';secondRows=[json.loads(x) for x in (second/'raw.jsonl').read_text().splitlines()];assert len(secondRows)==1 and load(second/'diagnosis.json')['status']=='invalid_setup_cpu_windows_differ'
proof=dict(status='passed',retainedUnequalWindowSha256=sha(second/'raw.jsonl'),measurementQualification=result['status'],records=len(rows),cycles=512,ratios=ratios,empiricalUncertainty=result['empiricalUncertainty'],rawSha256=sha(out/'raw.jsonl'),retainedInvalidSetupSha256=sha(failed/'raw.jsonl'),newFreeFlightQueries=0)
p=root/'aggregate-work-calibration-audit-v1.json';assert not p.exists();p.write_text(json.dumps(proof,indent=2)+'\n');print('Receipt audit passed; measurement qualification:',result['status'],'records',len(rows),'uncertainty',result['empiricalUncertainty'])
