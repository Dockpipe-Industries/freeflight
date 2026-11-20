# Core CPU versus paced latency

Local macOS arm64, 2026-10-22. Production runtime stays byte-identical to
`94eb4207c8ffd2d5544bca8a52dcb8d451285015` in the preserved worktree
`/Users/jamie/Source/freeflight-perf`, branch `investigate/rc2-warm-refresh`.
The [copy candidate](json-response-copies.md) stays unaccepted and archived. These
controls use frozen generated binaries explicitly; they do not reinstall it.
Main js/dev, strict defaults, fresh validation, recovery and persistent configuration
are unchanged. No commit, push, publication, merge or deployment occurred. All
processes ran serially; no additional agents were started.

The useful result is a localization, with a remaining mechanism gap: lower core CPU
reduces the large-response boundary, but worker invocation costs can offset it.
Pacing changes both worker and boundary costs; equalizing request gaps does not
universally restore the source comparison. Worker CPU also rises in an unfavorable
condition, so extra waiting alone is insufficient. These measurements do not identify
hardware frequency, cache state, GC or scheduler causation, or prove that copying
less caused the worker changes.

## Predefined context control

`bin/.local/benchmarks/response-copies/json-moves-v2/pacing-context-v1` retains the
collection plan before timing, all frozen binary/source identities, startup policy
hash, client/core/worker IDs, exact oracles, actual timestamps/gaps, verification and
sleep durations, and every response record. The old ordinary copy screen did not
record actual gaps/verification costs, so those cannot be reconstructed from it.
The earlier [cadence crossover](query-position-controls.md) already showed a large
spacing effect; this follow-up adds source/A/A cohorts and correlated stage costs.

Eight interleaved fresh processes form two cohorts. In the source cohort, labels use
baseline94 versus the archived move-only core. In the sham cohort, both labels use
the exact same baseline core. Both cohorts balance starting cadence and process order.
Startup configuration bytes and worker binary are identical across all eight processes.
Both reused generated cores have protocol/process qualification; the reused generated
worker has semantic/security and trusted-project qualification. All identities and
qualification receipts are verified before execution. The fixture is the same
5,845-file graph, 4,096 bytes/file, fourteen callers and C5 search, using pinned SDK 11.

After five-second warmup, each process alternates eight blocks of eight balanced
four-operation rounds. Each block retains four acclimation rounds, then measures
four rounds fixed before execution. Thus each policy has every operation/position
and directed predecessor pair balanced within each process. Measured samples are
past the policy boundary, and all boundary/acclimation records remain in raw data.

* Round policy: a 100 ms minimum total round period, with no inserted inter-query delay.
* Equal-gap policy: request start is scheduled no earlier than 25 ms after the previous
  client return. Actual gaps are measured, not assumed. OS sleep overshoot puts most
  equal-gap medians around 30 ms, matched across labels. Verification time counts
  toward the gap; requested sleep is excluded from request latency.

All 1,024 measured responses and 1,024 acclimation responses pass exact semantics,
text/structured equivalence and ID joins. Another 1,364 warmup responses and 32 initial
oracle responses pass and remain retained. Every one of the 768 measured symbol/
definition/reference requests reads one fresh 4,096-byte target. Measured search reads
zero source bytes; no measured foreground full recovery occurs. This is not an idle
successful-background-sweep accounting claim. Recovery remains enabled and unchanged.
All fixture hashes are checked before and after collection.

## Stage contrasts and session variation

Ratios are candidate label / baseline label, using medians of session medians. In
the sham cohort both labels execute identical code. These are descriptive diagnostic
estimates with two processes per label, not significance tests or acceptance limits.
All per-process and pooled summaries remain, including contradictory estimates.

