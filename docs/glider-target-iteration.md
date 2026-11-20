# Glider-target iteration: retained local experiment

This investigation starts from shipped `97c1342d9234` and the M6 product comparison
in [the head-to-head report](glider-head-to-head.md). It does not alter published
artifacts, active configuration or the freshness/security contract.

## Source-attributed costs and candidate

`SourceEngine.Invoke` always calls `Refresh` before semantic work. `Refresh` visits
every admitted graph member; `CheckSnapshotPath` refreshes every leaf's FileInfo
metadata, even when the content snapshot remains reusable. Ancestors are shared
only within that request. The subsequent read path still validates without that
ancestor set. Dictionary deltas and the solution commit happen after all admission
and reads succeed. None of those rules changes in this experiment.

The retained `sprint-winner-shipped/5845-profile-1-candidate.stderr` diagnostics
preceded this iteration and measured the same selected serial implementation.
For its last 100 target-only outlines, median admission was 9.546 ms, metadata
refresh 7.156 ms, total refresh 10.439 ms and semantic work 0.022 ms. Stages nest;
these cannot be added. The one full-expiry outline spent 189.545 ms in Invoke,
allocated 47,976,688 bytes and completed 11,710 pool items. This is diagnostic
SDK-hosted synthetic evidence, not packaged production latency or Linux evidence.

The candidate reuses MemoryStream scratch storage and the incremental SHA256
object within one refresh, resetting each between files, and disables FileStream's
additional buffer. The 8 KiB asynchronous read loop, cancellation tokens, bounded
byte accounting, exact hashes, uncached path checks and transactional commit remain.
SourceText consumes a changed input before scratch storage is reset. Buffers never
become cross-request authority and no source file is omitted.

The new paced worker comparison `glider-target-scratch` passed both existing suites,
mutation qualification and five failed-refresh transaction guards per variant.
All 4,800 ordinary and 1,600 diagnostic measured responses passed. On the full-graph
expiry diagnostic, allocations fell from 47,983,288 to 21,704,040 bytes; CPU from
487.665 to 451.633 ms and recorded GC pause from 2.749 to 1.171 ms. These are one
instrumented expiry sample per variant, not repeated production percentiles.
Ordinary medians and p90s were mixed, roughly within 1–2%; this is not a latency win.
All raw samples, maximum values and unfavorable sessions remain retained.

The final summary guard rejected a changed `glider.py` hash after measurements:
the optional candidate adapter had been edited while the frozen worker run was
active. Summary recovery restored the recorded driver set and SDK, then regenerated
only summaries from completed raw samples. No measurements were rerun or replaced.
The initial recovery missing SDK PATH and the guard failure remain in separate logs.

## Boundaries on the next design

The current portable path has O(N) fresh leaf validations per query and O(total
source bytes) rereading when all snapshots expire. Reducing scratch allocations
cannot eliminate those costs. This is a complexity constraint, not proof of a
universal millisecond lower bound or impossibility of a better implementation.

Possible future approaches require different proofs:

- A platform-native bulk metadata reader could preserve fresh admission while
  reducing syscall count. It must handle symlinks, ancestor replacement, exact
  membership, external inputs, ordering of failures and cancellation, and bound
  unrelated directory enumeration. No such backend is implemented or qualified.
- Background content revalidation could spread expiry reads, but would consume
  idle CPU/I/O and need explicit synchronization, cancellation, disposal and
  resource-budget proofs. It would not by itself remove per-query leaf admission.
- Watcher-only unchanged-query admission, a longer freshness interval or limiting
  validation to the query target changes the current contract. Those changes are
  not authorized as hidden optimizations and are not present here.

