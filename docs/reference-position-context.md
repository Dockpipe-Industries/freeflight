# Baseline reference position and predecessor context

## Question and predefined design

The 2026-10-23 baseline-only control follows the
[ordinary matched comparison](ordinary-matched-gaps.md). That comparison retained
all session/position results and left the JSON-copy candidate archived/unaccepted.
Its rotating four-order design associated each reference position with a particular
predecessor. This control expands order coverage without changing runtime source.

One bounded Sol/high read-only agent reviewed the design before collection. Its
findings and incorporated corrections are retained in
`bin/.local/benchmarks/reference-context/design-review-v1.json` and copied into the
run receipt. No agents or other benchmark processes overlap collection. The review
identified pacing/rate confounding, specified adjacent block pairing and required
reuse of the previously frozen exact oracle.

Receipt root:
`bin/.local/benchmarks/reference-context/baseline-position-v1/`.
The complete schedule and analysis plan are frozen in `run-manifest.json` before
any process starts. Four serial ordinary baseline94 processes use the previously
qualified frozen core and identical exact94 worker, canonical 5,845-file fixture,
configuration and startup arguments. Binaries, fixture, oracle and drivers are
hashed before/after collection. No CPU/stage probes, RSS sampler or event listener
is installed; outer timestamps and exact-answer verification remain observer work.

Each process warms for at least five seconds, then runs eight blocks. Each block
has four fixed acclimation rounds under the incoming policy, followed by the full
24 permutations of symbols, definitions, references and search. Each successive
group of four measured rounds balances every method/position. Adjacent blocks
(0,1), (2,3), (4,5), (6,7) have identical measured permutation orders; those orders
vary between pairs/sessions. Every method occurs at every position six times/block;
at each within-round reference position 1–3, every other method is its immediate
predecessor twice/block. Thus each policy/session has eight reference samples per
position/predecessor cell, with four block replicates. Sparse cell p90s are order
statistics, not reliable tail qualification.

Policies are **round** (100 ms minimum round) and **25 ms gap floor** (the same
round floor plus a 25 ms minimum previous-return to next-request-start gap).
Sequences are PQQPPQQP in each session; sessions 0/3 start with round and 1/2 with
gap floor. Verification counts toward gaps. End-of-round waiting and gap waiting
satisfy deadlines, without adding two full independent sleeps. State persists
across warmup, acclimation, measured blocks and transitions; the incoming request's
policy governs its preceding gap. Requested/actual sleeps, actual gaps, preceding
method, per-round duration and start-to-start periods remain in receipts.

Gap-floor pacing changes achieved request rate and round duration. Its ratios
(gap floor / round) are a policy contrast, not a pure isolated gap treatment.
Predecessor associations are conditioned on policy and position; earlier history,
elapsed work and background runtime behavior may also matter. Position zero carries
cross-round pacing/history and is reported separately, without a matched factorial
predecessor claim. Four acclimation rounds are a fixed bounded choice, not proof of
equilibration. Every acclimation/warmup/transition and early measured sample remains.

Every phase checks both MCP content forms, complete-result metadata, exact workload
semantics and the frozen ordinary-comparison oracle. No validation, security,
cancellation or recovery code changes. Ordinary timings do not measure fresh-byte
or recovery-sweep counters; they preserve the previously qualified implementation.
No timing exclusions, replacement cells, normalization by observed gap, new
performance acceptance thresholds, candidate reruns or Glider matrix are used.

## Replay

With perf-venv on PATH, collection requires a fresh label and refuses overwrite.
The receipt-only audit issues no requests and refuses different derived data:

```sh
FREEFLIGHT_REFERENCE_CONTEXT_LABEL=NEW_LABEL dockpipe --workflow benchmark.reference.context
FREEFLIGHT_REFERENCE_CONTEXT_LABEL=baseline-position-v1 dockpipe --workflow benchmark.reference.context.audit
```

Raw `samples.json` retains every phase and operation; `result.json` includes all
methods, sessions, matched block pairs, reference cells, within-policy position and
predecessor contrasts, cross-round position-zero histories and round pacing.
`oracle.json`, copied drivers, the design review, per-process configuration/stderr
and `completion-audit.json` preserve provenance and exact checkout state.

## Results

All four processes exit successfully. The audit passes **3,072 measured +512
acclimation +752 warmup +16 initial oracle =4,352 exact checked responses**.
All four methods, 32 blocks, 16 matched block pairs and every phase remain.

