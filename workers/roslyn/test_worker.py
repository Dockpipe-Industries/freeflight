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
                           stdout=subprocess.PIPE, text=True, encoding="utf-8", errors="strict")
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
    process.stdin.write(json.dumps(dict(id=sequence, method=method, params=params), ensure_ascii=False) + "\n")
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
        advanced = pathlib.Path(__file__).parent / "fixtures" / "Advanced.cs"
        (root / "Advanced.cs").write_text(advanced.read_text())
        def position(line, word, offset=0):
            return dict(file="Advanced.cs", line=line,
                        character=advanced.read_text().splitlines()[line].index(word) + offset)
        implementations = call("implementations", **position(1, "Add", 1))["result"]
        assert {item["locations"][0]["range"]["start"]["line"] for item in implementations} == {4, 8}, implementations
        info = call("typeInfo", **position(15, "42"))["result"]
        assert info["display"] == "int" and info["kind"] == "Struct", info
        signatures = call("signatureHelp", **position(15, "42"))["result"]
        assert len(signatures["signatures"]) == 2, signatures
        assert {item["parameters"][0]["display"] for item in signatures["signatures"]} == {"int value", "string value"}, signatures
        assert signatures["argumentIndex"] == 0 and signatures["argumentCount"] == 1, signatures
        assert signatures["signatures"][signatures["selectedItemIndex"]]["parameters"][0]["display"] == "int value", signatures
        two_arguments = call("signatureHelp", **position(12, "2"))["result"]
        assert two_arguments["argumentIndex"] == 1 and two_arguments["argumentCount"] == 2, two_arguments
        found = call("workspaceSymbols", query="deriv")["result"]
        assert len(found) == 1 and found[0]["name"] == "Derived", found
        assert found[0]["locations"][0]["range"]["start"] == dict(line=6, character=13), found
        assert "error" in call("workspaceSymbols", query="")
        hierarchy = call("typeHierarchy", **position(6, "Derived", 1))["result"]
        assert [item["name"] for item in hierarchy["supertypes"]] == ["Base"], hierarchy
        assert hierarchy["subtypes"] == [], hierarchy
        hierarchy = call("typeHierarchy", **position(2, "Base", 1))["result"]
        assert [item["name"] for item in hierarchy["subtypes"]] == ["Derived"], hierarchy
        hierarchy = call("typeHierarchy", **position(1, "ICalc", 1))["result"]
        assert [item["name"] for item in hierarchy["subtypes"]] == ["Base"], hierarchy
        calls = call("callHierarchy", **position(12, "Run", 1))["result"]
        assert len(calls) == 1 and calls[0]["incoming"] == [], calls
        assert {edge["to"]["name"] for edge in calls[0]["outgoing"]} == {".ctor", "Add"}, calls
        assert all(edge["locations"][0]["range"]["start"]["line"] == 12 for edge in calls[0]["outgoing"]), calls
        callers = call("callHierarchy", **position(8, "Add", 1))["result"]
        assert [edge["from"]["name"] for edge in callers[0]["incoming"] if edge["isDirect"]] == ["Run"], callers
        assert [edge["from"]["name"] for edge in callers[0]["incoming"] if not edge["isDirect"]] == ["Add"], callers
        assert callers[0]["incoming"][0]["locations"][0]["range"]["start"]["line"] == 12, callers
        nested = call("callHierarchy", **position(16, "Nested", 1))["result"]
        assert nested[0]["outgoing"] == [], nested
        local = call("callHierarchy", **position(16, "Local", 1))["result"]
        assert [edge["to"]["name"] for edge in local[0]["outgoing"]] == ["Overload"], local
        unicode_source = 'class Unicode { string text = "😀"; int Read() => text.Length; }'
        (root / "Unicode.cs").write_text(unicode_source, encoding="utf-8")
        unicode_character = len(unicode_source[:unicode_source.rindex("text")].encode("utf-16-le")) // 2
        unicode_type = call("typeInfo", file="Unicode.cs", line=0, character=unicode_character)["result"]
        assert unicode_type["display"] == "string", unicode_type
        utf8_file = root / "Καλημέρα-日本語.cs"
        utf8_source = 'class Καλημέρα { string text = "😀"; public int 値 = 7; public int Read() => 値; }'
        utf8_file.write_text(utf8_source, encoding="utf-8")
        utf8_symbols = call("symbols", file=str(utf8_file))["result"]
        assert {item["name"] for item in utf8_symbols} >= {"Καλημέρα", "値"}, utf8_symbols
        utf8_use = len(utf8_source[:utf8_source.rindex("値")].encode("utf-16-le")) // 2
        utf8_definition = call("definition", file=str(utf8_file), line=0, character=utf8_use)["result"]
        assert len(utf8_definition) == 1 and pathlib.Path(utf8_definition[0]["file"]) == utf8_file, utf8_definition
        assert utf8_definition[0]["range"]["start"] == {"line": 0, "character": len(utf8_source[:utf8_source.index("値")].encode("utf-16-le")) // 2}, utf8_definition
        (root / "Bounds.cs").write_text("\n".join(f"class QueryLimit{i} {{}}" for i in range(1001)))
        bounded = call("workspaceSymbols", query="QueryLimit")
        assert "1000 symbols" in bounded["error"]["message"], bounded
        (root / "Bounds.cs").unlink()
        (root / "Calls.cs").write_text("class CallLimit { static void Target() {} public static void Burst() {" + "Target();" * 501 + "} }")
        bounded = call("callHierarchy", file="Calls.cs", line=0, character=61)
        assert "500 outgoing" in bounded["error"]["message"], bounded
        (root / "Calls.cs").unlink()
        assert len(call("workspaceSymbols", query="Derived")["result"]) == 1


    print("Roslyn semantic navigation, implementations, types, signatures, hierarchies, limits, preview, refresh, boundary, no-MSBuild, malformed input, and cancellation checks passed")
finally:
    process.stdin.close()
    process.wait(timeout=15)

# Invalid raw UTF-8 is rejected deterministically instead of silently decoding as ACP
# or replacement characters. A decoding failure closes this worker stream safely.
for malformed_bytes in (b'{"id":"\xff","method":"capabilities"}\n', b'{"id":"\xe2\x82'):
    result = subprocess.run(command, input=malformed_bytes, stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE, timeout=15, check=True)
    assert not result.stdout.startswith(b'\xef\xbb\xbf'), 'Worker emitted a UTF-8 BOM'
    reply = json.loads(result.stdout.decode('utf-8', errors='strict'))
    assert reply == {"id": None, "error": {"message": "Invalid UTF-8 input"}}, reply
print("Roslyn raw UTF-8 filename/symbol semantics and strict invalid/truncated UTF-8 rejection passed")
