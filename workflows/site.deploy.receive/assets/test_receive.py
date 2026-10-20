"""Offline static delivery boundary, isolation and rollback tests."""
import base64
import gzip
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import receive


def fixture(environment="staging", version="0.1.0-preview.rc2"):
    source = "a" * 40
    files = {name: b"qualified " + name.encode() for name in receive.PUBLIC_FILES if name != "release.json"}
    if environment == "production":
        files["sitemap.xml"] = b"sitemap"
    assets = {name: receive.digest(data) for name, data in files.items()}
    receipt = {"sourceCommit": source, "sourceTree": "b" * 40, "sourceDirty": False,
               "environment": environment, "hostname": receive.HOSTS[environment], "assets": assets}
    files["release.json"] = json.dumps(receipt).encode()
    tag = "v" + version
    if environment == "staging":
        tag += (".staging." if "-" in version else "-staging.") + "42." + source[:12]
    metadata = {**receipt, "schema": 2, "promotedCommit": "c" * 40,
                "prerelease": environment == "staging", "version": version, "releaseTag": tag,
                "releaseUrl": "https://github.com/Dockpipe-Industries/freeflight/releases/tag/" + tag,
                "siteReleaseSha256": receive.digest(files["release.json"])}
    return {"format": 2, "product": "freeflight", "mode": "site", "deployment": metadata,
            "files": {name: {"sha256": receive.digest(data), "content": base64.b64encode(data).decode()}
                      for name, data in files.items()}}


def encode(bundle):
    data = gzip.compress(json.dumps(bundle).encode())
    return data, receive.digest(data)


class StaticDeliveryTests(unittest.TestCase):
    def setUp(self):
        if not hasattr(os, "geteuid"):
            uid = patch.object(receive.os, "geteuid", return_value=0, create=True)
            uid.start()
            self.addCleanup(uid.stop)
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name).resolve()
        (self.root / "releases").mkdir()
        self.config = {"environment": "staging", "root": str(self.root), "loopbackPort": 18080}
        sleeper = patch.object(receive.time, "sleep")
        sleeper.start()
        self.addCleanup(sleeper.stop)

    def activate(self, bundle=None, health=lambda m, base: None):
        data, digest = encode(bundle or fixture())
        return receive.activate(self.config, data, digest, health)

    @unittest.skipIf(os.name == "nt", "POSIX host receiver; filesystem activation runs on Linux/macOS")
    def test_success_serves_exact_bytes_without_executing_commands(self):
        probes = []
        result = self.activate(health=lambda m, base: probes.append(base))
        self.assertTrue(result["verifiedLocal"])
        self.assertNotIn("verifiedHttps", result)
        self.assertEqual(probes, ["http://127.0.0.1:18080"])
        self.assertEqual((self.root / "current/index.html").read_bytes(), b"qualified index.html")
        self.assertFalse((self.root / "deploy.lock").exists())

    @unittest.skipIf(os.name == "nt", "POSIX host receiver; filesystem activation runs on Linux/macOS")
    def test_first_failure_removes_only_new_current_link(self):
        marker = self.root / "unrelated"
        marker.write_text("preserve")
        with self.assertRaisesRegex(ValueError, "unhealthy"):
            self.activate(health=lambda m, base: (_ for _ in ()).throw(ValueError("unhealthy")))
        self.assertFalse((self.root / "current").exists())
        self.assertEqual(marker.read_text(), "preserve")
        self.assertEqual(len(list((self.root / "releases").iterdir())), 1)
        self.assertFalse((self.root / "deploy.lock").exists())

    @unittest.skipIf(os.name == "nt", "POSIX host receiver; filesystem activation runs on Linux/macOS")
    def test_failed_upgrade_restores_and_probes_previous_release(self):
        self.activate()
        previous = (self.root / "current").resolve()
        calls = []
        def health(metadata, base):
            calls.append((self.root / "current").resolve())
            if calls[-1] != previous:
                raise ValueError("candidate unhealthy")
        with self.assertRaises(ValueError):
            self.activate(health=health)
        self.assertEqual((self.root / "current").resolve(), previous)
        self.assertEqual(calls[-1], previous)
        self.assertFalse((self.root / "deploy.lock").exists())

    @unittest.skipIf(os.name == "nt", "POSIX host receiver; filesystem activation runs on Linux/macOS")
    def test_failed_rollback_retains_reconciliation_lock(self):
        self.activate()
        with self.assertRaises(ValueError):
            self.activate(health=lambda m, base: (_ for _ in ()).throw(ValueError("all unhealthy")))
        self.assertTrue((self.root / "deploy.lock").exists())
        with self.assertRaises(FileExistsError):
            self.activate()

    @unittest.skipIf(os.name == "nt", "POSIX host receiver; filesystem activation runs on Linux/macOS")
    def test_existing_nonlink_and_foreign_link_are_not_adopted(self):
        for kind in ("file", "foreign"):
            with self.subTest(kind=kind), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary).resolve()
                (root / "releases").mkdir()
                if kind == "file":
                    (root / "current").write_text("owned elsewhere")
                else:
                    (root / "current").symlink_to(self.root)
                data, digest = encode(fixture())
                with self.assertRaises(ValueError):
                    receive.activate({**self.config, "root": str(root)}, data, digest)

    def test_wrong_product_scope_and_extra_or_traversal_files_rejected(self):
        mutations = [lambda b: b.update(product="dockpipe"),
                     lambda b: b["deployment"].update(environment="production"),
                     lambda b: b["files"].update({"../escape": b["files"]["index.html"]}),
                     lambda b: b["files"].update({"unexpected.js": b["files"]["index.html"]})]
        for mutate in mutations:
            bundle = fixture()
            mutate(bundle)
            with self.assertRaises(ValueError):
                self.activate(bundle)
        self.assertEqual(list((self.root / "releases").iterdir()), [])

    def test_tampered_bytes_and_receipts_rejected(self):
        for mutate in [lambda b: b["files"]["index.html"].update(content="eA=="),
                       lambda b: b["deployment"].update(siteReleaseSha256="0" * 64),
                       lambda b: b["deployment"].update(assets={})]:
            bundle = fixture()
            mutate(bundle)
            with self.assertRaises(ValueError):
                self.activate(bundle)

    def test_production_requires_stable_and_matching_scope(self):
        data, digest = encode(fixture("production", "1.0.0"))
        receive.decode(data, digest, "production")
        with self.assertRaises(ValueError):
            receive.decode(data, digest, "staging")
        data, digest = encode(fixture("production", "1.0.0-preview"))
        with self.assertRaises(ValueError):
            receive.decode(data, digest, "production")

    def test_numeric_version_staging_tag_is_accepted(self):
        data, digest = encode(fixture(version="1.0.0"))
        receive.decode(data, digest, "staging")

    def test_duplicate_json_and_decompression_limit_rejected(self):
        data = gzip.compress(b'{"product":"freeflight","product":"dockpipe"}')
        with self.assertRaisesRegex(ValueError, "Duplicate"):
            receive.decode(data, receive.digest(data), "staging")
        data, digest = encode(fixture())
        with patch.object(receive, "MAX_DOCUMENT", 20):
            with self.assertRaisesRegex(ValueError, "Expanded"):
                receive.decode(data, digest, "staging")

    def test_root_execution_is_rejected_before_configuration_read(self):
        with patch.object(receive.os, "geteuid", return_value=0, create=True):
            with self.assertRaisesRegex(ValueError, "unprivileged"):
                receive.receive("/nonexistent")


if __name__ == "__main__":
    unittest.main()