The following ratio is gap floor / round. Session medians are summarized as a ratio
of the medians of four session metrics; individual session ratios remain separate.

| Operation | Session median ratio | Session p90 ratio | Four within-session median ratios |
| --- | ---: | ---: | --- |
| symbols | 3.213 | 1.474 | 2.887, 3.148, 3.291, 3.339 |
| definition | 3.121 | 1.329 | 2.797, 3.242, 3.125, 3.169 |
| references | 2.056 | 1.352 | 1.799, 2.257, 2.077, 2.068 |
| workspaceSymbols | 1.297 | 1.291 | 1.270, 1.279, 1.326, 1.290 |

This is baseline-only evidence of a pacing-policy association. It is neither a new
JSON-copy source comparison nor a performance acceptance result. All four operations
have higher median latency under the gap floor in all four sessions.

### References by position

Each policy/session has 24 references at each position. Times and actual gaps below
are medians of four session medians, in milliseconds. Session ratios use the individual
paired session values, not a ratio of these displayed rounded numbers.

| Position | Round latency | Gap-floor latency | Round gap | Gap-floor gap | Four session latency ratios | Higher gap-floor block pairs |
| --- | ---: | ---: | ---: | ---: | --- | ---: |
| 0 | 3.083 | 3.051 | 79.733 | 33.565 | 0.887, 0.986, 1.014, 0.998 | 6/16 |
| 1 | 2.031 | 3.082 | 0.050 | 32.348 | 1.507, 1.599, 1.518, 1.401 | 16/16 |
| 2 | 1.272 | 2.959 | 0.153 | 34.049 | 1.735, 2.498, 2.259, 2.504 | 16/16 |
| 3 | 1.057 | 3.092 | 0.142 | 32.398 | 2.528, 3.031, 2.819, 2.970 | 16/16 |

The round-policy reference median decreases with later position in all four sessions.
The gap-floor policy largely flattens this positional pattern; position zero has
mixed policy directions, while positions 1–3 are slower under the gap floor in every
matched block pair. This exposes a strong context interaction; it does not isolate
idle time from request rate, prior work or runtime state.

### References conditioned on predecessor and position

Each latency value below summarizes four session medians, with eight observations
per policy/cell/session. Actual gaps, every block pair, p90s and means remain in
`result.json`; sparse cell p90s are not used to claim tail improvement.

| Position | Predecessor | Round latency ms | Gap-floor latency ms | Four policy median ratios |
| --- | --- | ---: | ---: | --- |
| 1 | symbols | 2.283 | 4.399 | 1.879, 2.008, 1.930, 1.802 |
| 1 | definition | 2.374 | 3.367 | 1.353, 1.329, 1.347, 1.510 |
| 1 | workspaceSymbols | 1.222 | 1.678 | 1.483, 1.366, 1.313, 1.338 |
| 2 | symbols | 1.485 | 3.533 | 2.152, 2.381, 2.057, 2.378 |
| 2 | definition | 1.441 | 2.969 | 1.799, 2.036, 3.219, 2.085 |
| 2 | workspaceSymbols | 1.255 | 2.021 | 1.258, 2.073, 1.457, 1.816 |
| 3 | symbols | 1.022 | 3.147 | 2.913, 3.191, 2.967, 3.353 |
| 3 | definition | 1.007 | 3.351 | 2.843, 3.720, 3.337, 3.224 |
| 3 | workspaceSymbols | 1.147 | 2.753 | 1.588, 2.366, 2.508, 2.411 |

All predecessor comparisons were retained, including inconsistent directions. Each
cell below lists all four session median ratios within a policy/position.

| Policy | Position | Definition / symbols | Search / symbols | Search / definition |
| --- | ---: | --- | --- | --- |
| round | 1 | 1.013, 1.154, 1.053, 0.962 | 0.521, 0.546, 0.572, 0.511 | 0.514, 0.473, 0.544, 0.531 |
| round | 2 | 1.099, 0.936, 0.600, 1.006 | 1.071, 0.765, 0.735, 0.781 | 0.975, 0.817, 1.225, 0.776 |
| round | 3 | 0.990, 0.965, 1.009, 0.962 | 1.150, 1.101, 1.109, 1.158 | 1.161, 1.141, 1.099, 1.203 |
| gap-floor | 1 | 0.730, 0.764, 0.735, 0.806 | 0.411, 0.371, 0.389, 0.379 | 0.563, 0.486, 0.530, 0.470 |
| gap-floor | 2 | 0.919, 0.801, 0.939, 0.882 | 0.626, 0.666, 0.521, 0.596 | 0.682, 0.832, 0.555, 0.676 |
| gap-floor | 3 | 0.966, 1.125, 1.135, 0.925 | 0.627, 0.817, 0.937, 0.833 | 0.649, 0.726, 0.826, 0.900 |

