# SPDX-License-Identifier: Apache-2.0
"""Reuse the MCP benchmark client and frozen trusted fixtures for end-to-end timing."""
import importlib.util
import json
import os
from pathlib import Path
import statistics
import time
import run as trusted

spec=importlib.util.spec_from_file_location('freeflight_mcp_benchmark',trusted.REPO/'workflows/benchmark/assets/measure.py')
client=importlib.util.module_from_spec(spec);spec.loader.exec_module(client)
config=json.loads((trusted.OUT/'provenance.json').read_text())
assert json.loads((trusted.OUT/'qualification.json').read_text())['status']=='passed'
assert json.loads((trusted.OUT/'transaction-qualification.json').read_text())['status']=='passed'
assert (trusted.OUT/'summary.json').is_file(), 'Finish the worker comparison first'
label=os.environ.get('FREEFLIGHT_TRUSTED_MCP_LABEL','mcp')
assert label and all(c.isalnum() or c in '-_' for c in label), 'Invalid MCP receipt label'
output=trusted.OUT/label;output.mkdir(exist_ok=False)
def save(name,value):(output/name).write_text(json.dumps(value,indent=2)+'\n')
core=trusted.REPO/'bin/.local/build/freeflight'
if not core.is_file():core=trusted.REPO/'bin/.local/build/Release/freeflight.exe'
assert core.is_file(), 'Run the existing core.build workflow first'
for variant in config['variants'].values():
 assert trusted.digest(Path(variant['dll']))==variant['dllSha256'], 'Frozen worker binary changed'
for fixture in config['fixtures'].values():
 for relative,digest in fixture['hashes'].items():assert trusted.digest(Path(fixture['root'])/relative)==digest,relative
assert trusted.subprocess.check_output([trusted.DOTNET,'--version'],cwd=trusted.REPO,env=trusted.ENV).decode().strip()==config['sdk'], 'SDK changed'
rounds=int(os.environ.get('FREEFLIGHT_TRUSTED_MCP_ROUNDS',config['rounds']));assert rounds>=10
os.environ.update(trusted.ENV)
save('provenance.json',dict(workerProvenanceSha256=trusted.digest(trusted.OUT/'provenance.json'),core=str(core),coreSha256=trusted.digest(core),rounds=rounds,sessions=config['sessions'],warmupSeconds=config['warmupSeconds'],transport='C++ MCP stdio with frozen SDK-hosted trusted workers',driverHashes={str(p.relative_to(trusted.REPO)):trusted.digest(p) for p in (Path(__file__),Path(trusted.__file__),Path(client.__file__))},limitations=['Synthetic fixture, not Biztraak or Glider.', 'Core capabilities contain cached pre-open refreshStats; not used as live counters.', 'SDK-hosted workers, not self-contained release bundles.', 'No diagnostic instrumentation or RSS sampler in these timings.']))
sessions=[]
order=[]
for pair in range(config['sessions']):
 baseline_first=(pair%2==0)==(config.get('firstVariant','baseline')=='baseline')
 order.extend(['baseline','candidate'] if baseline_first else ['candidate','baseline'])
for size,fixture in config['fixtures'].items():
 root=Path(fixture['root']);queries,check=trusted.workload(fixture,int(size))
 for index,variant in enumerate(order):
  name=f'{size}-mcp-{index}-{variant}';directory=output/name;directory.mkdir()
  session=client.Session(root,directory,engines={'csharp':[trusted.DOTNET,config['variants'][variant]['dll']]},configuration={'trustedRoots':[str(root)],'csharp':{'project':fixture['project']}},sample_memory=False)
  receipt=dict(name=name,size=int(size),variant=variant,samples=[],startupDiscoveryMs=session.startup_ms);sessions.append(receipt)
  try:
   start=time.perf_counter_ns()
   caps=session.request('tools/call',{'name':'engine.capabilities','arguments':{'root':str(root),'language':'csharp'}})['structuredContent']
   receipt['loadMs']=(time.perf_counter_ns()-start)/1e6
   assert caps['analysis']['files']==int(size) and caps['analysis']['projects']==fixture['projects'],caps
   assert caps['analysis']['mode']=='trusted-msbuild',caps
   def cycle(phase,round):
    for method,args in queries:
     result,ms=session.query('csharp',method,**args);check(method,result)
     receipt['samples'].append(dict(method=method,phase=phase,round=round,ms=ms))
   start=time.monotonic();round=0
   while round<3 or time.monotonic()-start<config['warmupSeconds']:cycle('warmup',round);round+=1
   for round in range(rounds):cycle('steady',round)
   time.sleep(5.1);cycle('expiry',0);receipt['status']='passed'
  except Exception as error:receipt['status']='failed';receipt['error']=repr(error);raise
  finally:session.close();save('samples.json',sessions)
  print(name,'passed',flush=True)
summary=[];comparisons=[]
for session in sessions:
 for phase in ('warmup','steady','expiry'):
  for method in ('symbols','definition','references','workspaceSymbols'):
   summary.append(dict(session=session['name'],size=session['size'],variant=session['variant'],phase=phase,method=method,**trusted.stats([r['ms'] for r in session['samples'] if r['phase']==phase and r['method']==method])))
for size in config['sizes']:
 for method in ('symbols','definition','references','workspaceSymbols'):
  rows=[r for r in summary if r['size']==size and r['method']==method and r['phase']=='steady'];b=[r for r in rows if r['variant']=='baseline'];c=[r for r in rows if r['variant']=='candidate']
  item=dict(size=size,method=method,baseline=b,candidate=c,medianRatio=statistics.median(r['median'] for r in c)/statistics.median(r['median'] for r in b),p90Ratio=statistics.median(r['p90'] for r in c)/statistics.median(r['p90'] for r in b),unfavorableCandidateSessions=[r['session'] for r in c if r['p90']>statistics.median(x['p90'] for x in b)]);comparisons.append(item)
  print(size,method,'median ratio',round(item['medianRatio'],3),'p90 ratio',round(item['p90Ratio'],3))
save('summary.json',dict(sessions=summary,comparisons=comparisons))
