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
    widget_source = "namespace Library;\n#if PROJECT_SETTING\npublic class Widget { public int Value => 42; }\n#endif\n" + "/*" + "x" * (3 * 1024 * 1024) + "*/"
    (root / "Lib/Widget.cs").write_bytes(widget_source.encode("utf-8"))
    source = "using Library;\nclass Consumer { public int Read(Widget value) => value.Value; }\n"
    (root / "App/Consumer.cs").write_text(source)
    (root / "App/App.csproj").write_text(f'<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup>{properties}</PropertyGroup><ItemGroup><ProjectReference Include="../Lib/Lib.csproj" /></ItemGroup></Project>')
    # Fixture setup explicitly restores our own dependency-free projects. The worker must not restore.
    subprocess.run([dotnet, "restore", str(root / "App/App.csproj"), "--ignore-failed-sources"], check=True, timeout=60)
    env = os.environ.copy()
    env["DOTNET_ROOT"] = str(pathlib.Path(dotnet).resolve().parent)
    worker_command = [str(worker)] if "--native" in sys.argv[3:] else [dotnet, str(worker)]
    process = subprocess.Popen(worker_command + ["--trusted-msbuild"], stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True, env=env)
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
        # Initial project documents use inert placeholders; every source must have
        # its guarded snapshot installed before the following cross-project queries.
        initial = call("capabilities")["result"]["refreshStats"]
        assert initial["bytesRead"] == sum(path.stat().st_size for path in
            (root / "Lib/Widget.cs", root / "App/Consumer.cs")), initial
        assert initial["reusedSnapshots"] == 0, initial
        diagnostics = call("diagnostics", file="App/Consumer.cs")
        assert diagnostics["result"] == [], diagnostics
        definition = call("definition", file="App/Consumer.cs", line=1, character=57)["result"]
        assert len(definition) == 1 and pathlib.Path(definition[0]["file"]).resolve() == (root / "Lib/Widget.cs").resolve(), definition
        assert definition[0]["range"]["start"] == dict(line=2, character=33), definition
        references = call("references", file="Lib/Widget.cs", line=2, character=34)["result"]
        assert len(references) == 1 and pathlib.Path(references[0]["file"]).resolve() == (root / "App/Consumer.cs").resolve(), references
        # Actual NuGet assets logs are surfaced by Roslyn 5.9 as Failure, with
        # their code/severity stripped from WorkspaceDiagnostic.Message. Preserve
        # their original Warning evidence without allowing arbitrary failures.
        assets = root / "App/obj/project.assets.json"
        original_assets = assets.read_text()
        warning_logs = [
            {"code": "NU1603", "level": "Warning", "message": "Fixture depends on Example (>= 1.0.0) but Example 1.0.0 was not found. Example 1.0.1 was resolved instead."},
            {"code": "NU1903", "level": "Warning", "message": "Package Example 1.0.1 has a known high severity vulnerability, https://example.invalid/advisory"},
            {"code": "NU1701", "level": "Warning", "message": "Package Example was restored using .NETFramework instead of net10.0. This package may not be fully compatible with your project."},
        ]
        def set_logs(logs):
            data = json.loads(original_assets)
            data["logs"] = [{**entry, "libraryId": "Example", "targetGraphs": ["net10.0"]} for entry in logs]
            assets.write_text(json.dumps(data))
        set_logs(warning_logs)
        opened = call("open", root=str(root), project="App/App.csproj")["result"]
        assert opened["selectedProject"].replace("\\", "/") == "App/App.csproj", opened
        assert opened["degradedFidelity"] is True, opened
        warnings = opened["loadWarnings"]
        assert {w["code"] for w in warnings} == {w["code"] for w in warning_logs}, warnings
        for warning in warnings:
            expected = next(w for w in warning_logs if w["code"] == warning["code"])
            assert warning["message"] == expected["message"] and warning["severity"] == "Warning", warning
            assert warning["reportedKind"] == "Failure", warning
        assert call("capabilities")["result"]["loadWarnings"] == warnings
        assert call("diagnostics", file="App/Consumer.cs")["result"] == []
        definition = call("definition", file="App/Consumer.cs", line=1, character=57)["result"]
        assert len(definition) == 1 and definition[0]["range"]["start"] == dict(line=2, character=33), definition
        assert pathlib.Path(definition[0]["file"]).resolve() == root / "Lib/Widget.cs"
        # NU-shaped text alone is not proof: unsupported warning codes and an
        # assets file bound to another project cannot downgrade a Failure.
        set_logs([{**warning_logs[0], "code": "NU1605"}])
        rejected = call("open", root=str(root), project="App/App.csproj")["error"]
        assert rejected["code"] == "project_load_failed", rejected
        set_logs(warning_logs)
        mismatched = json.loads(assets.read_text())
        mismatched["project"]["restore"]["projectPath"] = str(root / "Different.csproj")
        assets.write_text(json.dumps(mismatched))
        rejected = call("open", root=str(root), project="App/App.csproj")["error"]
        assert rejected["code"] == "project_load_failed", rejected
        # The same warning-looking text with Error severity must remain fatal.
        set_logs([{**warning_logs[0], "level": "Error"}])
        rejected = call("open", root=str(root), project="App/App.csproj")["error"]
        assert rejected["code"] == "project_load_failed", rejected
        assert "NU1603" in json.dumps(rejected) and "Error" in json.dumps(rejected), rejected
        assets.write_text(original_assets)
        # A genuine design-time MSBuild error cannot be waved through simply
        # because project objects were still returned by MSBuildWorkspace.
        project = root / "App/App.csproj"
        original_project = project.read_text()
        project.write_text(original_project.replace("</Project>", '<Target Name="FixtureFailure" BeforeTargets="CoreCompile"><Error Text="Deliberate project-load failure" /></Target></Project>'))
        rejected = call("open", root=str(root), project="App/App.csproj")["error"]
        assert rejected["code"] == "project_load_failed" and "Deliberate project-load failure" in json.dumps(rejected), rejected
        assert "automatically indicated" in rejected["remediation"] and "Explicitly restore" not in rejected["remediation"], rejected
        project.write_text(original_project)
        # An actual MSBuild Error with the exact text of a persisted Warning
        # must not borrow that warning's severity (or be accepted twice).
        set_logs([warning_logs[1]])
        project.write_text(original_project.replace("</Project>", '<Target Name="FixtureCollision" BeforeTargets="CoreCompile"><Error Text="' + warning_logs[1]["message"] + '" /></Target></Project>'))
        rejected = call("open", root=str(root), project="App/App.csproj")["error"]
        assert rejected["code"] == "project_load_failed", rejected
        assert warning_logs[1]["message"] in json.dumps(rejected), rejected
        project.write_text(original_project)
        assets.write_text(original_assets)
        # MSBuild can promote a persisted Warning to a genuine Error according
        # to operator project policy. The original assets severity cannot override it.
        set_logs([warning_logs[1]])
        project.write_text(original_project.replace("</PropertyGroup>", "<MSBuildWarningsAsErrors>NU1903</MSBuildWarningsAsErrors></PropertyGroup>"))
        rejected = call("open", root=str(root), project="App/App.csproj")["error"]
        assert rejected["code"] == "project_load_failed", rejected
        assert warning_logs[1]["message"] in json.dumps(rejected), rejected
        project.write_text(original_project)
        assets.write_text(original_assets)
        # Removing real restore evidence justifies restore guidance; no restore
        # is performed by FreeFlight. Restore it ourselves only by restoring bytes.
        obj = root / "App/obj"
        saved_obj = {path.relative_to(obj): path.read_bytes() for path in obj.rglob("*") if path.is_file()}
        shutil.rmtree(obj)  # Remove design-time caches as well as the JSON assets.
        rejected = call("open", root=str(root), project="App/App.csproj")["error"]
        assert rejected["code"] == "restore_required", rejected
        assert not assets.exists(), "worker must not run dependency restore"
        for relative, contents in saved_obj.items():
            restored = obj / relative
            restored.parent.mkdir(parents=True, exist_ok=True)
            restored.write_bytes(contents)
        # Restoring cached target outputs after assets changes would make stale
        # warning caches appear newer than their inputs. Rebuild disposable caches.
        for cache in obj.rglob("*.cache"):
            cache.unlink()
        # Bounded discovery finds the nested solution and prefers it over projects.
        nested = root / "source"
        nested.mkdir()
        sln = nested / "Architecture.sln"
        sln.write_text('Microsoft Visual Studio Solution File, Format Version 12.00\n'
            'Project("{FAE04EC0-301F-11D3-BF4B-00C04F79EFBC}") = "App", "../App/App.csproj", "{F99CC167-3E5A-4E4E-8C0E-B43FD3F69B41}"\nEndProject\nGlobal\nEndGlobal\n')
        response = call("open", root=str(root))
        assert "result" in response, response
        opened = response["result"]
        assert opened["selectedProject"].replace("\\", "/") == "source/Architecture.sln", opened
        assert opened["loadWarnings"] == [], opened
        other = root / "Other.sln"
        other.write_text(sln.read_text().replace("../App/", "App/"))
        rejected = call("open", root=str(root))["error"]
        assert rejected["code"] == "project_selection_required", rejected
        assert "Architecture.sln" in json.dumps(rejected) and "Other.sln" in json.dumps(rejected), rejected
        assert "result" in call("open", root=str(root), project="source/Architecture.sln")
        other.unlink()
        empty_solution = nested / "Empty.sln"
        empty_solution.write_text("Microsoft Visual Studio Solution File, Format Version 12.00\nGlobal\nEndGlobal\n")
        rejected = call("open", root=str(root), project="source/Empty.sln")["error"]
        assert rejected["code"] == "project_load_failed", rejected
        empty_solution.unlink()
        assert "result" in call("open", root=str(root), project="source/Architecture.sln")
        # Refresh must reject replaced non-target leaves/ancestors even when the
        # previous source snapshot is reusable. Unix symlink fixture only; Windows
        # reparse-point qualification requires its own privilege-aware fixture.
        if os.name != "nt":
            with tempfile.TemporaryDirectory(prefix="trusted-path-outside-", dir=root.parent) as outside_dir:
                outside_root = pathlib.Path(outside_dir)
                (outside_root / "Widget.cs").write_bytes(widget_source.encode("utf-8"))
                leaf = root / "Lib/Widget.cs"
                saved_leaf = root / "Lib/Widget.cs.saved"
                leaf.rename(saved_leaf)
                try:
                    leaf.symlink_to(outside_root / "Widget.cs")
                    rejected = call("symbols", file="App/Consumer.cs")
                    assert "error" in rejected and "Symlink/reparse" in str(rejected), rejected
                finally:
                    leaf.unlink()
                    saved_leaf.rename(leaf)
                assert "result" in call("symbols", file="App/Consumer.cs"), "leaf replacement recovery"
                ancestor = root / "Lib"
                saved_ancestor = root / "Lib-saved"
                ancestor.rename(saved_ancestor)
                try:
                    ancestor.symlink_to(outside_root, target_is_directory=True)
                    rejected = call("symbols", file="App/Consumer.cs")
                    assert "error" in rejected and "Symlink/reparse" in str(rejected), rejected
                finally:
                    ancestor.unlink()
                    saved_ancestor.rename(ancestor)
                assert "result" in call("symbols", file="App/Consumer.cs"), "ancestor replacement recovery"
                leaf.unlink()
                try:
                    assert "error" in call("symbols", file="App/Consumer.cs"), "missing graph input silently omitted"
                finally:
                    leaf.write_bytes(widget_source.encode("utf-8"))
                assert "result" in call("symbols", file="App/Consumer.cs"), "missing input recovery"
        (root / "App/Consumer.cs").write_text(source.replace("value.Value", '"invalid"'))
        diagnostics = call("diagnostics", file="App/Consumer.cs")["result"]
        assert any(d["code"] == "CS0029" for d in diagnostics), diagnostics
        rejected = call("open", root=str(root), project="App/App.csproj", resources={"maxFileBytes": 2 * 1024 * 1024})["error"]
        assert rejected["code"] == "resource_limit_exceeded" and rejected["resource"] == "maxFileBytes", rejected
        assert rejected["path"].replace("\\", "/") == "Lib/Widget.cs" and rejected["observed"] == len(widget_source.encode()), rejected
        assert rejected["limit"] == 2 * 1024 * 1024, rejected
        assert "result" in call("open", root=str(root), project="App/App.csproj"), "trusted worker recovery"
        assert "error" in call("open", root=str(root), project="../outside.csproj")
        assert "error" in call("open", root=str(root), mode="safe-source", project="App/App.csproj")
        outside = root.parent / (root.name + "-outside.cs")
        outside.write_text("class Outside {}")
        try:
            project = root / "App/App.csproj"
            project.write_text(project.read_text().replace("</Project>", f'<ItemGroup><Compile Include="{outside.as_posix()}" /></ItemGroup></Project>'))
            opened = call("open", root=str(root), project="App/App.csproj")["result"]
            assert str(outside) in opened["externalCompilerInputs"], opened
            assert "error" in call("symbols", file=str(outside)), "external input is not a query grant"
        finally:
            outside.unlink()
        print("Trusted MSBuild project settings, cross-project definition/references, diagnostics, refresh and boundary tests passed")
    finally:
        process.stdin.close()
        process.wait(timeout=15)
