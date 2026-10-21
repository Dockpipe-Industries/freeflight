# RC2 residual trusted-refresh investigation

This follows the shipped `39c3cc83b04f21e352e7885c0589d39947b9efa4` optimization.
The operator's Linux retest reports about 24 ms outlines and 6,741 lstat calls,
versus about 49 ms and 31,015 calls previously. Those are supplied Linux/Biztraak
results, not measurements made on this M6. The Linux `/tmp` receipts were not
accessed. No Glider comparison was rerun here.

## Reproducible experiment

The [trusted workflow](trusted-performance-workflow.md) replaces the previous
one-off drivers with DockPipe preparation, qualification, measurement and summary
steps. The original rejected experiments and receipts remain under their previous
`bin/.local/perf*` directories. New runs use immutable labels under
`bin/.local/benchmarks/trusted`. Ordinary Release builds and separate diagnostic
copies use the pinned RC2 SDK. They are SDK-hosted worker measurements, not
self-contained package or full MCP measurements.

An initial identical-source control (`residual-baseline`) completed all four steps.
Source hashes matched exactly. Its small-graph baseline-labelled outline session
medians were 1.14, 3.42 and 3.46 ms; candidate-labelled medians were 1.21, 1.04 and
1.06 ms. This is evidence of noise/runtime state, not an optimization. Full-graph
control medians were 14.00, 14.64 and 17.15 ms versus 15.11, 15.33 and 15.75 ms.
The control used two seconds minimum warmup; subsequent comparisons use five.
No unfavorable session was discarded.

The first full-graph diagnostic control had approximate outline medians of 14.16
ms Refresh, 11.25 ms admission, 10.63 ms path checks (including 7.06 ms fresh
attributes), 1.18 ms collection preparation, 0.55 ms apply/rebuild and 0.09 ms
read/hash/decode. These nested stages cannot be added. Process-wide diagnostic
allocation median was 11.23 MB and GC pause median 0.78 ms. Instrumentation adds
work and allocations, so these are attribution measurements, not ordinary timing.
The CLR listener records JIT and GC events; event delivery is asynchronous and
counts do not establish exact causal attribution or thread scheduling.

## Source-confirmed opportunity and bounded candidate

`SourceEngine.Invoke` always calls `Refresh` before semantic queries. In the
shipped implementation, trusted Refresh copies and sorts all document keys,
clones three dictionaries, builds a membership set, validates every path and leaf,
and clears/repopulates all three dictionaries even when only one target is read.
`CheckPath` normalizes, relativizes, splits and reconstructs paths for each leaf.
`SemanticQueries.WorkspaceSymbols` then performs its source declaration search;
that cost is separate from the common refresh floor.

The candidate changes two measured costs:

1. `CheckSnapshotPath` receives only canonical workspace keys admitted by trusted
   open. It checks each parent once in the existing request-local ancestor set,
   and checks each leaf's fresh FileInfo attributes. It avoids repeating lexical
   normalization/reconstruction for every already-admitted document. No filesystem
   authority is retained across requests. External inputs bypass this helper;
   fresh content reads still use full uncached `CheckPath` immediately before open.
2. Trusted membership is fixed until reopen, so Refresh stages snapshot/hash deltas
   and commits them only after complete admission and successful Roslyn application.
   It avoids the membership/removal pass and complete dictionary rebuilds. Safe
   source mode retains its reconciliation copies. The immutable Roslyn solution is
   applied only when changed; cancellation is checked immediately before commit.

The target is still read every time. Five-second expiry, watcher generations,
resource accounting, external contexts/read-only handling and rename hashes retain
their existing paths. Failure must preserve the solution and committed dictionaries;
observational read/reuse counters and asynchronous watcher notifications may advance.
Portable checks remain subject to the previously documented concurrent-hostile
filesystem race limitation; this is not an atomic filesystem sandbox.

Even if bookkeeping vanished entirely, fresh leaf/ancestor attributes still impose
an O(files + unique ancestors) admission cost under this safety contract. This
candidate does not promise Glider's tiny-operation latency or replace validation
with watcher-only authority.

## Qualification and remaining limits

The first complete candidate comparison (`residual-candidate-v2`) passed all
ordinary and diagnostic semantic checks, plus native and mutation qualification.
The focused `benchmark.trusted.transaction` run then passed three failed-refresh
state-preservation cases per variant against the exact measured snapshots.

Full-graph ordinary results (three fresh sessions per variant, 20 measured rounds
per session, five seconds minimum warmup; milliseconds):

