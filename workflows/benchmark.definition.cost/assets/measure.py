# SPDX-License-Identifier: Apache-2.0
"""Correlated direct/MCP definition diagnostics, never ordinary acceptance timing."""
import hashlib,importlib.util,json,math,os,queue,shutil,statistics,subprocess,sys,threading,time
from pathlib import Path
repo=Path.cwd();assets=Path(__file__).parent;sys.path.insert(0,str(repo/'workflows/benchmark.trusted/assets'))
from native_profile import instrument_core,install_client,assert_clean_worker_log
from instrument import worker as instrument_worker, extended as instrument_extended, replay_search as instrument_replay
spec=importlib.util.spec_from_file_location('client',repo/'workflows/benchmark/assets/measure.py');client=importlib.util.module_from_spec(spec);spec.loader.exec_module(client);install_client(client)
receipt=repo/'bin/.local/benchmarks/trusted/background-cooperative-v4';config=json.loads((receipt/'provenance.json').read_text())
label=os.environ['FREEFLIGHT_DEFINITION_LABEL'];assert label and all(c.isalnum() or c in '-_' for c in label)
out=repo/'bin/.local/benchmarks/definition-cost'/label;out.mkdir(parents=True,exist_ok=False)
extended=os.environ.get('FREEFLIGHT_DEFINITION_EXTENDED')=='1'
replay=os.environ.get('FREEFLIGHT_DEFINITION_REPLAY_SEARCH')=='1'
assert not replay or extended
methods=['definition','references','workspaceSymbols','test.transport'] if extended else ['definition','test.transport']
if replay:methods=['definition','references','workspaceSymbols','test.replaySearch']
sessions=2 if extended else 3
intervals=[.1] if replay else [0,.1]
for p in assets.glob('*.py'):shutil.copy2(p,out/p.name)
(out/'driver-source').mkdir()
for p in [repo/'workflows/benchmark.trusted/assets/native_profile.py',repo/'workflows/benchmark/assets/measure.py']:shutil.copy2(p,out/'driver-source'/p.name)
def save(path,data):path.write_text(json.dumps(data,indent=2)+'\n')
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def command(args,name):
 with (out/name).open('w') as log:subprocess.run(args,stdout=log,stderr=subprocess.STDOUT,check=True)
source=out/'source';shutil.copytree(receipt/'candidate/source',source)
for name,h in config['variants']['candidate']['sourceHashes'].items():assert digest(source/name)==h
instrument_worker(source/'workers/roslyn/Program.cs')
if extended:instrument_extended(source/'workers/roslyn/Program.cs')
if replay:instrument_replay(source/'workers/roslyn/Program.cs')
command([config['dotnet'],'build',str(source/'workers/roslyn/FreeFlight.Roslyn.csproj'),'-c','Release','-p:RestoreLockedMode=true','--disable-build-servers','--artifacts-path',str(out/'worker-build')],'worker-build.log')
dll=out/'worker-build/bin/FreeFlight.Roslyn/release/FreeFlight.Roslyn.dll'
core=out/'core-source';core.mkdir();names=['CMakeLists.txt','README.md','LICENSE']+subprocess.check_output(['git','ls-tree','-r','--name-only','94eb420','src','include','tests'],text=True).splitlines()
for name in names:
 p=core/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(subprocess.check_output(['git','show','94eb420:'+name]))
instrument_core(core)
cmake='/Users/jamie/Documents/Codex/2026-10-19/task/toolchains/cmake-3.31.8-macos-universal/CMake.app/Contents/bin/cmake';build=out/'core-build'
for args,name in [([cmake,'-S',str(core),'-B',str(build),'-DCMAKE_BUILD_TYPE=Release','-DFETCHCONTENT_SOURCE_DIR_JSON='+str(repo/'bin/.local/build/_deps/json-src')],'core-configure.log'),([cmake,'--build',str(build),'--parallel','2'],'core-build.log'),([str(Path(cmake).with_name('ctest')),'--test-dir',str(build),'--output-on-failure'],'core-tests.log')]:command(args,name)
for test in ['test_worker.py','test_trusted.py']:
 command([sys.executable,'-B',str(repo/'workers/roslyn'/test),config['dotnet'],str(dll)],test+'.log')
 assert_clean_worker_log(out/(test+'.log'))
