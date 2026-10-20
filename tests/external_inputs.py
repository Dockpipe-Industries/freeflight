"""Real packaged MCP regression for evaluated, read-only external compiler inputs.

All projects/sources are authored in a disposable fixture. Restoring their pinned
Test SDK dependencies is explicit test setup, never an operation performed by the
server. --expect-rejection records the pre-fix failure with one external Compile
item whose exact path was independently obtained from MSBuild evaluation.
"""
import argparse
import hashlib
import json
import os
import pathlib
import platform
import queue
import shutil
import subprocess
import tempfile
import threading
import time
import tarfile
import urllib.request
from xml.sax.saxutils import escape

parser = argparse.ArgumentParser()
parser.add_argument("binary", type=pathlib.Path, nargs="?", default=os.environ.get("FREEFLIGHT_TEST_BINARY"))
parser.add_argument("--baseline-release", action="store_true")
parser.add_argument("--expect-rejection", action="store_true", default=os.environ.get("FREEFLIGHT_EXPECT_EXTERNAL_REJECTION") == "1")
args = parser.parse_args()
repo = pathlib.Path(__file__).resolve().parents[1]
baseline_directory = None
if args.baseline_release:
    assert args.binary is None and platform.system() == "Linux" and platform.machine() in ("x86_64", "AMD64"), "Baseline release requires Linux x64 and no binary argument"
    args.expect_rejection = True
    baseline_directory = tempfile.TemporaryDirectory(prefix="external-baseline-", dir=repo / "bin/.local")
    baseline_root = pathlib.Path(baseline_directory.name).resolve()
    archive = baseline_root / "preview.tar.gz"
    url = "https://github.com/Dockpipe-Industries/freeflight/releases/download/v0.1.0-preview.20261020.trusted.1997d38/freeflight-linux-x64-5f01db9a3b8edc85.tar.gz"
    digest = hashlib.sha256()
    size = 0
    with urllib.request.urlopen(url, timeout=120) as response, archive.open("xb") as output:
        while block := response.read(1024 * 1024):
            size += len(block)
            assert size <= 128 * 1024 * 1024, "Baseline archive exceeds bound"
            digest.update(block)
            output.write(block)
    assert digest.hexdigest() == "ab4d7f2312b56ed54870f688384f86b2dde470a42889f3820657c4384aa21048", "Baseline checksum mismatch"
    with tarfile.open(archive, "r:gz") as package:
        members = package.getmembers()
        assert len(members) <= 10000 and sum(member.size for member in members) <= 1024 ** 3
        seen = set()
        for member in members:
            path = pathlib.PurePosixPath(member.name)
            assert not path.is_absolute() and ".." not in path.parts and path.parts[0] == "freeflight-linux-x64", member.name
            assert member.isdir() or member.isfile(), "Baseline archive contains nonregular entry"
            assert path not in seen, "Baseline archive contains duplicate entry"
            seen.add(path)
        for member in members:
            destination = baseline_root / member.name
            if member.isdir():
                destination.mkdir(parents=True, exist_ok=True)
            else:
                destination.parent.mkdir(parents=True, exist_ok=True)
                with package.extractfile(member) as source_stream, destination.open("xb") as output:
                    shutil.copyfileobj(source_stream, output)
                destination.chmod(member.mode & 0o777)
    binary = baseline_root / "freeflight-linux-x64/bin/freeflight"
else:
    assert args.binary is not None, "Supply the packaged binary or --baseline-release"
    binary = args.binary.resolve()
records = []
dotnet = shutil.which("dotnet")
assert dotnet, "External-input qualification requires a provisioned .NET SDK"
setup_env = dict(os.environ)
# Do not make /tmp aliases into compiler input paths on macOS. The production
# policy rejects symlink/reparse components, including parent components.
if setup_env.get("NUGET_PACKAGES"):
    setup_env["NUGET_PACKAGES"] = str(pathlib.Path(setup_env["NUGET_PACKAGES"]).resolve())
