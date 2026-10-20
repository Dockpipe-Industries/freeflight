"""Qualify startup trust through the real packaged MCP endpoint and bundled Roslyn.

The fixture is authored here, restored explicitly by the test, and isolated beneath
bin/.local. No user repository or active MCP configuration is opened or modified.
Invoked by DockPipe package.native after assembling the complete native bundle.
"""
import json
import os
import pathlib
import queue
import shutil
import subprocess
import sys
import tempfile
import threading

repo = pathlib.Path(__file__).resolve().parents[1]
binary = pathlib.Path(sys.argv[1]).resolve()
dotnet = shutil.which("dotnet")
assert dotnet, "Trusted bundled qualification requires an installed SDK"
meta = {"io.modelcontextprotocol/protocolVersion": "2026-07-28",
        "io.modelcontextprotocol/clientCapabilities": {}}


class Client:
    def __init__(self, config, env=None):
        self.stderr = tempfile.TemporaryFile(mode="w+t")
        self.process = subprocess.Popen([str(binary), "--config", str(config)],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=self.stderr,
            text=True, encoding="utf-8", env=env)
        self.replies = queue.Queue()
        self.sequence = 0
        self.reader = threading.Thread(target=self.read, daemon=True)
        self.reader.start()

    def read(self):
        for line in self.process.stdout:
            self.replies.put(line)

    def call(self, name, arguments=None):
        self.sequence += 1
        self.process.stdin.write(json.dumps({"jsonrpc": "2.0", "id": self.sequence,
            "method": "tools/call", "params": {"_meta": meta, "name": name,
            "arguments": arguments or {}}}) + "\n")
        self.process.stdin.flush()
        value = json.loads(self.replies.get(timeout=90))
        assert value["id"] == self.sequence and "error" not in value, value
        return value["result"]

    def good(self, name, arguments=None):
        value = self.call(name, arguments)
        assert not value.get("isError"), value
        return value["structuredContent"]

    def close(self):
        self.process.stdin.close()
        try:
            self.process.wait(timeout=15)
            assert self.process.returncode == 0
        finally:
            if self.process.poll() is None:
                self.process.kill()
                self.process.wait(timeout=15)
            self.reader.join(timeout=5)
            self.process.stdout.close()
            self.stderr.close()


