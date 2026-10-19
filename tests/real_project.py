# SPDX-License-Identifier: Apache-2.0
"""Workflow-owned real-project qualification, never opens arbitrary user projects."""
import hashlib
import json
import os
from pathlib import Path
import queue
import re
import shutil
import subprocess
import tempfile
import threading
import time

repo = Path(__file__).resolve().parents[1]
generated = repo / 'bin/.local'
source = repo / 'workers/roslyn'
dotnet = shutil.which('dotnet')
assert dotnet, 'Provision the pinned .NET SDK on PATH'
binary = generated / 'build/freeflight'
if not binary.exists():
    binary = generated / 'build/Release/freeflight.exe'
worker = generated / 'roslyn/bin/FreeFlight.Roslyn/debug/FreeFlight.Roslyn.dll'
assert binary.is_file() and worker.is_file(), 'Run core.build and workers.roslyn first'
meta = {'io.modelcontextprotocol/protocolVersion': '2026-07-28',
        'io.modelcontextprotocol/clientCapabilities': {}}


def position(text, offset):
    before = text[:offset]
    return {'line': before.count('\n'),
            'character': len(before.rsplit('\n', 1)[-1].encode('utf-16-le')) // 2}


with tempfile.TemporaryDirectory(prefix='real-roslyn-', dir=generated) as directory:
    root = Path(directory).resolve()
    inputs = sorted(source.glob('*.cs')) + [source / 'FreeFlight.Roslyn.csproj', source / 'packages.lock.json']
    hashes = {path.name: hashlib.sha256(path.read_bytes()).hexdigest() for path in inputs}
    for path in inputs:
        shutil.copyfile(path, root / path.name)
    shutil.copyfile(repo / 'global.json', root / 'global.json')
    env = os.environ.copy()
    env['DOTNET_ROOT'] = str(Path(dotnet).resolve().parent)
    env['DOTNET_CLI_TELEMETRY_OPTOUT'] = '1'
    env['DOTNET_GENERATE_ASPNET_CERTIFICATE'] = 'false'
    env['DOTNET_NOLOGO'] = '1'
    # Explicit restore of this known project only, with its checked-in lock graph.
    subprocess.run([dotnet, 'restore', str(root / 'FreeFlight.Roslyn.csproj'),
                    '-p:RestoreLockedMode=true', '--ignore-failed-sources'],
                   cwd=root, env=env, check=True, timeout=180)
    config = root / 'freeflight-test.json'
    config.write_text(json.dumps({'roots': [str(root)], 'engines': {
        'csharp': [dotnet, str(worker), '--trusted-msbuild']}}), encoding='utf-8')
    process = subprocess.Popen([str(binary), '--config', str(config)], cwd=root,
                               stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                               text=True, encoding='utf-8', env=env)
    replies = queue.Queue()

    def read():
        for line in process.stdout:
            replies.put(line)
        replies.put(None)

    threading.Thread(target=read, daemon=True).start()
    sequence = 0
    measurements = {}

    def request(method, params):
        global sequence
        sequence += 1
        process.stdin.write(json.dumps({'jsonrpc': '2.0', 'id': sequence, 'method': method,
                                       'params': {**params, '_meta': meta}}) + '\n')
        process.stdin.flush()
        raw = replies.get(timeout=120)
        assert raw is not None, 'MCP exited before responding'
        response = json.loads(raw)
        assert response.get('id') == sequence and 'error' not in response, response
        assert not response['result'].get('isError'), response
        return response['result']

    def query(operation, **arguments):
        started = time.perf_counter()
        value = request('tools/call', {'name': 'semantic.query', 'arguments': {
            'root': str(root), 'language': 'csharp', 'operation': operation,
            'arguments': arguments}})['structuredContent']
        measurements.setdefault(operation, []).append(round((time.perf_counter() - started) * 1000, 3))
        return value.get('items', value)

    try:
        request('server/discover', {})
        caps = request('tools/call', {'name': 'engine.capabilities', 'arguments': {
            'root': str(root), 'language': 'csharp'}})['structuredContent']
        assert caps['fidelity'] == 'trusted-msbuild', caps
        semantic = (root / 'SemanticQueries.cs').read_text(encoding='utf-8')
        program = (root / 'Program.cs').read_text(encoding='utf-8')
        declaration = position(semantic, semantic.index('class SemanticQueries') + len('class '))
        expected_refs = [position(program, match.start()) for match in re.finditer(r'\bSemanticQueries\.', program)]
        assert len(expected_refs) == 6, 'Update exact reference contract after intentional worker changes'
        definition = query('definition', file=str(root / 'Program.cs'), **expected_refs[0])
        assert len(definition) == 1, definition
        assert Path(definition[0]['file']).resolve() == root / 'SemanticQueries.cs', definition
        assert definition[0]['range']['start'] == declaration, definition
        refs = query('references', file=str(root / 'SemanticQueries.cs'), **declaration)
        assert len(refs) == len(expected_refs), refs
        assert all(Path(item['file']).resolve() == root / 'Program.cs' for item in refs), refs
        assert sorted((item['range']['start']['line'], item['range']['start']['character']) for item in refs) == sorted((p['line'], p['character']) for p in expected_refs), refs
        for path in inputs:
            if path.suffix == '.cs':
                diagnostics = query('diagnostics', file=str(root / path.name))
                if path.name == 'TrustedProjectLoader.cs':
                    # Roslyn reports the real project's existing unused namespace import.
                    assert len(diagnostics) == 1 and diagnostics[0]['code'] == 'CS8019' and diagnostics[0]['severity'] == 'hidden', diagnostics
                    original = path.read_text(encoding='utf-8')
                    assert diagnostics[0]['location']['range']['start'] == position(original, original.index('using Microsoft.CodeAnalysis.Text;')), diagnostics
                else:
                    assert diagnostics == [], (path.name, diagnostics)
        # Modify only the disposable copy and verify exact live compiler error location.
        broken = semantic + '\ninternal sealed class RealProjectDiagnosticProbe { public int Value => "invalid"; }\n'
        (root / 'SemanticQueries.cs').write_text(broken, encoding='utf-8')
        diagnostics = query('diagnostics', file=str(root / 'SemanticQueries.cs'))
        assert len(diagnostics) == 1 and diagnostics[0]['code'] == 'CS0029', diagnostics
        assert diagnostics[0]['location']['range']['start'] == position(broken, broken.rindex('"invalid"')), diagnostics
        (root / 'SemanticQueries.cs').write_text(semantic, encoding='utf-8')
        assert query('diagnostics', file=str(root / 'SemanticQueries.cs')) == []
        report = {'project': 'FreeFlight.Roslyn.csproj', 'mode': 'trusted-msbuild',
                  'transport': 'C++ MCP stdio', 'sourceFiles': len(list(root.glob('*.cs'))),
                  'sourceSha256': hashes, 'crossFileReferenceCount': len(refs),
                  'assertions': ['exact SemanticQueries definition range', 'all six cross-file references',
                                 'no original errors/warnings; exact existing hidden CS8019 import', 'exact injected CS0029 location',
                                 'diagnostic removal after incremental refresh'],
                  'latencyMs': measurements,
                  'limitations': ['One actual project; not a large solution benchmark.',
                                  'Explicitly trusted own project; MSBuild is not sandboxed.']}
        output = generated / 'reports'
        output.mkdir(parents=True, exist_ok=True)
        (output / 'real-project.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
        print(json.dumps(report, indent=2))
    finally:
        process.stdin.close()
        try:
            process.wait(timeout=15)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)
            raise
        process.stdout.close()
        assert process.returncode == 0, process.returncode
        assert hashes == {path.name: hashlib.sha256(path.read_bytes()).hexdigest() for path in inputs}, 'Original source changed during qualification'
