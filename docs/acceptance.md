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

## Search and response regression investigation (2026-10-21)

No new runtime winner was accepted. Guarded compilation search and owned MCP
responses passed semantic/security gates, but the combined and response-only
M6 matrices retained unfavorable latency cells. Each matrix used 32 fresh
processes and passed 6,400 steady-state / 128 post-idle semantic checks against
shipped 97c1342, d8232ec and pinned Glider 13.3.0. The combined candidate improved
full-graph search but regressed paced outline/definition tails. The response-only
control improved search by 11% unpaced / 3% paced but retained a 10% paced
definition-p90 regression and an 18% unpaced reference-p90 regression. Recovery
remained about 158 ms versus Glider's roughly 5 ms. These are bounded synthetic
observations, not Linux/Biztraak results or a universal comparison.

Candidates are preserved locally at 5d14a4a and 5c44c97. Runtime is restored to
d8232ec; profiling, differential tests and deterministic comparison/replay
workflows remain. See [complete tables, source costs, failures and repeat commands](compilation-search.md).

Closing qualification passed in `bin/.local/benchmarks/trusted/restored-runtime-final`: worker/security/mutation gates, all 16 incremental fault checks, metadata/read proofs and five failed-refresh state-preservation cases per variant. Baseline/candidate worker source hashes are identical to d8232ec. `bin/.local/glider-comparison/response-ref-replay-qualification` passed native worker/core gates with zero timed processes; its pinned core source hashes exactly match the measured response-only control.

## Native attribution controls (2026-10-21)

No runtime winner accepted; production source remains d8232ec. Four ordinary
conditions (identical-binary A/A and response-only A/B, fixed/rotating order) passed
32 fresh processes and 10,368 measured semantic checks. Search gains remain modest
and rotating outline medians worsen in every candidate pair. Eight separate
diagnostic processes passed 2,592 measured semantic checks with 5,524 joined
records including warm-up. Stage data distinguishes worker execution, core JSON
parsing, construction, delivery, client parsing and profiler overhead.

Final log audit found EOF `ObjectDisposedException` in both diagnostic worker
qualification runs, hidden by a test script that did not check worker exit status.
Those gates are not accepted as clean. The workflow now rejects the retained crash
logs; four ordinary conditions pass this audit, both diagnostic conditions fail.
All evidence and the overriding `qualification-review.json` remain local. No
production fix, parallel recovery or publication was attempted. See
[attribution, mixed timings, failure and next proof obligations](native-mcp-attribution.md).

## Cancellation lifetime correction (2026-10-21)

The shutdown/cancel race is confirmed in ordinary production source as well as
diagnostic builds. A lifetime lease prevents source disposal during cancellation
without holding a lock across callbacks. All six forced before cases reproduce
the defect; all six fixed cases pass, plus five callback/disposal contracts.
Both worker harnesses now check EOF exit status. The broad worker qualification,
16 incremental faults and transactional failure cases pass; earlier diagnostic
failures remain recorded. Native/ordinary timing follow separately. See
[source reasoning, receipts and repeat commands](shutdown-lifetime.md).

Native diagnostic qualification of `6a06b1d` now passes the exit-status and crash-log
gates, plus core protocol/process tests. Ordinary matched/control qualification
passes 32 complete processes and 10,368 measured semantic checks. One additional
completed process from an interrupted condition remains separately preserved.
The incomplete condition was rejected, repeated under a new label after confirming
no live processes, and validated against matching provenance. A within-process
cadence crossover shows substantial context effects but does not identify a
hardware/runtime mechanism. Latency cells remain mixed; the lifetime repair is a
correctness acceptance, not a Glider win or a general performance claim. See
[full timing tables, interruption audit and repeat commands](query-position-controls.md).

2026-10-21 recovery feasibility gate: serial versus width-two/four source-extracted
workspace opens reproduced a non-draining FIFO case after an earlier resource
error; six byte-completion schedules also retain the ordered-accounting
counterexample. Speculative opens are rejected before runtime integration or timing
qualification. Runtime remains `6a06b1d`; no recovery speedup is claimed. See
[proof, receipts and remaining design constraints](recovery-parallel-proof.md).

2026-10-21 handle feasibility: the corrected macOS nonblocking/all-component
no-follow open plus regular-handle validation passes the local FIFO/race/cancellation
probe. The invalid flag combination and incorrect event-only assumption remain in
receipts. This is not a qualified parallel runtime: in-flight syscall termination
and device-open effects remain limitations. See [native proof and design decision](recovery-handle-feasibility.md).

