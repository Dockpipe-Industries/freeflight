# SPDX-License-Identifier: Apache-2.0
"""Fixed workloads through the real MCP endpoint; no direct engine shortcuts."""
import hashlib
import json
import os
from pathlib import Path
import platform
import queue
import random
import shutil
import signal
import statistics
import subprocess
import tempfile
import threading
import time

REPO = Path(__file__).resolve().parents[3]
SEED = 481516
REPEATS = 5
META = {"io.modelcontextprotocol/protocolVersion": "2026-07-28", "io.modelcontextprotocol/clientCapabilities": {}}


def summary(values):
    return {"samples": len(values), "median_ms": round(statistics.median(values), 3), "min_ms": round(min(values), 3), "max_ms": round(max(values), 3), "raw_ms": [round(value, 3) for value in values]}


class Session:
    def __init__(self, root, directory, installation=REPO):
        binary = installation / 'bin/.local/build/freeflight'
        if not binary.exists():
            binary = installation / 'bin/.local/build/Release/freeflight.exe'
        self.binary = binary
        node, dotnet = shutil.which('node'), shutil.which('dotnet')
        assert node and dotnet and binary.is_file(), 'Run DockPipe build before benchmarking'
        config = directory / 'freeflight.json'
        config.write_text(json.dumps({'roots': [str(root)], 'engines': {
            'typescript': [node, str(installation / 'bin/.local/typescript/worker.mjs')],
            'csharp': [dotnet, str(installation / 'bin/.local/roslyn/bin/FreeFlight.Roslyn/debug/FreeFlight.Roslyn.dll')]
        }}))
        self.root = root
        self.sequence = 0
        self.responses = queue.Queue()
        self.rss_samples = []
        self.stop = threading.Event()
        self.stderr = (directory / 'server.stderr.log').open('w')
        self.started = time.perf_counter()
        self.process = subprocess.Popen([str(binary), '--config', str(config)], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=self.stderr, text=True, start_new_session=os.name != 'nt')
        self.reader = threading.Thread(target=self.read_responses, daemon=True)
        self.reader.start()
        self.monitor = threading.Thread(target=self.sample_rss, daemon=True)
        self.monitor.start()
        try:
            self.request('server/discover', {})
        except Exception:
            self.close()
            raise
        self.startup_ms = (time.perf_counter() - self.started) * 1000

    def read_responses(self):
        for line in self.process.stdout:
            self.responses.put(line)
        self.responses.put(None)

    def sample_rss(self):
        if os.name == 'nt' or not shutil.which('ps'):
            return
        while not self.stop.is_set():
            try:
                result = subprocess.run(['ps', '-axo', 'pid=,ppid=,rss='], capture_output=True, text=True, check=True, timeout=5)
                rows = [tuple(map(int, line.split())) for line in result.stdout.splitlines() if line.strip()]
                pids = {self.process.pid}
                while True:
                    expanded = pids | {pid for pid, parent, rss in rows if parent in pids}
                    if expanded == pids:
                        break
                    pids = expanded
                core = next((rss for pid, parent, rss in rows if pid == self.process.pid), 0)
                total = sum(rss for pid, parent, rss in rows if pid in pids)
                self.rss_samples.append({'core_kib': core, 'tree_kib': total})
            except (OSError, ValueError, subprocess.SubprocessError):
                pass
            self.stop.wait(0.1)

    def request(self, method, params):
        self.sequence += 1
        self.process.stdin.write(json.dumps({'jsonrpc': '2.0', 'id': self.sequence, 'method': method, 'params': {**params, '_meta': META}}) + '\n')
        self.process.stdin.flush()
        response = self.responses.get(timeout=120)
        assert response is not None, 'MCP server closed before response'
        response = json.loads(response)
        assert response.get('id') == self.sequence and 'error' not in response, response
        assert not response['result'].get('isError'), response
        return response['result']

    def query(self, language, operation, **arguments):
        before = time.perf_counter()
        result = self.request('tools/call', {'name': 'semantic.query', 'arguments': {'root': str(self.root), 'language': language, 'operation': operation, 'arguments': arguments}})['structuredContent']
        return result.get('items', result), (time.perf_counter() - before) * 1000

    def close(self):
        try:
            self.process.stdin.close()
            self.process.wait(timeout=30)
        except subprocess.TimeoutExpired:
            if os.name == 'nt':
                self.process.kill()
            else:
                os.killpg(self.process.pid, signal.SIGKILL)
            self.process.wait(timeout=5)
            raise
        finally:
            self.stop.set()
            self.monitor.join(timeout=6)
            self.process.stdout.close()
            self.stderr.close()
        assert self.process.returncode == 0, self.process.returncode

    def memory(self):
        if not self.rss_samples:
            return {'status': 'unavailable', 'reason': 'ps sampling unavailable on this platform'}
        return {'status': 'sampled', 'samples': len(self.rss_samples), 'interval_target_ms': 100, 'peak_core_kib': max(s['core_kib'] for s in self.rss_samples), 'peak_tree_kib': max(s['tree_kib'] for s in self.rss_samples), 'method': 'sum of ps RSS across core and descendant workers; shared pages may be counted more than once'}


