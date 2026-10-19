# SPDX-License-Identifier: Apache-2.0
"""Explicit Registry submission through the pinned official publisher; never login."""
import hashlib
import io
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tarfile
import tempfile
from urllib.parse import urlparse
from urllib.request import HTTPRedirectHandler, build_opener
import zipfile

REPO = 'https://github.com/Dockpipe-Industries/freeflight'
API = 'https://api.github.com/repos/Dockpipe-Industries/freeflight'
REGISTRY = 'https://registry.modelcontextprotocol.io'
SCHEMA_HASH = '3fba09590c99f61735d234822279f4223fab9e300c0a81e81c91ab62a4114de0'
PINS = {
    '88126981225e7714fcc6b7a10cdba4a80ae5901e9740a8c06d0d5195c8bc294c',
    'e45e520892460732a4bdf37255576415d4a53ec171f8b913faf15bb1aef7cb77',
    'a06c9096dcb9727c13555b6be26c7effa707b01f06a4c561ba7a3635443cf2cc',
    '8dd75a6cf6845688b5d4e46df58d3ca26d5c8d233bb0626606e1db82c5e883e4',
    '399ad0d6e00a50812b563a71d8bfbff5160c085e6b13aac6ec083d98d5ff7c45',
    '2e3a3435e27afcaa35bec9cb573bab99db9e980d7fb49f90f32a59d03d4a3fa3',
}


def require(condition, message):
    if not condition:
        raise ValueError(message)


class SecureRedirect(HTTPRedirectHandler):
    def redirect_request(self, request, fp, code, message, headers, url):
        parsed = urlparse(url)
        require(parsed.scheme == 'https' and parsed.hostname in {
            'github.com', 'api.github.com', 'release-assets.githubusercontent.com',
            'objects.githubusercontent.com'}, 'Unapproved asset redirect')
        return super().redirect_request(request, fp, code, message, headers, url)


def fetch(url, limit=2 * 1024 ** 3, expected=None):
    with build_opener(SecureRedirect()).open(url, timeout=60) as response:
        require(response.status == 200, 'Remote asset unavailable')
        digest = hashlib.sha256()
        data = bytearray()
        total = 0
        while block := response.read(1024 * 1024):
            total += len(block)
            require(total <= limit, 'Remote response exceeds size limit')
            digest.update(block)
            if expected is None:
                data.extend(block)
        if expected is not None:
            require(digest.hexdigest() == expected, 'Remote artifact hash mismatch')
        return bytes(data)


def check_metadata(server, report, version):
    require(report.get('status') == 'prepared-not-published' and report.get('mode') == 'verify-urls',
            'Only URL-verified release.prepare output is eligible')
    require(re.fullmatch(r'\d+\.\d+\.\d+(?:-[A-Za-z0-9.-]+)?', version), 'Invalid version')
    require(server.get('version') == report.get('version') == version and report.get('tag') == 'v' + version,
            'Version or release tag mismatch')
    require(server.get('name') == 'io.github.Dockpipe-Industries/freeflight', 'Wrong Registry namespace')
    require(server.get('repository') == {'url': REPO, 'source': 'github'}, 'Wrong source repository')
    require(not server.get('remotes'), 'Unexpected remote endpoint')
    packages = server.get('packages', [])
    require(len(packages) == 1, 'Exactly one selected MCPB required')
    artifacts = report.get('artifacts', [])
    selected = [a for a in artifacts if a.get('rid') == report.get('registryRid') and a.get('format') == 'mcpb']
    require(len(selected) == 1, 'Missing or duplicate selected MCPB')
    artifact = selected[0]
    require(re.fullmatch(r'freeflight-(osx-arm64|osx-x64|linux-x64|linux-arm64|win-x64|win-arm64)-[a-f0-9]{16}\.mcpb', artifact.get('filename', '')), 'Invalid asset filename')
    require(re.fullmatch('[a-f0-9]{64}', artifact.get('sha256', '')), 'Invalid SHA256')
    url = REPO + '/releases/download/v' + version + '/' + artifact['filename']
    require(artifact.get('candidateUrl') == url, 'Release asset URL mismatch')
    require(packages[0] == {'registryType': 'mcpb', 'identifier': url,
                           'fileSha256': artifact['sha256'], 'transport': {'type': 'stdio'}},
            'Unexpected package contract')
    receipt = artifact.get('verification', {})
    require(receipt.get('sourceDirty') is False and re.fullmatch('[a-f0-9]{40}', receipt.get('sourceCommit', '')),
            'Missing clean source commit')
    meta = server.get('_meta', {}).get('io.modelcontextprotocol.registry/publisher-provided', {})
    require(meta.get('assetUrlsVerified') is True and meta.get('selectedRid') == artifact['rid'], 'Missing preparation receipt')
    return artifact