with tempfile.TemporaryDirectory(prefix="trusted-bundle-", dir=repo / "bin/.local") as directory:
    base = pathlib.Path(directory).resolve()
    root = base / "workspace"
    sibling = base / "untrusted-sibling"
    sibling.mkdir()
    (sibling / "Safe.cs").write_text("public class SafeSibling {}\n")
    (root / "source/Lib").mkdir(parents=True)
    (root / "source/App").mkdir()
    props = "<TargetFramework>net8.0</TargetFramework><GenerateAssemblyInfo>false</GenerateAssemblyInfo><GenerateTargetFrameworkAttribute>false</GenerateTargetFrameworkAttribute><EnableNETAnalyzers>false</EnableNETAnalyzers>"
    library = root / "source/Lib/Lib.csproj"
    library.write_text(f'<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup>{props}<DefineConstants>PROJECT_SETTING</DefineConstants></PropertyGroup></Project>')
    app = root / "source/App/App.csproj"
    app.write_text(f'<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup>{props}</PropertyGroup><ItemGroup><ProjectReference Include="../Lib/Lib.csproj" /></ItemGroup></Project>')
    widget = root / "source/Lib/Widget.cs"
    widget.write_text("namespace Library;\n#if PROJECT_SETTING\npublic class Widget { public int Value => 42; }\n#endif\n")
    consumer = root / "source/App/Consumer.cs"
    consumer.write_text("using Library;\nclass Consumer { public int Read(Widget value) => value.Value; }\n")
    outlines = {
        "OutlineOne.cs": "namespace Shared.Area;\npublic partial class Merged { }\n",
        "OutlineTwo.cs": "// second file\n\nnamespace Shared.Area;\npublic partial class Merged { public int Here => 1; }\n",
        "OutlineThree.cs": "namespace Shared.Area { public class Third { } }\n\nnamespace Shared.Area { public enum Choice { One } }\n",
    }
    for name, text in outlines.items():
        (root / "source/Lib" / name).write_text(text)
    sln = root / "source/Architecture.sln"
    sln.write_text('Microsoft Visual Studio Solution File, Format Version 12.00\n'
        'Project("{FAE04EC0-301F-11D3-BF4B-00C04F79EFBC}") = "App", "App/App.csproj", "{F99CC167-3E5A-4E4E-8C0E-B43FD3F69B41}"\nEndProject\nGlobal\nEndGlobal\n')
    subprocess.run([dotnet, "restore", str(app), "--ignore-failed-sources"], check=True, timeout=60)
    assets = root / "source/App/obj/project.assets.json"
    pristine_assets = assets.read_text()
    data = json.loads(pristine_assets)
    warning_message = "Package Example 1.0.1 has a known high severity vulnerability, https://example.invalid/advisory"
    data["logs"] = [{"code": "NU1903", "level": "Warning", "message": warning_message,
                     "libraryId": "Example", "targetGraphs": ["net8.0"]}]
    assets.write_text(json.dumps(data))
    # No internal engines, worker executables or separate runtime paths appear.
    config = base / "operator.json"
    config.write_text(json.dumps({"roots": [str(root), str(sibling)],
        "trustedRoots": [str(root)], "csharp": {"project": "source/Architecture.sln"}}))
    client = Client(config)
    selection = {"root": str(root), "language": "csharp"}
    def query(operation, **arguments):
        return client.good("semantic.query", {**selection, "operation": operation,
            "arguments": arguments})["items"]
    try:
        sibling_selection = {"root": str(sibling), "language": "csharp"}
        sibling_caps = client.good("engine.capabilities", sibling_selection)
        assert sibling_caps["analysis"]["mode"] == "safe-source", sibling_caps
        assert client.call("workspace.open", {"root": str(sibling), "mode": "trusted-msbuild"})["isError"]
        assert client.good("engine.capabilities", sibling_selection)["analysis"]["mode"] == "safe-source"
        capabilities = client.good("engine.capabilities", selection)
        analysis = capabilities["analysis"]
        assert capabilities["loadWarnings"] == analysis["loadWarnings"], capabilities
        assert capabilities["degradedFidelity"] == analysis["degradedFidelity"], capabilities
        assert capabilities["selectedProject"] == analysis["selectedProject"], capabilities
        assert analysis["mode"] == "trusted-msbuild", analysis
        assert analysis["selectedProject"].replace("\\", "/") == "source/Architecture.sln", analysis
        assert analysis["degradedFidelity"] is True, analysis
        assert len(analysis["loadWarnings"]) == 1, analysis
        warning = analysis["loadWarnings"][0]
        assert warning["code"] == "NU1903" and warning["message"] == warning_message, warning
        assert warning["reportedKind"] == "Failure" and warning["severity"] == "Warning", warning
        assert query("diagnostics", file=str(consumer)) == []
        definition = query("definition", file=str(consumer), line=1, character=57)
        assert len(definition) == 1 and pathlib.Path(definition[0]["file"]).resolve() == widget, definition
        assert definition[0]["range"]["start"] == {"line": 2, "character": 33}, definition
        references = query("references", file=str(widget), line=2, character=34)
        assert len(references) == 1 and pathlib.Path(references[0]["file"]).resolve() == consumer, references
        assert references[0]["range"]["start"] == {"line": 1, "character": 56}, references
        symbols = query("symbols", file=str(widget))
        assert any(symbol["name"] == "Widget" for symbol in symbols), symbols
        expected_namespaces = {
            "OutlineOne.cs": [{"line": 0, "character": 17}],
            "OutlineTwo.cs": [{"line": 2, "character": 17}],
            "OutlineThree.cs": [{"line": 0, "character": 17}, {"line": 2, "character": 17}],
        }
        for name, starts in expected_namespaces.items():
            requested_file = root / "source/Lib" / name
            outline = query("symbols", file=str(requested_file))
            assert all(pathlib.Path(item["location"]["file"]).resolve() == requested_file for item in outline), outline
            namespaces = [item for item in outline if item["kind"] == "Namespace"]
            assert [item["name"] for item in namespaces] == ["Area"] * len(starts), outline
            assert [item["location"]["range"]["start"] for item in namespaces] == starts, outline
            if name in ("OutlineOne.cs", "OutlineTwo.cs"):
                partial = next(item for item in outline if item["name"] == "Merged")
                assert partial["location"]["range"]["start"] == {
                    "line": 1 if name == "OutlineOne.cs" else 3, "character": 21}, partial
        listed = client.good("workspace.list")["workspaces"][0]
        assert listed["engines"]["csharp"]["analysis"] == analysis, listed
        # Reload is explicit and does not require restarting the server or changing
        # its immutable trust policy. It rereads assets and project selection.
        assets.write_text(pristine_assets)
        client.good("workspace.open", {"root": str(root), "reload": True})
        assert client.good("engine.capabilities", selection)["analysis"]["loadWarnings"] == []
        assert client.call("workspace.open", {"root": str(root), "project": "source/App/App.csproj"})["isError"]
        client.good("workspace.open", {"root": str(root), "project": "source/App/App.csproj", "reload": True})
        assert client.good("engine.capabilities", selection)["analysis"]["selectedProject"].replace("\\", "/") == "source/App/App.csproj"
        assert client.call("workspace.open", {"root": str(root), "project": "../outside.csproj", "reload": True})["isError"]
        assert client.call("workspace.open", {"root": str(base), "reload": True})["isError"]
        assert client.call("semantic.query", {**selection, "operation": "symbols", "arguments": {"file": str(widget), "mode": "trusted-msbuild"}})["isError"]
    finally:
        client.close()
    # A separate server with no trust setting remains safe-source; tool arguments
    # cannot opt it in even though its fixture has a restorable valid project.
    config.write_text(json.dumps({"roots": [str(root)]}))
    client = Client(config)
    try:
        assert client.good("engine.capabilities", selection)["analysis"]["mode"] == "safe-source"
        assert client.call("workspace.open", {"root": str(root), "mode": "trusted-msbuild"})["isError"]
        assert client.call("semantic.query", {**selection, "operation": "symbols", "arguments": {"file": str(widget), "trustedMsbuild": True}})["isError"]
        assert client.good("engine.capabilities", selection)["analysis"]["mode"] == "safe-source"
    finally:
        client.close()
    # The normal operator configuration authorizes source folders once. Each
    # contains independent repositories, discovered lazily from requested files.
    source_a, source_b = base / "Source A", base / "Source B"
    source_a.mkdir(); source_b.mkdir()
    architecture = source_a / "Architecture"
    shutil.copytree(root, architecture)
    (architecture / ".git").mkdir()
    subprocess.run([dotnet, "restore", str(architecture / "source/App/App.csproj"),
        "--ignore-failed-sources"], check=True, timeout=60)

    def make_repository(parent, name):
        target = parent / name
        (target / ".git").mkdir(parents=True)
        project = target / "App.csproj"
        project.write_text(f'<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup>{props}</PropertyGroup></Project>')
        document = target / "Sample.cs"
        document.write_text("namespace Library; public class Widget { public int Value = 7; public int Read() => Value; }\n")
        subprocess.run([dotnet, "restore", str(project), "--ignore-failed-sources"],
            check=True, timeout=60)
        return target, document

    other, other_file = make_repository(source_b, "Other")
    config.write_text(json.dumps({"trustedRoots": [str(source_a), str(source_b)]}))
    client = Client(config)

    def routed(source, language, operation, **arguments):
        return client.good("semantic.query", {"root": str(source), "language": language,
            "operation": operation, "arguments": arguments})["items"]

    try:
        initial = client.good("workspace.list")
        assert set(initial["allowedRoots"]) == {str(source_a), str(source_b)}, initial
        assert all(not workspace.get("engines") for workspace in initial["workspaces"]), initial
        routed_consumer = architecture / "source/App/Consumer.cs"
        routed_widget = architecture / "source/Lib/Widget.cs"
        definition = routed(source_a, "csharp", "definition", file=str(routed_consumer), line=1, character=57)
        assert len(definition) == 1 and pathlib.Path(definition[0]["file"]).resolve() == routed_widget, definition
        assert definition[0]["range"]["start"] == {"line": 2, "character": 33}, definition
        assert routed(source_a, "csharp", "diagnostics", file=str(routed_consumer)) == []
        text = other_file.read_text()
        definition = routed(source_b, "csharp", "definition", file=str(other_file), line=0,
            character=text.rindex("Value") + 1)
        assert len(definition) == 1 and pathlib.Path(definition[0]["file"]).resolve() == other_file, definition
        assert definition[0]["range"]["start"] == {"line": 0, "character": text.index("Value")}, definition
        assert routed(source_b, "csharp", "diagnostics", file=str(other_file)) == []
        other_file.write_text(text.replace("Value = 7", 'Value = "wrong"'))
        diagnostics = routed(source_b, "csharp", "diagnostics", file=str(other_file))
        assert len(diagnostics) == 1 and diagnostics[0]["code"] == "CS0029", diagnostics
        assert pathlib.Path(diagnostics[0]["location"]["file"]).resolve() == other_file, diagnostics
        other_file.write_text(text)
        assert routed(source_b, "csharp", "diagnostics", file=str(other_file)) == []
        # A later-created project works without Git metadata, rewriting config or
        # restarting. Its nearest project directory provides the scoped workspace.
        later, later_file = make_repository(source_a, "Created Later")
        (later / ".git").rmdir()
        assert routed(source_a, "csharp", "diagnostics", file=str(later_file)) == []
        client.good("workspace.close", {"root": str(later)})
        assert client.call("semantic.query", {"root": str(source_a), "language": "csharp",
            "operation": "symbols", "arguments": {"file": str(other_file)}})["isError"]
        assert client.call("semantic.query", {"root": str(source_a), "language": "csharp",
            "operation": "symbols", "arguments": {"file": str(widget)}})["isError"]
        # Workspace-level selection is a tool operation, never a config edit.
        client.good("workspace.open", {"root": str(architecture)})
        capabilities = client.good("engine.capabilities", {"root": str(architecture), "language": "csharp"})
        assert capabilities["analysis"]["selectedProject"].replace("\\", "/") == "source/Architecture.sln", capabilities
        duplicate = architecture / "source/Alternative.sln"
        duplicate.write_text((architecture / "source/Architecture.sln").read_text())
        client.good("workspace.open", {"root": str(architecture), "reload": True})
        ambiguous = client.call("engine.capabilities", {"root": str(architecture), "language": "csharp"})
        assert ambiguous["isError"], ambiguous
        error = ambiguous["structuredContent"]["error"]
        assert error["code"] == "project_selection_required", error
        assert pathlib.Path(error["workspaceRoot"]).resolve() == architecture, error
        assert {item["candidate"].replace("\\", "/") for item in error["diagnostics"]} == {
            "source/Architecture.sln", "source/Alternative.sln"}, error
        client.good("workspace.open", {"root": str(architecture), "project": "source/Architecture.sln", "reload": True})
        assert routed(architecture, "csharp", "diagnostics", file=str(routed_consumer)) == []
        client.good("workspace.close", {"root": str(architecture)})
        client.good("workspace.close", {"root": str(other)})
        # The same source-root configuration routes both official TS/JS services.
        for language, extension in (("typescript", "ts"), ("javascript", "js")):
            web = source_b / language
            (web / ".git").mkdir(parents=True)
            (web / "tsconfig.json").write_text(json.dumps({"compilerOptions": {
                "strict": True, "allowJs": True, "checkJs": True}, "include": ["*." + extension]}))
            document = web / ("sample." + extension)
            document.write_text("export const answer = 42;\nexport const result = answer;\n")
            definition = routed(source_b, language, "definition", file=str(document), line=1, character=23)
            assert len(definition) == 1 and pathlib.Path(definition[0]["file"]).resolve() == document, definition
            assert definition[0]["range"]["start"] == {"line": 0, "character": 13}, definition
            assert routed(source_b, language, "diagnostics", file=str(document)) == []
            client.good("workspace.close", {"root": str(web)})
        # One physical document in two projects has two compilation contexts.
        # Returning an arbitrary first project would silently give wrong answers.
        linked = source_a / "Linked Contexts"
        (linked / ".git").mkdir(parents=True)
        shared = linked / "Shared.cs"
        shared.write_text("public class Shared { public int Value => 42; }\n")
        solution_projects = []
        for number, name in enumerate(("First", "Second"), start=1):
            directory = linked / name
            directory.mkdir()
            project = directory / (name + ".csproj")
            project.write_text(f'<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup>{props}</PropertyGroup>'
                '<ItemGroup><Compile Include="../Shared.cs" Link="Shared.cs" /></ItemGroup></Project>')
            subprocess.run([dotnet, "restore", str(project), "--ignore-failed-sources"],
                check=True, timeout=60)
            solution_projects.append(
                f'Project("{{FAE04EC0-301F-11D3-BF4B-00C04F79EFBC}}") = "{name}", '
                f'"{name}/{name}.csproj", "{{00000000-0000-0000-0000-{number:012d}}}"\nEndProject\n')
        (linked / "Contexts.sln").write_text("Microsoft Visual Studio Solution File, Format Version 12.00\n"
            + "".join(solution_projects) + "Global\nEndGlobal\n")
        client.good("workspace.open", {"root": str(linked)})
        ambiguous = client.call("engine.capabilities", {"root": str(linked), "language": "csharp"})
        assert ambiguous["isError"], ambiguous
        error = ambiguous["structuredContent"]["error"]
        assert error["code"] == "project_selection_required", error
        assert pathlib.Path(error["workspaceRoot"]).resolve() == linked, error
        assert {item["candidate"].replace("\\", "/") for item in error["diagnostics"]} == {
            "First/First.csproj", "Second/Second.csproj"}, error
        client.good("workspace.open", {"root": str(linked), "project": "First/First.csproj", "reload": True})
        assert routed(linked, "csharp", "diagnostics", file=str(shared)) == []
        client.good("workspace.close", {"root": str(linked)})
        if sys.platform != "win32":
            escape = source_a / "escape.cs"
            escape.symlink_to(widget)
            assert client.call("semantic.query", {"root": str(source_a), "language": "csharp",
                "operation": "symbols", "arguments": {"file": str(escape)}})["isError"]
        print("trustedRoots-only packaged routing: two source roots, nested solution, isolated same-name symbols, new repository, ambiguity/selection, TS/JS and boundaries passed")
    finally:
        client.close()
    # This Mac has only a task-local SDK. A separate test process can therefore
    # verify runtime-only behavior without altering any installed SDK or session.
    standard_sdk_roots = [pathlib.Path(path) for path in (
        "/usr/local/share/dotnet", "/opt/homebrew/share/dotnet", "/usr/share/dotnet",
        "/Library/Frameworks/dotnet")]
    if sys.platform == "darwin" and not any(path.exists() for path in standard_sdk_roots):
        empty_sdk = base / "empty-sdk"
        empty_sdk.mkdir()
        config.write_text(json.dumps({"roots": [str(root)], "trustedRoots": [str(root)],
            "csharp": {"project": "source/Architecture.sln"}}))
        client = Client(config, env=dict(os.environ, PATH=str(empty_sdk),
            DOTNET_ROOT=str(empty_sdk), DOTNET_MULTILEVEL_LOOKUP="0"))
        try:
            failure = client.call("engine.capabilities", selection)
            assert failure["isError"], failure
            error = failure["structuredContent"]["error"]
            assert error["code"] == "sdk_not_found", error
            assert "SDK" in error["remediation"] and "restore" not in error["remediation"].lower(), error
            print("Packaged Mac runtime-only missing SDK produces sdk_not_found without restore advice")
        finally:
            client.close()
    else:
        print("Missing-SDK isolation not run: host may discover global SDKs; not counted as a passing SDK-absence test")
print("Packaged MCP -> bundled Roslyn net8.0 project: startup trust, warnings, nested solution selection, exact symbols/definition/references, reload and root/query boundaries passed")
