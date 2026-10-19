"""Black-box MCP framing, versioning, validation and workspace security tests."""
import json
import pathlib
import subprocess
import sys
import tempfile
import time
import unittest

BINARY = str(pathlib.Path(sys.argv.pop(1)).resolve())
META = {"io.modelcontextprotocol/protocolVersion": "2026-07-28",
        "io.modelcontextprotocol/clientCapabilities": {}}


class ProtocolTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.root = pathlib.Path(self.directory.name).resolve() / "workspace José-日本語"
        self.root.mkdir()
        self.config = self.root / "configuration-日本語.json"
        self.config.write_text(json.dumps({"roots": [str(self.root)], "engines": {}}))
        self.process = subprocess.Popen([BINARY, "--config", str(self.config)],
                                        stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                        stderr=subprocess.PIPE, text=True, encoding="utf-8")
        self.sequence = 0

    def tearDown(self):
        self.process.stdin.close()
        self.process.wait(timeout=5)
        errors = self.process.stderr.read()
        self.process.stdout.close()
        self.process.stderr.close()
        self.assertEqual(self.process.returncode, 0, errors)
        self.directory.cleanup()

    def call(self, method, params=None, modern=True):
        self.sequence += 1
        params = dict(params or {})
        if modern:
            params["_meta"] = META
        message = {"jsonrpc": "2.0", "id": self.sequence, "method": method, "params": params}
        self.process.stdin.write(json.dumps(message, ensure_ascii=False) + "\n")
        self.process.stdin.flush()
        result = json.loads(self.process.stdout.readline())
        self.assertEqual(result["id"], self.sequence)
        return result

    def test_modern_discovery_and_tools(self):
        result = self.call("server/discover")["result"]
        self.assertEqual(result["resultType"], "complete")
        self.assertEqual(result["supportedVersions"], ["2026-07-28"])
        tools = self.call("tools/list")["result"]["tools"]
        self.assertEqual([tool["name"] for tool in tools],
                         ["workspace.discover", "engine.capabilities", "semantic.query"])
        self.assertTrue(all(tool["annotations"]["readOnlyHint"] for tool in tools))

    def test_legacy_initialization(self):
        self.assertIn("error", self.call("tools/list", modern=False))
        result = self.call("initialize", {"protocolVersion": "2025-11-25",
                                         "capabilities": {},
                                         "clientInfo": {"name": "test", "version": "1"}}, False)
        self.assertEqual(result["result"]["protocolVersion"], "2025-11-25")
        self.process.stdin.write('{"jsonrpc":"2.0","method":"notifications/initialized"}\n')
        self.process.stdin.flush()
        self.assertIn("tools", self.call("tools/list", modern=False)["result"])

    def test_bad_version_and_missing_metadata(self):
        response = self.call("server/discover", {"_meta": {**META,
                             "io.modelcontextprotocol/protocolVersion": "2099-01-01"}}, False)
        self.assertEqual(response["error"]["code"], -32022)
        self.assertEqual(self.call("server/discover", modern=False)["error"]["code"], -32602)

    def test_parse_recovery(self):
        self.process.stdin.write("{broken\n")
        self.process.stdin.flush()
        self.assertEqual(json.loads(self.process.stdout.readline())["error"]["code"], -32700)
        self.assertIn("result", self.call("ping"))

    def test_nesting_limit_and_recovery(self):
        for opening, closing in (("[", "]"), ('{"value":', '}')):
            # Construct text directly: Python's encoder also has recursion limits.
            self.process.stdin.write(opening * 10000 + "0" + closing * 10000 + "\n")
            self.process.stdin.flush()
            response = json.loads(self.process.stdout.readline())
            self.assertEqual(response["error"]["code"], -32700)
            self.assertIsNone(response["id"])
            self.assertIn("result", self.call("ping"))
        # Root and params count toward the 128-container budget.
        allowed = '[' * 126 + '0' + ']' * 126
        self.process.stdin.write('{"jsonrpc":"2.0","id":99,"method":"ping",'
                                 '"params":{"value":' + allowed + '}}\n')
        self.process.stdin.flush()
        self.assertIn("result", json.loads(self.process.stdout.readline()))

    def test_project_discovery(self):
        (self.root / "tsconfig.json").write_text("{}")
        (self.root / "example.ts").write_text("export const value = 1")
        (self.root / "example.cs").write_text("class Example {}")
        (self.root / "example.mjs").write_text("export const value = 1")
        ignored = self.root / "node_modules"
        ignored.mkdir()
        (ignored / "hidden.csproj").write_text("<Project />")
        result = self.call("tools/call", {"name": "workspace.discover"})["result"]
        self.assertFalse(result["isError"])
        self.assertEqual(result["structuredContent"]["workspaces"][0]["projects"],
                         [str(self.root / "tsconfig.json")])
        self.assertEqual(result["structuredContent"]["workspaces"][0]["languages"],
                         ["csharp", "javascript", "typescript"])

    def test_unicode_paths_reach_worker_unchanged(self):
        self.process.stdin.close()
        self.process.wait(timeout=5)
        self.process.stdout.close()
        self.process.stderr.close()
        document = self.root / "document-été-日本語.ts"
        document.write_text("export const value = 1", encoding="utf-8")
        project = self.root / "projet-日本語.csproj"
        project.write_text("<Project />", encoding="utf-8")
        worker = self.root / "worker-日本語.py"
        worker.write_text("import sys,json\nfor line in sys.stdin.buffer:\n"
                          " request=json.loads(line)\n"
                          " result={'operations':['echo']} if request['method']=='capabilities' else request['params']\n"
                          " print(json.dumps({'id':request['id'],'result':result}),flush=True)\n",
                          encoding="utf-8")
        self.config.write_text(json.dumps({"roots": [str(self.root)], "engines": {
            "fixture": [sys.executable, str(worker)]}}), encoding="utf-8")
        self.process = subprocess.Popen([BINARY, "--config", str(self.config)],
                                        stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                        stderr=subprocess.PIPE, text=True, encoding="utf-8")
        discovered = self.call("tools/call", {"name": "workspace.discover"})["result"]
        workspace = discovered["structuredContent"]["workspaces"][0]
        self.assertEqual(workspace["root"], str(self.root))
        self.assertIn(str(project), workspace["projects"])
        response = self.call("tools/call", {"name": "semantic.query", "arguments": {
            "root": str(self.root), "language": "fixture", "operation": "echo",
            "arguments": {"file": str(document)}}})["result"]
        self.assertFalse(response["isError"], response)
        self.assertEqual(response["structuredContent"]["root"], str(self.root))
        self.assertEqual(response["structuredContent"]["file"], str(document))

    def test_outside_root(self):
        result = self.call("tools/call", {"name": "engine.capabilities",
            "arguments": {"root": str(self.root.parent), "language": "typescript"}})["result"]
        self.assertTrue(result["isError"])
        self.assertIn("outside", result["content"][0]["text"])

    def test_unknown_tools(self):
        self.assertEqual(self.call("tools/call", {"name": "invented"})["error"]["code"], -32602)
        self.assertEqual(self.call("invented")["error"]["code"], -32601)

    def test_inflight_cancellation_keeps_protocol_responsive(self):
        self.process.stdin.close()
        self.process.wait(timeout=5)
        self.process.stdout.close()
        self.process.stderr.close()
        worker = self.root / "slow.py"
        worker.write_text("import sys,json,time\nfor line in sys.stdin.buffer:\n"
                          " request=json.loads(line)\n time.sleep(10)\n"
                          " print(json.dumps({'id':request['id'],'result':{}}),flush=True)\n")
        self.config.write_text(json.dumps({"roots": [str(self.root)], "engines": {
            "slow": [sys.executable, str(worker)]}}))
        self.process = subprocess.Popen([BINARY, "--config", str(self.config)],
                                        stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                        stderr=subprocess.PIPE, text=True, encoding="utf-8")
        messages = [
            {"jsonrpc": "2.0", "id": "cancel-me", "method": "tools/call", "params": {
                "_meta": META, "name": "engine.capabilities",
                "arguments": {"root": str(self.root), "language": "slow"}}},
            {"jsonrpc": "2.0", "method": "notifications/cancelled", "params": {"requestId": "cancel-me"}},
        ]
        for message in messages:
            self.process.stdin.write(json.dumps(message) + "\n")
        self.process.stdin.flush()
        started = time.monotonic()
        self.assertIn("result", self.call("ping"))
        self.assertLess(time.monotonic() - started, 3)
        # Another call must complete without any queued response for cancel-me.
        result = self.call("tools/call", {"name": "workspace.discover"})
        self.assertFalse(result["result"]["isError"])


if __name__ == "__main__":
    unittest.main()
