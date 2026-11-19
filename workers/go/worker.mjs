import { constants } from "node:fs";
import { spawn } from "node:child_process";
import { access, lstat, mkdir, realpath, stat, writeFile } from "node:fs/promises";
import { basename, dirname, isAbsolute, join } from "node:path";
import { createInterface } from "node:readline";
import { pathToFileURL } from "node:url";
import { LspClient } from "../lsp/client.mjs";
import { OpenDocuments } from "../lsp/documents.mjs";
import { compactLocations, resultOptions, validPosition, within } from "../lsp/locations.mjs";

const operations = ["workspaceSymbols", "definition", "references"];
const capabilities = { languages: ["go"], operations, positionEncoding: "utf-16" };
const goplsSymbolLimit = 100;
const [goplsPath, goPath, moduleCache, cacheRoot] = process.argv.slice(2);

function failure(code, message) {
  return { code, message };
}

async function manifest(root, name) {
  const path = join(root, name);
  try {
    const info = await lstat(path);
    if (info.isFile())
      return path;
    throw failure("go_index_failed", `${name} must be a regular file in the workspace root`);
  } catch (error) {
    if (error.code !== "ENOENT")
      throw error;
    return null;
  }
}

async function backendEnvironment(workFile) {
  if (![goplsPath, goPath, moduleCache, cacheRoot].every((path) => path && isAbsolute(path)) ||
      !["go", "go.exe"].includes(basename(goPath).toLowerCase()))
    throw failure("go_backend_unavailable", "Configure absolute gopls, go, module-cache and worker-cache paths");

  try {
    for (const path of [goplsPath, goPath]) {
      if (!(await stat(path)).isFile())
        throw new Error();
      await access(path, constants.X_OK);
    }
  } catch {
    throw failure("go_backend_unavailable", "The configured gopls or go executable is missing or inaccessible");
  }

  // Route platform defaults (including Go telemetry) to a FreeFlight-owned directory.
  const home = join(cacheRoot, "home");
  const config = process.platform === "darwin" ? join(home, "Library", "Application Support") : home;
  const telemetry = join(config, "go", "telemetry");
  try {
    await mkdir(telemetry, { recursive: true, mode: 0o700 });
    await writeFile(join(telemetry, "mode"), "off\n", { mode: 0o600 });
  } catch {
    throw failure("go_backend_unavailable", "The configured Go worker cache is not writable");
  }

  const env = {};
  for (const name of ["SystemRoot", "WINDIR", "TEMP", "TMP", "TMPDIR", "LANG", "LC_ALL"]) {
    if (process.env[name] !== undefined)
      env[name] = process.env[name];
  }
  if (process.platform === "win32")
    env.NoDefaultCurrentDirectoryInExePath = "1";

  return {
    ...env,
    PATH: dirname(goPath),
    HOME: home,
    USERPROFILE: home,
    APPDATA: config,
    LOCALAPPDATA: home,
    XDG_CONFIG_HOME: config,
    GOCACHE: join(cacheRoot, "build"),
    GOPLSCACHE: join(cacheRoot, "gopls"),
    GOMODCACHE: moduleCache,
    GO111MODULE: "on",
    GOENV: "off",
    GOTOOLCHAIN: "local",
    GOPACKAGESDRIVER: "off",
    GOPROXY: "off",
    GOSUMDB: "off",
    GOVCS: "*:off",
    CGO_ENABLED: "0",
    GOWORK: workFile ?? "off",
    GOFLAGS: "-mod=readonly -buildvcs=false",
  };
}

async function checkModule(root, env) {
  await new Promise((resolve, reject) => {
    const check = spawn(goPath, ["list", "-m"], {
      cwd: root, env, stdio: "ignore", windowsHide: true,
    });
    const timer = setTimeout(() => {
      check.kill();
      reject(failure("go_index_failed", "Go module discovery timed out"));
    }, 5_000);
    check.on("error", () => {
      clearTimeout(timer);
      reject(failure("go_backend_unavailable", "Could not start the configured Go executable"));
    });
    check.on("exit", (code) => {
      clearTimeout(timer);
      if (code === 0)
        resolve();
      else
        reject(failure("go_index_failed", "Go could not load module metadata. Check go.mod/go.work and the installed toolchain"));
    });
  });
}

class Workspace {
  #root;
  #gopls;
  #indexFailed = false;
  #maxFileBytes;
  #documents;

