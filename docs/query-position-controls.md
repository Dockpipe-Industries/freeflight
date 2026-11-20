# Ordinary query-position controls

This follow-up accepts the scoped cancellation-lifetime correction at `6a06b1d`
for local qualification, not the rejected response-copy or parallel-recovery
experiments. It compares the corrected worker with before source `6636d94`, then
uses identical corrected binaries to test query ordering and spacing. No new
Glider timing is claimed. Fixtures remain the immutable M6 synthetic 433-file/
two-project and 5,845-file/26-project graphs, not Linux/Biztraak.

## Controlled factors

The prior cyclic rotation balanced positions but kept most within-round
predecessors fixed. The new four-round Williams design uses indices
`0132`, `1203`, `2310`, `3021` for outline, definition, references and search.
Each operation occupies each position once, and each of the twelve distinct
directed predecessor pairs occurs once within a block. The postprocessor verifies
that design from actual samples. Cross-round predecessor context is also retained.

Each ordinary sample records its actual response-end-to-next-request-start gap
and predecessor. The gap includes semantic-oracle/receipt work and deliberate
sleep. It is not inferred from an operation's position, nor from a nominal pacing
parameter. Timing itself retains the existing endpoint boundary and exact oracle.
No per-request profiler, GC observer or process sampler is enabled in these runs.

The serial workflow performs:

1. Fresh native before/fixed worker preparation and existing semantic/security
   tests, followed by fixed diagnostic preparation and native protocol/process
   tests. Preparation records zero timed processes. The old deterministic race
   remains known even if an ordinary baseline preparation happens to exit cleanly.
2. Before/fixed ordinary comparisons with balanced order, both graph sizes,
   back-to-back and 100 ms round pacing, two fresh pairs per cell, 10 seconds
   warm-up and 80 measured rounds. Both labels use the exact same newly built core
   executable; only worker lifetime handling and test source differ.
3. Three full-graph identical-binary controls, each with two fresh pairs: fixed
   order/100 ms round pacing; balanced order/100 ms round pacing; balanced order
   with a deliberate 20 ms delay before each query and no round pacing. Both
   labels share the exact same core and worker executable in these controls.
4. A bounded within-process crossover of those cadence policies, using four-round
   balanced blocks and alternating starting policy across fresh processes.

The equal-gap condition deliberately changes cadence; it is an intervention to
test timing context, not an apples-to-apples candidate speed claim. Actual gaps
remain necessary because prior-operation oracle work adds time. A change in
position effects can support a role for spacing without identifying CPU frequency,
cache residency, thread scheduling or any other lower-level mechanism.

All startup, whole-session CPU, steady-state, post-idle, per-position and
predecessor-conditioned data remain available. No recovery or tail samples are
removed. Two fresh pairs are bounded evidence, not broad statistical qualification.
Earlier response-copy and small-graph regressions remain in their original reports.

## Workflow and repeat command

`benchmark.trusted.position` reuses the existing native MCP driver rather than
adding another client or semantic implementation. Candidate source requires both
passing worker qualification and transactional receipts. An explicit recorded
qualified-only input option permits native timing without redundantly requiring a
worker-only timing pass first. The crash-log rejection gate remains mandatory.

```sh
PATH="$PWD/bin/.local/perf-venv/bin:/Users/jamie/Documents/Codex/2026-10-20/task/freeflight-dependabot/bin/.local/dotnet11:$PATH" \
DOTNET_CLI_USE_MSBUILD_SERVER=0 \
FREEFLIGHT_GLIDER_CMAKE=/Users/jamie/Documents/Codex/2026-10-19/task/toolchains/cmake-3.31.8-macos-universal/CMake.app/Contents/bin/cmake \
FREEFLIGHT_GLIDER_DOTNET_ROOT=/Users/jamie/Documents/Codex/2026-10-19/task/toolchains/dotnet \
FREEFLIGHT_POSITION_LABEL=position-lifetime-v2 \
dockpipe --workflow benchmark.trusted.position
```

