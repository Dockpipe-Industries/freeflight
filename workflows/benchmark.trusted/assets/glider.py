# SPDX-License-Identifier: Apache-2.0
"""Pinned product comparison using the existing MCP client and trusted fixture oracle.
No implementation inspection, active MCP edits, concurrent timing, or runtime changes.
"""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import platform
import shutil
import statistics
import subprocess
import time
import uuid
import run as trusted

spec=importlib.util.spec_from_file_location('mcp_benchmark',trusted.REPO/'workflows/benchmark/assets/measure.py')
client=importlib.util.module_from_spec(spec);spec.loader.exec_module(client)
BASE=trusted.REPO/'bin/.local/glider-comparison'
label=os.environ['FREEFLIGHT_GLIDER_LABEL']
assert label and all(c.isalnum() or c in '-_' for c in label)
OUT=BASE/label;OUT.mkdir(exist_ok=False)
def save(path,value):path.write_text(json.dumps(value,indent=2)+'\n')
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def unpack(result):
    if 'structuredContent' in result:return result['structuredContent']
    return json.loads(next(x['text'] for x in result['content'] if x['type']=='text'))
def complete(result):
    assert result.get('success') is True and not result.get('error'),result
    assert result.get('coverage',{}).get('complete',True),result
    paging=result.get('paging',{})
    assert not paging.get('hasMore') and not paging.get('truncatedForSize') and not result.get('truncatedForSize'),result
    return result

SDK=Path(os.environ['FREEFLIGHT_GLIDER_DOTNET_ROOT']).resolve()
GLIDER=Path(os.environ.get('FREEFLIGHT_GLIDER_COMMAND',str(BASE/'tools/glider'))).resolve()
BUNDLE=Path(os.environ.get('FREEFLIGHT_GLIDER_FREEFLIGHT_BUNDLE',str(BASE/'freeflight/freeflight-osx-arm64'))).resolve()
origin=Path(os.environ.get('FREEFLIGHT_GLIDER_FIXTURE_PROVENANCE',str(trusted.REPO/'bin/.local/benchmarks/trusted/sprint-winner-shipped/provenance.json')))
original=json.loads(origin.read_text())
ENV=dict(os.environ,DOTNET_ROOT=str(SDK),PATH=str(SDK)+os.pathsep+os.environ['PATH'],DO_NOT_TRACK='1',GLIDER_LOCAL_ERROR_LOG='0',DOTNET_CLI_TELEMETRY_OPTOUT='1',DOTNET_GENERATE_ASPNET_CERTIFICATE='false',DOTNET_CLI_HOME=str(BASE/'home'))
assert subprocess.check_output([str(GLIDER),'--version'],env=ENV).decode().strip()=='13.3.0'
assert (SDK/'sdk/10.0.402').is_dir(), 'Use the pinned shared SDK 10.0.402'
assert json.loads((BUNDLE.parent/'global.json').read_text())['sdk']['version']=='10.0.402', 'Pin SDK discovery above the isolated bundle too'
for line in (BUNDLE/'SHA256SUMS').read_text().splitlines():
    digest,name=line.split(maxsplit=1);assert sha(BUNDLE/name)==digest,name
