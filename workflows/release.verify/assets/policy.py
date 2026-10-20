# SPDX-License-Identifier: Apache-2.0
"""Release policy and composition of existing release.prepare validation."""
import importlib.util
import json
import os
from pathlib import Path
import re
import subprocess
import hashlib
import zipfile
import ast
import tarfile

REPO = 'Dockpipe-Industries/freeflight'
PLATFORMS = {'native-ubuntu-24.04': 'linux-x64', 'native-ubuntu-24.04-arm': 'linux-arm64',
             'native-windows-2022': 'win-x64', 'native-macos-15': 'osx-arm64'}
EXTRAS = {'qt-wasm-site-staging', 'qt-wasm-site-production', 'qt-site-container-staging',
          'qt-site-container-production', 'qt-corresponding-sources', 'qt-site-audit-staging', 'qt-site-audit-production'}


def require(value, message):
    if not value:
        raise ValueError(message)


def check_run(run, path, source=None):
    require(run.get('repository', {}).get('full_name') == REPO and
            run.get('head_repository', {}).get('full_name') == REPO, 'Foreign run repository')
    require(run.get('path') == path and run.get('event') == 'push' and
            run.get('head_branch') == 'js/dev', 'Expected exact js/dev push workflow')
    require(run.get('status') == 'completed' and run.get('conclusion') == 'success', 'Run not successfully completed')
    require(re.fullmatch('[a-f0-9]{40}', run.get('head_sha', '')), 'Invalid source SHA')
    require(source is None or source == run['head_sha'], 'Qualification source mismatch')
    return run['head_sha']


def platforms(channel):
    require(channel in ('production', 'staging'), 'Unknown release channel')
    if channel == 'production':
        return PLATFORMS
    return {name: rid for name, rid in PLATFORMS.items() if rid != 'linux-x64'} | {
        'preview-ubuntu-22.04-linux-x64': 'linux-x64'}


def release_context():
    channel = os.environ.get('FREEFLIGHT_RELEASE_CHANNEL', 'production')
    require(channel in ('production', 'staging'), 'Unknown release channel')
    branch = 'staging' if channel == 'staging' else 'master'
    event = 'push' if channel == 'staging' else 'workflow_dispatch'
    require(os.environ.get('GITHUB_EVENT_NAME') == event and
            os.environ.get('GITHUB_REF') == 'refs/heads/' + branch and
            os.environ.get('GITHUB_REPOSITORY') == REPO, 'Invalid release event, branch or repository')
    return channel, branch


def staging_tag(version, run_id, source):
    require(re.fullmatch(r'\d+\.\d+\.\d+(?:-[A-Za-z0-9.-]+)?', version), 'Invalid staging version')
    require(type(run_id) is int and run_id > 0 and re.fullmatch('[a-f0-9]{40}', source), 'Invalid staging identity')
    separator = '.' if '-' in version else '-'
    return 'v' + version + separator + 'staging.' + str(run_id) + '.' + source[:12]


def check_promotion(source, master, pulls, ancestor, tree, channel='production'):
    require(ancestor(source, master), 'Qualified source is not ancestor of promoted master')
    require(tree(source) == tree(master), 'Promoted master differs from qualified source tree')
    target = master
    chain = []
    require(channel in ('production', 'staging'), 'Unknown promotion channel')
    edges = [('staging', 'dev'), ('dev', 'js/dev')]
    if channel == 'production':
        edges.insert(0, ('master', 'staging'))
    for base, head in edges:
        eligible = [p for p in pulls if p.get('merged_at') and p.get('base', {}).get('ref') == base
                    and p.get('head', {}).get('ref') == head
                    and p['base'].get('repo', {}).get('full_name') == REPO
                    and (p['head'].get('repo') or {}).get('full_name') == REPO
                    and re.fullmatch('[a-f0-9]{40}', p.get('merge_commit_sha') or '')
                    and re.fullmatch('[a-f0-9]{40}', p['head'].get('sha', ''))
                    and ancestor(p['merge_commit_sha'], target)
                    and ancestor(source, p['head']['sha'])]
        require(eligible, 'Missing merged same-repository promotion ' + head + ' -> ' + base)
        selected = max(eligible, key=lambda p: p['merged_at'])
        chain.append(selected['number'])
        target = selected['head']['sha']
    return list(reversed(chain))