Use a new label to repeat. `FREEFLIGHT_POSITION_FIXED_REF`,
`FREEFLIGHT_POSITION_FIXED_RECEIPT`, `FREEFLIGHT_POSITION_SESSIONS` and
`FREEFLIGHT_POSITION_ROUNDS` parameterize the fixed source/qualified receipt and
sample plan. Defaults pin `6a06b1d` and `shutdown-lifetime-v1`. Local toolchain paths
must be replaced on another machine; the required qualified source and native
receipts must already exist. Source, fixture, package and driver hashes are retained.
The session count must be at least two and the round count a multiple of eight.

`position-lifetime-v1` is a preserved setup failure: the adapter initially required
a worker-only timing summary from an otherwise qualified worker receipt. It failed
before timing. `position-lifetime-v2` explicitly records the qualified-only input
and retains all security/transaction gates. Nothing was deleted or overwritten.

## Lifetime-fix ordinary results

The before/fixed comparison passed all 16 fresh processes: 5,120 steady and 64 post-idle semantic checks. These are balanced-order comparisons with two fresh sessions per variant/cell. Values below are medians of per-session median/p90 statistics; maximum is the largest retained sample. Units are milliseconds. No latency-based exclusions are used.

| Files | Round interval | Operation | Before median | Fixed median | Before p90 | Fixed p90 | Before max | Fixed max |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 433 | 0.0 s | symbols | 0.152 | 0.153 | 0.163 | 0.162 | 0.241 | 0.253 |
| 433 | 0.0 s | definition | 0.141 | 0.141 | 0.154 | 0.159 | 0.279 | 0.447 |
| 433 | 0.0 s | references | 0.467 | 0.473 | 0.508 | 0.542 | 0.873 | 1.193 |
| 433 | 0.0 s | workspaceSymbols | 0.235 | 0.231 | 0.246 | 0.238 | 0.779 | 0.387 |
| 5845 | 0.0 s | symbols | 0.184 | 0.184 | 0.230 | 0.228 | 2.416 | 0.319 |
| 5845 | 0.0 s | definition | 0.169 | 0.169 | 0.231 | 0.211 | 0.593 | 0.553 |
| 5845 | 0.0 s | references | 0.648 | 0.644 | 0.736 | 0.720 | 1.251 | 1.809 |
| 5845 | 0.0 s | workspaceSymbols | 8.011 | 7.983 | 8.473 | 8.474 | 10.403 | 10.590 |
| 433 | 0.1 s | symbols | 1.371 | 1.286 | 2.182 | 2.221 | 33.774 | 29.707 |
| 433 | 0.1 s | definition | 1.199 | 1.217 | 2.140 | 2.127 | 2.615 | 2.557 |
| 433 | 0.1 s | references | 3.342 | 3.303 | 4.635 | 4.670 | 6.827 | 7.384 |
| 433 | 0.1 s | workspaceSymbols | 2.454 | 2.404 | 3.326 | 3.307 | 4.705 | 36.465 |
| 5845 | 0.1 s | symbols | 0.524 | 0.598 | 1.478 | 1.571 | 144.066 | 146.087 |
| 5845 | 0.1 s | definition | 0.502 | 0.586 | 1.551 | 1.556 | 121.189 | 144.897 |
| 5845 | 0.1 s | references | 1.571 | 1.751 | 3.384 | 3.227 | 4.777 | 4.846 |
| 5845 | 0.1 s | workspaceSymbols | 26.015 | 26.048 | 28.847 | 29.279 | 33.620 | 32.203 |

The repair is accepted for correctness, not as a performance optimization. Full-graph unpaced medians are near parity. Paced mixed-position medians worsen in several full-graph cells; small-graph unpaced reference p90 also worsens. These unfavorable observations are retained. The identical-binary balanced control itself has a 1.096 outline-p90 label ratio, so an observed tail difference is not automatically attributable to the repair. It is also not automatically dismissed as noise.

Full-graph post-idle outline samples are 159.94/161.55 ms before and 158.98/159.03 ms fixed for unpaced sessions; paced samples are 155.89/176.90 ms before and 155.38/156.33 ms fixed. No recovery algorithm changed; the unfavorable 176.90 ms baseline sample remains. Small-graph idle samples span 32.78–35.06 ms before and 33.01–34.96 ms fixed.

Load medians (before/fixed) are 3,084.36/3,102.75 ms full/unpaced and 2,882.31/2,898.04 ms full/paced. Whole-session child CPU medians are 18.193/18.203 seconds and 11.573/11.709 seconds respectively. Small-graph CPU medians are 26.780/26.365 seconds unpaced and 5.318/5.204 seconds paced. These CPU totals include startup, time-based warm-up, queries and idle recovery, exclude the Python driver, and are not normalized per request; faster warm-up loops can execute more requests.