2026-10-22 serial recovery qualification: retained experiments `b04d21f` and
`c3ae753` reduce full recovery work, but neither is selected as a broad performance
winner. The refined candidate passes worker/security/incremental/transaction and
strengthened root-replacement gates; the earlier fallback fails that added gate.
Across both comparisons, 54 fresh processes passed 8,856 measured semantic checks.
Full recovery improves while ordinary reference p90 remains unfavorable. Active
worker sources are restored exactly to `6a06b1d`; all samples and failed attempts
remain. See [source attribution, timings and replay](serial-recovery-handles.md).

2026-10-22 resumed buffer qualification: no new runtime winner. Both hash and
request-local buffer candidates passed fault/transaction gates but had unfavorable
ordinary latency; all 24 fresh-process screen results remain. Buffer ownership
passed against pinned Roslyn. Runtime restored to `6a06b1d`; no new MCP/Glider
or cross-platform claim. See [screens and design constraint](recovery-buffer-screen.md).

### 2026-10-22 — cooperative recovery resumed qualification

Preserved the rejected semantic-model reuse source/patch/raw receipts, restored
worker source exactly to performance candidate 94eb420, and retained the linked
investigate/rc2-warm-refresh branch. The instruction-only hook was verified on a
real Sol/medium bounded read-only review. Main js/dev and unrelated edits remain.

Actual semaphore-handoff EOF shutdown and ordinary five-second foreground
fallback during suspended maintenance pass. Idle accounting now proves successful
full sweeps and exact bytes, not merely attempts. Twelve repeated idle windows pass;
nine sweeps average 203.437 ms process CPU and 57.642 MB allocations each.

Matched MCP comparison completed 36 fresh processes and 5,904 measured semantic
checks across two graph sizes/cadences and three balanced product positions.
All raw sessions and maxima remain. This is local qualification, not an overall
performance win: definition latency and idle costs remain acceptance concerns.
The initial missing-PyYAML preflight and symlink-alias idle rejection are retained.
See docs/background-recovery.md for complete tables, receipts and limitations.
No new runtime optimization, publication, merge, deployment or platform claim.

### 2026-10-22 — definition/search and idle allocation screens

Two new serial matched direct-worker screens against 94eb420 pass functional gates
but are rejected on latency: background-only buffer reuse cuts idle allocations from
57.642 to 33.194 MB/sweep descriptively, with reference p90 +22.6%; bounded two-project
Roslyn search improves full-graph search p90 17.0%, with definition p90 +13.5%.
All source, patches, raw sessions and rejection decisions are retained. Runtime
worker files are restored exactly to 94eb420; main js/dev is untouched.

The corrected five-second warmup attribution probe passes 200 checked post-warmup
responses. Earlier timer/window mistakes have retained validity notes. Search passes
104 oracle comparisons plus two-task cancellation/drain/error-order probes. Buffer
ownership (nine cases), actual handoff/fallback and eight idle windows pass; six sweeps
verify exact byte accounting, averaging 199.817 ms CPU and 33.194 MB allocations.
Existing worker/security/mutation/incremental/background/transaction gates pass in
both screens. No new overall win or competitor matrix is claimed. Allocation-stack,
transport/wakeup, Glider idle costs and real/cross-platform qualification remain open.
See docs/background-recovery.md for tables, receipts and replay. No publication.

### 2026-10-22 — allocation stacks and definition boundary diagnostics

Two isolated EventPipe traces verify six successful full sweeps (5,845 files and
23,941,120 bytes each), zero lost events, and 3,227 managed-stack samples. Sampled
byte attribution is 50.68% compiler path/attribute validation and 37.63% MemoryStream
growth; measured allocation averages 57.606 MB/sweep. Exact per-type counts are not
claimed. Raw traces, collector package lock/notices, generated source and hashes remain.

Twelve matched direct/MCP diagnostic processes pass 960 ID-joined responses, including
480 exact definitions. Burst direct/MCP medians are 0.062/0.140 ms; paced medians
1.197/1.791 ms. Worker invocation and outer boundary both increase with pacing;
gate median remains <=0.0005 ms. Position-stratified results and all sessions remain.
Native protocol/process and generated worker/trusted suites pass. Two diagnostic
setup/logging failures are preserved and excluded. Production C++/Roslyn files remain
exactly 94eb420, with no application dependency/trust/default changes or publication.
See docs/allocation-definition-costs.md for limits, receipts, replay and next steps.

