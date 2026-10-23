# SPDX-License-Identifier: Apache-2.0
"""Predefined within-process pacing intervention with A/A and source contrasts."""
import hashlib,importlib.util,json,os,shutil,sys,time
from pathlib import Path
repo=Path.cwd();sys.path.insert(0,str(repo/'workflows/benchmark.trusted/assets'))
import run as trusted
from native_profile import install_client,assert_clean_worker_log
spec=importlib.util.spec_from_file_location('client',repo/'workflows/benchmark/assets/measure.py');client=importlib.util.module_from_spec(spec);spec.loader.exec_module(client);install_client(client)
receipt=repo/'bin/.local/benchmarks/response-copies/json-moves-v2';prepared=json.loads((receipt/'manifest.json').read_text());profile=receipt/'fixed-payload-profile-v1';cores=json.loads((profile/'run-manifest.json').read_text())
workerReceipt=repo/'bin/.local/benchmarks/definition-cost/operations-boundaries-v1';workerResult=json.loads((workerReceipt/'result.json').read_text());worker=dll=workerReceipt/'worker-build/bin/FreeFlight.Roslyn/release/FreeFlight.Roslyn.dll'
cpuObserverEnabled=os.environ.get('FREEFLIGHT_CONTEXT_CPU')=='1'
label=os.environ['FREEFLIGHT_CONTEXT_LABEL'];assert label and all(c.isalnum() or c in '-_' for c in label)
out=receipt/label;out.mkdir(exist_ok=False)
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(name,v):(out/name).write_text(json.dumps(v,indent=2)+'\n')
assert prepared['status']==workerResult['status']=='passed';assert sha(dll)==workerResult['workerSha256'];assert json.loads((profile/'result.json').read_text())['status']=='passed'
for v in ['baseline','candidate']:
 assert sha(Path(cores['binaries'][v]['path']))==cores['binaries'][v]['sha256']
 assert '100% tests passed' in (profile/(v+'-qualification.log')).read_text()
for name in ['test_worker.py.log','test_trusted.py.log']:assert_clean_worker_log(workerReceipt/name)
config=json.loads((repo/'bin/.local/benchmarks/trusted/background-cooperative-v4/provenance.json').read_text());fixture=dict(config['fixtures']['5845']);root=Path(fixture['root']).resolve();fixture['root']=str(root);queries,check=trusted.workload(fixture,5845)
assert config['variants']['candidate']['sourceHashes']['workers/roslyn/Program.cs']=='2a2bb9e4e0f0f17ad5d1e53b9c69262905398b691221121b9d63397ebdf99484'
for name,h in fixture['hashes'].items():assert sha(root/name)==h
plan=[('sham','baseline','baseline'),('source','candidate','candidate'),('source','baseline','baseline'),('sham','candidate','baseline'),('sham','candidate','baseline'),('source','baseline','baseline'),('source','candidate','candidate'),('sham','baseline','baseline')]
cpuObserver=None
if cpuObserverEnabled:
 from context_cpu_prepare import prepare
 dll,cpuObserver=prepare(repo,out,workerReceipt,config)
 plan=[('source','baseline','baseline'),('source','candidate','candidate'),('source','candidate','candidate'),('source','baseline','baseline')]