| Cohort | Policy | Operation | Client | Worker invoke | Outside invoke | Core thread CPU |
| --- | --- | --- | ---: | ---: | ---: | ---: |
| sham | round | symbols | 0.975 | 1.070 | 0.940 | 0.996 |
| sham | round | definition | 1.057 | 1.056 | 1.038 | 1.066 |
| sham | round | references | 1.027 | 0.981 | 1.064 | 1.048 |
| sham | round | workspaceSymbols | 1.045 | 1.102 | 1.004 | 1.000 |
| sham | equal-gap | symbols | 1.176 | 1.207 | 1.197 | 1.150 |
| sham | equal-gap | definition | 1.011 | 1.077 | 0.943 | 1.029 |
| sham | equal-gap | references | 1.099 | 1.061 | 1.111 | 1.038 |
| sham | equal-gap | workspaceSymbols | 1.005 | 1.080 | 0.942 | 0.991 |
| source | round | symbols | 1.066 | 1.112 | 1.058 | 1.063 |
| source | round | definition | 1.096 | 1.224 | 1.005 | 1.099 |
| source | round | references | 1.101 | 1.080 | 1.040 | 1.037 |
| source | round | workspaceSymbols | 1.012 | 1.236 | 0.864 | 0.795 |
| source | equal-gap | symbols | 1.611 | 1.703 | 1.525 | 1.455 |
| source | equal-gap | definition | 1.149 | 1.090 | 1.161 | 1.101 |
| source | equal-gap | references | 1.025 | 1.023 | 1.024 | 0.984 |
| source | equal-gap | workspaceSymbols | 1.119 | 1.327 | 0.908 | 0.883 |

The same-binary labels differ (for example equal-gap symbol latency +17.6% and reference
latency +9.9%). The source cohort has other adverse cells, including equal-gap symbol
latency +61.1%, which remain. This variation prevents assigning every contrast to
source changes. A/A results are not grounds to erase an adverse source result.

Within unchanged processes, equal-gap / round client median ratios have median 2.244
for symbols, 2.377 for definition, 1.700 for references and 1.259 for search. Definition
ranges 1.649–3.393 and references 1.335–2.204 across the eight processes: both slow in
all eight. Worker invocation and outer-boundary costs both increase. This demonstrates
a context effect with sleep outside the request timer, not its hardware/runtime cause.
The intervention changes throughput/cadence; it is not an ordinary candidate speed claim.

Search localizes the lost benefit. Exact mean wall decomposition is valid per request:
`client total = worker invocation + outside invocation`. The following are differences
of those means, not subtraction of independent medians. Positive means candidate
label slower. Core CPU is a separate overlapping CPU measure and is not added to wall.

| Source cohort policy | Client delta ms | Invoke delta ms | Outside delta ms | Core CPU delta ms |
| --- | ---: | ---: | ---: | ---: |
| round | +0.5208 | +2.0564 | -1.5356 | -1.8498 |
| equal-gap | -0.4735 | +1.1234 | -1.5969 | -1.9914 |

Round-paced search saves 1.54 ms outside invocation while worker invocation rises 2.06 ms,
leaving total mean 0.52 ms higher. Equal-gap source search still has higher worker cost;
matching gaps does not universally rescue its session-median contrast. Its mean total
is slightly favorable, while its ratio of session medians is unfavorable. Both views
remain. Nonlinear summaries and different distributions cannot be treated as additive
or selected to manufacture a winner. Median worker gate waits remain tiny; this is
not evidence that relaxing the gate or freshness would solve the gap.

## Bounded worker CPU follow-up

`pacing-worker-cpu-v1` is a narrower four-process source-only ABBA follow-up, with the
same block/gap/oracle plan and both starting policies balanced per core. It adds two
process-CPU clock reads around invocation in a generated copy of the qualified worker.
No production file changes. Native `clock_gettime(CLOCK_PROCESS_CPUTIME_ID)` is checked
against the installed Apple SDK and a compiled ABI probe (clock ID 12, sixteen-byte
Timespec with two eight-byte fields). No application dependency is added.

A standalone generated calibration distinguishes elapsed wall time from process CPU:
sleep wall/CPU 53.961/0.160 ms; busy wall/CPU 50.005/49.821 ms.
Median overhead for a warmed pair of clock reads is 0.0005 ms.
This is a calibration, not a full observer-overhead bound. The new generated worker
passes semantic/security, UTF-8, mutation/cancellation and trusted-project suites.
Both reused core identities remain verified. All 512 measured, 512 acclimation, 680
warmup and 16 initial-oracle responses pass. All 384 measured targeted requests read
exactly 4,096 fresh bytes; no measured foreground recovery occurs. All hashes remain.

