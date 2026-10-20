// SPDX-License-Identifier: Apache-2.0
import { test } from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { Worker, serve } from "../worker.mjs";

function fixture(t) {
  const root = fs.realpathSync(
    fs.mkdtempSync(path.join(os.tmpdir(), "freeflight-ts-")),
  );
  const worker = new Worker();
  t.after(() => {
    worker.close();
    fs.rmSync(root, { recursive: true, force: true });
  });
  fs.writeFileSync(
    path.join(root, "tsconfig.json"),
    JSON.stringify({
      compilerOptions: {
        strict: true,
        target: "es2022",
        allowJs: true,
        checkJs: true,
        plugins: [{ name: "./never-execute.js" }],
      },
      include: ["*.ts", "*.js"],
    }),
  );
  fs.writeFileSync(
    path.join(root, "never-execute.js"),
    'throw new Error("PLUGIN EXECUTED");',
  );
  fs.writeFileSync(
    path.join(root, "a.ts"),
    "export function add(left: number, right: number): number { return left + right; }\nexport const total = add(1, 2);\nconst wrong: string = 42;\n",
  );
  fs.writeFileSync(
    path.join(root, "b.ts"),
    'import { add } from "./a";\nexport const answer = add(3, 4);\n',
  );
  worker.open({ root });
  return { root, worker };
}
test("semantic symbols, definitions, references, diagnostics, hover and signature help", (t) => {
  const { worker } = fixture(t);
  assert.ok(
    worker
      .handle("symbols", { file: "a.ts" })
      .some((s) => s.name === "add" && s.kind === "function"),
  );
  const definition = worker.handle("definition", {
    file: "b.ts",
    line: 1,
    character: 23,
  });
  assert.equal(definition[0].name, "add");
  assert.equal(definition[0].range.start.line, 0);
  const refs = worker.handle("references", {
    file: "a.ts",
    line: 0,
    character: 17,
  });
  assert.equal(refs.length, 4);
  assert.match(
    worker.handle("hover", { file: "b.ts", line: 1, character: 23 }).display,
    /add\(left: number, right: number\): number/,
  );
  const diagnostic = worker
    .handle("diagnostics", { file: "a.ts" })
    .find((d) => d.code === 2322);
  assert.equal(diagnostic.range.start.line, 2);
  const sig = worker.handle("signatureHelp", {
    file: "b.ts",
    line: 1,
    character: 26,
  });
  assert.equal(sig.signatures[0].parameters[0].name, "left");
});
test("rename previews include content checksums and never modify files", (t) => {
  const { root, worker } = fixture(t),
    before = fs.readFileSync(path.join(root, "a.ts"), "utf8");
  const result = worker.handle("rename", {
    file: "a.ts",
    line: 0,
    character: 17,
    newName: "sum",
  });
  assert.equal(result.preview, true);
  assert.equal(result.edits.length, 4);
  assert.ok(
    result.edits.every(
      (e) =>
        /^[a-f0-9]{64}$/.test(e.expectedSha256) && e.newText.includes("sum"),
    ),
  );
  assert.equal(fs.readFileSync(path.join(root, "a.ts"), "utf8"), before);
  assert.throws(() =>
    worker.handle("rename", {
      file: "a.ts",
      line: 0,
      character: 17,
      newName: "class",
    }),
  );
});
test("incremental content updates refresh diagnostic results", (t) => {
  const { root, worker } = fixture(t);
  assert.ok(
    worker.handle("diagnostics", { file: "a.ts" }).some((d) => d.code === 2322),
  );
  const file = path.join(root, "a.ts");
  fs.writeFileSync(
    file,
    fs.readFileSync(file, "utf8").replace("wrong: string", "wrong: number"),
  );
  assert.ok(
    !worker
      .handle("diagnostics", { file: "a.ts" })
      .some((d) => d.code === 2322),
  );
});
test("workspace traversal, symlinks and invalid positions are rejected", (t) => {
  const { root, worker } = fixture(t);
  assert.throws(() => worker.handle("symbols", { file: "../outside.ts" }));
  // A real fixture target works on Windows as well as Unix; /etc/passwd does not.
  const external = fs.realpathSync(
    fs.mkdtempSync(path.join(os.tmpdir(), "freeflight-outside-")),
  );
  t.after(() => fs.rmSync(external, { recursive: true, force: true }));
  const target = path.join(external, "outside.ts");
  fs.writeFileSync(target, "export const forbidden = 1;\n");
  const link = path.join(root, "escape.ts");
  fs.symlinkSync(target, link, "file");
  assert.equal(fs.realpathSync(link), fs.realpathSync(target));
  assert.throws(
    () => worker.handle("symbols", { file: "escape.ts" }),
    /outside/,
  );
  assert.throws(() =>
    worker.handle("hover", { file: "a.ts", line: -1, character: 0 }),
  );
  assert.throws(() =>
    worker.handle("hover", { file: "a.ts", line: 99, character: 0 }),
  );
});
test("JavaScript uses JSDoc types and reports semantic errors", (t) => {
  const { root, worker } = fixture(t);
  fs.writeFileSync(
    path.join(root, "sample.js"),
    '/** @param {number} x */\nexport function twice(x) { return x * 2; }\ntwice("wrong");\n',
  );
  assert.ok(
    worker
      .handle("diagnostics", { file: "sample.js" })
      .some((d) => d.code === 2345),
  );
  assert.match(
    worker.handle("hover", { file: "sample.js", line: 1, character: 17 })
      .display,
    /twice\(x: number\): number/,
  );
});
test("nearest nested config controls project compilation", (t) => {
  const { root, worker } = fixture(t);
  fs.mkdirSync(path.join(root, "nested"));
  fs.writeFileSync(
    path.join(root, "nested", "tsconfig.json"),
    '{"compilerOptions":{"strict":true},"include":["*.ts"]}',
  );
  fs.writeFileSync(
    path.join(root, "nested", "index.ts"),
    "function sample(x) { return x; }",
  );
  assert.ok(
    worker
      .handle("diagnostics", { file: "nested/index.ts" })
      .some((d) => d.code === 7006),
  );
});
test("configuration cannot read inherited files outside the authorized root", (t) => {
  const { root, worker } = fixture(t);
  fs.writeFileSync(
    path.join(root, "tsconfig.json"),
    '{"extends":"../outside-tsconfig.json","include":["*.ts"]}',
  );
  assert.throws(
    () => worker.handle("symbols", { file: "a.ts" }),
    /Cannot read file/,
  );
});
test("UTF-16 positions preserve astral-character offsets", (t) => {
  const { root, worker } = fixture(t);
  fs.writeFileSync(
    path.join(root, "unicode.ts"),
    'const face = "😀"; export const value = face;',
  );
  const definition = worker.handle("definition", {
    file: "unicode.ts",
    line: 0,
    character: 40,
  });
  assert.equal(definition[0].name, "face");
  assert.equal(definition[0].range.start.character, 6);
});
test("stdio returns correlated JSON and survives malformed requests", async (t) => {
  const { spawn } = await import("node:child_process");
  const { fileURLToPath } = await import("node:url");
  const child = spawn(
    process.execPath,
    [fileURLToPath(new URL("../worker.mjs", import.meta.url))],
    { stdio: ["pipe", "pipe", "pipe"] },
  );
  t.after(() => child.kill());
  let output = "";
  child.stdout.setEncoding("utf8");
  child.stdout.on("data", (s) => (output += s));
  child.stdin.end(
    "not json\n" +
      JSON.stringify({ id: 7, method: "capabilities" }) +
      "\n" +
      JSON.stringify({ id: 8, method: "unknown" }) +
      "\n",
  );
  const code = await new Promise((resolve, reject) => {
    child.on("close", resolve);
    child.on("error", reject);
  });
  assert.equal(code, 0);
  const responses = output.trim().split("\n").map(JSON.parse);
  assert.ok(responses[0].error.message);
  assert.equal(responses[1].id, 7);
  assert.ok(responses[1].result.operations.includes("definition"));
  assert.equal(responses[2].id, 8);
  assert.match(responses[2].error.message, /Unsupported/);
});
test("organize imports previews remove unused imports without writing source", (t) => {
  const { root, worker } = fixture(t);
  const source =
    'import { total, add } from "./a";\nexport const result = add(1, 2);\n';
  fs.writeFileSync(path.join(root, "imports.ts"), source);
  const result = worker.handle("organizeImports", { file: "imports.ts" });
  assert.equal(result.preview, true);
  assert.equal(result.edits.length, 1);
  assert.equal(result.edits[0].newText, 'import { add } from "./a";\n');
  assert.deepEqual(result.edits[0].range, {
    start: { line: 0, character: 0 },
    end: { line: 1, character: 0 },
  });
  assert.match(result.edits[0].expectedSha256, /^[a-f0-9]{64}$/);
  assert.equal(fs.readFileSync(path.join(root, "imports.ts"), "utf8"), source);
});
test("implementations locate the concrete method for an interface", (t) => {
  const { root, worker } = fixture(t);
  fs.writeFileSync(
    path.join(root, "contract.ts"),
    'export interface Greeter { greet(): string; }\nexport class Friendly implements Greeter { greet() { return "hi"; } }\n',
  );
  const items = worker.handle("implementations", {
    file: "contract.ts",
    line: 0,
    character: 28,
  });
  assert.equal(items.length, 1);
  assert.equal(items[0].range.start.line, 1);
  assert.equal(items[0].range.start.character, 43);
  assert.equal(items[0].kind, "method");
});
test("type info returns the official inferred declaration display", (t) => {
  const { worker } = fixture(t);
  const info = worker.handle("typeInfo", {
    file: "a.ts",
    line: 1,
    character: 14,
  });
  assert.equal(info.display, "const total: number");
});
test("bounded symbol search locates declarations across configured project files", (t) => {
  const { worker } = fixture(t);
  const result = worker.handle("workspaceSymbols", {
    file: "a.ts",
    query: "answer",
  });
  assert.equal(result.scope, "selected-project");
  assert.equal(result.items.length, 1);
  assert.equal(result.items[0].name, "answer");
  assert.equal(path.basename(result.items[0].file), "b.ts");
  assert.equal(result.items[0].range.start.line, 1);
  const limited = worker.handle("workspaceSymbols", {
    file: "a.ts",
    query: "",
    limit: 1,
  });
  assert.equal(limited.items.length, 1);
  assert.equal(limited.truncated, true);
  assert.throws(() =>
    worker.handle("workspaceSymbols", { file: "a.ts", query: "", limit: 501 }),
  );
});
test("call hierarchy reports exact incoming and outgoing functions", (t) => {
  const { root, worker } = fixture(t);
  fs.writeFileSync(
    path.join(root, "calls.ts"),
    "export function leaf() { return 1; }\nexport function middle() { return leaf(); }\nexport function top() { return middle(); }\n",
  );
  const result = worker.handle("callHierarchy", {
    file: "calls.ts",
    line: 1,
    character: 17,
  });
  assert.equal(result.length, 1);
  assert.equal(result[0].item.name, "middle");
  assert.equal(result[0].incoming.length, 1);
  assert.equal(result[0].incoming[0].from.name, "top");
  assert.equal(result[0].incoming[0].locations[0].range.start.line, 2);
  assert.equal(result[0].outgoing.length, 1);
  assert.equal(result[0].outgoing[0].to.name, "leaf");
  assert.equal(result[0].outgoing[0].locations[0].range.start.line, 1);
});
test("code action previews add missing interface method without writing source", (t) => {
  const { root, worker } = fixture(t);
  const source =
    "interface Contract { greet(): string; }\nclass Missing implements Contract {}\n";
  fs.writeFileSync(path.join(root, "fix.ts"), source);
  const actions = worker.handle("codeActions", {
    file: "fix.ts",
    line: 1,
    character: 7,
  });
  const action = actions.find(
    (a) => a.fixName === "fixClassIncorrectlyImplementsInterface",
  );
  assert.ok(action, JSON.stringify(actions));
  assert.equal(action.preview, true);
  assert.equal(action.edits.length, 1);
  assert.match(action.edits[0].newText, /greet\(\): string/);
  assert.match(
    action.edits[0].newText,
    /throw new Error\("Method not implemented\."\)/,
  );
  assert.deepEqual(action.edits[0].range, {
    start: { line: 1, character: 35 },
    end: { line: 1, character: 35 },
  });
  assert.match(action.edits[0].expectedSha256, /^[a-f0-9]{64}$/);
  assert.equal(fs.readFileSync(path.join(root, "fix.ts"), "utf8"), source);
});
test("external typeRoots cannot provide ambient declarations", (t) => {
  const { root, worker } = fixture(t);
  const external = fs.mkdtempSync(
    path.join(os.tmpdir(), "freeflight-external-types-"),
  );
  t.after(() => fs.rmSync(external, { recursive: true, force: true }));
  fs.mkdirSync(path.join(external, "leak"));
  fs.writeFileSync(
    path.join(external, "leak", "index.d.ts"),
    "declare const outsideSecret: string;",
  );
  fs.writeFileSync(
    path.join(root, "tsconfig.json"),
    JSON.stringify({
      compilerOptions: { typeRoots: [external] },
      include: ["*.ts"],
    }),
  );
  fs.writeFileSync(path.join(root, "ambient.ts"), "outsideSecret;");
  const diagnostics = worker.handle("diagnostics", { file: "ambient.ts" });
  assert.ok(
    diagnostics.some(
      (d) => d.code === 2304 && d.message.includes("outsideSecret"),
    ),
  );
});
test("preview edits reject changed source and overlapping replacements", (t) => {
  const { root, worker } = fixture(t);
  const fileName = path.join(root, "a.ts");
  const service = worker.project(fileName).service;
  service.getProgram();
  assert.throws(
    () =>
      worker.previewEdits(
        [
          {
            fileName,
            textChanges: [
              { span: { start: 0, length: 10 }, newText: "a" },
              { span: { start: 5, length: 1 }, newText: "b" },
            ],
          },
        ],
        service,
      ),
    /Overlapping/,
  );
  // Pin the analyzed Program as a concurrent request would see it before the disk change.
  const analyzed = service.getProgram();
  fs.appendFileSync(fileName, "\n// concurrent modification");
  assert.throws(
    () =>
      worker.previewEdits(
        [
          {
            fileName,
            textChanges: [{ span: { start: 0, length: 0 }, newText: "x" }],
          },
        ],
        { getProgram: () => analyzed },
      ),
    /changed during analysis/,
  );
});


