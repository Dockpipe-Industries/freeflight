# SPDX-License-Identifier: Apache-2.0
import copy
import unittest
import hashlib
import json
from pathlib import Path
import tempfile
import zipfile
import io
import tarfile
from unittest.mock import patch
from policy import REPO, check_promotion, check_run, verify_extra, check_extra_links, verify_runtime_notices, release_context, staging_tag, platforms


class ReleasePolicy(unittest.TestCase):
    def test_staging_context_cannot_authorize_master_or_manual_publication(self):
        environment = {"FREEFLIGHT_RELEASE_CHANNEL": "staging", "GITHUB_EVENT_NAME": "push",
                       "GITHUB_REF": "refs/heads/staging", "GITHUB_REPOSITORY": REPO}
        with patch.dict("os.environ", environment, clear=True):
            self.assertEqual(release_context(), ("staging", "staging"))
        for key, value in (("GITHUB_REF", "refs/heads/master"), ("GITHUB_EVENT_NAME", "workflow_dispatch"),
                           ("GITHUB_REPOSITORY", "other/freeflight")):
            with patch.dict("os.environ", {**environment, key: value}, clear=True):
                with self.assertRaises(ValueError):
                    release_context()

    def test_production_remains_explicit_master_dispatch(self):
        with patch.dict("os.environ", {"GITHUB_EVENT_NAME": "push", "GITHUB_REF": "refs/heads/master",
                                      "GITHUB_REPOSITORY": REPO}, clear=True):
            with self.assertRaises(ValueError):
                release_context()

    def test_staging_identity_is_unique_and_uses_compatible_linux_build(self):
        self.assertEqual(staging_tag("0.1.0", 42, "a" * 40), "v0.1.0-staging.42." + "a" * 12)
        self.assertNotEqual(staging_tag("0.1.0-preview.rc2", 42, "a" * 40),
                            staging_tag("0.1.0-preview.rc2", 43, "a" * 40))
        self.assertEqual(platforms("staging")["preview-ubuntu-22.04-linux-x64"], "linux-x64")
        self.assertNotIn("native-ubuntu-24.04", platforms("staging"))

    def test_staging_requires_both_promotions_but_not_master(self):
        self.assertEqual(check_promotion(self.source, "c" * 40, self.pulls[:2],
                                         lambda a, b: a <= b, lambda sha: "e" * 40, "staging"), [1, 2])
        with self.assertRaises(ValueError):
            check_promotion(self.source, "c" * 40, self.pulls[1:2],
                            lambda a, b: a <= b, lambda sha: "e" * 40, "staging")

    def setUp(self):
        self.run = {'repository': {'full_name': REPO}, 'head_repository': {'full_name': REPO},
                    'path': '.github/workflows/ci.yml', 'event': 'push', 'head_branch': 'js/dev',
                    'status': 'completed', 'conclusion': 'success', 'head_sha': 'a' * 40}
        self.source, self.master = 'a' * 40, 'd' * 40
        self.pulls = []
        for n, (base, head, before, after) in enumerate([
                ('dev', 'js/dev', 'a', 'b'), ('staging', 'dev', 'b', 'c'), ('master', 'staging', 'c', 'd')], 1):
            self.pulls.append({'number': n, 'merged_at': '2026-10-19', 'merge_commit_sha': after * 40,
                               'base': {'ref': base, 'repo': {'full_name': REPO}},
                               'head': {'ref': head, 'sha': before * 40, 'repo': {'full_name': REPO}}})

    def promotion(self, pulls=None, ancestor=None, tree=None):
        return check_promotion(self.source, self.master, self.pulls if pulls is None else pulls,
                               ancestor or (lambda a, b: a <= b), tree or (lambda sha: 'e' * 40))

    def test_successful_push_and_exact_codeql_source(self):
        self.assertEqual(check_run(self.run, '.github/workflows/ci.yml'), self.source)
        self.run['path'] = '.github/workflows/codeql.yml'
        self.assertEqual(check_run(self.run, self.run['path'], self.source), self.source)
        with self.assertRaises(ValueError):
            check_run(self.run, self.run['path'], 'f' * 40)

    def test_invalid_run_ref_event_state_source(self):
        for field, value in [('event', 'pull_request'), ('head_branch', 'master'),
                             ('status', 'in_progress'), ('conclusion', 'failure'),
                             ('path', '.github/workflows/other.yml'), ('head_sha', 'invalid'),
                             ('head_repository', {'full_name': 'attacker/freeflight'})]:
            with self.subTest(field=field):
                run = copy.deepcopy(self.run)
                run[field] = value
                with self.assertRaises(ValueError):
                    check_run(run, '.github/workflows/ci.yml')

    def test_complete_promotion_chain(self):
        self.assertEqual(self.promotion(), [1, 2, 3])

    def test_missing_and_unmerged_promotions(self):
        for index in range(3):
            with self.assertRaises(ValueError):
                self.promotion(self.pulls[:index] + self.pulls[index + 1:])
            pulls = copy.deepcopy(self.pulls)
            pulls[index]['merged_at'] = None
            with self.assertRaises(ValueError):
                self.promotion(pulls)

    def test_foreign_or_wrong_branch_promotion(self):
        for field, value in [('ref', 'other'), ('repo', {'full_name': 'other/freeflight'})]:
            pulls = copy.deepcopy(self.pulls)
            pulls[1]['head'][field] = value
            with self.assertRaises(ValueError):
                self.promotion(pulls)

    def test_nonancestor_and_changed_master_tree(self):
        with self.assertRaises(ValueError):
            self.promotion(ancestor=lambda a, b: False)
        with self.assertRaises(ValueError):
            self.promotion(tree=lambda sha: sha)

    def test_wrong_merge_ancestry(self):
        pulls = copy.deepcopy(self.pulls)
        pulls[1]['merge_commit_sha'] = 'f' * 40
        with self.assertRaises(ValueError):
            self.promotion(pulls)


    def test_container_source_environment_hash(self):
        receipt = {'sourceDirty': False, 'sourceCommit': self.source, 'sourceTree': 'e' * 40,
                   'environment': 'production', 'artifacts': {'image.tar.gz': hashlib.sha256(b'image').hexdigest()}}
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'container.zip'
            def write(value, content=b'image'):
                with zipfile.ZipFile(path, 'w') as bundle:
                    bundle.writestr('verification.json', json.dumps(value))
                    bundle.writestr('image.tar.gz', content)
            write(receipt)
            verify_extra(path, 'qt-site-container-production', self.source, 'e' * 40)
            for key, value in [('sourceDirty', True), ('sourceCommit', 'f' * 40),
                               ('sourceTree', 'f' * 40), ('environment', 'staging')]:
                write({**receipt, key: value})
                with self.assertRaises(ValueError):
                    verify_extra(path, 'qt-site-container-production', self.source, 'e' * 40)
            write(receipt, b'tampered')
            with self.assertRaises(ValueError):
                verify_extra(path, 'qt-site-container-production', self.source, 'e' * 40)

    def test_incomplete_corresponding_sources_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'sources.zip'
            with zipfile.ZipFile(path, 'w') as bundle:
                bundle.writestr('verification.json', json.dumps({'sourceDirty': False,
                    'sourceCommit': self.source, 'sourceTree': 'e' * 40, 'artifacts': {'NOTICES.txt': hashlib.sha256(b'notice').hexdigest()}}))
                bundle.writestr('NOTICES.txt', 'notice')
            with self.assertRaises(ValueError):
                verify_extra(path, 'qt-corresponding-sources', self.source, 'e' * 40)

    def test_obsolete_qt_renderer_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'site.zip'
            with zipfile.ZipFile(path, 'w') as bundle:
                bundle.writestr('release.json', json.dumps({'sourceDirty': False,
                    'sourceCommit': self.source, 'sourceTree': 'e' * 40, 'environment': 'production',
                    'qt': '6.8.3', 'assets': {'index.html': hashlib.sha256(b'site').hexdigest()}}))
                bundle.writestr('index.html', 'site')
            with self.assertRaises(ValueError):
                verify_extra(path, 'qt-wasm-site-production', self.source, 'e' * 40)

    def test_audit_container_site_bindings(self):
        receipts = {}
        site_hashes = {}
        for environment in ('staging', 'production'):
            receipts['qt-site-container-' + environment] = {'artifacts': {'freeflight-site-image.tar.gz': 'a' * 64}, 'siteReleaseSha256': 'b' * 64}
            receipts['qt-site-audit-' + environment] = {'imageArchiveSha256': 'a' * 64}
            site_hashes[environment] = 'b' * 64
        check_extra_links(receipts, site_hashes)
        receipts['qt-site-audit-production']['imageArchiveSha256'] = 'c' * 64
        with self.assertRaises(ValueError):
            check_extra_links(receipts, site_hashes)
        receipts['qt-site-audit-production']['imageArchiveSha256'] = 'a' * 64
        site_hashes['production'] = 'd' * 64
        with self.assertRaises(ValueError):
            check_extra_links(receipts, site_hashes)

    def test_scan_rejects_critical_findings_and_altered_report(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'audit.zip'
            for vulnerabilities, tamper, valid in [([], False, True), ([{'Severity': 'CRITICAL'}], False, False), ([], True, False)]:
                report = json.dumps({'Results': [{'Vulnerabilities': vulnerabilities}]}).encode()
                receipt = {'scanner': 'Trivy', 'version': '0.76.0', 'scannerArchiveSha256': 'e24b1c51293c1b15e4ba8d45bbc7891ba053f90278ec2698f3562c993e145fe7',
                           'status': 'passed', 'ignoreUnfixed': False, 'severity': ['HIGH', 'CRITICAL'],
                           'reportSha256': 'f' * 64 if tamper else hashlib.sha256(report).hexdigest()}
                with zipfile.ZipFile(path, 'w') as bundle:
                    bundle.writestr('verification.json', json.dumps(receipt))
                    bundle.writestr('vulnerabilities.json', report)
                if valid:
                    verify_extra(path, 'qt-site-audit-production', self.source, 'e' * 40)
                else:
                    with self.assertRaises(ValueError):
                        verify_extra(path, 'qt-site-audit-production', self.source, 'e' * 40)


    def test_runtime_notice_originals_and_receipt(self):
        text = b'Original runtime license text\n'
        toolchain = {'emsdk': '5.0.5', 'emscriptenSourceCommit': 'b' * 40,
                     'runtimeNotices': {'LICENSE': hashlib.sha256(text).hexdigest()}}
        receipt = {'emscriptenVersion': '5.0.5', 'sourceCommit': 'b' * 40, 'files': toolchain['runtimeNotices']}
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'notices.zip'
            for content, combined, valid in [(text, text, True), (b'altered', text, False), (text, b'omitted', False)]:
                archive_bytes = io.BytesIO()
                with tarfile.open(fileobj=archive_bytes, mode='w:gz') as archive:
                    item = tarfile.TarInfo('emscripten/LICENSE')
                    item.size = len(content)
                    archive.addfile(item, io.BytesIO(content))
                with zipfile.ZipFile(path, 'w') as bundle:
                    bundle.writestr('emscripten-runtime-notices.tar.gz', archive_bytes.getvalue())
                    bundle.writestr('runtime-notice-checksums.json', json.dumps(receipt))
                    bundle.writestr('NOTICES.txt', combined)
                with zipfile.ZipFile(path) as bundle:
                    hashes = {'emscripten-runtime-notices.tar.gz': '', 'runtime-notice-checksums.json': ''}
                    if valid:
                        verify_runtime_notices(bundle, toolchain, hashes)
                    else:
                        with self.assertRaises(ValueError):
                            verify_runtime_notices(bundle, toolchain, hashes)
                    with self.assertRaises(ValueError):
                        verify_runtime_notices(bundle, toolchain, {})


if __name__ == '__main__':
    unittest.main()
