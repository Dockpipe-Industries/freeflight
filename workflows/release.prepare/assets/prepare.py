# SPDX-License-Identifier: Apache-2.0
"""DockPipe-owned release qualification, never publication."""
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import tarfile
import tempfile
from urllib.request import urlopen
import zipfile

RIDS = {'osx-arm64', 'osx-x64', 'linux-x64', 'linux-arm64', 'win-x64', 'win-arm64'}
NAME = re.compile(r'freeflight-(osx-arm64|osx-x64|linux-x64|linux-arm64|win-x64|win-arm64)-([a-f0-9]{16})\.(tar\.gz|mcpb)')
CHECKS = {'legacy MCP initialization', 'TypeScript TS2322', 'JavaScript increment symbol', 'Roslyn CS0029', 'Roslyn Widget symbol', 'graceful shutdown', 'native Roslyn safe-source semantic suite', 'native Roslyn trusted-project suite (external SDK)'}
REPO_URL = 'https://github.com/Dockpipe-Industries/freeflight'


def require(condition, message):
    if not condition:
        raise ValueError(message)


def digest(stream):
    result = hashlib.sha256()
    for block in iter(lambda: stream.read(1024 * 1024), b''):
        result.update(block)
    return result.hexdigest()


def file_digest(file):
    with file.open('rb') as stream:
        return digest(stream)


def safe_name(name):
    p = PurePosixPath(name)
    require(name and not p.is_absolute() and '..' not in p.parts and '\\' not in name and ':' not in name, 'Unsafe archive path')
    require(str(p) == name, 'Noncanonical archive path')
    return name


def inspect_archive(path, version):
    match = NAME.fullmatch(path.name)
    require(match is not None and path.is_file() and not path.is_symlink(), 'Invalid artifact filename or file')
    rid, prefix, kind = match.groups()
    require(path.stat().st_size <= 2 * 1024 ** 3, 'Archive exceeds 2 GiB compressed limit')
    actual_hash = file_digest(path)
    sidecar = path.with_name(path.name + '.sha256')
    require(sidecar.is_file() and not sidecar.is_symlink(), 'Missing checksum receipt')
    require(sidecar.read_text().strip() == actual_hash + '  ' + path.name, 'Artifact checksum receipt mismatch')
    archive = zipfile.ZipFile(path) if kind == 'mcpb' else tarfile.open(path)
    try:
        entries = {}
        for item in archive.infolist() if kind == 'mcpb' else archive.getmembers():
            if kind == 'mcpb':
                if item.is_dir():
                    continue
                require((item.external_attr >> 16) & 0o170000 != 0o120000, 'Symlink in MCPB')
                name, size = item.filename, item.file_size
            else:
                if item.isdir():
                    continue
                require(item.isfile(), 'Nonregular tar member')
                require(item.name.startswith('freeflight-' + rid + '/'), 'Wrong tar root')
                name, size = item.name[len('freeflight-' + rid + '/'):], item.size
            name = safe_name(name)
            require(name not in entries and size <= 512 * 1024 * 1024, 'Duplicate or oversized archive member')
            require(len(entries) < 20000, 'Too many archive entries')
            entries[name] = item
        require(len(entries) <= 20000, 'Too many archive entries')
        require(sum(i.file_size if kind == 'mcpb' else i.size for i in entries.values()) <= 2 * 1024 ** 3, 'Archive exceeds 2 GiB expanded limit')
        def read(name):
            require(name in entries, 'Missing archive file: ' + name)
            stream = archive.open(entries[name]) if kind == 'mcpb' else archive.extractfile(entries[name])
            return stream
        def text(name):
            with read(name) as stream:
                data = stream.read(4 * 1024 * 1024 + 1)
            require(len(data) <= 4 * 1024 * 1024, 'Oversized metadata')
            return data.decode('utf-8')
        sums_text = text('SHA256SUMS')
        sums = {}
        for line in sums_text.splitlines():
            parts = line.split('  ', 1)
            require(len(parts) == 2 and re.fullmatch('[a-f0-9]{64}', parts[0]), 'Malformed internal checksums')
            name = safe_name(parts[1])
            require(name not in sums, 'Duplicate internal checksum')
            sums[name] = parts[0]
        require(set(sums) == set(entries) - {'SHA256SUMS'}, 'Internal checksum coverage mismatch')
        for name, expected in sums.items():
            with read(name) as stream:
                require(digest(stream) == expected, 'Tampered archive file: ' + name)
        require(prefix == (actual_hash if kind == 'mcpb' else hashlib.sha256(sums_text.encode()).hexdigest())[:16], 'Filename digest mismatch')
        receipt = json.loads(text('verification.json'))
        manifest = json.loads(text('manifest.json'))
        require(receipt.get('rid') == rid and receipt.get('productionPublication') is False, 'Incompatible verification receipt')
        require(CHECKS <= set(receipt.get('checks', [])), 'Missing required native qualification checks')
        require(receipt.get('sourceDirty') is False, 'Missing clean-source provenance or source tree was dirty')
        for key in ('sourceCommit', 'sourceTree'):
            require(isinstance(receipt.get(key), str) and re.fullmatch('[a-f0-9]{40}', receipt[key]), 'Missing Git provenance: ' + key)
        require(manifest.get('version') == version and manifest.get('manifest_version') == '0.3' and manifest.get('name') == 'freeflight', 'Incompatible MCPB version or identity')
        windows = rid.startswith('win-')
        node = 'lib/freeflight/node/node.exe' if windows else 'lib/freeflight/node/bin/node'
        binary = 'bin/freeflight.exe' if windows else 'bin/freeflight'
        require(node in sums and binary in sums and receipt.get('nodeExecutableSha256') == sums[node], 'Runtime receipt mismatch')
        require(manifest.get('server', {}).get('entry_point') == binary and manifest['server'].get('type') == 'binary', 'Incompatible executable entry point')
        require(manifest['server'].get('mcp_config') == {'command': '${__dirname}/' + binary, 'args': ['--workspace', '${user_config.workspace}']}, 'Incompatible MCP launch contract')
        system = 'darwin' if rid.startswith('osx-') else 'win32' if windows else 'linux'
        require(manifest.get('compatibility', {}).get('platforms') == [system], 'Incompatible platform declaration')
        return {'filename': path.name, 'source': str(path), 'rid': rid, 'format': kind, 'sha256': actual_hash, 'bytes': path.stat().st_size, 'files': sums, 'verification': receipt}
    finally:
        archive.close()