test("resource policy rejects malformed settings and query overrides", (t) => {
  const { root, worker } = fixture(t);
  for (const resources of [null, [], { bogus: 1 }, { maxFiles: 0 }, { maxFiles: 1.5 }, { maxFiles: null }, { maxFiles: 200001 }, { maxFileBytes: 100, maxWorkspaceBytes: 99 }])
    assert.throws(() => worker.open({ root, resources }));
  assert.throws(() => worker.handle("symbols", { file: "a.ts", resources: {} }), /startup-owned/);
});

test("bounded source reads accept exact limit, reject growth and recover", (t) => {
  const { root, worker } = fixture(t);
  const file = path.join(root, "large.ts");
  worker.open({ root, resources: { maxFileBytes: 1024, maxWorkspaceBytes: 4096 } });
  fs.writeFileSync(file, " ".repeat(1024));
  assert.equal(worker.read(file).length, 1024);
  fs.appendFileSync(file, " ");
  assert.throws(() => worker.read(file), (error) => {
    assert.equal(error.details.code, "resource_limit_exceeded");
    assert.equal(error.details.path, "large.ts");
    assert.equal(error.details.observed, 1025);
    assert.equal(error.details.limit, 1024);
    assert.match(error.details.remediation, /resources.maxFileBytes/);
    return true;
  });
  fs.writeFileSync(file, "export const recovered = 1;");
  assert.match(worker.read(file), /recovered/);
});

