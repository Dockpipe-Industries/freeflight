# Internal Go engine

FreeFlight starts one Node adapter and one persistent `gopls serve` process per
active Go workspace. C++ handles startup authorization, capability discovery,
timeouts, cancellation, workspace close and process-tree cleanup. gopls owns the
Go package graph, build constraints, type resolution and symbol indexes. The
adapter translates the existing worker protocol to LSP over stdio. There are no
npm dependencies.

The official [gopls LSP navigation operations](https://go.dev/gopls/features/navigation)
provide workspace symbols, definitions and references with a shared package cache.
The gopls CLI is useful for diagnosis, but per-query CLI processes would lose the
live workspace and repeat setup. Using `go/packages` directly would require
FreeFlight to maintain indexing, symbol identity, reference search and refresh.

## Startup setup

This engine is opt-in on the development branch. Use Node 22 or newer and a
compatible installed gopls and Go toolchain. Local qualification used gopls
0.23.0 and Go 1.26.10. Prepopulate the Go module cache through your normal
provisioning process. Choose a dedicated writable cache outside the indexed
workspace. All worker arguments below are absolute paths.

```json
{
  "trustedRoots": ["/source/dockpipe"],
  "engines": {
    "go": [
      "/runtime/bin/node",
      "/source/freeflight/workers/go/worker.mjs",
      "/runtime/bin/gopls",
      "/runtime/go/bin/go",
      "/cache/go/modules",
      "/cache/freeflight/go"
    ]
  }
}
```

Pass this policy using `freeflight --config /absolute/freeflight.json`. The
explicit `engines` map replaces the bundled worker map. Include the existing
C#, JavaScript and TypeScript entries in that map when using them in the same
instance. With the `trustedRoots`-only policy, call `workspace.open` on the
selected Go module or workspace before asking for `engine.capabilities`. This
policy also grants the existing trusted C# project-loading authority if C# is
configured.

A selected root needs a regular `go.mod` or `go.work`. A root-level `go.work`
is honored. Automatic ancestor `go.work` discovery is disabled. gopls uses a
restricted environment, preinstalled Go, offline module resolution, cgo disabled
and no external package driver. It may read toolchain sources, cached dependencies
and project-declared module paths outside the selected root. Only canonical
locations in the selected root are returned. See [Security](../../SECURITY.md).

## MCP queries

Use `semantic.query` with `language: "go"`, the selected absolute `root`,
and an operation from `engine.capabilities`.

| Operation | Arguments |
| --- | --- |
| `workspaceSymbols` | Nonempty gopls search `query`, up to 256 UTF-16 code units |
| `definition` | Absolute `.go` `file`, zero-based UTF-16 `line` and `character` |
| `references` | Same position arguments and optional `includeDeclaration`, default false |

All three accept `limit` from 1 to 100 (default 30) and an optional
workspace-relative or absolute `scope` to return only locations within a file
or directory. Use `exact: true` with symbol lookup to select the exact name.
`format: "citations"` returns compact one-based `file:line` strings and collapses
repeated references on the same line. Symbol citations carry the name too.
Results contain `items` and `truncated`. In the default `positions` format,
each item has a slash-separated workspace-relative `file`,
zero-based `line` and UTF-16 `character`. Symbol results additionally carry
`name`. gopls ranks symbol matches and caps them at 100, so a saturated search
is marked truncated. Reference results cover packages available to the loaded
Go workspace. Incomplete package graphs, cgo and build constraints can reduce
coverage. Out-of-workspace targets are excluded.

A missing or incompatible backend reports `go_backend_unavailable`. An
untrusted root reports `go_workspace_not_trusted`. A failed initial workspace
load reports `go_index_failed`. Check the selected module, installed Go version
and cached dependencies, then retry explicitly. For changes gopls does not pick up
through its file watcher, use `workspace.open` with `reload: true`.

## Verification

Build FreeFlight with `dockpipe --workflow core.build`. Set
`FREEFLIGHT_GO_GOPLS`, `FREEFLIGHT_GO_TOOLCHAIN` and `FREEFLIGHT_GO_MODCACHE`
to absolute paths as in the startup example, then run
`dockpipe --workflow integration.go`. Optionally set `FREEFLIGHT_GO_DOCKPIPE`
to the local DockPipe checkout to run exact snapshot assertions against it.
The selected DockPipe anchors are recorded in the
[navigation report](../../docs/go-navigation.md).
