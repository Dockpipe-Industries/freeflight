# SPDX-License-Identifier: Apache-2.0
"""DockPipe asset: trusted worker isolation of the existing benchmark workloads.
Not full MCP timing. Native test assets remain the semantic/security authority.
"""
import hashlib
import json
import math
import os
from pathlib import Path
import platform
import queue
import shutil
import statistics
import subprocess
import sys
import threading
import time

REPO = Path(__file__).resolve().parents[3]
LABEL = os.environ.get('FREEFLIGHT_TRUSTED_BENCH_LABEL', 'latest')
assert LABEL and all(c.isalnum() or c in '-_' for c in LABEL), 'Invalid receipt label'
OUT = REPO / 'bin/.local/benchmarks/trusted' / LABEL
DOTNET = shutil.which('dotnet')
ENV = dict(os.environ, DOTNET_ROOT=str(Path(DOTNET).resolve().parent) if DOTNET else '', DOTNET_CLI_TELEMETRY_OPTOUT='1')

def save(name, value):
    (OUT / name).write_text(json.dumps(value, indent=2) + '\n')

def command(args, log, cwd=REPO, timeout=300):
    with (OUT / log).open('w') as stream:
        subprocess.run(args, cwd=cwd, env=ENV, stdout=stream, stderr=subprocess.STDOUT, check=True, timeout=timeout)

def git(*args):
    return subprocess.check_output(['git', *args], cwd=REPO).decode().strip()

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def build(source, output, log):
    command([DOTNET, 'build', str(source / 'workers/roslyn/FreeFlight.Roslyn.csproj'), '-c', 'Release', '-p:RestoreLockedMode=true', '--artifacts-path', str(output)], log, source)
    return output / 'bin/FreeFlight.Roslyn/release/FreeFlight.Roslyn.dll'

