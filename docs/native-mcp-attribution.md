# Native MCP attribution controls

This local investigation starts at `fb19231`, with production runtime equal to
`d8232ec`. It replays the rejected response-only core `5c44c97`; it does not install
that candidate. The earlier combined candidate `5d14a4a` and all unfavorable
receipts remain recoverable. No runtime source, active MCP configuration or
published branch changes are part of this pass.

Outcome: no accepted runtime winner. Ordinary controls completed successfully;
post-run log review found EOF shutdown crashes in both diagnostic qualification
runs that their pinned test script failed to reject. Diagnostic stage observations
are retained, but those qualification gates are **not clean**. The authoritative
additive audit is `native-attribution-v1/qualification-review.json`; original
receipts are preserved rather than rewritten to hide the test-harness gap.

## Reproduce

Use `dockpipe --workflow benchmark.trusted.attribution` with a fresh
`FREEFLIGHT_ATTRIBUTION_LABEL`. Put the pinned .NET 11 SDK and the existing Python
benchmark environment on PATH. Set `FREEFLIGHT_GLIDER_CMAKE` to the installed
CMake executable and `FREEFLIGHT_GLIDER_DOTNET_ROOT` to the .NET 10 fixture SDK.
The existing trusted `incremental-v3` worker receipt and Glider-comparison
`incremental-v3` baseline receipt must be present. The driver validates their
source hashes; it does not reinterpret Linux-local receipts as local evidence.
See [the original workflow guide](trusted-performance-workflow.md) for fixture
and receipt preparation, and [incremental validation](incremental-validation.md)
for the prototype's opt-in freshness contract.

Exact M6 invocation used for this pass (choose a new label for a repeat):

```sh
PATH="$PWD/bin/.local/perf-venv/bin:/Users/jamie/Documents/Codex/2026-10-20/task/freeflight-dependabot/bin/.local/dotnet11:$PATH" \
DOTNET_CLI_USE_MSBUILD_SERVER=0 \
FREEFLIGHT_GLIDER_CMAKE=/Users/jamie/Documents/Codex/2026-10-19/task/toolchains/cmake-3.31.8-macos-universal/CMake.app/Contents/bin/cmake \
FREEFLIGHT_GLIDER_DOTNET_ROOT=/Users/jamie/Documents/Codex/2026-10-19/task/toolchains/dotnet \
FREEFLIGHT_ATTRIBUTION_LABEL=native-attribution-v1 \
dockpipe --workflow benchmark.trusted.attribution
```

Paths are local toolchain locations, not portable prerequisites. On another
machine substitute the installed pinned toolchain paths and first produce the
required qualified receipts. No active MCP installation is changed.

The workflow runs six conditions serially: identical-binary A/A and response-only
A/B with fixed operation order, then the same two controls with rotating order,
then two separate generated-source diagnostic conditions. Defaults are four
fresh pairs per ordinary condition, two per diagnostic condition, 10 seconds of
warm-up and 80 measured rounds, paced at 100 ms per round. Every round retains
outline, definition, references and broad search with the existing exact oracle.
Rotation changes order, not semantic scope. There are no simultaneous timing
processes. The 5,845-file/26-project synthetic fixture is not Biztraak.

Both labels use the exact same newly published worker executable. A/A also uses
the exact same core executable; effective commands and source hashes are recorded.
The shared worker removes a compilation-time binary difference from the core
comparison. These focused conditions compare local FreeFlight variants, not
Glider or a fresh shipped-build run. Prior head-to-head results are retained in
[the comparison report](glider-head-to-head.md).

Set `FREEFLIGHT_ATTRIBUTION_MODES`, `FREEFLIGHT_ATTRIBUTION_SESSIONS`,
`FREEFLIGHT_ATTRIBUTION_PROFILE_SESSIONS` and `FREEFLIGHT_ATTRIBUTION_ROUNDS` only
when deliberately changing the experiment. Receipts record the settings and driver
hashes. Failed attempts are retained; reuse of an output label fails closed.

## Instrumentation boundaries

`native_profile.py` instruments generated source copies using exact source
anchors, then runs the existing native core and worker qualification. Production
sources are untouched. The current native diagnostic uses POSIX process counters
and was qualified on macOS; Windows diagnostics need a separate implementation.

