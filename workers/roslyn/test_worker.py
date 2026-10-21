"""Semantic contract test; invoked by DockPipe, requires built worker path and dotnet."""
import json
import os
import hashlib
import pathlib
import queue
import shutil
import subprocess
import sys
import tempfile
import threading
import time

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
        # Merged namespace/partial symbols must keep document-local declaration
        # locations. Different line offsets expose accidental first-file reuse.
        outlines = {
            "OutlineA.cs": "namespace Shared.Area;\npublic partial class Merged { }\n",
            "OutlineB.cs": "// second\n// offset\nnamespace Shared.Area;\npublic partial class Merged { public int Local => 1; }\n",
            "OutlineC.cs": "namespace Shared.Area { public class Third { } }\n\nnamespace Shared.Area { public enum Choice { One } }\n",
        }
        try:
            for name, content in outlines.items():
                (root / name).write_text(content)
            for name, starts in (("OutlineA.cs", [dict(line=0, character=17)]),
                                 ("OutlineB.cs", [dict(line=2, character=17)]),
                                 ("OutlineC.cs", [dict(line=0, character=17), dict(line=2, character=17)])):
                outline = call("symbols", file=name)["result"]
                namespaces = [item for item in outline if item["kind"] == "Namespace"]
                assert [item["location"]["range"]["start"] for item in namespaces] == starts, outline
                assert all(pathlib.Path(item["location"]["file"]).resolve() == root / name for item in outline), outline
            merged = next(item for item in call("symbols", file="OutlineB.cs")["result"] if item["name"] == "Merged")
            assert merged["location"]["range"]["start"] == dict(line=3, character=21), merged
        finally:
            for name in outlines:
                (root / name).unlink()
        print("Document-local file-scoped/block namespace and partial-type outline locations passed")
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


    # Controlled generated source crosses both historical limits without private code.
    with tempfile.TemporaryDirectory(prefix="freeflight-roslyn-large-") as folder:
        root = pathlib.Path(folder).resolve()
        started = time.monotonic()
        for index in range(3):
            declaration = f"public class Large{index} {{ public static int Value => 42; }}\n"
            generated = "public class GeneratedConstants {\n" + "".join(f"public const int GeneratedValue{i:05d} = {i};\n" for i in range(55000)) + "}\n" if index == 0 else ""
            (root / f"Large{index}.cs").write_text(declaration + generated + "/*" + "x" * (22 * 1024 * 1024) + "*/", encoding="utf-8")
        use = "public class Use { public int Read() => Large0.Value; }\n"
        (root / "Use.cs").write_text(use, encoding="utf-8")
        sizes = {p.name: p.stat().st_size for p in root.glob("*.cs")}
        started = time.monotonic()
        opened = call("open", root=str(root))
        assert opened["result"]["files"] == 4, opened
        opened_seconds = time.monotonic() - started
        queried = time.monotonic()
        definition = call("definition", file="Use.cs", line=0, character=use.index("Value"))["result"]
        assert len(definition) == 1 and pathlib.Path(definition[0]["file"]).name == "Large0.cs", definition
        assert definition[0]["range"]["start"] == {"line": 0, "character": 40}, definition
        references = call("references", file="Large0.cs", line=0, character=40)["result"]
        assert len(references) == 1 and pathlib.Path(references[0]["file"]).name == "Use.cs", references
        assert call("diagnostics", file="Large0.cs")["result"] == []
        assert {x["name"] for x in call("symbols", file="Large2.cs")["result"]} == {"Large2", "Value"}
        # Settle filesystem notifications, then establish and measure a warm snapshot.
        time.sleep(0.2)
        call("definition", file="Use.cs", line=0, character=use.index("Value"))
        before = call("capabilities")["result"]["refreshStats"]
        warm = call("definition", file="Use.cs", line=0, character=use.index("Value"))
        after = call("capabilities")["result"]["refreshStats"]
        assert warm["result"] == definition
        assert after["bytesRead"] - before["bytesRead"] == sizes["Use.cs"], (before, after)
        assert after["reusedSnapshots"] - before["reusedSnapshots"] == 3, (before, after)
        print(json.dumps({"fixture": "roslyn-warm-query", "sourceBytesRead": after["bytesRead"] - before["bytesRead"], "unchangedLargeSnapshotsReused": 3}))
        before = call("capabilities")["result"]["refreshStats"]
        found = call("workspaceSymbols", query="Large0")["result"]
        after = call("capabilities")["result"]["refreshStats"]
        assert len(found) == 1 and found[0]["name"] == "Large0", found
        assert after["bytesRead"] == before["bytesRead"], (before, after)
        assert after["reusedSnapshots"] - before["reusedSnapshots"] == 4, (before, after)
        # The directly queried file is always validated, even with preserved length/mtime.
        stamp = (root / "Use.cs").stat()
        (root / "Use.cs").write_text(use.replace("Large0", "Large1"), encoding="utf-8")
        os.utime(root / "Use.cs", ns=(stamp.st_atime_ns, stamp.st_mtime_ns))
        changed = call("definition", file="Use.cs", line=0, character=use.index("Value"))["result"]
        assert pathlib.Path(changed[0]["file"]).name == "Large1.cs", changed
        # Exercise bounded watcher bookkeeping with more distinct paths than its cache.
        generation = call("capabilities")["result"]["refreshStats"]["invalidationGeneration"]
        for index in range(4200):
            (root / f"event-{index}.txt").write_text("event")
        deadline = time.monotonic() + 10
        while call("capabilities")["result"]["refreshStats"]["invalidationGeneration"] <= generation and time.monotonic() < deadline:
            time.sleep(0.05)
        assert call("capabilities")["result"]["refreshStats"]["invalidationGeneration"] > generation, "watcher cache overflow did not invalidate"
        before = call("capabilities")["result"]["refreshStats"]["bytesRead"]
        assert "result" in call("definition", file="Use.cs", line=0, character=use.index("Value"))
        after = call("capabilities")["result"]["refreshStats"]["bytesRead"]
        assert after - before == sum(sizes.values()), (before, after, sizes)
        # Periodic content revalidation bounds missed/delayed watcher notifications.
        dependency = root / "Large1.cs"
        stamp = dependency.stat()
        dependency.write_bytes(dependency.read_bytes().replace(b"Value =>", b"Other =>", 1))
        os.utime(dependency, ns=(stamp.st_atime_ns, stamp.st_mtime_ns))
        time.sleep(5.1)
        before = call("capabilities")["result"]["refreshStats"]["bytesRead"]
        diagnostics = call("diagnostics", file="Use.cs")["result"]
        assert len(diagnostics) == 1 and diagnostics[0]["code"] == "CS0117", diagnostics
        assert "Value" in diagnostics[0]["message"], diagnostics
        after = call("capabilities")["result"]["refreshStats"]["bytesRead"]
        assert after - before == sum(sizes.values()), (before, after, sizes)
        print(json.dumps({"fixture": "roslyn-large-source", "bytes": sum(sizes.values()), "largestFileBytes": max(sizes.values()), "openSeconds": round(opened_seconds, 3), "checksIncludingFallbackWaitSeconds": round(time.monotonic()-queried, 3)}))
    with tempfile.TemporaryDirectory(prefix="freeflight-roslyn-structure-") as folder:
        root = pathlib.Path(folder).resolve()
        usage = "class Use { public int Read() => Target.Value; }"
        dependency_source = "class Target { public static int Value => 42; }"
        (root / "Use.cs").write_text(usage)
        dependency = root / "Target.cs"
        dependency.write_text(dependency_source)
        assert call("open", root=str(root))["result"]["files"] == 2
        def target_definition():
            return call("definition", file="Use.cs", line=0, character=usage.index("Value"))["result"]
        assert target_definition()[0]["file"] == str(dependency)
        moved = root / "Moved.cs"
        dependency.rename(moved)
        found = target_definition()
        assert len(found) == 1 and found[0]["file"] == str(moved), found
        assert found[0]["range"]["start"] == dict(line=0, character=dependency_source.index("Value")), found
        moved.unlink()
        diagnostics = call("diagnostics", file="Use.cs")["result"]
        assert len(diagnostics) == 1 and diagnostics[0]["code"] == "CS0103", diagnostics
        added = root / "Added.cs"
        added.write_text(dependency_source)
        found = target_definition()
        assert len(found) == 1 and found[0]["file"] == str(added), found
        assert call("diagnostics", file="Use.cs")["result"] == []
        stamp = added.stat()
        added.write_text(dependency_source.replace("Value", "Other"))
        os.utime(added, ns=(stamp.st_atime_ns, stamp.st_mtime_ns))
        # Explicit worker reopen (MCP workspace.close then workspace.open) reloads
        # all content, independently of event delivery or preserved metadata.
        assert call("open", root=str(root))["result"]["files"] == 2
        diagnostics = call("diagnostics", file="Use.cs")["result"]
        assert len(diagnostics) == 1 and diagnostics[0]["code"] == "CS0117", diagnostics
        assert "Value" in diagnostics[0]["message"], diagnostics
        print("Roslyn source add/remove/rename and preserved-metadata dependency reload passed")
    with tempfile.TemporaryDirectory(prefix="freeflight-roslyn-policy-") as folder:
        root = pathlib.Path(folder).resolve()
        sample = root / "Boundary.cs"
        sample.write_bytes(b"class Boundary {}" + b" " * (1024 - len(b"class Boundary {}")))
        policy = dict(maxFileBytes=1024, maxWorkspaceBytes=2048, maxFiles=2, maxDirectoryEntries=2)
        assert "result" in call("open", root=str(root), resources=policy)
        assert "error" in call("symbols", file="Boundary.cs", resources=policy)
        sample.write_bytes(sample.read_bytes() + b" ")
        rejected = call("symbols", file="Boundary.cs")["error"]
        assert rejected["code"] == "resource_limit_exceeded" and rejected["resource"] == "maxFileBytes", rejected
        assert rejected["path"] == "Boundary.cs" and rejected["observed"] == 1025 and rejected["limit"] == 1024, rejected
        assert "resources.maxFileBytes" in rejected["remediation"]
        sample.write_bytes(sample.read_bytes()[:-1])
        assert call("symbols", file="Boundary.cs")["result"][0]["name"] == "Boundary"
        (root / "Second.cs").write_bytes(b"class Second { Boundary field; }" + b" " * (1024 - len(b"class Second { Boundary field; }")))
        assert "result" in call("open", root=str(root), resources=policy)
        second = root / "Second.cs"
        stamp = second.stat()
        second.write_bytes(second.read_bytes()[:-2] + b"//")
        os.utime(second, ns=(stamp.st_atime_ns, stamp.st_mtime_ns))
        preview = call("rename", file="Boundary.cs", line=0, character=6, newName="Renamed")["result"]
        second_edit = next(edit for edit in preview["edits"] if pathlib.Path(edit["file"]).name == "Second.cs")
        assert second_edit["expectedSha256"] == hashlib.sha256(second.read_bytes()).hexdigest(), second_edit
        low_total = dict(policy, maxWorkspaceBytes=2047)
        rejected = call("open", root=str(root), resources=low_total)["error"]
        assert rejected["resource"] == "maxWorkspaceBytes" and rejected["observed"] == 2048 and rejected["limit"] == 2047, rejected
        assert rejected["path"] in ("Boundary.cs", "Second.cs")
        rejected = call("open", root=str(root), resources=dict(policy, maxFiles=1))["error"]
        assert rejected["resource"] == "maxFiles" and rejected["observed"] == 2, rejected
        rejected = call("open", root=str(root), resources=dict(policy, maxDirectoryEntries=1))["error"]
        assert rejected["resource"] == "maxDirectoryEntries" and rejected["observed"] == 2, rejected
        for invalid in (None, [], {"unknown": 1}, {"maxFiles": True}, {"maxFiles": 1.5}, {"maxFiles": 0}, {"maxFileBytes": 268435457}, {"maxWorkspaceBytes": 2147483649}, {"maxFileBytes": 2049, "maxWorkspaceBytes": 2048}):
            assert "error" in call("open", root=str(root), resources=invalid), invalid
        assert "result" in call("open", root=str(root), resources=policy), "failed open must allow recovery"

    print("Roslyn semantic navigation, implementations, types, signatures, hierarchies, limits, preview, refresh, boundary, no-MSBuild, malformed input, and cancellation checks passed")
finally:
    process.stdin.close()
    assert process.wait(timeout=15) == 0, "worker failed during EOF shutdown"

# Invalid raw UTF-8 is rejected deterministically instead of silently decoding as ACP
# or replacement characters. A decoding failure closes this worker stream safely.
for malformed_bytes in (b'{"id":"\xff","method":"capabilities"}\n', b'{"id":"\xe2\x82'):
    result = subprocess.run(command, input=malformed_bytes, stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE, timeout=15, check=True)
    assert not result.stdout.startswith(b'\xef\xbb\xbf'), 'Worker emitted a UTF-8 BOM'
    reply = json.loads(result.stdout.decode('utf-8', errors='strict'))
    assert reply == {"id": None, "error": {"message": "Invalid UTF-8 input"}}, reply
print("Roslyn raw UTF-8 filename/symbol semantics and strict invalid/truncated UTF-8 rejection passed")
