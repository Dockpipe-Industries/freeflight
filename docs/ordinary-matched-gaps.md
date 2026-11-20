# Ordinary matched comparisons with recorded gaps

## Scope and predefined plan

The 2026-10-23 follow-up uses the retained, qualified **ordinary** baseline94 and
JSON-copy candidate binaries and the identical frozen baseline94 Roslyn worker.
Production source remains `94eb420`; the copy candidate remains archived/unaccepted.
This follows the [instrumented pacing controls](copy-pacing-context.md), whose CPU
benefit did not establish consistent ordinary latency improvement.

The plan is recorded before collection in
`bin/.local/benchmarks/response-copies/json-moves-v2/ordinary-matched-gaps-v1/run-manifest.json`.
It comprises 16 serial processes: four chronological baseline/candidate pairs in a
source cohort and four pairs in a sham cohort whose two labels execute the same
baseline binary. Two interleaved epochs each balance baseline-first/candidate-first
pairs. Both labels have four sessions per cohort. Every session uses the same startup
configuration, the canonical synthetic 5,845-file graph, at least five seconds of
warmup and 48 measured rounds of symbols, definition, references and workspace search.

Each measured round uses a rotating Williams order. Each method appears at each of
four positions 12 times per session; each of the 12 directed within-round predecessor
pairs occurs 12 times. The minimum round period is 100 ms. Actual request-return to
next-request-start gaps, preceding method, verification duration and requested/actual
round sleeps are recorded. Verification is outside request timing and inside gaps.
No artificial per-query delay, CPU/stage probes, event listener, memory sampler or
generated worker instrumentation is used. Outer timestamps and answer verification
still have observer cost.

Every response must match the fixed exact semantic oracle, the workload assertions,
both MCP content forms and complete-result metadata. The initial four answers in
each process are checked separately. Fixture hashes, binary/worker/driver hashes and
startup configuration identity are audited. Ordinary collection does not count fresh
read bytes or recovery sweeps: those were established in earlier instrumented gates;
this run preserves their exact worker/runtime implementation and startup arguments.

The audit retains every warmup and measured sample, every chronological pair and all
positions. It reports session metrics, median paired ratios and pooled metrics as
distinct estimates. Gaps are descriptive; no gap normalization, timing exclusions,
replacement cells or post-hoc performance acceptance threshold is used. A correctness
and plan audit passing does not mean a performance candidate passed qualification.

## Replay and limits

Use perf-venv on PATH. A fresh collection label refuses overwrite; the audit performs
no semantic requests and refuses replacement of different derived data:

```sh
FREEFLIGHT_ORDINARY_LABEL=NEW_LABEL dockpipe --workflow benchmark.response.copies.ordinary
FREEFLIGHT_ORDINARY_LABEL=ordinary-matched-gaps-v1 dockpipe --workflow benchmark.response.copies.ordinary.audit
```

All raw samples, initial oracle, copied drivers, per-process configs/stderr, collection
counts and derived summaries remain under the receipt directory. This is one bounded
synthetic full-graph workload on macOS/SDK11, with four pairs per cohort. It does not
measure Glider, other platforms, real repositories, long-duration memory, allocation
stacks, GC/scheduler behavior or hardware frequency. No overall win, hardware cause,
publication or new Glider matrix follows from an unstable aggregate.

## Results

All 16 processes exited successfully. The independent audit passes **3,072 measured
+3,084 warmup +64 initial oracle =6,220 exact checked responses**. All samples remain.
This is an audit pass; the copy candidate remains unaccepted. Ratios below are
candidate-label/baseline-label; values above one mean higher latency.

| Cohort | Operation | Session median ratio | Session p90 ratio | Four paired median ratios, chronological |
| --- | --- | ---: | ---: | --- |
| sham | symbols | 0.976 | 0.976 | 0.990, 0.953, 0.931, 1.127 |
| sham | definition | 0.943 | 1.001 | 0.925, 1.101, 0.961, 0.898 |
| sham | references | 0.979 | 0.997 | 1.023, 0.823, 1.092, 0.986 |
| sham | workspaceSymbols | 1.004 | 1.018 | 0.959, 0.934, 1.037, 1.073 |
| source | symbols | 1.093 | 1.030 | 1.172, 1.080, 1.119, 1.019 |
| source | definition | 1.117 | 1.043 | 1.117, 0.998, 1.117, 1.171 |
| source | references | 1.263 | 0.963 | 1.511, 1.147, 1.144, 1.193 |
| source | workspaceSymbols | 1.015 | 0.996 | 0.972, 1.048, 0.938, 1.071 |

