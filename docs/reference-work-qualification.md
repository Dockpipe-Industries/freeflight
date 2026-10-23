# Work versus execution-state measurement qualification

The 2026-10-23 follow-up to [fixed-schedule attribution](reference-fixed-attribution.md)
**does not establish whether the extra FindReferences/core-routing time is more
executed work or lower execution throughput**. Short-interval instruction measurements
failed qualification before any new FreeFlight probe was built or timed. All failed
samples and gates remain; no thresholds were relaxed and no outliers removed.

## Scope and instrumentation boundary

One bounded Astra/high read-only review challenged the design before collection,
then reviewed the separately scoped native-only proposal. The review is retained at
`bin/.local/benchmarks/reference-context/work-design-review-v1.json`.
The existing 250 ms schedule, exact oracle, fresh validation, recovery, security and
ordinary-control requirements were to remain. None of the planned workload runs
was reached. Production source and all earlier receipts remain unchanged.

`xcrun xctrace list templates` reports that xctrace is unavailable in the installed
developer tools. The installed public `sys/resource.h` exposes `RUSAGE_INFO_V4`
process instruction/cycle counters through `proc_pid_rusage`. Own-process access
works without privilege/settings changes. Apple's [Recount documentation](https://github.com/apple-oss-distributions/xnu/blob/main/doc/observability/recount.md)
explains context-switch and user/kernel-transition accounting. Availability of a
counter does not establish adequate precision or attribution for a short concurrent
measurement.

The native helper reads monotonic time, process instructions/cycles, process CPU,
then monotonic time, with return-code checks and a fixed 48-byte interop stamp.
These reads are ordered, not simultaneous. Planned worker snapshots would bracket
the unchanged FindReferencesAsync overload; planned core snapshots would subtract
same-process workerRoundTrip counters from the enclosing serverCall. Neither is
foreground/thread-exclusive, nor a frequency/cache/scheduler metric.

The review excluded precise allocation scans and Roslyn progress callbacks from
this first probe. Microsoft's [allocation-counter documentation](https://learn.microsoft.com/en-us/dotnet/api/system.gc.gettotalallocatedbytes?view=net-10.0)
warns that precise allocation counting has significant overhead. Such proxies would
also not substitute for retired instructions. No allocation/progress observer was
added to the preserved worker.

## Qualification results

| Receipt directory under `bin/.local/benchmarks/reference-context/` | Outcome |
| --- | --- |
| `work-capabilities-v1` | Initial native capability passes; doubling a known loop yields instruction ratios 1.984, 2.000, 1.996. Snapshot-pair median wall cost 2.541 µs. |
| `work-probe-v1` | Exact managed/interop short-interval calibration fails the declared scaling checks; FreeFlight probe build/timing stops. |
| `native-work-probe-v1` | Independently scoped native small-complement calibration passes scaling but fails the declared repeat-variability gate; core probe build/timing stops. |

The initial capability calibration is a necessary feasibility check, not evidence
that managed async or native small-complement measurements are fit for inference.
Both later failures remain prominent; neither is relabeled a successful experiment.

### Managed/interop calibration

Five repeats cover 25,000, 100,000 and 1,000,000 deterministic native-loop iterations,
with factors one/two, invoked directly, through Task.Run, and through two joined
worker tasks. There are 90 work observations, 500 empty pairs, 20 nested observations
and one ABI record. Fixed scaling bands are 1.7–2.3 at the smallest size and 1.8–2.2
at the larger sizes. Nested integer composition/monotonicity checks complete.

| Mode | 25k doubling ratio | 100k doubling ratio | 1m doubling ratio |
| --- | ---: | ---: | ---: |
| Direct | 1.284 | 1.650 | 2.202 |
| Async | 1.239 | 1.589 | 1.931 |
| Joined | 4.441 | 1.438 | 3.023 |

These measurements fail qualification for the proposed short process-level window.
Real JIT/background work, accounting granularity and observation can contribute;
the result is **not proof that hardware counters are broken**, nor evidence about
FreeFlight's foreground instruction count. The managed probe stops at its gate.
No worker source copy or FreeFlight build directory is created.

### Independent native-only calibration

The follow-up asks only whether the synchronous core complement can be measured;
it does not retry or rehabilitate the managed experiment. The exact helper executes
on the main thread and a single executor thread while its caller waits. A known
small-work complement surrounds a 3 ms nested wait, with immediate and 25 ms idle
contexts, seven repeats and four work sizes. All 224 nested observations and 2,000
empty pairs remain. Parent-minus-child counts compose correctly without clamping.

Scaling bands pass. The predeclared repeat-range limit is under 5% for at least
50,000 iterations. One 100,000-iteration main-thread/immediate/factor-one cell has
median 519,056 counted instructions and a **6.6099% repeat range**, so qualification
fails. Small 10,000-iteration characterization reaches an 81.2% range; those samples
are retained too. The empty-pair-derived instruction resolution floor is 39,524.
A requested ±5% practical count distinction cannot simply be asserted from these
observations. No native FreeFlight core source copy or build directory is created.

This failure does not prove that every larger native interval is unmeasurable.
It does block the specific short-interval precision claim frozen for this experiment.
No repeat, threshold relaxation, selective exclusion or four-process matrix follows.

## Preserved state, audit and next step

Both `decision.json` files explicitly record failed qualification, zero new
FreeFlight workload queries and zero new FreeFlight probe builds. Calibration
executables/libraries and the managed calibration program were built; those are
not FreeFlight correctness/performance passes. All raw JSONL, build logs, helper
sources, executed-adapter snapshots and rejection decisions remain. The authored
post-gate probe-building paths were not executed or qualified.