releasePath=Path(os.environ.get('FREEFLIGHT_GLIDER_RELEASE_MANIFEST',str(trusted.REPO/'bin/.local/sprint-release-manifest.json')))
release=json.loads(releasePath.read_text())
assert release['sourceCommit']=='97c1342d9234f9d2146cd209760d6af1ea125b6e'
rounds=int(os.environ.get('FREEFLIGHT_GLIDER_ROUNDS','100'))
sessions=int(os.environ.get('FREEFLIGHT_GLIDER_SESSIONS','3'))
warmup=float(os.environ.get('FREEFLIGHT_GLIDER_WARMUP','5'))
intervals=[float(x) for x in os.environ.get('FREEFLIGHT_GLIDER_INTERVALS','0,0.1').split(',')]
sizes=[int(x) for x in os.environ.get('FREEFLIGHT_GLIDER_SIZES','433,5845').split(',')]
assert rounds>=10 and sessions>=1 and warmup>=2 and set(sizes)<={433,5845}
assert all(0<=x<=10 for x in intervals)
fixtures={}
for size in sizes:
    old=original['fixtures'][str(size)];root=BASE/f'fixtures-net10/{size}'
    if not root.exists():
        root.mkdir(parents=True)
        for relative,expected in old['hashes'].items():
            src=Path(old['root'])/relative;assert sha(src)==expected
            dst=root/relative;dst.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(src,dst)
            if dst.suffix=='.csproj':dst.write_text(dst.read_text().replace('net11.0','net10.0'))
        (root/'Comparison.slnx').write_text('<Solution>'+''.join(f'<Project Path="source/P{i:02}/P{i:02}.csproj" />' for i in range(old['projects']))+'</Solution>')
        save(root/'global.json',{'sdk':{'version':'10.0.402','rollForward':'disable'}})
        with (OUT/f'restore-{size}.log').open('w') as log:subprocess.run([str(SDK/'dotnet'),'restore',str(root/'Comparison.slnx')],cwd=root,env=ENV,stdout=log,stderr=subprocess.STDOUT,check=True)
    sln=root/'Comparison.sln'
    if not sln.exists():
        lines=['Microsoft Visual Studio Solution File, Format Version 12.00','# Visual Studio Version 17']
        ids=[]
        for i in range(old['projects']):
            name=f'P{i:02}';guid=str(uuid.uuid5(uuid.NAMESPACE_URL,'freeflight-comparison/'+name)).upper();ids.append(guid)
            lines += [f'Project("{{FAE04EC0-301F-11D3-BF4B-00C04F79EFBC}}") = "{name}", "source/{name}/{name}.csproj", "{{{guid}}}"','EndProject']
        lines += ['Global','GlobalSection(SolutionConfigurationPlatforms) = preSolution','Debug|Any CPU = Debug|Any CPU','Release|Any CPU = Release|Any CPU','EndGlobalSection','GlobalSection(ProjectConfigurationPlatforms) = postSolution']
        for guid in ids:
            for mode in ['Debug','Release']:
                lines += [f'{{{guid}}}.{mode}|Any CPU.ActiveCfg = {mode}|Any CPU',f'{{{guid}}}.{mode}|Any CPU.Build.0 = {mode}|Any CPU']
        lines += ['EndGlobalSection','EndGlobal'];sln.write_text('\n'.join(lines)+'\n')
    hashes={name:sha(root/name) for name in [*old['hashes'],'Comparison.sln','Comparison.slnx','global.json']}
    assert all(hashes[n]==v for n,v in old['hashes'].items() if n.endswith('.cs'))
    fixtures[str(size)]={**old,'root':str(root),'project':'Comparison.sln','hashes':hashes,'aggregateSha256':hashlib.sha256(json.dumps(hashes,sort_keys=True).encode()).hexdigest()}
