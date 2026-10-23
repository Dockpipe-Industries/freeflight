# SPDX-License-Identifier: Apache-2.0
"""Independent response-copy receipt identities, balance and derived summaries."""
import collections,hashlib,json,os,statistics,sys
from pathlib import Path
repo=Path.cwd();sys.path.insert(0,str(repo/'workflows/benchmark.trusted/assets'));from run import stats
out=repo/'bin/.local/benchmarks/response-copies'/os.environ['FREEFLIGHT_RESPONSE_LABEL'];m=json.loads((out/'manifest.json').read_text());assert m['status']=='passed'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
assert sha(Path(m['worker']['dll']))==m['worker']['dllSha256']
for variant,entry in m['variants'].items():
 assert sha(Path(entry['binary']))==entry['binarySha256']
 for name,h in entry['sourceHashes'].items():assert sha(Path(entry['source'])/name)==h
 log=(out/(variant+'-qualification.log')).read_text();assert '100% tests passed' in log and '\nOK\n' in log
summaries=[]
for directory in [out/'all-operations-v1']:
 manifest=json.loads((directory/'run-manifest.json').read_text());result=json.loads((directory/'result.json').read_text());rows=json.loads((directory/'samples.json').read_text());n=12 if manifest['mode']=='all' else 4;rounds=manifest['rounds']
 assert result['status']=='passed' and manifest['preparedManifestSha256']==sha(out/'manifest.json')
 assert len(rows)==len({(r['size'],r['index'],r['variant']) for r in rows})==len(manifest['sizes'])*2*manifest['sessions']
 assert sha(directory/'adapter-source.py')==manifest['adapterSha256'];assert sha(directory/'client-source.py')==manifest['clientSha256']
 positions=[]
 for row in rows:
  samples=row['samples'];assert len(samples)==n*rounds and len({(x['measuredRound'],x['ordinal']) for x in samples})==n*rounds
  counts=collections.Counter((x['method'],x['ordinal']) for x in samples);assert len(counts)==n*n and set(counts.values())=={rounds//n}
  pairs=collections.Counter()
  for i in range(rounds):
   a=sorted((x for x in samples if x['measuredRound']==i),key=lambda x:x['ordinal']);pairs.update((x['method'],y['method']) for x,y in zip(a,a[1:]))
  assert len(pairs)==n*(n-1) and set(pairs.values())=={rounds//n}
 for comp in result['comparisons']:
  for v in ['baseline','candidate']:
   source=[r for r in rows if r['size']==comp['size'] and r['variant']==v]
   recalculated=[stats([x['ms'] for x in r['samples'] if x['method']==comp['method']]) for r in source]
   assert recalculated==comp['stats'][v]
  for key,metric in [('medianRatio','median'),('p90Ratio','p90')]:
   ratio=statistics.median(x[metric] for x in comp['stats']['candidate'])/statistics.median(x[metric] for x in comp['stats']['baseline']);assert abs(comp[key]-ratio)<1e-12
  for ordinal in range(n):
   perSession={v:[statistics.median(x['ms'] for x in r['samples'] if x['method']==comp['method'] and x['ordinal']==ordinal) for r in rows if r['size']==comp['size'] and r['variant']==v] for v in ['baseline','candidate']}
   positions.append(dict(size=comp['size'],method=comp['method'],ordinal=ordinal,sessionMediansMs=perSession,ratio=statistics.median(perSession['candidate'])/statistics.median(perSession['baseline'])))
 assert result['measuredChecks']==sum(len(r['samples']) for r in rows)
 summaries.append(dict(label=directory.name,processes=len(rows),checks=result['measuredChecks'],comparisons=result['comparisons'],positionStrata=positions,rawSha256=sha(directory/'samples.json')))
for size,f in m['fixtures'].items():
 for name,h in f['hashes'].items():assert sha(Path(f['root']).resolve()/name)==h
base=Path(m['variants']['baseline']['source']);candidate=Path(m['variants']['candidate']['source'])
assert (base/'tests/process.cpp').read_bytes()==(candidate/'tests/process.cpp').read_bytes()
for name in m['variants']['baseline']['sourceHashes']:
 if name!='src/process.cpp':assert (base/name).read_bytes()==(candidate/name).read_bytes()
import subprocess
assert (base/'src/process.cpp').read_bytes()==subprocess.check_output(['git','show','94eb420:src/process.cpp'])
s=(candidate/'src/process.cpp').read_text();assert 'buffered.substr(0, newline)' not in s and "find('\\n', previousSize)" in s and 'cbegin() + static_cast<std::ptrdiff_t>(newline)' in s
adverse=[dict(size=x['size'],method=x['method'],medianRatio=x['medianRatio'],p90Ratio=x['p90Ratio']) for x in summaries[0]['comparisons'] if x['medianRatio']>1.10 or x['p90Ratio']>1.10]
value=dict(status='passed',decision='stop_expansion_unaccepted' if adverse else 'screen_only_not_accepted',adverseCells=adverse,ordinaryChecks=sum(x['checks'] for x in summaries),ordinaryProcesses=sum(x['processes'] for x in summaries),ordinary=summaries,scope='Complete original sessions and adverse cells retained. Position strata are descriptive and do not replace aggregate results. No new benchmark requests. Instrumented fixed-payload CPU is separate from ordinary acceptance latency.')
for name,data in [('validated-summary.json',(json.dumps(value,indent=2)+'\n').encode()),('audit-adapter.py',Path(__file__).read_bytes())]:
 p=out/name
 if p.exists():assert p.read_bytes()==data,'Refuse replacement of a different derived receipt'
 else:p.write_bytes(data)
print('Reader receipt audit passed:',value['ordinaryChecks'],'exact measured checks;',len(adverse),'adverse cells; decision',value['decision'])