def git(*args):
    return subprocess.check_output(['git', *args], text=True).strip()


def verify_runtime_notices(bundle, toolchain, hashes):
    require({'emscripten-runtime-notices.tar.gz', 'runtime-notice-checksums.json'} <= set(hashes),
            'Missing Emscripten runtime redistribution notices')
    expected = {'emscriptenVersion': toolchain['emsdk'], 'sourceCommit': toolchain['emscriptenSourceCommit'],
                'files': toolchain['runtimeNotices']}
    require(bundle.getinfo('runtime-notice-checksums.json').file_size <= 1024 * 1024,
            'Oversized runtime notice checksum receipt')
    require(json.loads(bundle.read('runtime-notice-checksums.json')) == expected, 'Runtime notice pin mismatch')
    require(bundle.getinfo('NOTICES.txt').file_size <= 16 * 1024 ** 2, 'Oversized combined notices')
    combined = bundle.read('NOTICES.txt')
    found = set()
    with bundle.open('emscripten-runtime-notices.tar.gz') as stream, tarfile.open(fileobj=stream, mode='r|gz') as archive:
        for member in archive:
            prefix = 'emscripten/'
            require(member.isfile() and member.name.startswith(prefix) and member.size <= 2 * 1024 ** 2,
                    'Invalid runtime notice archive member')
            name = member.name[len(prefix):]
            require(name in expected['files'] and name not in found, 'Unexpected runtime notice archive member')
            text = archive.extractfile(member).read()
            require(hashlib.sha256(text).hexdigest() == expected['files'][name], 'Runtime notice content hash mismatch')
            require(text in combined, 'Combined redistribution notices omit original runtime text')
            found.add(name)
    require(found == set(expected['files']), 'Incomplete runtime notice archive')