def generate(directory, count):
    root = directory / 'workspace'
    root.mkdir()
    rng = random.Random(SEED)
    digest = hashlib.sha256()
    total = 0
    def write(name, content):
        nonlocal total
        encoded = content.encode()
        (root / name).write_bytes(encoded)
        total += len(encoded)
        digest.update(name.encode() + b'\0' + encoded)
    write('tsconfig.json', json.dumps({'compilerOptions': {'strict': True, 'target': 'es2022', 'allowJs': True, 'checkJs': True}, 'include': ['*.ts', '*.js']}, sort_keys=True))
    for index in range(count):
        value = rng.randrange(1, 1000)
        write(f'unit{index:04}.ts', f'export function value{index}(input: number): number {{ return input + {value}; }}\nexport const result{index} = value{index}({index});\n')
        write(f'unit{index:04}.js', f'/** @param {{number}} input */\nexport function jsValue{index}(input) {{ return input + {value}; }}\nexport const jsResult{index} = jsValue{index}({index});\n')
        write(f'Unit{index:04}.cs', f'public class Unit{index} {{ public int Value(int input) => input + {value}; public int Read() => Value({index}); }}\n')
    return root, {'seed': SEED, 'files_per_language': count, 'source_files': 3 * count, 'bytes_including_config': total, 'content_sha256': digest.hexdigest()}


def benchmark_fixture(base, name, count):
    directory = base / name
    directory.mkdir()
    root, fixture = generate(directory, count)
    session = Session(root, directory)
    measurements = {}
    try:
        for language, engine, file, line, character, expected in [
            ('typescript', 'typescript', 'unit0000.ts', 0, 17, 2),
            ('javascript', 'typescript', 'unit0000.js', 1, 17, 2),
            ('csharp', 'csharp', 'Unit0000.cs', 0, 33, 1)
        ]:
            arguments = {'file': str(root / file)}
            result, elapsed = session.query(engine, 'diagnostics', **arguments)
            assert result == [], result
            measurements[language + '.first_diagnostics_including_lazy_load'] = summary([elapsed])
            for operation in ('diagnostics', 'symbols', 'references'):
                samples = []
                for _ in range(REPEATS):
                    result, elapsed = session.query(engine, operation, **arguments, **({'line': line, 'character': character} if operation == 'references' else {}))
                    if operation == 'diagnostics':
                        assert result == [], result
                    elif operation == 'references':
                        assert len(result) == expected, result
                    else:
                        expected_name = 'value0' if language == 'typescript' else 'jsValue0' if language == 'javascript' else 'Unit0'
                        assert any(item['name'] == expected_name for item in result), result
                    samples.append(elapsed)
                measurements[language + '.' + operation] = summary(samples)
    finally:
        session.close()
    return {'name': name, 'fixture': fixture, 'startup_discovery_ms': round(session.startup_ms, 3), 'measurements': measurements, 'rss': session.memory()}


