// SPDX-License-Identifier: Apache-2.0
import fs from "node:fs";
import path from "node:path";
import { createHash } from "node:crypto";
import { createRequire } from "node:module";
import { pathToFileURL } from "node:url";
import ts from "typescript";

const require = createRequire(import.meta.url);
const libRoot = path.dirname(require.resolve("typescript"));
const inside = (root, file) => {
  const rel = path.relative(root, file);
  return (
    rel === "" ||
    (!rel.startsWith(`..${path.sep}`) && rel !== ".." && !path.isAbsolute(rel))
  );
};
const hash = (text) => createHash("sha256").update(text).digest("hex");
export class Worker {
  root;
  projects = new Map();
  capabilities() {
    return {
      languages: ["typescript", "javascript"],
      operations: [
        "symbols",
        "definition",
        "references",
        "hover",
        "diagnostics",
        "rename",
        "signatureHelp",
        "organizeImports",
        "implementations",
        "typeInfo",
        "workspaceSymbols",
        "callHierarchy",
        "codeActions",
      ],
      rename: "preview-only",
      positionEncoding: "utf-16",
    };
  }
  resolve(file, library = false) {
    if (!this.root) throw new Error("Open an authorized workspace first");
    if (typeof file !== "string" || file.includes("\0"))
      throw new Error("Invalid file path");
    const resolved = fs.realpathSync(path.resolve(this.root, file));
    if (!inside(this.root, resolved) && !(library && inside(libRoot, resolved)))
      throw new Error("Path outside authorized workspace");
    return resolved;
  }
  allowed(file, library = true) {
    try {
      this.resolve(file, library);
      return true;
    } catch {
      return false;
    }
  }
  read(file) {
    try {
      const canonical = this.resolve(file, true);
      if (fs.statSync(canonical).size > 8 * 1024 * 1024)
        throw new Error("File exceeds 8 MiB limit");
      return fs.readFileSync(canonical, "utf8");
    } catch {
      return undefined;
    }
  }
  open({ root }) {
    if (typeof root !== "string" || !path.isAbsolute(root))
      throw new Error("root must be an absolute authorized directory");
    const canonical = fs.realpathSync(root);
    if (!fs.statSync(canonical).isDirectory())
      throw new Error("root must be a directory");
    this.close();
    this.root = canonical;
    return { root: this.root, ...this.capabilities() };
  }
  close() {
    for (const p of this.projects.values()) p.service.dispose();
    this.projects.clear();
  }
  project(file) {
    let directory = path.dirname(file),
      config;
    while (inside(this.root, directory)) {
      config = ["tsconfig.json", "jsconfig.json"]
        .map((name) => path.join(directory, name))
        .find((name) => this.allowed(name, false));
      if (config || directory === this.root) break;
      directory = path.dirname(directory);
    }
    const key = config || this.root;
    const configText = config ? this.read(config) : "";
    let p = this.projects.get(key);
    // Reparse config on each request, including inherited configs. No plugin loader is used.
    const parseHost = {
      useCaseSensitiveFileNames: ts.sys.useCaseSensitiveFileNames,
      readFile: (f) => this.read(f),
      fileExists: (f) => this.allowed(f),
      readDirectory: (dir, extensions, exclude, include, depth) =>
        this.allowed(dir, false)
          ? ts.sys
              .readDirectory(dir, extensions, exclude, include, depth)
              .filter((f) => this.allowed(f, false))
          : [],
    };
    let parsed;
    if (config) {
      const result = ts.parseConfigFileTextToJson(config, configText);
      if (result.error)
        throw new Error(
          ts.flattenDiagnosticMessageText(result.error.messageText, "\n"),
        );
      parsed = ts.parseJsonConfigFileContent(
        result.config,
        parseHost,
        path.dirname(config),
        undefined,
        config,
      );
      const fatal = parsed.errors.filter((e) => e.code !== 18003);
      if (fatal.length)
        throw new Error(
          fatal
            .map((e) => ts.flattenDiagnosticMessageText(e.messageText, "\n"))
            .join("\n"),
        );
    } else {
      parsed = {
        options: {
          allowJs: true,
          checkJs: true,
          noEmit: true,
          target: ts.ScriptTarget.ES2022,
          module: ts.ModuleKind.NodeNext,
          moduleResolution: ts.ModuleResolutionKind.NodeNext,
        },
        fileNames: [file],
      };
    }
    delete parsed.options.plugins;
    parsed.options.noEmit = true;
    parsed.fileNames = parsed.fileNames.filter((f) => this.allowed(f, false));
    if (!parsed.fileNames.includes(file)) parsed.fileNames.push(file);
    if (parsed.fileNames.length > 20000)
      throw new Error("Project exceeds 20,000 source file limit");
    const fingerprint = JSON.stringify([parsed.options, parsed.fileNames]);
    if (p && p.fingerprint !== fingerprint) {
      p.service.dispose();
      this.projects.delete(key);
      p = undefined;
    }
    if (!p) {
      if (this.projects.size >= 8) {
        const oldest = this.projects.keys().next().value;
        this.projects.get(oldest).service.dispose();
        this.projects.delete(oldest);
      }
      p = { fingerprint, files: parsed.fileNames, options: parsed.options };
      const host = {
        getCompilationSettings: () => p.options,
        getScriptFileNames: () => p.files,
        getScriptVersion: (f) => hash(this.read(f) ?? ""),
        getScriptSnapshot: (f) => {
          const text = this.read(f);
          return text === undefined
            ? undefined
            : ts.ScriptSnapshot.fromString(text);
        },
        getCurrentDirectory: () => this.root,
        getDefaultLibFileName: (o) => ts.getDefaultLibFilePath(o),
        fileExists: (f) => this.allowed(f),
        readFile: (f) => this.read(f),
        readDirectory: parseHost.readDirectory,
        directoryExists: (f) => {
          try {
            return this.allowed(f) && fs.statSync(f).isDirectory();
          } catch {
            return false;
          }
        },
        getDirectories: (dir) =>
          this.allowed(dir)
            ? ts.sys
                .getDirectories(dir)
                .filter((f) => this.allowed(path.join(dir, f)))
            : [],
        realpath: (f) => this.resolve(f, true),
        useCaseSensitiveFileNames: () => ts.sys.useCaseSensitiveFileNames,
        getNewLine: () => "\n",
      };
      p.service = ts.createLanguageService(host);
      this.projects.set(key, p);
    }
    return p;
  }
  position(source, line, character) {
    if (
      !Number.isSafeInteger(line) ||
      line < 0 ||
      !Number.isSafeInteger(character) ||
      character < 0
    )
      throw new Error(
        "Position requires nonnegative integer line and character",
      );
    const starts = source.getLineStarts();
    if (line >= starts.length) throw new Error("Line out of range");
    let end = line + 1 < starts.length ? starts[line + 1] : source.text.length;
    while (
      end > starts[line] &&
      (source.text[end - 1] === "\n" || source.text[end - 1] === "\r")
    )
      end--;
    if (starts[line] + character > end)
      throw new Error("Character out of range");
    return starts[line] + character;
  }
  location(file, span) {
    const canonical = this.resolve(file, true),
      text = this.read(canonical);
    if (text === undefined) throw new Error("Source unavailable");
    const source = ts.createSourceFile(canonical, text, ts.ScriptTarget.Latest);
    return {
      file: canonical,
      range: {
        start: source.getLineAndCharacterOfPosition(span.start),
        end: source.getLineAndCharacterOfPosition(span.start + span.length),
      },
    };
  }
  previewEdits(changes, service) {
    const edits = [];
    const grouped = new Map();
    for (const change of changes) {
      if (change.isNewFile)
        throw new Error("New-file code actions are not supported");
      const file = this.resolve(change.fileName);
      if (!grouped.has(file)) grouped.set(file, []);
      grouped.get(file).push(...change.textChanges);
    }
    for (const [fileName, textChanges] of grouped) {
      const change = { fileName, textChanges };
      if (change.isNewFile)
        throw new Error("New-file code actions are not supported");
      const target = this.resolve(change.fileName);
      const text = this.read(target);
      const source = service.getProgram()?.getSourceFile(target);
      if (!source || text !== source.text)
        throw new Error("Document changed during analysis; retry the preview");
      const expectedSha256 = hash(text);
      const sorted = [];
      for (const next of [...change.textChanges].sort(
        (a, b) => a.span.start - b.span.start,
      )) {
        const previous = sorted.at(-1);
        if (
          previous &&
          previous.span.start === next.span.start &&
          previous.span.length === 0 &&
          next.span.length === 0
        ) {
          previous.newText += next.newText;
        } else {
          sorted.push({ span: { ...next.span }, newText: next.newText });
        }
      }
      let previousEnd = -1;
      for (const edit of sorted) {
        if (
          edit.span.start < previousEnd ||
          edit.span.start < 0 ||
          edit.span.start + edit.span.length > text.length
        ) {
          throw new Error("Overlapping or invalid code action edits");
        }
        previousEnd = edit.span.start + edit.span.length;
        edits.push({
          file: target,
          range: {
            start: source.getLineAndCharacterOfPosition(edit.span.start),
            end: source.getLineAndCharacterOfPosition(previousEnd),
          },
          newText: edit.newText,
          expectedSha256,
        });
      }
    }
    return edits;
  }
  hierarchyItem(item) {
    return {
      name: item.name,
      kind: item.kind,
      containerName: item.containerName || "",
      ...this.location(item.file, item.span),
      selectionRange: this.location(item.file, item.selectionSpan).range,
    };
  }
  handle(method, params = {}) {
    if (method === "capabilities") return this.capabilities();
    if (method === "open") return this.open(params);
    if (method === "shutdown") {
      this.close();
      return {};
    }
    if (!this.capabilities().operations.includes(method))
      throw new Error(`Unsupported method: ${method}`);
    const file = this.resolve(params.file),
      p = this.project(file),
      service = p.service;
    const program = service.getProgram();
    const source = program?.getSourceFile(file);
    const analyzed = { getProgram: () => program };
    if (!source) throw new Error("File is not a supported project document");
    if (method === "symbols") {
      const convert = (item) => ({
        name: item.text,
        kind: item.kind,
        ...this.location(file, item.spans[0]),
        children: (item.childItems || []).map(convert),
      });
      return (service.getNavigationTree(file).childItems || []).map(convert);
    }
    if (method === "diagnostics")
      return [
        ...service.getSyntacticDiagnostics(file),
        ...service.getSemanticDiagnostics(file),
      ]
        .map((d) => ({
          code: d.code,
          severity: ts.DiagnosticCategory[d.category].toLowerCase(),
          message: ts.flattenDiagnosticMessageText(d.messageText, "\n"),
          ...(d.file
            ? this.location(d.file.fileName, {
                start: d.start ?? 0,
                length: d.length ?? 0,
              })
            : {}),
        }))
        .sort(
          (a, b) =>
            (a.range?.start.line ?? 0) - (b.range?.start.line ?? 0) ||
            a.code - b.code,
        );
    if (method === "organizeImports") {
      const changes = service.organizeImports(
        { type: "file", fileName: file },
        {},
        {},
      );
      return { preview: true, edits: this.previewEdits(changes, analyzed) };
    }
    if (method === "workspaceSymbols") {
      if (typeof params.query !== "string" || params.query.length > 256)
        throw new Error("query must be a string of at most 256 characters");
      const limit = params.limit ?? 100;
      if (!Number.isSafeInteger(limit) || limit < 1 || limit > 500)
        throw new Error("limit must be between 1 and 500");
      const matches = service.getNavigateToItems(
        params.query,
        limit + 1,
        undefined,
        true,
        true,
      );
      const items = matches
        .slice(0, limit)
        .map((item) => ({
          name: item.name,
          kind: item.kind,
          containerName: item.containerName,
          ...this.location(item.fileName, item.textSpan),
        }))
        .sort(
          (a, b) =>
            a.name.localeCompare(b.name) ||
            a.file.localeCompare(b.file) ||
            a.range.start.line - b.range.start.line,
        );
      return {
        scope: "selected-project",
        truncated: matches.length > limit,
        items,
      };
    }
    const pos = this.position(source, params.line, params.character);
    if (method === "implementations") {
      return (service.getImplementationAtPosition(file, pos) || []).map(
        (item) => ({
          kind: item.kind,
          display: ts.displayPartsToString(item.displayParts),
          ...this.location(item.fileName, item.textSpan),
        }),
      );
    }
    if (method === "callHierarchy") {
      const prepared = service.prepareCallHierarchy(file, pos);
      const items = prepared
        ? Array.isArray(prepared)
          ? prepared
          : [prepared]
        : [];
      if (items.length > 100)
        throw new Error("Call hierarchy exceeds 100 root items");
      const boundedCalls = (calls) => {
        if (calls.length > 500)
          throw new Error(
            "Call hierarchy exceeds 500 edges; select a narrower symbol",
          );
        return calls;
      };
      return items.map((item) => ({
        item: this.hierarchyItem(item),
        incoming: boundedCalls(
          service.provideCallHierarchyIncomingCalls(
            item.file,
            item.selectionSpan.start,
          ),
        ).map((call) => ({
          from: this.hierarchyItem(call.from),
          locations: call.fromSpans.map((span) =>
            this.location(call.from.file, span),
          ),
        })),
        outgoing: boundedCalls(
          service.provideCallHierarchyOutgoingCalls(
            item.file,
            item.selectionSpan.start,
          ),
        ).map((call) => ({
          to: this.hierarchyItem(call.to),
          locations: call.fromSpans.map((span) =>
            this.location(item.file, span),
          ),
        })),
      }));
    }
    if (method === "codeActions") {
      const diagnostics = [
        ...service.getSyntacticDiagnostics(file),
        ...service.getSemanticDiagnostics(file),
      ].filter(
        (d) =>
          d.start !== undefined &&
          d.start <= pos &&
          pos <= d.start + (d.length ?? 0),
      );
      const actions = [];
      const seen = new Set();
      for (const diagnostic of diagnostics) {
        const fixes = service.getCodeFixesAtPosition(
          file,
          diagnostic.start,
          diagnostic.start + (diagnostic.length ?? 0),
          [diagnostic.code],
          {},
          {},
        );
        for (const fix of fixes) {
          // Commands can install packages; never execute or offer them.
          if (
            fix.commands?.length ||
            fix.changes.some((change) => change.isNewFile)
          )
            continue;
          const edits = this.previewEdits(fix.changes, analyzed);
          const key = JSON.stringify(edits);
          if (seen.has(key)) continue;
          seen.add(key);
          actions.push({
            title: fix.description,
            fixName: fix.fixName,
            preview: true,
            edits,
          });
          if (actions.length === 100) return actions;
        }
      }
      return actions;
    }
    if (method === "definition")
      return (service.getDefinitionAtPosition(file, pos) || []).map((d) => ({
        name: d.name,
        kind: d.kind,
        ...this.location(d.fileName, d.textSpan),
      }));
    if (method === "references")
      return (service.getReferencesAtPosition(file, pos) || []).map((r) => ({
        ...this.location(r.fileName, r.textSpan),
        isWriteAccess: r.isWriteAccess,
      }));
    if (method === "hover" || method === "typeInfo") {
      const h = service.getQuickInfoAtPosition(file, pos);
      return h
        ? {
            display: ts.displayPartsToString(h.displayParts),
            documentation: ts.displayPartsToString(h.documentation),
            ...this.location(file, h.textSpan),
          }
        : null;
    }
    if (method === "signatureHelp") {
      const h = service.getSignatureHelpItems(file, pos, undefined);
      return h
        ? {
            selectedItemIndex: h.selectedItemIndex,
            argumentIndex: h.argumentIndex,
            argumentCount: h.argumentCount,
            signatures: h.items.map((i) => ({
              prefix: ts.displayPartsToString(i.prefixDisplayParts),
              suffix: ts.displayPartsToString(i.suffixDisplayParts),
              separator: ts.displayPartsToString(i.separatorDisplayParts),
              documentation: ts.displayPartsToString(i.documentation),
              parameters: i.parameters.map((v) => ({
                name: v.name,
                display: ts.displayPartsToString(v.displayParts),
                documentation: ts.displayPartsToString(v.documentation),
                optional: v.isOptional,
              })),
            })),
          }
        : null;
    }
    if (method === "rename") {
      if (
        typeof params.newName !== "string" ||
        !ts.isIdentifierText(params.newName, ts.ScriptTarget.Latest) ||
        ts.stringToToken(params.newName) !== undefined
      )
        throw new Error("newName must be an identifier, not a keyword");
      const info = service.getRenameInfo(file, pos, {
        allowRenameOfImportPath: false,
      });
      if (!info.canRename) throw new Error(info.localizedErrorMessage);
      const locations =
        service.findRenameLocations(file, pos, false, false, true) || [];
      const changes = locations.map((r) => ({
        fileName: r.fileName,
        textChanges: [
          {
            span: r.textSpan,
            newText: `${r.prefixText || ""}${params.newName}${r.suffixText || ""}`,
          },
        ],
      }));
      const edits = this.previewEdits(changes, analyzed);
      return { preview: true, edits };
    }
  }
}

