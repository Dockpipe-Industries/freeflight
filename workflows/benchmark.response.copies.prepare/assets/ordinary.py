# SPDX-License-Identifier: Apache-2.0
"""Ordinary interleaved A/A and A/B observations, with no generated CPU/stage probes."""
import hashlib,importlib.util,json,os,shutil,sys,time
from pathlib import Path
repo=Path.cwd();sys.path.insert(0,str(repo/'workflows/benchmark.trusted/assets'));import run as trusted
spec=importlib.util.spec_from_file_location('client',repo/'workflows/benchmark/assets/measure.py');client=importlib.util.module_from_spec(spec);spec.loader.exec_module(client)
receipt=repo/'bin/.local/benchmarks/response-copies/json-moves-v2';m=json.loads((receipt/'manifest.json').read_text());assert m['status']=='passed'
label=os.environ['FREEFLIGHT_ORDINARY_LABEL'];assert label and all(c.isalnum() or c in '-_' for c in label)
out=receipt/label;out.mkdir(exist_ok=False)
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def save(name,v):(out/name).write_text(json.dumps(v,indent=2)+'\n')
assert sha(Path(m['worker']['dll']))==m['worker']['dllSha256']
assert m['worker']['sourceHashes']['workers/roslyn/Program.cs']=='2a2bb9e4e0f0f17ad5d1e53b9c69262905398b691221121b9d63397ebdf99484'
for name,v in m['variants'].items():
 assert sha(Path(v['binary']))==v['binarySha256']
 assert b'CORE_PROFILE ' not in Path(v['binary']).read_bytes()
 assert sha(receipt/(name+'-qualification.log'))==v['qualificationSha256']
 assert '100% tests passed' in (receipt/(name+'-qualification.log')).read_text()
