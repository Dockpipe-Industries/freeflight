# Internal Python, C++, and PipeLang engines

One FreeFlight instance can register these optional project engines alongside
Go, C#, JavaScript, and TypeScript. Each engine uses the existing C++ MCP
authorization, discovery, request limits, cancellation, and process custody.
A single Node worker translates requests for the selected backend through the
same bounded stdio transport used by Go. The backends own language semantics.

## Startup configuration

Use Node 22 or later. Configure each backend with absolute paths. Every project
root must have an explicit startup `trustedRoots` entry or be a descendant of
one. The following is an `engines` map fragment for an operator-owned FreeFlight
configuration. An explicit map replaces the bundled map, so include the
entries for any other engines used by that server.

```json
{
  "python": [
    "/runtime/bin/node",
    "/freeflight/workers/lsp/worker.mjs",
    "python",
    "/runtime/pyright/langserver.index.js"
  ],
  "cpp": [
    "/runtime/bin/node",
    "/freeflight/workers/lsp/worker.mjs",
    "cpp",
    "/runtime/clangd/bin/clangd",
    "/build/workspace/compile_commands.json",
    "/cache/freeflight/clangd"
  ],
  "pipelang": [
    "/runtime/bin/node",
    "/freeflight/workers/lsp/worker.mjs",
    "pipelang",
    "/runtime/pipelang/language-server.js",
    "/runtime/pipelang/bin/pipelang-modelc",
    "/workspace/workflow/src/Entry.pipe",
    "/workspace/workflow/src",
    "/workspace/sdk/src"
  ]
}
```

Call `workspace.open` on the desired root and then `engine.capabilities`.
Configuration is local and opt-in. Default bundle provisioning remains a
separate release task.

| Engine | Coverage and prerequisites |
| --- | --- |
| Python | Pyright's tracked source workspace and static imports. Use the published Node language-server module with its package and built-in typeshed intact. The adapter supplies no usable interpreter and isolates executable search. Dynamic imports and interpreter-dependent dependencies have limited coverage. [Pyright import resolution](https://github.com/microsoft/pyright/blob/main/docs/import-resolution.md) |
| C++ | clangd's index for an operator-supplied compilation database. Supply all generated headers, compile options, and system include paths needed by the selected toolchain. The worker copies in-root compile units into the configured writable cache. It disables clangd config discovery and compiler probing. [clangd compile commands](https://clangd.llvm.org/design/compile-commands) |
| PipeLang | Ordinary-model semantics for the listed `.pipe` source roots and the entry's import closure. Configure the owning compiler's headless editor server and a compatible installed `pipelang-modelc`. Select one entry file and up to sixteen source roots, all within the authorized workspace. [PipeLang assessment](../../docs/go-navigation.md#what-pipelang-already-exposes) |

## Queries and freshness

The operations are `workspaceSymbols`, `definition`, and `references`.
Symbol lookup accepts `query` and optional `exact: true`. File queries use an
absolute `file`, zero-based UTF-16 `line` and `character`. References can include
the declaration with `includeDeclaration: true`.

All queries accept a `limit` from 1 to 100 (default 30), an optional in-workspace
file or directory `scope`, and `format: "citations"` for one-based `file:line`
output. The default `positions` format returns exact zero-based positions.
Citations collapse multiple occurrences on the same line. `truncated` reports
result limiting. Backend coverage depends on what the selected project can index.

Python and C++ queries wait for initial indexing. A long-running index can
return `lsp_index_pending`. Retry explicitly. Backend failure returns a
structured error and a later explicit call can start a new worker.

Open documents are bounded to 16 files and 1 MiB per file, or the operator's
lower file limit. The adapter refreshes open texts from disk and retains no
result cache. For changes to unopened dependencies or project metadata, use
`workspace.open` with `reload: true`. PipeLang references are closure-scoped.
They cover checked locals, parameters, and supported source methods.

## Local verification

After `core.build`, run `dockpipe --workflow integration.lsp` with the desired
backends provisioned. Set `FREEFLIGHT_PYRIGHT` to the Node module,
`FREEFLIGHT_CLANGD` to the clangd executable, and
`FREEFLIGHT_PIPELANG_SERVER` and `FREEFLIGHT_PIPELANG_COMPILER` to the
PipeLang executables from the configuration example. Missing test inputs
skip the corresponding evidence. For the real-source checks, optionally set
`FREEFLIGHT_CPP_TEST_DATABASE` to a compilation database for FreeFlight and
`FREEFLIGHT_GO_DOCKPIPE` to the DockPipe checkout. The Python real-source check
uses the existing FreeFlight packaging helper files.