def prepare():
    assert DOTNET, 'Provision the repository-pinned SDK on PATH'
    OUT.mkdir(parents=True, exist_ok=False)  # never overwrite prior evidence
    sdk = subprocess.check_output([DOTNET, '--version'], cwd=REPO, env=ENV).decode().strip()
    expected = json.loads((REPO / 'global.json').read_text())['sdk']['version']
    assert sdk == expected, (sdk, expected)
    config = dict(schema=1, host=platform.platform(), machine=platform.machine(), logicalCpus=os.cpu_count(), runtimeEnvironment={key:os.environ[key] for key in ('DOTNET_PROCESSOR_COUNT','DOTNET_TieredPGO','DOTNET_TieredCompilation','DOTNET_ReadyToRun','DOTNET_gcServer','DOTNET_gcConcurrent') if key in os.environ}, sdk=sdk, dotnet=DOTNET,
                  baseline=os.environ.get('FREEFLIGHT_TRUSTED_BENCH_BASELINE', '39c3cc83b04f21e352e7885c0589d39947b9efa4'),
                  candidate=os.environ.get('FREEFLIGHT_TRUSTED_BENCH_CANDIDATE', 'WORKTREE'),
                  sessions=int(os.environ.get('FREEFLIGHT_TRUSTED_BENCH_SESSIONS', '3')),
                  rounds=int(os.environ.get('FREEFLIGHT_TRUSTED_BENCH_ROUNDS', '20')),
                  warmupSeconds=float(os.environ.get('FREEFLIGHT_TRUSTED_BENCH_WARMUP', '5')),
                  roundIntervalSeconds=float(os.environ.get('FREEFLIGHT_TRUSTED_BENCH_INTERVAL','0')),
                  sizes=[int(x) for x in os.environ.get('FREEFLIGHT_TRUSTED_BENCH_SIZES', '433,5845').split(',')],
                  paddingBytes=int(os.environ.get('FREEFLIGHT_TRUSTED_BENCH_PADDING', '0')),
                  referenceCallers=int(os.environ.get('FREEFLIGHT_TRUSTED_BENCH_CALLERS','1')),
                  searchQuery=os.environ.get('FREEFLIGHT_TRUSTED_BENCH_QUERY','C58'),
                  firstVariant=os.environ.get('FREEFLIGHT_TRUSTED_BENCH_FIRST','baseline'),
                  baselineArgs=['--incremental-validation'] if os.environ.get('FREEFLIGHT_TRUSTED_BENCH_BASELINE_INCREMENTAL') == '1' else [],
                  candidateArgs=['--incremental-validation'] if os.environ.get('FREEFLIGHT_TRUSTED_BENCH_INCREMENTAL') == '1' else [],
                  configuration='Release', transport='direct trusted worker; not full MCP', variants={})
    if os.environ.get('FREEFLIGHT_TRUSTED_BENCH_BASELINE_BACKGROUND') == '1':
        assert config['baselineArgs'], 'Background baseline requires incremental mode'
        config['baselineArgs'].append('--background-recovery')
    if os.environ.get('FREEFLIGHT_TRUSTED_BENCH_BACKGROUND') == '1':
        assert config['candidateArgs'], 'Background screening requires incremental mode'
        config['candidateArgs'].append('--background-recovery')
    assert 0 <= config['paddingBytes'] <= 65536
    assert 1 <= config['referenceCallers'] <= 1000 and 1 <= len(config['searchQuery']) <= 256
    assert config['firstVariant'] in ('baseline','candidate')
    assert all(sum(config['searchQuery'].casefold() in f'C{f}'.casefold() for f in range(count)) <= 1000 for count in config['sizes']), 'Search exceeds worker symbol limit'
    assert 0 <= config['roundIntervalSeconds'] <= 10
    assert config['sessions'] >= 2 and config['rounds'] >= 10 and config['warmupSeconds'] >= 2
    assert set(config['sizes']) <= {16, 128, 256, 433, 1024, 2048, 5845} and 433 in config['sizes'], '433 fixture required for mutation qualification'
    # Copy only repository-owned worker inputs; never reuse dirty build outputs.
    paths = ['global.json'] + git('ls-files', 'workers/roslyn').splitlines()
    for variant in ('baseline', 'candidate'):
        ref = config[variant]; source = OUT / variant / 'source'; source.mkdir(parents=True)
        commit = git('rev-parse', 'HEAD' if ref == 'WORKTREE' else ref)
        hashes = {}
        variantPaths = paths if ref == 'WORKTREE' else ['global.json'] + git('ls-tree','-r','--name-only',commit,'workers/roslyn').splitlines()
        for path in variantPaths:
            data = (REPO/path).read_bytes() if ref == 'WORKTREE' else subprocess.check_output(['git','show',f'{commit}:{path}'], cwd=REPO)
            target = source/path; target.parent.mkdir(parents=True, exist_ok=True); target.write_bytes(data)
            hashes[path] = hashlib.sha256(data).hexdigest()
        dll = build(source, OUT / variant / 'build', variant+'-build.log')
        profile = OUT / variant / 'profile-source'; shutil.copytree(source, profile)
        from profile import instrument
        instrument(profile / 'workers/roslyn/Program.cs')
        pdll = build(profile, OUT / variant / 'profile-build', variant+'-profile-build.log')
        config['variants'][variant] = dict(commit=commit, sourceHashes=hashes, dll=str(dll), dllSha256=digest(dll), profileDll=str(pdll), profileDllSha256=digest(pdll))
    fixtures = {}
    for count in config['sizes']:
        projects = 26 if count == 5845 else 2; root = OUT / f'fixture-{count}'
        hashes = {}
        for i in range(projects):
            d = root/'source'/f'P{i:02}'; d.mkdir(parents=True)
            refs = ''.join(f'<ProjectReference Include="../P{j:02}/P{j:02}.csproj" />' for j in range(projects-1)) if i == projects-1 else ''
            (d/f'P{i:02}.csproj').write_text('<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup><TargetFramework>net11.0</TargetFramework><GenerateAssemblyInfo>false</GenerateAssemblyInfo><GenerateTargetFrameworkAttribute>false</GenerateTargetFrameworkAttribute></PropertyGroup><ItemGroup>'+refs+'</ItemGroup></Project>')
        callers=list(range(projects-1,count,projects))[:config['referenceCallers']]
        for f in range(count):
            i=f%projects; d=root/'source'/f'P{i:02}'/'Nested'; d.mkdir(exist_ok=True)
            value = 'new P00.C0().Value()' if f in callers else str(f)
            content=f'namespace P{i:02}; public class C{f} {{ public int Value() => {value}; }}\n'
            if config['paddingBytes']>len(content)+5:content+='/*'+' '*(config['paddingBytes']-len(content)-5)+'*/\n'
            (d/f'C{f}.cs').write_bytes(content.encode('utf-8'))
        for p in sorted(root.rglob('*')):
            if p.is_file(): hashes[str(p.relative_to(root))] = digest(p)
        project=f'source/P{projects-1:02}/P{projects-1:02}.csproj'
        command([DOTNET, 'restore', str(root/project), '--ignore-failed-sources'], f'restore-{count}.log')
        fixtures[str(count)] = dict(root=str(root), projects=projects, project=project, hashes=hashes,callers=callers,searchQuery=config['searchQuery'])
    config['fixtures'] = fixtures
    command([DOTNET, '--info'], 'dotnet-info.log')
    config['driverHashes'] = {p.name:digest(p) for p in Path(__file__).parent.glob('*.py')}
    drivers=OUT/'driver-source';drivers.mkdir()
    for name in config['driverHashes']:shutil.copyfile(Path(__file__).parent/name,drivers/name)
    save('provenance.json',config)
    print('Prepared pinned source/build/fixture receipts:', OUT, flush=True)