The source cohort has higher symbol medians in 4/4 pairs, definition medians in 3/4
and reference medians in 4/4. Search changes direction across pairs. Same-binary
paired medians also vary (for example references 0.823–1.092); these are observations
from this run, not noise bounds or a statistical significance threshold. Source
regressions justify leaving the candidate archived, without proving their mechanism.

Position evidence remains essential. Each cell below is the ratio of the medians of
the four session medians **at that position**, followed by the number of paired
comparisons with higher candidate latency. Each session contributes 12 queries/cell.

| Cohort | Operation | Position 0 ratio; higher pairs | Position 1 | Position 2 | Position 3 |
| --- | --- | --- | --- | --- | --- |
| sham | symbols | 1.004; 1/4 | 0.996; 2/4 | 1.015; 3/4 | 0.997; 1/4 |
| sham | definition | 0.992; 1/4 | 0.987; 2/4 | 0.948; 1/4 | 1.013; 4/4 |
| sham | references | 1.028; 2/4 | 1.011; 2/4 | 0.972; 0/4 | 0.974; 1/4 |
| sham | workspaceSymbols | 1.039; 2/4 | 0.984; 1/4 | 0.975; 2/4 | 1.011; 2/4 |
| source | symbols | 1.056; 4/4 | 1.050; 4/4 | 1.064; 2/4 | 1.064; 4/4 |
| source | definition | 1.057; 4/4 | 1.048; 3/4 | 1.097; 4/4 | 1.057; 4/4 |
| source | references | 0.970; 1/4 | 1.077; 3/4 | 1.136; 4/4 | 1.064; 4/4 |
| source | workspaceSymbols | 1.022; 3/4 | 0.969; 1/4 | 1.012; 3/4 | 1.012; 2/4 |

Source references improve at position 0 in 3/4 pairs, while worsening at positions
2 and 3 in 4/4 each. Their position median ratios are 0.970, 1.077, 1.136 and 1.064;
the aggregate ratio is 1.263. A median over a position mixture is nonlinear and need
not equal an average of positional median ratios. The p90 aggregate also improves
(0.963), while position p90 ratios are 0.894, 1.104, 1.307 and 1.291. These differing
summaries are retained; none substitutes for the others. Search position median
ratios straddle one (1.022, 0.969, 1.012, 1.012). No robust search win appears.

Actual gaps are recorded rather than inferred from the 100 ms round target. The
following are median-of-session-median gaps, in milliseconds, for the source cohort;
each value has a descriptive role, with no gap adjustment of query latency.

| Operation | Label | Position 0 | Position 1 | Position 2 | Position 3 |
| --- | --- | ---: | ---: | ---: | ---: |
| symbols | baseline | 75.272 | 2.614 | 0.075 | 0.154 |
| symbols | candidate | 74.062 | 2.680 | 0.077 | 0.167 |
| definition | baseline | 75.374 | 0.048 | 2.584 | 0.032 |
| definition | candidate | 75.243 | 0.051 | 2.631 | 0.036 |
| references | baseline | 79.860 | 0.043 | 0.150 | 2.599 |
| references | candidate | 79.187 | 0.048 | 0.166 | 2.662 |
| workspaceSymbols | baseline | 74.024 | 0.768 | 0.022 | 0.036 |
| workspaceSymbols | candidate | 73.775 | 0.772 | 0.023 | 0.037 |

Round-boundary gaps differ strongly from within-round gaps. Search verification
costs roughly 2.4–2.6 ms per response across these sessions and is outside measured
service latency but inside the next gap; small targeted responses verify much faster.
Every session, pair and position also retains p90/mean latency, gaps and verification
metrics in `result.json`. Warmups, round sleeps and preceding methods remain in
`samples.json`. These controls expose the observed context; they do not isolate
worker CPU, GC, scheduler or frequency causality.

## Decision and next step

Keep production exact `94eb420` and the JSON-copy candidate archived/unaccepted.
This ordinary follow-up confirms the candidate has no reproducible overall win in
this workload. Do not repeat it unchanged or expand it into a Glider matrix.
For further optimization, first isolate the baseline reference position/preceding-
operation sensitivity with a narrowly predefined within-process control, keeping
the fresh-validation/security/recovery contracts. A different response design needs
a new mechanism and ordinary screening across all operations. The existing definition/
search gap against Glider, Glider idle accounting, native allocation attribution, real
repositories, long-duration memory and other platforms remain open. No source change,
commit, publication, merge or deployment was made.

Follow-up: [baseline reference position and predecessor control](reference-position-context.md)
uses complete-order blocks and retains each matched pacing-policy pair.
