# SPDX-License-Identifier: Apache-2.0
"""Baseline-only ordinary control; all orders, pacing policies and sessions retained."""
import hashlib,importlib.util,itertools,json,os,shutil,sys,time
from pathlib import Path
repo=Path.cwd();sys.path.insert(0,str(repo/'workflows/benchmark.trusted/assets'));import run as trusted
spec=importlib.util.spec_from_file_location('client',repo/'workflows/benchmark/assets/measure.py');client=importlib.util.module_from_spec(spec);spec.loader.exec_module(client)
prepared=repo/'bin/.local/benchmarks/response-copies/json-moves-v2';p=json.loads((prepared/'manifest.json').read_text());assert p['status']=='passed'
sha=lambda path:hashlib.sha256(path.read_bytes()).hexdigest()
label=os.environ['FREEFLIGHT_REFERENCE_CONTEXT_LABEL'];assert label and all(c.isalnum() or c in '-_' for c in label)
out=repo/'bin/.local/benchmarks/reference-context'/label;out.mkdir(parents=True,exist_ok=False)
def save(name,value):(out/name).write_text(json.dumps(value,indent=2)+'\n')
base=p['variants']['baseline'];worker=p['worker'];assert sha(Path(base['binary']))==base['binarySha256'] and sha(Path(worker['dll']))==worker['dllSha256']
assert sha(prepared/'baseline-qualification.log')==base['qualificationSha256'] and '100% tests passed' in (prepared/'baseline-qualification.log').read_text()
assert b'CORE_PROFILE ' not in Path(base['binary']).read_bytes()
assert worker['sourceHashes']['workers/roslyn/Program.cs']=='2a2bb9e4e0f0f17ad5d1e53b9c69262905398b691221121b9d63397ebdf99484'
fixture=dict(p['fixtures']['5845']);root=Path(fixture['root']).resolve();fixture['root']=str(root)
for name,h in fixture['hashes'].items():assert sha(root/name)==h
queries,check=trusted.workload(fixture,5845);methods=[m for m,args in queries]
bases=[(0,*tail) for tail in itertools.permutations([1,2,3])]
def orders(session,block):
 # Each consecutive group of four balances every method/ordinal, all24 exactly once.
 pair=block//2
 groups=bases[(session+pair)%6:]+bases[:(session+pair)%6]
 if (session+pair)%2:groups=list(reversed(groups))
 return [[(i+shift+session+pair)%4 for i in base] for base in groups for shift in range(4)]
plan=[]
for session in range(4):
 first='round' if session in [0,3] else 'gap-floor'
 sequence=[first if i in [0,3,4,7] else ('gap-floor' if first=='round' else 'round') for i in range(8)]
 plan.append(dict(session=session,blocks=[dict(block=b,policy=policy,orders=orders(session,b),acclimationOrders=[[(i+j+session+b)%4 for i in [0,1,3,2]] for j in range(4)]) for b,policy in enumerate(sequence)]))