test("aggregate and directory budgets report structured failures", (t) => {
  const { root, worker } = fixture(t);
  worker.open({ root, resources: { maxFileBytes: 1024, maxWorkspaceBytes: 1024 } });
  for (const name of ["first.ts", "second.ts"]) fs.writeFileSync(path.join(root, name), " ".repeat(600));
  worker.read(path.join(root, "first.ts"));
  assert.throws(() => worker.read(path.join(root, "second.ts")), (error) => error.details.resource === "maxWorkspaceBytes" && error.details.observed === 1200);
  worker.open({ root, resources: { maxDirectoryEntries: 1 } });
  assert.throws(() => worker.handle("symbols", { file: "a.ts" }), (error) => error.details.resource === "maxDirectoryEntries");
  assert.equal(worker.projects.size, 0);
  worker.open({ root });
  assert.ok(worker.handle("symbols", { file: "a.ts" }).some((item) => item.name === "add"));
});

test("large generated source retains exact semantics and warm snapshots", (t) => {
  const { root, worker } = fixture(t);
  const file = path.join(root, "generated.ts");
  const text = "export const generatedValue: number = 42;\nexport const use = generatedValue;\n/*" + "x".repeat(9 * 1024 * 1024) + "*/\n";
  fs.writeFileSync(file, text);
  const started = performance.now();
  const definitions = worker.handle("definition", { file: "generated.ts", line: 1, character: 22 });
  assert.equal(definitions.length, 1);
  assert.equal(definitions[0].range.start.line, 0);
  assert.equal(definitions[0].name, "generatedValue");
  const before = worker.diskReads;
  assert.equal(worker.read(file), text);
  assert.equal(worker.diskReads, before);
  const previous = fs.statSync(file);
  fs.writeFileSync(file, text.replace("number = 42", "string = 42"));
  fs.utimesSync(file, previous.atime, previous.mtime);
  const diagnostics = worker.handle("diagnostics", { file: "generated.ts" });
  assert.ok(diagnostics.some((d) => d.code === 2322));
  t.diagnostic(JSON.stringify({ bytes: Buffer.byteLength(text), elapsedMs: performance.now() - started, diskReads: worker.diskReads, snapshotBytes: worker.snapshotBytes }));
});


