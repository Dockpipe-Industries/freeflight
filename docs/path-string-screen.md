# Repeated path construction screen, 2026-10-22

The lexical-only candidate reduces successful-sweep allocation but is rejected on
latency evidence. Production worker source is restored exactly to performance
candidate `94eb4207c8ffd2d5544bca8a52dcb8d451285015`; the preserved worktree remains
`investigate/rc2-warm-refresh`. No reset, replacement from js/dev, commit, publication,
push, merge or deployment occurred. Main js/dev and unrelated local work are untouched.

## Candidate and preserved state

The candidate records immutable parent-path strings only for exact canonical files
already admitted by trusted open. Parent arrays are shared by files in the same
directory. Every validation still invokes fresh `File.GetAttributes` on every parent
and the leaf in the original order. Relative paths, alternate spellings, unknown keys,
external compiler inputs and safe-source mode retain the original checker. The
catalogue clears on reopen and requests cannot add entries. First full validation
and existing graph resource bounds precede construction. No stat result, file content,
semantic result, deadline or authorization is reused. Background descriptor opening,
strict defaults, transaction publication and recovery scheduling are unchanged.

The first implementation has graph-count/path-length bounds rather than a separate
byte budget for retained strings. Startup/long-path catalogue memory and cancellation
cost would require further qualification if reconsidered. The short RSS observations
below are not a bound or measured peak.

Starting tracked state and worker source are preserved under
`bin/.local/perf-preservation/20261022-path-strings-start`. Rejected source, patch and
decision live under `20261022-path-strings-rejected`. Complete frozen baseline/candidate
source, exact SDK/flags, driver snapshots, qualification logs and raw samples remain
under `bin/.local/benchmarks/trusted/path-strings-screen-v1`.

Candidate Program.cs SHA-256: `ed7fdd5f9c5d130c6d29ae26751049ae0238965137af7e6371cb8813ba69c311`.

## Fresh validation and semantic gates

Existing worker, trusted/external-input, mutation, Darwin metadata/handle/expiry,
sixteen incremental fault cases, background recovery and five failed-refresh rollback
cases per variant pass. These include fresh target reads, lost same-size/restored-mtime
edits, watcher failure/overflow, ancestor replacement, cancellation and resource accounting.

The generated `lexical-proof` compares the new canonical-key route with the unchanged
three-argument uncached checker. Twelve cases pass with identical result/exception and
fresh attribute-call order: repeated canonical reads, shared parents, relative and
alternate spellings, escape, unknown/missing leaf, leaf symlink, regular replacement,
ancestor symlink and restoration. The proof also verifies shared parent arrays and
that arbitrary requests do not grow the table. This is a generated probe, not a test
hook in shipping source.

All twelve semantic operations pass 960 measured exact-result comparisons against
the frozen baseline. Existing worker tests separately supply positive advanced-operation
oracles. Rename remains a preview; complete fixture hashes are unchanged after timing.
No baseline result or failed sample was dropped.

Actual gate-handoff EOF shutdown passes, including foreground ownership, uncancellable
maintenance reacquisition and join before disposal: 35.079 ms. Five-second fallback
passes while maintenance is suspended at age 4505 ms; an ordinary query at age
6021 ms recovers the suppressed same-size/restored-timestamp edit and rejects the
older prepared sweep. No forced deadline or rename triggers this fallback test.

## Four-operation matched screen

Both source variants enable incremental validation and background recovery. Two
sessions per variant/size alternate baseline/candidate process order, with five-second
warmup, twenty measured rounds, 100 ms round cadence, C5 search, 4096-byte source
padding and fourteen callers. Eight ordinary and four separate diagnostic processes
pass. There are 640 ordinary measured semantic checks and 320 diagnostic checks,
excluding warmup and expiry. Fixed operation order and small session/sample counts
limit inference. This is direct-worker screening, not MCP or Glider timing.

Ratios below are candidate/baseline, based on the median of session metrics. Lower
is faster; every raw session, maximum and outlier remains.

| Files | Operation | Median ratio | p90 ratio |
| ---: | --- | ---: | ---: |
| 433 | symbols | 0.989 | 0.989 |
| 433 | definition | 0.942 | 0.967 |
| 433 | references | 1.010 | 0.914 |
| 433 | workspaceSymbols | 0.974 | 1.065 |
| 5845 | symbols | 1.001 | 0.970 |
| 5845 | definition | 0.967 | 0.998 |
| 5845 | references | 0.882 | 0.768 |
| 5845 | workspaceSymbols | 0.917 | 1.022 |

Reference p90 improves 23.2% on the full graph, but search p90 worsens 2.2% full-graph
and 6.5% small-graph (both small candidate sessions unfavorable). Definition is nearly
flat at full-graph p90. These mixed results do not establish an overall gain.

## All twelve operation screen

