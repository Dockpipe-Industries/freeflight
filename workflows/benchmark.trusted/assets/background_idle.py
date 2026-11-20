# SPDX-License-Identifier: Apache-2.0
"""Repeated, isolated idle accounting; diagnostic build is never latency-timed."""
import hashlib
import json
import os
from pathlib import Path
import queue
import shutil
import subprocess
import threading
import time

repo = Path.cwd()
receipt = repo / 'bin/.local/benchmarks/trusted' / os.environ['FREEFLIGHT_BACKGROUND_RECEIPT']
config = json.loads((receipt / 'provenance.json').read_text())
label = os.environ.get('FREEFLIGHT_BACKGROUND_IDLE_LABEL', 'idle-cost-qualified')
assert label and all(c.isalnum() or c in '-_' for c in label)
out = receipt / label
out.mkdir(exist_ok=False)
variant = os.environ.get('FREEFLIGHT_BACKGROUND_IDLE_VARIANT', 'candidate')
assert variant in ('baseline', 'candidate', 'both')
variants = ['baseline', 'candidate'] if variant == 'both' else [variant]
shutil.copy2(__file__, out / 'adapter-source.py')

def prepare(selected):
    buildOut = out / selected if variant == 'both' else out
    buildOut.mkdir(exist_ok=True)
    source = buildOut / 'source'
    shutil.copytree(receipt / selected / 'source', source)
    program = source / 'workers/roslyn/Program.cs'
    original = program.read_bytes()
    assert hashlib.sha256(original).hexdigest() == config['variants'][selected]['sourceHashes']['workers/roslyn/Program.cs']
    s = original.decode().replace('    private long backgroundAttempts;', '    private long testBackgroundCompletions;\n    private long backgroundAttempts;')
    s = s.replace('            await Refresh(token, forceAll: true);',
                  '            await Refresh(token, forceAll: true);\n            testBackgroundCompletions++;')
    anchor = '        if (method != "open" && new[]'
    pos = s.index(anchor)
    s = s[:pos] + '''        if (method == "test.idle.stats") return new
            {
                cpuMs=System.Diagnostics.Process.GetCurrentProcess().TotalProcessorTime.TotalMilliseconds,
                allocatedBytes=GC.GetTotalAllocatedBytes(true), gcPauseMs=GC.GetTotalPauseDuration().TotalMilliseconds,
                gen0=GC.CollectionCount(0),gen1=GC.CollectionCount(1),gen2=GC.CollectionCount(2),
                workingSetBytes=System.Diagnostics.Process.GetCurrentProcess().WorkingSet64,
                managedHeapBytes=GC.GetTotalMemory(false),
                bytesRead, readFiles, backgroundAttempts, backgroundFailures, backgroundAborts,
                fullRecoveries, testBackgroundCompletions, committedBytes
            };
    ''' + s[pos:]
    program.write_text(s)
    with (buildOut / 'build.log').open('w') as log:
        subprocess.run([config['dotnet'], 'build', str(source / 'workers/roslyn/FreeFlight.Roslyn.csproj'),
                        '-c', 'Release', '-p:RestoreLockedMode=true', '--disable-build-servers',
                        '--artifacts-path', str(buildOut / 'build')], stdout=log, stderr=subprocess.STDOUT, check=True)
    return buildOut / 'build/bin/FreeFlight.Roslyn/release/FreeFlight.Roslyn.dll'

dlls = {selected: prepare(selected) for selected in variants}
fixture = dict(config['fixtures']['5845'])
fixture['root'] = str(Path(fixture['root']).resolve())
target = str(Path(fixture['root']) / 'source/P00/Nested/C0.cs')
results = []
sessions = int(os.environ.get('FREEFLIGHT_BACKGROUND_IDLE_SESSIONS', '3'))
assert sessions >= 2
manifest = dict(variant=variant, sessions=sessions, fixture=fixture,
    sourceHashes={selected: config['variants'][selected]['sourceHashes'] for selected in variants},
    dlls={selected: dict(path=str(dll), sha256=hashlib.sha256(dll.read_bytes()).hexdigest()) for selected,dll in dlls.items()},
    adapterSha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    sequence=[dict(pair=pair,variant=selected,mode=mode) for pair in range(sessions)
        for selected in (variants if pair%2==0 else list(reversed(variants)))
        for mode in (['foreground-only','background'] if pair%2==0 else ['background','foreground-only'])])
