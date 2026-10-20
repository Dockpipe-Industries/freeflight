"""Rejection tests for promotion and environment boundaries; no remote operations."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import prepare


class PreparationPolicy(unittest.TestCase):
    def test_changed_container_archive_is_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            archive = root / "image.tar.gz"
            archive.write_bytes(b"changed")
            receipt = root / "receipt.json"
            receipt.write_text(json.dumps({
                "sourceCommit": "a" * 40, "sourceTree": "b" * 40, "sourceDirty": False,
                "environment": "staging", "hostname": "freeflight-staging.dockpipe.com",
                "imageId": "sha256:" + "e" * 64, "artifacts": {archive.name: "0" * 64}}))
            with patch.object(prepare, "git", side_effect=["b" * 40, "c" * 40, "a" * 40, "b" * 40]):
                with self.assertRaisesRegex(ValueError, "archive mismatch"):
                    prepare.validate({"environment": "staging", "sourceCommit": "a" * 40,
                                      "loopbackPort": 18080, "containerReceipt": str(receipt),
                                      "containerArchive": str(archive), "containerArchiveSha256": "0" * 64})

    def test_unpromoted_source_is_rejected(self):
        with patch.object(prepare, "git", side_effect=["b" * 40, "c" * 40, "d" * 40]):
            with self.assertRaisesRegex(ValueError, "not promoted"):
                prepare.validate({"environment": "staging", "sourceCommit": "a" * 40})

    def test_prerelease_cannot_prepare_production(self):
        with patch.object(prepare, "git", side_effect=[
                "b" * 40, "c" * 40, "a" * 40, "b" * 40, "0.1.0-preview.rc2"]):
            with self.assertRaisesRegex(ValueError, "stable VERSION"):
                prepare.validate({"environment": "production", "sourceCommit": "a" * 40})

    def test_wrong_environment_archive_is_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            receipt = Path(temporary) / "receipt.json"
            receipt.write_text(json.dumps({
                "sourceCommit": "a" * 40, "sourceTree": "b" * 40, "sourceDirty": False,
                "environment": "production", "hostname": "freeflight.dockpipe.com"}))
            with patch.object(prepare, "git", side_effect=["b" * 40, "c" * 40, "a" * 40, "b" * 40]):
                with self.assertRaisesRegex(ValueError, "environment/hostname"):
                    prepare.validate({"environment": "staging", "sourceCommit": "a" * 40,
                                      "loopbackPort": 18080, "containerReceipt": str(receipt)})

    def test_symlink_artifact_is_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary) / "target"
            target.write_bytes(b"artifact")
            link = Path(temporary) / "link"
            link.symlink_to(target)
            with self.assertRaisesRegex(ValueError, "regular artifact"):
                prepare.digest(link)


if __name__ == "__main__":
    unittest.main()
