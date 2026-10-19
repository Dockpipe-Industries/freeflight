# SPDX-License-Identifier: Apache-2.0
import copy
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import publish


class PublicationPolicy(unittest.TestCase):
    def setUp(self):
        self.artifact = {'rid': 'osx-arm64', 'format': 'mcpb',
                         'filename': 'freeflight-osx-arm64-' + 'a' * 16 + '.mcpb',
                         'sha256': 'a' * 64,
                         'verification': {'sourceDirty': False, 'sourceCommit': 'b' * 40}}
        self.artifact['candidateUrl'] = publish.REPO + '/releases/download/v0.1.0/' + self.artifact['filename']
        self.report = {'status': 'prepared-not-published', 'mode': 'verify-urls', 'version': '0.1.0',
                       'tag': 'v0.1.0', 'registryRid': 'osx-arm64', 'artifacts': [self.artifact]}
        self.server = {'name': 'io.github.Dockpipe-Industries/freeflight', 'version': '0.1.0',
                       'repository': {'url': publish.REPO, 'source': 'github'},
                       'packages': [{'registryType': 'mcpb', 'identifier': self.artifact['candidateUrl'],
                                     'fileSha256': 'a' * 64, 'transport': {'type': 'stdio'}}],
                       '_meta': {'io.modelcontextprotocol.registry/publisher-provided': {
                           'assetUrlsVerified': True, 'selectedRid': 'osx-arm64'}}}

    def test_valid_prepared_contract(self):
        self.assertEqual(publish.check_metadata(self.server, self.report, '0.1.0'), self.artifact)

    def test_reject_unqualified_inputs(self):
        cases = [(['mode'], 'draft'), (['tag'], 'v9.9.9'), (['registryRid'], 'win-x64'),
                 (['artifacts', 0, 'candidateUrl'], 'http://example.com/file'),
                 (['artifacts', 0, 'verification', 'sourceDirty'], True),
                 (['artifacts', 0, 'verification', 'sourceCommit'], 'unknown')]
        for keys, value in cases:
            with self.subTest(keys=keys):
                report = copy.deepcopy(self.report)
                target = report
                for key in keys[:-1]:
                    target = target[key]
                target[keys[-1]] = value
                with self.assertRaises(ValueError):
                    publish.check_metadata(self.server, report, '0.1.0')

    def test_reject_metadata_changes(self):
        for field, value in [('name', 'io.github.other/freeflight'), ('version', '9.9.9'),
                             ('repository', {'url': 'https://example.com'}),
                             ('remotes', [{'url': 'https://example.com'}]), ('packages', [])]:
            with self.subTest(field=field):
                server = copy.deepcopy(self.server)
                server[field] = value
                with self.assertRaises(ValueError):
                    publish.check_metadata(server, self.report, '0.1.0')

    def test_reject_package_hash_change(self):
        self.server['packages'][0]['fileSha256'] = 'c' * 64
        with self.assertRaises(ValueError):
            publish.check_metadata(self.server, self.report, '0.1.0')

    def test_tag_commit_match(self):
        with patch.object(publish, 'fetch', return_value=b'{"object":{"type":"commit","sha":"bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"}}'):
            publish.verify_tag('0.1.0', 'b' * 40)

    def test_promoted_tag_requires_ancestor_and_identical_tree(self):
        tag = {'object': {'type': 'commit', 'sha': 'd' * 40}}
        for status, base, target_tree, valid in [('ahead', 'b' * 40, 'e' * 40, True),
                ('diverged', 'a' * 40, 'e' * 40, False), ('ahead', 'b' * 40, 'f' * 40, False)]:
            replies = [tag, {'status': status, 'merge_base_commit': {'sha': base}},
                       {'tree': {'sha': 'e' * 40}}, {'tree': {'sha': target_tree}}]
            with patch.object(publish, 'fetch', side_effect=[__import__('json').dumps(value).encode() for value in replies]):
                if valid:
                    publish.verify_tag('0.1.0', 'b' * 40)
                else:
                    with self.assertRaises(ValueError):
                        publish.verify_tag('0.1.0', 'b' * 40)

    def test_redirect_security(self):
        for url in ['http://github.com/asset', 'https://example.com/asset', 'https://github.com.evil.test/asset']:
            with self.assertRaises(ValueError):
                publish.SecureRedirect().redirect_request(None, None, 302, '', {}, url)

    def test_unpinned_publisher_rejected_without_execution(self):
        with tempfile.TemporaryDirectory() as directory:
            archive = Path(directory) / 'archive.tar.gz'
            archive.write_bytes(b'untrusted executable archive')
            with patch.object(publish.subprocess, 'run') as execute:
                with self.assertRaises(ValueError):
                    publish.verify_publisher(Path(directory) / 'publisher', archive)
                execute.assert_not_called()


if __name__ == '__main__':
    unittest.main()