test("default policy analyzes a configured source set over 64 MiB", (t) => {
  const { root, worker } = fixture(t);
  fs.writeFileSync(path.join(root, "tsconfig.json"), JSON.stringify({ compilerOptions: { noLib: true }, include: ["generated*.ts"] }));
  let bytes = 0;
  for (let index = 0; index < 9; index++) {
    const text = `export const item${index}: number = ${index};\n/*` + "x".repeat(8 * 1024 * 1024) + "*/\n";
    bytes += Buffer.byteLength(text);
    fs.writeFileSync(path.join(root, `generated${index}.ts`), text);
  }
  const started = performance.now();
  assert.deepEqual(worker.handle("diagnostics", { file: "generated0.ts" }), []);
  const symbols = worker.handle("workspaceSymbols", { file: "generated0.ts", query: "item8" });
  assert.ok(symbols.items.some((item) => item.name === "item8"));
  assert.ok(worker.budgetBytes > 64 * 1024 * 1024);
  assert.ok(worker.snapshotBytes <= 64 * 1024 * 1024);
  const warmReads = worker.diskReads, warmHashes = worker.contentHashes;
  assert.deepEqual(worker.handle("diagnostics", { file: "generated0.ts" }), []);
  assert.equal(worker.diskReads - warmReads, 1);
  assert.equal(worker.contentHashes - warmHashes, 1);
  t.diagnostic(JSON.stringify({ sourceBytes: bytes, elapsedMs: performance.now() - started, snapshotBytes: worker.snapshotBytes, rssBytes: process.memoryUsage().rss }));
});


