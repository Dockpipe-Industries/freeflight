# Release acceptance checklist

Status: implementation in progress; no production release is approved by tests yet.

## Verified milestones (2026-10-19)

Broad acceptance items below remain unchecked where any required portion is pending.

| Scope | Verified evidence | Still pending |
| --- | --- | --- |
| C++ core | macOS ARM64 DockPipe build; protocol/process CTest 2/2; independent official MCP SDK client | Exact-head hosted requalification; full client matrix |
| TS/JS | 17 worker tests; real-worker definitions/references/diagnostics and incremental changes | Large real repositories and broad configuration fidelity |
| C# | Safe-source semantics/security/cancellation; explicit trusted two-project SDK fixture and actual Roslyn project through C++ MCP, exact cross-project results | Broad solutions/multi-targeting; analyzers unsupported |
| Standalone | macOS ARM64 native/MCPB extraction, hashes and semantic tests | Clean exact-head multi-platform qualification and publication |
| DockPipe | Draft DockPipe PR #168, registry search/version/history and config contract tests plus live discovery | Installation/lifecycle/gateway integration |
| Security audit | npm 0 vulnerabilities; NuGet no findings; 11 fail-closed audit-policy tests | Hosted scan completion and ongoing dependency monitoring |
| Branch policy | Implementation moved to js/dev; PR #2 promotes to dev; master remains default | Protection applied/read back; promotion gates pending |

No production release, registry listing or website deployment has been performed.

## Mandatory instruction prerequisite (latest amendment)
- [x] Pause implementation/builds and preserve existing code when gate was requested.
- [x] Inspect actual Cloud YAML schemas and current extracted DorkPipe bootstrap.
- [x] Flesh out core/workers/workflows/security/dependencies/release/site/registry guidance.
- [x] Validate all router/task references and amendment consistency through repo.check.
- [x] Verify requested Homebrew DockPipe upgrade and record exact candidate/toolchain.
- [x] Report gate evidence before resuming implementation or builds.

## A — Repository and infrastructure
- [x] Verify Dockpipe-Industries identity and connected repository permissions.
- [x] Inspect DockPipe, DockPipe Cloud and Nucleon agent guidance and conventions.
- [x] Inspect public Pipelang compiler/Qt boundary; keep future integration decoupled.
- [x] Create public Apache-2.0 repository; master default, staging, dev, js/dev.
- [x] Establish branch protections using separately approved security changes.
- [ ] C++23/CMake core, licensed dependencies, tested engine interfaces and CI.

## B — Core server
- [ ] Official MCP stdio initialization/discovery/invocation/errors/cancellation/shutdown.
- [ ] Workspace authorization, discovery, projects/solutions, language routing and reuse.
- [ ] Lazy worker processes, supervision/recovery, structured logs and one configuration.
- [ ] Bounded memory/concurrency, incremental updates and filesystem change handling.

## C — Language intelligence
- [ ] Real C#/.NET Roslyn semantic tests and project-aware trusted MSBuildWorkspace mode.
- [ ] Official TypeScript Language Service; TS/JS multi-project configuration tests.
- [ ] Symbols/search, definitions/references/implementations, hover/types/signatures.
- [ ] Compiler/analyzer diagnostics, call/type hierarchy, semantic navigation.
- [ ] Explicit preview rename/code actions/import organization; boundary/change safety.
- [ ] Advertise only verified engine capabilities; mature additional LSP adapters evaluated.
- [ ] Public Glider/TGlider capability comparison; legally independent implementation.

## D — Distribution
- [ ] Verified prebuilt standalone installation with provisioned internal runtimes.
- [ ] Official MCP Registry metadata/publication verified against real standalone artifact.
- [ ] DockPipe registry discovery, pinned compatible installation/configuration and lifecycle.
- [ ] Real install/start/invoke/stop/restart/update/remove end-to-end test through DockPipe.
- [ ] Narrow general DockPipe registry integration in separate branch/draft PR, common configured-server contract.
- [ ] Test missing dependencies, invalid metadata, incompatible platform, startup and permission failures.

The native MCP Registry amendment supersedes the original DockPipe-specific store
publication requirement. Do not create a duplicate FreeFlight distribution for the
DockPipe store. Registry is a discovery service, not an artifact host. Standalone
release takes priority over general gateway completion. Existing MCP-capable
DockPipe packages remain supported by their existing infrastructure. Official
registry, local and remote servers should converge on a common scoped contract;
no new package manager, unrestricted grants or shared secret leakage.

## E — Website and release
- [ ] Responsive home/install/docs/languages/MCP/contributing website, configurable hostname.
- [ ] Repository-authoritative docs, truthful capability matrix, independent branding.
- [ ] DockPipe-driven Linux/Windows/macOS/supported ARM64 CI and staging verification.
- [ ] Formatting/static analysis/dependency/security scans and artifact checksums.
- [ ] Tested promotion/version/release/publication pipeline; missing services documented.

## F — Hardening
- [ ] Semantic correctness fixtures and real repositories, mixed roots and large solutions.
- [ ] Security/path/symlink/concurrent edit/cancellation/crash recovery tests.
- [ ] Standard client compatibility and cross-platform smoke tests.
- [ ] Reproducible startup/RSS/diagnostic/symbol/reference benchmarks.
- [ ] No account/subscription/source telemetry/uploads or automatic repository execution.
- [ ] Contributor onboarding and all limitations documented; all release gates satisfied.

## DockPipe workflow amendment
- [x] Inspect actual DockPipe Cloud workflow files before designing development tasks.
- [ ] DockPipe owns setup/build/test/lint/format/check/clean/package/release verification.
- [ ] Small composable tasks use actual schema and naming conventions.
- [ ] Adapt existing repo.check workflow, required paths and generated-output controls.
- [ ] Dependency/docs/format/secret/binary/stale-output hygiene enforced automatically.
- [ ] GitHub Actions call pinned DockPipe workflows; minimal justified fallback only.
- [ ] No unnecessary scripts or duplicate orchestration; safe generated-output cleanup.
- [ ] Document DockPipe onboarding and native builds; standalone users need no DockPipe.

Final report must include repository/branches, architecture, dependencies/build,
language capabilities, competitor comparison, standalone install, DockPipe package,
gateway, website, CI, tests/benchmarks, and exact unmet criteria/blockers.
