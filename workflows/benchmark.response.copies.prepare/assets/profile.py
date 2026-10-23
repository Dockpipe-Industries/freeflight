# SPDX-License-Identifier: Apache-2.0
"""Fixed-payload generated diagnostic, separate from ordinary acceptance timing."""
import hashlib,importlib.util,json,os,shutil,statistics,subprocess,sys,time
from pathlib import Path
repo=Path.cwd();sys.path.insert(0,str(repo/'workflows/benchmark.trusted/assets'))
import run as trusted
from native_profile import instrument_core
spec=importlib.util.spec_from_file_location('client',repo/'workflows/benchmark/assets/measure.py');client=importlib.util.module_from_spec(spec);spec.loader.exec_module(client)
receipt=repo/'bin/.local/benchmarks/response-copies'/os.environ['FREEFLIGHT_RESPONSE_LABEL'];m=json.loads((receipt/'manifest.json').read_text());assert m['status']=='passed'
out=receipt/'fixed-payload-profile-v1';out.mkdir(exist_ok=False)
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(name,v):(out/name).write_text(json.dumps(v,indent=2)+'\n')
shutil.copy2(__file__,out/'adapter-source.py');shutil.copy2(repo/'workflows/benchmark.trusted/assets/native_profile.py',out/'native_profile.py')
workerReceipt=repo/'bin/.local/benchmarks/definition-cost/search-replay-boundaries-v1';w=json.loads((workerReceipt/'result.json').read_text());dll=workerReceipt/'worker-build/bin/FreeFlight.Roslyn/release/FreeFlight.Roslyn.dll';assert sha(dll)==w['workerSha256']
config=json.loads((repo/'bin/.local/benchmarks/trusted/background-cooperative-v4/provenance.json').read_text());fixture=dict(config['fixtures']['5845']);root=Path(fixture['root']).resolve();fixture['root']=str(root);queries,check=trusted.workload(fixture,5845);search=dict(queries)['workspaceSymbols']
cmake=m['cmake'];binaries={};sourceHashes={}
for variant in ['baseline','candidate']:
 source=out/(variant+'-source');shutil.copytree(m['variants'][variant]['source'],source);instrument_core(source);build=out/(variant+'-build')
 with (out/(variant+'-qualification.log')).open('w') as log:
  for command in [[cmake,'-S',str(source),'-B',str(build),'-DCMAKE_BUILD_TYPE=Release','-DFETCHCONTENT_SOURCE_DIR_JSON='+str(repo/'bin/.local/build/_deps/json-src')],[cmake,'--build',str(build),'--parallel','2'],[str(Path(cmake).with_name('ctest')),'--test-dir',str(build),'--output-on-failure']]:subprocess.run(command,stdout=log,stderr=subprocess.STDOUT,check=True)
 binaries[variant]=str(build/'freeflight');sourceHashes[variant]={str(p.relative_to(source)):sha(p) for p in source.rglob('*') if p.is_file()}
env={k:os.environ[k] for k in ['PATH','SystemRoot','WINDIR','TEMP','TMP','TMPDIR','LANG','LC_ALL'] if k in os.environ};env.update(DOTNET_ROOT=str(Path(config['dotnet']).parent),DOTNET_CLI_TELEMETRY_OPTOUT='1',DOTNET_EnableDiagnostics='0',DOTNET_GENERATE_ASPNET_CERTIFICATE='false',DOTNET_SKIP_FIRST_TIME_EXPERIENCE='1')
save('run-manifest.json',dict(workerDll=str(dll),workerSha256=sha(dll),binaries={v:dict(path=p,sha256=sha(Path(p))) for v,p in binaries.items()},sourceHashes=sourceHashes,sequence=['baseline','candidate','candidate','baseline'],rounds=48,warmupSeconds=5,intervalSeconds=.1,environment=env,fixture=fixture,adapterSha256=sha(Path(__file__))))
rows=[];expected=None
for index,variant in enumerate(['baseline','candidate','candidate','baseline']):
 directory=out/f'{index}-{variant}';directory.mkdir();s=client.Session(root,directory,engines={'csharp':[config['dotnet'],str(dll),'--incremental-validation','--background-recovery']},configuration={'trustedRoots':[str(root)],'csharp':{'project':fixture['project']}},sample_memory=False,command=[binaries[variant],'--config',str(directory/'freeflight.json')],environment=env,working_directory=root)
 samples=[]
 def call(method):
  start=time.perf_counter_ns();r=s.request('tools/call',{'name':'semantic.query','arguments':{'root':str(root),'language':'csharp','operation':method,'arguments':search}});ms=(time.perf_counter_ns()-start)/1e6
  value=json.loads(r['content'][0]['text']);assert r['structuredContent']=={'items':value};check('workspaceSymbols',value)
  return value,ms
 try:
  primed,_=call('workspaceSymbols')
  if expected is None:expected=primed;save('oracle.json',expected)
  assert primed==expected
  start=time.monotonic();measured=0
  while time.monotonic()-start<5 or measured<48:
   steady=time.monotonic()-start>=5;began=time.monotonic();value,ms=call('test.replaySearch');assert value==expected
   if steady:samples.append(dict(id=s.sequence,ms=ms,measuredRound=measured));measured+=int(steady)
   time.sleep(max(0,.1-(time.monotonic()-began)))
 finally:s.close()
 logs=(directory/'server.stderr.log').read_text();assert 'Unhandled exception' not in logs
 core={}
 for line in logs.splitlines():
  if line.startswith('CORE_PROFILE '):
   record=json.loads(line[len('CORE_PROFILE '):]);key=str(record['id']);assert key not in core;core[key]=record
 for sample in samples:sample['core']=core[str(sample['id'])]
 assert len(samples)==48
 rows.append(dict(variant=variant,index=index,samples=samples));save('samples.json',rows);print(variant,index,'48 identical payloads passed',flush=True)
metrics={v:{k:statistics.median(statistics.median(x['core']['threadCpuStages'][k] for x in row['samples']) for row in rows if row['variant']==v) for k in ['coreTotal','workerResponseParse','responseConstruction','resultEnvelope','mcpSerialize']} for v in ['baseline','candidate']}
for name,h in fixture['hashes'].items():assert sha(root/name)==h
save('result.json',dict(status='passed',processes=4,measuredChecks=192,coreThreadCpuMs=metrics,coreCpuRatio=metrics['candidate']['coreTotal']/metrics['baseline']['coreTotal'],scope='Generated-only exact fixed-search-payload replay; matched binary source and SDK with normal security checks. Instrumented core thread CPU, not ordinary latency, native allocation or fresh semantic-answer acceptance. Every record retained. Nested scopes overlap and cannot be summed.'))
print('core CPU ratio',metrics['candidate']['coreTotal']/metrics['baseline']['coreTotal'],flush=True)