### 2026-10-22 — lexical path-string reuse screen

A graph-bound lexical-only parent-string candidate preserves fresh component/leaf
attribute checks and recovery. Twelve focused fresh-check/order equivalence cases,
existing semantic/security/incremental/rollback gates, actual handoff/fallback and
all twelve operation oracles pass. All-operation timing includes 960 exact measured
responses; four-operation timing adds 640 ordinary and 320 diagnostic responses.

Idle accounting proves six successful full sweeps across eight windows: 41.480 MB
allocation and 197.230 ms CPU per sweep. Allocation is descriptively 28.0% below the
prior 94eb420 run, but latency is mixed/unfavorable (full all-operation definition
p90 +8.7%, signature help +14.9%). Candidate is rejected, archived with source/patch/
raw receipts, and production source restored exactly to 94eb420. No larger competitor
matrix or overall-win claim. See docs/path-string-screen.md. No publication.

### 2026-10-22 — fresh native attribute candidate remains unaccepted

A macOS getattrlist reparse-flag reader retains fresh component validation and original
fallback. Thirty equivalence/fault/fallback cases pass; 2,000 warmed reads allocate
zero measured managed bytes versus 480,000 for the original reader. One race-probe
assertion error is preserved and corrected without changing production candidate code.
Worker/security/trusted/incremental/background/rollback gates and actual handoff/fallback
pass. Six verified idle sweeps average 46.888 MB allocations and184.375 ms CPU; this
is a separate-run descriptive improvement, not matched statistical idle qualification.

Four-operation and all-twelve-operation screens retain all adverse tails. A fixed-phase,
position/predecessor-balanced confirmation adds4,608 exact responses across8 actual
processes; symbols/references p90 remain about6% unfavorable. A duplicate-output-row
bookkeeping bug is preserved, independently validated/corrected in separate derived
files, and fixed for future runs; no timed requests or outliers were dropped.
Production is restored exactly to94eb420. Candidate source/patch/raw receipts remain
under perf-preservation and native-attributes-screen-v1. No overall-win claim or
larger competitor matrix. See docs/native-attribute-screen.md. No publication.

### 2026-10-22 — native attribute noise control and matched follow-up

Eight identical-binary balanced processes pass4,608 exact all-operation responses;
independent audit confirms identical commands, unique slots and balanced positions/
predecessors. Tail variation differs by operation and does not erase adverse cells.
Nine matched real MCP processes compare94eb420/native/Glider13.3.0 on the paced
5,845-file graph, passing1,440 steady and3,220 total responses. Native references
median is9.7% slower than94; search p90 is2.5% slower. Definition/search medians remain
64.4%/5.4% slower than Glider. Every sample, adapter and position stratum is retained.

Matched idle sources alternate order across eight serial processes and sixteen windows.
Each source verifies six successful full sweeps with exact byte/publication accounting
and no failures/aborts. Native managed allocation falls57.643→46.889 MB/sweep and CPU
206.820→189.148 ms/sweep; GC pause increases2.975→3.508 ms/sweep. Short synthetic
macOS evidence does not qualify native allocation, Glider idle or real/cross-platform
behavior. Native candidate remains unaccepted; production runtime is byte-identical
to94eb420 on investigate/rc2-warm-refresh. No commit or publication. See
docs/native-attribute-screen.md for all receipts, limitations and replay. Next isolate
reference median and definition/search boundary costs before another allocation design.

### 2026-10-22 — reference and response-boundary isolation

Extended generated diagnostics pass 1,280 joined responses across eight serial
processes; a same-search-payload control adds 640 across four processes. Protocol/
process tests 2/2 and generated semantic/security/trusted suites pass in each probe.
Independent audits verify exact IDs, balanced positions/predecessors, semantic and
replay identities. All 960 measured definition/reference requests read exactly one
fresh 4,096-byte target; production validation/recovery is unchanged.

