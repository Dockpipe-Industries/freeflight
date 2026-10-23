# Structural reference and core-boundary review

Local macOS arm64, 2026-10-23. Work remains in `/Users/jamie/Source/freeflight-perf`,
branch `investigate/rc2-warm-refresh`, HEAD
`94eb4207c8ffd2d5544bca8a52dcb8d451285015`. Production src/include/Roslyn files stay
byte-identical to that commit. Existing local work and receipts remain. No commit,
push, publication, merge or deployment. This bounded source review and generated
candidate required no additional agents; benchmarks ran serially.

## Findings and scope choice

The source review covers `SourceEngine.Invoke`, reference result rendering,
`Program.Main` request lifetime/dispatch, `Server::call` and `Process::request`:

- References use the unchanged document-based Roslyn FindSymbolAtPositionAsync and
  FindReferencesAsync paths after fresh Refresh. Eager text/syntax/model acquisition
  is visible, but source-level duplication does not establish expensive repeated
  semantic execution. Earlier model-reuse failure remains unaccepted and was not
  retried. Removing fresh CheckPath/Refresh checks was not justified by repetition.
- Reference rendering creates JSON serialization sort keys through LINQ OrderBy.
  Those keys are materialized for ordering; the source does not justify claiming
  serialization on every comparison. Replacing it with numeric/path ordering could
  change the observable order, particularly numeric lexicography/escaping. No such
  semantic change was made.
- The core copies its capabilities operations array per query. This is a separate
  small ownership opportunity; it is recorded, not bundled into the tested candidate.
  Prior response-ownership experiments and their adverse cells remain untouched.
- The worker reader repeatedly searches growing buffered prefixes for a newline:
  after append, then again at loop entry. It then allocates/copies the complete frame
  through `substr` before JSON parsing. This is concrete avoidable scanning/copying
  without changing semantics, validation or recovery. It was the only tested change.
- Worker request handling clones the parsed root and then clones id/params subtrees
  before Task.Run. This is a separate ownership/lifetime question requiring review
  of independent cancellation, bounded queues and shutdown; no worker change was made.

For a response arriving in k similar chunks of total N bytes, the old delimiter
search revisits growing prefixes; its cumulative scan is quadratic in chunk count.
The generated candidate searches the initial buffered tail once, then only appended
bytes. JSON parsing receives a bounded iterator range into the existing buffer;
erasure occurs after parsing. This removes one frame-sized temporary string. These
are structural work/allocation reductions, not measured instruction counts, allocator
traces, stage CPU savings or established end-to-end latency improvements.

The candidate retains both MCP content forms, the same JSON parser and nesting-128
callback, 8MiB request/response caps, correlation IDs, worker-stop-on-error behavior,
partial reads, cancellation polling and deadlines. Root authorization/worker dispatch,
Roslyn semantics, all fresh input validation, strict defaults and cooperative recovery
are untouched. No security setting or trust change occurred.

## Frozen candidate and correctness qualification

`bin/.local/benchmarks/response-copies/worker-frame-view-v1` retains both generated
source trees/binaries, manifest/source/binary hashes, candidate diff, toolchain/build
logs, protocol and process results, all screen data and derived receipt audit. The
baseline is exact94; candidate runtime changes only generated `src/process.cpp`.
Both receive identical generated additions to `tests/process.cpp`:

- Successive coalesced frames preserve the buffered second response.
- Repeated large fragmented responses retain exact Unicode content.
- An exact8MiB JSON response succeeds; one byte over with newline rejects and stops
  the worker. Existing no-newline oversize, malformed/deep JSON, ID mismatch,
  cancellation while read/write blocked, crash/no retry and cleanup cases also run.

Each core passes native protocol/process targets **2/2**, plus the current **24-test**
dual-content/protocol suite. The Roslyn worker is the same previously qualified exact94
binary for both cores with `--incremental-validation --background-recovery`; its
semantic/security/recovery qualification is reused by verified source/binary identity,
not claimed as a newly executed worker recovery run. The earlier gate-handoff shutdown,
suspended-maintenance fallback and successful-sweep receipts remain unchanged.

## All-operation narrow screen and rejection

