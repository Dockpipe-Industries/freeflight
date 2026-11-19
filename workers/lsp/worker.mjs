import { realpath } from "node:fs/promises";
import { basename, isAbsolute } from "node:path";
import { createInterface } from "node:readline";
import { pathToFileURL } from "node:url";
import { configureBackend, languageId, sourceFile } from "./backends.mjs";
import { LspClient } from "./client.mjs";
import { OpenDocuments } from "./documents.mjs";
import { compactLocations, resultOptions, validPosition, within } from "./locations.mjs";

const [language, ...backendArgs] = process.argv.slice(2);
const operations = ["workspaceSymbols", "definition", "references"];
const maxDocuments = 16;
const capabilities = { languages: [language], operations, positionEncoding: "utf-16" };

function failure(code, message) {
  return { code, message };
}

class Workspace {
  #root;
  #backend;
  #client;
  #documents;
  #index;
  #indexError;
  #missingHeaders = new Set();

  async open(params) {
    this.#root = await realpath(params.root);

    try {
      this.#backend = await configureBackend(language, backendArgs, this.#root);
    } catch (error) {
      throw failure("lsp_backend_unavailable", error.message);
    }

    const { name, executable, args, env, options, settings, entry, coverage } = this.#backend;
    const rootUri = pathToFileURL(this.#root).href;
    let finishIndex;
    if (language === "cpp" || language === "python")
      this.#index = new Promise((resolve) => { finishIndex = resolve; });

    this.#client = new LspClient({ name, executable, args, cwd: this.#root, env }, {
      onNotification: ({ method, params }) => {
        if (language === "cpp" && method === "$/progress" && params.token === "backgroundIndexProgress" &&
            params.value?.kind === "end")
          finishIndex();
        if (language === "python" && method === "window/logMessage" &&
            /^(?:Found \d+ source files?|No source files found)\.?$/.test(params.message))
          finishIndex();
        if (language === "pipelang" && method === "window/logMessage" &&
            params.type === 1 && params.message?.startsWith("PipeLang analysis unavailable:"))
          this.#indexError = new Error("PipeLang analysis failed. Check the installed compiler and source roots");
        if (language === "cpp" && method === "textDocument/publishDiagnostics") {
          this.#missingHeaders.delete(params.uri);
          if (params.diagnostics.some(({ code }) => code === "pp_file_not_found")) {
            if (this.#missingHeaders.size === maxDocuments)
              this.#missingHeaders.delete(this.#missingHeaders.values().next().value);
            this.#missingHeaders.add(params.uri);
          }
        }
      },
      onExit: (error) => {
        this.#indexError = error;
        finishIndex?.();
      },
      onRequest: ({ method, params }) => {
        if (method === "workspace/configuration")
          return params.items.map(({ section }) => settings?.[section] ?? null);
        if (method === "client/registerCapability" || method === "client/unregisterCapability")
          return null;
        if (method === "workspace/workspaceFolders")
          return [{ uri: rootUri, name: basename(this.#root) }];
        return undefined;
      },
    });

    this.#documents = new OpenDocuments({
      root: this.#root,
      client: this.#client,
      maximumBytes: Math.min(params.resources.maxFileBytes, 1024 * 1024),
      limit: maxDocuments,
      language: (file) => languageId(language, file),
      pinned: entry,
      watched: true,
    });

    try {
      const initialized = await this.#client.request("initialize", {
        processId: process.pid,
        rootUri,
        workspaceFolders: [{ uri: rootUri, name: basename(this.#root) }],
        capabilities: {
          general: { positionEncodings: ["utf-16"] },
          window: { workDoneProgress: language === "cpp" },
          workspace: { configuration: true, workspaceFolders: true },
        },
        initializationOptions: options,
      });
      const provided = initialized?.capabilities;
      if (!provided?.workspaceSymbolProvider || !provided.definitionProvider || !provided.referencesProvider ||
          (provided.positionEncoding && provided.positionEncoding !== "utf-16"))
        throw new Error(`${name} did not advertise all UTF-16 navigation operations`);

      this.#client.notify("initialized", {});
      if (entry)
        await this.#syncDocument(entry);
    } catch (error) {
      throw failure("lsp_backend_unavailable", error.message);
    }
    return { ...capabilities, root: this.#root, backend: name, coverage };
  }

  async query(method, params) {
    let options;
    try {
      options = await resultOptions(params, this.#root);
    } catch (error) {
      throw failure("lsp_invalid_query", error.message);
    }

    const symbols = method === "workspaceSymbols";
    let result;
    let exact;
    try {
      await this.#waitForIndex();
      if (symbols) {
        if (typeof params.query !== "string" || !params.query.trim() || params.query.length > 256)
          throw failure("lsp_invalid_query", "query must contain 1–256 characters");
        if (params.exact !== undefined && typeof params.exact !== "boolean")
          throw failure("lsp_invalid_query", "exact must be boolean");
        if (params.exact)
          exact = params.query;
        await this.#documents.refreshOtherThan(this.#backend.entry);
        if (this.#backend.entry)
          await this.#syncDocument(this.#backend.entry);
        result = await this.#client.request("workspace/symbol", { query: params.query });
      } else {
        const point = await this.#position(params);
        if (method === "references") {
          if (params.includeDeclaration !== undefined && typeof params.includeDeclaration !== "boolean")
            throw failure("lsp_invalid_query", "includeDeclaration must be boolean");
          point.context = { includeDeclaration: params.includeDeclaration ?? false };
        }
        result = await this.#client.request(`textDocument/${method}`, point);
        if ((!result || (Array.isArray(result) && result.length === 0)) &&
            this.#missingHeaders.has(point.textDocument.uri))
          throw failure("lsp_index_failed", "clangd could not resolve headers for this file. Check the include paths in compile_commands.json");
      }
    } catch (error) {
      throw error.code ? error : failure("lsp_query_failed", error.message);
    }
    if (this.#indexError)
      throw failure("lsp_index_failed", this.#indexError.message);
    return compactLocations(result, { ...options, root: this.#root, symbols, exact });
  }

  async #waitForIndex() {
    if (!this.#index)
      return;

    let timer;
    try {
      await Promise.race([this.#index, new Promise((_, reject) => {
        timer = setTimeout(() => reject(failure("lsp_index_pending",
          `${this.#backend.name} is still indexing. Retry the navigation query once indexing has progressed`)), 20_000);
      })]);
    } finally {
      clearTimeout(timer);
    }
    if (this.#indexError)
      throw failure("lsp_index_failed", this.#indexError.message);
  }

  async #position(params) {
    if (typeof params.file !== "string" || !isAbsolute(params.file) ||
        !validPosition(params.line) || !validPosition(params.character))
      throw failure("lsp_invalid_query", "Supply an absolute file and a zero-based UTF-16 position");

    let path;
    try {
      path = await realpath(params.file);
      if (!within(this.#root, path) || !sourceFile(language, path))
        throw new Error();
      if (this.#backend.sourceRoots && !this.#backend.sourceRoots.some((root) => within(root, path)))
        throw new Error();
    } catch {
      throw failure("lsp_invalid_query", "The file is outside the selected language sources");
    }

    await this.#documents.refreshOtherThan(path);
    const uri = await this.#syncDocument(path);
    return { textDocument: { uri }, position: { line: params.line, character: params.character } };
  }

  async #syncDocument(path) {
    try {
      return await this.#documents.sync(path);
    } catch {
      throw failure("lsp_invalid_query", "The document is unreadable, changed, or exceeds the allowed size");
    }
  }

  close() {
    this.#client?.close();
  }
}

const workspace = new Workspace();
try {
  for await (const line of createInterface({ input: process.stdin, crlfDelay: Infinity })) {
    let request;
    try {
      request = JSON.parse(line);
      const { id, method, params } = request;
      let result;
      if (method === "capabilities")
        result = capabilities;
      else if (method === "open")
        result = await workspace.open(params);
      else if (operations.includes(method))
        result = await workspace.query(method, params);
      else
        throw failure("lsp_invalid_query", "Unsupported operation");
      process.stdout.write(JSON.stringify({ id, result }) + "\n");
    } catch (error) {
      const detail = typeof error?.code === "string" && error.code.startsWith("lsp_")
        ? error : failure("lsp_worker_failed", "Language worker request failed");
      process.stdout.write(JSON.stringify({ id: request?.id ?? null, error: detail }) + "\n");
    }
  }
} finally {
  workspace.close();
}