Core stages cover queue admission, server call, worker request serialization,
pipe write/receive, worker response parsing, MCP response construction and
delivery, envelope construction, JSON serialization and output write. Thread CPU
and process CPU/context-switch deltas accompany wall times. Worker stages reuse
the existing refresh/read/hash/allocation/GC/JIT instrumentation, adding task queue,
semaphore admission and response serialization/write. Client diagnostics record
JSON encoding/parsing, stdout arrival, reader-queue delay and Python GC pauses.
Request IDs join all three layers; malformed, missing or duplicate joins fail.

Stages are nested, not additive percentages. Process-level switch counts do not
identify which thread was descheduled, and wall minus CPU is not a causal proof
of scheduler interference. A profile is not an ordinary production benchmark.
The worker profiler itself performs allocation/process/event observations before
invocation and after its reply. Those prelude and previous-postlude durations are
explicitly retained; the smoke run measured approximately 0.3–0.4 ms each, material
for sub-millisecond operations. Diagnostic logs also add post-response work.

`native_summary.py` preserves the largest samples with complete joined records.
Full sweeps are classified from live worker read counts, not latency. Ordinary
summaries retain every sample, including recovery and maxima. The paired
postprocessor reports each pair and its ratio range rather than declaring a win
from pooled medians. Rotating ordinal does not establish an idle gap: an earlier
round can overrun its pacing interval.

## Recovery constraints

`Program.cs:Refresh` starts its five-second clock before recovery, admits and reads
files in sorted order, validates each path again without cached authority directly
before opening it, charges actual chunks against file/workspace byte limits, stages
hashes/text/snapshots, checks cancellation and invalidation generation, then commits.
The current recovery is a complete content sweep even when stat values match.

Parallel metadata admission already exists. Parallel *content* reads are a distinct
change: naïve completion-order publication would change error precedence and the
`observed` byte total returned by resource failures. Unbounded tasks could retain
many open files/buffers and continue work after cancellation. No such candidate is
implemented or benchmarked in this pass.

A concrete accounting counterexample is two sorted 12 KiB files, each read in
8+4 KiB chunks, with a 20 KiB aggregate limit and a 16 KiB per-file limit. Serial
accounting fails on file B at 24 KiB. A shared concurrent counter with completion
order B8, A8, B4, A4 instead fails on A at 24 KiB. Both reject the workspace, but
the observable error path differs. Similarly, throwing a later path-admission
error before consuming an earlier file's read failure changes precedence. These
are source-derived counterexamples to naïve parallelization, not measured
parallel-runtime results or a contradiction for every bounded design.

A bounded design would need ordered result/error consumption, bounded descriptor
and buffer reservations, explicit handling of growing files and the existing
overshoot chunk, cancellation/draining of outstanding reads before return, and
generation/dirty-version acknowledgment only after successful publication. It
must preserve external-input open restrictions and uncached pre-open checks, and
fall back safely when aggregate byte reservations cannot cover the next batch.
Tests must compare the first error, path, limit and actual-byte `observed` value
against serial behavior, not only compare eventual success. The current contract
does not promise zero speculative I/O after a different file's failure; this report
does not invent that restriction or claim parallelism is impossible. Its proof and
resource accounting remain additional work before implementation.

Returning before the sweep, extending its deadline, or silently treating watcher
silence as freshness would change the approved contract. Those are not equivalent
optimizations. Background maintenance would also require measured total CPU/I/O,
query contention and the same failure/deadline guarantees.

## Qualification review and exact remaining gates

All 40 timed processes completed the semantic oracle: 10,240 ordinary steady
checks plus 128 ordinary idle checks, and 2,560 diagnostic steady checks plus 32
diagnostic idle checks. The diagnostic join retained 5,524 records including
warm-up. Native protocol/process tests and worker semantic/boundary assertions
completed. However, final log review found `ObjectDisposedException` in the
diagnostic trusted worker's EOF cleanup in both fixed and rotating conditions.
No such message appears in the four ordinary qualification logs or timed MCP
server logs. This is an observed diagnostic failure, not proof ordinary shutdown
cannot race.

Source cause: `Program.Main` enumerates `active.Values` and calls `Cancel()` at
EOF while a job's `finally` removes and disposes its cancellation source. A value
captured before removal can be disposed before cancellation. Generated profiling
extends the post-response job lifetime; the race also exists structurally in
unchanged source. `test_trusted.py` waits for worker exit but does not assert its
return code, so its Python process misleadingly exits successfully. The benchmark
now rejects an `Unhandled exception.` in either worker qualification log. The
new check was exercised against all six retained conditions: four ordinary pass,
both diagnostic conditions fail. This is a fail-closed qualification correction,
not a runtime fix or a silently suppressed exception.