  async open(params) {
    this.#root = await realpath(params.root);
    this.#maxFileBytes = params.resources.maxFileBytes;
    const workFile = await manifest(this.#root, "go.work");
    if (!workFile && !await manifest(this.#root, "go.mod"))
      throw failure("go_index_failed", "Select a Go module or workspace root containing go.mod or go.work");

    const env = await backendEnvironment(workFile);
    await checkModule(this.#root, env);
    const rootUri = pathToFileURL(this.#root).href;
    let indexReady, backendFailure;
    const ready = new Promise((resolve) => { indexReady = resolve; });
    let token;
    this.#gopls = new LspClient(
      { executable: goplsPath, args: ["serve"], cwd: this.#root, env, name: "gopls" },
      {
        onNotification: ({ method, params }) => {
          const value = params?.value;
          if ((method === "window/logMessage" || method === "window/showMessage") &&
              params.type === 1 && /initial workspace load|loading workspace folders|loading workspace/i.test(params.message)) {
            this.#indexFailed = true;
            indexReady();
          }
          if (method !== "$/progress")
            return;

          if (value?.kind === "begin" && value.title === "Error loading workspace") {
            this.#indexFailed = true;
            indexReady();
          }
          if (value?.kind === "begin" && value.title === "Setting up workspace")
            token = params.token;
          if (token !== undefined && params.token === token && value?.kind === "end") {
            this.#indexFailed ||= value.message?.startsWith("Error loading packages") ?? false;
            indexReady();
          }
        },
        onExit: (error) => {
          backendFailure = error;
          indexReady();
        },
      },
    );

    const timer = setTimeout(() => {
      this.#indexFailed = true;
      indexReady();
      this.close();
    }, 23_000);
    try {
      const initialized = await this.#gopls.request("initialize", {
        processId: process.pid,
        rootUri,
        workspaceFolders: [{ uri: rootUri, name: basename(this.#root) }],
        capabilities: { general: { positionEncodings: ["utf-16"] }, window: { workDoneProgress: true } },
        initializationOptions: {
          symbolScope: "workspace",
          symbolStyle: "Dynamic",
          fileWatcher: "fsnotify",
          diagnosticsTrigger: "Save",
          telemetryPrompt: false,
        },
      });
      const server = initialized?.capabilities;
      if (!server?.workspaceSymbolProvider || !server.definitionProvider || !server.referencesProvider ||
          (server.positionEncoding && server.positionEncoding !== "utf-16"))
        throw failure("go_backend_unavailable", "gopls did not advertise the required UTF-16 navigation operations");

      this.#gopls.notify("initialized", {});
      await ready;
      this.#checkIndex();
      if (backendFailure)
        throw backendFailure;

      this.#documents = new OpenDocuments({
        root: this.#root,
        client: this.#gopls,
        maximumBytes: Math.min(this.#maxFileBytes, 1024 * 1024),
        limit: 4,
        language: () => "go",
      });
    } catch (error) {
      this.#checkIndex();
      throw error.code ? error : failure("go_backend_unavailable", error.message);
    } finally {
      clearTimeout(timer);
    }
    return { ...capabilities, root: this.#root, mode: "gopls-offline" };
  }

  #checkIndex() {
    if (this.#indexFailed)
      throw failure("go_index_failed", "gopls could not index the workspace. Check go.mod/go.work, the installed Go version and the offline module cache");
  }

  async query(method, params) {
    let options;
    try {
      options = await resultOptions(params, this.#root);
    } catch (error) {
      throw failure("go_invalid_query", error.message);
    }

    this.#checkIndex();
    let response;
    let exact;
    const symbols = method === "workspaceSymbols";
    try {
      if (symbols) {
        if (typeof params.query !== "string" || !params.query.trim() || params.query.length > 256)
          throw failure("go_invalid_query", "query must contain 1–256 characters");
        if (params.exact !== undefined && typeof params.exact !== "boolean")
          throw failure("go_invalid_query", "exact must be boolean");

        if (params.exact) {
          if (/\s/.test(params.query))
            throw failure("go_invalid_query", "exact search requires a single symbol name");
          exact = params.query;
        }
        await this.#documents.refreshOtherThan();
        const query = exact === undefined ? params.query : `'${exact}`;
        response = await this.#gopls.request("workspace/symbol", { query });
      } else {
        const point = await this.#point(params);
        if (method === "references") {
          if (params.includeDeclaration !== undefined && typeof params.includeDeclaration !== "boolean")
            throw failure("go_invalid_query", "includeDeclaration must be boolean");
          point.context = { includeDeclaration: params.includeDeclaration ?? false };
        }
        response = await this.#gopls.request(`textDocument/${method}`, point);
      }
    } catch (error) {
      this.#checkIndex();
      throw error.code ? error : failure("go_query_failed", error.message);
    }
    this.#checkIndex();
    return compactLocations(response, {
      ...options,
      root: this.#root,
      symbols,
      exact,
      backendLimit: symbols ? goplsSymbolLimit : undefined,
    });
  }

  async #point(params) {
    if (typeof params.file !== "string" || !isAbsolute(params.file) ||
        !validPosition(params.line) || !validPosition(params.character))
      throw failure("go_invalid_query", "Supply an absolute .go file and a zero-based UTF-16 line and character");

    let file;
    try {
      file = await realpath(params.file);
      const info = await stat(file);
      if (!file.endsWith(".go") || !within(this.#root, file) || !info.isFile() || info.size > this.#maxFileBytes)
        throw new Error();
    } catch {
      throw failure("go_invalid_query", "The Go file is outside the workspace, unreadable, or exceeds the file limit");
    }
    await this.#documents.refreshOtherThan(file);
    const uri = pathToFileURL(file).href;
    // An open document lets gopls retain the package's typed state for
    // later queries. Larger files still use its on-disk snapshot.
    try {
      await this.#documents.sync(file);
    } catch {
      this.#documents.close(file);
    }

    return { textDocument: { uri }, position: { line: params.line, character: params.character } };
  }

  close() {
    this.#gopls?.close();
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
        throw failure("go_invalid_query", "Unsupported Go operation");
      process.stdout.write(JSON.stringify({ id, result }) + "\n");
    } catch (error) {
      const detail = typeof error?.code === "string" && error.code.startsWith("go_")
        ? error : failure("go_worker_failed", "Go worker request failed");
      process.stdout.write(JSON.stringify({ id: request?.id ?? null, error: detail }) + "\n");
    }
  }
} finally {
  workspace.close();
}