// Deliberately independent from MCP: the C++ core owns client protocol and authorization.
export function serve(input = process.stdin, output = process.stdout) {
  const worker = new Worker();
  let buffer = "";
  const maxBytes = 1024 * 1024;
  input.setEncoding("utf8");
  input.on("data", (chunk) => {
    buffer += chunk;
    if (Buffer.byteLength(buffer) > maxBytes) {
      process.stderr.write("Worker request exceeds limit\n");
      input.destroy();
      worker.close();
      process.exitCode = 1;
      return;
    }
    for (;;) {
      const newline = buffer.indexOf("\n");
      if (newline < 0) break;
      const line = buffer.slice(0, newline);
      buffer = buffer.slice(newline + 1);
      let request;
      try {
        request = JSON.parse(line);
        if (
          !request ||
          typeof request.method !== "string" ||
          !["string", "number"].includes(typeof request.id) ||
          (request.params !== undefined &&
            (!request.params ||
              typeof request.params !== "object" ||
              Array.isArray(request.params)))
        )
          throw new Error("Invalid request");
        output.write(
          `${JSON.stringify({ id: request.id, result: worker.handle(request.method, request.params) })}\n`,
        );
      } catch (error) {
        output.write(
          `${JSON.stringify({ id: request?.id ?? null, error: { message: error.message } })}\n`,
        );
      }
    }
  });
  input.on("end", () => worker.close());
}
if (
  process.argv[1] &&
  import.meta.url === pathToFileURL(path.resolve(process.argv[1])).href
)
  serve();