class Session:
    def __init__(self,dll,name,args=()):
        self.log=(OUT/(name+'.stderr')).open('w'); self.q=queue.Queue(); self.seq=0
        self.p=subprocess.Popen([DOTNET,dll,'--trusted-msbuild',*args],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=self.log,text=True,env=ENV)
        def reader():
            for line in self.p.stdout:self.q.put(line)
            self.q.put(None)
        threading.Thread(target=reader,daemon=True).start()
    def call(self,method,**params):
        self.seq+=1; start=time.perf_counter_ns()
        self.p.stdin.write(json.dumps(dict(id=self.seq,method=method,params=params))+'\n');self.p.stdin.flush()
        line=self.q.get(timeout=90); assert line is not None, 'Worker exited'
        reply=json.loads(line); ms=(time.perf_counter_ns()-start)/1e6
        assert reply['id']==self.seq and 'error' not in reply,reply
        return reply['result'],ms
    def close(self):
        self.p.stdin.close()
        try:self.p.wait(timeout=15)
        except subprocess.TimeoutExpired:self.p.kill();self.p.wait();raise
        finally:self.log.close()


def qualify(config):
    # Existing exact-result, cancellation, resources, traversal, symlink and external-input tests.
    for variant,v in config['variants'].items():
        for test in ('test_worker.py','test_trusted.py'):
            command([sys.executable,'-B',str(REPO/'workers/roslyn'/test),DOTNET,v['dll']],variant+'-'+test+'.log')
        command([sys.executable,'-B',str(Path(__file__).with_name('mutations.py')),DOTNET,v['dll'],str(OUT/variant/'mutations'),config['fixtures']['433']['root']],variant+'-mutations.log')
        if platform.system() == 'Darwin' and (OUT/variant/'source/workers/roslyn/DarwinMetadataBatch.cs').is_file():
            command([sys.executable,'-B',str(Path(__file__).with_name('metadata_tests.py')),DOTNET,str(OUT/variant/'source'),str(OUT/variant/'metadata-proof')],variant+'-metadata-proof.log')
        if platform.system() == 'Darwin' and (OUT/variant/'source/workers/roslyn/DarwinSourceHandle.cs').is_file():
            command([sys.executable,'-B',str(Path(__file__).with_name('serial_handle_tests.py')),DOTNET,str(OUT/variant/'source'),str(OUT/variant/'serial-handle-proof')],variant+'-serial-handle-proof.log')
        if platform.system() == 'Darwin' and 'ReadCompilerBytes(' in (OUT/variant/'source/workers/roslyn/Program.cs').read_text():
            command([sys.executable,'-B',str(Path(__file__).with_name('expiry_tests.py')),DOTNET,str(OUT/variant/'source'),str(OUT/variant/'expiry-proof')],variant+'-expiry-proof.log')
    if any(marker in (OUT/'candidate/source/workers/roslyn/SemanticQueries.cs').read_text() for marker in ('FindCompilationDeclarations(', 'FindProjectDeclarations(')):
        command([sys.executable, '-B', str(Path(__file__).with_name('search_tests.py')), DOTNET,
                 str(OUT/'candidate/source'), str(OUT/'candidate/search-proof')], 'candidate-search-proof.log')
    if config.get('candidateArgs'):
        command([sys.executable, '-B', str(Path(__file__).with_name('incremental_tests.py')), DOTNET,
                 str(OUT/'candidate/source'), str(OUT/'candidate/incremental-proof'),
                 config['fixtures']['433']['root']], 'candidate-incremental-proof.log')
    if '--background-recovery' in config.get('candidateArgs', []):
        command([sys.executable, '-B', str(Path(__file__).with_name('background_tests.py')), DOTNET,
                 str(OUT/'candidate/source'), str(OUT/'candidate/background-proof'),
                 config['fixtures']['433']['root']], 'candidate-background-proof.log')
    save('qualification.json',dict(status='passed',variants=list(config['variants']),suites=['test_worker.py','test_trusted.py','mutations.py'],testHashes={name:digest(REPO/'workers/roslyn'/name) for name in ('test_worker.py','test_trusted.py')}))


