# SPDX-License-Identifier: Apache-2.0
import json
import hashlib
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
import zipfile

import jsonschema
from package import REPO, SCHEMA_SHA256, create_mcpb_archive, validate_manifest

SCHEMA = Path(__file__).parent / 'schema'


class MCPBContract(unittest.TestCase):
    def test_autocrlf_checkout_preserves_pinned_schema(self):
        # A real isolated index/checkout reproduces Git for Windows conversion;
        # never change the contributor's repository config, index or worktree.
        relative = Path('workflows/package.native/assets/schema/mcpb-manifest-v0.3.schema.json')
        original = (REPO / relative).read_bytes()
        self.assertEqual(hashlib.sha256(original).hexdigest(), SCHEMA_SHA256)
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            environment = dict(os.environ, GIT_CONFIG_NOSYSTEM='1', GIT_CONFIG_GLOBAL=os.devnull)

            def git(*arguments):
                subprocess.run(['git', '-c', 'core.autocrlf=true', '-c', 'core.eol=crlf',
                                '-c', 'core.safecrlf=false', '-c', 'core.attributesFile=' + os.devnull,
                                '-C', str(root), *arguments], check=True, env=environment,
                               capture_output=True, timeout=30)

            git('init', '--quiet', '--template=')
            schema = root / relative
            schema.parent.mkdir(parents=True)
            schema.write_bytes(original)
            git('add', '--', relative.as_posix())
            schema.unlink()
            git('checkout-index', '--', relative.as_posix())
            converted = schema.read_bytes()
            self.assertIn(b'\r\n', converted)
            self.assertNotEqual(hashlib.sha256(converted).hexdigest(), SCHEMA_SHA256)

            # The policy must preserve the original bytes, not normalize them
            # inside the checksum verifier. Check general source LF policy too.
            attributes = root / '.gitattributes'
            attributes.write_bytes((REPO / '.gitattributes').read_bytes())
            schema.write_bytes(original)
            source = root / 'source.txt'
            source.write_bytes(b'first\nsecond\n')
            git('add', '--', '.gitattributes', relative.as_posix(), 'source.txt')
            for path in (schema, source, attributes):
                path.unlink()
            git('checkout-index', '--all')
            self.assertEqual(schema.read_bytes(), original)
            self.assertEqual(hashlib.sha256(schema.read_bytes()).hexdigest(), SCHEMA_SHA256)
            self.assertEqual(source.read_bytes(), b'first\nsecond\n')

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
