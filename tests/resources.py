"""Real-worker resource failures retain structured details across the MCP boundary."""
import json
import pathlib
import queue
import shutil
import subprocess
import tempfile
import threading

REPO = pathlib.Path(__file__).resolve().parents[1]
BINARY = REPO / "bin/.local/build/freeflight"
if not BINARY.exists():
    BINARY = REPO / "bin/.local/build/Release/freeflight.exe"
LIMIT = 4 * 1024 * 1024
META = {"io.modelcontextprotocol/protocolVersion": "2026-07-28",
        "io.modelcontextprotocol/clientCapabilities": {}}

with tempfile.TemporaryDirectory(prefix="freeflight-resource-contract-") as directory:
    root = pathlib.Path(directory).resolve()
    source = root / "source"
    source.mkdir()
    cs = source / "Generated.cs"
    ts = source / "generated.ts"
    cs.write_text("public class Generated { public int Value = 42; }\n")
    ts.write_text("export const value = 42;\n")
    (source / "tsconfig.json").write_text('{"include":["*.ts"]}')
    configuration = root / "operator.json"
    configuration.write_text(json.dumps({"roots": [str(source)],
        "resources": {"maxFileBytes": LIMIT, "maxWorkspaceBytes": 16 * 1024 * 1024},
        "engines": {
            "csharp": [shutil.which("dotnet"), str(REPO / "bin/.local/roslyn/bin/FreeFlight.Roslyn/debug/FreeFlight.Roslyn.dll")],
            "typescript": [shutil.which("node"), str(REPO / "bin/.local/typescript/worker.mjs")]
        }}))
    process = subprocess.Popen([str(BINARY), "--config", str(configuration)],
        stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        text=True, encoding="utf-8")
    replies = queue.Queue()
    reader = threading.Thread(target=lambda: [replies.put(line) for line in process.stdout], daemon=True)
    reader.start()
    sequence = 0

    def query(language, file):
        global sequence
        sequence += 1
        process.stdin.write(json.dumps({"jsonrpc": "2.0", "id": sequence,
            "method": "tools/call", "params": {"_meta": META, "name": "semantic.query",
                "arguments": {"root": str(source), "language": language,
                    "operation": "diagnostics", "arguments": {"file": str(file)}}}}) + "\n")
        process.stdin.flush()
        reply = json.loads(replies.get(timeout=30))
        assert reply["id"] == sequence and "error" not in reply, reply
        return reply["result"]

    try:
        for language, file in [("csharp", cs), ("typescript", ts)]:
            original = file.read_bytes()
            assert not query(language, file).get("isError")
            file.write_bytes(original + b" " * (LIMIT + 1 - len(original)))
            failure = query(language, file)
            assert failure["isError"], failure
            detail = failure["structuredContent"]["error"]
            assert detail["code"] == "resource_limit_exceeded", detail
            assert detail["resource"] == "maxFileBytes", detail
            assert detail["path"] == file.name, detail
            assert detail["observed"] == LIMIT + 1 and detail["limit"] == LIMIT, detail
            assert detail["remediation"], detail
            file.write_bytes(original)
            recovered = query(language, file)
            assert not recovered.get("isError") and recovered["structuredContent"]["items"] == [], recovered
        print("Real C#/TS MCP resource policy, structured failure and explicit retry recovery passed")
    finally:
        process.stdin.close()
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)
        reader.join(timeout=5)
        errors = process.stderr.read()
        process.stdout.close()
        process.stderr.close()
        assert process.returncode == 0, errors
