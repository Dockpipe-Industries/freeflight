# SPDX-License-Identifier: Apache-2.0
"""Generated production-semaphore handoff probes; never used for latency timing."""
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
label = os.environ.get('FREEFLIGHT_BACKGROUND_GAP_LABEL', 'handoff-fallback-proof')
assert label and all(c.isalnum() or c in '-_' for c in label)
out = receipt / label
out.mkdir(exist_ok=False)
source = out / 'source'
shutil.copytree(receipt / 'candidate/source', source)
program = source / 'workers/roslyn/Program.cs'
original = program.read_bytes()
assert hashlib.sha256(original).hexdigest() == config['variants']['candidate']['sourceHashes']['workers/roslyn/Program.cs']
s = original.decode()
# These seams only arrange scheduling and observe state. The actual gate release,
# uncancellable reacquisition, lifetime cancellation and revision check stay intact.
s = s.replace('        backgroundAttempts++;', '''        backgroundAttempts++;
        var probe = Environment.GetEnvironmentVariable("FREEFLIGHT_TEST_HANDOFF_DIR");
        if (probe is not null && File.Exists(Path.Combine(probe, "armed")) &&
            !File.Exists(Path.Combine(probe, "suspended")))
        {
            File.WriteAllText(Path.Combine(probe, "maintenance-owned"),
                JsonSerializer.Serialize(new { ageMs=Environment.TickCount64-recoveredAt, fullRecoveries }));
            while (!File.Exists(Path.Combine(probe, "request-queued"))) await Task.Delay(1, token);
        }''')
old = '                            gate.Release();\n                            await Task.Yield();'
assert s.count(old) == 1
s = s.replace(old, '''                            gate.Release();
                            var probe = Environment.GetEnvironmentVariable("FREEFLIGHT_TEST_HANDOFF_DIR");
                            if (probe is not null && File.Exists(Path.Combine(probe, "armed")) &&
                                !File.Exists(Path.Combine(probe, "suspended")))
                            {
                                File.WriteAllText(Path.Combine(probe, "suspended"), "gate released");
                                var condition = Environment.GetEnvironmentVariable("FREEFLIGHT_TEST_HANDOFF_MODE") == "shutdown"
                                    ? "foreground-entered" : "resume";
                                while (!File.Exists(Path.Combine(probe, condition))) await Task.Delay(1);
                            }
                            await Task.Yield();''')
s = s.replace('                            await gate.WaitAsync();', '''                            await gate.WaitAsync();
                            if (probe is not null) File.WriteAllText(Path.Combine(probe, "reacquired"), "owned");''')
s = s.replace('                        await gate.WaitAsync(cts.Token);', '''                        if (method == "test.hold")
                            File.WriteAllText(Path.Combine(Environment.GetEnvironmentVariable("FREEFLIGHT_TEST_HANDOFF_DIR")!, "request-queued"), "queued");
                        await gate.WaitAsync(cts.Token);''')
s = s.replace('        await Task.WhenAll(jobs.Append(maintenance));', '''        await Task.WhenAll(jobs.Append(maintenance));
        var joinedProbe = Environment.GetEnvironmentVariable("FREEFLIGHT_TEST_HANDOFF_DIR");
        if (joinedProbe is not null) File.WriteAllText(Path.Combine(joinedProbe, "joined"), "joined before disposal");''')
anchor = '        if (method != "open" && new[]'
pos = s.index(anchor)
s = s[:pos] + '''        if (method == "test.stats")
        {
            if (args.TryGetProperty("quiet", out var quiet) && quiet.GetBoolean()) watcher!.EnableRaisingEvents=false;
            return new { fullRecoveries, recoveredAt, backgroundAttempts, backgroundAborts,
                backgroundFailures, bytesRead, committedBytes,
                hashes=fingerprints.OrderBy(x=>x.Key).ToArray() };
        }
        if (method == "test.hold")
        {
            var probe=Environment.GetEnvironmentVariable("FREEFLIGHT_TEST_HANDOFF_DIR")!;
            File.WriteAllText(Path.Combine(probe,"foreground-entered"),"foreground owns gate");
            if (Environment.GetEnvironmentVariable("FREEFLIGHT_TEST_HANDOFF_MODE")=="shutdown")
                await Task.Delay(Timeout.Infinite,token);
            else await Task.Delay(1500,token);
            return new { held=true };
        }
''' + s[pos:]
program.write_text(s)
with (out / 'build.log').open('w') as log:
    subprocess.run([config['dotnet'], 'build', str(source / 'workers/roslyn/FreeFlight.Roslyn.csproj'),
                    '-c', 'Release', '-p:RestoreLockedMode=true', '--disable-build-servers',
                    '--artifacts-path', str(out / 'build')], stdout=log, stderr=subprocess.STDOUT, check=True)
dll = out / 'build/bin/FreeFlight.Roslyn/release/FreeFlight.Roslyn.dll'
checks = []


def wait_file(path, process, seconds=12):
    deadline = time.monotonic() + seconds
    while not path.exists():
        assert process.poll() is None, 'worker exited before ' + path.name
        if time.monotonic() > deadline:
            raise TimeoutError('waiting for ' + path.name)
        time.sleep(.005)