f=dict(config['fixtures']['5845']);root=Path(f['root']).resolve();f['root']=str(root)
sys.path.insert(0,str(repo/'workflows/benchmark.trusted/assets'));import run as trusted
queries,check=trusted.workload(f,5845);definition=dict(queries[1][1]);arguments=dict(queries);arguments['test.transport']=definition;arguments['test.replaySearch']=arguments['workspaceSymbols']
workerCommand=[config['dotnet'],str(dll),'--trusted-msbuild','--incremental-validation','--background-recovery']
env={k:os.environ[k] for k in ['PATH','SystemRoot','WINDIR','TEMP','TMP','TMPDIR','LANG','LC_ALL'] if k in os.environ}
env.update(DOTNET_ROOT=str(Path(config['dotnet']).parent),DOTNET_CLI_TELEMETRY_OPTOUT='1',DOTNET_EnableDiagnostics='0',DOTNET_GENERATE_ASPNET_CERTIFICATE='false',DOTNET_SKIP_FIRST_TIME_EXPERIENCE='1')
save(out/'run-manifest.json',dict(extended=extended,replaySearch=replay,methods=methods,sessions=sessions,rounds=40,intervals=intervals,sourceHashes=config['variants']['candidate']['sourceHashes'],workerCommand=workerCommand,environment=env,driverHashes={str(p.relative_to(repo)):digest(p) for p in [*assets.glob('*.py'),repo/'workflows/benchmark.trusted/assets/native_profile.py',repo/'workflows/benchmark/assets/measure.py']}))
records=[]
for interval in intervals:
 for session in range(sessions):
  for transport in (['direct','mcp'] if session%2==0 else ['mcp','direct']):
   name=f'{interval:g}-{session}-{transport}';directory=out/name;directory.mkdir();samples=[];process=None;s=None;log=None;seq=0
   if transport=='direct':
    log=(directory/'server.stderr.log').open('w');process=subprocess.Popen(workerCommand,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=log,text=True,cwd=root,env=env);q=queue.Queue()
    def read(p=process,replies=q):
     for line in p.stdout:replies.put((line,time.perf_counter_ns()))
     replies.put((None,time.perf_counter_ns()))
    threading.Thread(target=read,daemon=True).start()
    def call(method,**params):
     global seq
     seq+=1;start=time.perf_counter_ns();encoded=json.dumps(dict(id=seq,method=method,params=params))+'\n';serialized=time.perf_counter_ns();process.stdin.write(encoded);process.stdin.flush();written=time.perf_counter_ns();line,readAt=q.get(timeout=60);dequeued=time.perf_counter_ns();assert line is not None;r=json.loads(line);end=time.perf_counter_ns();assert r['id']==seq and 'result' in r,r
     return r['result'],dict(id=seq,totalMs=(end-start)/1e6,serializeMs=(serialized-start)/1e6,writeMs=(written-serialized)/1e6,waitUntilReadMs=(readAt-written)/1e6,readerQueueMs=(dequeued-readAt)/1e6,parseMs=(end-dequeued)/1e6,responseBytes=len(line.encode()))
   else:
    s=client.Session(root,directory,engines={'csharp':[x for x in workerCommand if x!='--trusted-msbuild']},configuration={'trustedRoots':[str(root)],'csharp':{'project':f['project']}},sample_memory=False,environment=env,command=[str(build/'freeflight'),'--config',str(directory/'freeflight.json')],working_directory=root)
    def call(method,**params):
     start=time.perf_counter_ns()
     if method=='open':r=s.request('tools/call',{'name':'engine.capabilities','arguments':{'root':str(root),'language':'csharp'}})['structuredContent']
     else:r,_=s.query('csharp',method,**params)
     return r,dict(totalMs=(time.perf_counter_ns()-start)/1e6,**s.last_request_profile)
   try:
    opened,_=call('open',root=str(root),project=f['project']);assert opened['files']==5845 if transport=='direct' else 'definition' in opened['operations']
    if replay:
     primed,_=call('workspaceSymbols',**arguments['workspaceSymbols']);check('workspaceSymbols',primed)
    started=time.monotonic();round=0;measured=0
    while time.monotonic()-started<5 or measured<40:
     steady=time.monotonic()-started>=5;roundStart=time.monotonic()
     phase=measured if steady else round
     selected=[methods[(i+phase)%4] for i in [0,1,3,2]] if extended else (methods if round%2==0 else list(reversed(methods)))
     for ordinal,method in enumerate(selected):
      result,timing=call(method,**arguments[method])
      if method!='test.transport':check('workspaceSymbols' if method=='test.replaySearch' else method,result)
      else:assert result=={'ok':True},result
      if steady:samples.append(dict(method=method,round=round,measuredRound=measured,ordinal=ordinal,client=timing,resultSha256=hashlib.sha256(json.dumps(result,sort_keys=True).encode()).hexdigest()))
     if steady:measured+=1
     round+=1;time.sleep(max(0,interval-(time.monotonic()-roundStart)))
   finally:
    if s:s.close()
    if process:
     process.stdin.close()
     try:process.wait(timeout=15)
     except subprocess.TimeoutExpired:process.kill();process.wait();raise
     log.close();assert process.returncode==0
   text=(directory/'server.stderr.log').read_text();assert 'Unhandled exception' not in text
   workerProfiles={};coreProfiles={}
   for line in text.splitlines():
    for prefix,mapping in [('DEFINITION_COST ',workerProfiles),('CORE_PROFILE ',coreProfiles)]:
     if prefix in line:
      row=json.loads(line.split(prefix,1)[1]);key=str(row['id']);assert key not in mapping;mapping[key]=row
   for sample in samples:
    ident=str(sample['client']['id'])
    if transport=='mcp':
     c=coreProfiles[ident];assert len(c['workerIds'])==1;sample['core']=c;ident=str(c['workerIds'][0])
    w=workerProfiles[ident];assert w['method']==sample['method'];sample['worker']=w
    # Per-request residuals; never subtract independently summarized medians.
    sample['outsideInvokeMs']=sample['client']['totalMs']-w['stages']['invoke']
   assert len(samples)==40*len(methods)
   if extended:
    for method in methods:
     assert all(sum(x['method']==method and x['ordinal']==position for x in samples)==10 for position in range(4))
    for x in samples:
     counts=x['worker']['counters']
     assert counts.get('readBytes',0)==4096*counts.get('readFiles',0)
     if x['method'] in ('definition','references'):assert counts['readFiles']>=1
     if x['method'] in ('test.transport','test.replaySearch'):assert counts=={}
   records.append(dict(name=name,transport=transport,interval=interval,session=session,samples=samples));save(out/'observations.json',records);print(name,len(samples),'joined responses passed',flush=True)