fixture=dict(m['fixtures']['5845']);root=Path(fixture['root']).resolve();fixture['root']=str(root);queries,check=trusted.workload(fixture,5845)
for name,h in fixture['hashes'].items():assert sha(root/name)==h
cycle=[('sham','baseline','baseline',0),('source','candidate','candidate',0),('source','baseline','baseline',0),('sham','candidate','baseline',0),('sham','candidate','baseline',1),('source','baseline','baseline',1),('source','candidate','candidate',1),('sham','baseline','baseline',1)]
plan=[dict(index=i+epoch*8,epoch=epoch,cohort=c,variant=v,actualCore=a,pair=pair+epoch*2) for epoch in range(2) for i,(c,v,a,pair) in enumerate(cycle)]
env={k:os.environ[k] for k in ['PATH','SystemRoot','WINDIR','TEMP','TMP','TMPDIR','LANG','LC_ALL'] if k in os.environ};env.update(DOTNET_ROOT=str(Path(m['dotnet']).parent),DOTNET_CLI_TELEMETRY_OPTOUT='1',DOTNET_EnableDiagnostics='0',DOTNET_GENERATE_ASPNET_CERTIFICATE='false',DOTNET_SKIP_FIRST_TIME_EXPERIENCE='1')
manifest=dict(status='planned',date='2026-10-23',plan=plan,methods=[method for method,args in queries],rounds=48,warmupSeconds=5,minimumRoundSeconds=.1,design=[0,1,3,2],expectedMeasuredChecks=3072,fixture=fixture,workerCommand=[m['dotnet'],m['worker']['dll'],*m['workerArgs']],workerSha256=m['worker']['dllSha256'],cores={v:dict(path=e['binary'],sha256=e['binarySha256']) for v,e in m['variants'].items()},preparedManifestSha256=sha(receipt/'manifest.json'),environment=env,driverHashes={name:sha(path) for name,path in [('ordinary.py',Path(__file__)),('ordinary_audit.py',Path(__file__).with_name('ordinary_audit.py')),('client-source.py',Path(client.__file__)),('trusted-source.py',Path(trusted.__file__))]},analysisPlan=['Four chronological matched pairs per cohort; no exclusions or timing replacements.','Report every pair, ratio of session medians, median of paired ratios, pooled metric and every position. They are distinct estimands.','Record actual client-return-to-next-request-start gaps, prior method, verification and round sleep durations. No gap normalization or post-hoc sample selection.','Report candidate directions across all pairs/positions and same-binary variation without inventing a post-hoc acceptance threshold.','No runtime source change, candidate acceptance, Glider matrix or winner claim from an unstable aggregate.'],limitations=['Ordinary binaries and worker; no core/worker timers, CPU clocks, event listener, profiler or RSS sampler.','Outer timestamps and exact-answer validation are observer work. Verification is outside request timing but affects gaps.','Single synthetic full graph, one paced workload, SDK11 macOS; not other platforms, Glider or an overall-win qualification.'])
save('run-manifest.json',manifest)
for name,path in [('ordinary.py',Path(__file__)),('ordinary_audit.py',Path(__file__).with_name('ordinary_audit.py')),('client-source.py',Path(client.__file__)),('trusted-source.py',Path(trusted.__file__))]:shutil.copy2(path,out/name)
rows=[];oracle=None;configurationHash=None
try:
 for entry in plan:
  index=entry['index'];directory=out/f"{index}-{entry['cohort']}-{entry['variant']}";directory.mkdir()
  s=client.Session(root,directory,engines={'csharp':manifest['workerCommand']},configuration={'trustedRoots':[str(root)],'csharp':{'project':fixture['project']}},sample_memory=False,command=[manifest['cores'][entry['actualCore']]['path'],'--config',str(directory/'freeflight.json')],environment=env,working_directory=root)
  row=dict(**entry,samples=[],rounds=[]);lastEnd=None;lastMethod=None
  configHash=sha(directory/'freeflight.json')
  if configurationHash is None:configurationHash=configHash
  assert configHash==configurationHash;row['configurationSha256']=configHash
  def call(method,args):
   global lastEnd,lastMethod
   started=time.perf_counter_ns();gap=(started-lastEnd)/1e6 if lastEnd else None
   result=s.request('tools/call',{'name':'semantic.query','arguments':{'root':str(root),'language':'csharp','operation':method,'arguments':args}});ended=time.perf_counter_ns()
   sample=dict(id=s.sequence,method=method,previousMethod=lastMethod,requestStartNs=started,clientReturnNs=ended,ms=(ended-started)/1e6,gapMs=gap)
   lastEnd=ended;lastMethod=method
   assert len(result['content'])==1 and result['content'][0]['type']=='text'
   semantic=json.loads(result['content'][0]['text']);assert result['structuredContent']==(semantic if isinstance(semantic,dict) else {'items':semantic})
   assert result['resultType']=='complete' and 'io.modelcontextprotocol/serverInfo' in result['_meta'];check(method,semantic)
   if oracle is not None:assert semantic==oracle[method]
   sample['verificationMs']=(time.perf_counter_ns()-ended)/1e6
   return semantic,sample
  try:
   caps=s.request('tools/call',{'name':'engine.capabilities','arguments':{'root':str(root),'language':'csharp'}})['structuredContent'];assert caps['analysis']['files']==5845
   current={method:call(method,args)[0] for method,args in queries}
   if oracle is None:oracle=current;save('oracle.json',oracle)
   assert current==oracle;row['initialOracleChecks']=4
   start=time.monotonic();warm=0;measured=0
   while time.monotonic()-start<5 or measured<48:
    steady=time.monotonic()-start>=5;phase=measured if steady else warm;began=time.perf_counter_ns()
    for ordinal,i in enumerate([0,1,3,2]):
     method,args=queries[(i+phase)%4];_,sample=call(method,args)
     sample.update(phase='measured' if steady else 'warmup',round=phase,ordinal=ordinal);row['samples'].append(sample)
    beforeSleep=time.perf_counter_ns();requested=max(0,.1-(beforeSleep-began)/1e9)
    if requested:time.sleep(requested)
    row['rounds'].append(dict(phase='measured' if steady else 'warmup',round=phase,activeMs=(beforeSleep-began)/1e6,requestedSleepMs=requested*1000,actualSleepMs=(time.perf_counter_ns()-beforeSleep)/1e6))
    if steady:measured+=1
    warm+=1
  finally:s.close()
  assert s.process.returncode==0
  text=(directory/'server.stderr.log').read_text();assert 'Unhandled exception' not in text and 'CORE_PROFILE ' not in text and 'DEFINITION_COST ' not in text
  assert sum(x['phase']=='measured' for x in row['samples'])==192
  rows.append(row);save('samples.json',rows);print(index,entry['cohort'],entry['variant'],'actual',entry['actualCore'],'192 ordinary dual-content checks passed',flush=True)
 for name,h in fixture['hashes'].items():assert sha(root/name)==h
 save('collection.json',dict(status='passed',processes=16,measuredChecks=3072,warmupChecks=sum(x['phase']=='warmup' for r in rows for x in r['samples']),initialOracleChecks=64,configurationSha256=configurationHash,scope='Predefined ordinary matched full-graph comparison with sham/source cohorts; all sessions/warmups/positions retained, no performance-based filtering.'))
except Exception as error:
 save('failure.json',dict(status='failed',error=repr(error),completedProcesses=len(rows)));raise