## Interrupted condition and recovery

The executor handle disappeared during the original equal-delay control. Read-only process inspection confirmed no surviving task benchmark processes before recovery. One complete baseline process and a partial candidate directory survived; the partial process's unflushed timings were unavailable. The original condition was not marked complete or pooled selectively. All its available evidence remains in `position-lifetime-v2-aa-equal-gap`, with the exact interruption recorded in `position-lifetime-v2/interruption-review.json`.

Only that four-process condition was repeated, under `position-lifetime-v2-aa-equal-gap-recovery`. `benchmark.trusted.position.summary` validates source hashes, fixtures, SDK, warm-up, sample plan, ordering and delays against the interrupted attempt. It refuses to replace a completed condition and rejects an incomplete condition without an explicit recovery receipt. The negative incomplete-condition check passed. The validated `completion-review.json` covers all 28 planned ordinary processes (8,960 steady and 112 idle checks); one additional completed process from the interrupted attempt remains separate. The original orchestrator was interrupted, not retroactively relabeled successful.

The equal-delay replacement had actual median gaps around 27–32 ms despite a requested 20 ms sleep. It also ran after the interruption. Therefore cross-condition differences alone cannot establish a spacing-only causal explanation. A separate bounded within-process cadence crossover was added to address that execution-epoch confound.

## Within-process crossover

The additional `position-lifetime-v3-crossover` control passed four fresh processes, 1,280 steady checks and 16 idle checks. Each process alternates four-round balanced blocks between 100 ms round pacing and a deliberate 20 ms pre-query delay with no round pacing. Starting policy alternates across processes. The same operation, ordinal, predecessor and binary can therefore be compared within a process; intentional sleeps remain outside the endpoint timer. This adds no runtime code change. The current workflow now includes this crossover automatically.

The combined final review covers 32 complete processes and 10,368 measured semantic checks (10,240 steady, 128 idle), plus the separately preserved interrupted-condition baseline. This is successful semantic/correctness qualification, not a claim every performance cell improved.

Medians and p90 below are medians of the four per-process statistics, in milliseconds. Gaps are measured response-end-to-request-start medians. All samples remain included.

| Operation | Position (1-based) | Round median | Delay median | Round p90 | Delay p90 | Round gap | Delay gap |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| symbols | 1 (boundary) | 0.759 | 1.691 | 0.861 | 1.977 | 0.079 | 95.935 |
| symbols | 2 | 0.414 | 0.573 | 0.488 | 0.708 | 3.030 | 27.907 |
| symbols | 3 | 0.684 | 1.873 | 0.828 | 2.159 | 0.114 | 24.064 |
| symbols | 4 | 0.308 | 1.327 | 0.332 | 1.506 | 0.148 | 25.117 |
| definition | 1 | 1.529 | 1.464 | 1.618 | 1.573 | 75.491 | 25.293 |
| definition | 2 | 0.524 | 2.015 | 0.657 | 2.162 | 0.051 | 24.082 |
| definition | 3 | 0.419 | 0.554 | 0.474 | 0.689 | 2.933 | 27.797 |
| definition | 4 | 0.293 | 1.477 | 0.327 | 1.692 | 0.045 | 24.457 |
| references | 1 | 3.111 | 2.459 | 3.477 | 3.177 | 77.130 | 28.495 |
| references | 2 | 2.273 | 3.487 | 2.437 | 4.067 | 0.057 | 23.515 |
| references | 3 | 1.072 | 2.952 | 1.506 | 3.245 | 0.145 | 25.227 |
| references | 4 | 1.120 | 2.772 | 1.172 | 3.650 | 2.981 | 28.558 |
| workspaceSymbols | 1 | 27.729 | 26.742 | 29.156 | 28.945 | 73.600 | 24.544 |
| workspaceSymbols | 2 | 24.259 | 24.603 | 26.402 | 26.854 | 0.140 | 25.105 |
| workspaceSymbols | 3 | 23.816 | 36.600 | 25.242 | 38.620 | 0.019 | 24.258 |
| workspaceSymbols | 4 | 23.608 | 34.850 | 25.334 | 36.638 | 0.046 | 23.273 |

