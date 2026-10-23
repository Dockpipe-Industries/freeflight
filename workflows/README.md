# Development workflows

DockPipe is the authoritative developer interface. Invoke dockpipe --workflow NAME.
Small tasks live at workflows/NAME/config.yml and compose through DockPipe commands.
core.build/core.test own C++; workers.typescript and workers.roslyn own internal
workers; integration.test validates the one endpoint; site.build stages the site;
repo.check validates guidance/layout; package.native qualifies complete artifacts;
registry.check validates registry metadata. build/test/check compose those tasks.

Generated output is bin/.local; engine state is bin/.dockpipe. Helper scripts are
workflow-local assets for validation, cross-platform staging or artifact inspection,
not alternate entry points. Do not introduce duplicate npm scripts or CI build logic.
See docs/agents/workflows/development.md and docs/README.md for requirements.

The website follows the Qt/WASM renderer architecture: `site.toolchain` provisions
pinned task-local SDKs, `site.build` compiles and stages environment-specific assets,
`site.test` runs real Chromium at desktop/mobile widths, and `site.container` builds
and smoke-tests a disposable unprivileged container.
`site.deploy.prepare` validates environment-specific delivery receipts and emits
isolated Compose wiring without accessing hosts or credentials. Production inputs
must have a stable version and matching qualified source, release-tag and master
trees. See `docs/site-deployment.md` for remaining activation gates.
`site.deploy.bundle`, `site.deploy.send` and the host-installed `site.deploy.receive`
implement published-byte verification and unprivileged static activation with
local health checks and rollback. `infra.up` uses the reviewed Cloud extension for
coordinated, plan-first setup and operator-private HTTPS readiness; it requires
explicit credentials and execution approval. `release.policy` tests rejection,
rollback and additive plans without hosts. `infra.alignment.test` tests the isolated
Cloud extension with fake providers.

To compare a locally built pinned baseline with the current source, set
`FREEFLIGHT_BENCHMARK_BASELINE` to its absolute checkout/archive directory and run
`dockpipe --workflow benchmark`. Both trees must first pass their native build and
worker workflows using the same provisioned toolchains. The comparison reuses the
MCP benchmark driver, runs fresh processes serially against identical generated
C#/TS/JS fixtures, alternates order for two compatible runs, and retains raw
semantic failures, timings and sampled process-tree RSS beneath
`bin/.local/benchmarks/comparison-*`. The archived baseline source receipt is read
from `bin/.local/baseline-provenance.json`; retain and verify it before comparison.
The compatible fixture contains 24 one-MiB generated files; additional cases
exercise a nine-MiB file and 72 one-MiB files. Each generated file has 100 real
declarations plus explicit comment padding. These controlled byte-budget workloads
are not representative real solutions. First diagnostics includes lazy engine
loading; subsequent query timings and changed-file diagnostics verify exact results.
Default `benchmark` behavior is unchanged when the variable is unset.

`benchmark.trusted` isolates trusted Roslyn refresh costs with pinned baseline and
candidate snapshots, native security/semantic qualification, alternating fresh
sessions and separate instrumentation/expiry receipts. See the
[usage guide](../docs/trusted-performance-workflow.md). It complements the full MCP
benchmark; it does not replace endpoint or packaged platform qualification.

`benchmark.trusted.mcp` reuses a completed trusted comparison through the existing
MCP client, recording endpoint timings separately against the same frozen workers.
It requires a local core build and does not modify active MCP configuration.

`benchmark.trusted.glider` compares the frozen published bundle with isolated official
Glider through MCP, using the existing trusted fixtures and semantic oracle. See
[methodology, results and repeat command](../docs/glider-head-to-head.md).

`benchmark.metadata` runs the macOS native metadata proof with generated test-only hooks.
Set a fresh `FREEFLIGHT_METADATA_LABEL` and put the repository-pinned .NET SDK on PATH.
The trusted benchmark automatically runs this proof for candidates containing the helper.
See [batching evidence and repeat commands](../docs/fresh-metadata-batching.md).

`benchmark.expiry` checks the pinned Darwin runtime IL and the exact bounded-read
helper's cancellation/error behavior. Set a fresh `FREEFLIGHT_EXPIRY_LABEL`; use
the repository-pinned SDK on PATH. The trusted workflow includes this proof for
Darwin candidates containing the inline-read helper.

`benchmark.trusted.behavior` clones a qualified comparison's fixture for edit,
watcher, repeated/distinct-query and payload diagnostics. It never edits the
immutable timing fixture. See [usage and proof limits](../docs/glider-behavior.md).
Run it separately from ordinary timing processes.

