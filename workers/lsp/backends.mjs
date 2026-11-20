import { constants } from "node:fs";
import { access, mkdir, realpath, rename, rm, stat, writeFile } from "node:fs/promises";
import { createHash, randomUUID } from "node:crypto";
import { dirname, isAbsolute, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { within } from "./locations.mjs";
import { readBoundedBytes } from "./documents.mjs";

const disabledExecutables = fileURLToPath(new URL("./no-executable-search", import.meta.url));

function isolatedEnvironment() {
  const environment = { PATH: disabledExecutables };
  for (const name of ["SystemRoot", "WINDIR", "TEMP", "TMP", "TMPDIR", "LANG", "LC_ALL"]) {
    if (process.env[name] !== undefined)
      environment[name] = process.env[name];
  }
  if (process.platform === "win32")
    environment.NoDefaultCurrentDirectoryInExePath = "1";
  return environment;
}

async function requireFile(path, label, executable = false) {
  if (!path || !isAbsolute(path))
    throw new Error(`Configure an absolute ${label} path`);

  try {
    if (!(await stat(path)).isFile())
      throw new Error();
    await access(path, executable ? constants.X_OK : constants.R_OK);
  } catch {
    throw new Error(`The configured ${label} is missing or inaccessible`);
  }
}

async function requireWorkspacePath(root, path, isDirectory) {
  if (!path || !isAbsolute(path))
    throw new Error("Configure absolute PipeLang entry and source root paths");

  const candidate = await realpath(path);
  const info = await stat(candidate);
  if (!within(root, candidate) || (isDirectory ? !info.isDirectory() : !info.isFile()))
    throw new Error("PipeLang entry and source roots must be within the selected workspace");
  return candidate;
}

async function clangdDatabase(root, database, cache) {
  const maximumBytes = 32 * 1024 * 1024;
  if (!cache || !isAbsolute(cache))
    throw new Error("Configure an absolute clangd cache path");

  let payload;
  try {
    payload = await readBoundedBytes(await realpath(database), maximumBytes);
  } catch {
    throw new Error("The clangd compilation database is unreadable, changed, or exceeds its file limit");
  }

  let records;
  try {
    records = JSON.parse(payload.toString("utf8"));
  } catch {
    throw new Error("The clangd compilation database is not valid JSON");
  }
  if (!Array.isArray(records) || records.length === 0)
    throw new Error("The clangd compilation database has no compile commands");

  const selected = [];
  let entry;
  for (const record of records) {
    if (!record || typeof record.file !== "string" || typeof record.directory !== "string" ||
        !isAbsolute(record.directory))
      throw new Error("The clangd compilation database contains an invalid record");

    const path = resolve(record.directory, record.file);
    if (!within(root, path))
      continue;

    let source;
    try {
      source = await realpath(path);
    } catch {
      continue;
    }
    if (!within(root, source) || !sourceFile("cpp", source))
      continue;

    selected.push({ ...record, file: source });
    entry ??= source;
  }
  if (!entry)
    throw new Error("The clangd compilation database contains no in-workspace source files");

  const digest = createHash("sha256").update(root).digest("hex");
  const directory = join(cache, digest);
  await mkdir(directory, { recursive: true, mode: 0o700 });
  const temporary = join(directory, randomUUID());
  try {
    await writeFile(temporary, JSON.stringify(selected), { mode: 0o600 });
    await rename(temporary, join(directory, "compile_commands.json"));
  } finally {
    await rm(temporary, { force: true });
  }
  return { directory, entry };
}

export function languageId(language, file) {
  if (language === "cpp")
    return file.endsWith(".c") ? "c" : "cpp";
  return language;
}

export function sourceFile(language, file) {
  if (language === "cpp")
    return /\.(?:c|cc|cpp|cxx|h|hh|hpp|hxx|ipp|ixx|cppm|m|mm)$/i.test(file);
  if (language === "python")
    return /\.pyi?$/.test(file);
  return file.endsWith(".pipe");
}

export async function configureBackend(language, args, root) {
  const env = isolatedEnvironment();
  if (language === "python") {
    await requireFile(args[0], "Pyright language-server module");
    if (args.length !== 1)
      throw new Error("Python takes one Pyright language-server module path");

    const pythonSettings = {
      python: { pythonPath: join(disabledExecutables, "python") },
      "python.analysis": {
        diagnosticMode: "workspace",
        autoSearchPaths: true,
        enablePytestSupport: false,
      },
      pyright: { disableOrganizeImports: true },
    };
    return {
      name: "Pyright",
      executable: process.execPath,
      args: [args[0], "--stdio"],
      env,
      settings: pythonSettings,
      coverage: "workspace-static-imports",
    };
  }

  if (language === "cpp") {
    if (args.length !== 3)
      throw new Error("C++ takes clangd, a compilation database and a cache path");

    await requireFile(args[0], "clangd executable", true);
    await requireFile(args[1], "compile_commands.json");
    const { directory, entry } = await clangdDatabase(root, args[1], args[2]);
    return {
      name: "clangd",
      executable: args[0],
      args: ["--enable-config=false", "--background-index", "--pch-storage=memory",
             "--log=error", "-j=2", `--compile-commands-dir=${directory}`],
      env,
      entry,
      coverage: "compilation-database",
    };
  }

  if (language === "pipelang") {
    if (args.length < 4 || args.length > 19)
      throw new Error("PipeLang takes a server, compiler, entry and 1–16 source roots");

    await requireFile(args[0], "PipeLang language-server module");
    await requireFile(args[1], "pipelang-modelc executable", true);
    const entry = await requireWorkspacePath(root, args[2], false);
    const sourceRoots = await Promise.all(args.slice(3).map((path) => requireWorkspacePath(root, path, true)));
    if (!sourceFile(language, entry) || !sourceRoots.some((sourceRoot) => within(sourceRoot, entry)))
      throw new Error("The PipeLang entry must be a .pipe file in one of the configured source roots");

    env.PATH = dirname(args[1]);
    return {
      name: "PipeLang",
      executable: process.execPath,
      args: [args[0], "--stdio"],
      env,
      entry,
      sourceRoots,
      options: { executablePath: args[1], sourceRoots, timeoutMs: 12_000, maxOutputBytes: 4 * 1024 * 1024 },
      coverage: "explicit-import-closure",
    };
  }

  throw new Error("Unsupported LSP worker language");
}