A synchronous-read experiment was considered because the diagnostic showed many
pool items. The installed runtime records commit
`820230c386db5b0106c5430b3e5aee92a7826bf5`; its public source URLs returned 404.
Current [.NET source](https://github.com/dotnet/runtime/blob/main/src/libraries/System.Private.CoreLib/src/Microsoft/Win32/SafeHandles/SafeFileHandle.ThreadPoolValueTaskSource.cs)
shows a queued synchronous read with a pre-operation cancellation check, but that
is not sufficient evidence for the exact installed build or every platform.
No synchronous-read candidate was adopted, and cancellation remains unchanged.

## Native three-product qualification

The optional adapter locally publishes the frozen candidate worker and uses the
unchanged published core. Both native suites run before timing. The first preparation
failed because the frozen source lacked its disposable `bin/.local` test directory;
no timing sessions started. `target-scratch-2` retains the corrected run separately.
It uses three fresh sessions per product/graph/cadence, ten seconds warmup and fifty
measured four-operation rounds, with identical fixtures and rotated product order.
The completed result follows.

## Completed result: candidate rejected for latency

All 36 native sessions completed; all 7,200 measured semantic checks, warmup and
144 post-idle responses passed. Both native security/semantic suites passed.
The native CoreCLR, System.Private.CoreLib and Microsoft.CodeAnalysis binaries
are byte-identical to those in the shipped bundle. This controls runtime packaging
without claiming platform qualification beyond this M6.

The allocation reduction is reproducible diagnostic evidence, but does not yield
a robust latency improvement. Full-graph unpaced p90 regresses for all operations;
paced search median/p90 regress, and outline maximum increases from 106.877 to
149.169 ms. The median first post-idle outline improves only from 179.195 to
174.998 ms across six samples with overlapping ranges. No Glider-target winner
is selected. The tracked runtime is restored to shipped source; the candidate is
preserved in the rejected patch and frozen source receipts.

### Unpaced

Cells: median of session medians / median of session p90s / maximum across sessions,
in milliseconds. Three fresh sessions per cell, not pooled percentiles.

| Files | Operation | Shipped | Candidate | Glider 13.3.0 |
| --- | --- | --- | --- | --- |
| 433 | Outline | 0.564 / 0.572 / 0.585 | 0.566 / 0.578 / 0.619 | 0.140 / 0.200 / 0.229 |
| 433 | Definition | 0.545 / 0.552 / 0.562 | 0.545 / 0.554 / 0.698 | 0.056 / 0.123 / 0.131 |
| 433 | References | 0.910 / 0.956 / 1.309 | 0.910 / 0.947 / 1.464 | 0.468 / 0.543 / 1.577 |
| 433 | Broad search | 0.644 / 0.655 / 0.920 | 0.653 / 0.660 / 0.959 | 0.445 / 0.466 / 0.632 |
| 5845 | Outline | 7.079 / 7.482 / 8.676 | 7.139 / 7.809 / 10.241 | 0.165 / 0.182 / 2.248 |
| 5845 | Definition | 6.071 / 6.287 / 7.343 | 6.140 / 6.467 / 10.394 | 0.066 / 0.092 / 0.207 |
| 5845 | References | 6.399 / 6.536 / 7.139 | 6.426 / 6.972 / 9.252 | 0.563 / 0.616 / 1.502 |
| 5845 | Broad search | 14.113 / 14.615 / 17.476 | 14.316 / 14.847 / 21.665 | 7.206 / 7.478 / 11.776 |

### Paced: minimum 100 ms per four-operation round

Cells: median of session medians / median of session p90s / maximum across sessions,
in milliseconds. Three fresh sessions per cell, not pooled percentiles.

| Files | Operation | Shipped | Candidate | Glider 13.3.0 |
| --- | --- | --- | --- | --- |
| 433 | Outline | 4.029 / 4.425 / 34.678 | 4.076 / 4.733 / 38.391 | 1.116 / 1.293 / 1.982 |
| 433 | Definition | 3.164 / 3.475 / 3.849 | 3.178 / 3.610 / 3.870 | 0.398 / 0.460 / 0.595 |
| 433 | References | 3.736 / 4.468 / 6.570 | 3.804 / 4.511 / 5.754 | 2.415 / 2.609 / 3.320 |
| 433 | Broad search | 2.848 / 2.999 / 4.083 | 2.908 / 3.132 / 4.390 | 2.987 / 3.335 / 4.029 |
| 5845 | Outline | 10.117 / 10.962 / 106.877 | 10.078 / 10.919 / 149.169 | 1.535 / 1.717 / 2.016 |
| 5845 | Definition | 7.576 / 7.785 / 26.088 | 7.560 / 7.887 / 13.179 | 0.439 / 0.515 / 0.605 |
| 5845 | References | 7.147 / 7.540 / 71.784 | 7.161 / 7.412 / 17.183 | 2.809 / 3.065 / 4.061 |
| 5845 | Broad search | 14.283 / 15.016 / 39.261 | 14.459 / 15.785 / 19.759 | 28.320 / 29.194 / 32.238 |

### Startup, load and post-idle

Six sessions per graph/product below. Load medians include awaited compilation for
FreeFlight; Glider background compilation is shown separately. Post-idle is the
first outline after 5.1 seconds; cells show median / minimum / maximum ms.

| Files | Product | Startup ms | Load ms | Background ms | Post-idle outline ms |
| --- | --- | --- | --- | --- | --- |
| 433 | freeflight | 3.04 | 732.77 | Included | 36.248 / 35.296 / 37.024 |
| 433 | candidate | 3.13 | 725.01 | Included | 34.832 / 34.292 / 35.742 |
| 433 | glider | 126.87 | 620.51 | 277.00 | 2.181 / 1.111 / 2.284 |
| 5845 | freeflight | 3.29 | 2938.31 | Included | 179.195 / 176.789 / 190.618 |
| 5845 | candidate | 3.15 | 2889.33 | Included | 174.998 / 171.728 / 184.154 |
| 5845 | glider | 127.09 | 1914.22 | 494.00 | 4.853 / 1.556 / 7.785 |

Glider full-graph post-idle samples differ by cadence in this repeat (unpaced about
1.6–2.3 ms, paced about 7.4–7.8 ms). Those unfavorable competitor samples are
retained too. They do not close FreeFlight’s roughly 175–179 ms expiry gap.

### Diagnostic stage attribution

Full-graph outlines, median milliseconds, one diagnostic session per variant.
Steady cells summarize 100 queries; expiry cells contain one query. Stages nest.

| Variant/phase | Admission | Leaf metadata | Open | Read I/O | Read/hash/decode | Refresh | Semantic |
| --- | --- | --- | --- | --- | --- | --- | --- |
| baseline/steady | 9.268 | 7.029 | 0.037 | 0.007 | 0.070 | 10.152 | 0.023 |
| baseline/expiry | 17.514 | 13.230 | 77.054 | 18.191 | 162.845 | 188.417 | 0.051 |
| candidate/steady | 9.656 | 7.099 | 0.038 | 0.007 | 0.066 | 10.524 | 0.023 |
| candidate/expiry | 17.730 | 12.897 | 77.617 | 17.200 | 156.702 | 182.308 | 0.055 |

### Per-session ordinary results

Each cell is median / p90 / maximum ms. Every measured session is retained.

| Session | Outline | Definition | References | Broad search |
| --- | --- | --- | --- | --- |
| 433-interval0-0-freeflight | 0.563 / 0.572 / 0.583 | 0.538 / 0.548 / 0.558 | 0.921 / 0.976 / 1.290 | 0.640 / 0.652 / 0.656 |
| 433-interval0-1-candidate | 0.569 / 0.586 / 0.619 | 0.548 / 0.560 / 0.698 | 0.916 / 1.051 / 1.464 | 0.652 / 0.673 / 0.739 |
| 433-interval0-2-glider | 0.186 / 0.200 / 0.211 | 0.056 / 0.122 / 0.126 | 0.461 / 0.543 / 1.577 | 0.436 / 0.461 / 0.471 |
| 433-interval0-3-candidate | 0.562 / 0.568 / 0.574 | 0.544 / 0.549 / 0.553 | 0.904 / 0.925 / 1.283 | 0.653 / 0.660 / 0.959 |
| 433-interval0-4-glider | 0.140 / 0.206 / 0.229 | 0.119 / 0.127 / 0.131 | 0.468 / 0.548 / 0.610 | 0.445 / 0.481 / 0.632 |
| 433-interval0-5-freeflight | 0.564 / 0.570 / 0.574 | 0.545 / 0.552 / 0.555 | 0.909 / 0.952 / 1.309 | 0.649 / 0.659 / 0.920 |
| 433-interval0-6-glider | 0.132 / 0.200 / 0.224 | 0.055 / 0.123 / 0.126 | 0.470 / 0.543 / 0.595 | 0.445 / 0.466 / 0.488 |
| 433-interval0-7-freeflight | 0.566 / 0.577 / 0.585 | 0.548 / 0.554 / 0.562 | 0.910 / 0.956 / 1.286 | 0.644 / 0.655 / 0.671 |
| 433-interval0-8-candidate | 0.566 / 0.578 / 0.592 | 0.545 / 0.554 / 0.568 | 0.910 / 0.947 / 1.289 | 0.653 / 0.659 / 0.943 |
| 5845-interval0-0-freeflight | 7.079 / 7.555 / 8.676 | 6.071 / 6.249 / 7.343 | 6.399 / 6.803 / 7.139 | 14.112 / 14.615 / 16.733 |
| 5845-interval0-1-candidate | 7.129 / 7.809 / 9.113 | 6.115 / 6.432 / 7.499 | 6.404 / 6.972 / 7.814 | 14.160 / 14.847 / 17.374 |
| 5845-interval0-2-glider | 0.163 / 0.176 / 0.383 | 0.066 / 0.092 / 0.112 | 0.552 / 0.589 / 0.746 | 7.206 / 7.357 / 11.776 |
| 5845-interval0-3-candidate | 7.139 / 7.537 / 8.068 | 6.140 / 6.467 / 6.625 | 6.426 / 6.560 / 6.927 | 14.316 / 14.615 / 16.590 |
| 5845-interval0-4-glider | 0.166 / 0.205 / 0.280 | 0.067 / 0.092 / 0.108 | 0.568 / 0.651 / 0.831 | 7.238 / 8.134 / 9.796 |
| 5845-interval0-5-freeflight | 7.076 / 7.428 / 8.256 | 6.045 / 6.335 / 6.574 | 6.399 / 6.536 / 6.972 | 14.113 / 14.457 / 16.972 |
| 5845-interval0-6-glider | 0.165 / 0.182 / 2.248 | 0.064 / 0.092 / 0.207 | 0.563 / 0.616 / 1.502 | 7.016 / 7.478 / 8.651 |
| 5845-interval0-7-freeflight | 7.172 / 7.482 / 8.234 | 6.106 / 6.287 / 6.569 | 6.419 / 6.534 / 6.861 | 14.226 / 14.710 / 17.476 |
| 5845-interval0-8-candidate | 7.257 / 8.529 / 10.241 | 6.161 / 7.118 / 10.394 | 6.473 / 7.148 / 9.252 | 14.411 / 16.433 / 21.665 |
| 433-interval0.1-0-freeflight | 4.098 / 4.479 / 34.116 | 3.164 / 3.471 / 3.849 | 3.839 / 4.468 / 6.570 | 2.848 / 2.999 / 3.881 |
| 433-interval0.1-1-candidate | 4.044 / 4.407 / 33.551 | 3.176 / 3.542 / 3.725 | 3.758 / 4.478 / 5.670 | 2.850 / 3.049 / 4.279 |
| 433-interval0.1-2-glider | 1.133 / 1.465 / 1.982 | 0.398 / 0.460 / 0.595 | 2.415 / 2.679 / 3.320 | 2.987 / 3.520 / 4.029 |
| 433-interval0.1-3-candidate | 4.238 / 4.733 / 33.343 | 3.180 / 3.628 / 3.870 | 3.804 / 4.511 / 5.754 | 2.974 / 3.132 / 4.390 |
| 433-interval0.1-4-glider | 1.116 / 1.293 / 1.840 | 0.393 / 0.475 / 0.529 | 2.401 / 2.609 / 2.995 | 3.047 / 3.335 / 3.655 |
| 433-interval0.1-5-freeflight | 4.029 / 4.425 / 33.979 | 3.184 / 3.475 / 3.798 | 3.722 / 4.644 / 5.763 | 2.881 / 3.070 / 4.038 |
| 433-interval0.1-6-glider | 1.116 / 1.285 / 1.545 | 0.401 / 0.438 / 0.493 | 2.428 / 2.604 / 2.706 | 2.963 / 3.204 / 3.680 |
| 433-interval0.1-7-freeflight | 4.007 / 4.394 / 34.678 | 3.157 / 3.501 / 3.741 | 3.736 / 4.407 / 5.868 | 2.810 / 2.942 / 4.083 |
| 433-interval0.1-8-candidate | 4.076 / 4.877 / 38.391 | 3.178 / 3.610 / 3.784 | 3.953 / 4.533 / 5.707 | 2.908 / 3.132 / 4.325 |
| 5845-interval0.1-0-freeflight | 9.888 / 10.553 / 106.877 | 7.503 / 7.778 / 26.088 | 7.147 / 7.434 / 7.933 | 14.401 / 15.016 / 18.117 |
| 5845-interval0.1-1-candidate | 10.131 / 10.919 / 114.244 | 7.560 / 7.887 / 8.603 | 7.144 / 7.412 / 8.233 | 14.114 / 15.018 / 16.619 |
| 5845-interval0.1-2-glider | 1.526 / 1.689 / 1.992 | 0.455 / 0.515 / 0.605 | 2.837 / 3.162 / 3.684 | 28.320 / 29.194 / 29.619 |
| 5845-interval0.1-3-candidate | 9.899 / 10.678 / 75.823 | 7.551 / 7.789 / 13.179 | 7.161 / 7.409 / 17.183 | 14.459 / 15.785 / 17.061 |
| 5845-interval0.1-4-glider | 1.535 / 1.818 / 2.016 | 0.439 / 0.515 / 0.572 | 2.809 / 3.065 / 3.992 | 28.357 / 29.043 / 31.722 |
| 5845-interval0.1-5-freeflight | 10.117 / 10.962 / 67.235 | 7.576 / 7.867 / 24.170 | 7.153 / 7.540 / 9.775 | 14.125 / 14.792 / 17.262 |
| 5845-interval0.1-6-glider | 1.536 / 1.717 / 1.785 | 0.429 / 0.487 / 0.546 | 2.748 / 3.057 / 4.061 | 27.939 / 29.348 / 32.238 |
| 5845-interval0.1-7-freeflight | 10.159 / 11.141 / 12.865 | 7.601 / 7.785 / 8.721 | 7.129 / 7.744 / 71.784 | 14.283 / 16.663 / 39.261 |
| 5845-interval0.1-8-candidate | 10.078 / 11.224 / 149.169 | 7.620 / 8.002 / 9.292 | 7.188 / 7.944 / 8.784 | 14.941 / 16.932 / 19.759 |

### Receipts and repeat command

- Worker qualification/profiling: `bin/.local/benchmarks/trusted/glider-target-scratch/`.
- Native three-product run: `bin/.local/glider-comparison/target-scratch-2/`.
- Failed native preparation: `bin/.local/glider-comparison/target-scratch-1/`.
- Rejected runtime patch: `workflows/benchmark.trusted/assets/scratch-reuse.rejected.patch`.
- Exact source, toolchain, fixture and binary hashes: each run’s `provenance.json`.
- No Linux/Biztraak results, active configuration changes or remote mutations.

Repeat the native comparison using the retained, qualified frozen candidate:

```sh
FREEFLIGHT_GLIDER_DOTNET_ROOT=/Users/jamie/Documents/Codex/2026-10-19/task/toolchains/dotnet \
FREEFLIGHT_GLIDER_CANDIDATE_RECEIPT="$PWD/bin/.local/benchmarks/trusted/glider-target-scratch" \
FREEFLIGHT_GLIDER_LABEL=target-scratch-repeat \
FREEFLIGHT_GLIDER_SESSIONS=3 FREEFLIGHT_GLIDER_ROUNDS=50 \
FREEFLIGHT_GLIDER_WARMUP=10 FREEFLIGHT_GLIDER_INTERVALS=0,0.1 \
dockpipe --workflow benchmark.trusted.glider
```