def verify_extra(path, name, source, tree):
    with zipfile.ZipFile(path) as bundle:
        entries = bundle.infolist()
        names = [item.filename for item in entries if not item.is_dir()]
        require(len(entries) <= 20000 and len(set(names)) == len(names), 'Unexpected extra artifact entries')
        require(sum(item.file_size for item in entries) <= 4 * 1024 ** 3, 'Oversized extra artifact')
        for item in entries:
            require(not item.filename.startswith('/') and '..' not in Path(item.filename).parts and
                    '\\' not in item.filename and ':' not in item.filename and
                    (item.external_attr >> 16) & 0o170000 != 0o120000, 'Unsafe extra artifact member')
        receipt_name = 'release.json' if name.startswith('qt-wasm-site-') else 'verification.json'
        require(bundle.getinfo(receipt_name).file_size <= 1024 * 1024, 'Oversized provenance receipt')
        receipt = json.loads(bundle.read(receipt_name))
        if name.startswith('qt-site-audit-'):
            scanner = Path(__file__).resolve().parents[3] / 'workflows/site.audit/assets/scan.py'
            pins = {target.id: ast.literal_eval(node.value) for node in ast.parse(scanner.read_text()).body
                    if isinstance(node, ast.Assign) for target in node.targets
                    if isinstance(target, ast.Name) and target.id in {'VERSION', 'PACKAGES'}}
            require(receipt.get('scanner') == 'Trivy' and receipt.get('version') == pins['VERSION'] and
                    receipt.get('scannerArchiveSha256') == pins['PACKAGES'][('Linux', 'x86_64')][1] and
                    receipt.get('status') == 'passed' and receipt.get('ignoreUnfixed') is False and
                    receipt.get('severity') == ['HIGH', 'CRITICAL'], 'Incomplete or unapproved image vulnerability scan')
            require(bundle.getinfo('vulnerabilities.json').file_size <= 32 * 1024 ** 2, 'Oversized image vulnerability report')
            report = bundle.read('vulnerabilities.json')
            require(hashlib.sha256(report).hexdigest() == receipt.get('reportSha256'), 'Image vulnerability report hash mismatch')
            results = json.loads(report).get('Results')
            require(isinstance(results, list) and results, 'Image scan returned no analyzed results')
            require(not any(v.get('Severity') in {'HIGH', 'CRITICAL'} for result in results
                            for v in (result.get('Vulnerabilities') or [])), 'Image scan contains HIGH/CRITICAL findings')
            return receipt
        require(receipt.get('sourceDirty') is False and receipt.get('sourceCommit') == source and
                receipt.get('sourceTree') == tree, 'Website/container/source provenance mismatch')
        hashes = receipt.get('assets') if name.startswith('qt-wasm-site-') else receipt.get('artifacts')
        require(isinstance(hashes, dict) and hashes, 'Missing extra artifact hashes')
        for filename, expected in hashes.items():
            require(filename in names and re.fullmatch('[a-f0-9]{64}', expected), 'Missing hashed member')
            digest = hashlib.sha256()
            with bundle.open(filename) as stream:
                for block in iter(lambda: stream.read(1024 * 1024), b''):
                    digest.update(block)
            require(digest.hexdigest() == expected, 'Extra artifact member checksum mismatch')
        if name != 'qt-corresponding-sources':
            require(receipt.get('environment') == name.rsplit('-', 1)[1], 'Website environment mismatch')
            if name.startswith('qt-wasm-site-'):
                toolchain = json.loads((Path(__file__).resolve().parents[3] / 'site/toolchain.json').read_text())
                require(receipt.get('qt') == toolchain['qt'], 'Website renderer Qt differs from approved toolchain')
        else:
            require({'freeflight-site-relink-source.tar.gz', 'NOTICES.txt'} <= set(hashes), 'Incomplete corresponding source')
            root = Path(__file__).resolve().parents[3]
            toolchain = json.loads((root / 'site/toolchain.json').read_text())
            qt = toolchain['qt']
            require(tuple(map(int, qt.split('.'))) >= (6, 12, 0), 'Legacy Qt release candidate blocked by security audit')
            require(receipt.get('qtVersion') == qt, 'Corresponding source Qt version mismatch')
            pins = toolchain['qtSources']
            require(json.loads(bundle.read('source-checksums.json')) == pins, 'Corresponding source pins differ from project')
            for module, expected in pins.items():
                require(hashes.get(module + '-everywhere-src-' + qt + '.tar.xz') == expected, 'Missing or obsolete Qt module source')
            verify_runtime_notices(bundle, toolchain, hashes)
        return receipt


def check_extra_links(receipts, site_hashes):
    for environment in ('staging', 'production'):
        image = receipts['qt-site-container-' + environment]
        audit = receipts['qt-site-audit-' + environment]
        require(audit.get('imageArchiveSha256') == image['artifacts'].get('freeflight-site-image.tar.gz'),
                'Vulnerability scan did not qualify the retained container bytes')
        require(image.get('siteReleaseSha256') == site_hashes[environment],
                'Container did not qualify the exact retained site assets')