def qualify_repository(base):
    directory = base / 'own-source'
    directory.mkdir()
    session = Session(REPO, directory)
    worker = REPO / 'workers/typescript/worker.mjs'
    test = REPO / 'workers/typescript/test/worker.test.mjs'
    content = test.read_text()
    position = content.index('new Worker(') + 4
    line = content[:position].count('\n')
    character = len(content[:position].rsplit('\n', 1)[-1])
    try:
        definitions, elapsed = session.query('typescript', 'definition', file=str(test), line=line, character=character)
        expected_line = worker.read_text().splitlines().index('export class Worker {')
        assert len(definitions) == 1 and Path(definitions[0]['file']) == worker, definitions
        assert definitions[0]['range']['start'] == {'line': expected_line, 'character': 13}, definitions
        symbols, symbol_ms = session.query('typescript', 'symbols', file=str(worker))
        assert any(item['name'] == 'Worker' and item['kind'] == 'class' for item in symbols), symbols
        return {'status': 'passed', 'scope': 'FreeFlight own worker source: inferred JS project; cross-file Worker constructor definition and class symbol only', 'definition_ms': round(elapsed, 3), 'symbols_ms': round(symbol_ms, 3), 'source_sha256': hashlib.sha256(worker.read_bytes()).hexdigest(), 'excludes': ['full project type checking', 'third-party real repository qualification', 'real large monorepo performance']}
    finally:
        session.close()


def main():
    output = REPO / 'bin/.local/benchmarks'
    output.mkdir(parents=True, exist_ok=True)
    base = Path(tempfile.mkdtemp(prefix='run-', dir=output)).resolve()
    report = {'schema': 1, 'status': 'running', 'platform': platform.platform(), 'machine': platform.machine(), 'seed': SEED, 'warm_repeats': REPEATS, 'generated_directory': str(base.relative_to(REPO)), 'limitations': ['Synthetic independent small files are not a real large repository or solution.', 'Single sequential client; round-trip includes protocol, IPC and engine work.', 'Discovery startup excludes lazy language initialization; first diagnostic includes it.', 'RSS sampling can miss short peaks and double-count shared pages.', 'Worker warm measurements include disk/config refresh; no isolated core overhead estimate.', 'No MSBuild project evaluation, package restore, filesystem watcher or concurrency load is measured.'], 'fixtures': []}
    binary = REPO / 'bin/.local/build/freeflight'
    if not binary.exists():
        binary = REPO / 'bin/.local/build/Release/freeflight.exe'
    report['toolchains'] = {
        'node': subprocess.check_output(['node', '--version'], text=True).strip(),
        'dotnet_sdk': subprocess.check_output(['dotnet', '--version'], cwd=REPO, text=True).strip(),
        'python': platform.python_version(),
        'mcp_protocol': META['io.modelcontextprotocol/protocolVersion'],
        'core_sha256': hashlib.sha256(binary.read_bytes()).hexdigest(),
        'typescript_worker_sha256': hashlib.sha256((REPO / 'bin/.local/typescript/worker.mjs').read_bytes()).hexdigest(),
        'roslyn_worker_sha256': hashlib.sha256((REPO / 'bin/.local/roslyn/bin/FreeFlight.Roslyn/debug/FreeFlight.Roslyn.dll').read_bytes()).hexdigest(),
    }
    receipt = REPO / 'bin/.local/reports/benchmark.json'
    receipt.parent.mkdir(parents=True, exist_ok=True)
    try:
        for name, count in [('medium', 100), ('large', 1000)]:
            result = benchmark_fixture(base, name, count)
            report['fixtures'].append(result)
            print(json.dumps(result), flush=True)
            receipt.write_text(json.dumps(report, indent=2) + '\n')
        report['own_source_qualification'] = qualify_repository(base)
        report['status'] = 'passed'
    except Exception as error:
        report['status'] = 'failed'
        report['error'] = str(error)
        raise
    finally:
        receipt.write_text(json.dumps(report, indent=2) + '\n')
    print(f'Benchmark complete: {receipt}', flush=True)


def comparison_fixture(directory, language, profile):
    """Fixed source with real declarations and explicit padding to exercise byte budgets."""
    directory.mkdir()
    suffix = {'csharp': 'cs', 'typescript': 'ts', 'javascript': 'js'}[language]
    source = ('public class Target { public static int Value() => Generated0.Field0 + 42; public int Read() => Value(); }\n'
              if language == 'csharp' else
              'import { field0_0 } from \"./Generated000\";\nexport function value() { return field0_0 + 42; }\nexport const result = value();\n')
    target = directory / ('Target.' + suffix)
    target.write_bytes(source.encode())
    if language != 'csharp':
        (directory / 'tsconfig.json').write_text(json.dumps({'compilerOptions': {
            'strict': True, 'target': 'es2022', 'allowJs': True, 'checkJs': True},
            'include': ['*.' + suffix]}))
    count, size = {'compatible': (24, 1024 * 1024), 'large-file': (1, 9 * 1024 * 1024),
                   'aggregate': (72, 1024 * 1024)}[profile]
    for index in range(count):
        declarations = ('public class Generated%d {\n' % index + ''.join(
            'public const int Field%d = %d;\n' % (n, n) for n in range(100)) + '}\n'
            if language == 'csharp' else ''.join(
                'export const field%d_%d = %d;\n' % (index, n, n) for n in range(100)))
        encoded = declarations.encode()
        encoded += b'/*' + b'x' * (size - len(encoded) - 4) + b'*/'
        (directory / ('Generated%03d.' % index + suffix)).write_bytes(encoded)
    files = sorted(directory.iterdir())
    digest = hashlib.sha256()
    for path in files:
        digest.update(path.name.encode() + b'\0' + path.read_bytes())
    return target, source, {'files': len(files), 'source_bytes': sum(p.stat().st_size for p in files if p.suffix == '.' + suffix),
                           'largest_file_bytes': max(p.stat().st_size for p in files),
                           'declarations_per_generated_file': 100, 'sha256': digest.hexdigest()}


