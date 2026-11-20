# SPDX-License-Identifier: Apache-2.0
"""Validate and summarize the preserved duplicate-row confirmation without changing raw data."""
from pathlib import Path
import collections,json,math,os,statistics,shutil
root=Path.cwd()/'bin/.local/benchmarks/trusted'/os.environ['FREEFLIGHT_OPERATION_RECEIPT']/os.environ['FREEFLIGHT_OPERATION_LABEL']
raw=json.loads((root/'samples.json').read_text());groups=collections.defaultdict(list)
for row in raw:groups[(row['size'],row['index'],row['variant'])].append(row)
assert len(groups)==8
names=['symbols','definition','references','workspaceSymbols','hover','diagnostics','rename','implementations','typeInfo','signatureHelp','callHierarchy','typeHierarchy'];design=[0,1,11,2,10,3,9,4,8,5,7,6];rows=[]
for key,copies in sorted(groups.items()):
 assert len(copies)==12 and all(x==copies[0] for x in copies)
 row=copies[0];samples=row['samples'];assert len(samples)==576 and len({(x['measuredRound'],x['ordinal']) for x in samples})==576
 for x in samples:assert x['method']==names[(design[x['ordinal']]+x['measuredRound'])%12]
 for name in names:assert all(sum(x['method']==name and x['ordinal']==position for x in samples)==4 for position in range(12))
 pairs=collections.Counter()
 for phase in range(48):
  selected=sorted([x for x in samples if x['measuredRound']==phase],key=lambda x:x['ordinal']);pairs.update((a['method'],b['method']) for a,b in zip(selected,selected[1:]))
 assert len(pairs)==132 and set(pairs.values())=={4};rows.append(row)
def stats(values):
 values=sorted(values);return dict(n=len(values),median=statistics.median(values),p90=values[math.ceil(.9*len(values))-1],maximum=max(values),mean=statistics.mean(values))
comparisons=[]
for method in names:
 values={v:[stats([x['ms'] for x in r['samples'] if x['method']==method]) for r in rows if r['variant']==v] for v in ['baseline','candidate']}
 comparisons.append(dict(size=5845,method=method,stats=values,medianRatio=statistics.median(x['median'] for x in values['candidate'])/statistics.median(x['median'] for x in values['baseline']),p90Ratio=statistics.median(x['p90'] for x in values['candidate'])/statistics.median(x['p90'] for x in values['baseline'])))
original=json.loads((root/'result.json').read_text())
for a,b in zip(comparisons,original['comparisons']):assert abs(a['medianRatio']-b['medianRatio'])<1e-12 and abs(a['p90Ratio']-b['p90Ratio'])<1e-12
validated=json.loads((root/'validated-summary.json').read_text());assert validated['comparisons']==comparisons and validated['measuredChecks']==4608
assert json.loads((root/'validated-samples.json').read_text())==rows
shutil.copy2(__file__,root/'validation-adapter.py')
print('Validated8 unique sessions,4608 actual responses, all balanced positions/predecessors; original ratios unchanged.')
