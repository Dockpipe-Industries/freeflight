import { spawn } from "node:child_process";

const maxHeaderBytes = 4096;
const maxBodyBytes = 8 * 1024 * 1024;

export class LspClient {
  #child;
  #buffer = Buffer.alloc(0);
  #length = null;
  #pending = null;
  #failure = null;
  #sequence = 0;

  constructor({ executable, args, cwd, env, name }, { onNotification, onExit, onRequest } = {}) {
    this.#child = spawn(executable, args, {
      cwd, env, stdio: ["pipe", "pipe", "ignore"], windowsHide: true,
    });
    const fail = (message) => {
      this.#fail(message);
      onExit?.(this.#failure);
    };
    this.#child.on("error", () => fail(`Could not start the configured ${name}`));
    this.#child.on("exit", () => fail(`${name} exited`));
    this.#child.stdin.on("error", () => fail(`${name} closed its input`));
    this.#child.stdout.on("data", (chunk) => {
      try {
        this.#read(chunk, onNotification, onRequest);
      } catch {
        fail(`${name} returned an invalid or oversized LSP message`);
      }
    });
  }

  #fail(message) {
    this.#failure ??= new Error(message);
    this.#pending?.reject(this.#failure);
    this.#pending = null;
    this.close();
  }

  #read(chunk, onNotification, onRequest) {
    this.#buffer = Buffer.concat([this.#buffer, chunk]);
    while (this.#buffer.length > 0) {
      if (this.#length === null) {
        const headerEnd = this.#buffer.indexOf("\r\n\r\n");
        if (headerEnd === -1 && this.#buffer.length <= maxHeaderBytes)
          return;

        const header = this.#buffer.subarray(0, headerEnd).toString("ascii");
        const lengths = [...header.matchAll(/^Content-Length: (\d+)\r?$/gim)];
        const length = Number(lengths[0]?.[1]);
        if (headerEnd < 0 || headerEnd > maxHeaderBytes || lengths.length !== 1 ||
            !Number.isSafeInteger(length) || length <= 0 || length > maxBodyBytes)
          throw new Error("Invalid content length");

        this.#length = length;
        this.#buffer = this.#buffer.subarray(headerEnd + 4);
      }

      if (this.#buffer.length < this.#length)
        return;

      const message = JSON.parse(this.#buffer.subarray(0, this.#length).toString("utf8"));
      this.#buffer = this.#buffer.subarray(this.#length);
      this.#length = null;
      if (typeof message.method === "string") {
        if (message.id === undefined) {
          onNotification?.(message);
        } else if (message.method === "window/workDoneProgress/create") {
          this.#send({ id: message.id, result: null });
        } else {
          const response = onRequest?.(message);
          if (response === undefined)
            this.#send({ id: message.id, error: { code: -32601, message: "Unsupported client request" } });
          else
            this.#send({ id: message.id, result: response });
        }
      } else if (this.#pending && this.#pending.id === message.id) {
        const pending = this.#pending;
        this.#pending = null;
        if (message.error)
          pending.reject(new Error("The language server could not resolve this request"));
        else
          pending.resolve(message.result);
      }
    }
  }

  #send(message) {
    const body = JSON.stringify({ jsonrpc: "2.0", ...message });
    this.#child.stdin.write(`Content-Length: ${Buffer.byteLength(body)}\r\n\r\n${body}`);
  }

  notify(method, params) {
    if (this.#failure)
      throw this.#failure;

    this.#send({ method, params });
  }

  request(method, params) {
    if (this.#failure)
      return Promise.reject(this.#failure);
    if (this.#pending)
      return Promise.reject(new Error("LSP request already in progress"));

    const id = ++this.#sequence;
    return new Promise((resolve, reject) => {
      this.#pending = { id, resolve, reject };
      this.#send({ id, method, params });
    });
  }

  close() {
    this.#child.kill();
  }
}