test("a source growing during reading cannot bypass the byte budget", (t) => {
  const { root, worker } = fixture(t);
  const file = path.join(root, "growth.ts");
  worker.open({ root, resources: { maxFileBytes: 1024, maxWorkspaceBytes: 4096 } });
  fs.writeFileSync(file, " ".repeat(1024));
  const original = fs.readSync;
  let appended = false;
  try {
    fs.readSync = (...args) => {
      const count = original(...args);
      if (!appended) { appended = true; fs.appendFileSync(file, "x"); }
      return count;
    };
    assert.throws(() => worker.read(file), (error) => error.details.resource === "maxFileBytes" && error.details.observed === 1025);
  } finally { fs.readSync = original; }
});

test("warm requests reread only the direct target and fallback revalidates cached content", (t) => {
  const { root, worker } = fixture(t);
  worker.handle("diagnostics", { file: "a.ts" });
  const before = worker.diskReads;
  const hashesBefore = worker.contentHashes;
  worker.handle("diagnostics", { file: "a.ts" });
  assert.equal(worker.diskReads - before, 1);
  assert.equal(worker.contentHashes - hashesBefore, 1);
  const canonical = path.join(root, "b.ts");
  const cached = worker.snapshots.get(canonical);
  assert.ok(cached);
  cached.verifiedAt = -Infinity;
  const prior = worker.diskReads;
  worker.read(canonical);
  assert.equal(worker.diskReads - prior, 1);
});


test("source I/O failures are explicit and do not return partial semantics", (t) => {
  const { worker } = fixture(t);
  const original = fs.readSync;
  try {
    fs.readSync = () => { const error = new Error("denied"); error.code = "EACCES"; throw error; };
    assert.throws(() => worker.handle("symbols", { file: "a.ts" }), (error) => error.details.code === "source_unavailable" && /EACCES/.test(error.message));
  } finally { fs.readSync = original; }
  assert.equal(worker.projects.size, 0);
  assert.ok(worker.handle("symbols", { file: "a.ts" }).some((item) => item.name === "add"));
});