The receipt-only audit recomputes both failures from every raw observation and
checks provenance/absence of probe outputs. It does not run native code or queries:

```sh
dockpipe --workflow benchmark.reference.work.audit
```

The preparation workflows use fixed fresh directories and refuse overwrite. Do not
rerun them unchanged seeking a pass. A future experiment needs a separately frozen,
validated measurement path and precision target first. Potential next steps are a
profiler/accounting method demonstrated to cover short concurrent work, or an
explicitly different question whose lower precision can be justified in advance.
No privileged profiler installation or trust/power/affinity change was attempted.

FindReferences and short core-routing work-versus-throughput attribution remain
unresolved. The earlier wall/CPU decomposition remains valid within its documented
scope; it does not become an instruction or frequency result. Preserve strict fresh
validation and recovery, and do not optimize away security checks from this failure.
Glider definition/search/idle, native allocations, real repositories, long memory
runs and other platforms remain open. No commit, push, merge, publication or deployment.


## Separate whole-block external-counter qualification — 2026-10-23

A bounded Astra/high read-only design review supported a distinctly coarser question:
total process instructions over complete four-second blocks. Such totals include all
operations, JIT/runtime/background work and observation; they cannot assign counts
to FindReferences or core routing. No new FreeFlight observer source or binary was
needed or created. The review and its limits are retained in
`aggregate-work-calibration-v3/design-review.json` under the receipt root above.

The external reader uses public `proc_pid_rusage(childPid, RUSAGE_INFO_V4)`, preserving
PID plus process-start identity, raw instruction/cycle/CPU fields, ordered syscall
timestamps and status. CPU fields use Mach time units, converted with the observed
125/3 timebase. Source evidence is pinned to Apple XNU revision
`f6217f891ac0bb64f3d375211650a4c1ff8ca1ea`, including
[task recount assignment](https://github.com/apple-oss-distributions/xnu/blob/f6217f891ac0bb64f3d375211650a4c1ff8ca1ea/osfmk/kern/task.c)
and [rusage population](https://github.com/apple-oss-distributions/xnu/blob/f6217f891ac0bb64f3d375211650a4c1ff8ca1ea/osfmk/kern/bsd_kern.c).
This is pinned upstream evidence, not a claim that the installed kernel is that
revision. Separate cumulative child CPU-clock values are bracketed by external
reads before/after collection; all four checks pass the frozen tolerance. The parent
and native helper use the same verified CLOCK_MONOTONIC domain.

Two implementation mistakes preceded the final calibration and remain visible:

- `aggregate-work-calibration-v1`: one retained observation exposes Python3.9
  process-relative monotonic timestamps mixed with native absolute CLOCK_MONOTONIC.
  The boundary gate stops collection. No scaling inference is valid.
- `aggregate-work-calibration-v2`: one retained observation passes clock boundaries,
  then an unequal-window CPU check stops collection. The child clock was read before
  result serialization while the external window included it and the remaining gap.
  Its 35.2ms difference cannot establish a conversion failure. Fixed complete-path
  warmup and a separate coordinated cumulative check correct this setup in v3.

These corrections are separately labeled; they do not erase samples or relax the
instruction gates. All executed sources, builds, raw data, plans and diagnoses remain.
Neither setup failure produced a target query or FreeFlight build.

The final finite v3 calibration uses two fresh managed children, each with 1,000
joined-call warmups, two fixed complete-path four-second warmup windows, then three
ABBA groups and four zero-loop windows: 24 workload windows plus eight zero-loop
windows, **512 measured cycles**. Each 250ms cycle dispatches two joined native-loop
tasks with exactly N or 2N combined iterations; every checksum and completion is
verified. Retained arm64 disassembly contains five instructions per loop iteration.
The independently predicted B-minus-A loop increment is 80 million instructions per
window. Zero-loop windows preserve dispatch/join/scheduling/serialization scaffolding;
no overhead is subtracted from observations.

All 32 windows pass identity/status/monotonicity, checksum, cycle-completion and quiet
boundary gates. **Instruction qualification fails:** all 12 adjacent paired composite
checks fail the frozen ratio 1.9–2.1 plus increment 80M±5% requirements. Ratios range
1.115–2.131; increments range 19.44M–104.23M. Zero-loop windows count 5.84M–25.06M
instructions; within-child same-factor repeat ranges reach 170.77M. The frozen
conservative empirical-uncertainty statistic (maximum zero window plus maximum
repeat range) is 195.82M instructions. It is not a certified hardware resolution.
Later closer ratios do not replace early observations or qualify another run.

`result.json`, `decision.json`, raw JSONL, complete-path warmups, coordinated CPU
checks, sources/disassembly and all hashes remain in `aggregate-work-calibration-v3`.
The receipt-only audit recomputes all structural checks and failed instruction gates:

```sh
dockpipe --workflow benchmark.reference.aggregate.audit
```

Its output is `aggregate-work-calibration-audit-v1.json`. Audit success verifies the
failed measurement decision; it does not qualify this reader for target inference.
The prepare workflow refuses to overwrite v3; do not rerun it unchanged. There are
**zero new FreeFlight queries, zero target probe builds and no four-process matrix**.
No threshold relaxation, selective exclusion or instruction/frequency claim follows.

The new aggregate path also cannot resolve the target's work-versus-runtime question.
Production remains exact94 with validation/security/recovery intact; prior correctness
qualifications are preserved by source/binary identity, not claimed as freshly rerun.
Next perform a bounded structural review of avoidable repeated work around the
reference invocation and core boundary, screening any proposed change with existing
wall/CPU and all-operation correctness workflows. Another counter run requires a new
validated measurement case. Glider definition/search/idle and other outstanding
qualification remain open. No commit, push, publication, merge or deployment.
