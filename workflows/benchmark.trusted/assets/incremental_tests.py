# SPDX-License-Identifier: Apache-2.0
"""Generated-only fault controls; never part of production or timing binaries."""
import hashlib
import json
import os
from pathlib import Path
import queue
import shutil
import subprocess
import sys
import threading

dotnet, source, destination, fixture = sys.argv[1:]
out = Path(destination)
out.mkdir(parents=True)
copy = out / 'source'
shutil.copytree(source, copy)
program = copy / 'workers/roslyn/Program.cs'
s = program.read_text()
s = s.replace('    private long fullRecoveries;', '    private bool testCancel;\n    private bool testInvalidate;\n    private string? testEvent;\n    private long fullRecoveries;')
anchor = '        if (method != "open" && new[]'
pos = s.index(anchor)
s = s[:pos] + '''        if (method == "test.control")
        {
            var action = args.GetProperty("action").GetString();
            if (action == "quiet") watcher!.EnableRaisingEvents = false;
            if (action == "lost") { watcher?.Dispose(); watcher = null; }
            if (action == "overflow") Interlocked.Increment(ref invalidationGeneration);
            if (action == "expire") recoveredAt -= 5001;
            if (action == "dirty") MarkDirty(args.GetProperty("file").GetString()!);
            if (action == "cancel") testCancel = true;
            if (action == "during-event") testEvent = args.GetProperty("file").GetString();
            if (action == "during-overflow") testInvalidate = true;
            if (action == "capacity")
                for (var i = 0; i < 4097; i++) MarkDirty(Path.Combine(root!, "lost-event-" + i));
            return new { committedBytes, recoveredAt, recoveredGeneration,
                fingerprints = fingerprints.OrderBy(x => x.Key).ToArray(),
                snapshots = snapshots.OrderBy(x => x.Key).ToArray(),
                dirty = dirtyFiles.OrderBy(x => x.Key).ToArray() };
        }
''' + s[pos:]
anchor = '        token.ThrowIfCancellationRequested();\n        if (incrementalValidation && startGeneration'
s = s.replace(anchor, '''        if (testEvent is not null) { MarkDirty(testEvent); testEvent = null; }
        if (testInvalidate) { testInvalidate = false; Interlocked.Increment(ref invalidationGeneration); }
        if (testCancel) { testCancel = false; throw new OperationCanceledException(); }
''' + anchor)
program.write_text(s)
from transaction import instrument
instrument(program)
with (out / 'build.log').open('w') as log:
    subprocess.run([dotnet, 'build', str(copy / 'workers/roslyn/FreeFlight.Roslyn.csproj'), '-c', 'Release', '--disable-build-servers', '--artifacts-path', str(out / 'build')], check=True, stdout=log, stderr=subprocess.STDOUT)
root = out / 'fixture'
shutil.copytree(fixture, root)
with (out / 'restore.log').open('w') as log:
    subprocess.run([dotnet, 'restore', str(root / 'source/P01/P01.csproj')], check=True, stdout=log, stderr=subprocess.STDOUT)
dll = out / 'build/bin/FreeFlight.Roslyn/release/FreeFlight.Roslyn.dll'
log = (out / 'worker.stderr').open('w')
p = subprocess.Popen([dotnet, str(dll), '--trusted-msbuild', '--incremental-validation'], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=log, text=True)
q = queue.Queue()
def reader():
    for line in p.stdout:
        q.put(line)
threading.Thread(target=reader, daemon=True).start()
seq = 0
receipts = []
def call(method, **params):
    global seq
    seq += 1
    p.stdin.write(json.dumps(dict(id=seq, method=method, params=params)) + '\n')
    p.stdin.flush()
    reply = json.loads(q.get(timeout=90))
    receipts.append(dict(method=method, params=params, reply=reply))
    return reply

def ok(method, **params):
    reply = call(method, **params)
    assert 'result' in reply, reply
    return reply['result']

