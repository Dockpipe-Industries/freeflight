# SPDX-License-Identifier: Apache-2.0
import json
import os
from pathlib import Path
import tempfile
import unittest
import zipfile

import jsonschema
from package import create_mcpb_archive, validate_manifest

SCHEMA = Path(__file__).parent / 'schema'


class MCPBContract(unittest.TestCase):
    def test_official_valid_example(self):
        validate_manifest(json.loads((SCHEMA / 'upstream-valid-manifest.json').read_text()))

    def test_official_invalid_example(self):
        with self.assertRaises(jsonschema.ValidationError):
            validate_manifest(json.loads((SCHEMA / 'upstream-invalid-manifest.json').read_text()))

    def test_missing_server_rejected(self):
        manifest = json.loads((SCHEMA / 'upstream-valid-manifest.json').read_text())
        del manifest['server']
        with self.assertRaises(jsonschema.ValidationError):
            validate_manifest(manifest)

    def test_zip_file_set_hash_bytes_and_permissions(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            bundle = root / 'bundle'
            bundle.mkdir()
            (bundle / 'manifest.json').write_bytes((SCHEMA / 'upstream-valid-manifest.json').read_bytes())
            (bundle / 'binary').write_bytes(b'\x00\x01native\xff')
            (bundle / 'binary').chmod(0o755)
            (bundle / 'lib.d.ts').write_text('declare const answer: number;')
            archive = root / 'server.mcpb'
            create_mcpb_archive(bundle, archive)
            with zipfile.ZipFile(archive) as source:
                self.assertEqual(set(source.namelist()), {'manifest.json', 'binary', 'lib.d.ts'})
                for file in bundle.iterdir():
                    self.assertEqual(source.read(file.name), file.read_bytes())
                if os.name != 'nt':
                    self.assertEqual((source.getinfo('binary').external_attr >> 16) & 0o777, 0o755)
            with self.assertRaises(FileExistsError):
                create_mcpb_archive(bundle, archive)

    def test_symlink_rejected_before_archive_creation(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            bundle = root / 'bundle'
            bundle.mkdir()
            (bundle / 'manifest.json').write_bytes((SCHEMA / 'upstream-valid-manifest.json').read_bytes())
            (root / 'outside').write_text('outside')
            (bundle / 'link').symlink_to(root / 'outside')
            with self.assertRaisesRegex(RuntimeError, 'Nonregular'):
                create_mcpb_archive(bundle, root / 'server.mcpb')
            self.assertFalse((root / 'server.mcpb').exists())


if __name__ == '__main__':
    unittest.main()
