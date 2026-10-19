# FreeFlight documentation

This repository is the authoritative documentation source. The Qt WebAssembly website
links here and must not claim more than the verified implementation.

## Architecture and dependencies

The C++23 core owns MCP framing/version negotiation, bounded request dispatch,
startup-authorized roots, project discovery, lazy worker routing and lifecycle.
Each configured language/root gets a reusable worker, limited to eight workers.
At most sixteen calls are pending; calls execute serially while the input thread
continues processing cancellation. Cancellation terminates an active worker;
the next explicit request starts a fresh one. Failed requests are never replayed.
Stdout is protocol-only. Stdin EOF cancels outstanding work and reaps workers.
Incoming JSON and worker responses reject nesting beyond 128 containers before
constructing deeply recursive values.

The protocol adapter uses nlohmann JSON 3.12.0 (MIT), pinned by archive SHA-256.
We evaluated hkr04/cpp-mcp (documents the older 2025-03-26 protocol) and
mpsm/mcp-cpp (a Rust clangd application, not a C++ SDK). Neither established a
drop-in current C++ SDK fit. This implementation adds no networking framework.
MCP revisions implemented are 2026-07-28 and legacy 2025-11-25/2025-06-18.
Modern requests use per-request metadata and `server/discover`; legacy clients
use `initialize` then `notifications/initialized`. Streamable HTTP is pending.

Roslyn 4.14.0 (MIT) runs inside .NET 10 with default AdhocWorkspace safe-source
loading. Explicit startup-only `--trusted-msbuild` enables MSBuildWorkspace project
evaluation, which can execute repository targets/imports and requires a compatible
.NET SDK. It must only be used for trusted projects. TypeScript 5.9.3 (Apache-2.0)
runs inside Node. Semantic compilation excludes repository plugins, custom
generators and analyzers. See SECURITY.md and worker READMEs for boundaries.

## Developer setup

See [developer onboarding](development.md) for setup, startup and safe cleanup.

Use DockPipe `build`, `test`, `repo.check`, `site.build`, `core.build`, `core.test`,
`workers.typescript`, `workers.roslyn`, and `integration.test` workflows. All task
logic lives in workflow YAML and focused workflow assets. CI calls those tasks.
Native alternatives are intentionally available:

```sh
cmake -S . -B bin/.local/build -DCMAKE_BUILD_TYPE=Release
cmake --build bin/.local/build --config Release
ctest --test-dir bin/.local/build -C Release --output-on-failure
dotnet build workers/roslyn/FreeFlight.Roslyn.csproj -p:RestoreLockedMode=true --artifacts-path bin/.local/roslyn
```

The TypeScript workflow stages source/lockfiles/tests under bin/.local/typescript
and runs npm ci --ignore-scripts there. Do not install node_modules in source.
Cleanup must target only identified generated artifacts; never use broad git clean.

## Development configuration

```json
{
  "roots": ["/absolute/project"],
  "engines": {
    "typescript": ["/absolute/node", "/absolute/freeflight/bin/.local/typescript/worker.mjs"],
    "javascript": ["/absolute/node", "/absolute/freeflight/bin/.local/typescript/worker.mjs"],
    "csharp": ["/absolute/dotnet", "/absolute/freeflight/bin/.local/roslyn/bin/FreeFlight.Roslyn/debug/FreeFlight.Roslyn.dll"]
  }
}
```

Run the compiled server with `--config /absolute/freeflight.json`. Configuration
is operator-owned, never discovered or executed from the opened workspace.
The bundle's `--workspace` mode derives trusted runtime paths from installation.

For a Codex MCP client, configure its normal stdio server entry:

```toml
[mcp_servers.freeflight]
command = "/absolute/freeflight/bin/freeflight"
args = ["--workspace", "/absolute/project"]
```

Other clients supporting `mcpServers` can use:

```json
{"mcpServers":{"freeflight":{"command":"/absolute/freeflight/bin/freeflight","args":["--workspace","/absolute/project"]}}}
```

## Engine contract

Workers exchange bounded newline JSON objects `{id,method,params}` and reply with
`{id,result}` or `{id,error}`. The core invokes `capabilities`, then `open {root}`,
then only operations advertised in `operations`. Root/file paths are canonical;
workers independently enforce them. Results use zero-based UTF-16 locations.
Preview edits include original-file hashes and must not be applied after changes.
No apply-edits operation exists yet. A future native Pipelang engine should consume
a stable versioned semantic projection, not private compiler/Qt internals. No
Pipelang API, SDK, LSP support or additional language support is claimed today.

## Known limitations

- Default C# source-only analysis does not reproduce MSBuild references or project
  settings. Explicit trusted MSBuildWorkspace mode passes a controlled two-project
  SDK fixture and the actual FreeFlight Roslyn project; broad solution/multi-targeting/generated-source fidelity is pending.
- Worker root authorization is not an OS sandbox; filesystem races remain possible
  against a hostile concurrent local writer. No source mutation is supported.
- Discovery scans at most 50,000 entries; worker/project/file limits are documented.
- Incremental worker refresh occurs on queries; no native filesystem watcher yet.
- Thread execution is serialized; long calls can delay other calls.
- Real-world large solution/monorepo qualification and exact-head cross-platform gates remain pending.
- Registry publication, DockPipe end-to-end installation and hosting are pending.

See [acceptance](acceptance.md), [comparison](comparison.md), and [release](release.md).

Additional evidence: [real project](real-project-qualification.md), [LSP evaluation](lsp-evaluation.md), [release preparation](release-preparation.md), and [Registry publication](registry-publication.md).
