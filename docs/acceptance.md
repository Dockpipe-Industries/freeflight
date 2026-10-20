# Release acceptance checklist

## Resource/scaling correction — development candidate (2026-10-20)

The published configure-once preview's 2 MiB C# file cap prevents full loading of
some legitimate repositories. The development correction adds shared validated
operator resource budgets, explicit structured failures and incremental source
snapshot reuse. This section does not claim the fix is published.

- [x] C++ policy validation/forwarding and structured MCP error/recovery tests.
- [x] C# 71,725,175-byte source fixture, largest file 25,587,657 bytes, including
  55,000 generated declarations; exact definition/reference/diagnostic checks.
- [x] C# warm request reads only the 56-byte target, reusing three large snapshots.
- [x] C# trusted 3 MiB source, configuration boundaries, cancellation/recovery,
  preserved-timestamp edits, rename hashes and watcher-bookkeeping overflow.
- [x] TS source above 8 MiB and configured aggregate above 64 MiB with semantic
  assertions; bounded source snapshots, explicit size and I/O errors.
- [ ] Fresh five-platform hosted qualification, including legacy Windows projects.
- [ ] Draft PR reviewed; no merge or replacement preview authorized for this fix.

These controlled fixtures do not establish full Biztraak solution fidelity,
unbounded memory scaling or complete TypeScript project-reference graph support.
See [workspace resources](workspaces.md#source-resources-and-incremental-refresh).

Evidence snapshot: 2026-10-19. Candidate 1ecf18d passed all four native targets,
both website environments and CodeQL. Its Ubuntu 24.04 x64 preview was published
and anonymously downloaded with matching checksums. That core requires glibc 2.38
and cannot run on stock Ubuntu 22.04; a separate Jammy preview at b22a53a passed native/clean-container tests and
was published with verified anonymous downloads. Pop!_OS itself is not tested. PR #12 remains draft after automatic approval review rejected the
ready-for-review transition; production promotion awaits explicit approval.
For subsequent status, consult the linked GitHub Actions and Releases records.
Source009a9c1 subsequently passed all five native targets, both site configurations
and CodeQL, including the same Linux bundle in clean Ubuntu22.04 and Fedora44
containers. That newer candidate was verified after download but not published.
Runtime workspace UX changes after that source require fresh qualification.

## Verified milestones (2026-10-19)

Broad acceptance items below remain unchecked where any required portion is pending.

| Scope | Verified evidence | Still pending |
| --- | --- | --- |
| C++ core | Five hosted native targets at009a9c1; protocol/process CTest 2/2; independent official MCP SDK client | New workspace lifecycle qualification; broader clients |
| TS/JS | 17 worker tests; real-worker definitions/references/diagnostics and incremental changes | Large real repositories and broad configuration fidelity |
| C# | Safe-source semantics/security/cancellation; explicit trusted two-project SDK fixture and actual Roslyn project through C++ MCP, exact cross-project results | Broad solutions/multi-targeting; analyzers unsupported |
| Standalone | Linux x64/ARM64, Windows x64 and macOS ARM64 native/MCPB extraction, hashes and semantics; public Ubuntu22.04 preview b22a53a; clean Fedora44 container candidate009a9c1 | Production publication; Pop!_OS and Bazzite host/client qualification |
| DockPipe | Draft DockPipe PR #168, registry search/version/history and config contract tests plus live discovery | Installation/lifecycle/gateway integration |
| Security audit | Four-platform dependency scans; both site image scans; 11 fail-closed audit-policy tests | Alert #4 fixed without dismissal; ongoing monitoring |
| Branch policy | Implementation on js/dev; master default; protections applied and read back | PRs #2, #1 and #3 merged; PR #12 promotion awaits explicit approval |

CI push run [39335341348](https://github.com/Dockpipe-Industries/freeflight/actions/runs/39335341348)
and CodeQL [39335341377](https://github.com/Dockpipe-Industries/freeflight/actions/runs/39335341377)
qualified 2c29369. The separate CodeQL alert check passed and the fixed bot thread
was resolved. All required checks also passed for both subsequent promotions.
Release verification [39337332446](https://github.com/Dockpipe-Industries/freeflight/actions/runs/39337332446)
failed before publication on HTTP 415 from the artifact API.

No production release, Registry listing or website deployment had been performed
at this snapshot. These records are historical evidence, not a live release feed.

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
- [x] C++23/CMake core, licensed dependencies, tested engine interfaces and CI.

## B — Core server
- [x] Official MCP stdio initialization/discovery/invocation/errors/cancellation/shutdown.
- [x] Workspace authorization, discovery, projects/solutions, language routing and reuse.
- [x] Lazy worker processes, supervision/recovery, structured logs and one configuration.
- [ ] Configure-once runtime open/list/close, dormant startup and optional client-root compatibility qualified on all supported platforms.
- [ ] Bounded memory/concurrency, incremental updates and filesystem change handling.

## C — Language intelligence
- [x] Real C#/.NET Roslyn semantic tests and project-aware trusted MSBuildWorkspace mode.
- [x] Official TypeScript Language Service; TS/JS multi-project configuration tests.
- [ ] Symbols/search, definitions/references/implementations, hover/types/signatures.
- [ ] Compiler/analyzer diagnostics, call/type hierarchy, semantic navigation.
- [ ] Explicit preview rename/code actions/import organization; boundary/change safety.
- [ ] Advertise only verified engine capabilities; mature additional LSP adapters evaluated.
- [x] Public Glider/TGlider capability comparison; legally independent implementation.

## D — Distribution
- [x] Verified prebuilt standalone installation with provisioned internal runtimes.
- [ ] Official MCP Registry metadata/publication verified against real standalone artifact.
- [ ] DockPipe registry discovery, pinned compatible installation/configuration and lifecycle.
- [ ] Real install/start/invoke/stop/restart/update/remove end-to-end test through DockPipe.
- [x] Narrow general DockPipe registry integration in separate branch/draft PR, common configured-server contract.
- [ ] Test missing dependencies, invalid metadata, incompatible platform, startup and permission failures.

The native MCP Registry amendment supersedes the original DockPipe-specific store
publication requirement. Do not create a duplicate FreeFlight distribution for the
DockPipe store. Registry is a discovery service, not an artifact host. Standalone
release takes priority over general gateway completion. Existing MCP-capable
DockPipe packages remain supported by their existing infrastructure. Official
registry, local and remote servers should converge on a common scoped contract;
no new package manager, unrestricted grants or shared secret leakage.

## E — Website and release
- [x] Responsive home/install/docs/languages/MCP/contributing website, configurable hostname.
- [x] Repository-authoritative docs, truthful capability matrix, independent branding.
- [ ] DockPipe-driven Linux/Windows/macOS/supported ARM64 CI and staging verification.
- [ ] Formatting/static analysis/dependency/security scans and artifact checksums.
- [ ] Tested promotion/version/release/publication pipeline; missing services documented.

## F — Hardening
- [ ] Semantic correctness fixtures and real repositories, mixed roots and large solutions.
- [x] Security/path/symlink/concurrent edit/cancellation/crash recovery tests.
- [x] Standard client compatibility and cross-platform smoke tests.
- [x] Reproducible startup/RSS/diagnostic/symbol/reference benchmarks.
- [x] No account/subscription/source telemetry/uploads or automatic repository execution.
- [ ] Contributor onboarding and all limitations documented; all release gates satisfied.

## DockPipe workflow amendment
- [x] Inspect actual DockPipe Cloud workflow files before designing development tasks.
- [x] DockPipe owns setup/build/test/lint/format/check/clean/package/release verification.
- [x] Small composable tasks use actual schema and naming conventions.
- [x] Adapt existing repo.check workflow, required paths and generated-output controls.
- [ ] Dependency/docs/format/secret/binary/stale-output hygiene enforced automatically.
- [x] GitHub Actions call pinned DockPipe workflows; minimal justified fallback only.
- [x] No unnecessary scripts or duplicate orchestration; safe generated-output cleanup.
- [x] Document DockPipe onboarding and native builds; standalone users need no DockPipe.

Final report must include repository/branches, architecture, dependencies/build,
language capabilities, competitor comparison, standalone install, DockPipe package,
gateway, website, CI, tests/benchmarks, and exact unmet criteria/blockers.

## Windows legacy .NET amendment (2026-10-20)

- [x] Intended C# .NET Framework support floor recorded as 4.7 through 4.8.1.
- [x] Controlled non-SDK two-project fixture and Windows-only trusted project semantic tests authored.
- [x] Windows CI verifies representative 4.7, 4.8 and 4.8.1 project loading, exact navigation, reference count and incremental diagnostics (a6456c2, run 39346076164).
- [ ] Broader project types and intermediate targeting-pack versions qualified.

Safe-source analysis does not establish legacy project compatibility. No user's
project target is changed; test target substitutions occur only in disposable copies
of the authored fixture. Legacy MSBuild evaluation remains explicit and trusted.

### Scaling candidate qualification update

Runtime 986b60b: all five hosted native targets, staging/production site validation and CodeQL passed. Reproducible paired Mac benchmarks against ba0c4ce passed candidate correctness checks for C#/TS/JS; see docs/benchmarks.md for raw-receipt location, timings, memory tradeoffs and limitations. This development candidate is not a new published release.