for relative,expected in f['hashes'].items():assert digest(root/relative)==expected
rows=[]
for transport in ['direct','mcp']:
 for interval in intervals:
  for method in methods:
   samples=[x for r in records if r['transport']==transport and r['interval']==interval for x in r['samples'] if x['method']==method];metrics={}
   for key in ['totalMs','serializeMs','writeMs','waitUntilReadMs','readerQueueMs','parseMs']:metrics['client.'+key]=trusted.stats([s['client'][key] for s in samples])
   for key in set().union(*(s['worker']['stages'] for s in samples)):metrics['worker.'+key]=trusted.stats([s['worker']['stages'].get(key,0) for s in samples])
   metrics['outsideInvoke']=trusted.stats([s['outsideInvokeMs'] for s in samples])
   if transport=='mcp':
    for key in set().union(*(s['core']['stages'] for s in samples)):metrics['core.'+key]=trusted.stats([s['core']['stages'].get(key,0) for s in samples])
   rows.append(dict(transport=transport,interval=interval,method=method,metrics=metrics))
save(out/'result.json',dict(status='passed',scope='Correlated instrumented diagnostic observations, not ordinary MCP or Glider acceptance timing; fixed-result operations are generated controls.',extended=extended,replaySearch=replay,methods=methods,sessions=sessions,intervals=intervals,rows=rows,sourceHashes=config['variants']['candidate']['sourceHashes'],workerSha256=digest(dll),coreSha256=digest(build/'freeflight'),workerEnvironment=env))
for p in assets.glob('*.py'):shutil.copy2(p,out/p.name)
