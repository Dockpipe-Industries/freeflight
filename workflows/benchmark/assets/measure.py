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
    def __init__(self, root, directory):
        binary = REPO / 'bin/.local/build/freeflight'
        if not binary.exists():
            binary = REPO / 'bin/.local/build/Release/freeflight.exe'
        self.binary = binary
        node, dotnet = shutil.which('node'), shutil.which('dotnet')
        assert node and dotnet and binary.is_file(), 'Run DockPipe build before benchmarking'
        config = directory / 'freeflight.json'
        config.write_text(json.dumps({'roots': [str(root)], 'engines': {
            'typescript': [node, str(REPO / 'bin/.local/typescript/worker.mjs')],
            'csharp': [dotnet, str(REPO / 'bin/.local/roslyn/bin/FreeFlight.Roslyn/debug/FreeFlight.Roslyn.dll')]
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


if __name__ == '__main__':
    main()