Paced MCP medians: definition 0.470 ms (refresh 0.117, outside invocation 0.277);
references 1.437 ms (FindReferences 0.823); search 23.143 ms (declarations 9.038,
outside invocation 12.562). Same-payload replay still costs 9.629 ms end-to-end,
including 7.788 ms core thread CPU, while worker invocation is 0.0009 ms. Core JSON
parsing/envelope/serialization work is material. Nested scopes are not additive.
These are instrumented synthetic diagnostics, not ordinary/Glider performance wins.
Prior native reference session ratios 0.945/1.133/0.945 also show aggregate instability;
all adverse results remain and the native source stays unaccepted.

Runtime remains byte-identical to 94eb 420 in the preserved worktree; no publication.
Receipts, source, raw sessions, per-position/per-session metrics and replay are in
docs/reference-boundary-costs.md. Next screen a narrowly scoped JSON ownership/copy
change while retaining dual content and all parser/security/cancellation contracts.

### 2026-10-22 — JSON ownership screen remains unaccepted

A move-only C++ response candidate preserves text/structured content, parser depth/
size/ID checks, cancellation locking, errors and unchanged exact 94 workers/recovery.
Both frozen cores pass native protocol/process gates and 24 current protocol tests,
including 24 modern/legacy payload subcases. One legacy-handshake test-setup rejection
against unchanged 94 is retained separately; corrected tests pass before all timing.

All-twelve MCP screening passes 4,608 measured checks across both graphs. Full search
median/p 90 improve 12.9%/10.7%, while full reference p 90 worsens 16.1% and small type-
hierarchy p 90 worsens 22.0%. A separate repeated paced full-graph screen passes 1,536
checks but definition/reference medians worsen 20.7%/28.9%, with search effectively
unchanged. A generated same-payload control passes 192 checks and records 17.5% lower
core thread CPU. This diagnostic benefit does not establish an ordinary overall win.
All sessions/adverse cells/position strata remain; no larger Glider matrix is run.

Candidate source/patch/decision is archived before restoring only its two runtime
files to 94eb 420. The dual-content protocol test and reproducible workflows remain.
No publication; main js/dev and unrelated changes are untouched. See
[JSON response copies](json-response-copies.md) for raw receipts, qualification limits,
replay and the predefined-control next step. Native allocation, Glider idle and
real/cross-platform qualification remain open.

### 2026-10-22 — lower core CPU versus paced latency controls

Eight interleaved source/A/A processes pass 1,024 measured +1,024 acclimation exact
responses with predefined within-process round/equal-gap blocks, measured actual gaps,
verification costs and correlated client/core/worker IDs. All 1,364 warmup and 32
initial oracles remain. All 768 targeted measured queries read one fresh 4,096-byte
file; no foreground full recovery occurs. Same-binary label variation remains.
Round search mean decomposition: outside invocation -1.536 ms, worker invocation
+2.056 ms, total +0.521 ms. Equalizing gaps does not universally rescue worker cost.

A narrower four-process generated worker-CPU follow-up passes 512 measured +512
acclimation, 680 warmup and 16 initial oracles, plus native-clock ABI/calibration and
worker semantic/security/trusted gates. Equal-gap search worker wall/CPU ratios are
1.393/1.413 while core CPU is 0.813; round search instead has essentially unchanged
worker costs and client ratio 0.952. Worker process CPU includes parallel runtime/GC
work and is not an off-CPU measure. Frequency/cache/scheduler causes are unmeasured.
No adverse cells, acclimation records or outliers are removed; mean and nonlinear
session-median estimates both remain. No accepted runtime or causal hardware claim.

All production runtime remains exact `94eb420`; copy candidate stays archived/unaccepted.
No publication, main checkout change or extra agents. See
[copy pacing context](copy-pacing-context.md) for all receipts, counts, plans, limits,
independent audits and replay. Next ordinary comparisons need actual-gap controls and
stable session/position evidence before another response design or acceptance.

### 2026-10-23 — ordinary matched gaps and session/position evidence

Sixteen predefined serial ordinary processes pass 3,072 measured +3,084 warmup +64
initial oracle =6,220 exact semantic/dual-content responses. Four source pairs and
four identical-binary sham pairs use the same frozen worker/configuration and balanced
positions/predecessors. Actual gaps, verification and round sleeps remain; no timing
filters, replacements, instrumentation or performance-driven exclusions are applied.

Source session median/p90 ratios: symbols 1.093/1.030, definition 1.117/1.043,
references 1.263/0.963, search 1.015/0.996. Symbols/references are slower in all four
chronological pairs; search directions vary. References improve at position zero but
worsen at positions two/three in every pair. Same-binary variation and all adverse
cells remain. Medians across position mixtures are nonlinear; aggregate p90 gains
do not establish a reproducible overall win. No cause is attributed to CPU/frequency.

