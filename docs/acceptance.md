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

### Focused pre-promotion review

See [scaling readiness](scaling-readiness.md) for corrected zero-read claims, exact invalidation tests, resource/failure semantics and benchmark regressions. Follow-up fixes address stale TS import/package resolution and the initial trusted Roslyn text-loader path. Local worker checks pass; this follow-up requires new exact-head CI before promotion/publication.


### Local trusted-loading repair after published 57851e3

- [x] Controlled warning-only NU1603/NU1701/NU1903 loading preserves warnings;
  actual errors, warning/error collisions and promoted warnings remain fatal.
- [x] Operator-owned per-root trust, read-only siblings, nested selection,
  workspace reload and truthful loaded status pass local protocol/bundle tests.
- [x] Exact namespace/partial-type outline positions and C# definition/reference
  results pass through the packaged C++ MCP endpoint on a controlled .NET 8 fixture.
- [x] Local macOS ARM64 tar/MCPB and official-client validation pass.
- [x] Full-bundle before/after benchmark retains exact semantic/freshness/boundary
  assertions and reports cold/RSS tradeoffs and tail regression without filtering.
- [x] Experimental optimization isolated and reverted after unresolved p90 regression.
- [ ] Future performance optimization explained and qualified; no speedup retained.
- [ ] These local repairs qualified on Linux/Windows and hosted CI; reported private
  solution compatibility verified by its operator.
- [ ] Repair passes exact-head hosted CI after authorized commit/push.
- [ ] Repair promoted/published (still requires separate authorization).

See [unreleased notes](unreleased.md), [task log](task-log.md) and
[hot-path evidence](hotpath-performance.md). Earlier release records are historical;
this update does not mark the full initial-release checklist complete.


### Configure-once source folders (2026-10-20, unreleased)

- [x] `trustedRoots` alone supplies access and trusted design-time loading policy.
- [x] Two source folders, separate repositories and nested solution routing pass
  local packaged C# semantic tests; same-name symbols resolve to the correct file.
- [x] New projects, source edits, TS/JS navigation and workspace boundaries pass.
- [x] Ambiguity returns structured candidates; tool-level selection needs no config edit.
- [x] Legacy safe-source and per-root policies remain covered by protocol tests.
- [x] Documentation distinguishes this UX from the published 1997d38 preview.
- [ ] Exact-head hosted cross-platform qualification for this new UX.
- [ ] Separate authorization/report checkpoint before promotion or publication.

The previous trusted-loading repair was qualified and published as
`v0.1.0-preview.20261020.trusted.1997d38`; its historical pending entries above
are superseded by the publication evidence in the task log. This new source-folder
UX is a separate, unreleased change and does not claim private-solution qualification.

### External compiler-input regression (2026-10-20, unreleased)

- [x] Old native preview reproduces boundary failure locally with Test SDK 16.0.1/17.8.0.
- [x] Exact external sources retained in trusted analysis without directory/query grants.
- [x] Rename refuses external edits; shared contexts refresh; symlink/FIFO tests pass locally.
- [x] Complete local native bundle and official-client regression qualification pass.
- [ ] Hosted Linux baseline reproduction and corrected cross-platform qualification.
- [ ] Operator verifies the original Linux solution/test project and navigation control.
- [ ] Separate promotion/publication approval and normal protected promotion.

## Consolidated dependency review (2026-10-20)

TypeScript 6.0.3: 34/34 worker tests passed on macOS ARM64 / Node 24.22.0,
including resource boundaries, resolution refresh, exact semantic results and
read-only previews. Baseline includes external compiler-input repair a446d37.
Combined native and hosted qualification is pending. TypeScript 7.0.2 and StringTools
18.11.0 remain held for API and net10.0 incompatibility respectively; see task log.
Setup-python v7.0.0 has exact-head green bot CI; consolidated workflow publication
is pending existing workflow-write permissions. This is not merge/release approval.

