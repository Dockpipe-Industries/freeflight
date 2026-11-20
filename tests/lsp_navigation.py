"""Exact fixture and real-source checks for optional LSP navigation engines."""
import json
import os
from pathlib import Path
import shutil
import tempfile
import unittest

from navigation_client import GENERATED, REPO, server

WORKER = REPO / "workers/lsp/worker.mjs"
PIPE_SERVER = os.environ.get("FREEFLIGHT_PIPELANG_SERVER")
PIPE_COMPILER = os.environ.get("FREEFLIGHT_PIPELANG_COMPILER")
PYRIGHT = os.environ.get("FREEFLIGHT_PYRIGHT")
CLANGD = os.environ.get("FREEFLIGHT_CLANGD")
DOCKPIPE = os.environ.get("FREEFLIGHT_GO_DOCKPIPE")
FREEFLIGHT_DATABASE = os.environ.get("FREEFLIGHT_CPP_TEST_DATABASE")


def locations(*items):
    return {"items": list(items), "truncated": False}


def command(language, *paths):
    node = shutil.which("node")
    assert node, "Node must be available on PATH"
    return [node, str(WORKER), language, *map(str, paths)]


def query(client, root, language, operation, **arguments):
    return client.ok("semantic.query", language=language, root=str(root),
                     operation=operation, arguments=arguments)


def position(root, file, line, character):
    return {"file": str(root / file), "line": line, "character": character,
            "format": "citations"}


def anchor(root, file, marker, symbol):
    with (root / file).open(encoding="utf-8") as source:
        for line, text in enumerate(source):
            if marker in text:
                character = len(text[:text.index(symbol)].encode("utf-16-le")) // 2
                return line, character
    raise AssertionError(f"Missing source anchor in {file}")


def capability(client, root, language, coverage):
    result = client.ok("engine.capabilities", root=str(root), language=language)
    assert result["operations"] == ["workspaceSymbols", "definition", "references"], result
    assert result["positionEncoding"] == "utf-16", result
    assert result["analysis"]["coverage"] == coverage, result


