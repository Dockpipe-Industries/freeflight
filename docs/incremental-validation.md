# Incremental validation prototype

Local opt-in prototype based on `789ba8d`; strict validation remains the default.
The operator may add `--incremental-validation` to the trusted Roslyn worker argv.
It requires `--trusted-msbuild`. Semantic requests cannot enable it. No active
MCP configuration is changed by the benchmark workflow.

## Freshness contract

Strict mode admits every source path and metadata on every semantic query, with
fresh target reads and a five-second content revalidation interval. Incremental
mode deliberately changes **non-target admission**: between recovery sweeps it
reads the query target, every observed dirty graph input and every external
compiler input. An undelivered event can leave a non-target dependency stale
until the next recovery. The next semantic request starting five seconds after
the previous full recovery began performs a complete content sweep before
answering, even if every timestamp and length is unchanged. No idle background
CPU or I/O hides this work. Requests already in flight are not atomic filesystem
snapshots, consistent with the existing single-user filesystem race limitation.

Overflow/generation changes, an unavailable watcher, unknown event paths
(including directory changes), initial open and rename previews force recovery.
A generation change during refresh rejects the transaction; the next request
still requires recovery. Events arriving after capture remain pending through
version-conditional acknowledgment. Errors and cancellation do not acknowledge
events, advance recovery time, change committed byte totals or publish partial
Roslyn/snapshot/hash state.

Every selected input is bounded and read after uncached path validation.
Symlink/reparse rejection, external exact-file admission and read-only rules,
resource ceilings, UTF-8 handling and edit hashes remain in force. Resource
accounting includes unchanged committed inputs plus actual selected bytes.
Selected paths are processed in ordinal order; recovery retains whole-graph
order. Error precedence across unselected inputs necessarily differs from strict
mode: those paths are not admitted until an event or recovery.

Trusted project membership is still fixed at open. Recovery does not reevaluate
MSBuild. Reopen after adding/removing project Compile items or changing project
configuration. Missing/renamed existing inputs fail rather than silently shrinking
the solution. Unknown new source events trigger recovery, not new execution grants.

## Nucleon concepts examined

Read-only inspection of Nucleon at `de9ba1cad9be2aa2ceb34df11d268b2e0e3f0289`
(`docs/architecture.md`, `AGENTS.md`) identified transferable non-ML practices:
immutable lookup indexes established at session creation, bounded pending work,
deterministic processing order, private staging and independent correctness
oracles. This prototype uses an immutable graph lookup, the existing bounded
watcher journal and versioned acknowledgment after publication. No Nucleon code,
models or training assets were imported. Benchmark results apply to the combined
prototype; they do not isolate the contribution of each general design practice.

## Qualification and repeat

The existing `benchmark.trusted` workflow accepts
`FREEFLIGHT_TRUSTED_BENCH_INCREMENTAL=1` for candidate-only startup argv. Baseline
argv remain strict. Provenance records the selected argv, frozen source and driver
hashes. Generated fault controls exist only in `incremental_tests.py` proof builds,
never production or ordinary/profile timing builds. Strict suites also run.
The Glider workflow consumes that qualified receipt and forwards recorded candidate
argv to its isolated core configuration. It does not edit user configuration.

Synthetic
M6 fixtures are not Jamie's Linux/Biztraak workload, and opt-in freshness semantics
must be considered when comparing with strict baselines or Glider.

## M6 direct-worker qualification

Three fresh ordinary sessions per variant and graph; 50 measured rounds per session,
10 seconds of warm-up, alternating order. All 2,400 ordinary and 800 diagnostic
responses passed. Diagnostics are separate processes. Both graphs use 4,096-byte
sources and 14 cross-project callers; full graph has 5,845 inputs/26 projects.

Numbers below are medians of the three session medians / session p90s (ms),
with the largest observed steady-state sample across sessions.

| Files | Operation | Strict 789ba8d median / p90 / max | Incremental median / p90 / max |
|---:|---|---:|---:|
| 433 | symbols | 0.417 / 0.434 / 0.631 | 0.063 / 0.070 / 0.359 |
| 433 | definition | 0.417 / 0.439 / 0.766 | 0.064 / 0.072 / 0.155 |
| 433 | references | 0.716 / 0.844 / 1.264 | 0.347 / 0.400 / 0.967 |
| 433 | workspaceSymbols | 0.489 / 0.516 / 0.847 | 0.134 / 0.142 / 0.427 |
| 5845 | symbols | 5.449 / 5.907 / 8.151 | 0.082 / 0.101 / 0.190 |
| 5845 | definition | 4.545 / 5.017 / 8.327 | 0.076 / 0.091 / 0.439 |
| 5845 | references | 4.850 / 5.320 / 8.364 | 0.453 / 0.547 / 0.951 |
| 5845 | workspaceSymbols | 7.956 / 8.828 / 62.653 | 2.663 / 3.032 / 60.123 |

