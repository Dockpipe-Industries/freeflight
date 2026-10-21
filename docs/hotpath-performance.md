# Warm C# hot-path investigation (unreleased)

The experimental runtime optimization described here was subsequently reverted.
The functional trusted-loading, configuration and outline repairs remain. Original
receipts and the experimental-only patch are retained; see disposition below.

This investigation compares a same-source macOS ARM64 rebuild of published
`57851e334bad0c7f264999a5d6e0454d16284681` with the experimental local changes at measurement time.
It is not a Linux binary measurement, competitor benchmark or private-project
result. No source-specific tuning is used.

Local-only diagnostic tooling adds an opt-in complete-bundle mode to the existing
DockPipe `benchmark` workflow. That tooling is excluded from the functional repair
commit; the following invocation describes the preserved local experiment. Set `FREEFLIGHT_HOTPATH_BASELINE_BUNDLE` and
`FREEFLIGHT_HOTPATH_CANDIDATE_BUNDLE` to extracted bundle directories, then run
`dockpipe --workflow benchmark`. The default benchmark and previous comparison
mode remain unchanged. Both complete bundles must be built and qualified first.
The driver asserts declaration positions, exact definition/reference results,
next-request file addition/removal and changed-document freshness.

For diagnosis on macOS ARM64, set `FREEFLIGHT_HOTPATH_PROFILE_SOURCE` to the
pinned source tree instead of the candidate bundle. The same workflow copies the
baseline bundle and Roslyn sources into generated output, instruments the copy,
and builds an instrumented self-contained worker with the installed SDK. Production source/binaries are
not modified. Stopwatch stages measure refresh, total engine invocation and
worker serialization/output; the residual full-MCP time includes core routing,
IPC, client framing and instrumentation overhead, not separately identified
network latency. Profiling copies are diagnostic evidence, not production timing
comparisons.

## Initial profile

The controlled fixture contains 514 C# files in 16 nested directory groups,
including an arithmetic declaration and 12 exact call sites. After three warmups,
20 sequential samples of each operation ran through the native core and bundled
worker. A private instrumented copy of source `57851e3` showed:

| Operation | Full MCP median | Refresh median | Semantic work median | Worker reply median |
| --- | ---: | ---: | ---: | ---: |
| Outline | 6.290 ms | 6.108 ms | 0.054 ms | 0.008 ms |
| Definition | 6.317 ms | 6.156 ms | 0.070 ms | 0.006 ms |
| References | 6.908 ms | 6.028 ms | 0.791 ms | 0.013 ms |

Stage and end-to-end medians are independently computed; they need not sum
exactly. The remaining approximately 0.12–0.15 ms includes the C++/IPC/client
round trip and profiling overhead. Refresh dominates this many-file workload.
Inspection identifies repeated ancestor validation and metadata queries for each
file within the same refresh as a bounded optimization opportunity. Directory
membership must still be enumerated every request, target contents reread, and
path checks performed afresh; this is not evidence for a cross-request trust or
membership cache.

Raw profile: `bin/.local/benchmarks/hotpath-profile-bc3t38ea/profile.json`.
The baseline was extracted with `git archive` into `bin/.local/baseline-578`;
its native core, workers and `package.native` passed. Its broader `build` wrapper
then failed the unrelated website step because the isolated tree had no Qt kit;
no website result is claimed for the benchmark baseline.

## Qualified bundle comparison

Two fresh sessions per version ran in alternating order (baseline, candidate,
candidate, baseline), with three warmups and 20 measured requests per operation
per session. Each session passed exact declaration/definition/reference checks,
next-query file addition/removal, changed-target freshness and replacement of a
previously traversed ancestor with an escaping symlink between requests.

| Operation | Baseline median | Candidate median | Median reduction | Baseline p90 | Candidate p90 |
| --- | ---: | ---: | ---: | ---: | ---: |
| Outline | 6.050 ms | 3.878 ms | 35.9% | 6.576 ms | 8.667 ms |
| Definition | 6.024 ms | 3.821 ms | 36.6% | 6.480 ms | 8.691 ms |
| References | 6.897 ms | 4.578 ms | 33.6% | 7.489 ms | 9.524 ms |