The local incremental-validation prototype reuses `benchmark.trusted` with
`FREEFLIGHT_TRUSTED_BENCH_INCREMENTAL=1`. It records candidate-only startup argv
and adds generated missed-event, overflow, concurrency, transaction and boundary
proofs. `benchmark.trusted.glider` forwards those frozen arguments from the
qualified candidate receipt. See [freshness semantics and repeat commands](../docs/incremental-validation.md);
strict mode remains the default and active MCP configuration is unchanged.

`benchmark.trusted.attribution` runs identical-binary and response-copy controls
through the existing MCP driver, with fixed/rotating operation order and separate
generated-source native diagnostics. It retains paired session ratios, live
recovery events and correlated core/worker/client costs. See
[usage and interpretation limits](../docs/native-mcp-attribution.md).

`benchmark.shutdown` forces the captured-cancellation/disposal race against pinned
before and current source, in ordinary and generated diagnostic builds, then checks
callback lifetime contracts. It is a correctness proof, not a timing run. See
[commands and retained failures](../docs/shutdown-lifetime.md).

`benchmark.trusted.position` reuses native qualification, matched lifetime-fix
timings and identical-binary fixed/balanced/spacing controls. It includes a
within-process cadence crossover. `benchmark.trusted.position.summary` validates
complete receipts and an explicitly identified replacement for an interrupted
condition; it cannot replace a completed condition. See
[commands, measured gaps and interpretation limits](../docs/query-position-controls.md).

`benchmark.recovery.proof` runs the source-pinned negative gates for speculative
recovery opens and ordered byte accounting. It contains potentially blocking
operations in disposable child processes; see `docs/recovery-parallel-proof.md`
for expected rejection results and limitations. It is not a latency benchmark.

`benchmark.recovery.handles` tests the macOS nonblocking/all-component no-follow
open and regular-handle admission proposal using disposable fixtures. It records
negative race controls and descriptor ownership; it is not a runtime performance
qualification. See `docs/recovery-handle-feasibility.md`.

`benchmark.recovery.serial` qualifies the source-extracted serial handle primitive,
including retained Git candidates when the active runtime has been restored.
`benchmark.trusted.qualification` includes this proof whenever the frozen source
contains the helper. `benchmark.recovery.compare` reuses the existing MCP oracle
for paired comparisons, identical-binary controls and separate per-source profiles;
`benchmark.recovery.summary` retains every sample and reports descriptive pooled
post-idle quantiles. See `docs/serial-recovery-handles.md` for exact replay commands,
rejected candidates, the restored runtime and remaining performance tradeoffs.

`benchmark.recovery.buffer` verifies pinned Roslyn SourceText ownership for a
retained reusable-buffer candidate after its worker screen. Set
`FREEFLIGHT_BUFFER_RECEIPT` to a fresh completed trusted benchmark label. It checks
shrinking/chunk-boundary/Unicode inputs through overwrite and disposal; it does
not measure performance. See `docs/recovery-buffer-screen.md`.

`benchmark.recovery.background.gaps` verifies actual semaphore-handoff EOF shutdown and ordinary five-second fallback while maintenance is suspended. `benchmark.recovery.background.idle` measures repeated isolated CPU/allocation/GC/RSS windows and requires successful completed sweeps with exact byte accounting. Set `FREEFLIGHT_BACKGROUND_RECEIPT` to a frozen candidate receipt; use fresh `FREEFLIGHT_BACKGROUND_GAP_LABEL` / `FREEFLIGHT_BACKGROUND_IDLE_LABEL` values for repeats. These generated probes do not enter production or latency builds.

`benchmark.trusted.glider` accepts optional `FREEFLIGHT_GLIDER_PRODUCT_ORDER=balanced` with explicit `FREEFLIGHT_GLIDER_PRODUCTS`; the session count must be a multiple of the product count. Every product occupies each process position once per cycle. Default reversed ordering is retained. See `docs/background-recovery.md` for the exact matched configuration, negative receipts and qualification limits.

`benchmark.trusted.focus` generates a diagnostic-only stage attribution worker from
`FREEFLIGHT_FOCUS_RECEIPT` (default `background-cooperative-v4`). A fresh
`FREEFLIGHT_FOCUS_LABEL` is required. It retains two processes with five-second
warmup and 25 balanced post-warmup rounds each; empty timer calibration and exact
results are included. This is separate from ordinary MCP/Glider timing. Trusted
screens accept `FREEFLIGHT_TRUSTED_BENCH_BASELINE_BACKGROUND=1` only with baseline
incremental mode. Idle diagnostics accept `FREEFLIGHT_BACKGROUND_IDLE_VARIANT`
(`baseline`, default `candidate`, or `both`) and session count (minimum two).
`both` builds both frozen diagnostic sources before measurement and reverses source
order in alternating pairs, with maintenance off/on for each. A pre-timing manifest
retains source/DLL identities and sequence; each window still requires matching
successful completion/publication and full-file byte counts. This synthetic matched
comparison does not isolate native allocation or qualify Glider idle costs.

