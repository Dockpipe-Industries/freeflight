# RC2 trusted-refresh optimization sprint

This is the local M6 follow-up to [the residual investigation](rc2-residual-refresh-investigation.md).
The named baselines are shipped `39c3cc83b04f21e352e7885c0589d39947b9efa4`
and local `80ea256263699b9efed0917cf0e10ac81f4d2c61`. Measurements here use
synthetic dependency-free projects and the pinned RC2 SDK on Darwin ARM64.
They are not a rerun of the operator's Linux/Biztraak/Glider measurements.

The unpaced and paced results differ materially. Read the paced qualification below
alongside the headline throughput-loop numbers: cadence changes expiry batching and
parallel metadata costs. This is not a universal fourfold latency improvement.

The selected runtime is the serial `3084d82` checkpoint. Four-worker admission was
rejected after the final paced comparison below; its faster unpaced results remain
recorded as experimental evidence, not as performance claims for the selected build.

## Iterations and retained evidence

Every label below lives under `bin/.local/benchmarks/trusted/`; provenance records
source and fixture hashes, SDK identity and driver hashes. Ordinary and diagnostic
processes are separate. Baseline/candidate processes never run concurrently.

| Receipt | Change / interpretation |
| --- | --- |
| `sprint-read-reuse` | `74b3bc6`: one request-local read buffer; avoid decoding when the freshly read SHA-256 equals the committed hash. Steady-state timings essentially flat; expiry allocation decreased, expiry timings mixed. |
| `sprint-lexical` | `8d9007d`: retain sorted canonical graph identity and lexical parent strings until reopen. All measured median/p90 pairs improved in this run. No filesystem authority is retained. |
| `sprint-fresh-info` | Preparation failed on an ambiguous diagnostic anchor; no timing used. |
| `sprint-fresh-info-v2` | `3084d82`: retain FileInfo objects, explicitly Refresh before every use of their metadata. All measured median/p90 pairs improved in this run. |
| `sprint-padded-control` | Identical `3084d82` sources, 4 KiB files, three sessions each, 2,000 rounds. Near-parity medians/p90; small-graph reference p90 ratio 1.048 is retained as noise evidence. |
| `sprint-parallel-metadata` | Preliminary bounded four-way metadata admission, 4 KiB files, 2,000 rounds. Full-graph median ratios 0.478–0.565, p90 0.492–0.588 against `3084d82`. Not the final candidate: error timing needed refinement. |
| `sprint-parallel-crossover` | Qualification stopped on unchanged baseline: the new resource-order test used a limit too low for project loading. No timing used. |
| `sprint-parallel-eight` | Eight versus four workers with 14 reference sites and C5 search. Full outline median/p90 ratios 0.872/0.932, but diagnostic mean CPU rose from 12.006 to 18.592 ms per outline and small-graph tails regressed. Rejected as the default; retained as a latency/CPU tradeoff. |
| `sprint-parallel-two` | Four versus two workers at 256/433/5845 files. Two reduced diagnostic mean process CPU but worsened every measured p90 pair (full outline ratio 1.411); rejected. Source snapshot and patch retained. |
| `sprint-parallel-crossover-v2` | Corrected serial error ordering passed qualification/transaction guards and all six graph sizes. Parallelism regressed 16-file median/p90 on every operation; 128-file outline p90 ratio 1.019, definition 1.001. All median/p90 pairs from 433 files upward improved. This motivates a serial small-graph path, with the 256-file boundary tested separately. |

Old rejected leaf-only/ancestor-only experiments and their unfavorable p90 evidence
remain in `bin/.local/perf*`. None is silently reinstated by this work.

## Source and security reasoning