At position 1, references after search are roughly half as slow as after symbols
under round pacing in every session (ratios 0.511–0.572). At position 3, that relation
reverses under round pacing (1.101–1.158). Under the gap floor, search precedes faster
reference responses at all three within-round positions in all four sessions.
Definition-versus-symbol directions remain mixed in some contexts. There is no
single constant predecessor penalty that explains every position/policy.

These are marginal request-history associations in the predefined complete-order
schedule. Search does substantial prior work and its response verification takes
longer; round-policy reference gaps after search are about 2.5–2.6 ms versus about
0.03–0.10 ms after the small targeted responses. Gap-floor cells realize about
30.8–34.5 ms. Timing control reduces one gap disparity but does not fix all prior
work, total request rate, deeper history or runtime state. No CPU-frequency, cache,
GC, thread-pool, scheduler or semantic-cache mechanism is established.

round measured round start-to-start periods: median 110.075 ms, range 100.116–111.213 ms.

gap-floor measured round start-to-start periods: median 163.788 ms, range 125.487–186.297 ms.

Achieved round periods differ materially, confirming the pacing/rate limit of the
comparison. All transitions and actual periods are retained, without replacement.

## Astra causal review and fixed-cycle follow-up

A bounded Astra/high read-only synthesis independently checked the schedule and
summary counts and found no consequential design/summary inconsistency. It was an
artifact review, not another raw/hash audit. `causal-review.json` retains its findings:
the full-order control resolves descriptive aliasing, while position still changes
earlier work/history and pacing changes request rate. Four processes are replication;
16 nested block pairs are not 16 independent process/machine replications. Client
return-to-start gap is not worker idle duration. Prior instrumented CPU localization
cannot automatically be transferred to these ordinary baseline cells.

The review proposed one discriminating ordinary follow-up, retained at
`bin/.local/benchmarks/reference-context/baseline-wait-placement-v1/`.
Four fresh serial baseline94 processes use only the fixed order **symbols → references
→ definition → search**. References stays at position 1 after symbols. Within each
process, eight counterbalanced blocks use the same adjacent pairing/complement
sequence, with 16 measured and four acclimation cycles/block after 24 fixed warmup
cycles. Both arms execute the same requests; no dummy work or power/affinity/recovery
setting changes fill time.

| Event | Absolute target within each cycle |
| --- | --- |
| Symbols | 0 ms |
| References, immediate arm | After symbols response and required verification |
| References, wait-before arm | At least 25 ms after symbols response, including verification |
| Definition, both arms | 100 ms |
| Search, both arms | 150 ms |
| Next symbols, both arms | 250 ms |

Waiting moves across references rather than changing intended cycle rate or other
request starts. Slots are chosen conservatively from retained all-phase service /
verification maxima: symbols 2.645/0.107 ms, references 9.669/0.199 ms, definition
5.231/0.070 ms, search 40.875/6.893 ms. The new plan records these bounds and their raw
source hashes before collection. Absolute anchors are not rebased; overdue calls
run once with lateness recorded, with no omissions, replacements or timing filters.
Any fixed-slot readiness overrun makes matched-cadence interpretation inconclusive.
Actual timer wake jitter, reference gaps, start offsets and symbol-start periods
are reported even when no slot overruns occur.

This control tests whether a throughput-only explanation suffices for the local
reference penalty in this fixed context. Persistence at the same intended cadence
would weigh against that explanation; disappearance would implicate broader context
without proving rate alone caused the first result. Neither outcome identifies
frequency, caches, GC, scheduler or semantic-cache behavior, or warrants a production
optimization. Both arms keep fresh validation, security, cancellation and recovery.

Replay uses a fresh collection label; audit issues no semantic requests:

```sh
FREEFLIGHT_REFERENCE_WAIT_LABEL=NEW_LABEL dockpipe --workflow benchmark.reference.wait
FREEFLIGHT_REFERENCE_WAIT_LABEL=baseline-wait-placement-v1 dockpipe --workflow benchmark.reference.wait.audit
```

### Fixed-cycle results