def transaction(config):
    from transaction import instrument
    results=[]
    for variant,v in config['variants'].items():
        source=OUT/variant/'source'
        for relative,expected in v['sourceHashes'].items():
            assert digest(source/relative)==expected, 'Snapshot changed: '+relative
        target=OUT/variant/'transaction-source'
        shutil.copytree(source,target)
        instrument(target/'workers/roslyn/Program.cs')
        dll=build(target,OUT/variant/'transaction-build',variant+'-transaction-build.log')
        destination=OUT/variant/'transaction-mutations'
        command([sys.executable,'-B',str(Path(__file__).with_name('mutations.py')),DOTNET,str(dll),str(destination),config['fixtures']['433']['root'],'--transaction'],variant+'-transaction-mutations.log')
        log=(destination/'worker.stderr').read_text()
        assert 'BENCH_TRANSACTION_FAILURE' not in log, 'Failed refresh changed committed state'
        count=log.count('BENCH_TRANSACTION_PRESERVED')
        assert count>=5 and 'BENCH_PRE_READ_SWAP_EXECUTED' in log, 'Transaction/boundary failure paths were not exercised'
        results.append(dict(variant=variant,preservedFailures=count,dllSha256=digest(dll)))
    save('transaction-qualification.json',dict(status='passed',results=results,adapterSha256=digest(Path(__file__).with_name('transaction.py')),testSha256=digest(Path(__file__).with_name('mutations.py'))))
    print('Failed-refresh state preservation passed:', results, flush=True)


def workload(fixture,size):
    root=Path(fixture['root']);last=fixture['projects']-1;target=root/'source/P00/Nested/C0.cs'; caller=root/f'source/P{last:02}/Nested/C{last}.cs'
    queries=[('symbols',dict(file=str(target))),('definition',dict(file=str(caller),line=0,character=caller.read_text().index('.Value()')+2)),('references',dict(file=str(target),line=0,character=45)),('workspaceSymbols',dict(query=fixture.get('searchQuery','C58')))]
    def location(file, start, length):
        return dict(file=str(file),range=dict(start=dict(line=0,character=start),end=dict(line=0,character=start+length)))
    expected_definition=location(target,44,5)
    reference_files=[root/f'source/P{last:02}/Nested/C{f}.cs' for f in fixture.get('callers',[last])]
    expected_references=[location(file,file.read_text().index('.Value()')+1,5) for file in reference_files]
    expected_symbols={name:(kind,location(target,start,len(name))) for name,kind,start in [('P00','Namespace',10),('C0','NamedType',28),('Value','Method',44)]}
    expected_search={f'C{f}':location(root/f'source/P{f%fixture["projects"]:02}/Nested/C{f}.cs',28,len(f'C{f}')) for f in range(int(size)) if fixture.get('searchQuery','C58').casefold() in f'C{f}'.casefold()}
    def check(method,result):
        if method=='symbols':
            assert len(result)==len(expected_symbols),result
            assert {x['name']:(x['kind'],x['location']) for x in result}==expected_symbols,result
        elif method=='definition':assert result==[expected_definition],result
        elif method=='references':assert sorted(result,key=lambda x:x['file'])==sorted(expected_references,key=lambda x:x['file']),result
        else:
            assert len(result)==len(expected_search),result
            assert all(x['kind']=='NamedType' and x['locations']==[expected_search[x['name']]] for x in result),result
            assert {x['name'] for x in result}==set(expected_search),result
    return queries,check