test("internal transport preserves structured resource errors", async (t) => {
  const { PassThrough } = await import("node:stream");
  const { root } = fixture(t);
  fs.writeFileSync(path.join(root, "oversize.ts"), " ".repeat(1025));
  const input = new PassThrough(), output = new PassThrough();
  let text = "";
  output.on("data", (chunk) => { text += chunk.toString(); });
  serve(input, output);
  input.write(JSON.stringify({ id: 1, method: "open", params: { root, resources: { maxFileBytes: 1024 } } }) + "\n");
  input.end(JSON.stringify({ id: 2, method: "symbols", params: { file: "oversize.ts" } }) + "\n");
  await new Promise((resolve) => setImmediate(resolve));
  const responses = text.trim().split("\n").map(JSON.parse);
  assert.equal(responses[1].id, 2);
  assert.equal(responses[1].error.code, "resource_limit_exceeded");
  assert.equal(responses[1].error.path, "oversize.ts");
  assert.equal(responses[1].error.observed, 1025);
});


test("explicit missing project sources fail instead of disappearing", (t) => {
  const { root, worker } = fixture(t);
  fs.writeFileSync(path.join(root, "tsconfig.json"), JSON.stringify({ files: ["a.ts", "missing.ts"] }));
  assert.throws(() => worker.handle("symbols", { file: "a.ts" }), (error) => error.details.code === "source_unavailable" && error.details.path === "missing.ts");
});

test("large JavaScript source keeps JSDoc diagnostics and incremental changes", (t) => {
  const { root, worker } = fixture(t);
  const file = path.join(root, "generated.js");
  const text = "/** @type {number} */\nexport const value = 42;\n/*" + "x".repeat(9 * 1024 * 1024) + "*/\n";
  fs.writeFileSync(file, text);
  const started = performance.now();
  assert.deepEqual(worker.handle("diagnostics", { file: "generated.js" }), []);
  const before = fs.statSync(file);
  fs.writeFileSync(file, text.replace("= 42", '= "x"'));
  fs.utimesSync(file, before.atime, before.mtime);
  assert.ok(worker.handle("diagnostics", { file: "generated.js" }).some((d) => d.code === 2322));
  t.diagnostic(JSON.stringify({ language: "javascript", bytes: Buffer.byteLength(text), elapsedMs: performance.now() - started }));
});

test("navigation follows imports across configured project directories", (t) => {
  const { root, worker } = fixture(t);
  for (const name of ["left", "right"]) {
    fs.mkdirSync(path.join(root, name));
    fs.writeFileSync(path.join(root, name, "tsconfig.json"), JSON.stringify({ compilerOptions: { composite: true }, include: ["*.ts"] }));
  }
  fs.writeFileSync(path.join(root, "right", "value.ts"), "export const shared = 42;\n");
  fs.writeFileSync(path.join(root, "left", "use.ts"), 'import { shared } from "../right/value";\nexport const result = shared;\n');
  const location = worker.handle("definition", { file: "left/use.ts", line: 1, character: 25 });
  assert.equal(location.length, 1);
  assert.equal(location[0].file, path.join(root, "right", "value.ts"));
  assert.equal(location[0].range.start.line, 0);
  const refs = worker.handle("references", { file: "left/use.ts", line: 1, character: 25 });
  assert.equal(refs.length, 3);
  assert.equal(refs.filter((item) => item.file === path.join(root, "right", "value.ts")).length, 1);
});


test("project-reference graphs fail explicitly rather than returning incomplete navigation", (t) => {
  const { root, worker } = fixture(t);
  fs.mkdirSync(path.join(root, "dependency"));
  fs.writeFileSync(path.join(root, "dependency", "tsconfig.json"), JSON.stringify({ compilerOptions: { composite: true }, files: ["value.ts"] }));
  fs.writeFileSync(path.join(root, "dependency", "value.ts"), "export const dependency = 1;\n");
  fs.writeFileSync(path.join(root, "tsconfig.json"), JSON.stringify({ files: ["a.ts"], references: [{ path: "./dependency" }] }));
  assert.throws(() => worker.handle("symbols", { file: "a.ts" }), (error) => error.details.code === "unsupported_project_references" && error.details.path === "tsconfig.json");
});


test("version metadata eviction cannot substitute another source hash", (t) => {
  const { root, worker } = fixture(t);
  const first = path.join(root, "a.ts"), second = path.join(root, "b.ts");
  const expected = worker.version(first);
  assert.notEqual(worker.version(second), expected);
  worker.versions.delete(first);
  assert.ok(worker.snapshots.has(first));
  assert.equal(worker.version(first), expected);
});
