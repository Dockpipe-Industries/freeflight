"""Exercise real worker semantics through the single compiled MCP endpoint."""
import json
import pathlib
import shutil
import subprocess
import tempfile
import time
import statistics

repo = pathlib.Path(__file__).resolve().parents[1]
binary = repo / "bin/.local/build/freeflight"
if not binary.exists():
    binary = repo / "bin/.local/build/Release/freeflight.exe"
worker = repo / "bin/.local/roslyn/bin/FreeFlight.Roslyn/debug/FreeFlight.Roslyn.dll"
node = shutil.which("node")
dotnet = shutil.which("dotnet")
assert node and dotnet, "Node and .NET SDK must be provisioned"
meta = {"io.modelcontextprotocol/protocolVersion": "2026-07-28",
        "io.modelcontextprotocol/clientCapabilities": {}}
with tempfile.TemporaryDirectory(prefix="freeflight-integration-") as directory:
    root = pathlib.Path(directory).resolve()
    ts = root / "sample.ts"
    ts.write_text("export const answer: number = 42;\nexport const result = answer;\n")
    cs = root / "Sample.cs"
    cs.write_text("public class Sample { public int Answer = 42; public int Read() => Answer; }\n")
    (root / "tsconfig.json").write_text('{"compilerOptions":{"strict":true},"include":["*.ts"]}')
    config = root / "freeflight.json"
    config.write_text(json.dumps({"roots": [str(root)], "engines": {
        "typescript": [node, str(repo / "bin/.local/typescript/worker.mjs")],
        "csharp": [dotnet, str(worker)]}}))
    started = time.perf_counter()
    process = subprocess.Popen([str(binary), "--config", str(config)], text=True,
                               stdin=subprocess.PIPE, stdout=subprocess.PIPE)
    sequence = 0
    measurements = {}

    def request(method, params):
        global sequence
        sequence += 1
        process.stdin.write(json.dumps({"jsonrpc": "2.0", "id": sequence,
            "method": method, "params": {**params, "_meta": meta}}) + "\n")
        process.stdin.flush()
        response = json.loads(process.stdout.readline())
        assert response["id"] == sequence, response
        assert "error" not in response, response
        assert not response["result"].get("isError"), response
        return response["result"]

    def query(language, operation, **arguments):
        before = time.perf_counter()
        value = request("tools/call", {"name": "semantic.query", "arguments": {
            "root": str(root), "language": language, "operation": operation,
            "arguments": arguments}})["structuredContent"]
        measurements.setdefault(language + "." + operation, []).append((time.perf_counter() - before) * 1000)
        return value.get("items", value)

    try:
        request("server/discover", {})
        measurements["startup.discovery"] = [(time.perf_counter() - started) * 1000]
        for language in ["typescript", "csharp"]:
            caps = request("tools/call", {"name": "engine.capabilities", "arguments": {
                "root": str(root), "language": language}})["structuredContent"]
            assert {"definition", "references", "diagnostics"} <= set(caps["operations"])
        ts_def = query("typescript", "definition", file=str(ts), line=1, character=23)
        assert ts_def[0]["range"]["start"]["line"] == 0, ts_def
        assert len(query("typescript", "references", file=str(ts), line=0, character=14)) == 2
        assert query("typescript", "diagnostics", file=str(ts)) == []
        csharp = query("csharp", "definition", file=str(cs), line=0, character=cs.read_text().rindex("Answer") + 1)
        assert csharp[0]["range"]["start"]["character"] == 33, csharp
        assert len(query("csharp", "references", file=str(cs), line=0, character=34)) == 1
        assert query("csharp", "diagnostics", file=str(cs)) == []
        for language, file in [("typescript", ts), ("csharp", cs)]:
            for _ in range(5):
                assert query(language, "diagnostics", file=str(file)) == []
                query(language, "symbols", file=str(file))
        ts.write_text(ts.read_text().replace("42", '"wrong"'))
        diagnostics = query("typescript", "diagnostics", file=str(ts))
        assert any(item["code"] == 2322 for item in diagnostics), diagnostics
        report = {key: {"samples": len(values), "median_ms": round(statistics.median(values), 3),
                        "max_ms": round(max(values), 3)} for key, values in measurements.items()}
        output = repo / "bin/.local/reports"
        output.mkdir(parents=True, exist_ok=True)
        (output / "latency.json").write_text(json.dumps({"fixture": "two tiny source files; warm engine",
            "excludes": ["large repository", "project evaluation", "RSS"], "measurements": report}, indent=2) + "\n")
        print("C++ MCP -> real TS/Roslyn semantic assertions passed")
        print(json.dumps(report, indent=2))
    finally:
        process.stdin.close()
        process.wait(timeout=10)
        process.stdout.close()
        assert process.returncode == 0
