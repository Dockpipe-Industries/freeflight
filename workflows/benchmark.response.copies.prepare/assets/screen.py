# SPDX-License-Identifier: Apache-2.0
"""Ordinary matched MCP screens; exact dual forms and full semantic oracles."""
import collections,hashlib,importlib.util,json,os,shutil,statistics,sys,time
from pathlib import Path
repo=Path.cwd();sys.path.insert(0,str(repo/'workflows/benchmark.trusted/assets'));import run as trusted
spec=importlib.util.spec_from_file_location('client',repo/'workflows/benchmark/assets/measure.py');client=importlib.util.module_from_spec(spec);spec.loader.exec_module(client)
label=os.environ['FREEFLIGHT_RESPONSE_LABEL'];receipt=repo/'bin/.local/benchmarks/response-copies'/label
manifest=json.loads((receipt/'manifest.json').read_text());assert manifest['status']=='passed'
mode=os.environ.get('FREEFLIGHT_RESPONSE_MODE','all');assert mode in ('all','four')
runLabel=os.environ.get('FREEFLIGHT_RESPONSE_SCREEN',mode+'-operations-v1');assert runLabel and all(c.isalnum() or c in '-_' for c in runLabel)
out=receipt/runLabel;out.mkdir(exist_ok=False)
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(name,v):(out/name).write_text(json.dumps(v,indent=2)+'\n')
for v in manifest['variants'].values():assert sha(Path(v['binary']))==v['binarySha256']
assert sha(Path(manifest['worker']['dll']))==manifest['worker']['dllSha256']
assert sha(Path(manifest['workerReceipt'])/'provenance.json')==manifest['workerProvenanceSha256']
rounds=int(os.environ.get('FREEFLIGHT_RESPONSE_ROUNDS','48'));sessions=int(os.environ.get('FREEFLIGHT_RESPONSE_SESSIONS','2'));sizes=os.environ.get('FREEFLIGHT_RESPONSE_SIZES','433,5845' if mode=='all' else '5845').split(',')
assert sessions>=2 and rounds>=24 and rounds%(12 if mode=='all' else 4)==0 and set(sizes)<={'433','5845'}
env={k:os.environ[k] for k in ['PATH','SystemRoot','WINDIR','TEMP','TMP','TMPDIR','LANG','LC_ALL'] if k in os.environ}
env.update(DOTNET_ROOT=str(Path(manifest['dotnet']).parent),DOTNET_CLI_TELEMETRY_OPTOUT='1',DOTNET_EnableDiagnostics='0',DOTNET_GENERATE_ASPNET_CERTIFICATE='false',DOTNET_SKIP_FIRST_TIME_EXPERIENCE='1')
sequence=[]
for pair in range(sessions):sequence.extend(['baseline','candidate'] if pair%2==0 else ['candidate','baseline'])
save('run-manifest.json',dict(mode=mode,rounds=rounds,sessions=sessions,sizes=sizes,sequence=sequence,warmupSeconds=5,minimumRoundSeconds=.1,environment=env,preparedManifestSha256=sha(receipt/'manifest.json'),adapterSha256=sha(Path(__file__)),clientSha256=sha(Path(client.__file__))))
shutil.copy2(__file__,out/'adapter-source.py');shutil.copy2(client.__file__,out/'client-source.py')
rows=[];comparisons=[]
for size in sizes:
 frozen=manifest['fixtures'][size];f=dict(frozen);root=Path(f['root']).resolve();f['root']=str(root)
 for name,h in frozen['hashes'].items():assert sha(root/name)==h
 queries,check=trusted.workload(f,int(size))
 if mode=='all':
  target=queries[0][1]['file'];position=queries[1][1];line=Path(position['file']).read_text().splitlines()[0]
  queries += [('hover',position),('diagnostics',dict(file=position['file'])),('rename',dict(**position,newName='RenamedValue')),('implementations',position),('typeInfo',position),('signatureHelp',dict(file=position['file'],line=0,character=line.index('.Value(')+len('.Value('))),('callHierarchy',position),('typeHierarchy',dict(file=target,line=0,character=29))]
 names=[m for m,a in queries];n=len(names);design=[0,1,11,2,10,3,9,4,8,5,7,6] if n==12 else [0,1,3,2];oracle=None
 for index,variant in enumerate(sequence):
  directory=out/f'{size}-{index}-{variant}';directory.mkdir();s=client.Session(root,directory,engines={'csharp':[manifest['dotnet'],manifest['worker']['dll'],*manifest['workerArgs']]},configuration={'trustedRoots':[str(root)],'csharp':{'project':f['project']}},sample_memory=False,command=[manifest['variants'][variant]['binary'],'--config',str(directory/'freeflight.json')],environment=env,working_directory=root)
  row=dict(size=int(size),index=index,variant=variant,samples=[])
  def call(method,args):
   start=time.perf_counter_ns();result=s.request('tools/call',{'name':'semantic.query','arguments':{'root':str(root),'language':'csharp','operation':method,'arguments':args}});ms=(time.perf_counter_ns()-start)/1e6
   assert len(result['content'])==1 and result['content'][0]['type']=='text'
   value=json.loads(result['content'][0]['text']);structured=value if isinstance(value,dict) else {'items':value}
   assert result['structuredContent']==structured,(method,'dual content mismatch')
   assert result['resultType']=='complete' and 'io.modelcontextprotocol/serverInfo' in result['_meta']
   if method in ('symbols','definition','references','workspaceSymbols'):check(method,value)
   return value,ms
  try:
   caps=s.request('tools/call',{'name':'engine.capabilities','arguments':{'root':str(root),'language':'csharp'}})['structuredContent'];assert caps['analysis']['files']==int(size)
   current={method:call(method,args)[0] for method,args in queries}
   if oracle is None:oracle=current;save(size+'-oracle.json',oracle)
   assert current==oracle,(size,variant,'initial exact semantic oracle')
   start=time.monotonic();warmRound=0;measured=0
   while time.monotonic()-start<5 or measured<rounds:
    steady=time.monotonic()-start>=5;phase=measured if steady else warmRound;began=time.monotonic()
    for ordinal,i in enumerate(design):
     method,args=queries[(i+phase)%n];value,ms=call(method,args);assert value==oracle[method],(size,variant,method,'semantic mismatch')
     if steady:row['samples'].append(dict(method=method,ms=ms,measuredRound=measured,ordinal=ordinal,id=s.sequence))
    if steady:measured+=1
    warmRound+=1;time.sleep(max(0,.1-(time.monotonic()-began)))
  finally:s.close()
  assert 'Unhandled exception' not in (directory/'server.stderr.log').read_text()
  assert len(row['samples'])==rounds*n and len({x['id'] for x in row['samples']})==rounds*n
  positions=collections.Counter((x['method'],x['ordinal']) for x in row['samples']);assert len(positions)==n*n and set(positions.values())=={rounds//n}
  pairs=collections.Counter()
  for i in range(rounds):
   ordered=sorted((x for x in row['samples'] if x['measuredRound']==i),key=lambda x:x['ordinal']);pairs.update((a['method'],b['method']) for a,b in zip(ordered,ordered[1:]))
  assert len(pairs)==n*(n-1) and set(pairs.values())=={rounds//n}
  rows.append(row);save('samples.json',rows);print(size,index,variant,mode,'MCP exact dual-content/oracle passed',flush=True)
 for method in names:
  stats={v:[trusted.stats([x['ms'] for x in r['samples'] if x['method']==method]) for r in rows if r['size']==int(size) and r['variant']==v] for v in ['baseline','candidate']}
  comparisons.append(dict(size=int(size),method=method,stats=stats,medianRatio=statistics.median(x['median'] for x in stats['candidate'])/statistics.median(x['median'] for x in stats['baseline']),p90Ratio=statistics.median(x['p90'] for x in stats['candidate'])/statistics.median(x['p90'] for x in stats['baseline'])))
 for name,h in frozen['hashes'].items():assert sha(root/name)==h
assert len(rows)==len({(r['size'],r['index'],r['variant']) for r in rows})
save('result.json',dict(status='passed',mode=mode,processes=len(rows),measuredChecks=sum(len(r['samples']) for r in rows),balancedPositions=True,balancedPredecessors=True,comparisons=comparisons,scope='Ordinary exact dual-content MCP screen using same frozen exact94 worker, compiler/options and unchanged security/recovery. All-operation rename forces full fresh validation and changes following work; do not pool with four-operation timing. Five-second warmup and fixed measured phase; raw outliers and every session retained. Synthetic SDK11 macOS, not Glider/production/cross-platform qualification.'))
for x in comparisons:print(x['size'],x['method'],'median',round(x['medianRatio'],3),'p90',round(x['p90Ratio'],3),flush=True)
