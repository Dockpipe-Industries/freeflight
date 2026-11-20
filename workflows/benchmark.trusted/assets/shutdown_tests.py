# SPDX-License-Identifier: Apache-2.0
"""Force the actual Program capture -> completion/disposal -> Cancel interleaving."""
import hashlib
import json
import os
from pathlib import Path
import queue
import shutil
import subprocess
import threading
import run as trusted

label = os.environ['FREEFLIGHT_SHUTDOWN_LABEL']
assert label and all(c.isalnum() or c in '-_' for c in label)
out = trusted.REPO / 'bin/.local/benchmarks/shutdown' / label
out.mkdir(parents=True, exist_ok=False)
assert trusted.DOTNET
results = []


def build(source, destination):
    with (destination / 'build.log').open('w') as log:
        subprocess.run([trusted.DOTNET, 'build', str(source / 'workers/roslyn/FreeFlight.Roslyn.csproj'),
                        '-c', 'Release', '-p:RestoreLockedMode=true', '--disable-build-servers',
                        '--artifacts-path', str(destination / 'build')], cwd=source,
                       env=trusted.ENV, stdout=log, stderr=subprocess.STDOUT, check=True, timeout=180)
    return destination / 'build/bin/FreeFlight.Roslyn/release/FreeFlight.Roslyn.dll'


def barriers(path):
    text = path.read_text()
    anchor = 'internal static class Program\n{'
    assert text.count(anchor) == 1
    text = text.replace(anchor, anchor + '''
    private static readonly ManualResetEventSlim TestCaptured = new(false);
    private static readonly ManualResetEventSlim TestDisposed = new(false);
    private static void CapturedForTest()
    {
        TestCaptured.Set();
        if (!TestDisposed.Wait(TimeSpan.FromSeconds(10))) throw new Exception("TEST_DISPOSE_TIMEOUT");
        Console.Error.WriteLine("TEST_CAPTURE_DISPOSE_CANCEL");
    }
''')
    anchor = 'finally { active.TryRemove(key, out _); cts.Dispose(); }'
    assert text.count(anchor) == 1
    text = text.replace(anchor, '''finally {
        if (!TestCaptured.Wait(TimeSpan.FromSeconds(10))) throw new Exception("TEST_CAPTURE_TIMEOUT");
        active.TryRemove(key, out _); cts.Dispose(); TestDisposed.Set();
    }''')
    assert text.count('cancellation.Cancel();') == 2
    text = text.replace('cancellation.Cancel();', '{ CapturedForTest(); cancellation.Cancel(); }')
    path.write_text(text)


for variant, ref in [('before', '6636d94'), ('after', None)]:
    names = ['global.json'] + (trusted.git('ls-files', 'workers/roslyn').splitlines() if ref is None
                             else trusted.git('ls-tree', '-r', '--name-only', ref, 'workers/roslyn').splitlines())
    for diagnostic in (False, True):
        dest = out / (variant + ('-diagnostic' if diagnostic else '-ordinary'))
        source = dest / 'source'
        hashes = {}
        for name in names:
            data = (trusted.REPO / name).read_bytes() if ref is None else subprocess.check_output(
                ['git', 'show', ref + ':' + name], cwd=trusted.REPO)
            p = source / name; p.parent.mkdir(parents=True, exist_ok=True); p.write_bytes(data)
            hashes[name] = hashlib.sha256(data).hexdigest()
        (dest / 'source-hashes.json').write_text(json.dumps(hashes, indent=2))
        if diagnostic:
            from native_profile import instrument_worker
            instrument_worker(source)
        barriers(source / 'workers/roslyn/Program.cs')
        dll = build(source, dest)
        for mode in ('eof', 'shutdown', 'cancel'):
            p = subprocess.Popen([trusted.DOTNET, str(dll)], stdin=subprocess.PIPE,
                                 stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, env=trusted.ENV)
            replies = queue.Queue()
            def read():
                for line in p.stdout: replies.put(line)
            reader = threading.Thread(target=read, daemon=True); reader.start()
            p.stdin.write(json.dumps({'id': 1, 'method': 'capabilities', 'params': {}}) + '\n'); p.stdin.flush()
            first = json.loads(replies.get(timeout=15)); assert first['id'] == 1 and 'result' in first
            if mode != 'eof':
                p.stdin.write(json.dumps({'id': 2, 'method': mode, 'params': {'id': 1}}) + '\n'); p.stdin.flush()
            p.stdin.close()
            try: code = p.wait(timeout=15)
            except subprocess.TimeoutExpired:
                p.kill(); p.wait(); raise
            stderr = p.stderr.read(); reader.join(timeout=2)
            extra = []
            while not replies.empty(): extra.append(json.loads(replies.get()))
            (dest / (mode + '.stderr')).write_text(stderr)
            assert 'TEST_CAPTURE_DISPOSE_CANCEL' in stderr and 'TIMEOUT' not in stderr
            if variant == 'before':
                if mode == 'cancel':
                    assert code == 0 and len(extra) == 1 and 'disposed' in extra[0]['error']['message'].lower(), extra
                else: assert code != 0 and 'ObjectDisposedException' in stderr, (code, stderr)
            else: assert code == 0 and not extra and 'Unhandled exception.' not in stderr, (code, extra, stderr)
            results.append({'variant': variant, 'diagnostic': diagnostic, 'mode': mode, 'exitCode': code,
                            'first': first, 'extra': extra, 'expectedOutcomeConfirmed': True})
            print(variant, diagnostic, mode, 'expected result confirmed', flush=True)
