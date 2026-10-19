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
        self.root = pathlib.Path(self.directory.name).resolve()
        self.config = self.root / "configuration.json"
        self.config.write_text(json.dumps({"roots": [str(self.root)], "engines": {}}))
        self.process = subprocess.Popen([BINARY, "--config", str(self.config)],
                                        stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                        stderr=subprocess.PIPE, text=True)
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
        self.process.stdin.write(json.dumps(message) + "\n")
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

    def test_project_discovery(self):
        (self.root / "tsconfig.json").write_text("{}")
        result = self.call("tools/call", {"name": "workspace.discover"})["result"]
        self.assertFalse(result["isError"])
        self.assertEqual(result["structuredContent"]["workspaces"][0]["projects"],
                         [str(self.root / "tsconfig.json")])

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
        worker.write_text("import sys,json,time\nfor line in sys.stdin:\n"
                          " request=json.loads(line)\n time.sleep(10)\n"
                          " print(json.dumps({'id':request['id'],'result':{}}),flush=True)\n")
        self.config.write_text(json.dumps({"roots": [str(self.root)], "engines": {
            "slow": [sys.executable, str(worker)]}}))
        self.process = subprocess.Popen([BINARY, "--config", str(self.config)],
                                        stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                        stderr=subprocess.PIPE, text=True)
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