Full-graph post-idle outline samples: strict 161.425 / 162.118 / 159.320 ms;
incremental 158.386 / 159.623 / 155.779 ms. Small-graph samples: strict
33.980 / 33.787 / 35.078 ms; incremental 35.175 / 29.973 / 33.916 ms.
The slowest small-graph candidate sample remains slightly worse. No statistically
qualified expiry win is claimed. All full sweeps still read 23,941,120 bytes.

Separate full-graph diagnostics: outline refresh median 5.895 → 0.040 ms,
CPU 6.003 → 0.139 ms, allocations 446,696 → 32,736 bytes. Outline semantic work
was 0.023 → 0.012 ms. Search refresh was 5.062 → 0.0005 ms; search semantic
work remained 2.083 → 1.778 ms. Ordinary timing remains the performance authority.
Instrumented expiry CPU was worse: 159.869 → 168.558 ms; allocations stayed
approximately 44.79 MB and GC pause was 2.580 → 2.256 ms (one diagnostic sample
per variant). This is retained, not folded into the ordinary latency table.

Receipts: `bin/.local/benchmarks/trusted/incremental-v3/` includes raw
`samples.json`, `summary.json`, `profile-summary.json`, runtime event/tail records,
source/toolchain/fixture provenance, strict qualification and the 16-check
`candidate/incremental-proof/summary.json` with raw fault responses.

Earlier `incremental-v1` and `incremental-v2` receipts are retained. V1/V2 full
recovery was slower (v1 183.7–187.5 ms vs 159.5–159.8 ms). V3 restores bounded
request-local batch admission only for recovery sweeps, retaining uncached
pre-read validation. V1 ordinary `readDocuments` estimates assumed all graph
entries were visited and are invalid for incremental mode; its actual byte
counters and instrumented read counts remain valid. V2/V3 use live `readFiles`.
V1 refresh stage timing excludes selection; V2/V3 include it.


## Source attribution

`workers/roslyn/Program.cs` exposes the startup mode and live counters near line
204. `SelectIncrementalFiles` (line 418) uses the immutable catalogue and bounded
captured event set. `Refresh` (line 444) chooses recovery based on generation and
elapsed time, then reuses the existing guarded reads and staged Roslyn updates.
Uncached pre-read validation remains at line 546. Generation validation before
publication is at line 591; byte totals, recovery time and conditional event
acknowledgment publish at lines 603–616. Broad declaration search remains the
existing `SemanticQueries.WorkspaceSymbols` at line 50; no new semantic service
or answer cache was introduced.

## Repeat commands on this M6

Use fresh receipt labels; existing receipts intentionally cannot be overwritten.
Run from the isolated `freeflight-perf` checkout. The paths below select existing
installed toolchains and do not change active MCP configuration.

```sh
export PATH="$PWD/bin/.local/perf-venv/bin:/Users/jamie/Documents/Codex/2026-10-20/task/freeflight-dependabot/bin/.local/dotnet11:$PATH"
export DOTNET_CLI_USE_MSBUILD_SERVER=0
FREEFLIGHT_TRUSTED_BENCH_LABEL=incremental-repeat \
FREEFLIGHT_TRUSTED_BENCH_BASELINE=789ba8d \
FREEFLIGHT_TRUSTED_BENCH_INCREMENTAL=1 \
FREEFLIGHT_TRUSTED_BENCH_SESSIONS=3 \
FREEFLIGHT_TRUSTED_BENCH_ROUNDS=50 \
FREEFLIGHT_TRUSTED_BENCH_WARMUP=10 \
FREEFLIGHT_TRUSTED_BENCH_PADDING=4096 \
FREEFLIGHT_TRUSTED_BENCH_CALLERS=14 \
FREEFLIGHT_TRUSTED_BENCH_QUERY=C5 \
dockpipe --workflow benchmark.trusted

FREEFLIGHT_GLIDER_LABEL=incremental-repeat \
FREEFLIGHT_GLIDER_CANDIDATE_RECEIPT="$PWD/bin/.local/benchmarks/trusted/incremental-repeat" \
FREEFLIGHT_GLIDER_DOTNET_ROOT=/Users/jamie/Documents/Codex/2026-10-19/task/toolchains/dotnet \
FREEFLIGHT_GLIDER_SESSIONS=3 \
FREEFLIGHT_GLIDER_ROUNDS=50 \
FREEFLIGHT_GLIDER_WARMUP=10 \
dockpipe --workflow benchmark.trusted.glider
```

