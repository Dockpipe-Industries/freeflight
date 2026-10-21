# Search and response performance investigation

**Outcome:** no regression-free runtime winner. Runtime is restored to `d8232ec`;
local candidates `5d14a4a` (combined) and `5c44c97` (response only) preserve the
tested alternatives. The workflows and all favorable/unfavorable evidence remain.
Neither candidate is approved for promotion.

Local continuation from `d8232ec`; no change to strict-default or incremental
freshness/recovery contracts. No answer cache, background maintenance, project
scope reduction, publication or active configuration change.

## Paced regression diagnosis

`bin/.local/benchmarks/trusted/incremental-paced-profile/` compares strict
`789ba8d` with unchanged incremental `d8232ec`, in matched 100 ms rounds. The
ordinary run reproduces the full-graph search regression (median ratio 1.963,
p90 ratio 2.010; both candidate sessions unfavorable). Instrumentation is confined
to separate builds/processes and now splits declaration discovery, ordering and
result construction.

Full-graph diagnostic search medians (strict → incremental): refresh 5.633 →
0.005 ms; declaration discovery 1.945 → 9.517 ms; ordering 0.264 → 0.743 ms;
rendering 0.240 → 0.594 ms; semantic total 2.527 → 11.352 ms. CPU was 8.878 →
13.231 ms, allocation 2,569,216 → 2,164,108 bytes, and median GC pause zero.
No thread-pool work completed during those samples. Thus the remaining regression
is in semantic/search execution, not the removed refresh pass or measured queue
dispatch. The exact reason unchanged Roslyn work costs more after pacing is not
isolated: these counters do not establish CPU frequency, cache residency or core
placement as the cause.