def comparison_run(installation, root, target, source, language, directory):
    directory.mkdir()
    record = {'status': 'running', 'measurements': {}, 'phase': 'startup'}
    session = None
    engine = 'csharp' if language == 'csharp' else 'typescript'
    name = 'Value' if language == 'csharp' else 'value'
    declaration_offset = source.index(name)
    use_offset = source.rindex(name)
    def position(offset):
        return {'line': source[:offset].count('\n'), 'character': len(source[:offset].rsplit('\n', 1)[-1])}
    declaration, use = position(declaration_offset), position(use_offset)
    def verify(operation, result):
        if operation == 'diagnostics':
            assert result == [], result
        elif operation == 'symbols':
            assert sum(item['name'] == name for item in result) == 1, result
        elif operation == 'definition':
            assert len(result) == 1 and Path(result[0]['file']) == target, result
            assert result[0]['range']['start'] == declaration, result
        else:
            expected = [use] if language == 'csharp' else [declaration, use]
            assert len(result) == len(expected), result
            assert all(Path(item['file']) == target for item in result), result
            assert sorted((r['range']['start']['line'], r['range']['start']['character']) for r in result) == sorted((p['line'], p['character']) for p in expected), result
    try:
        session = Session(root, directory, installation)
        record['startup_discovery_ms'] = session.startup_ms
        record['phase'] = 'workspace.open'
        started = time.perf_counter()
        session.request('tools/call', {'name': 'workspace.open', 'arguments': {'root': str(root)}})
        record['workspace_open_ms'] = (time.perf_counter() - started) * 1000
        for operation in ('diagnostics', 'symbols', 'definition', 'references'):
            arguments = {'file': str(target)}
            if operation in ('definition', 'references'):
                arguments.update(use if operation == 'definition' else declaration)
            samples = []
            for index in range(REPEATS + 1):
                record['phase'] = operation + ('.first' if index == 0 else '.warm')
                result, elapsed = session.query(engine, operation, **arguments)
                verify(operation, result)
                if index == 0:
                    record['measurements'][operation + '.first'] = summary([elapsed])
                else:
                    samples.append(elapsed)
            record['measurements'][operation + '.warm'] = summary(samples)
        record['phase'] = 'changed-file.refresh'
        changed = source.replace('42', 'missingBenchmarkName')
        target.write_bytes(changed.encode())
        result, elapsed = session.query(engine, 'diagnostics', file=str(target))
        expected_code = 'CS0103' if language == 'csharp' else 2304
        assert len(result) == 1 and result[0]['code'] == expected_code and 'missingBenchmarkName' in result[0]['message'], result
        record['measurements']['changed-file.diagnostics'] = summary([elapsed])
        target.write_bytes(source.encode())
        result, elapsed = session.query(engine, 'diagnostics', file=str(target))
        assert result == [], result
        record['measurements']['restored-file.diagnostics'] = summary([elapsed])
        record['phase'] = 'steady-memory'
        first = len(session.rss_samples)
        time.sleep(0.6)
        samples = session.rss_samples[first:]
        record['steady_rss'] = {'samples': samples, 'median_tree_kib': statistics.median(s['tree_kib'] for s in samples)} if samples else {'status': 'unavailable'}
        record['status'] = 'passed'
    except Exception as error:
        record['status'] = 'failed'
        record['error_type'] = type(error).__name__
        record['error'] = str(error)
        # Preserve the actual protocol response when an MCP assertion rejected it.
        if error.args and isinstance(error.args[0], (dict, list)):
            record['response'] = error.args[0]
    finally:
        target.write_bytes(source.encode())
        if session:
            record['rss'] = session.memory()
            record['rss']['raw_samples'] = list(session.rss_samples)
            try:
                session.close()
            except Exception as error:
                record['shutdown_error'] = str(error)
                record['status'] = 'failed'
    return record