Two sessions per variant/size alternate baseline/candidate process order. Each fresh
worker warms for at least five seconds, then runs ten rotating-order rounds over all
twelve operations, with a minimum 100 ms round period. All eight processes pass all
960 measured responses. Full JSON is compared with the first baseline oracle for that
fixture; every session also validates the existing four-operation exact oracle.

Rename forces full fresh validation, intentionally changing the recovery/workload
context for following operations. These measurements must not be pooled with the
four-operation screen. Ten measured observations per operation/session give limited
tail resolution and do not prove that string reuse caused each timing change.

| Operation | 433 median ratio | 433 p90 ratio | 5845 median ratio | 5845 p90 ratio |
| --- | ---: | ---: | ---: | ---: |
| symbols | 1.080 | 0.809 | 1.029 | 1.028 |
| definition | 1.147 | 1.067 | 1.082 | 1.087 |
| references | 1.080 | 1.398 | 1.018 | 0.992 |
| workspaceSymbols | 1.052 | 2.472 | 0.976 | 0.927 |
| hover | 1.013 | 1.647 | 1.016 | 0.890 |
| diagnostics | 1.069 | 1.210 | 1.015 | 1.090 |
| rename | 1.025 | 1.210 | 0.982 | 0.997 |
| implementations | 1.183 | 1.359 | 1.048 | 1.111 |
| typeInfo | 1.033 | 0.889 | 0.997 | 1.065 |
| signatureHelp | 1.064 | 1.117 | 1.050 | 1.149 |
| callHierarchy | 0.963 | 0.892 | 1.068 | 1.009 |
| typeHierarchy | 1.136 | 1.258 | 1.063 | 1.089 |

Several operations have unfavorable ratios across this distinct workload. Full-graph
definition p90 is +8.7%, diagnostics +9.0%, implementations +11.1% and signature help
+14.9%; small-graph search has particularly unstable unfavorable tails. The evidence
is insufficient for acceptance, even though correctness and fresh validation pass.
A larger competitor matrix is not justified for this rejected candidate.

## Successful-sweep idle costs

`idle-path-cost-v1` uses the frozen candidate for two alternating foreground-only/
background process pairs, eight-second warmup and two 5.2-second windows per process.
All eight windows pass. Each background window requires successful completions,
matching full-recovery publication and exact all-file byte/read counts. Six sweeps
complete; all idle-window failure/abort deltas are zero.

| Metric | Frozen path-string candidate |
| --- | ---: |
| Allocated MB/sweep | 41.480 |
| Process CPU ms/sweep | 197.230 |
| Observed one-core CPU % | 5.680 |
| GC pause ms/sweep | 3.609 |
| Sampled background RSS MB | 363.9–365.3 |

Allocation is 28.0% below the earlier qualified 94eb420 observation (57.642 MB/sweep).
This is a descriptive comparison across separate runs, not a matched statistical
source-version cost comparison. Each individual idle run matches maintenance off/on
for its own frozen source. CPU stays near 200 ms/sweep. The allocation reduction
supports the stack diagnosis but does not override latency regressions. Long-duration
RSS, peak memory, real-repository and cross-platform costs remain unqualified.

## State, next step and replay

Production remains the stronger cooperative 94eb420 candidate. Diagnostic workflow,
proof, profiling support and evidence changes remain uncommitted. The latest accepted
competitor comparison is unchanged; there is still no reproducible overall win over
Glider. Previous negative experiments/receipts remain intact.

The remaining large path/attribute cost includes fresh FileInfo/attribute work, which
this string-only candidate retains. Next investigate allocation-free fresh attribute
validation or descriptor-backed admission, with the same containment, symlink,
regular-file, cancellation and recovery guarantees. A new design needs a fresh narrow
all-operation screen; do not repeat this rejected implementation or reinstate buffer
reuse without new evidence. No query cache or validation weakening is justified.

Use the existing perf-venv and pinned dotnet11 PATH. To reproduce the extra proofs
against a newly frozen receipt:

```sh
FREEFLIGHT_PATH_RECEIPT=NEW_RECEIPT dockpipe --workflow benchmark.recovery.paths
FREEFLIGHT_BACKGROUND_RECEIPT=NEW_RECEIPT FREEFLIGHT_BACKGROUND_IDLE_LABEL=idle-path-cost-repeat FREEFLIGHT_BACKGROUND_IDLE_SESSIONS=2 dockpipe --workflow benchmark.recovery.background.idle
FREEFLIGHT_BACKGROUND_RECEIPT=NEW_RECEIPT FREEFLIGHT_BACKGROUND_GAP_LABEL=handoff-fallback-repeat dockpipe --workflow benchmark.recovery.background.gaps
```

First replay the retained `benchmark.trusted` provenance with a fresh label, baseline
94eb420 and the archived candidate source; both variants need incremental/background
flags. All workflows refuse existing output labels. No generated builds or sources
are installed into the application or published.