def verify_publisher(binary, archive):
    payload = archive.read_bytes()
    require(hashlib.sha256(payload).hexdigest() in PINS, 'Publisher archive is not pinned v1.8.1')
    name = 'mcp-publisher.exe' if os.name == 'nt' else 'mcp-publisher'
    if zipfile.is_zipfile(io.BytesIO(payload)):
        with zipfile.ZipFile(io.BytesIO(payload)) as bundle:
            expected = bundle.read(name)
    else:
        with tarfile.open(fileobj=io.BytesIO(payload)) as bundle:
            member = bundle.getmember(name)
            require(member.isfile() and member.size < 100 * 1024 ** 2, 'Invalid publisher member')
            expected = bundle.extractfile(member).read()
    require(binary.is_absolute() and binary.is_file() and binary.read_bytes() == expected,
            'Publisher executable differs from verified archive')


def verify_tag(version, commit):
    ref = json.loads(fetch(API + '/git/ref/tags/v' + version, limit=1024 ** 2))['object']
    for _ in range(5):
        require(re.fullmatch('[a-f0-9]{40}', ref['sha']), 'Invalid GitHub object')
        if ref['type'] == 'commit':
            if ref['sha'] != commit:
                comparison = json.loads(fetch(API + '/compare/' + commit + '...' + ref['sha'], limit=4 * 1024 ** 2))
                require(comparison.get('status') == 'ahead' and comparison.get('merge_base_commit', {}).get('sha') == commit,
                        'Qualified source is not ancestor of release tag')
                source = json.loads(fetch(API + '/git/commits/' + commit, limit=1024 ** 2))
                target = json.loads(fetch(API + '/git/commits/' + ref['sha'], limit=1024 ** 2))
                require(source.get('tree', {}).get('sha') and source['tree']['sha'] == target.get('tree', {}).get('sha'),
                        'Promoted release tag tree differs from qualified source')
            return
        require(ref['type'] == 'tag', 'Release tag does not resolve to commit')
        ref = json.loads(fetch(API + '/git/tags/' + ref['sha'], limit=1024 ** 2))['object']
    raise ValueError('Excessive annotated tag nesting')


def main():
    import jsonschema

    root = Path(__file__).resolve().parents[3]
    mode = os.environ.get('FREEFLIGHT_REGISTRY_MODE', 'verify')
    require(mode in {'verify', 'publish'}, 'Mode must be verify or publish')
    for variable in ('FREEFLIGHT_REGISTRY_INPUT', 'FREEFLIGHT_PUBLISHER', 'FREEFLIGHT_PUBLISHER_ARCHIVE'):
        require(bool(os.environ.get(variable)), 'Set ' + variable + '; see docs/registry-publication.md')
    prepared = Path(os.environ['FREEFLIGHT_REGISTRY_INPUT']).resolve(strict=True)
    server = json.loads((prepared / 'server.draft.json').read_text())
    report = json.loads((prepared / 'release-manifest.json').read_text())
    artifact = check_metadata(server, report, (root / 'VERSION').read_text().strip())
    schema = (root / 'bin/.local/registry/server.schema.json').read_bytes()
    require(hashlib.sha256(schema).hexdigest() == SCHEMA_HASH, 'Schema pin mismatch')
    jsonschema.validate(server, json.loads(schema))
    binary = Path(os.environ['FREEFLIGHT_PUBLISHER'])
    verify_publisher(binary, Path(os.environ['FREEFLIGHT_PUBLISHER_ARCHIVE']))
    verify_tag(server['version'], artifact['verification']['sourceCommit'])
    fetch(artifact['candidateUrl'], expected=artifact['sha256'])
    if mode == 'verify':
        print('Registry preflight passed; no authentication read and no publication attempted')
        return
    # Upstream v1.8.1 uses exactly this existing auth file; never write or create it.
    auth = json.loads((Path.home() / '.config/mcp-publisher/token.json').read_text())
    require(auth.get('registry', REGISTRY) in {'', REGISTRY} and bool(auth.get('token')),
            'Existing official Registry authentication required')
    output = root / 'bin/.local/registry'
    with tempfile.TemporaryDirectory(prefix='submission-', dir=output) as temporary:
        snapshot = Path(temporary) / 'server.json'
        snapshot.write_text(json.dumps(server, indent=2) + '\n')
        subprocess.run([str(binary), 'publish', str(snapshot)], check=True, cwd=temporary)
    print('Official publisher returned success; confirm the published Registry entry independently')


if __name__ == '__main__':
    try:
        main()
    except (ValueError, KeyError, OSError) as error:
        print('Registry preflight stopped: ' + str(error), file=sys.stderr)
        sys.exit(1)