`benchmark.recovery.allocations` samples managed allocation stacks only inside marked
successful synthetic full sweeps. Set a fresh `FREEFLIGHT_ALLOCATION_LABEL`; pinned
MIT collector packages use locked restore in diagnostic output. Raw EventPipe and
ETLX files remain local. `benchmark.definition.cost` uses a fresh
`FREEFLIGHT_DEFINITION_LABEL`, serial direct/MCP sessions, generated no-op controls,
and request-ID joins with per-position summaries. Both are diagnostic-only and use
the retained background-cooperative-v4 fixture/source receipt. See
[allocation and definition diagnostics](../docs/allocation-definition-costs.md).

`benchmark.recovery.paths` accepts `FREEFLIGHT_PATH_RECEIPT` for a frozen path-string
candidate. It compares canonical-key validation against the unchanged uncached checker
with observed fresh attribute-call order, then screens all twelve semantic APIs in
serial rotating-order baseline/candidate sessions. Rename remains preview-only and
all fixture hashes are rechecked. These descriptive direct-worker timings remain
separate from MCP/Glider and the four-operation workload.

`benchmark.recovery.attributes` uses `FREEFLIGHT_ATTRIBUTE_LABEL` for a fresh native
attribute proof against the current candidate. `benchmark.trusted.operations` accepts
`FREEFLIGHT_OPERATION_RECEIPT` and reuses the exact twelve-operation oracle driver.
Optional `FREEFLIGHT_OPERATION_LABEL`, `_SIZES`, `_ROUNDS`, `_SESSIONS`, and `_ORDER`
select a fresh sub-label and a fixed balanced measured phase (`balanced` requires
rounds divisible by12). Defaults retain the original ten rotating rounds/two sessions
and both graphs. Balanced mode verifies every operation's position counts; all modes
reject duplicate session identities. Optional `FREEFLIGHT_OPERATION_IDENTICAL=baseline`
(or `candidate`) maps both labels to that frozen binary for a noise control; it
requires matching flags, verifies the DLL hashes and identical commands, and saves
its manifest/adapter before timing. Omit it for ordinary A/B comparisons.
See docs/native-attribute-screen.md for the
preserved bookkeeping correction, limitations and full replay configuration.

`benchmark.definition.cost` accepts `FREEFLIGHT_DEFINITION_EXTENDED=1` for balanced
four-operation diagnostics (definition/references/search/generated no-op), two
sessions per transport/cadence, fine validation/read/semantic scopes and exact read
counters. Optional `FREEFLIGHT_DEFINITION_REPLAY_SEARCH=1` requires extended mode;
it substitutes a generated fixed-search-payload control and uses paced sessions
only. These controls are never production operations. Default paired definition/
no-op behavior is retained. `benchmark.definition.cost.audit` uses a completed
`FREEFLIGHT_DEFINITION_LABEL` to validate IDs, balanced positions/predecessors,
source/adapter identities, fresh reads and replay equivalence without new timing.
Derived summaries refuse replacement when contents differ. See
[reference and boundary isolation](../docs/reference-boundary-costs.md).

`benchmark.response.copies.prepare` freezes94eb 420 and worktree C++ cores under a
fresh `FREEFLIGHT_RESPONSE_LABEL`, builds with identical options and checks existing
native gates plus the current dual-content protocol suite. It reuses one frozen
exact 94 worker for both. `benchmark.response.copies` defaults to a balanced all-twelve
MCP screen; `FREEFLIGHT_RESPONSE_MODE=four` selects a separate paced navigation
workload. `_SESSIONS`, `_ROUNDS`, `_SIZES` and `_SCREEN` select counts/fresh output.
`benchmark.response.copies.profile` uses generated cores and retained search replay
only for CPU attribution. `benchmark.response.copies.audit` issues no new queries;
it verifies complete receipts and refuses replacement of differing derived data.
See [JSON ownership evidence and limits](../docs/json-response-copies.md). The tested
move-only candidate is unaccepted; production source has been restored 94eb 420.