Worker process CPU covers all worker threads during invocation, including runtime/GC
and any concurrent process work. It follows async continuations and can exceed wall
time when threads run in parallel (notably references). Therefore wall minus process
CPU is not an off-CPU/wait estimate. This observer is separate from the first probe;
do not pool samples or interpret cross-probe latency differences as optimizations.

| Policy | Operation | Client ratio | Invoke wall ratio | Worker process CPU ratio | Core thread CPU ratio |
| --- | --- | ---: | ---: | ---: | ---: |
| round | symbols | 1.023 | 1.069 | 0.919 | 0.921 |
| round | definition | 1.458 | 1.529 | 1.430 | 1.287 |
| round | references | 1.058 | 1.136 | 1.038 | 0.891 |
| round | workspaceSymbols | 0.952 | 1.009 | 1.009 | 0.798 |
| equal-gap | symbols | 1.017 | 1.018 | 1.036 | 0.984 |
| equal-gap | definition | 0.910 | 1.032 | 1.032 | 0.893 |
| equal-gap | references | 1.064 | 1.069 | 1.084 | 0.992 |
| equal-gap | workspaceSymbols | 1.107 | 1.393 | 1.413 | 0.813 |

In equal-gap search, worker wall and process CPU rise 39.3%/41.3% while core CPU falls
18.7%. In round search, worker wall/CPU are essentially unchanged, core CPU falls 20.2%
and client median improves 4.8%. Thus a core CPU benefit can appear without a consistent
paced-latency win. CPU time growth is observable in the adverse condition; pure pipe
waiting is insufficient. CPU time is not retired work/instructions: lower frequency,
cache/runtime work and parallelism remain possible explanations, not measured findings.

As in the first probe, some mean deltas differ in direction from session-median ratios;
raw outliers, all means and every process remain. Definition also changes direction
between policies. No acceptance threshold, causal source attribution, hardware
explanation or overall win is claimed from these small diagnostic cohorts.

## State and next step

The copy candidate stays archived/unaccepted. All 28 tracked production src/include/
Roslyn files remain byte-identical to `94eb420`. The previously authored dual-content
protocol test and all prior local changes/receipts remain. Independent audits verify
balanced positions/predecessors, exact timing identities, source/binary/config hashes,
fresh reads and each mean wall decomposition. Derived summaries refuse replacement
with different data. No measured or unfavorable record is removed.

Next use predefined ordinary matched controls with recorded actual gaps and stable
session/position summaries before accepting a response change. Further worker CPU
attribution would need scheduler/GC or hardware observations; do not assume a power
mechanism or change power settings from these results. There is no reason to repeat
the unchanged rejected candidate simply to obtain favorable cells. Glider idle,
native allocation, real repositories, long-duration memory and other platforms remain
open. No new Glider matrix is justified by this diagnostic.

## Replay

Use perf-venv and pinned dotnet11 on PATH; fresh labels refuse overwrite:

```sh
FREEFLIGHT_CONTEXT_LABEL=NEW_LABEL dockpipe --workflow benchmark.response.copies.context
FREEFLIGHT_CONTEXT_LABEL=NEW_CPU_LABEL dockpipe --workflow benchmark.response.copies.context.cpu
FREEFLIGHT_CONTEXT_LABEL=pacing-context-v1 dockpipe --workflow benchmark.response.copies.context.audit
FREEFLIGHT_CONTEXT_LABEL=pacing-worker-cpu-v1 dockpipe --workflow benchmark.response.copies.context.cpu.audit
```

Collection reuses retained qualified instrumented cores and the frozen worker receipt.
CPU mode builds only generated diagnostic source and calibration, then runs its worker
gates before timing. The CPU audit workflow issues no new requests and its adapter is retained with the receipt;
all paths, versions, qualifiers and exact plan are in each run manifest. Replay documents
reproducibility, not a recommendation for another unchanged benchmark run.

Follow-up: [ordinary matched sessions and recorded gaps](ordinary-matched-gaps.md) uses
the uninstrumented qualified binaries and retains same-binary variation and every pair/position.
