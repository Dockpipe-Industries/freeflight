# SPDX-License-Identifier: Apache-2.0
"""Summarize all serial candidate/control samples without latency filtering."""
import json,os,pathlib,statistics
from native_summary import summarize
root=pathlib.Path.cwd();base=root/'bin/.local/glider-comparison';label=os.environ.get('FREEFLIGHT_SERIAL_COMPARE_LABEL','serial-handles-mcp-v1');out=base/label
assert json.loads((out/'result.json').read_text())['status']=='passed'
rows=[];counts={}
for condition in [x['stage'] for x in json.loads((out/'result.json').read_text())['conditions']]:
 receipt=base/(label+'-'+condition);data=json.loads((receipt/'samples.json').read_text())
 assert all(s['status']=='passed' for s in data)
 counts[condition]=dict(processes=len(data),measuredChecks=sum(sum(x['phase']!='warmup' for x in s['samples']) for s in data))
 if condition.endswith('diagnostic'):summarize(receipt);continue
 summary=json.loads((receipt/'summary.json').read_text())
 for size in sorted({s['size'] for s in data}):
  for interval in sorted({s['interval'] for s in data}):
   for phase in ['steady','idle-5.1s']:
    for method in ['symbols','definition','references','workspaceSymbols']:
     cell=dict(condition=condition,size=size,interval=interval,phase=phase,method=method)
     for variant in ['local-baseline','candidate']:
      values=[r for r in summary['sessions'] if r['size']==size and r['interval']==interval and r['phase']==phase and r['method']==method and r['variant']==variant]
      assert values
      cell[variant]={key:statistics.median(r[key] for r in values) for key in ['median','p90']}
      cell[variant]['maximum']=max(r['maximum'] for r in values)
      cell[variant]['sessions']=values
      if phase=='idle-5.1s':
       from run import stats
       pooled=[x['ms'] for session in data if session['size']==size and session['interval']==interval and session['variant']==variant for x in session['samples'] if x['phase']==phase and x['method']==method]
       cell[variant]['pooledIdle']=stats(pooled)
     cell['medianRatio']=cell['candidate']['median']/cell['local-baseline']['median']
     cell['p90Ratio']=cell['candidate']['p90']/cell['local-baseline']['p90']
     rows.append(cell)
 cpu=[]
 for s in data:
  t=s['wholeSessionChildCpuSeconds'];cpu.append(dict(session=s['name'],variant=s['variant'],size=s['size'],interval=s['interval'],seconds=t['user']+t['system'],loadMs=s['loadMs'],startupMs=s['startupDiscoveryMs'],backgroundWarmupMs=s['backgroundWarmupMs']))
 (out/(condition+'-session-costs.json')).write_text(json.dumps(cpu,indent=2)+'\n')
(out/'review.json').write_text(json.dumps(dict(status='all-samples-retained',counts=counts,cells=rows),indent=2)+'\n')
print(json.dumps(counts))
for r in rows:
 if r['condition'] in ('balanced','small-repeat','small-control') and (r['phase']=='steady' or r['method']=='symbols'):
  print(r['size'],r['interval'],r['phase'],r['method'],r['local-baseline']['median'],r['candidate']['median'],'p90',r['local-baseline']['p90'],r['candidate']['p90'],'max',r['local-baseline']['maximum'],r['candidate']['maximum'])