`SourceEngine.Invoke` serializes engine work through the protocol gate and runs
Refresh before semantic operations. Trusted membership is fixed until reopen;
therefore immutable canonical ordering/parent strings can be reused. The semantic
maps and Roslyn solution remain staged until all checks succeed. FileInfo identity
can be reused only because `Refresh()` is called on every request before metadata
is consumed. The [documented API contract](https://learn.microsoft.com/en-us/dotnet/api/system.io.filesysteminfo.refresh?view=net-10.0)
explicitly distinguishes updating that snapshot from reading cached attributes.

The parallel experiment partitions metadata admission into at most four contiguous
ranges. Each partition owns a request-local ancestor set and distinct FileInfo
objects. Snapshot/external-input maps are read-only during the joined prepass.
There are no parallel content reads or Roslyn mutations. Cancellation is checked
per file and after joining. A metadata error is retained with its sorted index and
reported when the serial loop reaches it; earlier resource/read errors retain
precedence. No failed prepass grants permission to consume unrefreshed metadata.
The first-error index stops the serial loop before any unvalidated suffix.

Every content read still performs uncached path validation immediately before
open, including external inputs on the parallel path. Fresh target reads, external
input read-only restrictions, bounded reads and aggregate resource checks, watcher
generations, five-second expiry, and edit-preview hashes remain required. Parent
strings and FileInfo objects are bounded by the loaded graph and cleared on reopen.
This does not create an atomic filesystem sandbox; the existing concurrent-hostile
filesystem race limitation remains. No watcher-only admission is introduced.

## Diagnostic observations and limits

At `3084d82`, the padded full-graph control's outline expiry Refresh was about
183–186 ms: opening streams accounted for about 76 ms, uncached path checks about
38 ms, read I/O about 18 ms, hash append about 12 ms and hash construction about
1.8 ms. These stages overlap/nest; do not add them as independent percentages.
Hash-context reuse was not implemented because measured construction was a small
part of expiry. Open-handle caching would undermine replacement freshness and is
not proposed. Parallel content reads would require additional proofs for bounds,
cancellation, resource/error ordering and transactional failure, so remain deferred.

The preliminary parallel diagnostic full-graph outline Refresh median was 3.364 ms
versus 7.037 ms serial, with admission wall time 2.723 ms. Aggregate metadata-refresh
time rose from 4.547 to 7.368 ms: reduced latency trades for concurrent work.
Managed attribute-call counts rose from 5,910 to 5,919 due to partition-local
ancestor checks; these are not OS syscall counts. Both read the target's 4,096 bytes
and reused 5,844 snapshots. Approximate process allocation deltas were 270,504 versus 89,608
bytes in those instrumented builds; instrumentation and concurrent runtime activity
are included. Median GC pause was zero, which does not exclude individual pauses.
All raw tails and runtime event observations remain in the receipts.

The final boundary run additionally passed five failed-refresh guards per variant,
including a deterministic ancestor swap after admission and before read. The swap
was rejected with zero additional source bytes read, and recovery succeeded. This
seam exists only in generated qualification binaries, never production or timing
builds. Final qualification and release status will be recorded after the sprint. These
intermediate observations alone do not qualify Linux/Windows packages or establish
a Glider performance win.

## Remaining performance ceiling

Fresh validation still visits every graph member on every semantic request. The
parallel prepass reduces wall time, not asymptotic work; extra partition-local
ancestor checks can slightly increase managed call counts. Periodic expiry still
reads and hashes all required bytes. Further removal of that work would need a
new freshness/security proof or an explicit contract change; watcher-only authority
and unchecked persistent path caching are not part of this change.

Worker reply timings include JSON serialization/stdout; the optional MCP comparison
measures the complete endpoint round trip. It does not isolate each C++ routing/IPC
stage. CLR JIT/GC events and process CPU/thread-pool observations are retained, but
do not establish exact PGO-tier or OS scheduling causality. The historical 77–79 ms
session and operator Linux tails cannot be retrospectively attributed from these
new synthetic runs. Kernel syscall tracing was not repeated on M6; managed call
counts must not be presented as kernel syscall counts.

## Final shipped-baseline comparison

`sprint-final-shipped`: three fresh sessions per variant/graph, 1,000 measured
rounds per session, five seconds minimum warmup, 4 KiB source files, 14 reference
call sites, and C5 search (956 full-graph type results). All 48,000 ordinary and
16,000 diagnostic measured semantic responses passed. Loading, warmup, diagnostic
and idle-expiry samples are separate. Candidate worker source is `bdcff71`.

Full 5,845-file/26-project graph, ordinary milliseconds:

| Operation | Baseline medians | Candidate medians | Baseline p90 | Candidate p90 | Baseline max | Candidate max |
| --- | --- | --- | --- | --- | --- | --- |
| symbols | 12.873, 12.649, 12.738 | 3.263, 3.278, 3.293 | 15.864, 14.109, 14.312 | 3.754, 3.664, 3.574 | 125.261 | 25.877 |
| definition | 12.114, 11.957, 11.942 | 3.052, 3.037, 3.053 | 14.683, 12.900, 12.907 | 3.342, 3.284, 3.274 | 84.359 | 18.931 |
| references | 12.456, 12.268, 12.217 | 3.437, 3.427, 3.433 | 15.273, 13.382, 13.234 | 3.869, 3.693, 3.750 | 79.499 | 13.424 |
| workspaceSymbols | 15.485, 15.261, 15.390 | 6.044, 5.944, 5.928 | 21.208, 17.981, 18.074 | 6.916, 6.671, 6.599 | 64.364 | 26.208 |

Every median/p90 pair improved at 433 and 5845 files in this run. This does not
erase the smaller-graph boundary regression or establish statistical universality.

Separate full-graph diagnostic outline medians: Refresh 13.135 → 3.508 ms;
sort/map preparation 1.069 → effectively zero; apply/rebuild 0.557 → 0.0002 ms;
semantic work 0.022 → 0.018 ms. Candidate parallel admission wall time was 2.846 ms.
Precise managed allocation delta was 11,284,140 → 85,072 bytes (instrumented
process-wide counts, excluding native allocation). Mean diagnostic process CPU
was 15.634 → 12.180 ms per outline. Managed attribute calls were 5,910 → 5,919:
the gain does not come from omitting leaf validation.

Broad-search semantic medians were 2.060 → 1.845 ms, separate from Refresh
12.510 → 3.282 ms and reply serialization. Parallel stage totals are aggregate
worker work; they cannot be added to elapsed prepass time.

The five slowest diagnostic baseline outlines read 1,371–1,380 documents, with
1,370–1,379 expired snapshots and approximately 1.49–1.73 ms GC pause. Their
elapsed times were 53.1–55.2 ms, with roughly 36.3–36.9 ms in reads/hash/decode.
Candidate top outline tails read 620–745 documents and took 18.0–21.7 ms, with
0–0.923 ms GC pause. These observations support expiry as a major measured tail
cost, not a claim that GC or JIT explains every outlier. The faster unpaced loop
changes expiry batching; a separately paced repeat is retained for that reason.

After 5.1 seconds idle, baseline full-graph outlines were 221.277, 245.466 and
218.338 ms; candidate values were 178.306, 174.397 and 195.093 ms. These controlled
whole-graph revalidation samples remain much slower than steady state.

## Final local-baseline comparison

`sprint-final-local` compares `80ea256` with the same candidate/runtime and broader
fixture settings, reversing the first pair. All 48,000 ordinary and 16,000
diagnostic measured semantic responses passed. All median/p90 pairs improved at
433 and 5845 files in this run. Full-graph ordinary milliseconds:

| Operation | Baseline medians | Candidate medians | Baseline p90 | Candidate p90 | Baseline max | Candidate max |
| --- | --- | --- | --- | --- | --- | --- |
| symbols | 8.343, 8.412, 8.392 | 3.258, 3.288, 3.281 | 8.948, 9.562, 8.908 | 3.645, 3.813, 3.625 | 63.376 | 27.894 |
| definition | 7.697, 7.719, 7.732 | 3.042, 3.048, 3.045 | 8.197, 8.215, 8.122 | 3.347, 3.281, 3.267 | 40.467 | 18.503 |
| references | 8.059, 8.061, 8.037 | 3.416, 3.433, 3.427 | 8.481, 8.452, 8.418 | 3.831, 3.833, 3.778 | 37.249 | 15.443 |
| workspaceSymbols | 10.852, 10.990, 10.975 | 5.854, 6.071, 5.948 | 11.634, 11.848, 11.604 | 6.547, 6.824, 6.724 | 41.946 | 32.061 |

## End-to-end MCP comparison

`sprint-final-shipped/mcp` uses the freshly built local C++ core and the exact
frozen ordinary worker binaries. Three fresh sessions per variant/graph, 500
measured rounds, five seconds minimum warmup, same 4 KiB/14-reference/C5 fixture.
All 24,000 measured semantic responses passed, including loaded graph counts.
The first summary failed because a loop variable shadowed Python round(); raw
measurements were complete. The workflow recovered only summary generation,
recording original provenance, raw-sample and recovery-driver hashes in
`summary-recovery.json`. The original failure log remains retained.

Full-graph ordinary endpoint milliseconds:

| Operation | Baseline medians | Candidate medians | Baseline p90 | Candidate p90 | Baseline max | Candidate max |
| --- | --- | --- | --- | --- | --- | --- |
| symbols | 13.307, 13.318, 13.303 | 3.526, 3.540, 3.562 | 14.333, 14.316, 14.267 | 3.752, 3.762, 3.797 | 75.813 | 22.570 |
| definition | 12.237, 12.214, 12.191 | 3.186, 3.182, 3.181 | 13.100, 13.083, 13.001 | 3.263, 3.326, 3.371 | 90.982 | 13.449 |
| references | 12.564, 12.568, 12.572 | 3.605, 3.594, 3.608 | 13.584, 13.514, 13.557 | 3.817, 3.823, 4.051 | 52.065 | 17.128 |
| workspaceSymbols | 20.881, 20.693, 20.571 | 11.223, 11.099, 11.170 | 22.290, 22.217, 22.185 | 12.072, 11.619, 11.877 | 70.638 | 25.358 |

These endpoint results include client parsing, core routing/IPC and worker reply
serialization. They remain SDK-hosted synthetic measurements, not a packaged
Linux/Biztraak or Glider comparison. Raw loading/discovery and post-idle samples
are retained separately in samples.json.

## Serial fallback and observability

`sprint-single-processor` set `DOTNET_PROCESSOR_COUNT=1` only for child workflow
processes. Diagnostic receipts report processorCount 1. Both native suites, all
five failed-refresh proofs per variant, and 1,600 ordinary/800 diagnostic measured
semantic responses passed. This exercises the serial branch; it is not a claim
about throughput on a physical single-core machine or an OS CPU quota.

The core still captures capabilities before opening the worker and returns that
cached object (`src/server.cpp`, engine creation). Its refreshStats are therefore
not live trusted-refresh telemetry. The direct workflow queries the actual worker,
whose Refresh updates read/reuse counters and whose watcher updates generations.
No cosmetic counter change was made to the core. Broad MCP responses contain both
text and structured JSON (`src/main.cpp`); that compatibility path is a candidate
for separate profiling, not an optimization included here. Worker reply medians
were about 0.005 ms for outlines and 0.305 ms for the 956-result search; these do not
isolate core parsing/serialization or client decoding costs.

## Paced qualification and retained regressions

`sprint-paced` repeats shipped `39c3cc83` versus the four-worker candidate with
three fresh sessions per graph/variant, ten seconds warmup, 100 measured rounds,
and a minimum 100 ms interval per four-operation round. The fixture remains
4 KiB sources, 14 references and C5 search. All semantic, native and five
transaction guards per variant passed. Ordinary full-graph milliseconds:

| Operation | Baseline medians | Candidate medians | Baseline p90 | Candidate p90 | Baseline max | Candidate max |
| --- | --- | --- | --- | --- | --- | --- |
| symbols | 14.810, 15.084, 14.926 | 9.714, 9.662, 9.467 | 15.916, 16.113, 15.960 | 10.352, 10.269, 10.073 | 173.13 | 100.60 |
| definition | 11.971, 12.080, 11.898 | 6.494, 6.578, 6.707 | 12.757, 12.598, 12.524 | 7.155, 7.394, 7.475 | 51.19 | 98.59 |
| references | 11.511, 11.620, 11.446 | 7.791, 7.652, 7.641 | 12.347, 12.758, 12.309 | 8.224, 8.209, 8.198 | 40.79 | 95.21 |
| workspaceSymbols | 14.303, 14.484, 14.303 | 10.508, 10.378, 10.520 | 15.913, 15.613, 16.608 | 11.670, 11.229, 11.315 | 152.54 | 58.16 |

All median/p90 pairs improved at both graph sizes against shipped baseline, but
full-graph definition/reference maxima regressed. Outline medians around 9.5–9.7 ms
are materially slower than the roughly 3.3 ms unpaced candidate loop. Separate
diagnostics observed outline Refresh median 15.311 → 7.975 ms and mean process CPU
16.087 → 32.255 ms. Candidate parallel admission wall time was 6.580 ms; aggregate
metadata work was 18.468 ms. These are instrumented costs, not ordinary timings.
Average read counts also differed (3.44 versus 94.04), so this does not isolate a
single scheduler, JIT or expiry cause. No host scheduling trace was captured.

This motivated a final paced serial-versus-four comparison before runtime selection.
The earlier faster unpaced result alone is insufficient to choose concurrency.

The corrected normal MCP workflow also completed under the separate
`sprint-final-shipped/mcp-fixed` label: three sessions per variant/graph, 200
rounds, all 9,600 measured exact responses passed. Full-graph median ratios were
0.267 outline, 0.262 definition, 0.289 references and 0.544 search; p90 ratios
0.261, 0.254, 0.299 and 0.549. This validates the normal summary path after the
retained first-run summary failure; the two runs are not pooled.

## Final selection: retain serial metadata admission

`sprint-paced-serial` compares serial `3084d82` against four-worker `60e5114`, with
two fresh sessions per graph/variant, ten seconds warmup, 100 rounds, minimum
100 ms round interval and the same broad padded fixture. All 3,200 ordinary and
1,600 diagnostic measured responses, native suites and five transaction guards
per variant passed. Full-graph ordinary milliseconds (serial → four workers):

| Operation | Serial medians | Four-worker medians | Serial p90 | Four-worker p90 |
| --- | --- | --- | --- | --- |
| symbols | 10.437, 10.235 | 9.761, 9.563 | 11.454, 11.226 | 24.659, 10.315 |
| definition | 8.103, 8.060 | 6.522, 6.546 | 8.631, 8.380 | 7.315, 7.179 |
| references | 7.657, 7.590 | 7.464, 7.566 | 8.267, 8.061 | 8.270, 8.102 |
| workspaceSymbols | 9.861, 9.899 | 10.407, 10.471 | 10.536, 10.640 | 11.447, 11.674 |

Four workers improved small-graph latency, full-graph definition latency and the
unpaced loop substantially. However, full-graph search regressed in both paced
sessions; outline p90 regressed in one. Diagnostic mean outline CPU was
13.982 → 31.578 ms, with different expiry batching (mean reads 50.35 → 114.1).
Four-worker outline maxima were lower (67.557/88.216 versus 98.913/99.788 ms),
so the evidence is mixed rather than uniformly negative. All raw maxima remain.

The final runtime restores Program.cs exactly to `3084d82`, retaining serial
fresh metadata validation, immutable lexical reuse, staged delta commits and
fresh-read hash/decode reuse. Parallel admission is deferred: its cadence-dependent
CPU/search/tail tradeoff is not a sufficiently broad improvement for this release.
The four-worker commit, source snapshots and rejected patch remain local. Expanded
security tests and all benchmark/profiling infrastructure remain in the delivered tree.
Final selected-runtime qualification against shipped baseline follows separately.


## Reproduction

With the repository-pinned SDK, Python/PyYAML and DockPipe on PATH, repeat the
selected-runtime paced comparison using a fresh immutable label:

```sh
FREEFLIGHT_TRUSTED_BENCH_LABEL=winner-repeat \
FREEFLIGHT_TRUSTED_BENCH_BASELINE=39c3cc83b04f21e352e7885c0589d39947b9efa4 \
FREEFLIGHT_TRUSTED_BENCH_CANDIDATE=WORKTREE \
FREEFLIGHT_TRUSTED_BENCH_PADDING=4096 \
FREEFLIGHT_TRUSTED_BENCH_CALLERS=14 \
FREEFLIGHT_TRUSTED_BENCH_QUERY=C5 \
FREEFLIGHT_TRUSTED_BENCH_FIRST=candidate \
FREEFLIGHT_TRUSTED_BENCH_SESSIONS=3 \
FREEFLIGHT_TRUSTED_BENCH_WARMUP=10 \
FREEFLIGHT_TRUSTED_BENCH_INTERVAL=0.1 \
FREEFLIGHT_TRUSTED_BENCH_ROUNDS=100 \
dockpipe --workflow benchmark.trusted

FREEFLIGHT_TRUSTED_BENCH_LABEL=winner-repeat \
FREEFLIGHT_TRUSTED_MCP_LABEL=mcp \
dockpipe --workflow benchmark.trusted.mcp
```

Build the unchanged core first with `dockpipe --workflow core.build` for the MCP
pass. See [workflow usage](trusted-performance-workflow.md) for controls, exact
checks, provenance, separate profiling and summary recovery. Set interval to zero
under a new label for an unpaced repeat; do not pool cadences. Kernel syscall
counts are not captured by these M6 workflows. The supplied Linux syscall results
remain external evidence, not a new local before/after trace.

## Selected serial runtime: final shipped-baseline qualification

`sprint-winner-shipped` uses three fresh sessions per variant/graph, ten seconds
warmup, 100 measured rounds, minimum 100 ms round interval, 4 KiB sources,
14 references and C5 search. The candidate Program.cs matches `3084d82` exactly.
All 4,800 ordinary and 1,600 diagnostic measured responses passed, along with
both native suites and five transaction guards per variant. Full-graph ordinary ms:

| Operation | Baseline medians | Selected medians | Baseline p90 | Selected p90 | Baseline max | Selected max |
| --- | --- | --- | --- | --- | --- | --- |
| symbols | 14.983, 15.193, 15.105 | 10.244, 10.393, 10.508 | 15.947, 16.224, 16.090 | 19.393, 11.006, 11.506 | 144.340 | 100.727 |
| definition | 12.057, 12.182, 12.217 | 8.041, 8.112, 8.104 | 12.687, 12.973, 12.872 | 8.442, 8.413, 8.553 | 26.606 | 20.933 |
| references | 11.637, 11.922, 11.773 | 7.616, 7.680, 7.609 | 12.317, 12.829, 12.610 | 7.942, 8.066, 7.991 | 71.790 | 25.994 |
| workspaceSymbols | 14.668, 14.942, 14.459 | 9.961, 9.837, 9.688 | 15.918, 16.550, 16.556 | 10.592, 10.463, 10.338 | 55.646 | 14.795 |

All small-graph median/p90 pairs improved. Full-graph per-session medians improved
for every operation; one selected outline session regressed p90, retained above.
Across-session median ratios were 0.688 outline, 0.665 definition, 0.647 references
and 0.671 search. These descriptive ratios do not establish statistical significance.

Separate full-graph outline diagnostics: Refresh 15.095 → 10.456 ms; collection
preparation 1.303 → 0.0002 ms; apply/rebuild 0.591 → 0.0006 ms; semantic work
0.025 → 0.022 ms. Selected metadata Refresh accounted for 7.156 ms within
snapshot-path validation 8.993 ms. These stages overlap. Managed allocation median
was 11,413,568 → 264,032 bytes, excluding native allocation and including diagnostic
activity. Mean observed CPU was 20.039 → 14.267 ms. Managed attribute checks stayed
at 5,910 per instrumented unchanged outline; this is not a kernel syscall measurement.
GC pause median was 0.910 → 0 ms; individual pauses and expiry tails remain.

The slowest ordinary outline samples read hundreds or thousands of documents:
the selected sessions' top samples read 2,142, 3,828 and 2,220 documents, rather
than only the target. After 5.1 seconds idle all 5,845 files were reread; baseline
outlines took 229.29/228.29/227.13 ms and selected runtime 183.61/186.65/184.07 ms.
This correlates tails with bulk revalidation without claiming that every tail has
one cause or that ordinary requests always reread the solution.

## Selected serial runtime: final MCP qualification

`sprint-winner-shipped/mcp` ran the frozen selected worker and shipped baseline
through the same freshly built C++ core: three fresh sessions per variant/graph,
ten seconds warmup, 100 measured rounds, minimum 100 ms round interval. All
4,800 measured responses and loaded graph counts passed. Full-graph endpoint ms:

| Operation | Baseline medians | Selected medians | Baseline p90 | Selected p90 | Baseline max | Selected max |
| --- | --- | --- | --- | --- | --- | --- |
| symbols | 15.325, 15.265, 15.249 | 10.489, 10.292, 10.392 | 16.285, 16.011, 16.179 | 11.104, 10.797, 11.014 | 158.165 | 105.738 |
| definition | 12.233, 12.184, 12.183 | 7.949, 7.848, 7.912 | 12.899, 12.788, 13.050 | 8.250, 8.087, 8.369 | 46.069 | 93.933 |
| references | 12.153, 12.017, 12.031 | 7.489, 7.468, 7.509 | 13.067, 12.899, 14.373 | 7.752, 7.704, 7.865 | 30.586 | 53.787 |
| workspaceSymbols | 19.827, 19.721, 20.213 | 14.510, 14.497, 14.353 | 21.039, 21.274, 21.590 | 15.129, 15.114, 14.930 | 168.899 | 115.107 |

Endpoint definition/reference maxima regressed (93.933/53.787 ms versus
46.069/30.586 ms baseline), despite lower medians/p90. These outliers remain
retained. All median/p90 pairs improved in this endpoint repeat. It does not erase the
worker-only outline regression or qualify other platforms. The selected source
continues to require fresh validation and expiry; the core's cached pre-open
refreshStats remain unsuitable as live worker telemetry. Hosted self-contained
platform/security qualification is required before staging promotion.