def measure(config):
    assert json.loads((OUT/'qualification.json').read_text())['status']=='passed'
    samples=[]
    for size,fixture in config['fixtures'].items():
        root=Path(fixture['root']);queries,check=workload(fixture,int(size))
        order=[]
        for pair in range(config['sessions']):
            baseline_first=(pair%2==0)==(config.get('firstVariant','baseline')=='baseline')
            order.extend(['baseline','candidate'] if baseline_first else ['candidate','baseline'])
        # Diagnostics are a separate fresh session for each variant, never pooled with ordinary timing.
        for diagnostic,variants in ((False,order),(True,['baseline','candidate'])):
            for index,variant in enumerate(variants):
                name=f'{size}-'+('profile' if diagnostic else 'plain')+f'-{index}-{variant}'
                session=Session(config['variants'][variant]['profileDll' if diagnostic else 'dll'],name,config.get(variant+'Args',[]))
                receipt=dict(name=name,size=int(size),variant=variant,diagnostic=diagnostic,samples=[])
                samples.append(receipt)
                try:
                    opened,receipt['loadMs']=session.call('open',root=str(root),project=fixture['project'])
                    assert opened['files']==int(size) and opened['projects']==fixture['projects'],opened
                    warmStart=time.monotonic(); round=0
                    def cycle(phase):
                        cycleStart=time.monotonic()
                        for method,args in queries:
                            before,_=session.call('capabilities'); result,ms=session.call(method,**args); ident=session.seq
                            check(method,result); after,_=session.call('capabilities')
                            readCount=(after['refreshStats']['readFiles']-before['refreshStats']['readFiles']) if 'readFiles' in after['refreshStats'] else int(size)-(after['refreshStats']['reusedSnapshots']-before['refreshStats']['reusedSnapshots'])
                            receipt['samples'].append(dict(readDocuments=readCount,readBytes=after['refreshStats']['bytesRead']-before['refreshStats']['bytesRead'],id=ident,round=round,phase=phase,method=method,ms=ms,before=before['refreshStats'],after=after['refreshStats']))
                        if config.get('roundIntervalSeconds',0)>0: time.sleep(max(0,config['roundIntervalSeconds']-(time.monotonic()-cycleStart)))
                    while round<3 or time.monotonic()-warmStart<config['warmupSeconds']:
                        cycle('warmup');round+=1
                    for round in range(config['rounds']):cycle('steady')
                    time.sleep(5.1)
                    cycle('expiry')
                    receipt['status']='passed'
                except Exception as e:
                    receipt['status']='failed';receipt['error']=repr(e);raise
                finally:
                    session.close();save('samples.json',samples)
                print(name,'passed',flush=True)


def stats(values):
    values=sorted(values)
    return dict(n=len(values),median=statistics.median(values),p90=values[math.ceil(.9*len(values))-1],maximum=max(values),mean=statistics.mean(values),total=sum(values))