Production stays exact `94eb420`; archived copy candidate remains unaccepted. No new
Glider matrix, source change or publication. See [ordinary matched evidence](ordinary-matched-gaps.md)
for raw receipts, every pair/position, actual gaps, replay and limits. Next isolate
baseline reference position/predecessor sensitivity with a narrow predefined control
before another response design; Glider idle/native allocation/real-platform gaps remain.

### 2026-10-23 — baseline reference history and fixed-cadence wait placement

A Sol/high design review precedes four serial ordinary baseline94 processes with
full 24-order blocks and adjacent matched pacing pairs. All 3,072 measured +512
acclimation +752 warmup +16 oracle responses pass. Position/predecessor associations
repeat but interact: after-search references are faster at position 1 under round
pacing, while slower at position 3. Gap-floor pacing changes achieved rate, so this
descriptive result cannot isolate idle time or a runtime/hardware cause.

Astra/high reviews the causal limits and proposes one executed fixed-cycle control.
Four new serial baseline processes hold 250 ms cycle targets, symbols/definition/search
slots, query order and predecessor fixed while relocating 25 ms waiting across refs.
All 2,048 measured +512 acclimation +384 warmup +16 oracle responses pass. References
median rises 2.523→3.930ms (ratio 1.558), worse in all 4 sessions/all 16 nested block pairs;
p90 ratio 1.502. Actual cycle medians stay 250 ms, with 0 fixed-slot readiness overruns.
Actual timer wake lateness is retained; no claim of perfectly equal realized starts.
Request rate alone is insufficient in this fixed context, without locating the
mechanism or transferring prior instrumented worker-CPU localization.

Combined 7,312 exact semantic/dual-content responses; all raw phases, gaps, periods,
paired blocks and adverse cells remain. No runtime change:28 production files exact94,
validation/security/recovery preserved; copy candidate still archived/unaccepted.
No publication or new Glider matrix. See [reference context](reference-position-context.md).
Next localize the fixed-schedule extra reference cost with a separate narrow stage/CPU
probe before any source remedy; Glider idle/native allocation/real-platform gaps remain.

### 2026-10-23 — fixed-schedule reference stage and boundary attribution

Four serial baseline processes (ordinary/probe/probe/ordinary), balanced incoming
wait orders and unchanged 250 ms cycles, pass 2,048 measured +512 acclimation +384 warmup
+16 initial oracle =2,960 exact semantic/dual-content responses. Sol/high scope review
finishes before timing. Existing generated observers/qualifications are reused by
hash; no new runtime build. Fresh ordinary/probe reference mean/median penalties
are positive in all 4 processes/all 16 nested pairs; median ratios 1.581/1.524. No fixed-slot
readiness overruns; wake lateness and all actual periods remain.

Probe wait-minus-immediate mean partitions: refresh/admission +0.2004/+0.2014ms,
measured semantic stages +0.4833/+0.5758ms, invocation residual +0.0554/+0.0661ms,
boundary +0.4977/+0.6185ms, totaling +1.2367/+1.4618ms. FindReferences adds
+0.4083/+0.4989ms; process invocation CPU increases but is parallel/background/GC
inclusive, not foreground/instructions/offCPU. Separate receipt-only boundary
algebra identifies increments around worker envelope, core routing and outer MCP/
client; none is pure transport. No nested timer double counting or median subtraction.

All 1,104 recorded targeted probe queries read 1×4,096 bytes; 368 searches read 0. No
foreground full recoveries; background sweep accounting is not inferred. All
phases/IDjoins/adversecells/meanidentities remain. Validation/security/recovery and
28 production files stay exact94; archived copy candidate remains unaccepted. See
[fixed-schedule attribution](reference-fixed-attribution.md) for receipts/replay/limits.
Next distinguish work growth from execution/runtime-state effects in FindReferences
and core routing before any remedy. No publication or Glider matrix.

### 2026-10-23 — short work-counter qualification fails before FreeFlight timing