Local combined qualification completed on macOS ARM64 with Node 24.22.0, .NET
SDK 10.0.402 / runtime 10.0.13: core tests, 34 TypeScript tests, Roslyn safe/trusted
suites, real MCP integration, real-project integration, official MCP SDK, lint,
strict dependency audits (no findings) and registry schema validation passed.
The native package exercised both external compiler-input fixtures (Test SDK
16.0.1 and 17.8.0), including routing, read-only definitions and selection/reload;
both passed. Local site compilation lacks Qt/WASM tooling; hosted site jobs remain
required. A separate current-baseline TypeScript 7.0.2 probe passed 6/34 and failed
28/34 tests (missing classic API, including ts.sys).

Draft PR #32 targets js/dev and is textually mergeable. Hosted five-platform/site
qualification is pending; promotion policy and CodeQL passed on its initial head.
No remote js/dev changes were made. The unpublished setup-python patch remains a
separate local deliverable pending an authorized workflow writer.

## Approved .NET 11 RC2 combined qualification (2026-10-20)

The user explicitly requested .NET 11 RC2 in draft PR #32. The worker now targets
net11.0 with pinned SDK 11.0.100-rc.2.26504.105 (prerelease explicitly enabled),
StringTools 18.11.0 and TypeScript 6.0.3. Original net8/net10 project fixtures and
legacy Framework targets remain unchanged. This supersedes the earlier StringTools
hold; TypeScript 7 remains held because 28/34 current API tests fail.

On macOS ARM64, the complete DockPipe check and package.native workflows passed
with .NET 11 RC2, including locked restore, zero-warning build, trusted real-project
loading, audits, self-contained package semantics and both external Test SDK input
fixtures (16.0.1 and 17.8.0). Both Roslyn build hosts remain in the native package.
Windows qualification now additionally verifies packaged non-SDK 4.7/4.8/4.8.1 and
SDK-style net48; these new Windows cases await hosted execution. Receipts explicitly
distinguish the in-process Locator from Roslyn's remote build-host selection.

The user confirmed saving workflow permission on the existing token. The consolidated
workflow changes include the five setup-python v7 replacements and CI's exact RC2
SDK pin. No authentication routing or credentials are replaced by this work.

Hosted RC2 source 6e7b9a5 subsequently passed all native/site jobs and CodeQL in
runs 39433227935 and 39433227841. Staging promotion PR #34 passed and merged.
Production/master promotion is paused for user acceptance. Site deployment
preparation is separate from activation: no hosted FreeFlight website or new RC2
prerelease is established by prepared files or local validation.
The preceding .NET 10 head 3a8ff3f passed all ten hosted checks, including all five
platforms, both sites and CodeQL. A fresh hosted run must qualify this RC2 revision.

PR #35 implementation 77e00b5 passed all ten hosted checks (CI 39454236338,
CodeQL 39454236572) and 78 local policy tests. It remains draft and unmerged.
The subsequent Cloud architecture comparison places deployment on hold: its
manual privileged receiver setup is withdrawn pending alignment with Cloud's
state-owned identities and unprivileged static delivery. Test success is not
evidence of deployment readiness, infrastructure setup or publication.

The static alignment replacement passes 88 local release/delivery/infrastructure
policy tests and four isolated Cloud routing/coordinator tests. A retained qualified
CI site artifact also passed the new bounded static bundle decoder. Five POSIX
filesystem activation tests apply to the Linux receiver and run on Linux/macOS;
Windows retains payload/scope and infrastructure policy tests. Cloud extension
commit 3f80112 is local-only and unpushed. Terraform validation and disposable Linux
bootstrap validation have not run; live setup remains blocked pending those checks,
provider/state access approval and review. No deployment result is claimed.

Follow-up validation: Terraform 1.13.5 (official checksum-pinned, task-local) passed
backend-disabled schema validation of the authored Cloud extension with the pinned
DigitalOcean 2.104.0 and TLS 4.1.0 providers. Only the disposable scratch lockfile
received macOS package hashes; the authored lock was unchanged. No state, credentials,
plan or apply was used. Hosted Windows exposed an unconditional Unix `pwd` import;
it is now deferred until actual Linux host installation. Fresh hosted CI is required.