`benchmark.response.copies.context` uses a fresh `FREEFLIGHT_CONTEXT_LABEL` for an
interleaved identical-core/source comparison and within-process round/equal-gap
crossover. It reuses qualified generated binaries, records actual gaps/verification
and joins client/core/worker stages. Fixed acclimation and measured windows remain.
`benchmark.response.copies.context.cpu` adds a locally ABI-verified/calibrated generated
worker process-CPU clock and reruns worker gates before a narrower source-only control.
`benchmark.response.copies.context.audit` validates the original context receipt with
no new queries. `benchmark.response.copies.context.cpu.audit` validates the CPU receipt without new
queries; its audit source is retained separately. All are diagnostic-only;
production stays exact94. See [pacing-context evidence](../docs/copy-pacing-context.md).

`benchmark.response.copies.ordinary` uses a fresh `FREEFLIGHT_ORDINARY_LABEL` for 16 serial
ordinary frozen-core processes: four source pairs and four identical-binary sham pairs.
It records actual gaps and verification time, preserves all warmups and positions, and
audits every session/pair. `benchmark.response.copies.ordinary.audit` replays the receipt
without new queries. See [ordinary matched evidence](../docs/ordinary-matched-gaps.md).

`benchmark.reference.context` requires a fresh `FREEFLIGHT_REFERENCE_CONTEXT_LABEL`
and runs four serial ordinary baseline94 processes. Full 24-permutation blocks and
predefined adjacent policy pairs retain all positions, predecessors, actual gaps
and round periods. `benchmark.reference.context.audit` replays receipts without
new queries. See [baseline reference context](../docs/reference-position-context.md)
for the design review, pacing/rate limits, evidence and replay.

`benchmark.reference.wait` uses a fresh `FREEFLIGHT_REFERENCE_WAIT_LABEL` for the
Astra-reviewed fixed 250 ms cycle baseline control, relocating 25 ms waiting across
references while keeping the other operation targets fixed. All deadline misses
and actual start offsets remain; `benchmark.reference.wait.audit` issues no new
queries. See [reference-context evidence](../docs/reference-position-context.md).

`benchmark.reference.attribution` uses a fresh `FREEFLIGHT_REFERENCE_ATTRIBUTION_LABEL`
for four serial ordinary/probe baseline processes under the fixed250ms schedule.
It reuses qualified generated observers, records exact client/core/worker IDs,
fresh-read counters and disjoint reference mean wall partitions, and gates
localization on fresh ordinary/probe directional reproduction.
`benchmark.reference.attribution.audit` replays receipts without new queries.
See [attribution scopes and evidence](../docs/reference-fixed-attribution.md).

`benchmark.reference.work.prepare` performs a tiny own-process public-counter
capability calibration. `benchmark.reference.work.build` checks exact managed short
intervals before its generated probe build gate; `benchmark.reference.work.native.prepare`
independently checks a native small complement. Both later qualifications failed on
this host before any FreeFlight probe build/timing; do not rerun unchanged or label
the unexecuted build paths as passing. Fixed output directories refuse overwrite.
`benchmark.reference.work.audit` recomputes retained failures without native execution
or new queries. See [counter qualification and limits](../docs/reference-work-qualification.md).


`benchmark.reference.aggregate.prepare` performs the separately scoped finite external
whole-block calibration before target collection. Final v3 fails instruction scaling;
its fixed output directory prevents unchanged reruns. Two diagnosed setup failures
and every final observation remain. `benchmark.reference.aggregate.audit` recomputes
all final structural/CPU checks and failed scaling gates without native execution or
queries. See [whole-block qualification](../docs/reference-work-qualification.md#separate-whole-block-external-counter-qualification--2026-10-23).


`benchmark.reference.reader.prepare` freezes exact94 and a generated-only bounded
worker-response reader candidate, adds identical framing regression tests and runs
native/current protocol gates. The existing response screen supports its manifest.
`benchmark.reference.reader.audit` independently recomputes all-operation source,
fixture/balance/metric and rejection receipts without new queries. Fresh preparation
labels refuse overwrite; the original candidate failed its narrow screen and must
not be rerun unchanged seeking acceptance. See [structural reader review](../docs/reference-structural-review.md).


`benchmark.evidence` captures completed JSON/JSONL receipts into deduplicated,
lossless objects with1MiB/blob and10MiB/checkpoint Git budgets. Larger observations
are cataloged external; build/source/fixture/cache trees and bulk diagnostics stay
ignored. `benchmark.evidence.check` checks Git object integrity and candidate source
reconstruction without old build outputs. No uploads or deletion occur. See
[small benchmark asset policy](../benchmarks/README.md) and its fresh-label usage.