Medians pool all 40 samples; p90 uses nearest rank. The candidate improves the
median, but its later samples have a pronounced slower mode. Tail latency did
not uniformly improve. This is a small synthetic workload, not evidence of a
general performance guarantee. No samples were removed.

The scoped change shares ancestor validation only within one Refresh call. It
still checks leaves, enumerates membership on every query, and fully validates
ancestors immediately before reading contents. It introduces no cross-request
path authorization or membership cache.

| Fresh-process observation | Baseline runs | Candidate runs |
| --- | --- | --- |
| Core startup/discovery | 123.939 / 2.666 ms | 48.424 / 2.439 ms |
| First outline (includes lazy worker load) | 858.256 / 392.685 ms | 848.897 / 394.836 ms |
| First definition after outline | 58.551 / 60.926 ms | 56.364 / 59.424 ms |
| First references after definition | 233.429 / 112.530 ms | 193.595 / 110.942 ms |
| Steady process-tree RSS | 268688 / 269312 KiB | 269296 / 269312 KiB |
| Sampled peak process-tree RSS | 268736 / 270256 KiB | 269296 / 269312 KiB |

Cold/startup observations vary substantially with warmed system state; no startup
improvement is established. Steady RSS differs by about 304 KiB when taking the
median of the two runs, effectively unchanged at this sampling resolution. RSS
is captured before the mutation/security checks to avoid recovery skew.

Candidate private-copy instrumentation retained the bimodal behavior: first
eight measured rounds spent approximately 3.7 ms in Refresh, later rounds about
8.3 ms. All 20 samples give Refresh medians of 8.323/8.364/8.345 ms for
outline/definition/references, while semantic medians remain
0.058/0.078/0.760 ms and replies 0.008/0.006/0.010 ms. This still identifies
Refresh as dominant, but does **not** establish a sustained Refresh improvement.
The reason for the mode transition is unresolved; further profiling should
precede additional optimization.

## Targeted tail investigation

A further private-copy diagnostic records each Refresh start timestamp,
enumeration time, bytes-read and snapshot-reuse deltas, and GC collection deltas.
It did not reproduce the sustained slow mode: all 60 measured Refresh calls
finished within approximately 889 ms of the initial Refresh, reused 513 files,
and read only the direct target (104 or 642 bytes). Enumeration was typically
2.25–2.5 ms of approximately 3.7–4.1 ms total. Periodic generation-zero collections
usually added about 0.2 ms. This run provides no evidence of five-second expiry or
GC causing the earlier sustained penalty. Added instrumentation changes execution
and compilation behavior; this successful run does not erase the original tails.

The first attempted tiering control used an environment variable that the core
correctly strips from child processes. Receipt `hotpath-profile-fh7w65oe` is
**invalid as a tiering-disabled control** and is retained as such. A corrected
control changed `System.Runtime.TieredCompilation` only in the generated private
worker's runtime configuration. Its Refresh medians were
3.607/3.617/3.589 ms (outline/definition/references), with 513 reused files and
only direct-target bytes read. First outline was 1241 ms, versus 889 ms in the
preceding default-tiering diagnostic; disabling tiering is not proposed as a
production fix. Both default and disabled-tiering diagnostics lacked the
sustained transition, so they cannot establish tiered compilation as its cause.

All diagnostic sessions passed the same correctness and security guards.
The defensible conclusion remains: the bounded optimization improves the original
comparison's median, while its p90 regression is unresolved. Do not promote it as
a uniformly faster path or treat this performance acceptance item as complete.
The original uninstrumented comparison is the authoritative result; diagnostic
runs are not replacements. No production runtime configuration was changed.

Diagnostic receipts:
`bin/.local/benchmarks/hotpath-profile-9a47cgra/profile.json` (default),
`bin/.local/benchmarks/hotpath-profile-fh7w65oe/profile.json` (invalid control),
`bin/.local/benchmarks/hotpath-profile-n7c1bbmb/profile.json` (corrected control).
To reproduce the corrected private-copy control, add
`FREEFLIGHT_HOTPATH_DISABLE_TIERING=1` to the profiling invocation.