Remaining technical gates are deterministic shutdown/disposal-race coverage and
a scoped correction, stronger causal scheduling evidence for ordinary position
effects, and ordered resource/error/cancellation proof before parallel recovery.
There was no permission denial, pending remote operation or connection blocker.
No additional runtime patch, parallel reader, publication or configuration change
was attempted. The prior d8232ec security/fault receipts remain preserved; this
pass does not claim to have rerun their generated 16-case fault suite.

## Ordinary matched results

All 32 ordinary fresh processes passed: 10,240 measured steady-state checks and 128 post-idle checks. Four fresh pairs per condition; same full synthetic graph, 100 ms round cadence. Below, median and p90 are medians of the four per-session statistics; maximum is the largest sample across those sessions. Units are milliseconds. Every recovery/outlier remains included.

| Order | Operation | Baseline median | Candidate median | Baseline p90 | Candidate p90 | Baseline max | Candidate max |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| fixed | symbols | 1.530 | 1.537 | 1.752 | 1.749 | 144.334 | 148.420 |
| fixed | definition | 0.787 | 0.801 | 0.973 | 1.023 | 1.554 | 2.463 |
| fixed | references | 2.250 | 2.264 | 2.858 | 3.005 | 4.608 | 141.910 |
| fixed | workspaceSymbols | 24.645 | 23.459 | 26.982 | 26.661 | 30.504 | 31.503 |
| rotating | symbols | 0.434 | 0.488 | 1.542 | 1.569 | 146.690 | 149.774 |
| rotating | definition | 0.397 | 0.400 | 1.587 | 1.595 | 160.362 | 141.627 |
| rotating | references | 2.265 | 2.208 | 3.337 | 3.358 | 5.556 | 5.456 |
| rotating | workspaceSymbols | 25.756 | 25.261 | 29.399 | 28.496 | 153.530 | 33.617 |

The paired receipt preserves every session and candidate/baseline ratio. Fixed-order search median improved in all four pairs (ratios 0.924–0.974); rotating search also improved in all four (0.970–0.994). This is a modest repeatable search benefit in this workload, not a general acceptance result. Rotating outline median worsened in all four pairs (1.042–1.143). Fixed reference p90 worsened in three of four pairs (0.966–1.102 overall). Neither behavior is hidden by the favorable search cells.

Identical-binary controls showed fixed-order definition-p90 ratios of 0.915–1.073 and reference-p90 ratios of 0.853–1.033. Rotating definition-median ratios ranged 0.727–1.222 despite identical executables. These are descriptive repeat ranges, not confidence bounds or permission to dismiss a candidate regression. A/A and A/B conditions execute sequentially rather than randomly interleaving all conditions, so longer-term host drift remains a limitation.

Position is a major observed factor. In rotating A/A, median outline latency was approximately 1.5 ms first in a round versus 0.4–0.45 ms later. Definition was approximately 1.6 ms first, 0.79 ms second, and 0.30 ms later. A combined distribution can put its median between distinct timing groups; per-position results are retained. This does not prove a specific CPU-frequency, cache, scheduler or GC mechanism.

The response-only candidate remains unaccepted. This focused paced full-graph pass does not erase the earlier unpaced or small-graph evidence. No additional runtime optimization was layered onto it.

Ordinary post-idle outline medians are 158.127/157.473 ms for fixed order and
158.442/157.500 ms for rotating order (baseline/candidate). All individual values
are retained; the A/B range is 156.159–160.887 ms. Load medians are
3,026.7/3,017.4 ms fixed and 3,061.7/2,902.1 ms rotating, separate from queries.
Whole-session child CPU medians are 11.722/11.491 seconds fixed and 11.968/11.454
seconds rotating. These CPU totals include startup, load, warm-up and idle recovery
and exclude the Python driver; they are not steady-query CPU measurements.

## Source-attributed diagnostic findings

The fixed-order diagnostic has two fresh sessions per variant. Values below are
medians of session medians in milliseconds, not ordinary endpoint latency.