| Operation | Baseline session medians | Candidate session medians | Baseline p90 range | Candidate p90 range |
| --- | --- | --- | --- | --- |
| Outline | 12.920, 13.416, 12.684 | 8.396, 8.565, 8.497 | 13.559–14.273 | 8.806–9.175 |
| Definition | 12.44, 12.99, 12.35 | 8.36, 8.25, 8.21 | 13.04–14.85 | 8.41–8.63 |
| References | 12.99, 13.61, 12.71 | 8.68, 8.51, 8.64 | 13.21–15.66 | 8.92–9.11 |
| Symbol search | 14.56, 15.18, 14.14 | 9.94, 10.00, 10.29 | 15.28–18.13 | 10.33–10.96 |

The search checks the exact set of generated `C58` substring declarations. This is
not equivalent to the operator's broad Biztraak search workload. The small-graph
outline p90 sessions were 0.871, 0.836, 0.855 ms for baseline and 0.947, 1.061,
0.591 ms for candidate: two unfavorable candidate sessions remain visible. Other
small-graph operations also have individual unfavorable sessions in summary.json.

Separate full-graph diagnostic outline medians:

| Stage/metric | Baseline | Candidate |
| --- | ---: | ---: |
| Refresh | 13.336 ms | 9.061 ms |
| Admission, including attributes | 10.614 ms | 7.450 ms |
| Fresh attributes | 6.557 ms | 5.917 ms |
| Sort/collection preparation | 1.079 ms | 0.617 ms |
| Apply/rebuild | 0.554 ms | 0.001 ms |
| Read/hash/decode | 0.071 ms | 0.067 ms |
| Process allocation delta | 11,371,568 bytes | 3,490,992 bytes |
| GC pause delta | 0.647 ms | 0 ms |
| Managed attributes | 5,910 | 5,910 |
| Target bytes read | 60 | 60 |

These are managed call counts, not Linux/macOS kernel syscall traces. Both versions
reused 5,844 snapshots in ordinary diagnostic outlines. JIT-start events remained
observable during the measured outline windows (72 baseline, 136 candidate across
20 samples); five seconds of warmup does not prove the runtime has stopped JITting.
Per-sample event and GC data are retained in `tails.json` and profile stderr. The
asynchronous event counts are observations, not a causal explanation of each tail.

Expiry remains a separate cost. After 5.1 seconds idle, ordinary full-graph outline
samples were 186.854, 181.821, 181.382 ms baseline and 197.011, 180.734, 183.387 ms
candidate. One candidate was slower than every baseline sample. Diagnostic expiry
read all 5,845 files (383,568 bytes), with 91.07 MB versus 84.06 MB allocation and
170.09 versus 171.78 ms Refresh. No expiry improvement is claimed. The failed first
candidate profile preparation (`residual-candidate`) is retained: an ambiguous
instrumentation anchor caused a deliberate failure before measurements. No timing
from that attempt is used. The corrected adapter uses a unique anchor.

No new branch was pushed, no PR was merged, and staging/master/deployment/active
MCP configuration remained unchanged during this investigation. Hosted Linux/Windows,
self-contained package, full MCP IPC and real-solution comparisons remain separate
qualification obligations. The earlier small-graph p90 regression remains part of
the historical record; it is not erased by subsequent comparisons.

## Final workflow repeat

`residual-repeat` completed the final five-stage workflow, including integrated
transaction guards, from preparation through automatic summary. All 960 ordinary
measured responses and 320 diagnostic measured responses passed, as did warmup and
post-idle checks. The first comparison has another 960 ordinary and 320 diagnostic
measured passes; these datasets are kept separate rather than pooled for a win.

Repeat full-graph outline session medians were 12.764, 12.696, 12.581 ms baseline
and 8.813, 8.866, 8.617 ms candidate; p90 ranges were 13.086–13.439 and
9.047–9.249 ms respectively. Full-graph definition/reference/search p90 also
improved in every candidate session. The largest ordinary outline samples were
23.274 ms baseline and 9.611 ms candidate. All raw maxima remain in receipts.
Small-graph references still had unfavorable candidate p90 sessions (1.429 and
1.400 ms versus baseline 1.368, 1.489, 1.340 ms); the descriptive ratio of session
p90 medians is 1.024. This is not a universal tail-latency win.

Repeat post-idle full-graph outlines were 184.715, 169.486, 184.284 ms baseline and
181.411, 178.366, 177.444 ms candidate. These few expiry observations do not establish
a performance improvement, and do not replace the slower candidate observation in
the first comparison. Failed preparation, identical-source noise, all warmups and
both comparison sets are retained. No hard statistical threshold is asserted.

Both workflow YAML files passed `dockpipe workflow validate`. Repository health
uses the existing task-local Python/PyYAML environment. The final candidate remains
local and unpromoted; the only completed platform execution here is M6/macOS ARM64.