Default candidate is the current working tree; frozen source hashes identify the
actual code tested. The MCP workflow pins shipped FreeFlight `97c1342` and official
Glider 13.3.0 and records native candidate arguments, bundle hashes and shared
net10.0 fixture provenance. Worker qualification uses the repository-pinned .NET 11
preview SDK. These distinct transports/toolchains are not pooled.

## Qualification limits

Fault proofs deterministically inject watcher-generation changes, suppress event
delivery and dispose the watcher in generated test builds. They cover recovery
state transitions, not every native OS buffer/driver failure. Deadline fault tests
advance the recovery clock seam; ordinary 5.1-second idle measurements exercise
real elapsed-time recovery. Late cancellation is injected at the publication
boundary; existing worker suites also exercise real protocol cancellation.

Linux and Windows execution are not qualified in this local M6 pass. The default
strict path and fallback code remain, but their presence is not cross-platform
test evidence. Unknown event paths conservatively force a full sweep, so workloads
with frequent unrelated directory events can perform worse than these unchanged
fixtures. The five-second recovery cost remains O(N), with no background work to
hide it. The incremental mode is an explicit operator choice, not a claim that
non-target files receive strict per-query admission.

Glider omits definition/search columns and reference end positions in some API
results. The reused adapter checks exposed locations exactly and qualifies source
declarations separately before timing; it does not fabricate missing fields or
claim byte-identical response envelopes. Product freshness/security policies and
response sizes differ. Current measurements establish performance only for these
M6 synthetic graphs and workloads.

## Actual MCP comparison: shipped / incremental / Glider

All 7,200 steady-state and 144 post-idle responses passed in 36 fresh processes,
with three sessions per product, graph and cadence. Products rotate order.
The same source hashes and solution-wide semantic oracle are used throughout.
Both products await compilation readiness; load and background compilation remain separate.

Each cell is median / p90 / max in ms, using medians of the three session medians
and p90s, plus the maximum across all three. Shipped is `97c1342`; candidate is
local incremental V3; Glider is the official pinned 13.3.0 installation.

| Files | Cadence | Operation | Shipped | Incremental | Glider |
|---:|---|---|---:|---:|---:|
| 433 | back-to-back | symbols | 0.582 / 0.597 / 0.934 | 0.152 / 0.164 / 0.282 | 0.192 / 0.204 / 0.233 |
| 433 | back-to-back | definition | 0.563 / 0.570 / 0.776 | 0.142 / 0.156 / 0.434 | 0.058 / 0.124 / 0.136 |
| 433 | back-to-back | references | 0.929 / 1.010 / 1.530 | 0.474 / 0.557 / 2.201 | 0.493 / 0.617 / 3.102 |
| 433 | back-to-back | workspaceSymbols | 0.669 / 0.687 / 1.036 | 0.239 / 0.252 / 0.560 | 0.453 / 0.541 / 0.660 |
| 433 | 100 ms rounds | symbols | 6.273 / 6.719 / 35.827 | 2.092 / 2.472 / 38.230 | 2.137 / 2.477 / 2.963 |
| 433 | 100 ms rounds | definition | 3.717 / 4.191 / 5.360 | 1.302 / 1.519 / 1.871 | 0.653 / 0.798 / 0.991 |
| 433 | 100 ms rounds | references | 4.468 / 5.112 / 7.743 | 3.143 / 3.798 / 6.300 | 3.103 / 3.491 / 4.669 |
| 433 | 100 ms rounds | workspaceSymbols | 3.294 / 3.869 / 5.045 | 2.059 / 2.410 / 4.067 | 3.839 / 4.379 / 4.770 |
| 5845 | back-to-back | symbols | 8.765 / 9.277 / 13.291 | 0.221 / 0.263 / 0.371 | 0.229 / 0.286 / 0.472 |
| 5845 | back-to-back | definition | 7.163 / 7.508 / 9.939 | 0.173 / 0.186 / 0.254 | 0.084 / 0.096 / 0.220 |
| 5845 | back-to-back | references | 7.444 / 7.828 / 8.525 | 0.614 / 1.003 / 1.142 | 0.642 / 0.762 / 0.949 |
| 5845 | back-to-back | workspaceSymbols | 15.639 / 16.480 / 19.388 | 8.115 / 8.750 / 11.561 | 7.737 / 8.579 / 20.432 |
| 5845 | 100 ms rounds | symbols | 11.227 / 11.768 / 128.291 | 1.587 / 1.717 / 144.599 | 1.691 / 1.888 / 2.581 |
| 5845 | 100 ms rounds | definition | 8.087 / 8.657 / 19.438 | 0.808 / 0.967 / 1.362 | 0.456 / 0.563 / 0.878 |
| 5845 | 100 ms rounds | references | 7.862 / 8.314 / 12.378 | 2.238 / 2.774 / 5.240 | 2.565 / 3.071 / 4.085 |
| 5845 | 100 ms rounds | workspaceSymbols | 15.425 / 16.639 / 24.145 | 24.324 / 27.166 / 31.878 | 24.585 / 26.367 / 32.510 |