Astra/high reviews a bounded process-instruction probe before collection. Public
proc_pid_rusage own-process access works; initial native loop doubling passes
(1.984/2.000/1.996), without profiling/settings/trust changes. xctrace is unavailable
in the installed developer tools. Stronger exact-helper managed direct/async/joined
calibration fails declared scaling bands; no FreeFlight probe is built or timed.
All 90 work +500 empty +20 nested +1 ABI observations remain, including joined ratios
4.441/1.438/3.023. This is not proof of broken counters or target instruction growth.

A separately reviewed native-only small-complement calibration retains 224 nested
and 2,000 empty observations. Scaling passes, but one routing-sized repeat range is
6.6099%, above the declared 5% limit; resolution floor 39,524 instructions. It also stops
before generated FreeFlight source/build/timing. No thresholds relaxed, samples
removed, repeated failed calibration or benchmark matrix follows. A no-query audit
recomputes both failure decisions; audit success does not convert qualification
failures into passes. Draft post-gate build paths remain unexecuted/unqualified.

Work-versus-runtime distinction remains unresolved for FindReferences/core routing;
prior wall/CPU attribution remains within its existing limits. All 28 production files
remain exact94 with fresh validation/security/recovery intact; prior local work and
receipts remain, main unchanged, copy candidate unaccepted. See
[qualification failures and receipts](reference-work-qualification.md). Next validate
a suitable short-concurrent-work measurement path or separately define a defensible
lower-precision question before another run. No publication/commit/Glider matrix.


### 2026-10-23 — whole-block external work counters also fail qualification

A separate bounded Astra/high review defines whole-process four-second work totals,
without stage attribution. Two diagnosed setup errors (clock origins, then unequal
CPU windows) remain in aggregate-work-calibration-v1/v2. Corrected v3 uses one clock
domain, separate bracketed cumulative CPU checks and fixed complete-path warmup.
Two fresh managed children retain all32windows/512measuredcycles and deterministic
joined-task checksums. Structural and CPU-unit checks pass; all12paired composite
instruction gates fail: doubling ratios1.115–2.131, predicted80M±5% increments instead
19.44M–104.23M. No outliers removed or scaling gates relaxed; no unchanged retry.
Empirical uncertainty195.82M includes whole-process scaffolding/runtime work and is
not a hardware-resolution claim. Receipt-only audit reproduces the failure.

Zero new FreeFlight queries/probe builds; no target matrix or optimization accepted.
All28 production files remain exact94 on investigate/rc2-warm-refresh at94eb420;
main js/dev unchanged and earlier local work/receipts preserved. Prior correctness
results are preserved, not freshly rerun. FindReferences/core-routing work-versus-
runtime attribution stays unresolved. Next use bounded structural review and the
existing all-operation wall/CPU screens before another remedy. See
[qualification evidence](reference-work-qualification.md#separate-whole-block-external-counter-qualification--2026-10-23).
No commit, push, merge, publication, deployment or Glider matrix.


### 2026-10-23 — structural worker-frame reader candidate screened and unaccepted

Review finds repeated worker-response prefix scans and a full-frame substr copy.
A generated-only incremental newline scan plus iterator-range JSON parse changes
only Process::request; no worker/model/cache/validation/recovery/default change.
Both frozen cores pass native protocol/process2/2 and current protocol24tests,
including new coalesced-tail, fragmented Unicode and exact/over8MiB response tests.
Unchanged exact94 worker qualifications are reused by identity, not freshly rerun.

Matched ABBA screens cover all12operations on433/5845files:8serial processes and
2304exact measured responses, both content forms, balanced positions/predecessors.
Frozen any-cell ratio>1.10 stop gate triggers: full-graph references p90+56.3%, small
callHierarchy p90+15.0%; full-graph search median improves1.9%. One candidate session
concentrates the reference tail; both remain, with no causal/noise excuse. Receipt-only
audit recomputes all ratios and rejection. No unchanged retry or larger matrix follows.
Candidate source/binaries/diff/logs/receipts remain archived under response-copies/
worker-frame-view-v1. All28 production files stay exact94 in the preserved worktree;
main and earlier work remain. See [structural review and every operation result](reference-structural-review.md).
Next review immutable worker request ownership/dispatch without weakening independent
cancellation, gate handoff or shutdown. Glider/idle/real-repository gaps remain.
No commit, push, merge, publication or deployment.

2026-10-23: [Performance checkpoint and remote-execution handoff](performance-handoff.md) records the requested js/dev consolidation, ignored receipt transfer requirements, unaccepted experiments and next A/A controls. Existing qualification limits remain.