The installed Roslyn 5.9.0 nuspec pins repository commit
`35d9211b841e7613c1d2f8f5af6d628ace696c4c`.
[Custom search](https://github.com/dotnet/roslyn/blob/35d9211b841e7613c1d2f8f5af6d628ace696c4c/src/Workspaces/Core/Portable/FindSymbols/SymbolFinder_Declarations_CustomQueries.cs)
performs a syntactic existence precheck before querying each compilation.
[Project.ContainsAsync](https://github.com/dotnet/roslyn/blob/35d9211b841e7613c1d2f8f5af6d628ace696c4c/src/Workspaces/Core/Portable/Workspace/Solution/Project.cs)
queries every document index with `Task.WhenAll` and then checks whether any match
exists. The trusted benchmark has awaited all compilations at open. Removing this
redundant existence scan is therefore a testable optimization; it is not evidence
about Glider's unpublished internals.

## Rejected unrestricted bypass and guarded candidate

`compilation-search-v1` failed the independent oracle before timing. Querying
`Finalize` returned a destructor that the old workspace API omitted. The compiler
name and syntactic declaration name differ. The failed source, logs and runtime
patch are retained in that receipt. No benchmark from that candidate is accepted.

The revised path still uses Roslyn's compilation symbols and existing output
ordering. It applies the existing explicit type/member and accessor filters. For
each project, one ordinary syntax declaration whose name matches the predicate
proves that the old syntactic existence precheck would succeed. Only then may the
compilation result bypass that precheck. If no such witness exists, the original
project-level `SymbolFinder.FindSourceDeclarationsAsync` runs. Empty filtered
compilation results are already empty regardless of the precheck. Unknown syntax,
compiler-generated names and special declarations therefore retain the old API's
behavior. A `TryGetCompilation` guard also retains the original API when the
compilation is not already available; a negative cold search must not trigger a
compilation merely to bypass the precheck. No new parser or persistent semantic
cache is introduced.

The generated differential harness compares complete JSON results/errors with the
unaltered `d8232ec` implementation. Its 104 comparisons cover types, fields, events,
properties/accessors, operators, destructors, explicit interfaces, indexers,
records, partial methods, Unicode names, shared external-style contexts, source
edits/removal, empty queries and the 1000-result limit; cancellation is separate.
`compilation-search-v2` additionally runs existing worker/trusted, mutation,
metadata, read-cancellation, 16 incremental and transaction tests. Measurements
are retained separately from the final guarded `compilation-search-v3` run.
The latter also alternates differential-oracle call order and proves a negative
cold search leaves every project uncompiled. Final qualification is in progress.

## Recovery evidence and contract boundary

In the paced diagnostic, a full recovery reads all 5,845 files / 23,941,120 bytes.
Incremental expiry refresh was 161.462 ms: opens 68.137 ms, uncached path checking
40.994 ms, actual read calls 7.686 ms, hash append 10.719 ms and buffer writes
2.721 ms. Stage scopes overlap; do not sum them as disjoint percentages. CPU was
166.117 ms and allocation 45,304,120 bytes. GC pause was 2.054 ms. This identifies
per-file open/path work as the main cost, not bulk byte transfer alone.

After 5.1 seconds idle, every input may be beyond the freshness deadline. A staged
sweep that returns the first semantic response before checking the remaining
inputs would violate the documented recovery guarantee. Splitting work across
future requests does not repair that contradiction. Idle background maintenance
would change the documented no-background-work behavior and requires separate
CPU/I/O, contention, failure and age qualification before any contract decision.
No such change is made here. Bounded parallel full recovery could retain the
contract in principle, but would need explicit proofs for deterministic error
precedence, aggregate resource accounting, cancellation and publication; it is
not claimed qualified by these measurements.


## Retained intermediate evidence

`compilation-search-v2` completed 2,400 ordinary and 800 diagnostic worker
responses, three fresh sessions per variant/size. Full-graph search median/p90
ratios against incremental `d8232ec` were 0.732/0.722. Instrumented declaration
discovery fell from 10.948 to 6.846 ms; semantic total 12.667 to 8.898 ms;
CPU 13.904 to 10.145 ms and allocation 2,154,788 to 2,017,352 bytes. These are
instrumented worker observations, not MCP end-to-end timings.

The corresponding four-product MCP comparison completed 6,400 steady-state and
128 idle semantic checks across 32 fresh processes. Full-graph paced search
candidate/local-baseline median/p90 ratios were only 0.969/0.939. It remained
1.540/1.533 times shipped FreeFlight; candidate/Glider was 0.967/0.948. Unpaced
candidate/Glider search was 1.010/0.959. Non-search regressions were retained:
full-graph paced outline median/p90 ratios versus local baseline were 1.068/1.071,
definition 1.060/1.081, references 1.072/0.941. This is not an overall win.
The intermediate candidate is superseded by the cold-compilation guard; do not
publish its timing as qualification of a different source tree.

The worker run's final summary initially rejected an unrelated benchmark-adapter
edit made during execution. Raw measurements had completed. The exact frozen
adapter was restored, all provenance guards passed on summary regeneration, and
the new adapter was then restored. The receipt's `summary-recovery-note.json`
records this event; no measurements were discarded or substituted.


## Repeating the comparison

Use a clean checkout with the repository SDK and the prerequisites in
[the trusted workflow guide](trusted-performance-workflow.md) and
[the Glider guide](glider-head-to-head.md). Generated receipts remain local under
`bin/.local`; each label must be new. Do not run concurrent performance workloads.
The local-baseline native receipt is verified against the requested commit before
reuse, including all native-file and source hashes.

```sh
FREEFLIGHT_TRUSTED_BENCH_LABEL=search-repeat \
FREEFLIGHT_TRUSTED_BENCH_BASELINE=d8232ec \
FREEFLIGHT_TRUSTED_BENCH_BASELINE_INCREMENTAL=1 \
FREEFLIGHT_TRUSTED_BENCH_INCREMENTAL=1 \
FREEFLIGHT_TRUSTED_BENCH_SESSIONS=3 \
FREEFLIGHT_TRUSTED_BENCH_ROUNDS=50 \
FREEFLIGHT_TRUSTED_BENCH_WARMUP=10 \
FREEFLIGHT_TRUSTED_BENCH_INTERVAL=0.1 \
FREEFLIGHT_TRUSTED_BENCH_PADDING=4096 \
FREEFLIGHT_TRUSTED_BENCH_CALLERS=14 \
FREEFLIGHT_TRUSTED_BENCH_QUERY=C5 \
dockpipe --workflow benchmark.trusted
```

Then set `FREEFLIGHT_GLIDER_LABEL` to a new label,
`FREEFLIGHT_GLIDER_CANDIDATE_RECEIPT` to that absolute worker receipt directory,
`FREEFLIGHT_GLIDER_DOTNET_ROOT` to the SDK 10.0.402 installation, and run
`dockpipe --workflow benchmark.trusted.glider`. The guide describes official
Glider 13.3.0 and published FreeFlight bundle verification. Optional
`FREEFLIGHT_GLIDER_LOCAL_BASELINE_RECEIPT` plus
`FREEFLIGHT_GLIDER_LOCAL_BASELINE_REF=d8232ec` adds the verified retained native
prototype. Set sessions=2, rounds=50 and warm-up=10 through the documented
`FREEFLIGHT_GLIDER_*` variables to reproduce this bounded four-product run.

This adapter currently publishes an osx-arm64 worker and uses the generated
433/5,845-file solution fixtures. It does **not** qualify arbitrary user solutions
by changing a root path. Such a run needs a workload manifest with project and
source hashes, expected complete symbol results, definition ranges and reference
locations, plus readiness criteria for both tools. Counts alone are insufficient.
The raw receipts and exact comparisons are reusable; portable arbitrary-solution
manifest support remains an explicit tooling gap, not a claimed capability.


## Owned MCP response construction

The core previously copied the structured result into an initializer-list
response, copied that response into the completion lambda, and copied it again
into the JSON-RPC envelope. `benchmark.response` replays the saved full-graph search
payload against both constructions. It verifies identical serialized bytes for
14 object/array/scalar/null and modern/legacy cases, then records three fresh
processes with alternating order. This is an allocation-instrumented diagnostic,
not an end-to-end product benchmark.

`bin/.local/benchmarks/response/copy-v1` recorded old medians
2.811/2.796/2.809 ms and moved medians 1.542/1.502/1.507 ms. Old p90 was
3.054/2.860/2.851 ms; moved p90 1.687/1.548/1.543 ms. Allocation calls fell
69,009 → 91 and allocated bytes 6,568,728 → 2,198,096 per construction.
Input parsing and an equal starting payload copy are excluded for both variants;
output serialization is included. These allocation counts are C++ allocations,
separate from the managed-worker allocation/GC measurements.

The production change transfers owned JSON values after generating the text
representation. Both `content` and `structuredContent`, completion metadata,
errors, IDs and JSON-RPC framing remain. Cancellation acceptance/delivery and
output locks stay in their existing positions. Other callers still copy borrowed
values when necessary. No payload truncation or narrower semantic result is used.

Repeat the diagnostic after `core.build` has provisioned the pinned JSON header:

```sh
FREEFLIGHT_RESPONSE_LABEL=copy-repeat \
FREEFLIGHT_RESPONSE_PAYLOAD=/absolute/path/to/workspaceSymbols-validated.json \
dockpipe --workflow benchmark.response
```

For the combined final MCP candidate, additionally set
`FREEFLIGHT_GLIDER_BUILD_CANDIDATE_CORE=1`. The existing comparison workflow freezes
the local core source, builds it and runs protocol/process tests before starting
any timed process; the core binary, source, compiler, dependency header and test
log are included in provenance. The retained local baseline core is built from its pinned commit with identical
compiler options and dependency headers, and receives the same test gates. The
shipped product remains the published binary. These distinctions are explicit in
the receipt.

`compilation-search-v3` retained three ordinary sessions per variant/graph and
separate diagnostic sessions: search median/p90 ratios versus `d8232ec` were
0.642/0.625 (small) and 0.741/0.749 (full). It passed the cold-workspace proof.
The final candidate restores the symbol-budget check to the unchanged `Ordered`
method, after discovery of all projects, to preserve original failure/cancellation
precedence. Final worker qualification is labeled `compilation-response-v4`;
intermediate timing is not substituted for that exact source.


Whole-session child CPU receipts in the final MCP run include startup, load,
readiness, initial semantic qualification, repeated warm-up, ordinary queries and the idle check, and exclude
Python driver work. Different tools execute different numbers of warm-up queries
in the fixed time window. These totals are not normalized per-operation CPU or a
Glider allocation profile. Managed allocation/GC comparisons come from the
separately instrumented FreeFlight worker sessions only.


The first combined native attempt (`compilation-response-v4`) stopped before any
timing because `cmake` was absent from the DockPipe host PATH. Native worker
publication/tests and baseline hash verification had passed. The failure receipt
is retained. The retry uses `FREEFLIGHT_GLIDER_CMAKE` to select the existing
CMake 3.31.8 executable explicitly; no toolchain installation or machine change
was needed. When CMake is not on PATH, set this variable for reproducibility.
The final native receipt label is `compilation-response-v4b`.

Final worker profiling (`compilation-response-v4`, instrumented full-graph search)
records baseline → candidate: declaration discovery 9.661 → 6.833 ms, semantic
work 11.110 → 8.915 ms, CPU 12.221 → 10.122 ms and managed allocation
2,169,044 → 2,018,304 bytes. Median GC pause was zero for both; p90 GC pause was
0.787 → 1.085 ms, so the reduced allocation does not establish a GC-tail win.
Ten versus five JIT-start events occurred during these steady samples; the raw
runtime events are retained, without assigning them causal percentages.

The candidate's separate expiry sample still read all 5,845 files / 23,941,120
bytes. Refresh was 161.547 ms, CPU 161.882 ms, allocation 45,163,832 bytes and GC
pause 2.065 ms. Nested open/path/read scopes were 68.529/42.748/7.917 ms. This
confirms that the search/response changes do not resolve bulk recovery. It does
not establish an unavoidable 161 ms lower bound for other implementations.


## Combined candidate MCP results

All combined-candidate native sessions passed. Same M6, synthetic 433/5,845-file graphs;
not a Linux or Biztraak rerun. Two fresh processes per product/size/cadence,
10 seconds warm-up and 50 measured rounds. Four products with reversed order
in the second session. All 6,400 steady-state and 128 post-idle semantic checks
passed. Worker validation separately passed 2,400 ordinary and 800 diagnostic
responses, 104 search comparisons, cold-negative/cancellation checks, 16
incremental fault checks and five failed-refresh preservation cases per variant.
Both local cores passed 23 protocol tests and the process/IPC/cancellation suite.

Tables report median of session medians / median of session p90 / maximum of
all retained ordinary samples, in milliseconds. All large periodic outliers are retained;
none are removed. Worker profiles separately identify full-recovery costs. These bounded samples are not a statistical universal-win claim.


### 433 files, 0-second round pacing

| Operation | Shipped | d8232ec | Final candidate | Glider |
| --- | ---: | ---: | ---: | ---: |
| symbols | 0.572 / 0.589 / 0.961 | 0.150 / 0.162 / 0.354 | 0.144 / 0.154 / 0.259 | 0.166 / 0.203 / 0.223 |
| definition | 0.551 / 0.560 / 0.568 | 0.141 / 0.157 / 0.284 | 0.138 / 0.159 / 0.184 | 0.073 / 0.127 / 0.141 |
| references | 0.925 / 0.997 / 2.081 | 0.469 / 0.575 / 1.864 | 0.460 / 0.477 / 1.042 | 0.476 / 0.564 / 1.770 |
| workspaceSymbols | 0.658 / 0.677 / 0.887 | 0.237 / 0.260 / 0.493 | 0.185 / 0.194 / 0.343 | 0.449 / 0.506 / 0.709 |

### 433 files, 0.1-second round pacing

| Operation | Shipped | d8232ec | Final candidate | Glider |
| --- | ---: | ---: | ---: | ---: |
| symbols | 6.227 / 6.671 / 35.534 | 2.107 / 2.482 / 33.959 | 2.063 / 2.369 / 36.559 | 2.077 / 2.384 / 3.775 |
| definition | 3.733 / 4.237 / 4.632 | 1.299 / 1.505 / 1.918 | 1.278 / 1.486 / 1.761 | 0.641 / 0.781 / 1.088 |
| references | 4.399 / 5.367 / 6.920 | 3.262 / 3.958 / 5.495 | 3.123 / 3.846 / 6.043 | 3.130 / 3.665 / 4.981 |
| workspaceSymbols | 3.269 / 3.724 / 4.901 | 2.030 / 2.284 / 4.158 | 1.521 / 1.710 / 3.284 | 3.778 / 4.188 / 4.863 |

### 5845 files, 0-second round pacing

| Operation | Shipped | d8232ec | Final candidate | Glider |
| --- | ---: | ---: | ---: | ---: |
| symbols | 8.880 / 9.311 / 11.651 | 0.220 / 0.259 / 0.678 | 0.202 / 0.236 / 0.397 | 0.203 / 0.256 / 4.560 |
| definition | 7.136 / 7.615 / 7.989 | 0.173 / 0.188 / 0.397 | 0.169 / 0.180 / 0.500 | 0.081 / 0.105 / 0.208 |
| references | 7.489 / 7.848 / 9.131 | 0.607 / 0.805 / 1.169 | 0.591 / 0.680 / 1.789 | 0.606 / 0.718 / 3.024 |
| workspaceSymbols | 15.523 / 16.463 / 18.675 | 8.011 / 8.525 / 11.497 | 6.619 / 6.954 / 10.104 | 7.457 / 8.369 / 17.765 |

### 5845 files, 0.1-second round pacing

| Operation | Shipped | d8232ec | Final candidate | Glider |
| --- | ---: | ---: | ---: | ---: |
| symbols | 11.324 / 11.880 / 91.686 | 1.548 / 1.722 / 144.079 | 1.607 / 1.891 / 151.085 | 1.680 / 1.914 / 2.130 |
| definition | 8.148 / 8.659 / 16.062 | 0.793 / 0.951 / 1.254 | 0.817 / 1.046 / 2.224 | 0.463 / 0.585 / 0.905 |
| references | 7.825 / 8.214 / 16.683 | 2.166 / 2.779 / 4.312 | 2.266 / 2.932 / 4.845 | 2.558 / 2.987 / 3.393 |
| workspaceSymbols | 15.516 / 16.519 / 24.559 | 24.104 / 26.872 / 34.741 | 22.224 / 24.077 / 32.511 | 24.485 / 26.575 / 30.493 |

### Startup and first post-idle query

Pooled across the four fresh processes per product/size (two cadences).
Load and background readiness are separate; FreeFlight awaits compilation in load.
CPU is the whole waited child-process session, not per-query CPU; warm-up query
counts differ. Idle values are the first outline after 5.1 seconds, median/max.

| Files | Product | Load median ms | Background readiness median ms | Idle outline median/max ms | Whole-session CPU median s |
| ---: | --- | ---: | ---: | ---: | ---: |
| 433 | Shipped 97c1342 | 770.6 | inside load | 35.06 / 37.57 | 14.47 |
| 433 | d8232ec incremental | 767.3 | inside load | 34.47 / 37.16 | 15.70 |
| 433 | Final incremental + owned responses | 762.7 | inside load | 33.26 / 34.07 | 15.70 |
| 433 | Glider 13.3.0 | 653.9 | 285.5 | 2.40 / 2.50 | 20.43 |
| 5845 | Shipped 97c1342 | 3125.7 | inside load | 181.20 / 197.65 | 17.44 |
| 5845 | d8232ec incremental | 3003.5 | inside load | 158.15 / 159.51 | 14.12 |
| 5845 | Final incremental + owned responses | 3053.7 | inside load | 158.25 / 159.03 | 13.74 |
| 5845 | Glider 13.3.0 | 2001.4 | 510.0 | 4.84 / 8.19 | 18.35 |


## Mixed result and response-only control

The combined candidate improves full-graph search versus incremental `d8232ec`
by 17.4% median / 18.4% p90 unpaced and 7.8% / 10.4% paced. It beats Glider's
search in these sessions, but remains 43.2% slower than shipped FreeFlight's paced
search. Full-graph paced outline, definition and reference medians regress
3.8%, 3.1% and 4.6%; their p90 regressions are 9.8%, 9.9% and 5.5%. Idle recovery
is unchanged at about 158 ms. This is not accepted as an overall winner.

A bounded `response-only-control` reuses the already qualified `incremental-v3`
worker source with only the new core ownership change. The worker receipt was
created before the `d8232ec` commit, so its recorded HEAD is older, but every
worker-source hash was checked against `d8232ec` and matches exactly. Matched core
builds, native worker/core tests, both graphs/cadences and both product sessions
remain unchanged. The combined candidate and all its unfavorable samples remain
recoverable; the control will determine which source is retained as the next
local candidate.

Exact response-only control command on this M6, from the repository root (choose
an unused label). The SDK, CMake and prior receipts must already exist; the guide
above covers preparation. These local refs/receipts are not advertised as a
published, arbitrary-solution benchmark package.

```sh
PATH="$PWD/bin/.local/perf-venv/bin:/Users/jamie/Documents/Codex/2026-10-20/task/freeflight-dependabot/bin/.local/dotnet11:$PATH" \
DOTNET_CLI_USE_MSBUILD_SERVER=0 \
FREEFLIGHT_GLIDER_LABEL=response-only-repeat \
FREEFLIGHT_GLIDER_CMAKE=/Users/jamie/Documents/Codex/2026-10-19/task/toolchains/cmake-3.31.8-macos-universal/CMake.app/Contents/bin/cmake \
FREEFLIGHT_GLIDER_CANDIDATE_RECEIPT="$PWD/bin/.local/benchmarks/trusted/incremental-v3" \
FREEFLIGHT_GLIDER_LOCAL_BASELINE_RECEIPT="$PWD/bin/.local/glider-comparison/incremental-v3" \
FREEFLIGHT_GLIDER_LOCAL_BASELINE_REF=d8232ec \
FREEFLIGHT_GLIDER_BUILD_CANDIDATE_CORE=1 \
FREEFLIGHT_GLIDER_CANDIDATE_CORE_REF=5c44c97 \
FREEFLIGHT_GLIDER_DOTNET_ROOT=/Users/jamie/Documents/Codex/2026-10-19/task/toolchains/dotnet \
FREEFLIGHT_GLIDER_SESSIONS=2 FREEFLIGHT_GLIDER_ROUNDS=50 FREEFLIGHT_GLIDER_WARMUP=10 \
dockpipe --workflow benchmark.trusted.glider
```

A new checkout without the retained native baseline first runs the trusted worker
workflow at the selected baseline ref (set `FREEFLIGHT_TRUSTED_BENCH_CANDIDATE` as
well as `BASELINE`), then the Glider workflow with that candidate worker receipt
and without the core-build flag. That creates the source-verified native baseline
receipt. The core comparison requires this receipt/ref and builds both local cores
with matching options. Only use refs available to the reproducing checkout.


## Response-only control results

All 32 fresh processes passed: 6,400 ordinary and 128 post-idle semantic checks.
Native worker tests and both cores' protocol/process gates passed. This is the
unchanged d8232ec worker plus owned MCP responses, not the guarded search worker.
The table convention remains median / p90 / max in milliseconds.


### Control: 433 files, 0-second round pacing

| Operation | Shipped | d8232ec | Response only | Glider |
| --- | ---: | ---: | ---: | ---: |
| symbols | 0.571 / 0.586 / 0.747 | 0.150 / 0.156 / 0.235 | 0.146 / 0.168 / 0.269 | 0.165 / 0.205 / 0.230 |
| definition | 0.553 / 0.563 / 0.859 | 0.140 / 0.149 / 0.261 | 0.140 / 0.150 / 0.288 | 0.104 / 0.127 / 0.136 |
| references | 0.930 / 1.065 / 2.091 | 0.469 / 0.527 / 0.900 | 0.465 / 0.552 / 0.999 | 0.467 / 0.568 / 3.079 |
| workspaceSymbols | 0.658 / 0.679 / 1.036 | 0.237 / 0.246 / 0.542 | 0.226 / 0.237 / 0.509 | 0.447 / 0.516 / 0.643 |

### Control: 433 files, 0.1-second round pacing

| Operation | Shipped | d8232ec | Response only | Glider |
| --- | ---: | ---: | ---: | ---: |
| symbols | 6.266 / 6.670 / 37.262 | 2.076 / 2.342 / 33.087 | 2.074 / 2.354 / 33.542 | 2.130 / 2.382 / 2.587 |
| definition | 3.768 / 4.220 / 4.981 | 1.282 / 1.450 / 1.763 | 1.337 / 1.519 / 31.038 | 0.648 / 0.771 / 1.061 |
| references | 4.479 / 5.196 / 6.552 | 3.235 / 3.809 / 5.549 | 3.156 / 3.789 / 6.804 | 3.118 / 3.464 / 4.354 |
| workspaceSymbols | 3.292 / 3.870 / 4.786 | 2.080 / 2.373 / 32.084 | 1.996 / 2.137 / 2.467 | 3.825 / 4.207 / 4.933 |

### Control: 5845 files, 0-second round pacing

| Operation | Shipped | d8232ec | Response only | Glider |
| --- | ---: | ---: | ---: | ---: |
| symbols | 8.867 / 9.352 / 12.434 | 0.219 / 0.257 / 0.324 | 0.199 / 0.224 / 0.347 | 0.198 / 0.234 / 0.334 |
| definition | 7.178 / 7.573 / 8.250 | 0.172 / 0.189 / 0.305 | 0.168 / 0.177 / 0.246 | 0.077 / 0.103 / 0.121 |
| references | 7.523 / 7.931 / 10.384 | 0.602 / 0.651 / 1.818 | 0.581 / 0.768 / 1.038 | 0.628 / 0.736 / 0.841 |
| workspaceSymbols | 15.574 / 16.459 / 18.880 | 8.000 / 8.507 / 11.457 | 7.142 / 7.510 / 10.699 | 7.401 / 8.368 / 19.374 |

### Control: 5845 files, 0.1-second round pacing

| Operation | Shipped | d8232ec | Response only | Glider |
| --- | ---: | ---: | ---: | ---: |
| symbols | 11.268 / 11.716 / 126.034 | 1.565 / 1.782 / 143.666 | 1.540 / 1.743 / 2.183 | 1.647 / 1.924 / 2.273 |
| definition | 8.104 / 8.581 / 26.033 | 0.791 / 0.917 / 142.745 | 0.819 / 1.006 / 144.648 | 0.445 / 0.584 / 0.772 |
| references | 7.828 / 8.327 / 16.799 | 2.301 / 3.023 / 5.723 | 2.202 / 3.023 / 143.706 | 2.508 / 2.862 / 3.202 |
| workspaceSymbols | 15.524 / 16.324 / 38.415 | 24.124 / 27.265 / 31.339 | 23.405 / 26.292 / 31.377 | 23.819 / 27.192 / 29.914 |

Full-graph local-baseline first post-idle outline median/max: 157.467/160.158 ms.

Full-graph candidate first post-idle outline median/max: 157.695/159.844 ms.

Full-graph glider first post-idle outline median/max: 4.796/8.923 ms.


## Selection and remaining proof obligations

Neither runtime candidate is accepted as a regression-free improvement. The
combined candidate gives the larger search gain but worsens paced full-graph
outline/definition tails. The simpler response-only control improves full-graph
search by 10.7% median / 11.7% p90 unpaced and 3.0% / 3.6% paced, yet paced
definition median/p90 regress 3.6%/9.7% and unpaced reference p90 regresses 18.0%.
Small-graph unfavorable tails are also retained in the tables. No unsupported
noise threshold is used to dismiss them. Lower allocation alone is not proof of
better latency for every operation.

Both candidate source trees remain recoverable in local commits `5d14a4a` and
`5c44c97`. The selected runtime
returns to d8232ec; the new profiling, differential, matched-core comparison and
response diagnostic workflows remain. Nothing here qualifies a release winner.

The definition regression also occurs with the original Roslyn search path, so
it is not isolated to the guarded search helper. The experiments do not establish
whether scheduling, CPU power state, code layout or another cause explains it.
The next useful measurement is an instrumented native-worker/core MCP run at the
same cadence, separating worker execution from IPC/response construction, with
scheduling observations. Framework-dependent worker profiles and the isolated
allocation diagnostic cannot resolve that attribution by themselves.

For recovery, returning a semantic response before completing the deadline-triggered
content sweep would violate the current contract. No such shortcut is accepted.
A bounded parallel open/read design remains a possible implementation experiment,
not a proved impossibility or a qualified fix: it must retain uncached validation
at each open, bounded descriptors/buffers and aggregate read budgets, sorted
failure precedence, cancellation and all-or-nothing publication. Staging recovery
across responses or adding idle work changes documented behavior and needs an
explicit contract decision plus total CPU/I/O and contention qualification.

No Linux/Windows run, syscall rerun, arbitrary-solution qualification or universal
win is claimed. All measurements here are M6 synthetic evidence. Strict default,
fresh target reads, external-input restrictions, watcher recovery and preview
hashes remain intact.


`FREEFLIGHT_GLIDER_CANDIDATE_CORE_REF` selects a pinned candidate core without
changing the checkout. It reuses the same Git-source freezing and native gates as
the local baseline. `FREEFLIGHT_GLIDER_PREPARE_ONLY=1` runs preparation and native
gates and emits `qualification-only.json` with zero timed processes; this is not
a benchmark result. The closing replay checks this ref path against the original
control source hashes.

`benchmark.trusted.qualification` reuses prepare/qualify/transaction from the full
workflow without timing. It is used for the restored runtime's closing fault and
security qualification; use a fresh `FREEFLIGHT_TRUSTED_BENCH_LABEL` and the same
SDK/fixture variables. No duplicate test implementation is introduced.

Closing qualification passed in `bin/.local/benchmarks/trusted/restored-runtime-final`: worker/security/mutation gates, all 16 incremental fault checks, metadata/read proofs and five failed-refresh state-preservation cases per variant. Baseline/candidate worker source hashes are identical to d8232ec. `bin/.local/glider-comparison/response-ref-replay-qualification` passed native worker/core gates with zero timed processes; its pinned core source hashes exactly match the measured response-only control.