env={k:os.environ[k] for k in ['PATH','SystemRoot','WINDIR','TEMP','TMP','TMPDIR','LANG','LC_ALL'] if k in os.environ};env.update(DOTNET_ROOT=str(Path(config['dotnet']).parent),DOTNET_CLI_TELEMETRY_OPTOUT='1',DOTNET_EnableDiagnostics='0',DOTNET_GENERATE_ASPNET_CERTIFICATE='false',DOTNET_SKIP_FIRST_TIME_EXPERIENCE='1')
workerCommand=[config['dotnet'],str(dll),'--incremental-validation','--background-recovery']
manifest=dict(status='planned',plan=[dict(index=i,cohort=c,label=v,actualCore=a,firstPolicy='round' if i%2==0 else 'equal-gap') for i,(c,v,a) in enumerate(plan)],policies=dict(round=dict(minimumRoundSeconds=.1),equalGap=dict(targetClientReturnToNextStartSeconds=.025)),warmupSeconds=5,blocks=8,roundsPerBlock=8,acclimationRoundsPerBlock=4,measuredRoundsPerBlock=4,methods=[m for m,a in queries],design=[0,1,3,2],expectedMeasuredChecks=128*len(plan),expectedAcclimationChecks=128*len(plan),cpuObserver=cpuObserver,workerCommand=workerCommand,workerSha256=sha(dll),cores=cores['binaries'],fixture=fixture,environment=env,sourceReceiptHashes={str(p):sha(p) for p in [receipt/'manifest.json',profile/'run-manifest.json',profile/'result.json',workerReceipt/'result.json']},adapterSha256=sha(Path(__file__)),limitations=['Diagnostic intervention, not ordinary performance acceptance or a production optimization.','A/A labels use identical binary and configuration; changing config file path is not a different policy.','No CPU-frequency, scheduler, thermal or native allocator measurement.','Core thread CPU and worker wall stages have observer overhead; scopes overlap.','Both cohorts, all blocks, acclimation, warmup and adverse results retained; no post-hoc exclusion.'])
save('run-manifest.json',manifest)
for p in [Path(__file__),Path(__file__).with_name('context_cpu_prepare.py'),repo/'workflows/benchmark.trusted/assets/native_profile.py',Path(client.__file__)]:shutil.copy2(p,out/p.name if p.name!='measure.py' else out/'client-source.py')
records=[];oracle=None;configHash=None
try:
 for index,(cohort,variant,actual) in enumerate(plan):
  directory=out/f'{index}-{cohort}-{variant}';directory.mkdir();s=client.Session(root,directory,engines={'csharp':workerCommand},configuration={'trustedRoots':[str(root)],'csharp':{'project':fixture['project']}},sample_memory=False,command=[cores['binaries'][actual]['path'],'--config',str(directory/'freeflight.json')],environment=env,working_directory=root)
  row=dict(index=index,cohort=cohort,variant=variant,actualCore=actual,samples=[],rounds=[]);lastEnd=None;lastMethod=None
  thisHash=sha(directory/'freeflight.json')
  if configHash is None:configHash=thisHash
  assert thisHash==configHash,'Startup policy changed across labels'
  row['startupConfigSha256']=thisHash
  def call(method,args):
   global lastEnd,lastMethod
   start=time.perf_counter_ns();gap=(start-lastEnd)/1e6 if lastEnd else None
   value=s.request('tools/call',{'name':'semantic.query','arguments':{'root':str(root),'language':'csharp','operation':method,'arguments':args}});end=time.perf_counter_ns()
   sample=dict(id=s.sequence,method=method,previousMethod=lastMethod,requestStartNs=start,clientReturnNs=end,gapMs=gap,client=dict(totalMs=(end-start)/1e6,**s.last_request_profile))
   lastEnd=end;lastMethod=method
   semantic=json.loads(value['content'][0]['text']);assert len(value['content'])==1 and value['content'][0]['type']=='text';assert value['structuredContent']==(semantic if isinstance(semantic,dict) else {'items':semantic})
   assert value['resultType']=='complete' and 'io.modelcontextprotocol/serverInfo' in value['_meta'];check(method,semantic)
   if oracle is not None:assert semantic==oracle[method]
   sample['verificationMs']=(time.perf_counter_ns()-end)/1e6
   return semantic,sample
  def cycle(policy,phase,roundIndex,block=None,blockRound=None):
   began=time.perf_counter_ns()
   for ordinal,i in enumerate([0,1,3,2]):
    method,args=queries[(i+roundIndex)%4];sleepStart=time.perf_counter_ns();requested=0
    if policy=='equal-gap' and lastEnd is not None:
     requested=max(0,(lastEnd+25_000_000-sleepStart)/1e9);time.sleep(requested)
    actualSleep=(time.perf_counter_ns()-sleepStart)/1e6
    _,sample=call(method,args);sample.update(policy=policy,phase=phase,round=roundIndex,block=block,blockRound=blockRound,ordinal=ordinal,requestedQuerySleepMs=requested*1000,actualQuerySleepMs=actualSleep,blockBoundaryCarryover=blockRound==0 and ordinal==0)
    row['samples'].append(sample)
   beforeSleep=time.perf_counter_ns();requested=max(0,.1-(beforeSleep-began)/1e9) if policy=='round' else 0
   if requested:time.sleep(requested)
   row['rounds'].append(dict(policy=policy,phase=phase,round=roundIndex,block=block,blockRound=blockRound,activeMs=(beforeSleep-began)/1e6,requestedRoundSleepMs=requested*1000,actualRoundSleepMs=(time.perf_counter_ns()-beforeSleep)/1e6))
  try:
   caps=s.request('tools/call',{'name':'engine.capabilities','arguments':{'root':str(root),'language':'csharp'}})['structuredContent'];assert caps['analysis']['files']==5845
   current={method:call(method,args)[0] for method,args in queries}
   if oracle is None:oracle=current;save('oracle.json',oracle)
   assert current==oracle
   row['initialOracleChecks']=4
   first='round' if index%2==0 else 'equal-gap';second='equal-gap' if first=='round' else 'round'
   began=time.monotonic();warmRound=0
   while time.monotonic()-began<5:cycle(first,'warmup',warmRound);warmRound+=1
   for block in range(8):
    policy=first if block%2==0 else second
    for blockRound in range(8):cycle(policy,'acclimation' if blockRound<4 else 'measured',block*8+blockRound,block,blockRound)
  finally:s.close()
  logs=(directory/'server.stderr.log').read_text();assert 'Unhandled exception' not in logs
  core={};worker={}
  for line in logs.splitlines():
   for prefix,mapping in [('CORE_PROFILE ',core),('DEFINITION_COST ',worker)]:
    if line.startswith(prefix):
     value=json.loads(line[len(prefix):]);key=str(value['id']);assert key not in mapping;mapping[key]=value
  for sample in row['samples']:
   c=core[str(sample['id'])];assert len(c['workerIds'])==1;w=worker[str(c['workerIds'][0])];assert w['method']==sample['method'];sample.update(core=c,worker=w,outsideInvokeMs=sample['client']['totalMs']-w['stages']['invoke'])
   counts=w['counters'];assert counts.get('readBytes',0)==4096*counts.get('readFiles',0)
   if sample['method']!='workspaceSymbols':assert counts['readFiles']>=1
   assert sample['outsideInvokeMs']>=0
  records.append(row);save('samples.json',records);print(index,cohort,variant,'two cadences, IDs, exact dual forms and fresh reads passed',flush=True)
 for name,h in fixture['hashes'].items():assert sha(root/name)==h
 save('collection.json',dict(status='passed',processes=len(records),measuredChecks=sum(x['phase']=='measured' for r in records for x in r['samples']),acclimationChecks=sum(x['phase']=='acclimation' for r in records for x in r['samples']),warmupChecks=sum(x['phase']=='warmup' for r in records for x in r['samples']),initialOracleChecks=4*len(plan),configurationSha256=configHash,scope='Predefined diagnostic, not acceptance timing. All samples retained; sleep excluded from request time; verification recorded separately.'))
except Exception as error:
 save('failure.json',dict(status='failed',error=repr(error),completedProcesses=len(records)));raise
