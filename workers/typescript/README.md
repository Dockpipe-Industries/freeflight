# Internal TypeScript / JavaScript engine

FreeFlight's C++ server starts this worker; users configure only FreeFlight. The official Apache-2.0 TypeScript 5.9.3 Language Service supplies semantic analysis. Node 22 or later is required in development and must be provisioned in distribution. No plugins, npm hooks, project scripts, transpilation or emitted code are executed. `dockpipe --workflow workers.typescript` stages the worker and tests in `bin/.local/typescript`, installs the pinned lockfile with npm lifecycle scripts disabled, and runs the semantic suite there. Dependencies never need to be installed under source directories. The workflow uses CMake file-copy commands, `npm ci --ignore-scripts --prefix bin/.local/typescript`, and `node --test bin/.local/typescript/test/worker.test.mjs` as native operations. Launch the staged worker with `node bin/.local/typescript/worker.mjs`.

The internal transport is one UTF-8 JSON request per line: `{ "id": 1, "method": "open", "params": { "root": "/authorized/workspace" } }`. Responses contain the same ID and either `result` or `error.message`. C++ must authorize the root before opening it. `capabilities` reports implemented methods. Queries take `file` (absolute or relative to root) and zero-based UTF-16 `line` / `character` where needed. Rename also requires `newName`; it returns previews and SHA-256 preconditions only and never writes files. `organizeImports` takes a file and returns the same preview edit structure, using the official TypeScript import organization API. Symbols are per document. A definition inside the packaged TypeScript standard library may be returned; other reads remain confined to the authorized root, including symlink targets.

Nearest tsconfig.json or jsconfig.json is respected, including safe in-root inherited configuration. Configuration is re-read for each request; content hashes drive incremental source versions. Source changes become visible on the next request. Each worker retains at most eight language service projects and supports at most 20,000 source files per project and 8 MiB per source. The C++ owner should bound worker RSS, supervise processes and terminate a worker for cancellation; synchronous TypeScript calls cannot consume a cancellation notification mid-request. No cancellation capability is advertised.

Limitations: no project-reference solution builder, no cross-workspace configuration or external symlinked dependency reads, no language service plugins, no cross-project symbol aggregation, type hierarchy or analyzer extensions. In inferred projects only the queried file and its imports are included; configured projects include their configured source set. Configured projects with reference graphs may require querying each root separately. Snapshot reads use filesystem paths, not an OS sandbox; authorization assumes the owner controls workspace changes during requests. Packaging must include this directory's pinned dependency and Node runtime. The worker alone is not the user-facing MCP server.


## Verified operation contracts

| Operation | Input beyond `file` | Result |
| --- | --- | --- |
| `symbols` | none | Document declaration tree with ranges |
| `definition`, `references`, `implementations` | `line`, `character` | Semantic locations; references include write access |
| `hover`, `typeInfo` | `line`, `character` | Official QuickInfo declaration/type display and documentation (`typeInfo` is an explicit alias, not a type graph) |
| `diagnostics` | none | Compiler syntactic and semantic diagnostics |
| `signatureHelp` | `line`, `character` | Parameter displays and selected argument |
| `workspaceSymbols` | `query`, optional `limit` (1–500, default 100) | Search within the project selected by `file`, with `scope: selected-project`, items and truncation flag |
| `callHierarchy` | `line`, `character` | Prepared items, incoming callers, outgoing callees and call-site ranges |
| `rename` | `line`, `character`, `newName` | Rename preview with file hashes |
| `organizeImports` | none | Import edit preview with file hashes |
| `codeActions` | `line`, `character` | Diagnostic quick-fix previews at the selected position |

Code actions are independent alternatives, not a combined edit set. Commands (including package installation) and new-file fixes are excluded. Existing-file edits must be inside the root; same-position insertions are merged in service order, overlapping replacements are rejected, and content must match the analyzed snapshot. Call hierarchy rejects results exceeding 100 roots or 500 edges per direction rather than silently dropping results. Code actions are limited to 100 alternatives. No edit application API is exposed.

Verification on macOS ARM64 with Node 24.11.1 and TypeScript 5.9.3 uses the `workers.typescript` DockPipe workflow. Fixtures check declaration names, exact reference counts, concrete implementation locations, inferred types, incoming/outgoing call identities, edit text/ranges, content hashes, no-write behavior, incremental updates, UTF-16 offsets, malformed transport recovery, and configuration/path boundaries. This fixture suite does not establish full monorepo or cross-platform coverage.
