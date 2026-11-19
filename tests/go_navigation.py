"""Black-box fixture and optional DockPipe qualification through FreeFlight MCP."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import tempfile
import time
import unittest

from navigation_client import GENERATED, REPO, server


def engine(cache):
    paths = [shutil.which("node"), str(REPO / "workers/go/worker.mjs")]
    for name in ("GOPLS", "TOOLCHAIN", "MODCACHE"):
        variable = f"FREEFLIGHT_GO_{name}"
        path = os.environ.get(variable)
        assert path and Path(path).is_absolute(), f"Set {variable} to an absolute path"
        paths.append(path)
    assert paths[0], "Node must be available on PATH"
    return [*paths, str(cache)]


def location(file, line, character):
    return {"file": file, "line": line, "character": character}


def column(text, symbol):
    return len(text[:text.index(symbol)].encode("utf-16-le")) // 2


class GoNavigation(unittest.TestCase):
    def setUp(self):
        GENERATED.mkdir(parents=True, exist_ok=True)
        directory = tempfile.TemporaryDirectory(prefix="go-test-", dir=GENERATED)
        self.addCleanup(directory.cleanup)
        self.directory = Path(directory.name).resolve()
        self.root = self.directory / "workspace José"
        self.root.mkdir()
        (self.root / "lib").mkdir()
        (self.root / "go.mod").write_text("module example.org/fixture\n\ngo 1.23.0\n", encoding="utf-8")
        (self.root / "lib/value.go").write_text("package lib\n\nfunc Target() int { return 42 }\n", encoding="utf-8")
        self.consumer = self.root / "consumer.go"
        self.use = 'func Use() int { _ = "😀"; return aliased.Target() }'
        self.consumer.write_text('package fixture\n\nimport aliased "example.org/fixture/lib"\n\n'
                                 'func Target() int { return 0 }\n' + self.use + '\n'
                                 'func Other() int { return aliased.Target() + Target() }\n',
                                 encoding="utf-8")
        self.cache = self.directory / "cache"

    def test_semantics_and_reload(self):
        with server(self.directory, [self.root], [self.root], engine(self.cache)) as client:
            root = str(self.root)
            discovered = client.ok("workspace.discover")["workspaces"]
            self.assertEqual(discovered[0]["languages"], ["go"])
            self.assertEqual(discovered[0]["projects"], [str(self.root / "go.mod")])
            caps = client.ok("engine.capabilities", root=root, language="go")
            self.assertEqual(caps["operations"], ["workspaceSymbols", "definition", "references"])
            self.assertEqual(caps["positionEncoding"], "utf-16")

            declaration = location("lib/value.go", 2, 5)
            symbols = client.query(self.root, "workspaceSymbols", query="Target")
            self.assertEqual(len(symbols["items"]), 2)
            self.assertIn({**declaration, "name": "Target"}, symbols["items"])
            self.assertFalse(symbols["truncated"])
            limited = client.query(self.root, "workspaceSymbols", query="Target", limit=1)
            self.assertEqual(len(limited["items"]), 1)
            self.assertTrue(limited["truncated"])

            point = {"file": str(self.consumer), "line": 5, "character": column(self.use, "Target")}
            self.assertEqual(client.query(self.root, "definition", **point),
                             {"items": [declaration], "truncated": False})
            refs = client.query(self.root, "references", **point)
            self.assertCountEqual(refs["items"], [
                location("consumer.go", 5, column(self.use, "Target")),
                location("consumer.go", 6, column("func Other() int { return aliased.Target()", "Target")),
            ])
            self.assertFalse(refs["truncated"])
            with_declaration = client.query(self.root, "references", includeDeclaration=True, **point)
            self.assertCountEqual(with_declaration["items"], [*refs["items"], declaration])
            self.assertTrue(client.query(self.root, "references", limit=1, **point)["truncated"])

            self.consumer.write_text(self.consumer.read_text(encoding="utf-8").replace(
                "aliased.Target() + Target()", "Target()"), encoding="utf-8")
            # The watcher is asynchronous. Keep the worker open while checking convergence.
            deadline = time.monotonic() + 5
            while True:
                refreshed = client.query(self.root, "references", **point)
                if len(refreshed["items"]) == 1 or time.monotonic() >= deadline:
                    break
                time.sleep(0.05)
            self.assertEqual(refreshed["items"], [location("consumer.go", 5, point["character"])])
            client.ok("workspace.close", root=root)
            self.assertTrue(client.tool("engine.capabilities", root=root, language="go")["isError"])
            client.ok("workspace.open", root=root)
            self.assertEqual(client.query(self.root, "references", **point), refreshed)

    def test_trust_backend_and_index_failures(self):
        cases = [
            ([], engine(self.cache), "go_workspace_not_trusted"),
            ([self.root], None, "Go engine is not configured"),
        ]
        missing_backend = engine(self.cache)
        missing_backend[2] = str(self.directory / "missing-gopls")
        cases.append(([self.root], missing_backend, "go_backend_unavailable"))
        for trusted, command, expected in cases:
            with self.subTest(expected=expected), server(self.directory, [self.root], trusted, command) as client:
                result = client.tool("engine.capabilities", root=str(self.root), language="go")
                self.assertTrue(result["isError"], result)
                self.assertIn(expected, json.dumps(result))

        (self.root / "go.mod").write_text("module example.org/fixture\n\ngo 99.0.0\n", encoding="utf-8")
        with server(self.directory, [self.root], [self.root], engine(self.cache)) as client:
            result = client.tool("engine.capabilities", root=str(self.root), language="go")
            self.assertTrue(result["isError"], result)
            self.assertIn("go_index_failed", json.dumps(result))

    def test_external_locations_and_files_are_excluded(self):
        self.consumer.write_text('package fixture\nimport "fmt"\nfunc Use() { fmt.Println("hello") }\n',
                                 encoding="utf-8")
        outside = self.directory / "outside.go"
        outside.write_text("package outside\n", encoding="utf-8")
        with server(self.directory, [self.root], [self.root], engine(self.cache)) as client:
            point = {"file": str(self.consumer), "line": 2, "character": 17}
            self.assertEqual(client.query(self.root, "definition", **point), {"items": [], "truncated": False})
            escaped = client.tool("semantic.query", root=str(self.root), language="go", operation="definition",
                                  arguments={**point, "file": str(outside)})
            self.assertTrue(escaped["isError"], escaped)
            try:
                link = self.root / "link.go"
                link.symlink_to(outside)
            except OSError:
                return
            escaped = client.tool("semantic.query", root=str(self.root), language="go", operation="definition",
                                  arguments={**point, "file": str(link)})
            self.assertTrue(escaped["isError"], escaped)


@unittest.skipUnless(os.environ.get("FREEFLIGHT_GO_DOCKPIPE"), "Set FREEFLIGHT_GO_DOCKPIPE to qualify the real checkout")
class DockPipeNavigation(unittest.TestCase):
    def test_exact_cross_package_results(self):
        root = Path(os.environ["FREEFLIGHT_GO_DOCKPIPE"]).resolve()
        app = "src/lib/application/project_build_cmd.go"
        durable = "src/lib/infrastructure/durable_state.go"
        removal = "src/lib/infrastructure/removal_safety.go"
        fixtures = ["go.mod", "go.sum", "go.work", "go.work.sum", app, durable, removal]
        hashes = {file: hashlib.sha256((root / file).read_bytes()).digest()
                  for file in fixtures if (root / file).is_file()}
        with tempfile.TemporaryDirectory(prefix="go-dockpipe-", dir=GENERATED) as directory:
            work = Path(directory).resolve()
            with server(work, [root], [root], engine(GENERATED / "go/cache")) as client:
                caps = client.ok("engine.capabilities", root=str(root), language="go")
                self.assertEqual(caps["analysis"]["mode"], "gopls-offline")
                symbols = client.query(root, "workspaceSymbols", query="DurableStateRoot")
                self.assertIn({**location(durable, 54, 5), "name": "DurableStateRoot"}, symbols["items"])
                exact = client.query(root, "workspaceSymbols", query="DurableStateRoot",
                                     exact=True, format="citations")
                self.assertEqual(exact, {"items": [{"name": "DurableStateRoot", "location": f"{durable}:55"}],
                                         "truncated": False})
                for line, character, declaration in [(279, 36, location(durable, 54, 5)),
                                                      (133, 26, location(removal, 19, 5))]:
                    definition = client.query(root, "definition", file=str(root / app), line=line, character=character)
                    self.assertEqual(definition, {"items": [declaration], "truncated": False})
                for file, line, expected in [
                    (durable, 54, {(app, 279), (app, 364),
                                   ("src/lib/application/project_build_cmd_test.go", 198),
                                   ("src/lib/application/project_build_cmd_test.go", 260)}),
                    (removal, 19, {(app, 133), (app, 154)}),
                ]:
                    result = client.query(root, "references", file=str(root / file), line=line, character=5, limit=100)
                    self.assertFalse(result["truncated"], result)
                    self.assertEqual({(item["file"], item["line"]) for item in result["items"]
                                      if item["file"].startswith("src/lib/application/")}, expected)
                    scoped = client.query(root, "references", file=str(root / file), line=line,
                                          character=5, scope="src/lib/application", format="citations")
                    self.assertFalse(scoped["truncated"], scoped)
                    self.assertCountEqual(scoped["items"], [f"{file}:{line + 1}" for file, line in expected])
        after = {file: hashlib.sha256((root / file).read_bytes()).digest()
                 for file in fixtures if (root / file).is_file()}
        self.assertEqual(after, hashes)


if __name__ == "__main__":
    unittest.main()
