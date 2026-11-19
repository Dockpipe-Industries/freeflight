import { realpath, stat } from "node:fs/promises";
import { isAbsolute, relative, resolve, sep } from "node:path";
import { fileURLToPath } from "node:url";

export function within(root, file) {
  const path = relative(root, file);
  return path !== ".." && !path.startsWith(`..${sep}`) && !isAbsolute(path);
}

export function validPosition(value) {
  return Number.isInteger(value) && value >= 0 && value <= 0x7fffffff;
}

export async function resultOptions(params, root) {
  const limit = params.limit ?? 30;
  if (!Number.isInteger(limit) || limit < 1 || limit > 100)
    throw new Error("limit must be between 1 and 100");

  const format = params.format ?? "positions";
  if (format !== "positions" && format !== "citations")
    throw new Error("format must be positions or citations");

  let scope = root;
  if (params.scope !== undefined) {
    if (typeof params.scope !== "string" || params.scope.length === 0)
      throw new Error("scope must name a workspace file or directory");
    try {
      scope = await realpath(resolve(root, params.scope));
      const info = await stat(scope);
      if (!within(root, scope) || (!info.isFile() && !info.isDirectory()))
        throw new Error();
    } catch {
      throw new Error("scope must name an existing file or directory within the workspace");
    }
  }
  return { limit, format, scope };
}

export async function compactLocations(response, { root, scope, limit, format, symbols, exact, backendLimit }) {
  const entries = Array.isArray(response) ? response : response ? [response] : [];
  const items = [];
  const seen = new Set();
  const canonicalFiles = new Map();
  let truncated = backendLimit !== undefined && entries.length >= backendLimit;
  for (const entry of entries) {
    if (!entry || (symbols && exact !== undefined && entry.name !== exact))
      continue;

    const location = entry.location ?? entry;
    const point = location.range?.start ?? location.targetSelectionRange?.start;
    const uri = location.uri ?? location.targetUri;
    if (typeof uri !== "string" || !validPosition(point?.line) || !validPosition(point?.character))
      continue;

    let file = canonicalFiles.get(uri);
    if (!canonicalFiles.has(uri)) {
      try {
        const candidate = await realpath(fileURLToPath(uri));
        file = within(scope, candidate) ? relative(root, candidate).split(sep).join("/") : null;
      } catch {
        file = null;
      }
      canonicalFiles.set(uri, file);
    }
    if (!file)
      continue;

    if (symbols && (typeof entry.name !== "string" || entry.name.length > 512)) {
      truncated = true;
      continue;
    }

    let item;
    if (format === "citations") {
      const citation = `${file}:${point.line + 1}`;
      item = symbols ? { name: entry.name, location: citation } : citation;
    } else {
      item = { file, line: point.line, character: point.character };
      if (symbols)
        item.name = entry.name;
    }
    const key = JSON.stringify(item);
    if (seen.has(key))
      continue;
    if (items.length === limit)
      return { items, truncated: true };

    seen.add(key);
    items.push(item);
  }
  return { items, truncated };
}
