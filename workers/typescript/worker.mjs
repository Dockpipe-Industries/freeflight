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
const resourceSpec = {
  maxFileBytes: [32 * 1024 * 1024, 256 * 1024 * 1024],
  maxWorkspaceBytes: [512 * 1024 * 1024, 2 * 1024 * 1024 * 1024],
  maxFiles: [50000, 200000],
  maxDirectoryEntries: [500000, 2000000],
};
function resourcePolicy(value = {}) {
  if (!value || typeof value !== "object" || Array.isArray(value))
    throw new Error("resources must be an object");
  for (const key of Object.keys(value))
    if (!Object.hasOwn(resourceSpec, key)) throw new Error(`Unknown resource setting: ${key}`);
  const result = {};
  for (const [key, [fallback, maximum]] of Object.entries(resourceSpec)) {
    const number = Object.hasOwn(value, key) ? value[key] : fallback;
    if (!Number.isSafeInteger(number) || number < 1 || number > maximum)
      throw new Error(`${key} must be an integer between 1 and ${maximum}`);
    result[key] = number;
  }
  if (result.maxFileBytes > result.maxWorkspaceBytes)
    throw new Error("maxFileBytes must not exceed maxWorkspaceBytes");
  return Object.freeze(result);
}
class SourceUnavailableError extends Error {
  constructor(file, reason) {
    super(`Source unavailable: ${file} (${reason})`);
    this.details = { code: "source_unavailable", message: this.message, path: file,
      remediation: "Restore readable source content and retry; no complete semantic result was produced." };
  }
}
class ResourceLimitError extends Error {
  constructor(resource, file, observed, limit) {
    super(`${file}: ${resource} observed ${observed}, limit ${limit}`);
    this.details = {
      code: "resource_limit_exceeded", message: this.message, resource,
      path: file, observed, limit,
      remediation: `Raise resources.${resource} in operator-owned FreeFlight startup configuration or open a smaller workspace.`,
    };
  }
}
export class Worker {
  root;
  projects = new Map();
  resources = resourcePolicy();
  budget = new Map();
  querySizes = new Map();
  budgetBytes = 0;
  directoryEntries = 0;
  snapshots = new Map();
  versions = new Map();
  snapshotBytes = 0;
  diskReads = 0;
  contentHashes = 0;
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
    } catch (error) {
      if (["EACCES", "EPERM"].includes(error.code))
        throw new SourceUnavailableError(path.relative(this.root, file), error.code);
      return false;
    }
  }
  checkResource(resource, file, observed) {
    if (observed > this.resources[resource])
      throw new ResourceLimitError(resource, path.relative(this.root, file) || ".", observed, this.resources[resource]);
  }
  recordSize(file, size) {
    const total = this.budgetBytes - (this.budget.get(file) || 0) + size;
    this.checkResource("maxWorkspaceBytes", file, total);
    this.checkResource("maxFiles", file, this.budget.size + (this.budget.has(file) ? 0 : 1));
    this.budgetBytes = total;
    this.budget.set(file, size);
    this.querySizes.set(file, size);
  }
  read(file, force = false) {
    let fd;
    try {
      const canonical = this.resolve(file, true);
      fd = fs.openSync(canonical, "r");
      const stamp = (stat) => [stat.dev, stat.ino, stat.size, stat.mtimeNs, stat.ctimeNs].join(":");
      const before = fs.fstatSync(fd, { bigint: true });
      const size = Number(before.size);
      const signature = stamp(before);
      const cached = this.snapshots.get(canonical);
      if (!force && canonical !== this.freshTarget && cached && cached.signature === signature && performance.now() - cached.verifiedAt < 5000) {
        this.recordSize(canonical, size);
        this.snapshots.delete(canonical);
        this.snapshots.set(canonical, cached);
        return cached.text;
      }
      if (canonical === this.freshTarget) this.freshTarget = undefined;
      this.diskReads++;
      this.checkResource("maxFileBytes", canonical, size);
      const chunks = [];
      let bytes = 0;
      for (;;) {
        const chunk = Buffer.allocUnsafe(Math.min(65536, this.resources.maxFileBytes - bytes + 1));
        const count = fs.readSync(fd, chunk, 0, chunk.length, null);
        if (!count) break;
        bytes += count;
        this.checkResource("maxFileBytes", canonical, bytes);
        this.checkResource("maxWorkspaceBytes", canonical, this.budgetBytes - (this.budget.get(canonical) || 0) + bytes);
        chunks.push(chunk.subarray(0, count));
      }
      if (stamp(fs.fstatSync(fd, { bigint: true })) !== signature)
        throw new Error("Source changed while reading; retry the operation");
      this.recordSize(canonical, bytes);
      const text = Buffer.concat(chunks, bytes).toString("utf8");
      const version = hash(text);
      this.contentHashes++;
      this.lastReadVersion = { file: canonical, version };
      if (this.versions.size >= this.resources.maxFiles && !this.versions.has(canonical))
        this.versions.delete(this.versions.keys().next().value);
      this.versions.set(canonical, { version, signature, bytes, verifiedAt: performance.now() });
      const capacity = Math.min(64 * 1024 * 1024, this.resources.maxWorkspaceBytes);
      if (cached) {
        this.snapshotBytes -= cached.bytes;
        this.snapshots.delete(canonical);
      }
      const cost = Math.max(bytes, text.length * 2);
      if (cost <= capacity) {
        while (this.snapshotBytes + cost > capacity) {
          const oldest = this.snapshots.keys().next().value;
          this.snapshotBytes -= this.snapshots.get(oldest).bytes;
          this.snapshots.delete(oldest);
        }
        this.snapshots.set(canonical, { text, version, bytes: cost, signature, verifiedAt: performance.now() });
        this.snapshotBytes += cost;
      }
      return text;
    } catch (error) {
      if (error instanceof ResourceLimitError || error.message === "Source changed while reading; retry the operation") throw error;
      if (fd !== undefined || this.budget.has(path.resolve(this.root, file)) || (error.code && !["ENOENT", "ENOTDIR"].includes(error.code)))
        throw new SourceUnavailableError(path.relative(this.root, file), error.code || error.message);
      return undefined;
    } finally {
      if (fd !== undefined) fs.closeSync(fd);
    }
  }
  version(file) {
    let canonical;
    try {
      canonical = this.resolve(file, true);
      const stat = fs.statSync(canonical, { bigint: true });
      const signature = [stat.dev, stat.ino, stat.size, stat.mtimeNs, stat.ctimeNs].join(":");
      const retained = this.versions.get(canonical);
      if (canonical !== this.freshTarget && retained && retained.signature === signature && performance.now() - retained.verifiedAt < 5000) {
        this.recordSize(canonical, retained.bytes);
        return retained.version;
      }
    } catch (error) {
      if (error.details) throw error;
      // The bounded reader distinguishes optional missing probes from required source failures.
    }
    const text = this.read(file);
    if (text === undefined) return "missing";
    const cachedVersion = this.versions.get(canonical)?.version || this.snapshots.get(canonical)?.version;
    if (cachedVersion) return cachedVersion;
    if (this.lastReadVersion?.file === canonical) return this.lastReadVersion.version;
    this.contentHashes++;
    return hash(text);
  }
  open({ root, resources }) {
    const policy = resourcePolicy(resources);
    if (typeof root !== "string" || !path.isAbsolute(root))
      throw new Error("root must be an absolute authorized directory");
    const canonical = fs.realpathSync(root);
    if (!fs.statSync(canonical).isDirectory())
      throw new Error("root must be a directory");
    this.close();
    this.resources = policy;
    this.root = canonical;
    return { root: this.root, resources: this.resources, ...this.capabilities() };
  }
  close() {
    for (const p of this.projects.values()) p.service.dispose();
    this.projects.clear();
    this.snapshots.clear();
    this.versions.clear();
    this.snapshotBytes = 0;
    this.lastReadVersion = undefined;
    this.budget.clear();
    this.querySizes.clear();
    this.budgetBytes = 0;
  }
  resolutionStamp(file, metadata) {
    if (!this.allowed(file)) return "missing";
    if (!metadata) return "present";
    const stat = fs.statSync(file, { bigint: true });
    return [stat.dev, stat.ino, stat.size, stat.mtimeNs, stat.ctimeNs].join(":");
  }
  trackResolution(project, file, metadata = false) {
    const key = path.resolve(file);
    if (!project.resolutionProbes.has(key))
      this.checkResource("maxDirectoryEntries", key, project.resolutionProbes.size + 1);
    metadata ||= project.resolutionProbes.get(key)?.metadata;
    project.resolutionProbes.set(key, { metadata, stamp: this.resolutionStamp(key, metadata) });
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
    if (!this.projects.has(key) && this.projects.size >= 8) {
      const oldest = this.projects.keys().next().value;
      this.projects.get(oldest).service.dispose();
      this.projects.delete(oldest);
    }
    this.budget = new Map();
    for (const [cachedKey, cached] of this.projects)
      if (cachedKey !== key)
        for (const [name, bytes] of cached.sizes || []) this.budget.set(name, bytes);
    this.budgetBytes = [...this.budget.values()].reduce((sum, bytes) => sum + bytes, 0);
    this.querySizes = new Map();
    this.directoryEntries = 0;
    const configText = config ? this.read(config) : "";
    let p = this.projects.get(key);
    // Reparse config on each request, including inherited configs. No plugin loader is used.
    const parseHost = {
      useCaseSensitiveFileNames: ts.sys.useCaseSensitiveFileNames,
      readFile: (f) => this.read(f),
      fileExists: (f) => this.allowed(f),
      readDirectory: (dir, extensions, exclude, include, depth) =>
        this.allowed(dir, false)
          ? ts.matchFiles(dir, extensions, exclude, include,
              ts.sys.useCaseSensitiveFileNames, this.root, depth,
              (directory) => {
                const files = [], directories = [];
                if (!this.allowed(directory, false)) return { files, directories };
                const handle = fs.opendirSync(directory);
                try {
                  for (let entry; (entry = handle.readSync()) !== null;) {
                    this.checkResource("maxDirectoryEntries", directory, ++this.directoryEntries);
                    if (entry.isSymbolicLink()) continue;
                    if (entry.isDirectory()) directories.push(entry.name);
                    else if (entry.isFile()) files.push(entry.name);
                  }
                } finally { handle.closeSync(); }
                return { files, directories };
              }, (file) => this.resolve(file, false))
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
    if (parsed.projectReferences?.length) {
      const message = "TypeScript project-reference graphs are not supported by this worker";
      const error = new Error(message);
      error.details = { code: "unsupported_project_references", message,
        path: path.relative(this.root, config),
        remediation: "Open a project without references for scoped analysis. Solution-wide reference graph analysis is not implemented; no complete result was produced." };
      throw error;
    }
    delete parsed.options.plugins;
    parsed.options.noEmit = true;
    parsed.fileNames = parsed.fileNames.filter((file) => {
      if (!inside(this.root, path.resolve(file)))
        throw new SourceUnavailableError(path.relative(this.root, file), "Configured source is outside the authorized workspace");
      try { this.resolve(file, false); return true; }
      catch (error) { throw new SourceUnavailableError(path.relative(this.root, file), error.code || error.message); }
    });
    if (!parsed.fileNames.includes(file)) parsed.fileNames.push(file);
    this.checkResource("maxFiles", file, parsed.fileNames.length);
    // Account every selected project source, including files the service has not read yet.
    for (const source of parsed.fileNames) {
      const canonical = this.resolve(source, false);
      const size = fs.statSync(canonical).size;
      this.checkResource("maxFileBytes", canonical, size);
      this.recordSize(canonical, size);
    }
    const fingerprint = JSON.stringify([parsed.options, parsed.fileNames]);
    // TypeScript retains failed module lookups and package.json resolution.
    // Source versions alone do not invalidate those when a dependency appears
    // or a package's types entry changes. Recheck only paths actually probed.
    const resolutionChanged = p && [...p.resolutionProbes].some(
      ([name, probe]) => this.resolutionStamp(name, probe.metadata) !== probe.stamp,
    );
    if (p && (p.fingerprint !== fingerprint || resolutionChanged)) {
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
      p = { fingerprint, files: parsed.fileNames, options: parsed.options,
        resolutionProbes: new Map() };
      const host = {
        getCompilationSettings: () => p.options,
        getScriptFileNames: () => p.files,
        getScriptVersion: (f) => this.version(f),
        getScriptSnapshot: (f) => {
          const text = this.read(f);
          return text === undefined
            ? undefined
            : ts.ScriptSnapshot.fromString(text);
        },
        getCurrentDirectory: () => this.root,
        getDefaultLibFileName: (o) => ts.getDefaultLibFilePath(o),
        fileExists: (f) => {
          this.trackResolution(p, f);
          return this.allowed(f);
        },
        readFile: (f) => {
          this.trackResolution(p, f, true);
          return this.read(f);
        },
        readDirectory: parseHost.readDirectory,
        directoryExists: (f) => {
          try {
            this.trackResolution(p, f, true);
            return this.allowed(f) && fs.statSync(f).isDirectory();
          } catch (error) {
            if (error.details) throw error;
            return false;
          }
        },
        getDirectories: (dir) =>
          (this.trackResolution(p, dir, true), this.allowed(dir))
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
    p.sizes = this.querySizes;
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
      const text = this.read(target, true);
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
    try { return this.invoke(method, params); }
    catch (error) {
      if (error instanceof ResourceLimitError || error instanceof SourceUnavailableError) this.close();
      throw error;
    }
  }
  invoke(method, params = {}) {
    if (method === "capabilities") return this.capabilities();
    if (method === "open") return this.open(params);
    if (method === "shutdown") {
      this.close();
      return {};
    }
    if (Object.hasOwn(params, "resources"))
      throw new Error("Resource policy is startup-owned and cannot change through a query");
    if (!this.capabilities().operations.includes(method))
      throw new Error(`Unsupported method: ${method}`);
    const file = this.resolve(params.file);
    this.freshTarget = file;
    const p = this.project(file), service = p.service;
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
          `${JSON.stringify({ id: request?.id ?? null, error: error.details || { message: error.message } })}\n`,
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
