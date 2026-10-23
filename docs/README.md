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

Roslyn 5.9.0 (MIT) runs inside .NET 10 with default AdhocWorkspace safe-source
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

## Configure a complete bundle

The development branch adds a **not-yet-published** source-folder configuration:

```json
{
  "trustedRoots": ["/absolute/source-a", "/absolute/source-b"]
}
```

Each folder can contain multiple repositories. It grants both access and permission
for C# design-time MSBuild evaluation, which can execute repository targets/imports.
Trust only folders containing trusted projects. C# project loading requires a
compatible installed SDK and restored dependencies. No worker paths or per-project
solution setting is needed in a complete bundle.

For a Codex MCP client:

```toml
[mcp_servers.freeflight]
command = "/absolute/freeflight/bin/freeflight"
args = ["--config", "/absolute/freeflight.json"]
```

For clients using `mcpServers`:

```json
{"mcpServers":{"freeflight":{"command":"/absolute/freeflight/bin/freeflight","args":["--config","/absolute/freeflight.json"]}}}
```

File queries route lazily from a configured source root to the appropriate
repository/project. Select a repository with `workspace.open` for workspace-wide
queries; resolve ambiguous projects through that tool, without editing MCP config.
See [workspace selection](workspaces.md) for exact routing, reload and access rules.

The published
[`v0.1.0-preview.20261020.trusted.1997d38`](https://github.com/Dockpipe-Industries/freeflight/releases/tag/v0.1.0-preview.20261020.trusted.1997d38)
requires its older `roots` plus `trustedRoots` configuration. It does not implement
the new source-folder routing. Follow its release notes until a replacement bundle
is qualified. `--workspace /absolute/project` remains a safe-source alternative,
and no-argument startup remains dormant. Neither grants MSBuild execution trust.

## Source-build configuration

Developers running an unbundled build may supply an `engines` object with absolute
commands for the staged worker outputs, alongside the chosen startup root policy:

```json
{
  "trustedRoots": ["/absolute/source-a"],
  "engines": {
    "typescript": ["/absolute/node", "/absolute/freeflight/bin/.local/typescript/worker.mjs"],
    "javascript": ["/absolute/node", "/absolute/freeflight/bin/.local/typescript/worker.mjs"],
    "csharp": ["/absolute/dotnet", "/absolute/freeflight/bin/.local/roslyn/bin/FreeFlight.Roslyn/debug/FreeFlight.Roslyn.dll"]
  }
}
```

Use `roots` instead of `trustedRoots` when intentionally choosing safe-source C#
analysis. Configuration is operator-owned and never discovered from repository
files. Worker executables run with the operator's OS privileges.

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
- Incremental refresh occurs on queries. C# combines filesystem invalidation with
  bounded content revalidation; TS/JS checks source and resolution metadata.
  Direct query targets are reread. See [scaling readiness](scaling-readiness.md).
- Thread execution is serialized; long calls can delay other calls.
- Real-world large solution/monorepo qualification remains pending; cross-platform
  results apply only to the exact commits identified in the acceptance evidence.
- Registry publication, DockPipe end-to-end installation and hosting are pending.

See [acceptance](acceptance.md), [comparison](comparison.md), and [release](release.md).

Additional evidence: [real project](real-project-qualification.md), [LSP evaluation](lsp-evaluation.md), [release preparation](release-preparation.md), and [Registry publication](registry-publication.md).

Unreleased source-folder configuration and routing are documented in
[next-release notes](unreleased.md), separately from the published trusted-loading repairs.

For reproducible trusted Roslyn baseline/candidate experiments, see the
[trusted performance workflow](trusted-performance-workflow.md) and
[residual refresh investigation](rc2-residual-refresh-investigation.md), and
[optimization sprint](rc2-refresh-sprint.md).

Same-machine product comparison: [Glider head-to-head](glider-head-to-head.md).

Glider-target experiments: [retained candidate and measurements](glider-target-iteration.md).

Fresh metadata batching: [API proof, qualification and limits](fresh-metadata-batching.md).

Expiry and comparative behavior: [bounded read scheduling](expiry-read-scheduling.md), [Glider evidence and contract boundary](glider-behavior.md).

Guarded search and MCP ownership: [profiling, retained regressions and repeat commands](compilation-search.md).

Native attribution: [identical-binary controls, stage costs and recovery constraints](native-mcp-attribution.md).

Shutdown correction: [deterministic cancellation lifetime proof](shutdown-lifetime.md).

Ordinary timing controls: [balanced order and cadence crossover](query-position-controls.md).

Background recovery: [cooperative handoff proofs, idle costs and matched comparisons](background-recovery.md).

Diagnostics: [successful-sweep allocation stacks and definition boundary costs](allocation-definition-costs.md).

Follow-up: [lexical-only path-string reuse screen and rejection](path-string-screen.md).

Follow-up: [fresh native attribute allocation and all-operation screens](native-attribute-screen.md).

Follow-up: [reference latency and search payload boundary isolation](reference-boundary-costs.md).

Follow-up: [JSON ownership screen, CPU benefit and ordinary-latency rejection](json-response-copies.md).

Follow-up: [core CPU, worker CPU and pacing context controls](copy-pacing-context.md).

Follow-up: [ordinary matched sessions, positions and actual gaps](ordinary-matched-gaps.md).

Follow-up: [baseline reference position and predecessor controls](reference-position-context.md).

Follow-up: [fixed-schedule reference stage/CPU attribution](reference-fixed-attribution.md).

Follow-up: [work-versus-execution counter qualification failures](reference-work-qualification.md).

Follow-up: [structural reference/core review and reader-screen rejection](reference-structural-review.md).

2026-10-23: [Performance checkpoint and remote-execution handoff](performance-handoff.md) records the requested js/dev consolidation, ignored receipt transfer requirements, unaccepted experiments and next A/A controls. Existing qualification limits remain.