for mode in ('shutdown', 'fallback'):
    directory = out / mode
    directory.mkdir()
    root = directory / 'fixture'
    fixture = config['fixtures']['433']
    shutil.copytree(fixture['root'], root)
    project = root / fixture['project']
    with (directory / 'restore.log').open('w') as log:
        subprocess.run([config['dotnet'], 'restore', str(project), '--ignore-failed-sources'],
                       stdout=log, stderr=subprocess.STDOUT, check=True)
    env = dict(os.environ, FREEFLIGHT_TEST_HANDOFF_DIR=str(directory), FREEFLIGHT_TEST_HANDOFF_MODE=mode)
    log = (directory / 'worker.stderr').open('w')
    process = subprocess.Popen([config['dotnet'], str(dll), '--trusted-msbuild', '--incremental-validation',
                                '--background-recovery'], env=env, stdin=subprocess.PIPE,
                               stdout=subprocess.PIPE, stderr=log, text=True)
    replies = queue.Queue()

    def read(worker=process, output=replies):
        for line in worker.stdout:
            output.put(json.loads(line))

    threading.Thread(target=read, daemon=True).start()
    seq = 0

    def send(method, **params):
        global seq
        seq += 1
        process.stdin.write(json.dumps(dict(id=seq, method=method, params=params)) + '\n')
        process.stdin.flush()
        return seq

    def call(method, **params):
        request = send(method, **params)
        result = replies.get(timeout=30)
        assert result['id'] == request and 'result' in result, result
        return result['result']

    try:
        opened = call('open', root=str(root), project=fixture['project'])
        assert opened['files'] == 433
        before = call('test.stats', quiet=True)
        (directory / 'armed').touch()
        wait_file(directory / 'maintenance-owned', process)
        hold_id = send('test.hold')
        wait_file(directory / 'suspended', process)
        wait_file(directory / 'foreground-entered', process)
        owned = json.loads((directory / 'maintenance-owned').read_text())
        assert 4000 <= owned['ageMs'] < 5000, owned
        if mode == 'shutdown':
            start = time.monotonic()
            process.stdin.close()
            process.wait(timeout=5)
            assert process.returncode == 0
            cancelled = replies.get(timeout=1)
            assert cancelled['id'] == hold_id and 'cancelled' in cancelled['error']['message'].lower()
            assert (directory / 'reacquired').exists() and (directory / 'joined').exists()
            checks.append(dict(case='EOF during real semaphore handoff', elapsedMs=(time.monotonic()-start)*1000,
                               gateReleased=True, foregroundOwned=True, reacquired=True, joinedBeforeDisposal=True))
        else:
            changed = root / 'source/P00/Nested/C2.cs'
            initial = changed.read_bytes()
            stamp = changed.stat()
            changed.write_bytes(initial.replace(b'Value', b'Other'))
            os.utime(changed, ns=(stamp.st_atime_ns, stamp.st_mtime_ns))
            held = replies.get(timeout=4)
            assert held['id'] == hold_id and 'result' in held
            assert not (directory / 'reacquired').exists()
            target = root / 'source/P00/Nested/C0.cs'
            result = call('symbols', file=str(target))  # Ordinary query, not rename or a forced-recovery test method.
            assert {x['name'] for x in result} == {'P00', 'C0', 'Value'}
            after = call('test.stats')
            assert after['fullRecoveries'] == before['fullRecoveries'] + 1
            assert after['recoveredAt'] - before['recoveredAt'] >= 5000
            assert after['backgroundFailures'] == before['backgroundFailures']
            assert {x['key']: x['value'] for x in after['hashes']}[str(changed)] == hashlib.sha256(changed.read_bytes()).hexdigest()
            (directory / 'resume').touch()
            wait_file(directory / 'reacquired', process)
            deadline = time.monotonic() + 3
            final = call('test.stats')
            while final['backgroundAborts'] == before['backgroundAborts'] and time.monotonic() < deadline:
                time.sleep(.01)
                final = call('test.stats')
            assert final['backgroundAborts'] == before['backgroundAborts'] + 1
            assert final['fullRecoveries'] == after['fullRecoveries']
            assert {x['name'] for x in call('symbols', file=str(changed))} == {'P00', 'C2', 'Other'}
            checks.append(dict(case='ordinary foreground five-second fallback during suspended maintenance',
                               suspensionAgeMs=owned['ageMs'], fallbackAgeMs=after['recoveredAt']-before['recoveredAt'],
                               foregroundFullRecoveries=1, suppressedEventRecovered=True, olderSweepAborted=True))
            process.stdin.close()
            process.wait(timeout=5)
            assert process.returncode == 0
    finally:
        if process.poll() is None:
            process.kill()
            process.wait()
        log.close()
    errors = (directory / 'worker.stderr').read_text()
    assert 'Unhandled exception' not in errors and 'SemaphoreFullException' not in errors
    (out / 'result.json').write_text(json.dumps(dict(status='passed' if len(checks)==2 else 'partial', checks=checks,
        sourceSha256=hashlib.sha256(original).hexdigest(), instrumentedSha256=hashlib.sha256(program.read_bytes()).hexdigest(),
        adapterSha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()), indent=2)+'\n')
print(json.dumps(checks, indent=2))