def verify_url(url, expected):
    with urlopen(url, timeout=60) as response:
        require(response.status == 200 and response.geturl().startswith('https://'), 'Asset URL unavailable or insecure')
        require(digest(response) == expected, 'Remote artifact checksum mismatch')


def prepare(config, output_root, verifier=verify_url):
    version = config.get('version', '')
    require(isinstance(version, str) and re.fullmatch(r'\d+\.\d+\.\d+(?:-[A-Za-z0-9.-]+)?', version), 'Explicit semantic version required')
    tag = config.get('tag')
    require(tag == 'v' + version, 'Tag must match v plus artifact version')
    mode = config.get('mode', 'draft')
    require(mode in {'draft', 'verify-urls'}, 'Unknown preparation mode')
    rids = config.get('expectedRids')
    require(isinstance(rids, list) and rids and len(set(rids)) == len(rids) and set(rids) <= RIDS, 'Explicit unique expected RIDs required')
    selected = config.get('registryRid')
    require(selected in rids, 'Select one registryRid; MCPB does not encode CPU architecture')
    paths = config.get('artifacts')
    require(isinstance(paths, list) and len(paths) == 2 * len(rids), 'Exactly one tar and one MCPB per RID required')
    artifacts = [inspect_archive(Path(p).absolute(), version) for p in paths]
    pairs = {(a['rid'], a['format']): a for a in artifacts}
    require(set(pairs) == {(rid, kind) for rid in rids for kind in ('tar.gz', 'mcpb')}, 'Missing, duplicate or unexpected platform artifact')
    require(len({(a['verification']['sourceCommit'], a['verification']['sourceTree']) for a in artifacts}) == 1, 'Artifacts have incompatible source provenance')
    for rid in rids:
        require(pairs[rid, 'tar.gz']['files'] == pairs[rid, 'mcpb']['files'], 'Native and MCPB contents differ for ' + rid)
    for artifact in artifacts:
        artifact['candidateUrl'] = REPO_URL + '/releases/download/' + tag + '/' + artifact['filename']
        if mode == 'verify-urls':
            verifier(artifact['candidateUrl'], artifact['sha256'])
    registry = {'$schema': 'https://static.modelcontextprotocol.io/schemas/2025-12-11/server.schema.json', 'name': 'io.github.Dockpipe-Industries/freeflight', 'title': 'FreeFlight', 'description': 'Independent C++ language intelligence for C#, TypeScript and JavaScript.', 'version': version, 'repository': {'url': REPO_URL, 'source': 'github'}, '_meta': {'io.modelcontextprotocol.registry/publisher-provided': {'publicationStatus': 'draft-not-published', 'selectedRid': selected, 'architectureSelection': 'Operator selected; MCPB 0.3 has no CPU architecture field', 'assetUrlsVerified': mode == 'verify-urls'}}}
    chosen = pairs[selected, 'mcpb']
    if mode == 'verify-urls':
        registry['packages'] = [{'registryType': 'mcpb', 'identifier': chosen['candidateUrl'], 'fileSha256': chosen['sha256'], 'transport': {'type': 'stdio'}}]
    report = {'status': 'prepared-not-published', 'mode': mode, 'version': version, 'tag': tag, 'expectedRids': rids, 'registryRid': selected, 'artifacts': [{k:v for k,v in a.items() if k != 'files'} for a in artifacts], 'limitations': ['Checksums and embedded receipts are not signed CI provenance.', 'No publication, tag creation, signatures or Registry submission occurred.', 'MCPB platform metadata does not select CPU architecture.']}
    output_root.mkdir(parents=True, exist_ok=True)
    output = Path(tempfile.mkdtemp(prefix=tag + '-', dir=output_root))
    (output / 'SHA256SUMS').write_text(''.join(a['sha256'] + '  ' + a['filename'] + '\n' for a in sorted(artifacts, key=lambda a:a['filename'])))
    (output / 'release-manifest.json').write_text(json.dumps(report, indent=2) + '\n')
    filename = 'server.draft.json' if mode == 'verify-urls' else 'server.template-not-publishable.json'
    (output / filename).write_text(json.dumps(registry, indent=2) + '\n')
    return output


if __name__ == '__main__':
    root = Path(__file__).resolve().parents[3]
    config = os.environ.get('FREEFLIGHT_RELEASE_INPUT')
    require(config, 'Set FREEFLIGHT_RELEASE_INPUT to reviewed release-input JSON')
    print(prepare(json.loads(Path(config).read_text()), root / 'bin/.local/release-prepared'))
