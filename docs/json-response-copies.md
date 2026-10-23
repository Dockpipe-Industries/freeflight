# Redundant JSON ownership screen

Local macOS arm64, 2026-10-22. The move-only candidate is **unaccepted**. Its generated
fixed-payload core CPU cost improved, while ordinary end-to-end latency was mixed and
unfavorable in the focused workload. The two runtime files are restored exactly to
`94eb4207c8ffd2d5544bca8a52dcb8d451285015` in
`/Users/jamie/Source/freeflight-perf`, branch `investigate/rc2-warm-refresh`.
The new protocol regression test and diagnostic workflows remain uncommitted.
Main js/dev and unrelated local work are untouched. No commit, push, publication,
merge, deployment, persistent configuration change or additional agent run occurred.

## Candidate and contracts

The archived candidate changes only src/main.cpp and src/server.cpp: move the local
worker result on return, move the completed response into the result callback, build
its JSON-RPC result field by move assignment, and move the structured result into the
success envelope. It serializes text before moving the value, retaining both text
content and structured content. Arrays/scalars/null keep the existing `items` wrapper;
objects remain objects. Cancellation/delivery locking, pending-ID removal, errors,
startup root/trust authorization, parser depth/size/ID checks and worker lifecycle are
unchanged. src/process.cpp and all language-worker production files are byte-identical
to 94eb420. No cache, parser shortcut, ML or relaxed freshness contract is introduced.

Starting state/patch is retained under
`bin/.local/perf-preservation/20261022-json-copies-start`. The unaccepted source,
protocol test, candidate/full tracked patches and decision are under
`20261022-json-copies-unaccepted`. Complete frozen source/builds, compiler/options,
SDK/worker identities, logs, adapters, exact oracles, every raw session/outlier and
position strata remain in `bin/.local/benchmarks/response-copies/json-moves-v2`.
Only the two owned runtime files were restored, after source-hash checks and archival.
The original main checkout was never used as a replacement source.

## Qualification and retained setup failure

Baseline 94 and candidate are built with AppleClang 21, Release C++23, the same pinned
CMake and local nlohmann JSON headers. Both pass native protocol/process targets 2/2.
The current protocol suite also passes 24 unittest cases against each frozen binary.
The new case checks twelve payload shapes in both modern and initialized legacy MCP:
empty objects/arrays, null, booleans, integer/float, escaped Unicode, inner reserved
keys, a 1,024-item array and a large escaped Unicode object. It verifies both content
forms exactly and checks outer metadata without mutating inner payload keys. Existing
malformed/deep JSON, path/root, resource, cancellation and lifecycle cases also pass.

`json-moves-v1` preserves a test-setup failure, before candidate build or any timing:
the new test omitted the required legacy initialize handshake. The unchanged 94
baseline correctly rejected all twelve legacy calls; modern payload cases and native
protocol/process tests passed. The corrected test performs initialize/initialized.
The runtime candidate did not change. No failed receipt was overwritten or included
in accepted timing. Fresh `json-moves-v2` contains both completed qualifications.

## All-operation ordinary MCP screen

The same frozen exact 94 .NET 11 worker, SDK, startup-only trust/flags and fixture are
used for both cores. Incremental validation and cooperative background recovery stay
enabled; strict application defaults are unchanged. Eight serial processes cover 433
and 5,845-file graphs, two sessions per core/size, at least five seconds warmup and 48
measured rounds. Baseline/candidate process order isABBA. A Williams design resets
measured phase and balances each operation's position and every directed within-round
predecessor pair. All 4,608 measured responses pass exact semantic comparison and
text/structured equivalence. Rename remains preview-only; all fixture source hashes
are verified before and after timing. No sampling or diagnostic core instrumentation
runs in ordinary timings. Result comparisons use medians of session metrics.

Rename forces full fresh graph validation, so this workload differs from four normal
navigation operations. Candidate/baseline ratios below are descriptive; smaller is
faster. Every session and maximum remains in the raw receipt.

| Operation | 433 median | 433 p 90 | 5845 median | 5845 p 90 |
| --- | ---: | ---: | ---: | ---: |
| symbols | 1.106 | 1.070 | 0.978 | 0.927 |
| definition | 1.082 | 0.994 | 0.959 | 1.012 |
| references | 1.044 | 0.934 | 0.967 | 1.161 |
| workspaceSymbols | 0.887 | 0.576 | 0.871 | 0.893 |
| hover | 0.856 | 0.570 | 0.987 | 0.981 |
| diagnostics | 0.981 | 0.703 | 0.951 | 0.939 |
| rename | 0.961 | 0.946 | 1.006 | 1.000 |
| implementations | 0.954 | 0.956 | 0.979 | 1.017 |
| typeInfo | 0.990 | 0.877 | 1.005 | 0.944 |
| signatureHelp | 0.974 | 1.080 | 0.992 | 0.946 |
| callHierarchy | 0.976 | 1.005 | 0.958 | 0.932 |
| typeHierarchy | 0.953 | 1.220 | 0.963 | 0.931 |

