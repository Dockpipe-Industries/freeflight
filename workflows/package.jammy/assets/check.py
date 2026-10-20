# SPDX-License-Identifier: Apache-2.0
"""Inspect ELF version requirements without executing packaged code."""
import importlib.util
import json
import os
from pathlib import Path
import platform
import re
import shutil
import subprocess
import tarfile
import tempfile
import uuid

ROOT = Path(__file__).resolve().parents[3]
LIMITS = {'GLIBC': (2, 35), 'GLIBCXX': (3, 4, 30), 'CXXABI': (1, 3, 13)}
IMAGE = 'ubuntu:22.04@sha256:98510ac07bb4545e389be502a8918b385c018bfe4ceeb5ac7e0375c782268b04'
PACKAGES = ['ca-certificates', 'libc6', 'libgcc-s1', 'libgssapi-krb5-2', 'libicu70',
            'libssl3', 'libstdc++6', 'tzdata', 'zlib1g']
FEDORA_IMAGE = 'registry.fedoraproject.org/fedora:44@sha256:0db60e5a404cb9913c396b0651ed269656554da1cd0a13a92d41409b12d7ecb0'
FEDORA_PACKAGES = ['ca-certificates', 'glibc', 'libgcc', 'krb5-libs', 'libicu',
                   'openssl-libs', 'libstdc++', 'tzdata', 'zlib-ng-compat']


def clean_runtime(archive, profile='ubuntu22'):
    """Test extracted payload with bundled Node, no host runtimes or network."""
    if profile == 'ubuntu22':
        image, packages = IMAGE, PACKAGES
        install = ('apt-get update && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends '
                   + ' '.join(packages) + ' && rm -rf /var/lib/apt/lists/*')
        query = ['/usr/bin/dpkg-query', '-W', '-f=${Package}=${Version}\\n', *packages]
    elif profile == 'fedora44':
        image, packages = FEDORA_IMAGE, FEDORA_PACKAGES
        install = 'dnf -y --setopt=install_weak_deps=False install ' + ' '.join(packages) + ' && dnf clean all'
        query = ['/usr/bin/rpm', '-q', '--queryformat', '%{NAME}=%{VERSION}-%{RELEASE}.%{ARCH}\\n', *packages]
    else:
        raise ValueError('Unknown clean runtime profile')
    tag = 'freeflight-jammy-test:' + uuid.uuid4().hex
    container = 'freeflight-jammy-' + uuid.uuid4().hex
    with tempfile.TemporaryDirectory(prefix='jammy-runtime-', dir=ROOT / 'bin/.local') as temporary:
        context = Path(temporary)
        with tarfile.open(archive) as bundle:
            # Copy validated regular files only; never apply archived ownership,
            # links, special files or directory permissions to the build context.
            for member in bundle.getmembers():
                if member.isdir():
                    continue
                destination = context / member.name
                if not member.isfile() or not destination.resolve().is_relative_to(context.resolve()):
                    raise ValueError('Unsafe runtime archive member')
                destination.parent.mkdir(parents=True, exist_ok=True)
                with bundle.extractfile(member) as source, destination.open('wb') as target:
                    shutil.copyfileobj(source, target)
                destination.chmod(member.mode & 0o777)
        shutil.copytree(ROOT / 'bin/.local/client', context / 'client')
        (context / 'Dockerfile').write_text(
            'FROM ' + image + '\n'
            'RUN ' + install + '\n'
            'COPY freeflight-linux-x64 /opt/freeflight\n'
            'COPY client /opt/client\n')
        try:
            subprocess.run(['docker', 'build', '--platform', 'linux/amd64', '--tag', tag, str(context)],
                           check=True, timeout=600)
            common = ['docker', 'run', '--rm', '--name', container, '--network', 'none', '--read-only',
                      '--tmpfs', '/tmp:rw,nosuid,size=512m', '--cap-drop', 'ALL',
                      '--security-opt', 'no-new-privileges', '--user', '65532:65532']
            result = subprocess.run(common + ['--env', 'FREEFLIGHT_BINARY=/opt/freeflight/bin/freeflight',
                '--entrypoint', '/opt/freeflight/lib/freeflight/node/bin/node', tag, '/opt/client/client.mjs'],
                check=False, text=True, capture_output=True, timeout=120)
            if result.returncode:
                print(result.stdout)
                print(result.stderr)
                result.check_returncode()
            required = 'Official MCP SDK verified packaged TS definition/references/diagnostics, JS symbol, C# diagnostics/symbol and engine capabilities'
            if required not in result.stdout:
                raise ValueError('Missing clean-container official SDK semantic result')
            versions = subprocess.check_output(common + ['--entrypoint', query[0], tag, *query[1:]], text=True, timeout=30)
            return {'baseImage': image, 'packages': versions.splitlines(), 'network': 'none',
                    'user': '65532:65532', 'hostRuntimeMounted': False, 'stdout': result.stdout}
        finally:
            subprocess.run(['docker', 'rm', '--force', container], check=False,
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=30)
            subprocess.run(['docker', 'image', 'rm', '--force', tag], check=False,
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=30)