contract = out / 'lifetime-contract'; contract.mkdir()
shutil.copyfile(trusted.REPO / 'global.json', contract / 'global.json')
shutil.copyfile(trusted.REPO / 'workers/roslyn/RequestCancellation.cs', contract / 'RequestCancellation.cs')
(contract / 'Contract.csproj').write_text('''<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup>
<OutputType>Exe</OutputType><TargetFramework>net11.0</TargetFramework><ImplicitUsings>enable</ImplicitUsings>
<Nullable>enable</Nullable><TreatWarningsAsErrors>true</TreatWarningsAsErrors></PropertyGroup></Project>''')
(contract / 'Program.cs').write_text('''using FreeFlight.Roslyn;
static void Check(bool value) { if (!value) throw new Exception("Lifetime contract failed"); }
static void Disposed(CancellationToken token) {
    try { _ = token.WaitHandle; throw new Exception("Source leaked after completion"); }
    catch (ObjectDisposedException) { }
}
using (var request = new RequestCancellation(Timeout.InfiniteTimeSpan)) {
    request.Dispose(); request.Dispose(); request.Cancel(); Disposed(request.Token);
}
using (var request = new RequestCancellation(Timeout.InfiniteTimeSpan)) {
    var calls = 0;
    using var registration = request.Token.Register(() => Interlocked.Increment(ref calls));
    request.Cancel(); request.Cancel(); Check(calls == 1 && request.Token.IsCancellationRequested);
    request.Dispose(); Disposed(request.Token);
}
using (var request = new RequestCancellation(Timeout.InfiniteTimeSpan)) {
    using var entered = new ManualResetEventSlim(); using var release = new ManualResetEventSlim();
    using var registration = request.Token.Register(() => {
        entered.Set(); Check(release.Wait(TimeSpan.FromSeconds(5)));
    });
    var cancel = Task.Run(request.Cancel); Check(entered.Wait(TimeSpan.FromSeconds(5)));
    // Completion must return while Cancel is still executing; disposal is deferred.
    request.Dispose(); request.Cancel(); Check(!cancel.IsCompleted); _ = request.Token.WaitHandle;
    release.Set(); Check(cancel.Wait(TimeSpan.FromSeconds(5))); Disposed(request.Token);
}
using (var request = new RequestCancellation(Timeout.InfiniteTimeSpan)) {
    using var registration = request.Token.Register(() => {
        // A callback can wait for another thread to finish the request: no lock cycle.
        Check(Task.Run(request.Dispose).Wait(TimeSpan.FromSeconds(5)));
    });
    request.Cancel(); Disposed(request.Token);
}
using (var request = new RequestCancellation(Timeout.InfiniteTimeSpan)) {
    using var registration = request.Token.Register(() => { request.Dispose(); throw new InvalidOperationException("expected"); });
    try { request.Cancel(); throw new Exception("Callback exception lost"); }
    catch (AggregateException error) { Check(error.InnerExceptions.Count == 1 && error.InnerException is InvalidOperationException); }
    Disposed(request.Token);
}
Console.WriteLine("Five cancellation lifetime contracts passed");
''')
with (contract / 'run.log').open('w') as log:
    subprocess.run([trusted.DOTNET, 'run', '--project', str(contract / 'Contract.csproj'), '-c', 'Release'],
                   cwd=contract, env=trusted.ENV, stdout=log, stderr=subprocess.STDOUT, check=True, timeout=90)
(out / 'summary.json').write_text(json.dumps({'status': 'passed', 'cases': results, 'lifetimeContracts': 5,
    'scope': 'Generated barriers force production Program interleaving; no timing claim.'}, indent=2))
