# SPDX-License-Identifier: Apache-2.0
"""Recompute failure decisions from all retained calibration records; no native code run."""
import hashlib,json,statistics
from pathlib import Path
repo=Path.cwd();root=repo/'bin/.local/benchmarks/reference-context';sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
caps=root/'work-capabilities-v1';initial=json.loads((caps/'result.json').read_text());assert initial['supported'] and initial['status']=='passed'
for name,h in initial['hashes'].items():assert sha(caps/name)==h
managed=root/'work-probe-v1';m=json.loads((managed/'calibration-result.json').read_text());rows=[json.loads(x) for x in (managed/'managed-calibration.jsonl').read_text().splitlines()]
assert len(rows)==611 and sum(x['kind']=='work' for x in rows)==90 and sum(x['kind']=='empty' for x in rows)==500 and sum(x['kind']=='nested' for x in rows)==20
for item in m['ratios']:
 values={factor:[x['delta']['instructions'] for x in rows if x['kind']=='work' and x['mode']==item['mode'] and x['size']==item['size'] and x['factor']==factor] for factor in [1,2]}
 assert all(len(a)==5 for a in values.values())
 assert item['oneMedian']==statistics.median(values[1]) and item['twoMedian']==statistics.median(values[2])
 assert item['ratio']==statistics.median(values[2])/statistics.median(values[1])
valid=all(1.7<x['ratio']<2.3 for x in m['ratios'] if x['size']==25000) and all(1.8<x['ratio']<2.2 for x in m['ratios'] if x['size']!=25000)
assert not valid and m['status']=='failed' and sha(managed/'managed-calibration.jsonl')==m['observationsSha256']
native=root/'native-work-probe-v1';n=json.loads((native/'calibration-result.json').read_text());rows=[json.loads(x) for x in (native/'native-calibration.jsonl').read_text().splitlines()]
assert len(rows)==2224 and sum(x['kind']=='empty' for x in rows)==2000 and sum(x['kind']=='nested' for x in rows)==224
for x in rows:
 if x['kind']=='nested':
  for key in ['instructions','cycles','cpuNs']:assert x['outer'][key]>=x['inner'][key] and x['outer'][key]-x['inner'][key]==x['pre'][key]+x['post'][key]
for item in n['variability']:
 values=[x['outer']['instructions']-x['inner']['instructions'] for x in rows if x['kind']=='nested' and all(x[k]==item[k] for k in ['thread','size','gap','factor'])]
 assert len(values)==7 and item['median']==statistics.median(values) and item['rangeFraction']==(max(values)-min(values))/statistics.median(values)
for item in n['ratios']:
 values={factor:[x['outer']['instructions']-x['inner']['instructions'] for x in rows if x['kind']=='nested' and all(x[k]==item[k] for k in ['thread','size','gap']) and x['factor']==factor] for factor in [1,2]}
 assert item['ratio']==statistics.median(values[2])/statistics.median(values[1])
valid=all(1.7<x['ratio']<2.3 for x in n['ratios'] if x['size']==10000) and all(1.8<x['ratio']<2.2 for x in n['ratios'] if x['size']>=50000) and all(x['rangeFraction']<.05 for x in n['variability'] if x['size']>=50000)
assert not valid and n['status']=='failed' and sha(native/'native-calibration.jsonl')==n['rawSha256'] and sha(managed/'calibration-result.json')==n['failedManagedSha256']
for folder in [managed,native]:
 decision=json.loads((folder/'decision.json').read_text());assert decision['status']=='qualification_failed' and not decision['freeflightProbeBuilt'] and decision['newFreeflightQueries']==0
 assert not (folder/'core-source').exists() and not (folder/'worker-source').exists() and not (folder/'core-build').exists() and not (folder/'worker-build').exists() and not (folder/'manifest.json').exists()
 assert sha(folder/'calibration-result.json')==decision['calibrationSha256']
 for name in ['prepare.py'] if folder==managed else ['native_prepare.py']:assert sha(folder/('failed-'+name))==decision['sourceSha256']
result=dict(status='passed',initialNativeCapability='passed',managedShortCalibration='failed;90work+500empty+20nested+1ABI records',nativeSmallComplement='failed;224nested+2000empty records',newFreeflightQueries=0,probeBuilt=False,managedLargestRatio=max(x['ratio'] for x in m['ratios']),nativeLargestQualifiedSizeRepeatRange=max(x['rangeFraction'] for x in n['variability'] if x['size']>=50000),rawHashes={str(p.relative_to(root)):sha(p) for p in [caps/'result.json',managed/'calibration-result.json',managed/'managed-calibration.jsonl',managed/'decision.json',native/'calibration-result.json',native/'native-calibration.jsonl',native/'decision.json',root/'work-design-review-v1.json']},adapterSha256=sha(Path(__file__)),scope='Failure receipt integrity/recomputed gates pass; this does not convert failed measurement qualification into success. All observations retained; no calibration/native library or FreeFlight code executed by audit.')
p=root/'work-qualification-audit-v1.json';value=json.dumps(result,indent=2)+'\n'
if p.exists():assert p.read_text()==value,'Refuse different derived data'
else:p.write_text(value)
print('Receipt-only audit passed; both instruction qualifications remain failed;0newFreeFlightqueries,0FreeFlightprobebuilds.')
