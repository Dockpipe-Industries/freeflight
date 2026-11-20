# SPDX-License-Identifier: Apache-2.0
"""Disposable-fixture behavior diagnostics, reusing the MCP benchmark transport.
Not an uninstrumented latency benchmark: polls and status calls deliberately observe
freshness and watcher state. No active MCP configuration or immutable fixture edits.
"""
import hashlib,importlib.util,json,os,platform,shutil,subprocess,time
from pathlib import Path
import run as trusted
spec=importlib.util.spec_from_file_location('mcp_benchmark',trusted.REPO/'workflows/benchmark/assets/measure.py')
client=importlib.util.module_from_spec(spec);spec.loader.exec_module(client)
BASE=trusted.REPO/'bin/.local/glider-comparison'
label=os.environ['FREEFLIGHT_BEHAVIOR_LABEL'];assert label and all(c.isalnum() or c in '-_' for c in label)
OUT=BASE/label;OUT.mkdir(exist_ok=False)
shutil.copyfile(Path(__file__),OUT/'driver.py')
shutil.copyfile(Path(client.__file__),OUT/'transport.py')
shutil.copyfile(Path(trusted.__file__),OUT/'trusted-driver.py')
origin=Path(os.environ['FREEFLIGHT_BEHAVIOR_COMPARISON']).resolve()
provenance=json.loads((origin/'provenance.json').read_text());assert json.loads((origin/'summary.json').read_text())['status']=='passed'
SDK=Path(provenance['sdkRoot']);GLIDER=Path(provenance['gliderCommand']);BUNDLE=BASE/'freeflight/freeflight-osx-arm64'
CANDIDATE=provenance['candidate']['command'];ENV=dict(os.environ,DOTNET_ROOT=str(SDK),PATH=str(SDK)+os.pathsep+os.environ['PATH'],DO_NOT_TRACK='1',GLIDER_LOCAL_ERROR_LOG='0',DOTNET_CLI_TELEMETRY_OPTOUT='1',DOTNET_GENERATE_ASPNET_CERTIFICATE='false',DOTNET_CLI_HOME=str(BASE/'home'))
sizes=[int(x) for x in os.environ.get('FREEFLIGHT_BEHAVIOR_SIZES','433,5845').split(',')]
cases=os.environ.get('FREEFLIGHT_BEHAVIOR_CASES','ordinary-target-edit,preserved-metadata-target-edit,rapid-cross-project-caller-edit').split(',');assert set(cases)<={'ordinary-target-edit','preserved-metadata-target-edit','rapid-cross-project-caller-edit'}
sessions=int(os.environ.get('FREEFLIGHT_BEHAVIOR_SESSIONS','2'));assert sessions>=1 and set(sizes)<={433,5845}
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(path,value):path.write_text(json.dumps(value,indent=2)+'\n')
def unpack(r):return r['structuredContent'] if 'structuredContent' in r else json.loads(next(x['text'] for x in r['content'] if x['type']=='text'))
def complete(r):
 assert r.get('success') is True and not r.get('error'),r
 assert r.get('coverage',{}).get('complete',True) and not r.get('paging',{}).get('hasMore') and not r.get('paging',{}).get('truncatedForSize') and not r.get('truncatedForSize'),r
 return r
assert subprocess.check_output([str(GLIDER),'--version'],env=ENV).decode().strip()=='13.3.0'
for line in (BUNDLE/'SHA256SUMS').read_text().splitlines():
 digest,name=line.split(maxsplit=1);assert sha(BUNDLE/name)==digest
for name,digest in provenance['candidate']['nativeFiles'].items():assert sha(Path(CANDIDATE[0]).parent/name)==digest
fixtures={}
for size in sizes:
 old=provenance['fixtures'][str(size)];root=OUT/f'fixture-{size}';root.mkdir()
 for name,digest in old['hashes'].items():
  src=Path(old['root'])/name;assert sha(src)==digest
  dst=root/name;dst.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(src,dst)
 target=root/'source/P00/Nested/C0.cs'
 base='namespace P00;\npublic class C0 {\n    public int Value() => 0;\n    public int Other() => 1;\n}\n'
 target.write_text(base)
 with (OUT/f'restore-{size}.log').open('w') as log:subprocess.run([str(SDK/'dotnet'),'restore',str(root/'Comparison.slnx'),'--disable-build-servers'],cwd=root,env=ENV,stdout=log,stderr=subprocess.STDOUT,check=True)
 with (OUT/f'build-{size}.log').open('w') as log:subprocess.run([str(SDK/'dotnet'),'build',str(root/'Comparison.slnx'),'--no-restore','--disable-build-servers'],cwd=root,env=ENV,stdout=log,stderr=subprocess.STDOUT,check=True)
 fixtures[str(size)]={**old,'root':str(root),'hashes':{n:sha(root/n) for n in old['hashes']},'targetBase':base,'sourceFixtureSha256':old['aggregateSha256']}
