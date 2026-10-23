# SPDX-License-Identifier: Apache-2.0
"""Baseline-only ordinary control; all orders, pacing policies and sessions retained."""
import gc,hashlib,importlib.util,itertools,json,os,shutil,sys,time
from pathlib import Path
repo=Path.cwd();sys.path.insert(0,str(repo/'workflows/benchmark.trusted/assets'));import run as trusted
spec=importlib.util.spec_from_file_location('client',repo/'workflows/benchmark/assets/measure.py');client=importlib.util.module_from_spec(spec);spec.loader.exec_module(client)
prepared=repo/'bin/.local/benchmarks/response-copies/json-moves-v2';p=json.loads((prepared/'manifest.json').read_text());assert p['status']=='passed'
sha=lambda path:hashlib.sha256(path.read_bytes()).hexdigest()
label=os.environ['FREEFLIGHT_REFERENCE_ATTRIBUTION_LABEL'];assert label and all(c.isalnum() or c in '-_' for c in label)
out=repo/'bin/.local/benchmarks/reference-context'/label;out.mkdir(parents=True,exist_ok=False)
def save(name,value):(out/name).write_text(json.dumps(value,indent=2)+'\n')
base=p['variants']['baseline'];worker=p['worker'];assert sha(Path(base['binary']))==base['binarySha256'] and sha(Path(worker['dll']))==worker['dllSha256']
assert sha(prepared/'baseline-qualification.log')==base['qualificationSha256'] and '100% tests passed' in (prepared/'baseline-qualification.log').read_text()
assert b'CORE_PROFILE ' not in Path(base['binary']).read_bytes()
assert worker['sourceHashes']['workers/roslyn/Program.cs']=='2a2bb9e4e0f0f17ad5d1e53b9c69262905398b691221121b9d63397ebdf99484'
fixture=dict(p['fixtures']['5845']);root=Path(fixture['root']).resolve();fixture['root']=str(root)
for name,h in fixture['hashes'].items():assert sha(root/name)==h
queries,check=trusted.workload(fixture,5845);methods=[m for m,args in queries]
originalSession=client.Session;originalCallbacks=list(gc.callbacks)
from native_profile import install_client
source=repo/'bin/.local/benchmarks/reference-context/baseline-position-v1';sourceRows=json.loads((source/'samples.json').read_text())
plan=[dict(session=session,observer='ordinary' if session in [0,3] else 'probe',blocks=[dict(block=b,arm=('immediate' if session%2==0 else 'wait-before') if b in [0,3,4,7] else ('wait-before' if session%2==0 else 'immediate')) for b in range(8)]) for session in range(4)]
env={k:os.environ[k] for k in ['PATH','SystemRoot','WINDIR','TEMP','TMP','TMPDIR','LANG','LC_ALL'] if k in os.environ};env.update(DOTNET_ROOT=str(Path(p['dotnet']).parent),DOTNET_CLI_TELEMETRY_OPTOUT='1',DOTNET_EnableDiagnostics='0',DOTNET_GENERATE_ASPNET_CERTIFICATE='false',DOTNET_SKIP_FIRST_TIME_EXPERIENCE='1')
drivers={'driver.py':Path(__file__),'audit.py':Path(__file__).with_name('attribution_audit.py'),'client-source.py':Path(client.__file__),'trusted-source.py':Path(trusted.__file__),'native_profile.py':repo/'workflows/benchmark.trusted/assets/native_profile.py'}
oraclePath=source/'oracle.json';oracle=json.loads(oraclePath.read_text())
manifest=dict(status='planned',date='2026-10-23',plan=plan,methods=methods,order=[0,2,1,3],fixedSlotsMs={'symbols':0,'definition':100,'workspaceSymbols':150},cycleMs=250,referenceGapFloorMs=25,warmupCycles=24,acclimationCyclesPerBlock=4,measuredCyclesPerBlock=16,expectedMeasuredChecks=2048,expectedAcclimationChecks=512,expectedWarmupChecks=384,fixture=fixture,core=dict(path=base['binary'],sha256=base['binarySha256']),workerCommand=[p['dotnet'],worker['dll'],*p['workerArgs']],workerSha256=worker['dllSha256'],environment=env,oracleSource=str(oraclePath),oracleSha256=sha(oraclePath),preparedManifestSha256=sha(prepared/'manifest.json'),sourceReceiptHashes={n:sha(source/n) for n in ['run-manifest.json','samples.json','result.json','causal-review.json']},retainedAllPhaseBounds={method:{k:max(x[k] for row in sourceRows for x in row['samples'] if x['method']==method) for k in ['ms','verificationMs']} for method in methods},driverHashes={n:sha(path) for n,path in drivers.items()},analysisPlan=['Four unchanged baseline serial processes,8counterbalanced blocks/session,16measured+4acclimation cycles/block,24fixedwarmupcycles.','Fixed symbols→references→definition→search order. Reference immediate after symbols+verification or25msreturn-to-startfloor; all other scheduled starts/cycle anchors identical across arms.','Absolute250ms cycles, definition100ms/search150ms slots chosen conservatively from retained all-phase bounds. No busy work, dummy requests, settings or recovery changes.','Retain all phases/deadline misses. Overdue calls run once with recorded lateness, no anchor rebasing, omissions, replacement or timing-based selection; any fixed-slot readiness overrun makes matched-cadence interpretation inconclusive.','Report every session and four adjacent block pairs; ratios wait-before/immediate; actual scheduled start offsets/periods and gaps remain. No hardware/GC/cache attribution.'],limitations=['Intended downstream request starts/cycle rate held fixed; actual wake jitter and service variation measured, not assumed identical.','Client return gap is not worker idle duration; local wait relocation can change state/history. Ordinary timing is not worker CPU/fresh-byte accounting.','One fixed position1 predecessor(symbols), synthetic5845graph macOSSDK11; no overall optimization acceptance.'])
profile=prepared/'fixed-payload-profile-v1';cpu=prepared/'pacing-worker-cpu-v1'
profileManifest=json.loads((profile/'run-manifest.json').read_text());cpuMetadata=json.loads((cpu/'cpu-observer.json').read_text())
probeCore=profileManifest['binaries']['baseline'];probeDll=cpu/'cpu-worker-build/bin/FreeFlight.Roslyn/release/FreeFlight.Roslyn.dll'
assert sha(Path(probeCore['path']))==probeCore['sha256'] and sha(probeDll)==cpuMetadata['workerSha256']
for name,h in profileManifest['sourceHashes']['baseline'].items():assert sha(profile/'baseline-source'/name)==h
assert sha(cpu/'cpu-worker-source/workers/roslyn/Program.cs')==cpuMetadata['programSha256']
assert cpuMetadata['status']=='passed' and cpuMetadata['calibration']['status']=='passed'
for test,h in cpuMetadata['qualificationHashes'].items():
 assert sha(cpu/(test+'.log'))==h and 'Unhandled exception' not in (cpu/(test+'.log')).read_text()