provenance=dict(officialPackageVerification=json.loads((BASE/'official-package-verification.json').read_text()),bundleSdkPinSha256=sha(BUNDLE.parent/'global.json'),releaseManifestSha256=sha(releasePath),sourceCommit=release['sourceCommit'],releaseTag=release['tag'],freeflightBinarySha256=sha(BUNDLE/'bin/freeflight'),bundleManifestSha256=sha(BUNDLE/'SHA256SUMS'),gliderVersion='13.3.0',gliderCommand=str(GLIDER),gliderFiles={str(p.relative_to(GLIDER.parent)):sha(p) for p in GLIDER.parent.rglob('*') if p.is_file()},sdk='10.0.402',sdkRoot=str(SDK),platform=platform.platform(),architecture=platform.machine(),rounds=rounds,sessions=sessions,warmupSeconds=warmup,intervals=intervals,fixtures=fixtures,originalProvenanceSha256=sha(origin),driverHashes={str(p.relative_to(trusted.REPO)):sha(p) for p in [Path(__file__),Path(client.__file__),Path(trusted.__file__)]},limitations=['Synthetic source graph, not Biztraak.','Source bytes and graph retained; both target net10.0 with SDK 10.0.402 instead of prior net11.0.','Published self-contained FreeFlight uses its bundled runtime; Glider uses existing .NET 10.0.13.','Glider definition/search omit columns and reference ends; exact source declarations are qualified separately and missing fields are not fabricated.','Reference symbol keys are discovered and validated before timing.','Contract differences in per-request freshness/security are not normalized away.'])
save(OUT/'provenance.json',provenance)
for p in [Path(__file__),Path(client.__file__),Path(trusted.__file__)]:
    target=OUT/'driver-source'/p.relative_to(trusted.REPO);target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,target)
# Optional qualified local worker: published core and source-pinned native worker.
# Preparation/tests finish before any timing process starts.
candidateReceipt=os.environ.get('FREEFLIGHT_GLIDER_CANDIDATE_RECEIPT')
candidateCommand=None
if candidateReceipt:
    receipt=Path(candidateReceipt).resolve()
    qualification=json.loads((receipt/'qualification.json').read_text())
    transaction=json.loads((receipt/'transaction-qualification.json').read_text())
    assert qualification['status']==transaction['status']=='passed'
    assert (receipt/'summary.json').is_file(), 'Finish worker qualification and measurements first'
    prepared=json.loads((receipt/'provenance.json').read_text())
    frozen=prepared['variants']['candidate'];source=receipt/'candidate/source'
    for name,digest in frozen['sourceHashes'].items():assert sha(source/name)==digest,name
    save(OUT/'global.json',{'sdk':{'version':'10.0.402','rollForward':'disable'}})
    native=OUT/'candidate-native'
    with (OUT/'candidate-publish.log').open('w') as log:
        subprocess.run([prepared['dotnet'],'publish',str(source/'workers/roslyn/FreeFlight.Roslyn.csproj'),'-c','Release','--runtime','osx-arm64','--self-contained','true','-p:RestoreLockedMode=true','--artifacts-path',str(OUT/'candidate-publish-artifacts'),'--output',str(native),'-p:PublishSingleFile=false'],cwd=source,env={**ENV,'DOTNET_ROOT':str(Path(prepared['dotnet']).resolve().parent)},stdout=log,stderr=subprocess.STDOUT,check=True)
    candidateCommand=[str(native/'FreeFlight.Roslyn'),*prepared.get('candidateArgs',[])]
    (source/'bin/.local').mkdir(parents=True,exist_ok=True)
    for test,args in [('test_worker.py',['--native',candidateCommand[0]]),('test_trusted.py',[prepared['dotnet'],candidateCommand[0],'--native'])]:
        with (OUT/(test+'.log')).open('w') as log:
            subprocess.run(['python3','-B',str(source/'workers/roslyn'/test),*args],cwd=source,env={**ENV,'DOTNET_ROOT':str(Path(prepared['dotnet']).resolve().parent),'PATH':str(Path(prepared['dotnet']).parent)+os.pathsep+ENV['PATH']},stdout=log,stderr=subprocess.STDOUT,check=True)
    provenance['candidate']={'workerProvenanceSha256':sha(receipt/'provenance.json'),'qualificationSha256':sha(receipt/'qualification.json'),'transactionSha256':sha(receipt/'transaction-qualification.json'),'sourceHashes':frozen['sourceHashes'],'sdk':prepared['sdk'],'nativeFiles':{str(p.relative_to(native)):sha(p) for p in native.rglob('*') if p.is_file()},'command':candidateCommand,'transport':'Published unchanged core with locally published self-contained candidate worker'}
    save(OUT/'provenance.json',provenance)