env={k:os.environ[k] for k in ['PATH','SystemRoot','WINDIR','TEMP','TMP','TMPDIR','LANG','LC_ALL'] if k in os.environ};env.update(DOTNET_ROOT=str(Path(p['dotnet']).parent),DOTNET_CLI_TELEMETRY_OPTOUT='1',DOTNET_EnableDiagnostics='0',DOTNET_GENERATE_ASPNET_CERTIFICATE='false',DOTNET_SKIP_FIRST_TIME_EXPERIENCE='1')
drivers={'driver.py':Path(__file__),'audit.py':Path(__file__).with_name('audit.py'),'client-source.py':Path(client.__file__),'trusted-source.py':Path(trusted.__file__)}
manifest=dict(status='planned',date='2026-10-23',plan=plan,methods=methods,fixture=fixture,core=dict(path=base['binary'],sha256=base['binarySha256']),workerCommand=[p['dotnet'],worker['dll'],*p['workerArgs']],workerSha256=worker['dllSha256'],environment=env,warmupSeconds=5,minimumRoundMs=100,gapFloorMs=25,expectedMeasuredChecks=3072,expectedAcclimationChecks=512,preparedManifestSha256=sha(prepared/'manifest.json'),driverHashes={n:sha(path) for n,path in drivers.items()},analysisPlan=['Four baseline-only serial processes; all queries, rounds, positions and sessions retained without exclusions or replacement.','Eight24-permutation blocks/process;4acclimation rounds/block excluded a priori, all retained. Four blocks/policy; complement PQQPPQQP session sequences.','Report every session, policy, block and all methods; references position-by-predecessor within positions1..3, position0 cross-round carryover separately.','25ms return-to-start floor and100ms round floor use max-of-deadlines scheduling; realized gaps/periods retained. This changes workload rate, not isolated idle magnitude.','Pair blocks(0,1),(2,3),(4,5),(6,7) with identical measured order; report every pair, session and all methods. Ratios gap-floor/round; predecessor and position marginal contrasts conditioned on policy. No gap normalization, posthoc thresholds or hardware causality.','No runtime changes, candidate reruns, Glider expansion or winner claim.'],limitations=['Ordinary frozen94 binaries; outer timestamps/exact verification are observer work, no stage/CPU/RSS/event instrumentation.','Cross-round predecessor at position0 depends on the deterministic schedule; not a factorial matched predecessor contrast.','Other than immediate predecessor, earlier operations and elapsed round work still vary; marginal effects do not uniquely identify CPU/GC/scheduler/cache causality.'])
save('run-manifest.json',manifest)
for name,path in drivers.items():shutil.copy2(path,out/name)
oraclePath=prepared/'ordinary-matched-gaps-v1/oracle.json'
oracle=json.loads(oraclePath.read_text());manifest['oracleSha256']=sha(oraclePath);manifest['oracleSource']=str(oraclePath)
reviewPath=repo/'bin/.local/benchmarks/reference-context/design-review-v1.json';manifest['designReviewSha256']=sha(reviewPath)
save('run-manifest.json',manifest);shutil.copy2(oraclePath,out/'oracle.json');shutil.copy2(reviewPath,out/'design-review.json')
rows=[];configurationHash=None
try:
 for entry in plan:
  session=entry['session'];directory=out/str(session);directory.mkdir()
  s=client.Session(root,directory,engines={'csharp':manifest['workerCommand']},configuration={'trustedRoots':[str(root)],'csharp':{'project':fixture['project']}},sample_memory=False,command=[base['binary'],'--config',str(directory/'freeflight.json')],environment=env,working_directory=root)
  row=dict(session=session,samples=[],rounds=[]);lastEnd=None;lastMethod=None
  configHash=sha(directory/'freeflight.json')
  if configurationHash is None:configurationHash=configHash
  assert configHash==configurationHash;row['configurationSha256']=configHash
  def call(method,args,policy):
   global lastEnd,lastMethod
   beforeWait=time.perf_counter_ns();requested=max(0,.025-(beforeWait-lastEnd)/1e9) if lastEnd is not None and policy=='gap-floor' else 0
   if requested:time.sleep(requested)
   started=time.perf_counter_ns();gap=(started-lastEnd)/1e6 if lastEnd is not None else None
   result=s.request('tools/call',{'name':'semantic.query','arguments':{'root':str(root),'language':'csharp','operation':method,'arguments':args}});ended=time.perf_counter_ns()
   sample=dict(id=s.sequence,method=method,previousMethod=lastMethod,requestStartNs=started,clientReturnNs=ended,ms=(ended-started)/1e6,gapMs=gap,requestedGapSleepMs=requested*1000,actualGapWaitMs=(started-beforeWait)/1e6)
   lastEnd=ended;lastMethod=method
   assert len(result['content'])==1 and result['content'][0]['type']=='text'
   semantic=json.loads(result['content'][0]['text']);assert result['structuredContent']==(semantic if isinstance(semantic,dict) else {'items':semantic})
   assert result['resultType']=='complete' and 'io.modelcontextprotocol/serverInfo' in result['_meta'];check(method,semantic)
   if oracle is not None:assert semantic==oracle[method]
   sample['verificationMs']=(time.perf_counter_ns()-ended)/1e6
   return semantic,sample
  def round_(order,phase,block,number,policy):
   began=time.perf_counter_ns()
   for ordinal,i in enumerate(order):
    method,args=queries[i];_,sample=call(method,args,policy)
    sample.update(phase=phase,block=block,round=number,ordinal=ordinal,policy=policy);row['samples'].append(sample)
   beforeSleep=time.perf_counter_ns();requested=max(0,.1-(beforeSleep-began)/1e9)
   if requested:time.sleep(requested)
   ended=time.perf_counter_ns()
   row['rounds'].append(dict(phase=phase,block=block,round=number,policy=policy,roundStartNs=began,activeMs=(beforeSleep-began)/1e6,requestedRoundSleepMs=requested*1000,actualRoundSleepMs=(ended-beforeSleep)/1e6,periodMs=(ended-began)/1e6))
  try:
   caps=s.request('tools/call',{'name':'engine.capabilities','arguments':{'root':str(root),'language':'csharp'}})['structuredContent'];assert caps['analysis']['files']==5845
   current={method:call(method,args,'round')[0] for method,args in queries}
   assert current==oracle;row['initialOracleChecks']=4
   start=time.monotonic();warm=0
   while time.monotonic()-start<5:
    round_([(i+warm)%4 for i in [0,1,3,2]],'warmup',-1,warm,'round');warm+=1
   for b in entry['blocks']:
    for number,order in enumerate(b['acclimationOrders']):round_(order,'acclimation',b['block'],number,b['policy'])
    for number,order in enumerate(b['orders']):round_(order,'measured',b['block'],number,b['policy'])
  finally:s.close()
  assert s.process.returncode==0
  text=(directory/'server.stderr.log').read_text();assert all(marker not in text for marker in ['Unhandled exception','CORE_PROFILE ','DEFINITION_COST '])
  rows.append(row);save('samples.json',rows);print('session',session,'768 measured +128 acclimation exact dual-content checks passed',flush=True)
 for name,h in fixture['hashes'].items():assert sha(root/name)==h
 for name,path in drivers.items():assert sha(path)==manifest['driverHashes'][name]
 assert sha(Path(base['binary']))==base['binarySha256'] and sha(Path(worker['dll']))==worker['dllSha256']
 assert sha(prepared/'manifest.json')==manifest['preparedManifestSha256'] and sha(oraclePath)==manifest['oracleSha256']
 save('collection.json',dict(status='passed',processes=4,measuredChecks=3072,acclimationChecks=512,warmupChecks=sum(x['phase']=='warmup' for r in rows for x in r['samples']),initialOracleChecks=16,configurationSha256=configurationHash))
except Exception as error:
 if 'row' in globals():save('partial-session.json',row)
 save('failure.json',dict(status='failed',error=repr(error),completedProcesses=len(rows)));raise