## Evidence and provenance

- Comparison receipt: `bin/.local/benchmarks/hotpath-668i_r7b/results.json`.
- Candidate profile: `bin/.local/benchmarks/hotpath-profile-xxv8i2aw/profile.json`.
- Baseline archive SHA-256: `3d0db1b83af20443aaa763d7690a533c3c5cadde0fb87e5a83698fcbb3a561f6`.
- Candidate archive SHA-256: `a63e9f15abb367b60d22c80bbefbdd19e4b44ac7420c1c21579e1577c7450dd5`.
- Candidate core SHA-256: `4e8f57d9bbe9f9bbbf530e0cbcdb83ef5b2dcf1ed6531502cc9267f50289b0f4`.
- Candidate Roslyn DLL SHA-256: `b42dd2010a4a48f48a10f5c122e1e34590714b90add065f55dd5476a5e8fbb40`.

The baseline source receipt at
`bin/.local/baseline-578/bin/.local/baseline-source-verification.json` verifies
all 195 archived source blobs against the pinned commit. Its packaging helper
observed the parent checkout's dirty status because the archive has no `.git`;
that embedded dirty flag is not evidence of modified baseline source. The
external source receipt is authoritative for this local rebuild. Generated raw
evidence stays outside tracked source; it has not been published.

Fresh processes do not imply cold OS caches. The RSS monitor samples process-tree
RSS at approximately 100 ms and may miss peaks or double-count shared pages.


## Disposition: experimental optimization reverted

The original uninstrumented comparison contains 20 warm samples per operation per
session, two sessions per version: 40 samples per operation per version (240 timed
requests total). The pooled nearest-rank p90 regressions were:

| Operation | Baseline p90 | Experimental p90 | Increase | Relative increase |
| --- | ---: | ---: | ---: | ---: |
| Outline | 6.576 ms | 8.667 ms | 2.091 ms | 31.8% |
| Definition | 6.480 ms | 8.691 ms | 2.211 ms | 34.1% |
| References | 7.489 ms | 9.524 ms | 2.035 ms | 27.2% |

Both experimental sessions had higher per-session p90 than either baseline session
for each operation. This is an observed regression in this bounded experiment,
not merely a conjecture from one outlier. However, sequential requests are
correlated, only two process sessions per version were measured, and diagnostic
runs did not consistently reproduce the transition. These data do not establish
a population-level effect, a statistical confidence interval or a root cause.
Do not treat the 40 requests as 40 independent experiments.

Traces place the sustained added time inside Refresh, with small semantic and
serialization costs. Repeated traversal/path validation is the principal measured
cost; why its execution entered a slower mode remains unknown. Counter diagnostics
exclude five-second expiry for those diagnostic runs and show small GC pauses,
but they cannot explain an earlier run that lacked those counters. Tiered-JIT and
allocation explanations remain hypotheses. There is no evidence-backed corrective
optimization to ship from this experiment.

Accordingly, only the experimental `Refresh`/`CheckPath` changes were removed;
those methods now match pinned 57851e3 exactly. All trusted-loader, per-root trust,
reload/status and document-outline fixes are retained. The isolated experimental
patch is saved at `bin/.local/experimental-hotpath-only.patch`; original receipts
and artifacts remain unchanged. Existing benchmark tooling is retained for future
controlled work. There is no retained-runtime 34–37% speedup claim. Post-revert
correctness qualification is recorded separately in the task log and receipt;
no favorable rerun replaces the original timing evidence.

## RC2 trusted graph follow-up

The [2026-10-21 M6 investigation](rc2-warm-refresh-investigation.md) confirms
whole-graph path validation before snapshot reuse in the RC2 trusted path and
explains why the core's cached capability counters remain zero. A separate narrow
leaf-metadata experiment passed native correctness checks and improved pooled
medians, but one process session regressed p90; its runtime change was removed.
The report retains all session timings, private profiles, limitations and the
experimental patch location. No production speedup is claimed.