def control(action, **params):
    return ok('test.control', action=action, **params)

def state():
    value = control('state')
    return {k: value[k] for k in ('committedBytes', 'recoveredAt', 'recoveredGeneration', 'fingerprints', 'snapshots', 'dirty')}

def outline(path):
    return ok('symbols', file=str(path))

target = root / 'source/P00/Nested/C0.cs'
caller = root / 'source/P01/Nested/C1.cs'
late = root / 'source/P01/Nested/C431.cs'
original = target.read_bytes()
stamp = target.stat()
checks = []
try:
    ok('open', root=str(root), project='source/P01/P01.csproj')
    assert ok('capabilities')['validationMode'] == 'incremental-with-recovery'
    control('quiet')
    # No watcher delivery: target is fresh, dependency remains old until recovery.
    target.write_bytes(original.replace(b'Value', b'Other'))
    os.utime(target, ns=(stamp.st_atime_ns, stamp.st_mtime_ns))
    position = caller.read_text().index('.Value()') + 2
    assert ok('definition', file=str(caller), line=0, character=position), 'Dependency unexpectedly absent before recovery'
    control('expire')
    assert ok('definition', file=str(caller), line=0, character=position) == [], 'Lost event was not recovered'
    checks.append('lost same-size/restored-mtime dependency recovered at deadline; cross-project semantics')
    assert any(x['name'] == 'Other' for x in outline(target))
    target.write_bytes(original)
    os.utime(target, ns=(stamp.st_atime_ns, stamp.st_mtime_ns))
    assert any(x['name'] == 'Value' for x in outline(target))
    checks.append('fresh target ignores metadata equality')
    for action in ('overflow', 'capacity'):
        target.write_bytes(original.replace(b'Value', b'Other'))
        control(action)
        assert ok('definition', file=str(caller), line=0, character=position) == []
        target.write_bytes(original)
        control('dirty', file=str(target))
        assert ok('definition', file=str(caller), line=0, character=position)
        checks.append(action + ' forces full content recovery')
    # A changed dependency event is sufficient without forcing a recovery.
    target.write_bytes(original.replace(b'Value', b'Other'))
    control('dirty', file=str(target))
    assert ok('definition', file=str(caller), line=0, character=position) == []
    target.write_bytes(original)
    control('dirty', file=str(target))
    outline(caller)
    checks.append('incremental cross-project dirty dependency updates')
    control('dirty', file=str(target))
    control('during-event', file=str(target))
    outline(caller)
    assert any(x['key'] == str(target) for x in state()['dirty'])
    outline(caller)
    assert not state()['dirty']
    checks.append('event arriving during refresh survives captured-version acknowledgment')
    control('dirty', file=str(target))
    control('during-overflow')
    before = state()
    assert 'error' in call('symbols', file=str(caller))
    assert state() == before
    outline(caller)
    checks.append('overflow during refresh rejects publication and recovers next query')
    # Cancellation after staged reads must preserve all state and pending events.
    target.write_bytes(original.replace(b'Value', b'Other'))
    control('dirty', file=str(target))
    control('cancel')
    before = state()
    assert 'error' in call('symbols', file=str(caller))
    assert state() == before
    assert ok('definition', file=str(caller), line=0, character=position) == []
    checks.append('cancelled staged refresh preserves semantic state, resource total, recovery deadline and pending events')
    target.write_bytes(original)
    outline(target)
    saved = late.read_bytes()
    late.unlink()
    control('dirty', file=str(late))
    before = state()
    assert 'error' in call('symbols', file=str(target))
    assert state() == before
    late.write_bytes(saved)
    outline(target)
    checks.append('delete failure is transactional and retryable')
    moved = late.with_suffix('.moved')
    late.rename(moved)
    control('dirty', file=str(late))
    control('dirty', file=str(moved))
    assert 'error' in call('symbols', file=str(target))
    moved.rename(late)
    outline(target)
    checks.append('rename unknown path triggers conservative recovery')
    nested = target.parent
    parked = nested.with_name('parked')
    nested.rename(parked)
    nested.symlink_to(parked, target_is_directory=True)
    control('dirty', file=str(nested))
    assert 'error' in call('symbols', file=str(caller))
    nested.unlink()
    parked.rename(nested)
    outline(caller)
    checks.append('ancestor replacement rejected during recovery')
    (root / '.swap-before-read').write_text('test')
    outside = out / 'outside-ancestor'
    outside.mkdir()
    (outside / 'C0.cs').write_bytes(original)
    before_bytes = ok('capabilities')['refreshStats']['bytesRead']
    assert 'error' in call('symbols', file=str(target))
    assert ok('capabilities')['refreshStats']['bytesRead'] == before_bytes
    nested.unlink()
    (root / '.saved-ancestor').rename(nested)
    outline(target)
    checks.append('uncached validation rejects ancestor swap immediately before read')
    preview = ok('rename', file=str(target), line=0, character=45, newName='Next')
    edit = next(x for x in preview['edits'] if x['file'] == str(target))
    assert edit['expectedSha256'] == hashlib.sha256(target.read_bytes()).hexdigest()
    checks.append('preview forces full sweep and exact current hash')
    # Reopen with a tight aggregate ceiling; unchanged committed bytes count too.
    total = sum(x.stat().st_size for x in root.glob('source/P*/Nested/*.cs'))
    ok('open', root=str(root), project='source/P01/P01.csproj',
       resources={'maxFileBytes': total, 'maxWorkspaceBytes': total + 16})
    control('quiet')
    target.write_bytes(original + b' ' * 32)
    before = state()
    failure = call('symbols', file=str(target))
    assert failure['error']['resource'] == 'maxWorkspaceBytes', failure
    assert state() == before
    target.write_bytes(original)
    outline(target)
    checks.append('incremental aggregate resource accounting includes unselected inputs and rolls back')
    # Exact external inputs remain fresh without watcher coverage and read-only.
    outside_file = out / 'external.cs'
    outside_file.write_text('class External { int Read(P00.C0 value) => value.Value(); }')
    project = root / 'source/P01/P01.csproj'
    project.write_text(project.read_text().replace('</Project>',
        '<ItemGroup><Compile Include="' + str(outside_file) + '" /></ItemGroup></Project>'))
    ok('open', root=str(root), project='source/P01/P01.csproj')
    control('quiet')
    assert 'error' in call('symbols', file=str(outside_file))
    failure = call('rename', file=str(target), line=0, character=45, newName='Next')
    assert failure['error']['code'] == 'external_input_read_only', failure
    external_text = outside_file.read_text()
    backing = outside_file.with_suffix('.backing')
    backing.write_text(external_text)
    outside_file.unlink()
    outside_file.symlink_to(backing)
    assert 'error' in call('symbols', file=str(caller))
    outside_file.unlink()
    outside_file.write_text(external_text)
    outline(caller)
    checks.append('incremental external inputs remain exact, uncached, symlink-rejecting and read-only')
    control('lost')
    target.write_bytes(original.replace(b'Value', b'Other'))
    assert ok('definition', file=str(caller), line=0, character=position) == []
    checks.append('unavailable watcher falls back to full content validation')
finally:
    p.stdin.close()
    p.wait(timeout=20)
    log.close()
    (out / 'raw.json').write_text(json.dumps(receipts, indent=2))
assert 'BENCH_TRANSACTION_FAILURE' not in (out / 'worker.stderr').read_text()
(out / 'summary.json').write_text(json.dumps(dict(status='passed', checks=checks, generatedSourceSha256=hashlib.sha256(program.read_bytes()).hexdigest()), indent=2))
print('Incremental proof passed:', len(checks), 'checks')