def summarize(config):
    sessions=json.loads((OUT/'samples.json').read_text()); result=[];comparisons=[]
    for session in sessions:
        for phase in ('warmup','steady','expiry'):
            for method in ('symbols','definition','references','workspaceSymbols'):
                rows=[s for s in session['samples'] if s['phase']==phase and s['method']==method]
                result.append(dict(session=session['name'],size=session['size'],variant=session['variant'],diagnostic=session['diagnostic'],phase=phase,method=method,**stats([r['ms'] for r in rows])))
    for size in config['sizes']:
        for method in ('symbols','definition','references','workspaceSymbols'):
            rows=[r for r in result if r['size']==size and r['method']==method and not r['diagnostic'] and r['phase']=='steady']
            b=[r for r in rows if r['variant']=='baseline'];c=[r for r in rows if r['variant']=='candidate']
            comparisons.append(dict(size=size,method=method,baseline=b,candidate=c,medianRatio=statistics.median(r['median'] for r in c)/statistics.median(r['median'] for r in b),p90Ratio=statistics.median(r['p90'] for r in c)/statistics.median(r['p90'] for r in b),unfavorableCandidateSessions=[r['session'] for r in c if r['p90']>statistics.median(x['p90'] for x in b)]))
    profiles=[]; tails=[]; bulk=[]
    for session in sessions:
        for method in ('symbols','definition','references','workspaceSymbols'):
            rows=[r for r in session['samples'] if r['phase']=='steady' and r['method']==method and r.get('readDocuments',0)>1]
            if rows:bulk.append(dict(session=session['name'],diagnostic=session['diagnostic'],method=method,**stats([r['ms'] for r in rows])))
    save('bulk-reads.json',bulk)
    for session in sessions:
        diagnostics={}
        if session['diagnostic']:
            for line in (OUT/(session['name']+'.stderr')).read_text().splitlines():
                if line.startswith('BENCH_PROFILE '):
                    row=json.loads(line[len('BENCH_PROFILE '):]);diagnostics[row['id']]=row
        for method in ('symbols','definition','references','workspaceSymbols'):
            ordinary=[r for r in session['samples'] if r['phase']=='steady' and r['method']==method]
            threshold=stats([r['ms'] for r in ordinary])['p90']
            for row in session['samples']:
                if row['method']!=method:continue
                details=diagnostics.get(row['id'])
                if row['phase']=='expiry' or (row['phase']=='steady' and row['ms']>=threshold):
                    tails.append(dict(session=session['name'],diagnostic=session['diagnostic'],sample=row,profile=details))
            if not diagnostics:continue
            for phase in ('warmup','steady','expiry'):
                chosen=[diagnostics[r['id']] for r in session['samples'] if r['phase']==phase and r['method']==method]
                stages=sorted({k for r in chosen for k in r['stages']})
                profiles.append(dict(session=session['name'],variant=session['variant'],size=session['size'],method=method,phase=phase,
                    stages={k:stats([r['stages'].get(k,0) for r in chosen]) for k in stages},
                    metrics={k:stats([r[k] for r in chosen]) for k in ('allocatedBytes','gcPauseMs','gen0','gen1','gen2','Reads','Expired','Dirty','Invalidated','Bytes','Reused','Attrs','invokeMs','replyMs','cpuMs','poolThreads','poolPending','poolCompleted','processorCount')},
                    runtimeEventTotals={k:sum(r['runtimeEvents'].get(k,0) for r in chosen) for k in sorted({k for r in chosen for k in r['runtimeEvents']})}))
    save('profile-summary.json',profiles)
    save('tails.json',tails)
    observations=[]
    for session in sessions:
        for method in ('symbols','definition','references','workspaceSymbols'):
            chosen=[r for r in tails if r['session']==session['name'] and r['sample']['phase']=='steady' and r['sample']['method']==method]
            top=sorted(chosen,key=lambda r:r['sample']['ms'],reverse=True)[:5]
            observations.append(dict(session=session['name'],method=method,diagnostic=session['diagnostic'],top=[dict(method=r['sample']['method'],ms=r['sample']['ms'],readDocuments=r['sample'].get('readDocuments'),readBytes=r['sample'].get('readBytes'),profile=None if not r['profile'] else {k:r['profile'].get(k) for k in ('Expired','Dirty','Invalidated','gcPauseMs','cpuMs','poolThreads','poolPending','runtimeEvents','stages','invokeMs','replyMs')}) for r in top]))
    for observation in observations:
        for row in observation['top']:
            if row['profile']:
                row['profile']['runtimeEvents']={k:v for k,v in row['profile']['runtimeEvents'].items() if v}
    save('tail-observations.json',observations)

    save('summary.json',dict(sessions=result,comparisons=comparisons,interpretation='Descriptive ratios only; no statistical acceptance threshold. Keep every session and outlier.'))
    lines=['# Trusted worker comparison', '', 'Descriptive results; all sessions/outliers retained. Not a competitor comparison.', '', '| Files | Operation | Baseline medians ms | Candidate medians ms | Baseline p90 ms | Candidate p90 ms | Median ratio | p90 ratio |', '| --- | --- | --- | --- | --- | --- | --- | --- |']
    for r in comparisons:
        values=lambda variant,key: ', '.join(f"{row[key]:.3f}" for row in r[variant])
        lines.append(f"| {r['size']} | {r['method']} | {values('baseline','median')} | {values('candidate','median')} | {values('baseline','p90')} | {values('candidate','p90')} | {r['medianRatio']:.3f} | {r['p90Ratio']:.3f} |")
    (OUT/'comparison.md').write_text('\n'.join(lines)+'\n')
    for r in comparisons:print(r['size'],r['method'],'median ratio',round(r['medianRatio'],3),'p90 ratio',round(r['p90Ratio'],3),'unfavorable sessions',len(r['unfavorableCandidateSessions']))

if __name__=='__main__':
    action=sys.argv[1]
    if action=='prepare':
        try:prepare()
        except Exception as error:
            if OUT.is_dir() and not (OUT/'provenance.json').exists():save('failure-prepare.json',dict(action=action,error=repr(error)))
            raise
    else:
        config=json.loads((OUT/'provenance.json').read_text())
        if action in ('measure','summarize'):
            for name,expected in config['driverHashes'].items():assert digest(Path(__file__).parent/name)==expected, 'Driver changed during run: '+name
        assert subprocess.check_output([DOTNET,'--version'],env=ENV).decode().strip()==config['sdk'], 'SDK changed since prepare'
        try:globals()[action](config)
        except Exception as error:
            save('failure-'+action+'.json',dict(action=action,error=repr(error)));raise
