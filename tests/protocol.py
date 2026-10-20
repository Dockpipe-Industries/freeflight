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
                         ["workspace.discover", "workspace.list", "workspace.open", "workspace.close",
                          "workspace.clientRoots", "engine.capabilities", "semantic.query"])
        self.assertTrue(tools[0]["annotations"]["readOnlyHint"])
        self.assertFalse(tools[2]["annotations"]["readOnlyHint"])

    def test_resource_configuration_validation(self):
        for policy in ([], None, {"maxFileBytes": 0}, {"maxFileBytes": True},
                       {"maxFileBytes": 1.5}, {"maxFileBytes": "32"},
                       {"maxWorkspaceBytes": 2147483649}, {"maxFiles": -1},
                       {"maxDirectoryEntries": 2000001}, {"unknown": 1},
                       {"maxFileBytes": 100, "maxWorkspaceBytes": 99}):
            config = self.root / "invalid.json"
            config.write_text(json.dumps({"roots": [], "engines": {}, "resources": policy}))
            result = subprocess.run([BINARY, "--config", str(config)], input="",
                                    capture_output=True, text=True, timeout=5)
            self.assertNotEqual(result.returncode, 0, policy)
            self.assertEqual(result.stdout, "")

    def test_operator_resource_forwarding_and_structured_failure(self):
        worker = self.root / "resource_worker.py"
        worker.write_text('''import json, sys
policy = None
for line in sys.stdin:
    request = json.loads(line)
    method = request['method']
    if method == 'capabilities': result = {'operations': ['inspect', 'fail']}
    elif method == 'open':
        policy = request['params']['resources']
        result = {}
    elif method == 'fail':
        print(json.dumps({'id': request['id'], 'error': {
            'code': 'resource_limit_exceeded', 'message': 'Source budget exceeded',
            'resource': 'maxFileBytes', 'path': 'Generated.cs', 'observed': 1025,
            'limit': policy['maxFileBytes'], 'remediation': 'Adjust operator configuration'}}), flush=True)
        continue
    else: result = policy
    print(json.dumps({'id': request['id'], 'result': result}), flush=True)
''')
        self.config.write_text(json.dumps({"roots": [str(self.root)],
            "resources": {"maxFileBytes": 1024},
            "engines": {"fixture": [sys.executable, str(worker)]}}))
        self.restart(["--config", str(self.config)])
        def query(operation, arguments=None):
            return self.tool("semantic.query", {"root": str(self.root), "language": "fixture",
                "operation": operation, "arguments": arguments or {}})
        self.assertEqual(query("inspect")["structuredContent"], {
            "maxFileBytes": 1024, "maxWorkspaceBytes": 536870912,
            "maxFiles": 50000, "maxDirectoryEntries": 500000})
        self.assertTrue(query("inspect", {"resources": {"maxFileBytes": 9999}})["isError"])
        failed = query("fail")
        self.assertTrue(failed["isError"])
        error = failed["structuredContent"]["error"]
        self.assertEqual(error["code"], "resource_limit_exceeded")
        self.assertEqual((error["path"], error["observed"], error["limit"]),
                         ("Generated.cs", 1025, 1024))
        self.assertEqual(query("inspect")["structuredContent"]["maxFileBytes"], 1024)

    def restart(self, args, cwd=None):
        self.process.stdin.close()
        self.process.wait(timeout=5)
        self.process.stdout.close()
        self.process.stderr.close()
        self.process = subprocess.Popen([BINARY, *args], cwd=cwd,
                                        stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                        stderr=subprocess.PIPE, text=True, encoding="utf-8")

    def tool(self, name, arguments=None):
        return self.call("tools/call", {"name": name, "arguments": arguments or {}})["result"]

    def roots(self, roots):
        return self.call("tools/call", {"name": "workspace.clientRoots", "_meta": {
            **META, "io.modelcontextprotocol/clientCapabilities": {"roots": {}}},
            "inputResponses": {"roots": {"roots": roots}}}, modern=False)

    def test_no_arguments_are_dormant_and_do_not_load_cwd(self):
        (self.root / "tsconfig.json").write_text('{broken untrusted config')
        (self.root / "freeflight.json").write_text('{broken untrusted config')
        self.restart([], cwd=self.root)
        listed = self.tool("workspace.list")["structuredContent"]
        self.assertEqual(listed, {"allowedRoots": [], "workspaces": [], "candidates": [],
                                 "authorization": "startup-only", "dormant": True})
        self.assertEqual(self.tool("workspace.discover")["structuredContent"], {"workspaces": []})
        for root in (self.root, self.root / "missing-private-path"):
            denied = self.tool("workspace.open", {"root": str(root)})
            self.assertTrue(denied["isError"])
            self.assertIn("startup-authorized", denied["content"][0]["text"])
        response = self.roots([{"uri": self.root.as_uri(), "name": "Untrusted candidate"}])
        self.assertEqual(len(response["result"]["structuredContent"]["candidates"]), 1)
        self.assertTrue(self.tool("workspace.open", {"root": str(self.root),
                                                    "candidateUri": self.root.as_uri()})["isError"])
        self.assertTrue(self.tool("engine.capabilities", {"root": str(self.root), "language": "typescript"})["isError"])

    def test_workspace_switch_close_and_explicit_reopen(self):
        a, b = self.root / "a", self.root / "b"
        a.mkdir(); b.mkdir()
        worker = self.root / "lifecycle.py"
        worker.write_text("import json,sys,os\nsys.stdin.reconfigure(encoding='utf-8')\n"
                          "sys.stdout.reconfigure(encoding='utf-8')\nfor line in sys.stdin:\n"
                          " r=json.loads(line)\n"
                          " v={'operations':['identity']} if r['method']=='capabilities' else {'pid':os.getpid(),'root':r['params']['root']}\n"
                          " print(json.dumps({'id':r['id'],'result':v}),flush=True)\n")
        self.config.write_text(json.dumps({"roots": [str(self.root)],
                                           "engines": {"fixture": [sys.executable, str(worker)]}}))
        self.restart(["--config", str(self.config)])
        def query(root):
            return self.tool("semantic.query", {"root": str(root), "language": "fixture", "operation": "identity"})
        self.assertTrue(query(a)["isError"])
        for root in (a, b):
            self.assertEqual(self.tool("workspace.open", {"root": str(root)})["structuredContent"],
                             {"root": str(root), "active": True})
        first = query(a)["structuredContent"]
        other = query(b)["structuredContent"]
        self.assertEqual(first["root"], str(a))
        self.assertNotEqual(first["pid"], other["pid"])
        self.tool("workspace.close", {"root": str(a)})
        self.assertTrue(query(a)["isError"])
        self.assertEqual(query(b)["structuredContent"]["pid"], other["pid"])
        self.tool("workspace.open", {"root": str(a)})
        self.assertNotEqual(query(a)["structuredContent"]["pid"], first["pid"])
        self.tool("workspace.close", {"root": str(self.root)})
        listed = self.tool("workspace.list")["structuredContent"]
        self.assertEqual(listed["workspaces"], [])
        self.assertEqual(listed["allowedRoots"], [str(self.root)])
        self.assertFalse(self.tool("workspace.open", {"root": str(b)})["isError"])
        self.assertTrue(self.tool("workspace.open", {"root": str(self.root.parent)})["isError"])

    def test_modern_roots_discovery_and_candidate_revocation(self):
        child = self.root / "child-日本語"
        child.mkdir()
        unsupported = self.tool("workspace.clientRoots")
        self.assertEqual(unsupported["structuredContent"]["candidates"], [])
        result = self.call("tools/call", {"name": "workspace.clientRoots", "_meta": {
            **META, "io.modelcontextprotocol/clientCapabilities": {"roots": {}}}}, modern=False)["result"]
        self.assertEqual(result["resultType"], "input_required")
        self.assertEqual(result["inputRequests"], {"roots": {"method": "roots/list"}})
        self.assertNotIn("requestState", result)
        self.roots([{"uri": child.as_uri()}, {"uri": self.root.parent.as_uri()}])
        self.assertTrue(self.tool("workspace.open", {"root": str(self.root.parent),
                                                    "candidateUri": self.root.parent.as_uri()})["isError"])
        opened = self.tool("workspace.open", {"root": str(child), "candidateUri": child.as_uri()})
        self.assertFalse(opened["isError"])
        self.roots([])
        listed = self.tool("workspace.list")["structuredContent"]
        self.assertEqual(listed["workspaces"], [{"root": str(self.root)}])
        self.assertTrue(self.tool("engine.capabilities", {"root": str(child), "language": "fixture"})["isError"])
        self.assertFalse(self.tool("workspace.open", {"root": str(child)})["isError"])
        self.roots([])
        self.assertEqual(len(self.tool("workspace.list")["structuredContent"]["workspaces"]), 2)
        bad = self.call("tools/call", {"name": "workspace.clientRoots", "inputResponses": {"roots": {"roots": []}}})
        self.assertEqual(bad["error"]["code"], -32602)
        malformed = self.roots([{"uri": 123}])
        self.assertEqual(malformed["error"]["code"], -32602)
        self.assertEqual(self.roots([{"uri": child.as_uri()}] * 33)["error"]["code"], -32602)

    def test_candidate_uri_validation_never_grants_access(self):
        child = self.root / "child"
        child.mkdir()
        bad_uris = ["file://remote/child", "file://user@localhost/child", child.as_uri() + "?query",
                    child.as_uri() + "#fragment", child.as_uri() + "%ZZ", child.as_uri() + "%00",
                    child.as_uri() + "%2F", child.as_uri() + "%5C"]
        for uri in bad_uris:
            self.roots([{"uri": uri}])
            self.assertTrue(self.tool("workspace.open", {"root": str(child), "candidateUri": uri})["isError"], uri)
        # A symlink under an allowed root cannot escape the startup boundary.
        link = self.root / "escape"
        try:
            link.symlink_to(self.root.parent, target_is_directory=True)
        except OSError:
            return
        self.assertTrue(self.tool("workspace.open", {"root": str(link)})["isError"])

    def test_legacy_roots_changes_ignore_stale_responses(self):
        child = self.root / "candidate"
        child.mkdir()
        self.call("initialize", {"protocolVersion": "2025-11-25", "capabilities": {
            "roots": {"listChanged": True}}, "clientInfo": {"name": "roots-test", "version": "1"}}, modern=False)
        def send(value):
            self.process.stdin.write(json.dumps(value) + "\n")
            self.process.stdin.flush()
        send({"jsonrpc": "2.0", "method": "notifications/initialized"})
        requested = json.loads(self.process.stdout.readline())
        self.assertEqual(requested["method"], "roots/list")
        send({"jsonrpc": "2.0", "id": requested["id"], "result": {"roots": [{"uri": child.as_uri()}]}})
        self.assertEqual(len(self.tool("workspace.list")["structuredContent"]["candidates"]), 1)
        self.assertFalse(self.tool("workspace.open", {"root": str(child), "candidateUri": child.as_uri()})["isError"])
        send({"jsonrpc": "2.0", "method": "notifications/roots/list_changed"})
        stale = json.loads(self.process.stdout.readline())
        send({"jsonrpc": "2.0", "method": "notifications/roots/list_changed"})
        fresh = json.loads(self.process.stdout.readline())
        send({"jsonrpc": "2.0", "id": fresh["id"], "result": {"roots": []}})
        send({"jsonrpc": "2.0", "id": stale["id"], "result": {"roots": [{"uri": child.as_uri()}]}})
        listed = self.tool("workspace.list")["structuredContent"]
        self.assertEqual(listed["candidates"], [])
        self.assertEqual(listed["workspaces"], [{"root": str(self.root)}])

    def test_unresponsive_legacy_roots_never_block_or_retain_associations(self):
        child = self.root / "candidate"
        child.mkdir()
        self.call("initialize", {"protocolVersion": "2025-11-25", "capabilities": {
            "roots": {"listChanged": True}}, "clientInfo": {"name": "roots-test", "version": "1"}}, modern=False)
        def send(value):
            self.process.stdin.write(json.dumps(value) + "\n")
            self.process.stdin.flush()
        send({"jsonrpc": "2.0", "method": "notifications/initialized"})
        requested = json.loads(self.process.stdout.readline())
        # Other calls do not await a client roots answer.
        self.assertTrue(self.call("ping")["result"])
        send({"jsonrpc": "2.0", "id": requested["id"], "result": {"roots": [{"uri": child.as_uri()}]}})
        self.assertFalse(self.tool("workspace.open", {"root": str(child), "candidateUri": child.as_uri()})["isError"])
        send({"jsonrpc": "2.0", "method": "notifications/roots/list_changed"})
        refresh = json.loads(self.process.stdout.readline())
        listed = self.tool("workspace.list")["structuredContent"]
        self.assertEqual(listed["candidates"], [])
        self.assertEqual(listed["workspaces"], [{"root": str(self.root)}])
        send({"jsonrpc": "2.0", "id": refresh["id"], "result": {"roots": "malformed"}})
        self.assertEqual(self.tool("workspace.list")["structuredContent"]["candidates"], [])
        send({"jsonrpc": "2.0", "method": "notifications/roots/list_changed"})
        self.assertEqual(json.loads(self.process.stdout.readline())["method"], "roots/list")
        # tearDown closes stdin with this roots request unanswered; bounded EOF.

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

    def test_cancelled_queued_lifecycle_calls_have_no_side_effects(self):
        active, unopened = self.root / "active", self.root / "unopened"
        active.mkdir(); unopened.mkdir()
        ready, release = self.root / "ready", self.root / "release"
        worker = self.root / "controlled.py"
        worker.write_text("import sys,json,time,pathlib\n"
                          "sys.stdin.reconfigure(encoding='utf-8')\n"
                          "sys.stdout.reconfigure(encoding='utf-8')\n"
                          "ready,release=map(pathlib.Path,sys.argv[1:])\n"
                          "for line in sys.stdin:\n"
                          " r=json.loads(line)\n"
                          " if r['method']=='capabilities':\n"
                          "  ready.write_text('ready')\n"
                          "  while not release.exists(): time.sleep(.01)\n"
                          " print(json.dumps({'id':r['id'],'result':{'operations':[]}}),flush=True)\n")
        self.config.write_text(json.dumps({"roots": [str(self.root)], "engines": {
            "controlled": [sys.executable, str(worker), str(ready), str(release)]}}))
        self.restart(["--config", str(self.config)])
        self.roots([{"uri": active.as_uri()}])
        self.assertFalse(self.tool("workspace.open", {"root": str(active),
                                                     "candidateUri": active.as_uri()})["isError"])
        before = self.tool("workspace.list")["structuredContent"]
        def send(value):
            self.process.stdin.write(json.dumps(value) + "\n")
            self.process.stdin.flush()
        send({"jsonrpc": "2.0", "id": "blocker", "method": "tools/call", "params": {
            "_meta": META, "name": "engine.capabilities",
            "arguments": {"root": str(self.root), "language": "controlled"}}})
        deadline = time.monotonic() + 5
        while not ready.exists() and time.monotonic() < deadline:
            time.sleep(.01)
        self.assertTrue(ready.exists(), "controlled worker never started")
        # MRTR roots discovery must not bypass duplicate in-flight ID checks.
        send({"jsonrpc": "2.0", "id": "blocker", "method": "tools/call", "params": {
            "name": "workspace.clientRoots", "_meta": {
                **META, "io.modelcontextprotocol/clientCapabilities": {"roots": {}}}}})
        duplicate = json.loads(self.process.stdout.readline())
        self.assertEqual(duplicate["id"], "blocker")
        self.assertEqual(duplicate["error"]["code"], -32600)
        self.assertNotIn("result", duplicate)
        queued = [
            ("cancel-open", {"name": "workspace.open", "arguments": {"root": str(unopened)}}),
            ("cancel-close", {"name": "workspace.close", "arguments": {"root": str(active)}}),
            ("cancel-roots", {"name": "workspace.clientRoots", "inputResponses": {"roots": {"roots": []}}}),
        ]
        for identifier, params in queued:
            send({"jsonrpc": "2.0", "id": identifier, "method": "tools/call", "params": {
                **params, "_meta": {**META, "io.modelcontextprotocol/clientCapabilities": {"roots": {}}}}})
            send({"jsonrpc": "2.0", "method": "notifications/cancelled", "params": {"requestId": identifier}})
        # The reader's ping response proves all preceding cancellations were
        # accepted while the executor was still blocked inside the first worker.
        self.assertIn("result", self.call("ping"))
        release.write_text("release")
        self.assertEqual(json.loads(self.process.stdout.readline())["id"], "blocker")
        self.assertEqual(self.tool("workspace.list")["structuredContent"], before)
        for identifier, _ in queued:
            # No suppressed response leaked, and the pending-ID slot was erased.
            send({"jsonrpc": "2.0", "id": identifier, "method": "tools/call", "params": {
                "_meta": META, "name": "workspace.list"}})
            response = json.loads(self.process.stdout.readline())
            self.assertEqual(response["id"], identifier)
            self.assertEqual(response["result"]["structuredContent"], before)

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