| Broad-search stage | d8232ec | Response-only core | Source |
| --- | ---: | ---: | --- |
| Worker declaration search | 8.359 | 8.972 | `workers/roslyn/SemanticQueries.cs`, `WorkspaceSymbols` |
| Worker reply serialization | 0.549 | 0.561 | `workers/roslyn/Program.cs`, reply writer |
| Worker reply pipe write | 0.328 | 0.328 | same reply writer |
| Core worker-response parse | 4.428 | 4.486 | `src/process.cpp`, `Process::request` |
| Core response construction | 1.327 | 0.961 | `src/main.cpp`, semantic result envelope |
| Core delivery, including serialization/write | 3.475 | 2.398 | `src/main.cpp`, result/send path |
| MCP JSON serialization, nested in delivery | 1.680 | 1.695 | same send path |
| MCP pipe write, nested in delivery | 0.293 | 0.300 | same send path |
| Client JSON parse | 2.108 | 2.143 | generated diagnostic MCP client |

Both replies contain 592,218 bytes. Core worker-response parsing also consumes
approximately 4.43/4.48 ms of thread CPU; this is actual parsing work, not just a
blocked pipe. Core request pipe writes are approximately 0.006 ms. Worker-receive
wall time includes worker execution and must not be labeled pure transport cost.
Core total thread CPU falls from 10.866 to 9.097 ms, while unchanged worker CPU
increases from 10.406 to 11.099 ms in these sessions. The candidate removes core
work, but the endpoint gain does not equal an isolated construction microbenchmark.

Definition has a different cost profile: core parsing is approximately 0.010 ms,
construction 0.007/0.006 ms, and delivery 0.022/0.019 ms. Its diagnostic worker
invocation is 0.395/0.400 ms, while profiler prelude alone is 0.317/0.359 ms.
Median core queue wait is approximately 0.011 ms, worker task queue 0.009 ms and
worker gate below 0.001 ms. These observations do not support a persistent queue
backlog; they do not exclude individual scheduling delays or explain ordinary
query-position differences causally.

Diagnostic process-wide worker allocation is approximately 2.12 MB per search,
32 KB per definition and 44.35 MB per full recovery. Median worker GC pause is zero
for ordinary search/definition samples; individual tails include GC. One baseline
2.041 ms definition records a 0.866 ms worker GC pause. A 7.046 ms reference records
3.302 ms GC. Conversely, a candidate 7.771 ms reference records zero worker GC and
4.454 ms gate wait following a 5.139 ms profiling postlude. The postlude executes
before gate release in the generated worker. That is a diagnostic interference
example, not evidence of a production gate regression. These selected tails record
zero JIT-start events; complete event counts and all raw records remain available.

Fixed-order post-idle sweeps read exactly 5,845 files and 23,941,120 bytes. Baseline
versus candidate refresh medians are 160.093/167.796 ms, including opens
70.028/78.475 ms, uncached path checks 39.417/39.187 ms, metadata batching
9.730/9.887 ms, read calls 7.448/7.387 ms and hash append 10.866/10.621 ms.
GC pauses are 2.377/3.061 ms and worker CPU 162.915/170.038 ms. These nested stages
must not be summed as disjoint percentages. The unchanged worker exhibits sweep
variability, but the dominant recovery cost is filesystem validation/open/read
work rather than response copying or GC alone.

Across both diagnostic orders, post-idle refresh ranges 152.468–177.590 ms. Nine
full sweeps also occurred during the measured steady phases and remain included.
Those phases recorded 137 JIT-start events, 177 generation-zero and 22
generation-one collections, and no generation-two collections. Dirty/invalidated
snapshot counters were zero. Event counts show runtime activity persists after
warm-up; they do not establish that JIT or GC caused every slow sample. The rotating
profile also retains position differences inside worker invocation (outline
approximately 0.546 ms first versus 0.145–0.174 ms later), rather than only in
transport. The exact scheduler/cache/power mechanism remains unresolved.

## Receipts

All paths below are local beneath `bin/.local/glider-comparison/`:

- `native-attribution-v1`: provenance, original completion summary, paired ordinary
  summary and the overriding qualification review.
- `native-attribution-v1-aa-fixed`, `-ab-fixed`, `-aa-rotating`, `-ab-rotating`:
  ordinary per-process provenance, samples, logs, source snapshots and summaries.
- `native-attribution-v1-profile-fixed`, `-profile-rotating`: generated sources,
  logs, samples, joined stage summaries and largest samples with raw profiles.
- `native-attribution-smoke-profile-fixed`: earlier diagnostic smoke, separately
  labeled and not pooled into the ordinary comparison.

The paired postprocessor and extra event summaries were added after measurement;
their output records its own source hash. This does not modify raw timings.
The post-run crash detector was likewise added after discovering the retained
failures. A future diagnostic rerun will stop at that gate until corrected rather
than reproduce the old false-positive qualification status.