meta = {"io.modelcontextprotocol/protocolVersion": "2026-07-28",
        "io.modelcontextprotocol/clientCapabilities": {}}


class Client:
    def __init__(self, config):
        self.errors = tempfile.TemporaryFile(mode="w+t", encoding="utf-8")
        self.process = subprocess.Popen([str(binary), "--config", str(config)], cwd=config.parent,
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=self.errors,
            text=True, encoding="utf-8")
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
        reply = json.loads(self.replies.get(timeout=120))
        assert reply.get("id") == self.sequence and "error" not in reply, reply
        return reply["result"]

    def good(self, name, arguments=None):
        result = self.call(name, arguments)
        assert not result.get("isError"), result
        return result["structuredContent"]

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
            self.errors.close()


def run(*command, cwd=None):
    return subprocess.run([str(item) for item in command], env=setup_env, cwd=cwd,
        capture_output=True, text=True, encoding="utf-8", check=True, timeout=180).stdout


def semantic(client, root, operation, **arguments):
    return client.call("semantic.query", {"root": str(root), "language": "csharp",
        "operation": operation, "arguments": arguments})


def good_query(client, root, operation, **arguments):
    result = semantic(client, root, operation, **arguments)
    assert not result.get("isError"), result
    return result["structuredContent"]["items"]


properties = ("<TargetFramework>net8.0</TargetFramework><GenerateAssemblyInfo>false</GenerateAssemblyInfo>"
    "<GenerateTargetFrameworkAttribute>false</GenerateTargetFrameworkAttribute>"
    "<EnableNETAnalyzers>false</EnableNETAnalyzers><NuGetAudit>false</NuGetAudit>")