(out / 'run-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')

for pair in range(sessions):
    selectedOrder = variants if pair % 2 == 0 else list(reversed(variants))
    for selected in selectedOrder:
        dll = dlls[selected]
        modes = ['foreground-only', 'background'] if pair % 2 == 0 else ['background', 'foreground-only']
        for mode in modes:
            name = (f'{selected}-' if variant == 'both' else '') + f'{pair}-{mode}'
            log = (out / (name + '.stderr')).open('w')
            process = subprocess.Popen([config['dotnet'], str(dll), '--trusted-msbuild', '--incremental-validation',
                        *(['--background-recovery'] if mode == 'background' else [])],
                        stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=log, text=True)
            replies = queue.Queue()

            def read(worker=process, output=replies):
                for line in worker.stdout:
                    output.put(json.loads(line))

            threading.Thread(target=read, daemon=True).start()
            seq = 0

            def call(method, **params):
                global seq
                seq += 1
                start = time.perf_counter_ns()
                process.stdin.write(json.dumps(dict(id=seq, method=method, params=params)) + '\n')
                process.stdin.flush()
                result = replies.get(timeout=60)
                assert result['id'] == seq and 'result' in result, result
                return result['result'], (time.perf_counter_ns()-start)/1e6

            def outline():
                result, ms = call('symbols', file=target)
                assert {x['name'] for x in result} == {'P00', 'C0', 'Value'}
                return ms

            try:
                loaded, _ = call('open', root=fixture['root'], project=fixture['project'])
                assert loaded['files'] == 5845
                start = time.monotonic()
                warm = 0
                while time.monotonic()-start < 8:
                    outline()
                    warm += 1
                for interval in range(2):
                    before, _ = call('test.idle.stats')
                    start = time.monotonic()
                    time.sleep(5.2)
                    after, _ = call('test.idle.stats')
                    duration = time.monotonic()-start
                    delta = {k: after[k]-before[k] for k in before}
                    assert delta['backgroundFailures'] == delta['backgroundAborts'] == 0
                    if mode == 'background':
                        assert delta['testBackgroundCompletions'] >= 1, 'No successful maintenance completion'
                        assert delta['fullRecoveries'] == delta['testBackgroundCompletions']
                        assert delta['readFiles'] == 5845 * delta['testBackgroundCompletions']
                        assert delta['bytesRead'] == before['committedBytes'] * delta['testBackgroundCompletions']
                    else:
                        assert delta['backgroundAttempts'] == delta['testBackgroundCompletions'] == delta['fullRecoveries'] == 0
                        assert delta['bytesRead'] == delta['readFiles'] == 0
                    results.append(dict(variant=selected, mode=mode, pair=pair, interval=interval, warmupQueries=warm,
                        idleSeconds=duration, before=before, after=after, delta=delta, afterIdleOutlineMs=outline()))
                    (out / 'observations.json').write_text(json.dumps(results, indent=2)+'\n')
            finally:
                process.stdin.close()
                try:
                    process.wait(timeout=15)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait()
                    raise
                log.close()
            assert process.returncode == 0
            assert 'Unhandled exception' not in (out / (name+'.stderr')).read_text()
            print(name, 'passed', flush=True)

result = dict(status='passed', variant=variant, sessions=sessions, sourceHashes=({selected: config['variants'][selected]['sourceHashes'] for selected in variants} if variant == 'both' else config['variants'][variant]['sourceHashes']),
    adapterSha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(), observations=results,
    scope=f'Frozen {variant} source(s), alternating source order when both, with maintenance off/on, {sessions} alternating process pairs, two 5.2-second intervals each. Whole-process CPU/GC/allocation/RSS includes runtime and stats probes; no sampler in ordinary MCP timing. Successful sweeps verified by completion counter, published full recovery count and exact all-file bytes. This is synthetic macOS qualification, not production or cross-platform cost.')
(out / 'result.json').write_text(json.dumps(result, indent=2)+'\n')
