"""Semantic contract test; invoked by DockPipe, requires built worker path and dotnet."""
import json
import hashlib
import pathlib
import queue
import shutil
import subprocess
import sys
import tempfile
import threading

worker = pathlib.Path(sys.argv[2]).resolve()
if sys.argv[1] == "--native":
    command = [str(worker)]
else:
    dotnet = shutil.which(sys.argv[1])
    if dotnet is None:
        raise SystemExit(f"Cannot find .NET executable: {sys.argv[1]}")
    command = [dotnet, str(worker)]
process = subprocess.Popen(command, stdin=subprocess.PIPE,
                           stdout=subprocess.PIPE, text=True)
sequence = 0
responses = queue.Queue()


def read_responses():
    for line in process.stdout:
        responses.put(line)


threading.Thread(target=read_responses, daemon=True).start()


def response():
    return json.loads(responses.get(timeout=75))


def call(method, **params):
    global sequence
    sequence += 1
    process.stdin.write(json.dumps(dict(id=sequence, method=method, params=params)) + "\n")
    process.stdin.flush()
    result = response()
    assert result["id"] == sequence, result
    return result


try:
    for malformed in ("{broken", "[]", "null", "42", "{}"):
        process.stdin.write(malformed + "\n")
        process.stdin.flush()
        assert "error" in response()
        assert "symbols" in call("capabilities")["result"]["operations"]
    with tempfile.TemporaryDirectory(prefix="freeflight-roslyn-cancel-") as folder:
        cancellation_root = pathlib.Path(folder).resolve()
        for index in range(500):
            (cancellation_root / f"File{index}.cs").write_text(f"class C{index} {{ int Value; }}")
        sequence += 1
        request_id = sequence
        process.stdin.write(json.dumps(dict(id=request_id, method="open", params=dict(root=str(cancellation_root)))) + "\n")
        process.stdin.write(json.dumps(dict(method="cancel", params=dict(id=request_id))) + "\n")
        process.stdin.flush()
        cancelled = response()
        assert cancelled["id"] == request_id and cancelled["error"]["message"] == "Request cancelled", cancelled
        assert "result" in call("capabilities"), "worker did not recover after cancellation"
    with tempfile.TemporaryDirectory(prefix="freeflight-roslyn-") as folder:
        root = pathlib.Path(folder).resolve()
        source = pathlib.Path(__file__).parent / "fixtures" / "Sample.cs"
        sample = root / "Sample.cs"
        sample.write_text(source.read_text())
        # If evaluated by MSBuild, this project would create a sentinel file.
        (root / "Unsafe.csproj").write_text('<Project Sdk="Microsoft.NET.Sdk"><Target Name="Run" BeforeTargets="Build"><WriteLinesToFile File="executed" Lines="unsafe" /></Target></Project>')
        opened = call("open", root=str(root))["result"]
        assert opened["mode"] == "safe-source" and opened["files"] == 1
        assert call("capabilities")["result"]["projectEvaluation"] is False
        assert "error" in call("open", root=str(root), mode="trusted-msbuild")
        assert not (root / "executed").exists()
        symbols = call("symbols", file="Sample.cs")["result"]
        assert {s["name"] for s in symbols} >= {"Counter", "Value", "Increment", "Consumer", "Read"}
        definition = call("definition", file="Sample.cs", line=8, character=51)["result"]
        assert definition[0]["range"]["start"] == {"line": 3, "character": 15}, definition
        references = call("references", file="Sample.cs", line=3, character=16)["result"]
        assert {r["range"]["start"]["line"] for r in references} == {4, 8}, references
        hover = call("hover", file="Sample.cs", line=3, character=16)["result"]
        assert "int" in hover["contents"] and "Value" in hover["contents"], hover
        assert call("diagnostics", file="Sample.cs")["result"] == []
        rename = call("rename", file="Sample.cs", line=3, character=16, newName="Count")["result"]
        assert rename["preview"] and len(rename["edits"][0]["edits"]) == 3, rename
        assert rename["edits"][0]["expectedSha256"] == hashlib.sha256(sample.read_bytes()).hexdigest(), rename
        assert sample.read_text() == source.read_text(), "rename wrote source"
        assert "error" in call("hover", file="../escape.cs", line=0, character=0)
        assert "error" in call("hover", file="Sample.cs", line=-1, character=0)
        outside = root.parent / (root.name + "-outside.cs")
        outside.write_text("class Secret {}")
        try:
            (root / "Escape.cs").symlink_to(outside)
            assert "error" in call("symbols", file="Escape.cs")
        finally:
            outside.unlink()
        sample.write_text(source.read_text().replace("++Value", "Missing"))
        diagnostics = call("diagnostics", file="Sample.cs")["result"]
        assert any(d["code"] == "CS0103" and d["location"]["range"]["start"]["line"] == 4 for d in diagnostics), diagnostics
        assert "error" in call("open", root=str(root), mode="msbuild")
    print("Roslyn semantic, preview, refresh, boundary, no-MSBuild, malformed input, and cancellation checks passed")
finally:
    process.stdin.close()
    process.wait(timeout=15)