with tempfile.TemporaryDirectory(prefix="external-inputs-", dir=repo / "bin/.local") as temporary:
    base = pathlib.Path(temporary).resolve()
    if args.baseline_release:
        # The pinned old binary cannot read the newer SDK's binary-log format.
        # Preserve its qualified toolchain; the corrected bundle still uses RC2.
        (base / "global.json").write_text(json.dumps({"sdk": {
            "version": "10.0.402", "rollForward": "disable", "allowPrerelease": False}}), encoding="utf-8")
        assert run(dotnet, "--version", cwd=base).strip() == "10.0.402"
    source = base / "Source"
    source.mkdir()
    config = base / "freeflight.json"
    for sdk in ("16.0.1", "17.8.0"):
        root = source / ("Tests-" + sdk)
        (root / ".git").mkdir(parents=True)
        (root / "source/Lib").mkdir(parents=True)
        (root / "source/App").mkdir()
        library = root / "source/Lib/Lib.csproj"
        library.write_text(f'<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup>{properties}</PropertyGroup></Project>', encoding="utf-8")
        widget = root / "source/Lib/Widget.cs"
        widget_text = "namespace Library; public class Widget { public int Value => 42; }\n"
        widget.write_text(widget_text, encoding="utf-8")
        (root / "source/Control").mkdir()
        control_project = root / "source/Control/Control.csproj"
        control_project.write_text(f'<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup>{properties}</PropertyGroup>'
            '<ItemGroup><ProjectReference Include="../Lib/Lib.csproj" /></ItemGroup></Project>', encoding="utf-8")
        control_file = root / "source/Control/Control.cs"
        control_file.write_text("using Library; public class Control { public int Read(Widget value) => value.Value; }\n", encoding="utf-8")
        app = root / "source/App/App.csproj"
        app_text = (f'<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup>{properties}</PropertyGroup><ItemGroup>'
            '<ProjectReference Include="../Lib/Lib.csproj" />'
            f'<PackageReference Include="Microsoft.NET.Test.Sdk" Version="{sdk}" />'
            '</ItemGroup></Project>')
        app.write_text(app_text, encoding="utf-8")
        consumer = root / "source/App/Consumer.cs"
        consumer_text = ("using Library; public class Consumer { public int Read(Widget value) => value.Value; "
            "public System.Type Generated => typeof(AutoGeneratedProgram); }\n")
        consumer.write_text(consumer_text, encoding="utf-8")
        solution = root / "source/Architecture.sln"
        solution.write_text('Microsoft Visual Studio Solution File, Format Version 12.00\n'
            'Project("{FAE04EC0-301F-11D3-BF4B-00C04F79EFBC}") = "App", "App/App.csproj", "{F99CC167-3E5A-4E4E-8C0E-B43FD3F69B41}"\nEndProject\nGlobal\nEndGlobal\n', encoding="utf-8")
        run(dotnet, "restore", app, "--ignore-failed-sources", cwd=root)
        run(dotnet, "restore", control_project, "--ignore-failed-sources", cwd=root)
        evaluated = json.loads(run(dotnet, "msbuild", app, "-target:GenerateProgramFile",
            "-getItem:Compile", "-property:DesignTimeBuild=true", "-verbosity:quiet", cwd=root))
        external = [pathlib.Path(item["FullPath"]) for item in evaluated["Items"]["Compile"]
            if not pathlib.Path(item["FullPath"]).is_relative_to(root)]
        assert len(external) == 1 and external[0].name == "Microsoft.NET.Test.Sdk.Program.cs", external
        generated = external[0]
        assert generated.is_file() and sdk in generated.parts, generated
        config.write_text(json.dumps({"roots": [str(root)], "trustedRoots": [str(root)]} if args.expect_rejection else {"trustedRoots": [str(source)]}), encoding="utf-8")
        client = Client(config)
        try:
            # Ordinary sibling-reference project control must load even on baseline.
            client.good("workspace.open", {"root": str(root), "project": "source/Control/Control.csproj"})
            control = client.good("engine.capabilities", {"root": str(root), "language": "csharp"})
            assert control["analysis"]["projects"] == 2, control
            assert good_query(client, root, "diagnostics", file=str(control_file)) == []
            client.good("workspace.close", {"root": str(root)})
            # No explicit project/config change: request through the source folder.
            if args.expect_rejection:
                client.good("workspace.open", {"root": str(root), "project": "source/Architecture.sln"})
            result = semantic(client, root if args.expect_rejection else source, "definition", file=str(consumer), line=0,
                character=consumer_text.index("AutoGeneratedProgram") + 1)
            if args.expect_rejection:
                assert result.get("isError") and "Path escapes workspace" in json.dumps(result), result
                record = {"platform": platform.system(), "testSdk": sdk,
                    "operation": "semantic.query/definition -> trusted project document loading",
                    "onlyExternalEvaluatedCompileInput": str(generated),
                    "baselineError": "Path escapes workspace",
                    "limitation": "Baseline error omits the exact rejected path; the sole external Compile item is independently evaluated evidence."}
                records.append(record)
                print(json.dumps(record), flush=True)
                continue
            assert not result.get("isError"), result
            definition = result["structuredContent"]["items"]
            assert len(definition) == 1 and pathlib.Path(definition[0]["file"]) == generated, definition
            generated_text = generated.read_text(encoding="utf-8-sig")
            generated_lines = generated_text.splitlines()
            generated_line = next(i for i, line in enumerate(generated_lines) if "class AutoGeneratedProgram" in line)
            assert definition[0]["range"]["start"] == {"line": generated_line,
                "character": generated_lines[generated_line].index("AutoGeneratedProgram")}, definition
            assert good_query(client, root, "diagnostics", file=str(consumer)) == []
            capability = client.good("engine.capabilities", {"root": str(root), "language": "csharp"})
            assert capability["analysis"]["projects"] == 2, capability
            assert str(generated) in capability["analysis"]["externalCompilerInputs"], capability
            assert semantic(client, root, "symbols", file=str(generated))["isError"]
            assert client.call("workspace.open", {"root": str(generated.parent)})["isError"]
            # Explicit selection/reload and historical startup project remain valid.
            client.good("workspace.open", {"root": str(root), "project": "source/Architecture.sln", "reload": True})
            assert good_query(client, root, "diagnostics", file=str(consumer)) == []
            # Add one exact evaluated external source; it references an in-root symbol.
            authored = base / ("External-" + sdk + ".cs")
            authored_text = "using Library; public class ExternalProvider { public Widget Build() => new Widget(); }\n"
            authored.write_text(authored_text, encoding="utf-8")
            app.write_text(app_text.replace('</ItemGroup>', '<Compile Include="' + escape(str(authored), {'"': '&quot;'}) + '" Link="External.cs" /></ItemGroup>'), encoding="utf-8")
            consumer.write_text(consumer_text.replace("public System.Type Generated", "public ExternalProvider Provider => new ExternalProvider(); public Widget ViaExternal() => new ExternalProvider().Build(); public System.Type Generated"), encoding="utf-8")
            client.good("workspace.open", {"root": str(root), "reload": True})
            assert good_query(client, root, "diagnostics", file=str(consumer)) == []
            assert good_query(client, root, "definition", file=str(consumer), line=0,
                character=consumer.read_text(encoding="utf-8").index("ExternalProvider") + 1)[0]["file"] == str(authored)
            rename = semantic(client, root, "rename", file=str(widget), line=0,
                character=widget_text.index("Widget") + 1, newName="RenamedWidget")
            assert rename.get("isError"), rename
            error = rename["structuredContent"]["error"]
            assert error["code"] == "external_input_read_only", error
            assert widget.read_text(encoding="utf-8") == widget_text
            assert authored.read_text(encoding="utf-8") == authored_text
            assert semantic(client, root, "symbols", file=str(authored))["isError"]
            # Refresh preserves external source semantics, not an inert dropped file.
            authored.write_text(authored_text.replace("Widget Build() => new Widget()", 'string Build() => "wrong"'), encoding="utf-8")
            client.good("workspace.open", {"root": str(root), "reload": True})
            diagnostics = good_query(client, root, "diagnostics", file=str(consumer))
            assert any(item["code"] == "CS0029" for item in diagnostics), diagnostics
            authored.write_text(authored_text, encoding="utf-8")
            client.good("workspace.open", {"root": str(root), "reload": True})
            assert good_query(client, root, "diagnostics", file=str(consumer)) == []
            # The same exact SDK source is compiled in two independent projects.
            # Every Roslyn DocumentId must receive fresh text, not only the first.
            shared = base / ("Shared-" + sdk + ".cs")
            shared_text = "internal static class SharedInput { public static int Value => 42; }\n"
            shared.write_text(shared_text, encoding="utf-8")
            shared_item = '<Compile Include="' + escape(str(shared), {'"': '&quot;'}) + '" />'
            (root / "source/Second").mkdir()
            second_project = root / "source/Second/Second.csproj"
            second_project.write_text(app_text.replace('</ItemGroup>', shared_item + '</ItemGroup>'), encoding="utf-8")
            second_file = root / "source/Second/Second.cs"
            second_file.write_text("public class SecondConsumer { public int Shared => SharedInput.Value; }\n", encoding="utf-8")
            app.write_text(app_text.replace('</ItemGroup>', shared_item + '<ProjectReference Include="../Second/Second.csproj" /></ItemGroup>'), encoding="utf-8")
            consumer.write_text(consumer_text.replace("public System.Type Generated", "public int Shared => SharedInput.Value; public System.Type Generated"), encoding="utf-8")
            run(dotnet, "restore", app, "--ignore-failed-sources", cwd=root)
            client.good("workspace.open", {"root": str(root), "reload": True})
            for document in (consumer, second_file):
                assert good_query(client, root, "diagnostics", file=str(document)) == []
            shared.write_text('internal static class SharedInput { public static string Value => "wrong"; }\n', encoding="utf-8")
            for document in (consumer, second_file):
                diagnostics = good_query(client, root, "diagnostics", file=str(document))
                assert any(item["code"] == "CS0029" for item in diagnostics), diagnostics
            shared.write_text(shared_text, encoding="utf-8")
            for document in (consumer, second_file):
                assert good_query(client, root, "diagnostics", file=str(document)) == []
            # Restore the single-project shape before testing special-file refusal.
            app.write_text(app_text, encoding="utf-8")
            consumer.write_text(consumer_text, encoding="utf-8")
            run(dotnet, "restore", app, "--ignore-failed-sources", cwd=root)
            if os.name != "nt":
                linked = base / ("Symlink-" + sdk + ".cs")
                linked.symlink_to(authored)
                app.write_text(app_text.replace('</ItemGroup>', '<Compile Include="' + escape(str(linked), {'"': '&quot;'}) + '" /></ItemGroup>'), encoding="utf-8")
                client.good("workspace.open", {"root": str(root), "reload": True})
                refused = client.call("engine.capabilities", {"root": str(root), "language": "csharp"})
                assert refused.get("isError") and any(word in json.dumps(refused).lower() for word in ("symlink", "reparse")), refused
                app.write_text(app_text, encoding="utf-8")
                fifo = base / ("Pipe-" + sdk + ".cs")
                os.mkfifo(fifo)
                app.write_text(app_text.replace('</ItemGroup>', '<Compile Include="' + escape(str(fifo), {'"': '&quot;'}) + '" /></ItemGroup>'), encoding="utf-8")
                client.good("workspace.open", {"root": str(root), "reload": True})
                started = time.monotonic()
                refused = client.call("engine.capabilities", {"root": str(root), "language": "csharp"})
                assert time.monotonic() - started < 30, "FIFO source must be refused without blocking until worker timeout"
                assert refused.get("isError"), refused
                error = refused["structuredContent"]["error"]
                assert error["code"] == "external_compiler_input_rejected", error
                assert any(item.get("operation") == "read_compiler_input" for item in error["diagnostics"]), error
                app.write_text(app_text, encoding="utf-8")
        finally:
            client.close()
        if not args.expect_rejection:
            config.write_text(json.dumps({"roots": [str(root)], "trustedRoots": [str(root)],
                "csharp": {"project": "source/Architecture.sln"}}), encoding="utf-8")
            # Restore the original source/project pair for legacy policy coverage.
            app.write_text(app_text, encoding="utf-8")
            consumer.write_text(consumer_text, encoding="utf-8")
            client = Client(config)
            try:
                caps = client.good("engine.capabilities", {"root": str(root), "language": "csharp"})
                assert str(generated) in caps["analysis"]["externalCompilerInputs"], caps
                assert good_query(client, root, "diagnostics", file=str(consumer)) == []
            finally:
                client.close()
            record = {"platform": platform.system(), "testSdk": sdk,
                "externalCompileInput": str(generated), "result": "passed",
                "checks": ["ordinary control", "nested solution and sibling reference", "automatic source-root routing",
                    "exact generated-source definition", "external source retained", "read-only rename refusal",
                    "direct external query/workspace refusal", "explicit selection/reload", "legacy startup project"]}
            records.append(record)
            print(json.dumps(record), flush=True)

report_dir = repo / "bin/.local/reports"
report_dir.mkdir(parents=True, exist_ok=True)
report = report_dir / ("external-input-baseline.json" if args.expect_rejection else "external-input-fixed.json")
report.write_text(json.dumps({"platform": platform.system(), "architecture": platform.machine(),
    "baselineRelease": "v0.1.0-preview.20261020.trusted.1997d38" if args.baseline_release else None,
    "expectRejection": args.expect_rejection, "records": records,
    "scope": "Authored fixture; does not establish private Biztraak reproduction acceptance."}, indent=2) + "\n", encoding="utf-8")
if baseline_directory is not None:
    baseline_directory.cleanup()