records=[]

def assert_fixture(f):
    for n,d in f['hashes'].items():assert sha(Path(f['root'])/n)==d,n

def source_check(s,key,file,kind):
    r=complete(unpack(s.request('tools/call',{'name':'get_source','arguments':{'symbolKey':key,'contextLines':0,'maxChars':10000}})))
    assert r['declarationCount']==1 and len(r['declarations'])==1,r
    d=r['declarations'][0];line=file.read_text().splitlines()[0]
    start=line.index('public int') if kind=='Method' else line.index('public class')
    end=line.index(';',start)+1 if kind=='Method' else len(line)
    span=d['declarationSpan'];assert d['filePath']==str(file) and d['sourceComplete'] and not d['truncated'],d
    assert (span['startLine'],span['startColumn'],span['endLine'],span['endColumn'],span['spanStart'],span['spanLength'])==(1,start+1,1,end+1,start,end-start),d
    assert d['source']==line[start:end] and d['contentSpan']==span,d
    return r

def run_session(variant,f,size,interval,index):
    name=f'{size}-interval{interval:g}-{index}-{variant}';directory=OUT/name;directory.mkdir()
    root=Path(f['root']);queries,check=trusted.workload(f,size);target=root/'source/P00/Nested/C0.cs';caller=Path(queries[1][1]['file'])
    assert_fixture(f)
    if variant!='glider':
        startup=directory/'startup.json';save(startup,{'roots':[str(root)],'trustedRoots':[str(root)],'csharp':{'project':f['project']}})
        if variant=='candidate':
            config=json.loads(startup.read_text());config['engines']={'csharp':candidateCommand};save(startup,config)
        command=[str(BUNDLE/'bin/freeflight'),'--config',str(startup)]
    else:command=[str(GLIDER),'--no-telemetry','--max-response-chars','2000000','--msbuild-path',str(SDK/'sdk/10.0.402')]
    s=client.Session(root,directory,command=command,environment=ENV,sample_memory=False,working_directory=root)
    rec=dict(name=name,variant=variant,size=size,interval=interval,startupDiscoveryMs=s.startup_ms,samples=[],status='running');records.append(rec)
    save(directory/'discovery.json',s.server_info)
    try:
        start=time.perf_counter_ns()
        if variant!='glider':
            loaded=unpack(s.request('tools/call',{'name':'engine.capabilities','arguments':{'root':str(root),'language':'csharp'}}))
            rec['loadMs']=(time.perf_counter_ns()-start)/1e6
            assert loaded['analysis']['files']==size and loaded['analysis']['projects']==f['projects'],loaded
            assert loaded['analysis']['mode']=='trusted-msbuild',loaded
            rec['backgroundWarmupMs']=None;rec['warmupNote']='Compilation awaited inside load; no separate background phase exposed.'
        else:
            loaded=complete(unpack(s.request('tools/call',{'name':'load','arguments':{'filePath':str(root/f['project']),'workingDirectory':str(root),'includeProjects':True}})))
            rec['loadMs']=(time.perf_counter_ns()-start)/1e6
            assert loaded['projectCount']==f['projects'] and sum(p['documentCount'] for p in loaded['projects'])==size,loaded
            start=time.perf_counter_ns();states=[]
            for attempt in range(1200):
                state=complete(unpack(s.request('tools/call',{'name':'server_status','arguments':{'includeWorkspaceDiagnostics':True}})));states.append(state)
                assert state['solutionPath']==str(root/f['project']) and state['solutionRoot']==str(root)
                assert state['workspaceDiagnostics']['count']==0,state
                if not state['workspaceWarmup']['inProgress']:break
                time.sleep(.05)
            assert not state['workspaceWarmup']['inProgress'] and state['workspaceWarmup']['lastCompletedUtc'],state
            rec['backgroundWarmupWaitMs']=(time.perf_counter_ns()-start)/1e6
            rec['backgroundWarmupMs']=state['workspaceWarmup']['lastDurationMs'];save(directory/'readiness.json',states)
        save(directory/'loaded.json',loaded)
        expected_search={f'C{i}':root/f'source/P{i%f["projects"]:02}/Nested/C{i}.cs' for i in range(size) if f['searchQuery'].casefold() in f'C{i}'.casefold()}
        ref_files=[root/f'source/P{f["projects"]-1:02}/Nested/C{i}.cs' for i in f['callers']]
        expected_refs=sorted((str(p),1,p.read_text().index('.Value()')+2) for p in ref_files)
        keys={}
        if variant=='glider':
            diag=complete(unpack(s.request('tools/call',{'name':'get_diagnostics','arguments':{'includeAnalyzers':False,'take':1}})))
            save(directory/'diagnostics.json',diag);assert diag['errorCount']==0 and diag['warningCount']==0,diag
            outline=complete(unpack(s.request('tools/call',{'name':'get_structure','arguments':{'filePath':str(target),'includeMembers':True}})))
            reference_key=next(x['symbolKey'] for x in outline['items'] if x['name']=='Value')
            source_check(s,reference_key,target,'Method')
            discovery=complete(unpack(s.request('tools/call',{'name':'find_code','arguments':{'query':f['searchQuery'],'matchMode':'all','scope':{'mode':'solution'},'take':1000}})))
            for item in discovery['candidates']:
                assert item['name'] in expected_search
                source_check(s,item['symbolKey'],expected_search[item['name']],'Class');keys[item['name']]=item['symbolKey']
            assert set(keys)==set(expected_search)
            definition=complete(unpack(s.request('tools/call',{'name':'get_symbol_at_position','arguments':{'filePath':str(caller),'line':1,'column':queries[1][1]['character']+1}})))
            definition_key=definition['symbolKey'];save(directory/'definition-source.json',source_check(s,definition_key,target,'Method'))
            save(directory/'validated-search-keys.json',keys)
        def invoke(method,args):
            start=time.perf_counter_ns()
            if variant!='glider':result,ignored=s.query('csharp',method,**args)
            else:
                if method=='symbols':tool='get_structure';arguments={'filePath':str(target),'includeMembers':True}
                elif method=='definition':tool='get_symbol_at_position';arguments={'filePath':str(caller),'line':1,'column':args['character']+1}
                elif method=='references':tool='find_references';arguments={'symbolKey':reference_key,'scope':{'mode':'solution'},'includeLineText':False,'take':1000}
                else:tool='find_code';arguments={'query':f['searchQuery'],'matchMode':'all','scope':{'mode':'solution'},'take':1000}
                result=unpack(s.request('tools/call',{'name':tool,'arguments':arguments}))
            ms=(time.perf_counter_ns()-start)/1e6
            if variant!='glider':check(method,result)
            else:
                complete(result)
                if method=='symbols':
                    expected={'P00':('Namespace',1,60),'C0':('Class',16,60),'Value':('Method',34,58)}
                    assert len(result['items'])==3 and result['filePath']==str(target),result
                    assert {x['name']:(x['kind'],x['startColumn'],x['endColumn']) for x in result['items']}==expected,result
                    assert all(x['startLine']==x['endLine']==1 for x in result['items']),result
                elif method=='definition':assert (result['symbolKey'],result['filePath'],result['lineNumber'],result['kind'])==(definition_key,str(target),1,'Method'),result
                elif method=='references':
                    assert result['referenceCount']==14 and len(result['references'])==14,result
                    assert sorted((x['filePath'],x['lineNumber'],x['column']) for x in result['references'])==expected_refs,result
                    assert all(x['referenceKind']=='Invocation' for x in result['references']),result
                else:
                    assert result['candidateCount']==len(expected_search) and len(result['candidates'])==len(expected_search),result
                    assert {x['name']:(x['symbolKey'],x['filePath'],x['lineNumber'],x['kind']) for x in result['candidates']}=={n:(keys[n],str(p),1,'Class') for n,p in expected_search.items()},result
            return result,ms
        for method,args in queries:
            result,ms=invoke(method,args);save(directory/(method+'-validated.json'),result)
        def cycle(phase,round_index):
            started=time.monotonic()
            for method,args in queries:
                result,ms=invoke(method,args)
                rec['samples'].append({'phase':phase,'round':round_index,'method':method,'ms':ms,'resultSha256':hashlib.sha256(json.dumps(result,sort_keys=True).encode()).hexdigest()})
            if interval:time.sleep(max(0,interval-(time.monotonic()-started)))
        start=time.monotonic();i=0
        while i<3 or time.monotonic()-start<warmup:cycle('warmup',i);i+=1
        for i in range(rounds):cycle('steady',i)
        time.sleep(5.1);cycle('idle-5.1s',0)
        if variant=='glider':save(directory/'final-status.json',unpack(s.request('tools/call',{'name':'server_status','arguments':{}})))
        assert_fixture(f);rec['status']='passed'
    except Exception as error:rec['status']='failed';rec['error']=repr(error);raise
    finally:s.close();save(OUT/'samples.json',records)
    print(name,'passed',flush=True)