All four processes exit successfully; independent audit passes **2,048 measured
+512 acclimation +384 warmup +16 initial oracle =2,960 exact checked responses**.
No fixed-slot **readiness** overruns occur. This does not mean perfect timer wakes:
actual starts are several milliseconds after their targets and remain in the data.

| Operation | Immediate latency median ms | Wait-before latency median ms | Session median ratio | Session p90 ratio | Four paired session median ratios |
| --- | ---: | ---: | ---: | ---: | --- |
| symbols | 1.590 | 1.576 | 0.991 | 0.978 | 0.990, 0.993, 0.976, 0.989 |
| definition | 2.109 | 2.051 | 0.972 | 1.017 | 0.975, 0.974, 0.970, 1.008 |
| references | 2.523 | 3.930 | 1.558 | 1.502 | 1.457, 1.454, 1.489, 1.723 |
| workspaceSymbols | 35.157 | 35.312 | 1.004 | 1.001 | 1.007, 0.981, 0.995, 1.009 |

References are slower under wait-before in all four processes and all 16 nested
block pairs. Every block ratio remains in `result.json`; process-level median
ratios range 1.454–1.723. Other operation medians remain close, with mixed block
directions. This is a deliberately changed local wait placement within an otherwise
fixed request order and intended cadence, not a production performance candidate.

All reference block-pair median ratios, chronological within each process:

| Process | Pair 0 | Pair 1 | Pair 2 | Pair 3 |
| --- | ---: | ---: | ---: | ---: |
| 0 | 1.509 | 1.424 | 1.316 | 1.523 |
| 1 | 1.534 | 1.512 | 1.389 | 1.564 |
| 2 | 1.399 | 1.419 | 1.472 | 1.357 |
| 3 | 1.404 | 1.826 | 1.683 | 1.837 |

Observed start offsets below are median-of-session medians, in milliseconds from
the absolute cycle anchor. They show the realized timing rather than assuming the
fixed targets were met exactly.

| Operation | Immediate start offset | Wait-before start offset |
| --- | ---: | ---: |
| symbols | 10.038 | 10.038 |
| definition | 107.000 | 106.889 |
| references | 11.688 | 40.912 |
| workspaceSymbols | 157.747 | 156.581 |

immediate symbol start-to-start period: median 250.001 ms, mean 250.032 ms, range 241.642–258.363 ms.


wait-before symbol start-to-start period: median 250.000 ms, mean 249.972 ms, range 240.047–259.950 ms.


Reference return-to-start gaps summarize to 0.061 ms immediate versus 31.582 ms
wait-before. Both arms have a 250 ms median cycle period, and the other scheduled
request starts are close (search offsets differ by about 1.17 ms). This supports
the narrow conclusion that request rate alone cannot explain the local reference
penalty in this fixed context. It does not prove an isolated worker-idle mechanism;
client timing, runtime work/state, deeper history and ordinary system jitter remain.
The result does not establish which portion of the extra latency belongs to fresh
validation, semantic execution, core/worker transport, serialization or scheduling.

## Preserved state and next step

Across both controls: **8 serial processes, 5,120 measured +1,024 acclimation
+1,136 warmup +32 initial oracle =7,312 exact checked responses**. Both receipt
audits and no-query replays pass; all raw phases, actual gaps/periods, cell results
and unfavorable observations remain. Sol/high reviewed the first design; Astra/high
reviewed its causal limits and proposed the executed fixed-cycle control. Their
reviews were sequential and completed outside collection. No extra agents or
unmodified rejected candidate reruns were used.

Production remains byte-identical to `94eb420` across all 28 tracked src/include/
Roslyn files, in `/Users/jamie/Source/freeflight-perf` on
`investigate/rc2-warm-refresh`. The dual-content protocol test and all earlier local
work/receipts remain; main js/dev is unchanged. The JSON-copy candidate stays
archived/unaccepted. No commit, push, merge, publication or deployment occurred.

Next use one separate, bounded timing/CPU attribution probe under this exact fixed
schedule to distinguish reference semantic work and fresh validation from core/worker
transport and serialization. Reproduce the ordinary effect before transferring any
instrumented localization; keep both arms and every block. Hardware frequency,
cache/GC/scheduler causes are still unmeasured. No production remedy or larger Glider
matrix is justified yet. The Glider definition/search gap, idle comparison, native
allocation attribution, real repositories, long-duration memory and other platforms
remain open.

Follow-up: [reference stage/CPU and boundary attribution](reference-fixed-attribution.md)
uses fresh interleaved ordinary controls before transferring diagnostic localization.
