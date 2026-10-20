# SPDX-License-Identifier: Apache-2.0
"""Windows-only controlled legacy project qualification; never opens arbitrary projects."""
import argparse
import sys
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

if sys.platform != 'win32':
    raise SystemExit('Legacy .NET Framework qualification requires Windows and the .NET Framework developer/targeting packs; no pass recorded.')

parser = argparse.ArgumentParser()
parser.add_argument('--framework', choices=('4.7', '4.8', '4.8.1'), required=True)
framework = parser.parse_args().framework
reference_root = Path(os.environ.get('ProgramFiles(x86)', 'C:/Program Files (x86)')) / 'Reference Assemblies/Microsoft/Framework/.NETFramework' / ('v' + framework)
assert (reference_root / 'mscorlib.dll').is_file(), f'Install the .NET Framework {framework} developer/targeting pack: missing {reference_root / "mscorlib.dll"}; qualification cannot skip this prerequisite'

repo = Path(__file__).resolve().parents[1]
generated = repo / 'bin/.local'
source = repo / 'workers/roslyn/fixtures/legacy-net48'
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


with tempfile.TemporaryDirectory(prefix='legacy-net48-', dir=generated) as directory:
    root = Path(directory).resolve()
    inputs = sorted(path for path in source.rglob('*') if path.is_file())
    hashes = {path.relative_to(source).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest() for path in inputs}
    shutil.copytree(source, root, dirs_exist_ok=True)
    for project in root.rglob('*.csproj'):
        project.write_text(project.read_text(encoding='utf-8').replace('<TargetFrameworkVersion>v4.8</TargetFrameworkVersion>', '<TargetFrameworkVersion>v' + framework + '</TargetFrameworkVersion>'), encoding='utf-8')
    env = os.environ.copy()
    env['DOTNET_ROOT'] = str(Path(dotnet).resolve().parent)
    env['DOTNET_CLI_TELEMETRY_OPTOUT'] = '1'
    env['DOTNET_GENERATE_ASPNET_CERTIFICATE'] = 'false'
    env['DOTNET_NOLOGO'] = '1'
    # This authored fixture has no NuGet dependencies: no restore or build needed.
    config = root / 'freeflight-test.json'
    config.write_text(json.dumps({'roots': [str(root)], 'engines': {
        'csharp': [dotnet, str(worker), '--trusted-msbuild']}}), encoding='utf-8')
    stderr_path = root / 'worker-stderr.log'
    stderr_log = stderr_path.open('wb')
    process = subprocess.Popen([str(binary), '--config', str(config)], cwd=root,
                               stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                               text=True, encoding='utf-8', env=env, stderr=stderr_log)
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
        library = (root / 'Lib/Widget.cs').read_text(encoding='utf-8')
        consumer = (root / 'App/Consumer.cs').read_text(encoding='utf-8')
        declaration = position(library, library.index('class Widget') + len('class '))
        use = position(consumer, consumer.index('Widget'))
        definition = query('definition', file=str(root / 'App/Consumer.cs'), **use)
        assert len(definition) == 1, definition
        assert Path(definition[0]['file']).resolve() == root / 'Lib/Widget.cs', definition
        assert definition[0]['range']['start'] == declaration, definition
        refs = query('references', file=str(root / 'Lib/Widget.cs'), **declaration)
        assert len(refs) == 1, refs
        assert Path(refs[0]['file']).resolve() == root / 'App/Consumer.cs', refs
        assert refs[0]['range']['start'] == use, refs
        for file in ('App/Consumer.cs', 'Lib/Widget.cs'):
            assert query('diagnostics', file=str(root / file)) == [], file
        broken = consumer.replace('value.Value', '"invalid"')
        (root / 'App/Consumer.cs').write_text(broken, encoding='utf-8')
        diagnostics = query('diagnostics', file=str(root / 'App/Consumer.cs'))
        assert len(diagnostics) == 1 and diagnostics[0]['code'] == 'CS0029', diagnostics
        assert diagnostics[0]['location']['range']['start'] == position(broken, broken.index('"invalid"')), diagnostics
        (root / 'App/Consumer.cs').write_text(consumer, encoding='utf-8')
        assert query('diagnostics', file=str(root / 'App/Consumer.cs')) == []
        toolsets = [json.loads(line) for line in stderr_path.read_text(encoding='utf-8').splitlines() if line.startswith('{') and 'freeflight.msbuild-toolset' in line]
        assert len(toolsets) == 1 and toolsets[0]['msbuildVersion'] and toolsets[0]['runtimeVersion'], toolsets
        reference_files = {name: hashlib.sha256((reference_root / name).read_bytes()).hexdigest() for name in ('mscorlib.dll', 'System.Xml.Linq.dll', 'RedistList/FrameworkList.xml')}
        report = {'toolset': toolsets[0], 'referencePack': {'path': str(reference_root), 'filesSha256': reference_files}, 'project': 'Legacy.sln', 'targetFramework': 'v' + framework,
                  'projectFormat': 'non-SDK C#', 'mode': 'trusted-msbuild',
                  'transport': 'C++ MCP stdio', 'sourceSha256': hashes,
                  'assertions': ['conditional project define and System.Xml.Linq reference resolution',
                                 'exact cross-project Widget definition and single reference',
                                 'zero original diagnostics', 'exact injected CS0029 and incremental removal'],
                  'latencyMs': measurements,
                  'limitations': ['Two controlled projects; no claim for all legacy solutions.',
                                  'No packages.config, COM, web application, VB, or untested framework qualification.',
                                  'Explicit trust required; MSBuild is not sandboxed.']}
        output = generated / 'reports'
        output.mkdir(parents=True, exist_ok=True)
        (output / ('legacy-net' + framework.replace('.', '') + '.json')).write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
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
        stderr_log.close()
        assert process.returncode == 0, process.returncode
        assert hashes == {path.relative_to(source).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest() for path in inputs}, 'Original source changed during qualification'