Disposable Ubuntu bootstrap job 118835315216 passed in CI run 39482701813 at
source e75b42c. The real installation and repeat setup, restricted SSH command/user/
forwarding rejection, exact static serving, private ingress, first-install failure,
upgrade rollback, failed-rollback lock retention and pre-existing site/admin-policy
preservation all passed. Keys were ephemeral test fixtures on a disposable runner;
no staging credentials or infrastructure were involved. This validates the local
host contract, not live provider/state/TLS readiness or deployment authorization.

- 2026-10-20: First-level staging hostname `freeflight-staging.dockpipe.com` is now
  used consistently by site generation, receipt validation and receiver/bootstrap.
  Local release policy and hostname rollback fixtures passed. The real Nginx
  migration is included in disposable Ubuntu CI; live/hosted status is not implied
  by these authored tests.

- 2026-10-20: Approved hostname-only live migration verified valid TLS and health
  for `freeflight-staging.dockpipe.com`; existing Cloud services and operator access
  policy preserved. Old nested-host DNS, ingress and transform removed with verified
  readback. No site activation or automatic-delivery enablement performed.

- 2026-10-21: RC2 trusted refresh investigation on M6 confirmed whole-graph ancestor
  validation and stale core capability counters. Native baseline/candidate suites
  and trusted boundary/overflow checks passed. A narrow leaf-metadata experiment
  improved pooled medians but regressed one session's p90 and was removed; warm
  performance acceptance remains open. See `docs/rc2-warm-refresh-investigation.md`.
  No Linux rerun, syscall-count reduction, packaged-platform pass or deployment
  is claimed.

- 2026-10-21 follow-up: A combined trusted-refresh admission optimization is retained
  on the isolated investigation branch. Native semantic/security suites, trusted
  mutation/overflow, external rename/symlink regressions, and a generated deterministic
  pre-read ancestor-swap check passed. All 2,880 measured responses in the combined
  short/long/small comparisons passed; full-graph per-session p90 improved, while
  one small-graph reference p90 regressed. See `docs/rc2-warm-refresh-followup.md`.
  Kernel syscall tracing, complete packaged/platform qualification and live core
  telemetry remain open; no deployment or universal performance claim is made.

## Residual trusted refresh — local candidate (2026-10-21)

- [x] Workflow-owned baseline/candidate source, fixture, toolchain and binary receipts.
- [x] Identical-source control; unfavorable small-graph noise retained.
- [x] Separate ordinary timing, instrumented allocation/GC/JIT observations and expiry.
- [x] Native semantic/security suites and mutation/overflow qualification for both variants.
- [x] Test-only guard proves failed Refresh preserves committed solution/maps for the
  exercised late missing-input, ancestor replacement and missing-input cases.
- [x] Three fresh sessions per variant show lower full-graph median/p90 in the first
  comparison; small-graph p90 and expiry regressions remain explicitly recorded.
- [ ] Self-contained packaged, full MCP and hosted-platform qualification of this candidate.
- [ ] Operator Linux/private-solution performance retest of this candidate.

See [residual investigation](rc2-residual-refresh-investigation.md) and
[workflow usage](trusted-performance-workflow.md). No new release or promotion is
claimed or authorized by these local checks.

## Trusted-refresh sprint — local qualification (2026-10-21)

- [x] Retained named shipped/local baselines, identical-source control, raw outliers,
  and rejected two/eight-worker experiments; no median-only acceptance gate.
- [x] Four-worker bound and serial small-graph fallback exercised across six sizes;
  explicit 256-file crossover check, including reversed first-pair ordering.
- [x] Expanded normal trusted tests cover 258 members, resource-error precedence,
  ancestor/leaf replacement and external read-only inputs.
- [x] Five test-only failed-refresh guards per variant, including a deterministic
  post-admission ancestor swap rejected before any additional source bytes read.
- [x] Native core tests and actual worker-project semantics through C++ MCP passed.
- [x] Final named-baseline/MCP comparisons and single-processor qualification.
- [x] Paced comparison retained alongside unpaced results, including CPU and maximum-latency regressions.
- [x] Rejected parallel admission after paced CPU/search/tail regressions; restored
  the measured serial runtime while retaining expanded tests and experiment receipts.
