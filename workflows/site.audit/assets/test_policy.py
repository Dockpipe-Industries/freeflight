"""Verify fail-closed image binding and scanner failure handling without Docker."""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import scan


class Policy(unittest.TestCase):
    def test_changed_archive_rejected_before_scanner(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            image = root / 'bin/.local/site-container/freeflight-site-image.tar.gz'
            image.parent.mkdir(parents=True)
            image.write_bytes(b'changed')
            (image.parent / 'verification.json').write_text(json.dumps({'artifacts': {image.name: '0' * 64}}))
            with patch.object(scan, 'ROOT', root), patch.object(scan.urllib.request, 'urlopen') as download:
                with self.assertRaisesRegex(RuntimeError, 'differs'):
                    scan.main()
                download.assert_not_called()
            self.assertFalse((root / 'bin/.local/site-audit/verification.json').exists())

    def test_old_pass_removed_on_failed_input(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            receipt = root / 'bin/.local/site-audit/verification.json'
            receipt.parent.mkdir(parents=True)
            receipt.write_text('{"status":"passed"}')
            with patch.object(scan, 'ROOT', root):
                with self.assertRaises(FileNotFoundError):
                    scan.main()
            self.assertFalse(receipt.exists())

    def test_streamed_digest(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / 'image'
            content = b'image' * 300000
            path.write_bytes(content)
            self.assertEqual(scan.sha(path), hashlib.sha256(content).hexdigest())


if __name__ == '__main__':
    unittest.main()