class LanguageNavigation(unittest.TestCase):
    def setUp(self):
        GENERATED.mkdir(parents=True, exist_ok=True)
        temp = tempfile.TemporaryDirectory(prefix="lsp-fixture-", dir=GENERATED)
        self.addCleanup(temp.cleanup)
        self.directory = Path(temp.name).resolve()
        self.root = self.directory / "workspace"
        self.root.mkdir()

    def test_untrusted_root_and_unavailable_backend(self):
        labels = ("cpp", "python", "pipelang")
        for language in labels:
            with self.subTest(language=language):
                argv = command(language, self.directory / "missing")
                with server(self.directory, [self.root], [], argv, language) as client:
                    result = client.tool("engine.capabilities", root=str(self.root), language=language)
                    self.assertIn("lsp_workspace_not_trusted", json.dumps(result))
                with server(self.directory, [self.root], [self.root], argv, language) as client:
                    result = client.tool("engine.capabilities", root=str(self.root), language=language)
                    self.assertIn("lsp_backend_unavailable", json.dumps(result))

    @unittest.skipUnless(PYRIGHT, "Set FREEFLIGHT_PYRIGHT to the pinned Pyright server module")
    def test_python_cross_module_identity(self):
        language = "python"
        library = self.root / "lib.py"
        library.write_text("def target(value: int) -> int:\n    return value\n", encoding="utf-8")
        application = self.root / "app.py"
        application.write_text("import lib\n\nvalue = lib.target(42)\n", encoding="utf-8")
        outside = self.directory / "outside.py"
        outside.write_text("def target():\n    pass\n", encoding="utf-8")

        with server(self.directory, [self.root], [self.root], command(language, PYRIGHT), language) as client:
            capability(client, self.root, language, "workspace-static-imports")
            lookup = query(client, self.root, language, "workspaceSymbols", query="target", format="citations")
            self.assertEqual(lookup, locations({"name": "target", "location": "lib.py:1"}))
            reference = position(self.root, "app.py", 2, 13)
            self.assertEqual(query(client, self.root, language, "definition", **reference),
                             locations("lib.py:1"))
            declaration = position(self.root, "lib.py", 0, 5)
            self.assertEqual(query(client, self.root, language, "references", **declaration),
                             locations("app.py:3"))
            with_declaration = query(client, self.root, language, "references",
                                     includeDeclaration=True, **declaration)
            self.assertCountEqual(with_declaration["items"], ["lib.py:1", "app.py:3"])
            application.write_text("import lib\n\nvalue = 42\n", encoding="utf-8")
            self.assertEqual(query(client, self.root, language, "references", **declaration), locations())
            rejected = client.tool("semantic.query", root=str(self.root), language=language,
                                   operation="definition", arguments={"file": str(outside), "line": 0, "character": 6})
            self.assertTrue(rejected["isError"], rejected)

    @unittest.skipUnless(CLANGD, "Set FREEFLIGHT_CLANGD to the pinned clangd executable")
    def test_cpp_cross_translation_unit_index(self):
        language = "cpp"
        (self.root / "api.hpp").write_text("int target(int value);\n", encoding="utf-8")
        (self.root / "lib.cpp").write_text('#include "api.hpp"\nint target(int value) { return value; }\n',
                                           encoding="utf-8")
        (self.root / "app.cpp").write_text('#include "api.hpp"\nint main() { return target(42); }\n',
                                           encoding="utf-8")
        database = self.directory / "compile_commands.json"
        compiler = "/compiler-is-not-launched/c++"
        database.write_text(json.dumps([
            {"directory": str(self.root), "file": str(file),
             "arguments": [compiler, "-std=c++17", "-c", str(file)]}
            for file in sorted(self.root.glob("*.cpp"))
        ]), encoding="utf-8")
        argv = command(language, CLANGD, database, self.directory / "cache")
        with server(self.directory, [self.root], [self.root], argv, language) as client:
            capability(client, self.root, language, "compilation-database")
            lookup = query(client, self.root, language, "workspaceSymbols", query="target", format="citations")
            self.assertEqual(lookup, locations({"name": "target", "location": "lib.cpp:2"}))
            self.assertEqual(query(client, self.root, language, "definition",
                                   **position(self.root, "app.cpp", 1, 21)), locations("lib.cpp:2"))
            self.assertEqual(query(client, self.root, language, "references",
                                   **position(self.root, "lib.cpp", 1, 5)), locations("app.cpp:2"))
            denied = client.tool("semantic.query", root=str(self.root), language=language, operation="references",
                                 arguments={**position(self.root, "lib.cpp", 1, 5), "scope": ".."})
            self.assertIn("lsp_invalid_query", json.dumps(denied))
            self.assertEqual(query(client, self.root, language, "references",
                                   **position(self.root, "lib.cpp", 1, 5)), locations("app.cpp:2"))
        self.assertFalse((self.root / ".cache").exists())

    @unittest.skipUnless(PIPE_SERVER and PIPE_COMPILER, "Set both PipeLang tool paths")
    def test_pipelang_import_closure(self):
        language = "pipelang"
        library = self.root / "Lib.pipe"
        entry = self.root / "Entry.pipe"
        library.write_text("module Example.Library;\npublic model Class Value {\n"
                           "    public int Read() { return 3; }\n}\n", encoding="utf-8")
        entry.write_text("module Example.App;\nimport Example.Library;\npublic model Class Entry {\n"
                         "    public int Run() { var value = new Value(); return value.Read(); }\n}\n",
                         encoding="utf-8")
        argv = command(language, PIPE_SERVER, PIPE_COMPILER, entry, self.root)
        with server(self.directory, [self.root], [self.root], argv, language) as client:
            capability(client, self.root, language, "explicit-import-closure")
            lookup = query(client, self.root, language, "workspaceSymbols", query="Read", format="citations")
            self.assertEqual(lookup, locations({"name": "Read", "location": "Lib.pipe:3"}))
            character = entry.read_text(encoding="utf-8").splitlines()[3].index("Read")
            call = position(self.root, "Entry.pipe", 3, character)
            self.assertEqual(query(client, self.root, language, "definition", **call), locations("Lib.pipe:3"))
            self.assertEqual(query(client, self.root, language, "references", **call,
                                   includeDeclaration=True), locations("Entry.pipe:4", "Lib.pipe:3"))

    @unittest.skipUnless(PIPE_SERVER and PIPE_COMPILER and DOCKPIPE, "Set both PipeLang paths and the DockPipe root")
    def test_pipelang_dockpipe_workflow(self):
        language = "pipelang"
        root = Path(DOCKPIPE).resolve()
        entry = "workflows/test/sdk-pipelang/assets/harness/src/Entry.pipe"
        definition = "src/lib/sdkassets/pipelang/src/Client.pipe"
        argv = command(language, PIPE_SERVER, PIPE_COMPILER, root / entry,
                       (root / entry).parent, (root / definition).parent)
        with server(self.directory, [root], [root], argv, language) as client:
            capability(client, root, language, "explicit-import-closure")
            target = position(root, entry, 12, 32)
            self.assertEqual(query(client, root, language, "definition", **target), locations(f"{definition}:42"))
            known = [f"{entry}:{line}" for line in (13, 29, 37, 46, 130, 134)]
            self.assertEqual(query(client, root, language, "references", **target), locations(*known))

    @unittest.skipUnless(CLANGD and FREEFLIGHT_DATABASE, "Set the clangd path and FreeFlight compile database")
    def test_cpp_freeflight_core(self):
        language = "cpp"
        caller = "src/main.cpp"
        target = "src/server.cpp"
        argv = command(language, CLANGD, FREEFLIGHT_DATABASE, self.directory / "cache")
        line, character = anchor(REPO, caller, "server.call(", "call(")
        declaration_line, declaration_character = anchor(REPO, target, "Server::call(", "call(")
        with server(self.directory, [REPO], [REPO], argv, language) as client:
            self.assertEqual(query(client, REPO, language, "definition",
                                   **position(REPO, caller, line, character)),
                             locations(f"{target}:{declaration_line + 1}"))
            self.assertEqual(query(client, REPO, language, "references", scope=caller,
                                   **position(REPO, target, declaration_line, declaration_character)),
                             locations(f"{caller}:{line + 1}"))

    @unittest.skipUnless(PYRIGHT, "Set the Pyright language-server path")
    def test_python_freeflight_packaging(self):
        language = "python"
        root = REPO / "workflows/package.native/assets"
        caller = "test_pe_imports.py"
        target = "pe_imports.py"
        line, character = anchor(root, caller, "from pe_imports import", "verify_core_runtime")
        declaration_line, declaration_character = anchor(root, target, "def verify_core_runtime", "verify_core_runtime")
        argv = command(language, PYRIGHT)
        with server(self.directory, [root], [root], argv, language) as client:
            self.assertEqual(query(client, root, language, "definition",
                                   **position(root, caller, line, character)),
                             locations(f"{target}:{declaration_line + 1}"))
            found = query(client, root, language, "references", scope=caller,
                          **position(root, target, declaration_line, declaration_character))
            self.assertIn(f"{caller}:{line + 1}", found["items"])
            self.assertFalse(found["truncated"])


if __name__ == "__main__":
    unittest.main()