assert '100% tests passed' in (profile/'baseline-qualification.log').read_text()
proofs=[profile/'run-manifest.json',profile/'result.json',profile/'baseline-qualification.log',cpu/'cpu-observer.json',cpu/'clock-abi.json',cpu/'clock-calibration.json',cpu/'test_worker.py.log',cpu/'test_trusted.py.log',source.parent/'baseline-wait-placement-v1/run-manifest.json',source.parent/'baseline-wait-placement-v1/result.json']
manifest.update(observers={'ordinary':dict(core=manifest['core'],workerCommand=manifest['workerCommand'],workerSha256=manifest['workerSha256']),'probe':dict(core=probeCore,workerCommand=[p['dotnet'],str(probeDll),*p['workerArgs']],workerSha256=cpuMetadata['workerSha256'])},qualificationHashes={str(path):sha(path) for path in proofs},ordinarySourceDriverSha256=sha(Path(__file__).with_name('wait.py')),analysisPlan=['Four baseline-only serial processes:ordinary/probe/probe/ordinary; each mode has both incoming wait orders. Two processes/mode, not mode equivalence qualification.','Same250ms cycle/slots/order/blocks/phasecounts as ordinary wait-placement control; exact frozen oracle/dual content and all records retained.','Descriptive reproduction gate: wait-before reference session mean and median > immediate in both ordinary and both probe sessions; retain every block-pair direction. If gate fails or scheduled readiness overruns occur, no transferred attribution or expanded matrix.','Reference per-request wall partition: clientTotal=invoke+boundaryResidual; invoke=refresh+sum(text,syntax,model,findSymbol,findReferences,referenceRender)+invokeResidual. Arithmetic means/deltas preserve identities.','pathCheck aggregates within and outside refresh; report separately without adding to refresh. openHandle/readHash are refresh children. invokeResidual includes unmeasured path checks/bookkeeping; boundaryResidual is not pure transport.','Worker CPU covers all worker threads/background/GC during invoke, not foreground-only CPU/instructions. No CPU subtraction from wall. All timer overhead/residual scopes remain.','Client GC callback/class restored after each probe before ordinary; common security policy identical, configs per observer. No source edits, candidate acceptance or Glider expansion.'],limitations=manifest['limitations']+['Probe changes core/worker/client observers and logging. Reproduction supports directional localization only; two processes/mode do not quantify or rule out observer interactions.','No claim of pure transport or disjoint global pathCheck. Raw logs/ID joins and mean partitions retained; stage medians do not add.'])
manifest['designReviewSha256']=sha(repo/'bin/.local/benchmarks/reference-context/attribution-review-v1.json')
save('run-manifest.json',manifest)
for name,path in drivers.items():shutil.copy2(path,out/name)
shutil.copy2(oraclePath,out/'oracle.json');shutil.copy2(source/'causal-review.json',out/'causal-review.json');shutil.copy2(repo/'bin/.local/benchmarks/reference-context/attribution-review-v1.json',out/'design-review.json')
rows=[];configurationHashes={};commonPolicy=None
try:
 for entry in plan:
  session=entry['session'];mode=entry['observer'];observation=manifest['observers'][mode];directory=out/str(session);directory.mkdir()
  assert gc.callbacks==originalCallbacks;client.Session=originalSession
  if mode=='probe':install_client(client)
  s=client.Session(root,directory,engines={'csharp':observation['workerCommand']},configuration={'trustedRoots':[str(root)],'csharp':{'project':fixture['project']}},sample_memory=False,command=[observation['core']['path'],'--config',str(directory/'freeflight.json')],environment=env,working_directory=root)
  row=dict(session=session,observer=mode,samples=[]);lastEnd=None;lastMethod=None
  configHash=sha(directory/'freeflight.json')
  configurationHashes.setdefault(mode,configHash);assert configHash==configurationHashes[mode];row['configurationSha256']=configHash
  policy=json.loads((directory/'freeflight.json').read_text());assert policy.pop('engines')=={'csharp':observation['workerCommand']}
  if commonPolicy is None:commonPolicy=policy
  assert policy==commonPolicy
  def call(method,args,target=None,fixed=False):
   global lastEnd,lastMethod
   ready=time.perf_counter_ns();target=ready if target is None else target;requested=max(0,(target-ready)/1e9)
   if requested:time.sleep(requested)
   started=time.perf_counter_ns();gap=(started-lastEnd)/1e6 if lastEnd is not None else None
   result=s.request('tools/call',{'name':'semantic.query','arguments':{'root':str(root),'language':'csharp','operation':method,'arguments':args}});ended=time.perf_counter_ns()
   sample=dict(id=s.sequence,method=method,previousMethod=lastMethod,requestStartNs=started,clientReturnNs=ended,ms=(ended-started)/1e6,gapMs=gap,readyNs=ready,targetStartNs=target,fixedSlot=fixed,requestedSleepMs=requested*1000,actualWaitMs=(started-ready)/1e6,fixedSlotOverrunMs=max(0,(ready-target)/1e6) if fixed else 0,wakeLatenessMs=(started-target)/1e6)
   if mode=='probe':sample['clientProfile']=dict(s.last_request_profile)
   lastEnd=ended;lastMethod=method
   assert len(result['content'])==1 and result['content'][0]['type']=='text'
   semantic=json.loads(result['content'][0]['text']);assert result['structuredContent']==(semantic if isinstance(semantic,dict) else {'items':semantic})
   assert result['resultType']=='complete' and 'io.modelcontextprotocol/serverInfo' in result['_meta'];check(method,semantic);assert semantic==oracle[method]
   sample['verificationMs']=(time.perf_counter_ns()-ended)/1e6
   return sample
  try:
   caps=s.request('tools/call',{'name':'engine.capabilities','arguments':{'root':str(root),'language':'csharp'}})['structuredContent'];assert caps['analysis']['files']==5845
   for method,args in queries:call(method,args)
   row['initialOracleChecks']=4;origin=time.perf_counter_ns()+20_000_000;row['originNs']=origin;tick=0
   def cycle(phase,block,number,arm):
    global tick
    anchor=origin+tick*250_000_000
    for ordinal,i in enumerate([0,2,1,3]):
     method,args=queries[i];fixed=method!='references'
     target=anchor+int(manifest['fixedSlotsMs'][method]*1e6) if fixed else (lastEnd+25_000_000 if arm=='wait-before' else None)
     sample=call(method,args,target,fixed);sample.update(phase=phase,block=block,cycle=number,tick=tick,anchorNs=anchor,ordinal=ordinal,arm=arm);row['samples'].append(sample)
    tick+=1
   for number in range(24):cycle('warmup',-1,number,'immediate')
   for b in entry['blocks']:
    for number in range(4):cycle('acclimation',b['block'],number,b['arm'])
    for number in range(16):cycle('measured',b['block'],number,b['arm'])
  finally:
   s.close();gc.callbacks[:]=originalCallbacks;client.Session=originalSession
  assert s.process.returncode==0
  log=(directory/'server.stderr.log').read_text();assert 'Unhandled exception' not in log
  if mode=='ordinary':assert all(marker not in log for marker in ['CORE_PROFILE ','DEFINITION_COST '])
  else:
   core={};workerLogs={}
   for line in log.splitlines():
    for prefix,mapping in [('CORE_PROFILE ',core),('DEFINITION_COST ',workerLogs)]:
     if line.startswith(prefix):
      value=json.loads(line[len(prefix):]);key=str(value['id']);assert key not in mapping;mapping[key]=value
   for x in row['samples']:
    c=core[str(x['id'])];assert len(c['workerIds'])==1;w=workerLogs[str(c['workerIds'][0])];assert w['method']==x['method']
    x.update(core=c,worker=w,boundaryResidualMs=x['ms']-w['stages']['invoke'])
    count=w['counters'];assert count.get('readBytes',0)==4096*count.get('readFiles',0)
    assert count.get('readFiles',0)==(0 if x['method']=='workspaceSymbols' else 1) and count.get('fullRecoveries',0)==0
    if x['method']=='references':
     stages=w['stages'];semantic=sum(stages[k] for k in ['text','syntax','model','findSymbol','findReferences','referenceRender'])
     x.update(semanticStagesMs=semantic,invokeResidualMs=stages['invoke']-stages['refresh']-semantic)


  rows.append(row);save('samples.json',rows);print('attribution session',session,mode,'512measured+128acclimation+96warmup exact checks passed',flush=True)
 for name,h in fixture['hashes'].items():assert sha(root/name)==h
 for name,path in drivers.items():assert sha(path)==manifest['driverHashes'][name]
 assert sha(Path(base['binary']))==base['binarySha256'] and sha(Path(worker['dll']))==worker['dllSha256']
 assert sha(prepared/'manifest.json')==manifest['preparedManifestSha256'] and sha(oraclePath)==manifest['oracleSha256']
 for observer in manifest['observers'].values():assert sha(Path(observer['core']['path']))==observer['core']['sha256'] and sha(Path(observer['workerCommand'][1]))==observer['workerSha256']
 for name,h in manifest['qualificationHashes'].items():assert sha(Path(name))==h
 assert gc.callbacks==originalCallbacks and client.Session is originalSession
 save('collection.json',dict(status='passed',processes=4,measuredChecks=2048,acclimationChecks=512,warmupChecks=384,initialOracleChecks=16,configurationHashes=configurationHashes,commonPolicy=commonPolicy,fixedSlotReadinessOverruns=sum(x['fixedSlotOverrunMs']>0 for row in rows for x in row['samples'])))
except Exception as error:
 if 'row' in globals():save('partial-session.json',row)
 save('failure.json',dict(status='failed',error=repr(error),completedProcesses=len(rows)));raise
