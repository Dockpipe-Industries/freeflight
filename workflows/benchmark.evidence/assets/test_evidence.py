import gzip
import json
from pathlib import Path
import tempfile
import unittest

from evidence import capture, verify


class EvidenceTests(unittest.TestCase):
    def test_lossless_dedup_pruning_and_relocation(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d); source = root / 'source'; source.mkdir()
            raw = b'{"samples":[{"phase":"failed","ms":4.5}]}\n'
            (source / 'samples.json').write_bytes(raw)
            (source / 'duplicate.json').write_bytes(raw)
            fixture = source / 'fixture-5845'; fixture.mkdir(); (fixture / 'input.json').write_text('{}')
            (source / 'binary.dll').write_bytes(b'ignored')
            (source / 'log.stderr').write_text('not measurement JSON')
            git = root / 'git'; external = root / 'external'
            result = capture(source, external, git)
            self.assertEqual((result['files'], result['gitObjects']), (2, 1))
            blob = next((git / 'objects').iterdir())
            self.assertEqual(gzip.decompress(blob.read_bytes()), raw)
            relocated = root / 'relocated'; git.rename(relocated)
            self.assertEqual(verify(relocated)['verifiedObjects'], 1)
            with self.assertRaises(ValueError): capture(source, external, git)

    def test_overflow_explicit_and_not_required_for_git_verification(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d); source = root / 'source'; source.mkdir()
            (source / 'samples.json').write_text('[1,2,3]')
            result = capture(source, root / 'external', root / 'git', max_blob=1)
            self.assertEqual((result['gitObjects'], result['externalObjects']), (0, 1))
            self.assertEqual(verify(root / 'git')['verifiedObjects'], 0)
            self.assertEqual(verify(root / 'git', root / 'external')['verifiedObjects'], 1)

    def test_corruption_path_escape_and_size_budget_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d); source = root / 'source'; source.mkdir()
            (source / 'samples.json').write_text('[1,2,3]')
            capture(source, root / 'external', root / 'git')
            manifest = root / 'git/manifest.json'; original = manifest.read_text()
            value = json.loads(original); value['entries'][0]['path'] = '../escape.json'
            manifest.write_text(json.dumps(value))
            with self.assertRaises(ValueError): verify(root / 'git')
            manifest.write_text(original)
            value = json.loads(original); value['limits']['setBytes'] = 1
            manifest.write_text(json.dumps(value))
            with self.assertRaises(ValueError): verify(root / 'git')
            manifest.write_text(original)
            next((root / 'git/objects').iterdir()).write_bytes(b'corrupted')
            with self.assertRaises(ValueError): verify(root / 'git')

    def test_symlink_sources_and_private_keys_not_archived(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d); source = root / 'source'; source.mkdir()
            (root / 'secret.json').write_text('private')
            (source / 'link.json').symlink_to(root / 'secret.json')
            self.assertEqual(capture(source, root / 'external', root / 'git')['files'], 0)
            (source / 'secret.json').write_text('-----BEGIN ' + 'PRIVATE KEY-----')
            with self.assertRaises(ValueError): capture(source, root / 'external2', root / 'git2')


if __name__ == '__main__':
    unittest.main()