try:
    for interval in intervals:
        for size in sizes:
            for pair in range(sessions):
                if candidateCommand:
                    products=['freeflight','candidate','glider'];rotation=pair%3
                    order=products[rotation:]+products[:rotation]
                else:order=['freeflight','glider'] if pair%2==0 else ['glider','freeflight']
                for offset,variant in enumerate(order):run_session(variant,fixtures[str(size)],size,interval,pair*len(order)+offset)
    rows=[]
    for r in records:
        for phase in ['warmup','steady','idle-5.1s']:
            for method in ['symbols','definition','references','workspaceSymbols']:
                rows.append(dict(session=r['name'],variant=r['variant'],size=r['size'],interval=r['interval'],phase=phase,method=method,**trusted.stats([x['ms'] for x in r['samples'] if x['phase']==phase and x['method']==method])))
    comparisons=[]
    for interval in intervals:
        for size in sizes:
            for method in ['symbols','definition','references','workspaceSymbols']:
                selected=[x for x in rows if x['phase']=='steady' and x['size']==size and x['interval']==interval and x['method']==method]
                ff=[x for x in selected if x['variant']=='freeflight'];gl=[x for x in selected if x['variant']=='glider']
                item=dict(size=size,interval=interval,method=method,freeflight=ff,glider=gl,medianRatio=statistics.median(x['median'] for x in ff)/statistics.median(x['median'] for x in gl),p90Ratio=statistics.median(x['p90'] for x in ff)/statistics.median(x['p90'] for x in gl));comparisons.append(item)
                print(size,interval,method,'FreeFlight/Glider median',round(item['medianRatio'],3),'p90',round(item['p90Ratio'],3),flush=True)
                if candidateCommand:
                    candidate=[x for x in selected if x['variant']=='candidate']
                    for other in ['freeflight','glider']:
                        baseline=[x for x in selected if x['variant']==other]
                        extra=dict(size=size,interval=interval,method=method,candidate=candidate,baseline=baseline,baselineName=other,medianRatio=statistics.median(x['median'] for x in candidate)/statistics.median(x['median'] for x in baseline),p90Ratio=statistics.median(x['p90'] for x in candidate)/statistics.median(x['p90'] for x in baseline));comparisons.append(extra)
                        print(size,interval,method,'candidate/'+other,'median',round(extra['medianRatio'],3),'p90',round(extra['p90Ratio'],3),flush=True)

    save(OUT/'summary.json',{'status':'passed','sessions':rows,'comparisons':comparisons})
except Exception as error:save(OUT/'failure.json',{'error':repr(error)});raise