- [ ] Hosted self-contained/platform qualification and staging publication.

See [sprint evidence](rc2-refresh-sprint.md). M6 synthetic measurements do not
establish Linux/Biztraak/Glider performance. No production promotion is authorized.

## Same-machine Glider comparison (2026-10-21)

Published FreeFlight `97c1342d9234` and official Glider 13.3.0 completed the local
`benchmark.trusted.glider` workflow: 24 fresh processes, both synthetic graph sizes,
unpaced and paced runs, all 9,600 measured semantic checks passed. Complete ranges
are checked where exposed; missing Glider fields and cached-key interaction are
disclosed. All maxima and setup failures are retained. Glider leads tiny operations;
broad-search ordering reverses with cadence. No runtime or remote changes.
See [full evidence and repeat command](glider-head-to-head.md).

## Glider-target local iteration (2026-10-21)

Scratch reuse passed worker/native security, cancellation, mutation and transaction
qualification plus 7,200 three-product MCP semantic checks. Full-expiry diagnostic
allocation fell 48.0 to 21.7 MB, but ordinary latency remained mixed and several
p90/max values regressed. Candidate rejected for latency; shipped runtime restored.
The rejected patch, raw failures and all measurements remain local. See
[iteration evidence and design proof obligations](glider-target-iteration.md).
No push, PR, release, deployment or active configuration change.

## Fresh Darwin metadata batching (2026-10-21)

Request-local bounded native metadata batching passed focused malformed-record,
ancestor replacement, symlink, resource, cancellation and descriptor lifetime
proofs plus existing worker/native semantic, security, mutation and transactional
qualification. All 4,800 ordinary worker, 1,600 diagnostic and 7,200 three-product
MCP measured responses passed. This M6/APFS candidate improves MCP steady-state
median/p90 across both synthetic graphs and cadences in this repeat. It does not
beat Glider on tiny queries or unpaced search; expiry, extra allocation and the
worker-only paced-search regression remain documented. Linux/Windows native
qualification and other filesystem qualification are not claimed. Local only.
See [complete evidence, failures, session tails and commands](fresh-metadata-batching.md).

## Expiry scheduling and Glider behavior (2026-10-21)

The bounded macOS internal-read candidate preserves the source/hash/validation
contract while avoiding a second thread-pool work item per read. Pinned runtime IL
and focused cancellation/error-order proofs passed, along with existing native
security/mutation and five failed-refresh guards per variant. Worker qualification
passed 2,400 ordinary and 800 diagnostic responses; the native shipped/candidate/
Glider comparison passed 7,200 steady-state checks in 36 fresh processes. Full-graph
post-idle median improved 180.55 to 158.33 ms versus shipped; Glider was 3.47 ms.
Worker p90/search regressions and all tails remain in the evidence. No universal win.

Twelve multi-case and twelve quiescent fresh-process behavior sessions passed.
Glider synchronized one file after a metadata-preserving edit from a zero-event
state, on both graph sizes; repeated/distinct queries remained similarly fast.
Both products briefly returned old dependency results before watcher invalidation.
The main measured gap is FreeFlight's mandatory whole-graph refresh work, not slow
outline semantics. Skipping unchanged non-target validation would change the
existing contract and was not implemented. All work remains local. See
[expiry qualification](expiry-read-scheduling.md) and
[comparative behavior, limitations and design boundary](glider-behavior.md).

## Incremental validation prototype (2026-10-21)

After explicit user approval of a separate affected-file mode, a local startup-only
prototype retains strict mode as default and adds bounded watcher-driven selection,
versioned acknowledgment, full-content recovery on a five-second deadline or watcher
uncertainty, and transactional aggregate resource accounting. Sixteen generated
fault/contract checks passed in final `incremental-v3`, along with 2,400 ordinary
and 800 diagnostic worker responses and 7,200 steady-state / 144 post-idle MCP
responses across 36 fresh processes. Outlines approach Glider, but definitions,
expiry spikes and a paced-search regression remain. No overall win, release or
configuration change.
See [the explicit freshness contract](incremental-validation.md).