A plan frozen before timing declares both433/5,845-file fixtures, all12operations,
24balanced rounds after5seconds warmup, minimum100ms round period, two sessions per
variant and ABBA process order per size. All **8 serial processes / 2,304 measured
responses** pass exact baseline-oracle comparisons and both content forms. All
fixture hashes, position/predecessor balance and raw sample IDs pass the independent
receipt-only audit. Initial oracle checks and warmup calls are checked but not included
in the2,304 measured count. Rename forces full fresh validation in this workload;
results are not pooled with ordinary four-operation/fixed-schedule comparisons.

Ratios below are candidate/baseline, comparing medians of session metrics. Every
operation and adverse cell remains. Each session has24samples per operation; two
sessions per variant is screening evidence, not statistical equivalence/causation.

| Operation | 433 median | 433 p90 | 5,845 median | 5,845 p90 |
| --- | ---: | ---: | ---: | ---: |
| symbols | 0.995 | 0.912 | 1.007 | 0.986 |
| definition | 0.998 | 0.977 | 0.935 | 0.961 |
| references | 0.930 | 0.748 | 1.022 | 1.563 |
| workspaceSymbols | 1.000 | 0.769 | 0.981 | 0.965 |
| hover | 0.924 | 0.907 | 1.045 | 0.986 |
| diagnostics | 0.919 | 0.951 | 0.981 | 1.021 |
| rename | 0.998 | 0.958 | 1.004 | 1.017 |
| implementations | 0.992 | 0.806 | 1.018 | 0.997 |
| typeInfo | 0.886 | 1.083 | 0.968 | 1.092 |
| signatureHelp | 0.883 | 0.990 | 0.999 | 0.984 |
| callHierarchy | 0.876 | 1.150 | 0.986 | 1.039 |
| typeHierarchy | 0.885 | 1.064 | 0.987 | 1.059 |

The frozen gate stops expansion if any median orp90 ratio exceeds1.10. It triggers
for small callHierarchy p90(+15.0%) and full-graph references p90(+56.3%). Full-graph
search improves only1.9%median/3.5%p90. These results do not establish an overall win.

Full-graph reference p90s are baseline0.7825/0.8295ms and candidate1.7880/0.7320ms.
The adverse tail is concentrated in one candidate session; both sessions remain and
neither is dismissed as noise. Small callHierarchy p90s are baseline2.0143/2.0044ms
and candidate2.5608/2.0625ms. All position strata and session summaries remain in
`validated-summary.json`. The screen does not identify why a structurally lower-work
core has an adverse tail, and does not prove the source change caused each difference.
It does disqualify accepting/expanding this candidate under the declared screen.

The generated candidate stays archived/unaccepted. Production source was never
installed or changed, so no restoration/reset was needed. No unchanged retry,
post-hoc gate relaxation, fixed-schedule extension or Glider matrix follows.
The failed instruction-counter experiments remain failed; no new hardware counters
were used to explain these latency results.

## Reproduction and next step

Use the existing perf-venv on PATH. Fresh labels refuse overwrite; these commands
record the method, not authorization to repeat the rejected candidate unchanged:

```sh
FREEFLIGHT_RESPONSE_LABEL=NEW_LABEL dockpipe --workflow benchmark.reference.reader.prepare
FREEFLIGHT_RESPONSE_LABEL=NEW_LABEL FREEFLIGHT_RESPONSE_ROUNDS=24 FREEFLIGHT_RESPONSE_SCREEN=all-operations-v1 dockpipe --workflow benchmark.response.copies
FREEFLIGHT_RESPONSE_LABEL=worker-frame-view-v1 dockpipe --workflow benchmark.reference.reader.audit
```

The last command audits receipts without native execution or new queries. The prior
[work-counter qualification failures](reference-work-qualification.md) and
[fixed-schedule stage evidence](reference-fixed-attribution.md) remain within their
original limits. Next review worker immutable request ownership and Task.Run dispatch
for a concrete bounded change while preserving the independent control reader,
cancellation, gate handoff and shutdown. A new candidate needs fresh correctness and
all-operation screening before broader timing. Definition/search versus Glider, idle
qualification, native allocation, long memory runs, real repositories and other
platforms remain open. No accepted production optimization or overall win is claimed.