def compare(baseline):
    output = REPO / 'bin/.local/benchmarks'
    output.mkdir(parents=True, exist_ok=True)
    base = Path(tempfile.mkdtemp(prefix='comparison-', dir=output)).resolve()
    receipt = base / 'comparison.json'
    installations = {'baseline': baseline, 'candidate': REPO}
    report = {'schema': 1, 'status': 'running', 'platform': platform.platform(), 'machine': platform.machine(),
              'cpu_count': os.cpu_count(), 'warm_repeats': REPEATS, 'runs': [], 'installations': {},
              'toolchains': {'node': subprocess.check_output(['node', '--version'], text=True).strip(),
                             'dotnet': subprocess.check_output(['dotnet', '--version'], text=True).strip(), 'python': platform.python_version()},
              'configuration': 'Identical roots and explicit worker commands; default resource policy of each version; no MSBuild evaluation.',
              'limitations': ['Synthetic declarations plus comment padding; not a real solution or monorepo.',
                              'Cold means fresh processes, not cold operating-system disk caches.',
                              'Workspace.open registers the root; first diagnostics includes lazy worker initialization and source loading.',
                              'First symbol/definition/reference measurements follow first diagnostics and are not cold compiler measurements.',
                              'Two compatible runs alternate version order; larger cases have one run each.',
                              'RSS is sampled ps process-tree RSS, can miss peaks and double-count shared pages; steady RSS is a 600ms post-query window.',
                              'No competitor comparison; no concurrency, trusted MSBuild or project-reference workload.']}
    for label, installation in installations.items():
        files = ['bin/.local/build/freeflight', 'bin/.local/typescript/worker.mjs',
                 'bin/.local/roslyn/bin/FreeFlight.Roslyn/debug/FreeFlight.Roslyn.dll']
        report['installations'][label] = {'directory': str(installation), 'sha256': {
            name: hashlib.sha256((installation / name).read_bytes()).hexdigest() for name in files}}
        provenance = (REPO / 'bin/.local/baseline-provenance.json') if label == 'baseline' else installation / 'benchmark-source.json'
        if provenance.exists():
            report['installations'][label]['source_receipt'] = json.loads(provenance.read_text())
        else:
            report['installations'][label]['git_head'] = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=installation, text=True).strip()
    if platform.system() == 'Darwin':
        report['hardware'] = subprocess.check_output(['/usr/sbin/sysctl', '-n', 'machdep.cpu.brand_string', 'hw.memsize'], text=True).splitlines()
    for profile in ('compatible', 'large-file', 'aggregate'):
        for language in ('csharp', 'typescript', 'javascript'):
            target, source, fixture = comparison_fixture(base / (profile + '-' + language), language, profile)
            for iteration in range(2 if profile == 'compatible' else 1):
                order = ('baseline', 'candidate') if iteration == 0 else ('candidate', 'baseline')
                for label in order:
                    result = comparison_run(installations[label], target.parent, target, source, language,
                                            base / (profile + '-' + language + '-' + str(iteration) + '-' + label))
                    result.update({'profile': profile, 'language': language, 'iteration': iteration, 'version': label, 'fixture': fixture})
                    report['runs'].append(result)
                    receipt.write_text(json.dumps(report, indent=2) + '\n')
                    print(json.dumps(result), flush=True)
    report['status'] = 'completed' if all(r['status'] == 'passed' for r in report['runs'] if r['version'] == 'candidate' or r['profile'] == 'compatible') else 'failed'
    receipt.write_text(json.dumps(report, indent=2) + '\n')
    print(f'Comparison complete: {receipt}', flush=True)
    if report['status'] != 'completed':
        raise RuntimeError('Candidate or compatible baseline failed correctness checks; inspect retained observations')


if __name__ == '__main__':
    if os.environ.get('FREEFLIGHT_BENCHMARK_BASELINE'):
        compare(Path(os.environ['FREEFLIGHT_BENCHMARK_BASELINE']).resolve())
    else:
        main()