def main():
    channel, branch = release_context()
    selected_platforms = platforms(channel)
    root = Path(__file__).resolve().parents[3]
    candidate = Path(os.environ['FREEFLIGHT_RELEASE_CANDIDATE']).resolve()
    evidence = json.loads((candidate / 'evidence.json').read_text())
    source = check_run(evidence['run'], '.github/workflows/ci.yml')
    check_run(evidence['codeql'], '.github/workflows/codeql.yml', source)
    master = os.environ['GITHUB_SHA']
    require(git('rev-parse', 'HEAD') == master == evidence['master'], 'Dispatch checkout or current master changed')
    ancestor = lambda a, b: subprocess.run(['git', 'merge-base', '--is-ancestor', a, b], capture_output=True).returncode == 0
    chain = check_promotion(source, master, evidence['pulls'], ancestor,
                            lambda commit: git('rev-parse', commit + '^{tree}'), channel)
    artifacts = evidence['artifacts']
    require(len(artifacts) == len(selected_platforms) + len(EXTRAS) and {a['name'] for a in artifacts} == set(selected_platforms) | EXTRAS, 'All native, website, container, source and audit artifacts required')
    for artifact in artifacts:
        require(artifact.get('expired') is False and artifact.get('workflow_run', {}).get('id') == evidence['run']['id'] and
                artifact['workflow_run'].get('head_sha') == source, 'Artifact run identity mismatch or expired artifact')
    spec = importlib.util.spec_from_file_location('release_prepare', root / 'workflows/release.prepare/assets/prepare.py')
    prepare = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(prepare)
    paths = sorted(p for p in (candidate / 'artifacts').rglob('*') if p.name.endswith(('.tar.gz', '.mcpb')))
    version = (root / 'VERSION').read_text().strip()
    config = {'version': version, 'tag': 'v' + version, 'mode': 'draft',
              'expectedRids': sorted(selected_platforms.values()), 'registryRid': 'osx-arm64',
              'artifacts': [str(p) for p in paths]}
    prepared = prepare.prepare(config, root / 'bin/.local/release-prepared')
    report = json.loads((prepared / 'release-manifest.json').read_text())
    report.update(channel=channel, sourceCommit=source, promotedCommit=master,
                  qualificationRun=evidence['run']['id'], codeqlRun=evidence['codeql']['id'])
    if channel == 'staging':
        report['tag'] = staging_tag(version, evidence['run']['id'], source)
        for artifact in report['artifacts']:
            artifact['candidateUrl'] = prepare.REPO_URL + '/releases/download/' + report['tag'] + '/' + artifact['filename']
    for artifact in report['artifacts']:
        require(artifact['verification']['sourceCommit'] == source and
                artifact['verification']['sourceTree'] == git('rev-parse', master + '^{tree}'), 'Embedded provenance differs from hosted qualified source')
    extras = []
    for artifact in artifacts:
        if artifact['name'] in EXTRAS:
            path = candidate / 'additional' / (artifact['name'] + '.zip')
            receipt = verify_extra(path, artifact['name'], source, git('rev-parse', master + '^{tree}'))
            with path.open('rb') as stream:
                digest = prepare.digest(stream)
            require('sha256:' + digest == artifact['digest'], 'Extra archive differs from GitHub receipt')
            extras.append({'filename': path.name, 'source': str(path), 'sha256': digest, 'verification': receipt})
    extra_receipts = {item['filename'][:-4]: item['verification'] for item in extras}
    site_hashes = {}
    for environment in ('staging', 'production'):
        with zipfile.ZipFile(candidate / 'additional' / ('qt-wasm-site-' + environment + '.zip')) as site:
            site_hashes[environment] = hashlib.sha256(site.read('release.json')).hexdigest()
    check_extra_links(extra_receipts, site_hashes)
    report['additionalAssets'] = extras
    if channel == 'staging':
        jammy = candidate / 'artifacts/preview-ubuntu-22.04-linux-x64/jammy-compatibility.json'
        receipt = json.loads(jammy.read_text())
        linux = next(a for a in report['artifacts'] if a['rid'] == 'linux-x64' and a['format'] == 'tar.gz')
        require(receipt.get('sourceCommit') == source and receipt.get('sourceTree') == git('rev-parse', master + '^{tree}')
                and receipt.get('status') == 'qualified-on-ubuntu-22.04'
                and receipt.get('artifact') == linux['filename'] and receipt.get('sha256') == linux['sha256'],
                'Jammy compatibility receipt mismatch')
        extras.append({'filename': jammy.name, 'source': str(jammy),
                       'sha256': hashlib.sha256(jammy.read_bytes()).hexdigest(), 'verification': receipt})
    (prepared / 'release-manifest.json').write_text(json.dumps(report, indent=2) + '\n')
    with (prepared / 'SHA256SUMS').open('a') as sums:
        for item in sorted(extras, key=lambda item: item['filename']):
            sums.write(item['sha256'] + '  ' + item['filename'] + '\n')
    result = {'prepared': str(prepared), 'master': master, 'source': source, 'promotionPulls': chain,
              'runId': evidence['run']['id'], 'codeqlRunId': evidence['codeql']['id'], 'config': config,
              'channel': channel, 'branch': branch}
    (candidate / 'verified.json').write_text(json.dumps(result, indent=2) + '\n')
    print('Complete release candidate verified; no tag or release created')


if __name__ == '__main__':
    main()