def version_needs(output):
    # readelf also prints version definitions. Only consumers' needs constrain
    # deployment; definitions must never be mistaken for required symbols.
    needs = output.split('Version needs section', 1)
    if len(needs) == 1:
        raise ValueError('ELF has no readable version needs section')
    names = re.findall(r'\bName: (\S+)', needs[1].split('\nVersion ', 1)[0])
    result = {}
    for name in names:
        for family, maximum in LIMITS.items():
            if not name.startswith(family + '_'):
                continue
            version = name[len(family) + 1:]
            if not re.fullmatch(r'\d+(?:\.\d+)+', version):
                raise ValueError('Unsupported ABI requirement: ' + name)
            parsed = tuple(map(int, version.split('.')))
            if parsed > maximum:
                raise ValueError('Exceeds Ubuntu 22.04 ABI baseline: ' + name)
            result[family] = max(result.get(family, ()), parsed)
    if 'GLIBC' not in result:
        raise ValueError('No GLIBC consumer requirements found')
    return {family: '.'.join(map(str, value)) for family, value in result.items()}


def main():
    if platform.system() != 'Linux' or platform.machine() != 'x86_64':
        raise ValueError('Jammy qualification requires a Linux x64 host')
    release = dict(line.split('=', 1) for line in Path('/etc/os-release').read_text().splitlines() if '=' in line)
    if release.get('ID', '').strip('"') != 'ubuntu' or release.get('VERSION_ID', '').strip('"') != '22.04':
        raise ValueError('Qualification host must be Ubuntu 22.04')
    spec = importlib.util.spec_from_file_location('prepare', ROOT / 'workflows/release.prepare/assets/prepare.py')
    prepare = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(prepare)
    packages = ROOT / 'bin/.local/packages'
    archives = list(packages.glob('freeflight-linux-x64-*.tar.gz'))
    if len(archives) != 1:
        raise ValueError('Expected one freshly qualified Linux x64 tar archive')
    archive = archives[0]
    report = prepare.inspect_archive(archive, (ROOT / 'VERSION').read_text().strip())
    if 'official MCP SDK bundled semantic qualification' not in report['verification']['checks']:
        raise ValueError('Missing installed official MCP SDK semantic qualification')
    results = {}
    with tempfile.TemporaryDirectory(prefix='jammy-abi-', dir=ROOT / 'bin/.local') as temporary, tarfile.open(archive) as bundle:
        target = Path(temporary) / 'inspect.elf'
        for item in bundle.getmembers():
            if not item.isfile():
                continue
            with bundle.extractfile(item) as stream:
                data = stream.read()
            if data[:4] != b'\x7fELF':
                continue
            target.write_bytes(data)
            output = subprocess.check_output(['readelf', '--version-info', '--wide', str(target)], text=True,
                                             env=dict(os.environ, LC_ALL='C'))
            results[item.name] = version_needs(output)
    required = ['bin/freeflight', 'lib/freeflight/node/bin/node', 'lib/freeflight/roslyn/FreeFlight.Roslyn',
                'lib/freeflight/roslyn/libcoreclr.so']
    if not all('freeflight-linux-x64/' + name in results for name in required):
        raise ValueError('Required native runtime ELF missing')
    runtime = clean_runtime(archive)
    fedora = clean_runtime(archive, 'fedora44')
    receipt = {'status': 'qualified-on-ubuntu-22.04', 'artifact': archive.name, 'sha256': report['sha256'],
               'sourceCommit': report['verification']['sourceCommit'], 'sourceTree': report['verification']['sourceTree'],
               'limits': {key: '.'.join(map(str, value)) for key, value in LIMITS.items()}, 'elfVersionNeeds': results,
               'cleanRuntime': runtime, 'popOsRuntimeTested': False, 'productionPublication': False,
               'fedoraRuntime': {**fedora, 'status': 'qualified-on-fedora-44',
                                 'artifact': archive.name, 'sha256': report['sha256'],
                                 'sourceCommit': report['verification']['sourceCommit'],
                                 'sourceTree': report['verification']['sourceTree'],
                                 'bazziteRuntimeTested': False}}
    output = ROOT / 'bin/.local/jammy-compatibility.json'
    output.write_text(json.dumps(receipt, indent=2) + '\n')
    print('Verified Ubuntu 22.04 ABI requirements for ' + str(len(results)) + ' bundled ELF files')


if __name__ == '__main__':
    main()
