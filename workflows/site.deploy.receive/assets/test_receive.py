"""Offline receiver boundary and rollback tests; never contact hosts or Docker."""
import hashlib
import io
import json
from pathlib import Path
import tarfile
import tempfile
import unittest
from unittest.mock import patch
import receive


class ReceiverTests(unittest.TestCase):
    def setUp(self):
        preflight = patch.object(receive, "host_preflight")
        preflight.start()
        self.addCleanup(preflight.stop)

    def fixture(self, root):
        candidate = root / "candidate"
        candidate.mkdir()
        image = candidate / "image.tar.gz"
        image.write_bytes(b"qualified image")
        report = candidate / "vulnerabilities.json"
        report.write_text('{"Results":[{"Vulnerabilities":[]}]}')
        audit = {"status": "passed", "imageArchiveSha256": receive.digest(image),
                 "ignoreUnfixed": False, "severity": ["HIGH", "CRITICAL"],
                 "reportSha256": receive.digest(report)}
        (candidate / "audit.json").write_text(json.dumps(audit))
        metadata = {"schema": 1, "environment": "staging", "hostname": receive.HOSTS["staging"],
                    "prerelease": True, "sourceCommit": "a" * 40, "sourceTree": "b" * 40,
                    "promotedCommit": "c" * 40, "imageId": "sha256:" + "d" * 64,
                    "imageSha256": receive.digest(image), "siteReleaseSha256": "e" * 64,
                    "version": "0.1.0-preview.rc2", "releaseTag": "v0.1.0-preview.rc2.staging.42." + "a" * 12,
                    "assets": {"index.html": "f" * 64}}
        metadata["releaseUrl"] = "https://github.com/Dockpipe-Industries/freeflight/releases/tag/" + metadata["releaseTag"]
        (candidate / "deployment.json").write_text(json.dumps(metadata))
        config = {"environment": "staging", "root": str(root.resolve()), "loopbackPort": 18080}
        return candidate, metadata, config

    def runner(self, calls, image, existing=""):
        def run(*args):
            calls.append(args)
            if args[1:3] == ("ps", "-aq"):
                return existing
            if args[1:3] == ("image", "inspect"):
                return json.dumps([{"Id": image, "Architecture": "amd64", "Os": "linux"}])
            return ""
        return run

    def test_success_is_scoped_and_requires_both_probes(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            candidate, metadata, config = self.fixture(root)
            calls, probes = [], []
            result = receive.activate(config, candidate, self.runner(calls, metadata["imageId"]),
                                      lambda m, url: probes.append(url))
            self.assertTrue(result["verifiedHttps"])
            self.assertEqual(probes, ["http://127.0.0.1:18080", "https://freeflight.staging.dockpipe.com"])
            self.assertEqual(json.loads((root / "current.json").read_text())["imageId"], metadata["imageId"])
            compose = (root / "compose.yaml").read_text()
            self.assertIn("127.0.0.1:18080:8080", compose)
            self.assertIn("cap_drop: [ALL]", compose)
            self.assertTrue(any(command[-5:] == ("up", "-d", "--no-build", "--pull", "never") for command in calls))

    def test_failed_first_activation_removes_only_own_project(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            candidate, metadata, config = self.fixture(root)
            calls = []
            with patch.object(receive.time, "sleep"):
                with self.assertRaisesRegex(ValueError, "unhealthy"):
                    receive.activate(config, candidate, self.runner(calls, metadata["imageId"]),
                                     lambda m, url: (_ for _ in ()).throw(ValueError("unhealthy")))
            self.assertFalse((root / "current.json").exists())
            self.assertFalse((root / "compose.yaml").exists())
            self.assertEqual(calls[-1][-3:], ("down", "--timeout", "10"))
            self.assertIn("freeflight-staging", calls[-1])

    def test_failed_upgrade_restores_previous_image_and_receipt(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            candidate, metadata, config = self.fixture(root)
            old = {**metadata, "imageId": "sha256:" + "1" * 64, "loopbackPort": 18080}
            (root / "current.json").write_text(json.dumps(old))
            (root / "compose.yaml").write_text(receive.compose_text("staging", 18080, old["imageId"]))
            calls = []
            def probe(m, url):
                if m["imageId"] != old["imageId"]:
                    raise ValueError("new image unhealthy")
            with patch.object(receive.time, "sleep"):
                with self.assertRaisesRegex(ValueError, "new image unhealthy"):
                    receive.activate(config, candidate, self.runner(calls, metadata["imageId"], "owned"), probe)
            self.assertIn(old["imageId"], (root / "compose.yaml").read_text())
            self.assertEqual(json.loads((root / "current.json").read_text()), old)
            self.assertEqual(sum(command[-5:] == ("up", "-d", "--no-build", "--pull", "never") for command in calls), 2)

    def test_existing_project_without_receipt_cannot_be_adopted(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            candidate, metadata, config = self.fixture(root)
            calls = []
            with self.assertRaisesRegex(ValueError, "no activation receipt"):
                receive.activate(config, candidate, self.runner(calls, metadata["imageId"], "foreign"))
            self.assertEqual(len(calls), 1)

    def test_tamper_wrong_environment_and_production_prerelease_rejected(self):
        for change in ("image", "environment", "production"):
            with self.subTest(change=change), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary).resolve()
                candidate, metadata, config = self.fixture(root)
                if change == "image":
                    (candidate / "image.tar.gz").write_bytes(b"tampered")
                elif change == "environment":
                    config["environment"] = "production"
                else:
                    metadata.update(environment="production", hostname=receive.HOSTS["production"], prerelease=False)
                    (candidate / "deployment.json").write_text(json.dumps(metadata))
                    config["environment"] = "production"
                calls = []
                with self.assertRaises(ValueError):
                    receive.activate(config, candidate, self.runner(calls, metadata["imageId"]))
                self.assertEqual(calls, [])

    def test_archive_traversal_and_links_rejected_before_extraction(self):
        for bad in ("../escape", "symlink"):
            with self.subTest(bad=bad), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                archive = root / "delivery.tar"
                with tarfile.open(archive, "w") as output:
                    for name in receive.FILES:
                        entry = tarfile.TarInfo("../escape" if bad == "../escape" and name == "image.tar.gz" else name)
                        if bad == "symlink" and name == "image.tar.gz":
                            entry.type = tarfile.SYMTYPE
                            entry.linkname = "/etc/passwd"
                        else:
                            entry.size = 1
                        output.addfile(entry, io.BytesIO(b"x"))
                destination = root / "out"
                destination.mkdir()
                with self.assertRaises(ValueError):
                    receive.extract(archive, destination)
                self.assertEqual(list(destination.iterdir()), [])


if __name__ == "__main__":
    unittest.main()
