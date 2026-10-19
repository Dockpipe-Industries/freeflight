import assert from "node:assert/strict";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { Client } from "@modelcontextprotocol/sdk/client/index.js";
import { StdioClientTransport } from "@modelcontextprotocol/sdk/client/stdio.js";

const repo = process.cwd();
const temporary = fs.mkdtempSync(path.join(os.tmpdir(), "freeflight client é 测试-"));
const root = fs.realpathSync.native(temporary);
const config = path.join(root, "freeflight.json");
fs.writeFileSync(config, JSON.stringify({ roots: [root], engines: {} }));
const packaged = Boolean(process.env.FREEFLIGHT_BINARY);
const binary = process.env.FREEFLIGHT_BINARY ?? (process.platform === "win32"
  ? path.join(repo, "bin/.local/build/Release/freeflight.exe")
  : path.join(repo, "bin/.local/build/freeflight"));
if (packaged) {
  fs.writeFileSync(path.join(root, "tsconfig.json"), JSON.stringify({
    compilerOptions: { strict: true, allowJs: true, checkJs: true }, include: ["*.ts", "*.js"],
  }));
  fs.writeFileSync(path.join(root, "sample.ts"),
    "export const answer: number = 42;\nexport const result = answer;\nexport const wrong: string = 42;\n");
  fs.writeFileSync(path.join(root, "sample.js"), "export function increment(value) { return value + 1; }\n");
  fs.writeFileSync(path.join(root, "Sample.cs"), 'public class Widget { public int Count = "wrong"; }\n');
}
const client = new Client({ name: "freeflight-compatibility", version: "0.1.0" });
const transport = new StdioClientTransport({ command: binary,
  args: packaged ? ["--workspace", root] : ["--config", config] });
try {
  await client.connect(transport);
  const listed = await client.listTools();
  assert.deepEqual(listed.tools.map(tool => tool.name),
    ["workspace.discover", "engine.capabilities", "semantic.query"]);
  const called = await client.callTool({ name: "workspace.discover", arguments: {} });
  assert.equal(called.isError, false);
  // Native canonicalization expands Windows 8.3 aliases as the C++ core does.
  // Compare exact canonical directories, not raw spellings or basenames.
  assert.equal(fs.realpathSync.native(called.structuredContent.workspaces[0].root), root);
  if (packaged) {
    async function call(name, args) {
      const response = await client.callTool({ name, arguments: { root, ...args } });
      assert.equal(response.isError, false, JSON.stringify(response));
      return response.structuredContent;
    }
    async function query(language, operation, file, position = {}) {
      const response = await call("semantic.query", { language, operation,
        arguments: { file: path.join(root, file), ...position } });
      return response.items;
    }
    for (const language of ["typescript", "javascript", "csharp"]) {
      const capabilities = await call("engine.capabilities", { language });
      for (const operation of ["definition", "references", "diagnostics", "symbols"]) {
        assert.ok(capabilities.operations.includes(operation), `${language}: ${operation}`);
      }
    }
    const definitions = await query("typescript", "definition", "sample.ts", { line: 1, character: 23 });
    assert.equal(definitions.length, 1);
    assert.deepEqual(definitions[0].range, { start: { line: 0, character: 13 }, end: { line: 0, character: 19 } });
    assert.equal((await query("typescript", "references", "sample.ts", { line: 0, character: 14 })).length, 2);
    const tsDiagnostics = await query("typescript", "diagnostics", "sample.ts");
    assert.deepEqual(tsDiagnostics.map(item => String(item.code)), ["2322"]);
    assert.equal(tsDiagnostics[0].range.start.line, 2);
    assert.ok((await query("javascript", "symbols", "sample.js")).some(item => item.name === "increment"));
    const csDiagnostics = await query("csharp", "diagnostics", "Sample.cs");
    assert.deepEqual(csDiagnostics.map(item => item.code), ["CS0029"]);
    assert.ok((await query("csharp", "symbols", "Sample.cs")).some(item => item.name === "Widget"));
    console.log("Official MCP SDK verified packaged TS definition/references/diagnostics, JS symbol, C# diagnostics/symbol and engine capabilities");
  }
  console.log("Official MCP SDK client initialized, discovered and invoked FreeFlight");
} finally {
  await client.close();
  fs.rmSync(root, { recursive: true });
}
