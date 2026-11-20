import { constants } from "node:fs";
import { open, realpath } from "node:fs/promises";
import { createHash } from "node:crypto";
import { pathToFileURL } from "node:url";
import { within } from "./locations.mjs";

const decoder = new TextDecoder("utf-8", { fatal: true, ignoreBOM: true });

export async function readBoundedBytes(path, maximumBytes) {
  const flags = constants.O_RDONLY | (constants.O_NOFOLLOW ?? 0) | (constants.O_NONBLOCK ?? 0);
  const file = await open(path, flags);
  try {
    const info = await file.stat();
    if (!info.isFile() || info.size > maximumBytes)
      throw new Error("Source exceeds the regular-file limit");

    const bytes = Buffer.allocUnsafe(info.size + 1);
    let count = 0;
    while (count < bytes.length) {
      const { bytesRead } = await file.read(bytes, count, bytes.length - count, count);
      if (bytesRead === 0)
        break;
      count += bytesRead;
    }
    if (count !== info.size)
      throw new Error("Source changed during read");

    return bytes.subarray(0, count);
  } finally {
    await file.close();
  }
}

export class OpenDocuments {
  #client;
  #root;
  #maximumBytes;
  #limit;
  #language;
  #pinned;
  #watched;
  #documents = new Map();
  #version = 0;

  constructor({ client, root, maximumBytes, limit, language, pinned, watched }) {
    this.#client = client;
    this.#root = root;
    this.#maximumBytes = maximumBytes;
    this.#limit = limit;
    this.#language = language;
    this.#pinned = pinned;
    this.#watched = watched;
  }

  async sync(path) {
    const canonical = await realpath(path);
    if (!within(this.#root, canonical) || canonical !== path)
      throw new Error("Source is outside the workspace or changed identity");

    const uri = pathToFileURL(path).href;
    const bytes = await readBoundedBytes(path, this.#maximumBytes);
    const digest = createHash("sha256").update(bytes).digest("hex");
    if (this.#documents.get(path) === digest)
      return uri;

    const text = decoder.decode(bytes);
    const version = ++this.#version;
    if (this.#documents.has(path)) {
      this.#client.notify("textDocument/didChange", {
        textDocument: { uri, version }, contentChanges: [{ text }],
      });
      if (this.#watched)
        this.#client.notify("workspace/didChangeWatchedFiles", { changes: [{ uri, type: 2 }] });
      this.#documents.delete(path);
    } else {
      if (this.#documents.size === this.#limit) {
        const oldest = [...this.#documents.keys()].find((item) => item !== this.#pinned);
        this.close(oldest);
      }
      this.#client.notify("textDocument/didOpen", {
        textDocument: { uri, languageId: this.#language(path), version, text },
      });
    }
    this.#documents.set(path, digest);
    return uri;
  }

  close(path) {
    if (this.#documents.delete(path))
      this.#client.notify("textDocument/didClose", { textDocument: { uri: pathToFileURL(path).href } });
  }

  async refreshOtherThan(path) {
    // Open LSP documents are overlays. Refresh their bytes so a newer copy on
    // disk is not hidden behind the text previously sent to the language server.
    for (const openPath of [...this.#documents.keys()]) {
      if (openPath === path)
        continue;
      try {
        await this.sync(openPath);
      } catch {
        this.close(openPath);
      }
    }
  }
}
