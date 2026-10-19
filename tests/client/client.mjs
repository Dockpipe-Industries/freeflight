import assert from "node:assert/strict";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { Client } from "@modelcontextprotocol/sdk/client/index.js";
import { StdioClientTransport } from "@modelcontextprotocol/sdk/client/stdio.js";

const repo = process.cwd();
const temporary = fs.mkdtempSync(path.join(os.tmpdir(), "freeflight-client-"));
const root = fs.realpathSync(temporary);
const config = path.join(root, "freeflight.json");
fs.writeFileSync(config, JSON.stringify({ roots: [root], engines: {} }));
const binary = process.platform === "win32"
  ? path.join(repo, "bin/.local/build/Release/freeflight.exe")
  : path.join(repo, "bin/.local/build/freeflight");
const client = new Client({ name: "freeflight-compatibility", version: "0.1.0" });
try {
  await client.connect(new StdioClientTransport({ command: binary, args: ["--config", config] }));
  const listed = await client.listTools();
  assert.deepEqual(listed.tools.map(tool => tool.name),
    ["workspace.discover", "engine.capabilities", "semantic.query"]);
  const called = await client.callTool({ name: "workspace.discover", arguments: {} });
  assert.equal(called.isError, false);
  assert.equal(called.structuredContent.workspaces[0].root, root);
  console.log("Official MCP SDK client initialized, discovered and invoked FreeFlight");
} finally {
  await client.close();
  fs.rmSync(root, { recursive: true });
}
