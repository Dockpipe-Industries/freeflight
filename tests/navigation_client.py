"""Shared black-box MCP client for local navigation fixtures."""
from contextlib import contextmanager
import json
import os
from pathlib import Path
from queue import Queue
import subprocess
from threading import Thread

REPO = Path(__file__).resolve().parents[1]
GENERATED = REPO / "bin/.local"
META = {"io.modelcontextprotocol/protocolVersion": "2026-07-28",
        "io.modelcontextprotocol/clientCapabilities": {}}


class Client:
    def __init__(self, process):
        self.process = process
        self.sequence = 0
        self.replies = Queue()
        Thread(target=self._read, daemon=True).start()

    def _read(self):
        for line in self.process.stdout:
            self.replies.put(line)
        self.replies.put(None)

    def tool(self, name, **arguments):
        self.sequence += 1
        request = {"jsonrpc": "2.0", "id": self.sequence, "method": "tools/call",
                   "params": {"name": name, "arguments": arguments, "_meta": META}}
        self.process.stdin.write(json.dumps(request) + "\n")
        self.process.stdin.flush()
        line = self.replies.get(timeout=40)
        assert line, "MCP closed without a reply"
        reply = json.loads(line)
        assert reply.get("id") == self.sequence and "result" in reply, reply
        return reply["result"]

    def ok(self, name, **arguments):
        result = self.tool(name, **arguments)
        assert not result.get("isError"), result
        return result["structuredContent"]

    def query(self, root, operation, **arguments):
        return self.ok("semantic.query", language="go", root=str(root),
                       operation=operation, arguments=arguments)


def executable():
    standard = GENERATED / ("build/Release/freeflight.exe" if os.name == "nt" else "build/freeflight")
    return os.environ.get("FREEFLIGHT_NAVIGATION_BINARY", os.environ.get("FREEFLIGHT_GO_BINARY", str(standard)))


@contextmanager
def server(directory, roots, trusted, command, language="go"):
    config = directory / "server.json"
    config.write_text(json.dumps({"roots": list(map(str, roots)), "trustedRoots": list(map(str, trusted)),
                                  "engines": {language: command} if command else {}}), encoding="utf-8")
    with subprocess.Popen([executable(), "--config", str(config)], stdin=subprocess.PIPE,
                          stdout=subprocess.PIPE, text=True, encoding="utf-8") as process:
        try:
            yield Client(process)
        finally:
            process.stdin.close()
            try:
                assert process.wait(timeout=5) == 0
            except subprocess.TimeoutExpired:
                process.kill()
                raise
