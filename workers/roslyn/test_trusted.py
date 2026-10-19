"""Explicitly trusted, locally authored SDK fixture; never runs arbitrary user projects."""
import json
import os
import pathlib
import queue
import shutil
import subprocess
import sys
import tempfile
import threading

repo = pathlib.Path(__file__).resolve().parents[2]
dotnet = shutil.which(sys.argv[1])
assert dotnet, "dotnet SDK is required for trusted-mode tests"
worker = pathlib.Path(sys.argv[2]).resolve()
with tempfile.TemporaryDirectory(prefix="trusted-roslyn-", dir=repo / "bin/.local") as directory:
    root = pathlib.Path(directory).resolve()
    properties = "<TargetFramework>net10.0</TargetFramework><LangVersion>12</LangVersion><GenerateAssemblyInfo>false</GenerateAssemblyInfo><GenerateTargetFrameworkAttribute>false</GenerateTargetFrameworkAttribute><EnableNETAnalyzers>false</EnableNETAnalyzers>"
    (root / "Lib").mkdir()
    (root / "App").mkdir()
    (root / "Lib/Lib.csproj").write_text(f'<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup>{properties}<DefineConstants>PROJECT_SETTING</DefineConstants></PropertyGroup></Project>')
    (root / "Lib/Widget.cs").write_text("namespace Library;\n#if PROJECT_SETTING\npublic class Widget { public int Value => 42; }\n#endif\n")
    source = "using Library;\nclass Consumer { public int Read(Widget value) => value.Value; }\n"
    (root / "App/Consumer.cs").write_text(source)
    (root / "App/App.csproj").write_text(f'<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup>{properties}</PropertyGroup><ItemGroup><ProjectReference Include="../Lib/Lib.csproj" /></ItemGroup></Project>')
    # Fixture setup explicitly restores our own dependency-free projects. The worker must not restore.
    subprocess.run([dotnet, "restore", str(root / "App/App.csproj"), "--ignore-failed-sources"], check=True, timeout=60)
    env = os.environ.copy()
    env["DOTNET_ROOT"] = str(pathlib.Path(dotnet).resolve().parent)
    process = subprocess.Popen([dotnet, str(worker), "--trusted-msbuild"], stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True, env=env)
    replies = queue.Queue()
    def read():
        for line in process.stdout:
            replies.put(line)
    threading.Thread(target=read, daemon=True).start()
    sequence = 0
    def call(method, **params):
        global sequence
        sequence += 1
        process.stdin.write(json.dumps(dict(id=sequence, method=method, params=params)) + "\n")
        process.stdin.flush()
        reply = json.loads(replies.get(timeout=75))
        assert reply["id"] == sequence, reply
        return reply
    try:
        assert call("capabilities")["result"]["fidelity"] == "trusted-msbuild"
        opened = call("open", root=str(root), project="App/App.csproj")
        assert opened["result"]["projects"] == 2, opened
        diagnostics = call("diagnostics", file="App/Consumer.cs")
        assert diagnostics["result"] == [], diagnostics
        definition = call("definition", file="App/Consumer.cs", line=1, character=57)["result"]
        assert len(definition) == 1 and definition[0]["file"].endswith("Lib/Widget.cs"), definition
        assert definition[0]["range"]["start"] == dict(line=2, character=33), definition
        references = call("references", file="Lib/Widget.cs", line=2, character=34)["result"]
        assert len(references) == 1 and references[0]["file"].endswith("App/Consumer.cs"), references
        (root / "App/Consumer.cs").write_text(source.replace("value.Value", '"invalid"'))
        diagnostics = call("diagnostics", file="App/Consumer.cs")["result"]
        assert any(d["code"] == "CS0029" for d in diagnostics), diagnostics
        assert "error" in call("open", root=str(root), project="../outside.csproj")
        assert "error" in call("open", root=str(root), mode="safe-source", project="App/App.csproj")
        outside = root.parent / (root.name + "-outside.cs")
        outside.write_text("class Outside {}")
        try:
            project = root / "App/App.csproj"
            project.write_text(project.read_text().replace("</Project>", f'<ItemGroup><Compile Include="{outside.as_posix()}" /></ItemGroup></Project>'))
            rejected = call("open", root=str(root), project="App/App.csproj")
            assert "escapes workspace" in rejected["error"]["message"], rejected
        finally:
            outside.unlink()
        print("Trusted MSBuild project settings, cross-project definition/references, diagnostics, refresh and boundary tests passed")
    finally:
        process.stdin.close()
        process.wait(timeout=15)
