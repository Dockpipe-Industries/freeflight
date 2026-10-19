# SPDX-License-Identifier: Apache-2.0
import copy
import hashlib
import io
import json
from pathlib import Path
import tarfile
import tempfile
import unittest
import zipfile
from prepare import CHECKS, inspect_archive, prepare


def sha(data):
    return hashlib.sha256(data).hexdigest()


def fixture(directory, rid='osx-arm64', version='0.1.0', receipt_rid=None, node=b'node', tamper=False, dirty=False, commit='1' * 40, unsafe=False):
    windows = rid.startswith('win-')
    binary = 'bin/freeflight.exe' if windows else 'bin/freeflight'
    runtime = 'lib/freeflight/node/node.exe' if windows else 'lib/freeflight/node/bin/node'
    files = {binary: b'core', runtime: node}
    files['verification.json'] = json.dumps({'rid': receipt_rid or rid, 'productionPublication': False, 'nodeExecutableSha256': sha(node), 'checks': sorted(CHECKS), 'sourceDirty': dirty, 'sourceCommit': commit, 'sourceTree': '2' * 40}).encode()
    files['manifest.json'] = json.dumps({'manifest_version': '0.3', 'version': version, 'name': 'freeflight', 'server': {'type': 'binary', 'entry_point': binary, 'mcp_config': {'command': '${__dirname}/' + binary, 'args': ['--workspace', '${user_config.workspace}']}}, 'compatibility': {'platforms': ['win32' if windows else 'darwin' if rid.startswith('osx') else 'linux']}}).encode()
    if unsafe:
        files['../escape'] = b'outside'
    sums = ''.join(sha(content) + '  ' + name + '\n' for name, content in sorted(files.items())).encode()
    files['SHA256SUMS'] = sums
    if tamper:
        files[binary] = b'changed'
    tar = directory / ('freeflight-' + rid + '-' + sha(sums)[:16] + '.tar.gz')
    with tarfile.open(tar, 'w:gz') as archive:
        for name, content in files.items():
            member = tarfile.TarInfo('freeflight-' + rid + '/' + name)
            member.size = len(content)
            archive.addfile(member, io.BytesIO(content))
    temp = directory / 'bundle.zip'
    with zipfile.ZipFile(temp, 'w') as archive:
        for name, content in files.items():
            archive.writestr(name, content)
    mcpb = directory / ('freeflight-' + rid + '-' + sha(temp.read_bytes())[:16] + '.mcpb')
    temp.rename(mcpb)
    for path in (tar, mcpb):
        path.with_name(path.name + '.sha256').write_text(sha(path.read_bytes()) + '  ' + path.name + '\n')
    return [str(tar), str(mcpb)]


class PrepareTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.paths = fixture(self.root)
        self.config = {'version': '0.1.0', 'tag': 'v0.1.0', 'expectedRids': ['osx-arm64'], 'registryRid': 'osx-arm64', 'artifacts': self.paths}

    def test_draft_no_network_and_no_publishable_packages(self):
        def forbidden(*args):
            self.fail('Draft must not query remote URLs')
        output = prepare(self.config, self.root / 'out', forbidden)
        server = json.loads((output / 'server.template-not-publishable.json').read_text())
        self.assertNotIn('packages', server)
        self.assertEqual(len((output / 'SHA256SUMS').read_text().splitlines()), 2)

    def test_verified_mode_checks_exact_urls_and_hashes(self):
        calls = []
        self.config['mode'] = 'verify-urls'
        output = prepare(self.config, self.root / 'out', lambda *args: calls.append(args))
        self.assertEqual(len(calls), 2)
        self.assertTrue(all(url.startswith('https://github.com/Dockpipe-Industries/freeflight/releases/download/v0.1.0/freeflight-osx-arm64-') for url, _ in calls))
        server = json.loads((output / 'server.draft.json').read_text())
        self.assertEqual(server['packages'][0]['identifier'], calls[1][0])
        self.assertEqual(server['packages'][0]['fileSha256'], calls[1][1])

    def test_remote_failure_emits_no_output(self):
        self.config['mode'] = 'verify-urls'
        def fail(*args):
            raise ValueError('Remote checksum mismatch')
        with self.assertRaisesRegex(ValueError, 'Remote'):
            prepare(self.config, self.root / 'out', fail)
        self.assertFalse((self.root / 'out').exists())

    def test_missing_receipt(self):
        Path(self.paths[0] + '.sha256').unlink()
        with self.assertRaisesRegex(ValueError, 'Missing checksum'):
            prepare(self.config, self.root / 'out')

    def test_tampered_outer_archive(self):
        with Path(self.paths[0]).open('ab') as output:
            output.write(b'tamper')
        with self.assertRaisesRegex(ValueError, 'checksum receipt'):
            prepare(self.config, self.root / 'out')

    def test_tampered_internal_file_with_updated_outer_hash(self):
        self.config['artifacts'] = fixture(self.root, tamper=True)
        with self.assertRaisesRegex(ValueError, 'Tampered archive file'):
            prepare(self.config, self.root / 'out')

    def test_wrong_receipt_rid(self):
        self.config['artifacts'] = fixture(self.root, receipt_rid='win-x64')
        with self.assertRaisesRegex(ValueError, 'Incompatible verification'):
            prepare(self.config, self.root / 'out')

    def test_incompatible_version(self):
        self.config['artifacts'] = fixture(self.root, version='0.2.0')
        with self.assertRaisesRegex(ValueError, 'Incompatible MCPB'):
            prepare(self.config, self.root / 'out')

    def test_missing_or_duplicate_platform(self):
        self.config['artifacts'] = self.paths[:1]
        with self.assertRaises(ValueError):
            prepare(self.config, self.root / 'out')
        self.config['artifacts'] = [self.paths[0], self.paths[0]]
        with self.assertRaises(ValueError):
            prepare(self.config, self.root / 'out')

    def test_mismatched_pair(self):
        other = self.root / 'other'
        other.mkdir()
        alternate = fixture(other, node=b'another-runtime')
        self.config['artifacts'] = [self.paths[0], alternate[1]]
        with self.assertRaisesRegex(ValueError, 'contents differ'):
            prepare(self.config, self.root / 'out')

    def test_dirty_or_missing_clean_provenance(self):
        for dirty in (True, None):
            self.config['artifacts'] = fixture(self.root, dirty=dirty)
            with self.assertRaisesRegex(ValueError, 'clean-source provenance'):
                prepare(self.config, self.root / 'out')

    def test_incompatible_source_provenance(self):
        other = self.root / 'other'
        other.mkdir()
        self.config['expectedRids'].append('linux-x64')
        self.config['artifacts'] += fixture(other, rid='linux-x64', commit='3' * 40)
        with self.assertRaisesRegex(ValueError, 'incompatible source provenance'):
            prepare(self.config, self.root / 'out')

    def test_archive_path_traversal(self):
        self.config['artifacts'] = fixture(self.root, unsafe=True)
        with self.assertRaisesRegex(ValueError, 'Unsafe archive path'):
            prepare(self.config, self.root / 'out')
        self.assertFalse((self.root / 'escape').exists())

    def test_tag_and_rid_required(self):
        for key, value in [('tag', 'v0.2.0'), ('registryRid', 'win-x64'), ('expectedRids', ['unknown'])]:
            config = copy.deepcopy(self.config)
            config[key] = value
            with self.assertRaises(ValueError):
                prepare(config, self.root / 'out')


if __name__ == '__main__':
    unittest.main()
