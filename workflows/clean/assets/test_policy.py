import importlib.util
from pathlib import Path
import shutil
import tempfile
import unittest


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


cleanup = load(Path(__file__).with_name("clean.py"), "cleanup")
start = load(Path(__file__).parents[2] / "dev/assets/start.py", "start")


class PolicyTests(unittest.TestCase):
    def test_selection_preview_apply_and_preservation(self):
        with tempfile.TemporaryDirectory() as temp:
            repo = Path(temp)
            selected = repo / "bin/.local/build"
            selected.mkdir(parents=True)
            (selected / "output").write_text("generated")
            receipt = repo / "bin/.local/packages/receipt"
            receipt.parent.mkdir()
            receipt.write_text("keep")
            self.assertFalse(cleanup.clean(repo, "core")["applied"])
            self.assertTrue(selected.exists())
            for invalid in ("", "all", "../packages", "site", "packages"):
                with self.assertRaises(ValueError):
                    cleanup.clean(repo, invalid, True)
            if shutil.rmtree.avoids_symlink_attacks:
                self.assertTrue(cleanup.clean(repo, "core", True)["applied"])
                self.assertFalse(selected.exists())
            else:
                with self.assertRaises(ValueError):
                    cleanup.clean(repo, "core", True)
            self.assertEqual(receipt.read_text(), "keep")

    def test_links_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            repo = Path(temp)
            selected = repo / "bin/.local/build"
            selected.mkdir(parents=True)
            outside = repo / "developer-work"
            outside.mkdir()
            try:
                (selected / "escape").symlink_to(outside, target_is_directory=True)
            except OSError as error:
                self.skipTest("symlink fixture unavailable: " + str(error))
            with self.assertRaises(ValueError):
                cleanup.clean(repo, "core")
            (selected / "escape").unlink()
            selected.rmdir()
            selected.symlink_to(outside, target_is_directory=True)
            with self.assertRaises(ValueError):
                cleanup.clean(repo, "core", True)
            self.assertTrue(outside.exists())

    def test_start_requires_explicit_configuration(self):
        for value in ("", "relative.json", "/nonexistent/freeflight.json"):
            with self.assertRaises(ValueError):
                start.command(value)


if __name__ == "__main__":
    unittest.main()