Full-graph search improves 12.9% at the median and 10.7% at p 90, but reference p 90
worsens 16.1% in both candidate sessions. Small-graph type-hierarchy p 90 worsens 22.0%
with both candidate sessions unfavorable. Small symbols/definition medians also rise.
No adverse cells are discarded or declared noise without evidence.

## Separate repeated four-operation screen

The same frozen cores/worker run eight fresh serial processes on the 5,845-file graph,
four sessions per core, at least five seconds warmup and 48 balanced measured rounds.
The fixed measured phase and process orderABBAABBA are retained. A100 ms minimum round
period is used; no rename forces recovery in this workload. All 1,536 exact measured
responses pass both content forms. Fixture hashes remain unchanged.

| Operation | Median ratio | p 90 ratio |
| --- | ---: | ---: |
| symbols | 1.039 | 1.036 |
| definition | 1.207 | 1.009 |
| references | 1.289 | 0.981 |
| workspaceSymbols | 1.003 | 0.959 |

Definition median worsens 20.7% and references 28.9%; search median is effectively
unchanged. Position strata retain unfavorable definition/reference median directions
in every position, though magnitudes differ from the aggregate. This does not prove
why the source versions differ. Worker code/answers/freshness are identical; OS
scheduling, CPU power state and frequency were not directly measured. Those possible
mechanisms are hypotheses, not grounds to accept the candidate or erase regressions.
No post-hoc acceptance threshold or overall win is claimed. A larger Glider matrix
is not justified for this unchanged candidate.

## Generated fixed-payload CPU control

`fixed-payload-profile-v1` builds generated instrumented copies of both frozen cores.
Both again pass native protocol/process targets 2/2. A retained generated search-replay
worker is identical for both cores and is primed by an exact ordinary search. Its
fixed object travels through the normal reply/parser/envelope path; it is a control,
never a fresh production semantic answer. Root authorization, depth/size/ID validation
and both content forms remain. Four fresh serial processes inABBA order, five-second
warmup,100 ms cadence and 48 measured requests each pass 192 exact replay checks.

Core thread CPU medians below are medians of session medians, milliseconds. This
observer/workload is separate from ordinary acceptance timing; nested scopes overlap.

| Scope | Baseline | Candidate |
| --- | ---: | ---: |
| coreTotal | 17.0905 | 14.1037 |
| workerResponseParse | 8.0415 | 8.3116 |
| responseConstruction | 1.7573 | 1.3897 |
| resultEnvelope | 3.4311 | 3.3061 |
| mcpSerialize | 2.1948 | 2.3627 |

Total observed core CPU falls 17.5%. Parser and MCP-serialization CPU are unfavorable
in this control and remain in the table. The source ownership changes reduce copying
and the matched total is favorable, but these measurements are not native allocation
counts, proof of causation for every scope, or an ordinary latency improvement.
Do not add nested stage medians or compare their absolute values with other observers.

## Decision and next step

Keep the candidate unaccepted and archived; production runtime stays 94eb420. Independent
`benchmark.response.copies.audit` verifies frozen source/binary identities, original
ratios, all 6,144 ordinary response records, unique session/sample IDs, position and
predecessor balance,192 generated CPU-control records and unchanged fixture hashes.
`validated-summary.json` retains per-session metrics, every adverse aggregate and
position strata; original samples are untouched. The diagnostic does not rerun timing.

Next isolate the interaction between lower core work and paced worker/boundary latency
with a predefined control before choosing a different response design. Do not repeat
this unchanged candidate merely to find a favorable run. The reference/definition gap,
Glider idle costs, native allocation, long-duration memory, real repositories and other
platforms remain unqualified. No accepted optimization is left active by this screen.

## Replay

Use the existing perf-venv on PATH. The ordinary screen and audit can use frozen
`json-moves-v2` without changing runtime source. Fresh screen labels refuse overwrite:

```sh
FREEFLIGHT_RESPONSE_LABEL=json-moves-v2 FREEFLIGHT_RESPONSE_SCREEN=NEW_LABEL dockpipe --workflow benchmark.response.copies
FREEFLIGHT_RESPONSE_LABEL=json-moves-v2 FREEFLIGHT_RESPONSE_MODE=four FREEFLIGHT_RESPONSE_SESSIONS=4 FREEFLIGHT_RESPONSE_SCREEN=NEW_LABEL dockpipe --workflow benchmark.response.copies
FREEFLIGHT_RESPONSE_LABEL=json-moves-v2 dockpipe --workflow benchmark.response.copies.audit
```

`benchmark.response.copies.prepare` freezes the worktree core into a fresh
`FREEFLIGHT_RESPONSE_LABEL`, builds matched cores and runs gates before timing. The
archived candidate must be intentionally installed after preserving any later local
changes to reproduce its source; current production is restored 94. The generated
profile uses the retained qualified replay worker and refuses to overwrite its label.
These replay commands document reproducibility, not a recommendation to repeat the
unaccepted experiment without new evidence. Normal native CMake workflows remain usable.

Follow-up: [core CPU, worker CPU and pacing context controls](copy-pacing-context.md).