This is **not an overall Glider win**. Full-graph outlines are near parity.
Paced references improve, but unpaced reference p90 is worse than Glider.
Definitions remain about 1.8–2.1 times slower on the full graph. Full-graph paced
search regresses versus shipped: median 15.425 → 24.324 ms and p90 16.639 →
27.166 ms, roughly level with Glider. Unpaced search remains slightly slower
(8.115 versus 7.737 ms). The paced search regression is reproducible in these
paired sessions, but its CPU scheduling/semantic/payload cause is **not isolated**
by this uninstrumented MCP run; do not attribute it to a specific runtime mechanism.
The direct-worker profile is unpaced and cannot explain this paced end-to-end result.

Full-graph steady-state outline maximum is still 144.599 ms (shipped 128.291;
Glider 2.581) because recovery can land inside the measured phase. Small-graph
paced outline maximum is 38.230 ms versus shipped 35.827 and Glider 2.963.
These unfavorable tails remain in raw receipts.

Post-idle outline samples below preserve each fresh session, grouped by product;
first three are unpaced sessions, last three paced sessions.

| Files | Product | Six post-idle samples (ms) | Median |
|---:|---|---|---:|
| 433 | freeflight | 36.765 / 36.848 / 25.084 / 37.114 / 33.179 / 35.069 | 35.917 |
| 433 | candidate | 33.144 / 27.005 / 33.868 / 34.688 / 25.622 / 33.536 | 33.340 |
| 433 | glider | 2.490 / 2.289 / 2.320 / 2.262 / 2.280 / 2.180 | 2.285 |
| 5845 | freeflight | 177.907 / 177.561 / 178.461 / 182.575 / 179.915 / 187.168 | 179.188 |
| 5845 | candidate | 158.421 / 158.476 / 159.795 / 157.112 / 158.463 / 157.125 | 158.442 |
| 5845 | glider | 2.674 / 2.823 / 2.299 / 8.912 / 9.291 / 9.217 | 5.868 |

Startup/readiness medians across six fresh sessions per product/size (ms):

| Files | Product | Discovery | Load | Background compilation |
|---:|---|---:|---:|---:|
| 433 | freeflight | 3.634 | 769.314 | awaited inside load |
| 433 | candidate | 3.265 | 770.452 | awaited inside load |
| 433 | glider | 132.562 | 656.741 | 287.500 |
| 5845 | freeflight | 3.419 | 3082.489 | awaited inside load |
| 5845 | candidate | 3.526 | 3113.206 | awaited inside load |
| 5845 | glider | 131.734 | 2027.205 | 512.000 |

MCP receipts: `bin/.local/glider-comparison/incremental-v3/`, including raw
`samples.json`, `summary.json`, provenance, frozen drivers, native package hashes
and validated semantic responses. CPU/allocation/GC figures above are separate
FreeFlight diagnostics, not equivalent Glider instrumentation. No Glider CPU or
allocation superiority claim follows.

The prototype is retained locally for review, with strict mode unchanged as the
default. No push, PR, merge, release, deployment, active MCP or Biztraak changes.
No execution blocker remains. Linux/Windows execution, broader mutation workloads,
Glider CPU/allocation measurement and the paced-search regression remain unqualified.
