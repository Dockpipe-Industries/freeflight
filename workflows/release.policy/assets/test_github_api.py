# SPDX-License-Identifier: Apache-2.0
"""Offline GitHub request and redirect regressions; never use real credentials."""
import importlib.util
import copy
import io
import json
from pathlib import Path
import unittest
import tempfile
import zipfile
from unittest.mock import Mock, patch
from urllib.request import Request

ROOT = Path(__file__).resolve().parents[3]
spec = importlib.util.spec_from_file_location('release_github_api', ROOT / '.github/release/api.py')
api = importlib.util.module_from_spec(spec)
spec.loader.exec_module(api)


class GitHubApiTests(unittest.TestCase):
    def test_draft_without_tag_blocks_duplicate_creation(self):
        with patch.object(api, 'request', return_value=[{'tag_name': 'v0.1.0-staging.42.abc', 'draft': True}]) as request:
            with self.assertRaisesRegex(ValueError, 'Existing draft'):
                api.require_release_absent('v0.1.0-staging.42.abc')
            self.assertEqual(request.call_count, 1)

    def test_absence_requires_both_release_and_tag_404(self):
        missing = api.HTTPError('https://api.github.com', 404, 'Not found', {}, None)
        with patch.object(api, 'request', side_effect=[[], missing, missing]) as request:
            api.require_release_absent('v0.1.0')
            self.assertEqual(request.call_count, 3)

    def test_jammy_receipt_requires_explicit_compatibility_artifact(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            archive = root / "download.zip"
            with zipfile.ZipFile(archive, "w") as bundle:
                bundle.writestr("jammy-compatibility.json", "{}")
            with self.assertRaises(ValueError):
                api.extract_native_artifact(archive, root)
            api.extract_native_artifact(archive, root, jammy=True)
            self.assertEqual((root / "jammy-compatibility.json").read_text(), "{}")

    def test_native_artifact_accepts_flat_and_packages_layout(self):
        for prefix in ('', 'packages/'):
            with self.subTest(prefix=prefix), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                archive = root / 'download.zip'
                names = ['freeflight-linux-x64-abcd.tar.gz', 'freeflight-linux-x64-abcd.tar.gz.sha256',
                         'freeflight-linux-x64-abcd.mcpb', 'freeflight-linux-x64-abcd.mcpb.sha256']
                with zipfile.ZipFile(archive, 'w') as bundle:
                    for name in names:
                        bundle.writestr(prefix + name, name.encode())
                api.extract_native_artifact(archive, root)
                for name in names:
                    self.assertEqual((root / name).read_bytes(), name.encode())

    def test_native_artifact_rejects_unsafe_layout_before_writes(self):
        valid = 'freeflight-linux-x64-abcd.tar.gz'
        for invalid in ('../' + valid, 'packages/../' + valid, '/' + valid,
                        'packages/packages/' + valid, 'other/' + valid, 'packages/',
                        'packages\\\\' + valid, 'jammy-compatibility.json',
                        'packages/' + valid):
            with self.subTest(invalid=invalid), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                archive = root / 'download.zip'
                with zipfile.ZipFile(archive, 'w') as bundle:
                    bundle.writestr(valid, b'first')
                    bundle.writestr(invalid, b'second')
                with self.assertRaisesRegex(ValueError, 'Unsafe artifact entry'):
                    api.extract_native_artifact(archive, root)
                self.assertFalse((root / valid).exists())

    def test_native_artifact_rejects_special_files_and_existing_outputs(self):
        name = 'freeflight-linux-x64-abcd.tar.gz'
        for mode in (0o120777, 0o010600, 0o020600):
            with self.subTest(mode=mode), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                archive = root / 'download.zip'
                entry = zipfile.ZipInfo('packages/' + name)
                entry.create_system = 3
                entry.external_attr = mode << 16
                with zipfile.ZipFile(archive, 'w') as bundle:
                    bundle.writestr(entry, b'target')
                with self.assertRaisesRegex(ValueError, 'Unsafe artifact entry'):
                    api.extract_native_artifact(archive, root)
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            archive = root / 'download.zip'
            (root / name).write_bytes(b'preserved')
            with zipfile.ZipFile(archive, 'w') as bundle:
                bundle.writestr(name, b'replacement')
            with self.assertRaises(FileExistsError):
                api.extract_native_artifact(archive, root)
            self.assertEqual((root / name).read_bytes(), b'preserved')

    def promotion_fixture(self):
        pull = {'number': 3, 'merged_at': '2026-10-19T22:46:42Z',
                'base': {'ref': 'master', 'repo': {'full_name': api.REPO}},
                'head': {'ref': 'staging', 'sha': 'a' * 40, 'repo': {'full_name': api.REPO}}}
        event = {'event': 'merged', 'commit_id': 'b' * 40,
                 'commit_url': api.API + '/commits/' + 'b' * 40,
                 'created_at': pull['merged_at']}
        return pull, event

    def commit_fixture(self, pull, event):
        parents = ['c' * 40, pull['head']['sha']]
        return {'sha': event['commit_id'], 'url': event['commit_url'],
                'parents': [{'sha': sha, 'url': api.API + '/commits/' + sha} for sha in parents]}

    def test_current_api_promotion_uses_authoritative_timeline_commit(self):
        pull, event = self.promotion_fixture()
        commit = self.commit_fixture(pull, event)
        with patch.object(api, 'request', side_effect=[[event], commit]) as request:
            evidence = api.promotion_evidence([pull])
        self.assertEqual(request.call_args_list[0].args, ('/issues/3/timeline?per_page=100&page=1',))
        self.assertEqual(request.call_args_list[1].args, ('/commits/' + 'b' * 40,))
        self.assertEqual(evidence[0]['merge_commit_sha'], 'b' * 40)
        self.assertEqual(evidence[0]['merge_event'], event)
        self.assertEqual(evidence[0]['merge_commit_evidence'], commit)
        self.assertNotIn('merge_commit_sha', pull)
        self.assertNotEqual(evidence[0]['merge_commit_sha'], pull['head']['sha'])

    def test_promotion_ignores_unmerged_foreign_deleted_and_unrelated_heads(self):
        pull, _ = self.promotion_fixture()
        variants = [copy.deepcopy(pull) for _ in range(5)]
        variants[0]['merged_at'] = None
        variants[1]['head']['repo']['full_name'] = 'elsewhere/freeflight'
        variants[2]['base']['repo']['full_name'] = 'elsewhere/freeflight'
        variants[3]['head']['repo'] = None
        variants[4]['head']['ref'] = 'feature/unrelated'
        with patch.object(api, 'request') as request:
            self.assertEqual(api.promotion_evidence(variants), [])
            request.assert_not_called()

    def test_promotion_rejects_missing_ambiguous_or_mismatched_events(self):
        pull, event = self.promotion_fixture()
        invalid = [[], [event, event],
                   [{**event, 'commit_id': 'not-a-sha'}],
                   [{**event, 'commit_url': 'https://api.github.com/repos/elsewhere/repo/commits/' + 'b' * 40}],
                   [{**event, 'created_at': '2026-10-19T00:00:00Z'}]]
        for events in invalid:
            with self.subTest(events=events), patch.object(api, 'request', return_value=events):
                with self.assertRaises(ValueError):
                    api.promotion_evidence([pull])

    def test_promotion_paginates_and_rejects_exhausted_history(self):
        pull, event = self.promotion_fixture()
        page = [{'event': 'commented'}] * 100
        with patch.object(api, 'request', side_effect=[page, [event], self.commit_fixture(pull, event)]) as request:
            self.assertEqual(api.promotion_evidence([pull])[0]['merge_commit_sha'], 'b' * 40)
            self.assertEqual(request.call_args_list[1].args[0], '/issues/3/timeline?per_page=100&page=2')
        with patch.object(api, 'request', return_value=page) as request:
            with self.assertRaisesRegex(ValueError, 'exceeds bounded query'):
                api.promotion_evidence([pull])
            self.assertEqual(request.call_count, 10)

    def test_real_pr28_shape_allows_one_second_recording_delay(self):
        pull, event = self.promotion_fixture()
        pull.update(number=28, merged_at='2026-10-20T05:49:54Z')
        pull['head']['sha'] = '013811b0f2fcab7ffb57eb1e37c1972cee640323'
        sha = 'feb339390a9b1948ded8fad398804fd5c10dd0f4'
        event.update(commit_id=sha, commit_url=api.API + '/commits/' + sha,
                     created_at='2026-10-20T05:49:55Z')
        commit = self.commit_fixture(pull, event)
        first = 'ea139acfd754f7afa2e24f18b46837dc8b15e4d4'
        commit['parents'][0] = {'sha': first, 'url': api.API + '/commits/' + first}
        with patch.object(api, 'request', side_effect=[[event], commit]):
            self.assertEqual(api.promotion_evidence([pull])[0]['merge_commit_sha'], sha)

    def test_promotion_timestamp_bound_is_not_identity_substitute(self):
        pull, event = self.promotion_fixture()
        for timestamp in ('2026-10-19T22:46:41Z', '2026-10-19T22:47:43Z', None, 'invalid'):
            with self.subTest(timestamp=timestamp), patch.object(api, 'request', return_value=[{
                    **event, 'created_at': timestamp}]) as request:
                with self.assertRaises(ValueError):
                    api.promotion_evidence([pull])
                self.assertEqual(request.call_count, 1)
        commit = self.commit_fixture(pull, event)
        wrong = [copy.deepcopy(commit) for _ in range(6)]
        wrong[0]['sha'] = 'd' * 40
        wrong[1]['url'] = 'https://api.github.com/repos/other/repo/commits/' + event['commit_id']
        wrong[2]['parents'] = commit['parents'][:1]
        wrong[3]['parents'][1] = {'sha': 'd' * 40, 'url': api.API + '/commits/' + 'd' * 40}
        wrong[4]['parents'][1]['url'] = 'https://api.github.com/repos/other/repo/commits/' + 'a' * 40
        wrong[5]['parents'] = list(reversed(commit['parents']))
        for value in wrong:
            with self.subTest(commit=value), patch.object(api, 'request', side_effect=[[event], value]):
                with self.assertRaisesRegex(ValueError, 'does not corroborate'):
                    api.promotion_evidence([pull])

    def test_promotion_rejects_non_numeric_identifier_before_request(self):
        pull, _ = self.promotion_fixture()
        for number in ('../3', True, 0):
            with self.subTest(number=number), patch.object(api, 'request') as request:
                with self.assertRaisesRegex(ValueError, 'Invalid promotion PR number'):
                    api.promotion_evidence([{**pull, 'number': number}])
                request.assert_not_called()

    def request_with_response(self, payload, **options):
        response = io.BytesIO(payload)
        opener = Mock()
        opener.open.return_value = response
        with patch.dict(api.os.environ, {'GITHUB_TOKEN': 'test-token-not-a-credential'}, clear=True), \
                patch.object(api, 'build_opener', return_value=opener) as build:
            result = api.request('/actions/artifacts/123/zip', **options)
        build.assert_called_once()
        self.assertIsInstance(build.call_args.args[0], api.Redirect)
        query = opener.open.call_args.args[0]
        self.assertEqual(opener.open.call_args.kwargs, {'timeout': 120})
        self.assertEqual(query.full_url, api.API + '/actions/artifacts/123/zip')
        self.assertEqual(query.get_header('Accept'), 'application/octet-stream' if options.get('asset') else 'application/vnd.github+json')
        self.assertEqual(query.get_header('X-github-api-version'), '2026-03-10')
        self.assertEqual(query.get_header('Authorization'), 'Bearer test-token-not-a-credential')
        self.assertNotIn('Authorization', query.headers)
        return result, response, query

    def test_artifact_binary_preserves_vendor_accept_and_returns_open_stream(self):
        result, response, query = self.request_with_response(b'PK\x03\x04test-zip', binary=True)
        self.assertIs(result, response)
        self.assertFalse(response.closed)
        self.assertEqual(result.read(), b'PK\x03\x04test-zip')
        self.assertEqual(query.method, 'GET')
        result.close()

    def test_release_asset_uses_octet_stream_without_changing_artifact_contract(self):
        result, response, query = self.request_with_response(b'asset', binary=True, asset=True)
        self.assertEqual(query.get_header('Accept'), 'application/octet-stream')
        self.assertEqual(result.read(), b'asset')
        result.close()

    def test_json_is_decoded_and_response_closed(self):
        result, response, query = self.request_with_response(b'{"id":123,"expired":false}')
        self.assertEqual(result, {'id': 123, 'expired': False})
        self.assertTrue(response.closed)
        self.assertEqual(query.method, 'GET')

    def test_json_body_sets_content_type_without_changing_accept(self):
        result, response, query = self.request_with_response(b'{"id":123}', method='POST', data={'draft': True})
        self.assertEqual(json.loads(query.data), {'draft': True})
        self.assertEqual(query.get_header('Content-type'), 'application/json')
        self.assertEqual(query.method, 'POST')
        self.assertEqual(result, {'id': 123})
        self.assertTrue(response.closed)

    def test_redirect_strips_all_authorization_headers(self):
        for destination in ('https://api.github.com/download',
                            'https://release-assets.githubusercontent.com/file.zip',
                            'https://artifactstore.blob.core.windows.net/file.zip?signature=test'):
            for unredirected in (False, True):
                with self.subTest(destination=destination, unredirected=unredirected):
                    query = Request(api.API + '/actions/artifacts/123/zip',
                                    headers={'Accept': 'application/vnd.github+json'})
                    add = query.add_unredirected_header if unredirected else query.add_header
                    add('Authorization', 'Bearer must-not-follow')
                    redirected = api.Redirect().redirect_request(query, None, 302, 'Found', {}, destination)
                    self.assertEqual(redirected.full_url, destination)
                    self.assertIsNone(redirected.get_header('Authorization'))
                    self.assertFalse(any(name.lower() == 'authorization' for name, _ in redirected.header_items()))
                    self.assertEqual(redirected.get_header('Accept'), 'application/vnd.github+json')

    def test_redirect_rejects_unapproved_origin_and_plaintext(self):
        for destination in ('http://release-assets.githubusercontent.com/file.zip',
                            'https://example.com/file.zip',
                            'https://api.github.com.evil.example/file.zip',
                            'https://blob.core.windows.net.evil.example/file.zip'):
            with self.subTest(destination=destination):
                query = Request(api.API + '/actions/artifacts/123/zip')
                with self.assertRaisesRegex(ValueError, 'Unapproved GitHub download redirect'):
                    api.Redirect().redirect_request(query, None, 302, 'Found', {}, destination)

    def test_initial_unapproved_host_never_opens(self):
        with patch.object(api, 'build_opener') as build:
            with self.assertRaisesRegex(ValueError, 'Unexpected API host'):
                api.request('https://example.com/actions/artifacts/123/zip', binary=True)
            build.assert_not_called()


if __name__ == '__main__':
    unittest.main()