save(OUT/'provenance.json',dict(comparison=str(origin),comparisonSha256=sha(origin/'provenance.json'),platform=platform.platform(),fixtures=fixtures,sessions=sessions,cases=cases,driverSha256=sha(Path(__file__)),transportSha256=sha(Path(client.__file__)),trustedDriverSha256=sha(Path(trusted.__file__)),scope='Behavior diagnostic; no hidden watcher disabling; disposable clones only'))
records=[]

def run(variant,f,size,index):
 directory=OUT/f'{size}-{index}-{variant}';directory.mkdir();root=Path(f['root']);target=root/'source/P00/Nested/C0.cs';caller=root/f'source/P{f["projects"]-1:02}/Nested/C{f["projects"]-1}.cs'
 target.write_text(f['targetBase']);callerBase=caller.read_text();assert '.Value()' in callerBase
 startup=directory/'startup.json';save(startup,dict(roots=[str(root)],trustedRoots=[str(root)],csharp={'project':'Comparison.sln'},**({'engines':{'csharp':CANDIDATE}} if variant=='candidate' else {})))
 command=[str(GLIDER),'--no-telemetry','--max-response-chars','2000000','--msbuild-path',str(SDK/'sdk/10.0.402')] if variant=='glider' else [str(BUNDLE/'bin/freeflight'),'--config',str(startup)]
 session=client.Session(root,directory,command=command,environment=ENV,sample_memory=False,working_directory=root)
 rec=dict(variant=variant,size=size,index=index,status='running',observations=[],cases=[],queries=[]);records.append(rec)
 def tool(name,args):return complete(unpack(session.request('tools/call',{'name':name,'arguments':args})))
 def status():
  return tool('server_status',{}) if variant=='glider' else unpack(session.request('tools/call',{'name':'engine.capabilities','arguments':{'root':str(root),'language':'csharp'}}))
 def query(kind,path=None,search='C5'):
  path=path or target;start=time.perf_counter_ns()
  if variant=='glider':
   if kind=='definition':name='get_symbol_at_position';args={'filePath':str(caller),'line':1,'column':callerBase.index('.Value()')+3}
   elif kind=='references':name='find_references';args={'symbolKey':referenceKey,'scope':{'mode':'solution'},'includeLineText':False,'take':1000}
   elif kind=='search':name='find_code';args={'query':search,'matchMode':'all','scope':{'mode':'solution'},'take':1000}
   else:name='get_structure';args={'filePath':str(path),'includeMembers':True}
   raw=session.request('tools/call',{'name':name,'arguments':args});result=complete(unpack(raw))
  else:
   if kind=='definition':op='definition';args={'file':str(caller),'line':0,'character':callerBase.index('.Value()')+2}
   elif kind=='references':op='references';args={'file':str(target),'line':2,'character':f['targetBase'].splitlines()[2].index('Value')+1}
   elif kind=='search':op='workspaceSymbols';args={'query':search}
   else:op='symbols';args={'file':str(path)}
   raw=session.request('tools/call',{'name':'semantic.query','arguments':{'root':str(root),'language':'csharp','operation':op,'arguments':args}});result=unpack(raw);result=result.get('items',result) if isinstance(result,dict) else result
  ms=(time.perf_counter_ns()-start)/1e6
  row={'kind':kind,'path':str(path),'ms':ms,'payloadJsonBytes':len(json.dumps(raw,separators=(',',':')).encode()),'result':result};rec['queries'].append(row);return row
 def line_of_definition(row):
  r=row['result']
  if variant=='glider':assert r['filePath']==str(target) and r['kind']=='Method',r;return r['lineNumber']
  assert len(r)==1 and r[0]['file']==str(target),r
  line=r[0]['range']['start']['line'];assert r[0]['range']['end']=={'line':line,'character':r[0]['range']['start']['character']+5},r
  return line+1
 def outline_lines(row):
  r=row['result'];items=r['items'] if variant=='glider' else r
  return {x['name']:(x['startLine'] if variant=='glider' else x['location']['range']['start']['line']+1) for x in items if x['name'] in ['Value','Other']}
 def refs(row):
  r=row['result'];items=r['references'] if variant=='glider' else r
  if variant=='glider':assert all(x['referenceKind']=='Invocation' for x in items),r
  else:assert all(x['range']['end']=={'line':x['range']['start']['line'],'character':x['range']['start']['character']+5} for x in items),r
  return sorted((x['filePath'],x['lineNumber'],x['column']) if variant=='glider' else (x['file'],x['range']['start']['line']+1,x['range']['start']['character']+1) for x in items)
 referenceKey=None
 try:
  save(directory/'discovery.json',session.server_info);save(directory/'tools.json',session.request('tools/list',{}))
  start=time.perf_counter_ns()
  if variant=='glider':
   loaded=tool('load',{'filePath':str(root/'Comparison.sln'),'workingDirectory':str(root),'includeProjects':True});assert loaded['projectCount']==f['projects'] and sum(p['documentCount'] for p in loaded['projects'])==size
   rec['loadMs']=(time.perf_counter_ns()-start)/1e6;states=[]
   for _ in range(1200):
    st=status();states.append(st)
    if not st['workspaceWarmup']['inProgress']:break
    time.sleep(.05)
   assert st['workspaceWarmup']['lastCompletedUtc'];save(directory/'readiness.json',states)
   diagnostics=tool('get_diagnostics',{'includeAnalyzers':False,'take':1});assert diagnostics['errorCount']==0 and diagnostics['warningCount']==0,diagnostics;rec['diagnostics']=diagnostics
  else:
   loaded=status();assert loaded['analysis']['files']==size and loaded['analysis']['projects']==f['projects'];rec['loadMs']=(time.perf_counter_ns()-start)/1e6
  rec['loaded']=loaded
  def reset():
   nonlocal referenceKey
   if target.read_text()!=f['targetBase']:target.write_text(f['targetBase'])
   if caller.read_text()!=callerBase:caller.write_text(callerBase)
   if variant=='glider':rec.setdefault('resets',[]).append(tool('sync',{'filePaths':[str(target),str(caller)]}))
   row=query('outline');assert outline_lines(row)=={'Value':3,'Other':4},row
   if variant=='glider':referenceKey=next(x['symbolKey'] for x in row['result']['items'] if x['name']=='Value')
   assert line_of_definition(query('definition'))==3
   time.sleep(1.1)
   quiet=status()
   if variant=='glider':assert quiet['fileWatcher']['pendingChanges']==0 and quiet['fileWatcher']['activeOperations']==0,quiet
   rec.setdefault('quiescence',[]).append(quiet)
  reset()
  # Interleave repeated and first-touch targets after shared method warm-up.
  for i in range(23):
   order=['repeated','distinct'] if i%2==0 else ['distinct','repeated']
   for phase in order:
    number=0 if phase=='repeated' else 1+i%20
    path=root/f'source/P{number%f["projects"]:02}/Nested/C{number}.cs'
    row=query('outline',path);row['phase']='outline-warmup' if i<3 else phase
    names={x['name'] for x in (row['result']['items'] if variant=='glider' else row['result'])}
    assert names==({f'P{number%f["projects"]:02}',f'C{number}','Value'} | ({'Other'} if number==0 else set())),names
  def search_check(row,text):
   r=row['result'];items=r['candidates'] if variant=='glider' else r
   expected={f'C{i}':root/f'source/P{i%f["projects"]:02}/Nested/C{i}.cs' for i in range(size) if text.lower() in f'C{i}'.lower()}
   assert {x['name'] for x in items}==set(expected) and len(items)==len(expected)
   if variant=='glider':assert all(x['filePath']==str(expected[x['name']]) and x['lineNumber']==1 and x['kind']=='Class' and x['symbolKey'] for x in items)
   else:assert all(x['locations']==[{'file':str(expected[x['name']]),'range':{'start':{'line':0,'character':28},'end':{'line':0,'character':28+len(x['name'])}}}] for x in items)
  for i in range(23):
   order=['repeated-search','distinct-search'] if i%2==0 else ['distinct-search','repeated-search']
   for phase in order:
    text='C50' if phase=='repeated-search' else f'C{51+i%4}'
    row=query('search',search=text);row['phase']='search-warmup' if i<3 else phase;row['search']=text;search_check(row,text)
  for _ in range(5):
   row=query('search');row['phase']='payload-search';search_check(row,'C5')
  rec['unchangedStatus']=status()
  for scenario in cases:
   reset();before=status();changed=caller if scenario.startswith('rapid') else target;old=changed.stat();oldText=changed.read_text()
   new=oldText.replace('.Value()','.Other()') if changed==caller else oldText.replace('Value','TEMP_').replace('Other','Value').replace('TEMP_','Other')
   assert len(new.encode())==len(oldText.encode()) and new!=oldText
   changed.write_text(new)
   if scenario.startswith('preserved'):os.utime(changed,ns=(old.st_atime_ns,old.st_mtime_ns))
   after=changed.stat();assert after.st_size==old.st_size
   if scenario.startswith('preserved'):assert after.st_mtime_ns==old.st_mtime_ns
   started=time.monotonic();case=dict(name=scenario,before=before,oldMtimeNs=old.st_mtime_ns,newMtimeNs=after.st_mtime_ns,oldSha256=hashlib.sha256(oldText.encode()).hexdigest(),newSha256=sha(changed),observations=[]);rec['cases'].append(case)
   expectedRefs=sorted((str(root/f'source/P{f["projects"]-1:02}/Nested/C{i}.cs'),1,min(n for n in [(root/f'source/P{f["projects"]-1:02}/Nested/C{i}.cs').read_text().find('.Value()'),(root/f'source/P{f["projects"]-1:02}/Nested/C{i}.cs').read_text().find('.Other()')] if n>=0)+2) for i in f['callers'])
   oldRefs=expectedRefs;newRefs=[x for x in oldRefs if x[0]!=str(caller)]
   for delay in [0,.025,.1,.25,.5,1,5.1]:
    time.sleep(max(0,delay-(time.monotonic()-started)))
    row=query('references' if changed==caller else 'definition');observed=refs(row) if changed==caller else line_of_definition(row)
    assert observed in ([oldRefs,newRefs] if changed==caller else [3,4]),observed
    case['observations'].append(dict(delayRequested=delay,elapsedMs=(time.monotonic()-started)*1000,queryMs=row['ms'],fresh=observed==(newRefs if changed==caller else 4),observed=observed,status=status()))
   # Target read and explicit sync controls are separated from the passive probes.
   case['afterTargetRead']=query('outline');case['afterTargetDefinition']=query('definition')
   if variant=='glider':
    case['forceSweep']=tool('sync',{'forceSync':True});case['afterSweep']=query('references' if changed==caller else 'definition')
    case['namedSync']=tool('sync',{'filePaths':[str(changed)]});case['afterNamedSync']=query('references' if changed==caller else 'definition')
    assert (refs(case['afterNamedSync'])==newRefs if changed==caller else line_of_definition(case['afterNamedSync'])==4)
   case['finalStatus']=status()
  rec['status']='passed'
 finally:
  session.close();target.write_text(f['targetBase']);caller.write_text(callerBase);save(OUT/'samples.json',records)
 print(size,index,variant,rec['status'],flush=True)

try:
 for size in sizes:
  for index in range(sessions):
   products=['freeflight','candidate','glider'];order=products[index%3:]+products[:index%3]
   for variant in order:run(variant,fixtures[str(size)],size,index)
 save(OUT/'summary.json',dict(status='passed',sessions=len(records),cases=[dict(size=r['size'],variant=r['variant'],session=r['index'],name=c['name'],freshAtObservedMs=next((o['elapsedMs'] for o in c['observations'] if o['fresh']),None),lastPassiveFresh=c['observations'][-1]['fresh']) for r in records for c in r['cases']]))
except Exception as error:save(OUT/'failure.json',dict(error=repr(error)));raise
