# SPDX-License-Identifier: Apache-2.0
"""Offline GitHub request and redirect regressions; never use real credentials."""
import importlib.util
import io
import json
from pathlib import Path
import unittest
from unittest.mock import Mock, patch
from urllib.request import Request

ROOT = Path(__file__).resolve().parents[3]
spec = importlib.util.spec_from_file_location('release_github_api', ROOT / '.github/release/api.py')
api = importlib.util.module_from_spec(spec)
spec.loader.exec_module(api)


class GitHubApiTests(unittest.TestCase):
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
        self.assertEqual(query.get_header('Accept'), 'application/vnd.github+json')
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