The first outline in each block inherits the preceding block's end-of-round pacing. Its policy label is not an independent current-policy gap: the measured gaps show this reversal, and `blockBoundaryCarryover` flags it. No boundary samples were removed. Within-block comparisons avoid that particular boundary issue. For example, last-position definition rises from 0.293 to 1.477 ms, with delayed/round median ratios 4.40–5.26 across the four processes; actual gaps rise from 0.045 to 24.457 ms. Last-position outline rises from 0.308 to 1.327 ms, with ratios 4.16–4.55. Search in positions three/four also becomes materially slower. These changes occur inside unchanged processes with sleep excluded from response timing.

This supports a substantial cadence/context effect on measured service latency; it does not identify a CPU-frequency, cache, scheduler, runtime or GC mechanism. This Williams design balances predecessors but does not independently vary every predecessor at every position for one operation. Full separation of predecessor versus ordinal would need a larger factorial order design. Conditions remain bounded synthetic evidence, and the five-second recovery contract remains active throughout.

Largest retained crossover response samples by operation and policy (milliseconds):

| Operation | Round maximum | Delayed maximum |
| --- | ---: | ---: |
| symbols | 1.544 | 130.025 |
| definition | 141.945 | 142.523 |
| references | 4.609 | 140.504 |
| workspaceSymbols | 31.373 | 165.055 |

The retained raw data is the authority for every sample. Large ordinary samples are not classified as recovery solely from their latency. Earlier instrumented source attribution remains separate.

## Qualification outcome and remaining constraints

Accepted local runtime change: the cancellation lifetime correction at `6a06b1d`.
Deterministic ordinary/diagnostic before failures and after successes, callback
contracts, worker shutdown/cancellation/security/mutation gates, all 16 incremental
fault checks, transaction checks and native protocol/process tests pass. The
previous diagnostic shutdown failure is corrected in new receipts, not erased.
No response-copy, search or parallel-recovery candidate is accepted here.

The service-time changes under cadence crossover are much larger than the lifetime
repair's direct scope. They establish that benchmark context matters and that
mixed-position medians are unsafe as a sole decision criterion. They do not justify
dismissing every unfavorable before/fixed cell or claiming a specific low-level
cause. Position/predecessor separation and low-overhead scheduling/CPU observations
remain technical work; diagnostic profiler overhead remains a separate concern.

Full recovery still must read the complete graph by the documented deadline.
The prior ordered-byte-accounting counterexample remains: naïve parallel completion
can report the wrong failing file. Any future bounded parallel reader needs sorted
error consumption, bounded memory/descriptors and reservations for actual bytes,
uncached pre-open validation, cancellation/draining and atomic publication before
performance qualification. No watcher-only authority, TTL extension or background
work was introduced. See [the recovery proof obligations](native-mcp-attribution.md).

All artifacts are local. There is no unresolved permission or connection blocker.
The original orchestrator was interrupted; the executed qualification was completed
through an explicit replacement and standalone crossover, not an uninterrupted
run of the final default recipe. The current recipe automates those same stages.
No publication, remote CI/platform claim, active MCP or Biztraak change occurred.

Final validation of the retained recovered receipts used:

```sh
PATH="$PWD/bin/.local/perf-venv/bin:$PATH" \
FREEFLIGHT_POSITION_LABEL=position-lifetime-v2 \
FREEFLIGHT_POSITION_EQUAL_GAP_RECEIPT="$PWD/bin/.local/glider-comparison/position-lifetime-v2-aa-equal-gap-recovery" \
FREEFLIGHT_POSITION_CROSSOVER_RECEIPT="$PWD/bin/.local/glider-comparison/position-lifetime-v3-crossover" \
dockpipe --workflow benchmark.trusted.position.summary
```

The final machine-readable result is
`bin/.local/glider-comparison/position-lifetime-v2/final-review.json`.
Raw samples and per-session median/p90/max remain under each condition directory;
`position-summary.json` retains predecessor/position/gap statistics, and
`position-lifetime-v3-crossover/crossover-summary.json` retains matched policy
statistics and the boundary-carryover flag. The interrupted first process is not
silently pooled into the complete comparison or discarded from evidence.
