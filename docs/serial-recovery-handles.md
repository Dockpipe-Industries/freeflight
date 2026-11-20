# Serial recovery handle admission

This is local M6 work against runtime baseline `6a06b1d`; no release, installed MCP
configuration or remote platform qualification is implied. The native API feasibility
and its rejected assumptions remain in [the preceding report](recovery-handle-feasibility.md).

## Candidates and correctness

`b04d21f` replaces trusted macOS pre-read pathname walks with a serial kernel open
using `O_RDONLY | O_NONBLOCK | O_CLOEXEC | O_NOFOLLOW_ANY`, then descriptor-based
object-type validation. Only regular handles become FileStreams. It remains an
experiment: ordinary paced results were mixed, and a later root-replacement gate
found that its generic fallback could discard an explicit kernel symlink rejection.

`c3ae753` narrows the optimization to full **incremental-mode recovery**, preserving
strict-default and ordinary target-read paths. It makes Darwin ELOOP terminal.
The helper retains lexical root confinement; the kernel check is uncached, covers
all path components and applies to the same opened handle subsequently read.
Metadata/capability failures retain checked serial fallback. Exact external compiler
inputs retain their existing allowlist, validation, open flags and read-only policy.
There is no parallelism, handle cache, deferred sweep or changed five-second deadline.

The sorted loop, stat size admission, actual read-chunk budget checks, hash/decode,
final cancellation/generation guard, transaction publication and dirty acknowledgment
remain unchanged. Single-file synchronous calls still cannot promise a hard
cancellation deadline. Full hostile filesystem-mutation race freedom is not claimed;
SECURITY.md's existing limitation remains applicable, including legacy fallback.

`DarwinSourceHandle.Open` owns a descriptor until handing it to FileStream; failure
paths dispose it. A generated .NET proof uses the actual helper and original
pathname check, with test-only hooks around the native open and metadata call.
It covers the real fast path (zero fallback), metadata fallback, cleanup on fallback
failure, escapes, leaf/ancestor symlinks, missing inputs, directory/FIFO rejection,
pre-open replacement, restored-timestamp bytes, caller cancellation, ordered early
failure and root replacement. No hook enters production or ordinary timing builds.

The initial cleanup oracle tested a numeric descriptor after it could be reused and
reported a leak. `serial-proof-v1` is retained as a failed oracle; v2 checks the owned
SafeFileHandle's closed state and passes. The later `serial-proof-root-before` fails
on `b04d21f`: an explicit ELOOP falls through the older root-relative check and opens
a replacement root symlink. The negative control confirms that older check also
accepts the fixture; this is an inherited root-mutation limitation, not evidence that
the old runtime was race-free. The refinement's integrated proof rejects it.

Qualification receipts:

- `bin/.local/benchmarks/trusted/serial-handles-v1`: initial candidate against 6a06b1d.
- `bin/.local/benchmarks/serial-handles/serial-proof-v2`: initial helper proof.
- `bin/.local/benchmarks/serial-handles/serial-proof-root-before`: retained failing gate.
- `bin/.local/benchmarks/trusted/serial-handles-v2`: refined candidate, including the
  newly integrated source-extracted handle proof.

Both worker variants passed semantics, resource/cancellation/EOF, trusted external
inputs, mutation, Darwin metadata and read proofs; the candidate passed all sixteen
incremental fault cases. Failed-refresh transaction guards preserved state in five
cases per variant. These tests do not replace platform-wide packaging qualification.

## Initial candidate: retained mixed evidence

`serial-handles-mcp-v1` completed 32 ordinary fresh processes (candidate comparisons,
identical-binary controls and a focused small-graph repeat) plus four separately
instrumented processes. All 5,904 measured semantic checks passed. The MCP oracle
checks full symbol locations/ranges, cross-project definition, fourteen references
and broad search identities over unchanged synthetic 433-file/two-project and
5,845-file/26-project graphs. This is not Biztraak or a Linux rerun.

Ordinary sessions alternate tool order and use balanced query positions, five seconds
of warm-up and forty measured rounds. Round pacing is either zero or 100 ms; sleep
is excluded from endpoint latency. Every sample, including periodic-recovery tails,
remains in raw JSON. The full solution's first post-idle outline was 131–133 ms versus
157–158 ms unpaced. Paced observations were 95–135 ms versus 149–157 ms; the favorable
95 ms sample is retained, not selected as the headline. Each cadence has only two
fresh samples per variant for this post-idle operation.

Unfavorable evidence includes small-graph paced reference p90 +7.4% initially
(+0.5% in the repeat), and search p90 +4.7% initially/+10.1% in the repeat. Full-graph
paced definition median was +12.4% while p90 was +0.4%. Identical-binary controls
were substantially tighter in those cells. This does not identify a scheduler/CPU
mechanism; the all-query version was not selected as a broad improvement.
A small unpaced reference maximum of 12.7435 ms is retained versus baseline 2.088 ms.

Separate source-profile medians across two processes per source:

| Full post-idle worker metric | 6a06b1d | b04d21f |
| --- | ---: | ---: |
| Refresh, ms | 159.815 | 135.396 |
| Existing pathname-check stage, ms | 39.780 | 0.522 |
| Open stage including new handle validation, ms | 70.149 | 82.462 |
| Read I/O, ms | 7.332 | 8.546 |
| Hash append, ms | 10.871 | 11.616 |
| Process allocation, bytes | 44,356,004 | 31,808,376 |
| GC pause, ms | 2.173 | 1.871 |
| Worker process CPU, ms | 162.974 | 138.604 |
| Documents read | 5,845 | 5,845 |
| Bytes read | 23,941,120 | 23,941,120 |

The saved path work exceeds the additional open/handle-validation cost. Instrumented
stages are nested and are not additive percentages; new handle attribute calls are
inside the open stage, not the old pathname-attribute counter. These are diagnostics,
not ordinary timing or measured syscall counts.

The first orchestrator requested a two-source diagnostic run incompatible with the
adapter's shared-worker requirement. An early guard rejected it before diagnostic
build/timing, preserving `failure.json`. Explicit resume validated completed ordinary
receipts and ran separate baseline/candidate source profiles under new names. The
initial orchestrator is not represented as uninterrupted success.

## Refined candidate: final comparison and decision

The recovery-only candidate `c3ae753` completed another sixteen ordinary and two
separately instrumented fresh processes: 2,952 measured semantic checks passed.
Across both experiments this is 54 fresh processes and 8,856 measured semantic
checks. No fresh Glider timings were collected in this pass.

Ordinary steady-state figures below are medians of the two per-session medians and
p90 values; maxima are the largest retained sample. Each session has forty rounds.
B/C means baseline 6a06b1d / candidate c3ae753. Units are milliseconds.

| Files | Round gap | Operation | Median B/C | p90 B/C | Max B/C |
| --- | --- | --- | ---: | ---: | ---: |
| 433 | 0.0 s | symbols | 0.157 / 0.161 | 0.173 / 0.178 | 0.438 / 0.344 |
| 433 | 0.0 s | definition | 0.147 / 0.155 | 0.163 / 0.168 | 0.258 / 0.234 |
| 433 | 0.0 s | references | 0.516 / 0.537 | 0.592 / 0.659 | 1.155 / 1.147 |
| 433 | 0.0 s | workspaceSymbols | 0.244 / 0.270 | 0.272 / 0.286 | 0.513 / 0.589 |
| 433 | 0.1 s | symbols | 1.237 / 1.216 | 2.215 / 2.100 | 2.616 / 2.496 |
| 433 | 0.1 s | definition | 1.184 / 1.168 | 2.130 / 2.168 | 2.307 / 2.710 |
| 433 | 0.1 s | references | 3.378 / 3.501 | 4.718 / 5.063 | 5.490 / 6.199 |
| 433 | 0.1 s | workspaceSymbols | 2.433 / 2.307 | 3.403 / 3.343 | 5.462 / 4.096 |
| 5845 | 0.0 s | symbols | 0.189 / 0.189 | 0.230 / 0.238 | 0.512 / 0.318 |
| 5845 | 0.0 s | definition | 0.169 / 0.171 | 0.221 / 0.223 | 0.464 / 0.259 |
| 5845 | 0.0 s | references | 0.647 / 0.664 | 0.721 / 0.760 | 1.052 / 1.105 |
| 5845 | 0.0 s | workspaceSymbols | 8.007 / 7.957 | 8.457 / 8.345 | 10.065 / 10.010 |
| 5845 | 0.1 s | symbols | 0.516 / 0.505 | 1.437 / 1.501 | 146.394 / 119.226 |
| 5845 | 0.1 s | definition | 0.450 / 0.469 | 1.582 / 1.467 | 1.958 / 1.720 |
| 5845 | 0.1 s | references | 1.224 / 1.292 | 3.322 / 3.497 | 5.030 / 6.472 |
| 5845 | 0.1 s | workspaceSymbols | 24.824 / 25.778 | 28.888 / 28.609 | 153.759 / 127.490 |

First outline after 5.1 seconds idle, separate from steady-state:

| Files | Prior round gap | N per variant | Median B/C | Descriptive p90 B/C | Max B/C |
| --- | --- | ---: | ---: | ---: | ---: |
| 433 | 0.0 s | 2 | 34.397 / 28.612 | 34.474 / 28.922 | 34.474 / 28.922 |
| 433 | 0.1 s | 2 | 33.073 / 25.366 | 35.121 / 28.323 | 35.121 / 28.323 |
| 5845 | 0.0 s | 2 | 158.782 / 143.227 | 159.311 / 151.286 | 159.311 / 151.286 |
| 5845 | 0.1 s | 2 | 157.967 / 134.446 | 159.832 / 134.823 | 159.832 / 134.823 |

With only two post-idle samples per cadence, nearest-rank p90 equals the maximum;
it is descriptive, not a statistically robust tail estimate. The 151.286 ms
candidate sample remains included. Full-graph recovery median improves about 9.8%
unpaced and 14.9% paced, but this is not a general performance acceptance.

The narrow gate removes the repeated small paced-search regression from the first
experiment. However, reference p90 remains unfavorable: small graph +11.2% unpaced
and +7.3% paced; full graph about +5.4% and +5.3%. Raw absolute deltas are in the
table. Prior same-binary controls are retained separately, not pooled into these
comparisons. They do not establish a cause for the candidate differences.

Separate source-profile results for refined full recovery (two fresh instrumented
processes; baseline uses the preceding same-source profile, not a new baseline run):

| Metric | Baseline | Refined candidate |
| --- | ---: | ---: |
| worker.stages.refresh | 159.815 | 135.977 |
| worker.stages.path | 39.780 | 0.515 |
| worker.stages.open | 70.149 | 83.235 |
| worker.stages.readIo | 7.332 | 8.663 |
| worker.stages.hashAppend | 10.871 | 11.387 |
| worker.allocatedBytes | 44356004.000 | 31805648.000 |
| worker.gcPauseMs | 2.173 | 2.157 |
| worker.cpuMs | 162.974 | 139.327 |
| worker.Reads | 5845.000 | 5845.000 |
| worker.Bytes | 23941120.000 | 23941120.000 |

Load and whole-session CPU remain separate. CPU includes startup/load, timed
warm-up, steady requests and idle recovery; it is not per-query CPU:

| Files | Round gap | Load ms B/C | All-phase child CPU seconds B/C |
| --- | --- | ---: | ---: |
| 433 | 0 s | 820.522 / 753.999 | 16.984 / 17.080 |
| 433 | 0.1 s | 754.429 / 763.105 | 3.980 / 4.031 |
| 5845 | 0 s | 2992.316 / 3015.486 | 12.321 / 12.450 |
| 5845 | 0.1 s | 2974.824 / 3003.875 | 8.952 / 9.000 |

Decision: retain `b04d21f` and `c3ae753` as recoverable experiments, but select neither
as a broad performance winner. The active worker source is restored exactly to
`6a06b1d`. The refined primitive passes the tested correctness gates and does reduce
the targeted recovery work, but the ordinary reference tails remain an unresolved
tradeoff. No known correctness failure is being shipped, and no performance result
is hidden by dropping a cadence or removing outliers.

Further broad matrices without attribution are not recommended. The next technical
question is whether code layout, closure allocation or runtime/cadence interactions
explain the remaining ordinary differences; those are hypotheses, not established
causes. Alternatively, choosing this measured recovery-versus-reference-tail tradeoff
would be an explicit product decision. No freshness/security relaxation is needed
for the serial primitive, and no guaranteed syscall termination or safe speculative
parallelism has been established. The graph-wide content-sweep obligation remains.

## Exact replay and limits

These commands reuse the task-local M6 toolchains, immutable synthetic fixtures and
retained native baseline from the existing [benchmark infrastructure](benchmarks.md).
They are not a claim of a self-contained clean-clone benchmark or a user-solution
adapter. Substitute equivalent pinned toolchain paths on another authorized host;
`FREEFLIGHT_SERIAL_BASELINE_NATIVE_RECEIPT` can select a previously qualified native
6a06b1d baseline. Fresh labels are required; receipts are never overwritten.

```sh
export PATH="$PWD/bin/.local/perf-venv/bin:/Users/jamie/Documents/Codex/2026-10-20/task/freeflight-dependabot/bin/.local/dotnet11:$PATH"
export DOTNET_CLI_USE_MSBUILD_SERVER=0

FREEFLIGHT_SERIAL_HANDLE_LABEL=serial-proof-repeat \
FREEFLIGHT_SERIAL_HANDLE_REF=c3ae753 \
dockpipe --workflow benchmark.recovery.serial

FREEFLIGHT_TRUSTED_BENCH_LABEL=serial-handles-repeat \
FREEFLIGHT_TRUSTED_BENCH_BASELINE=6a06b1d \
FREEFLIGHT_TRUSTED_BENCH_CANDIDATE=c3ae753 \
FREEFLIGHT_TRUSTED_BENCH_BASELINE_INCREMENTAL=1 \
FREEFLIGHT_TRUSTED_BENCH_INCREMENTAL=1 \
FREEFLIGHT_TRUSTED_BENCH_PADDING=4096 \
FREEFLIGHT_TRUSTED_BENCH_CALLERS=14 \
dockpipe --workflow benchmark.trusted.qualification

FREEFLIGHT_SERIAL_COMPARE_LABEL=serial-recovery-repeat \
FREEFLIGHT_SERIAL_CANDIDATE_RECEIPT="$PWD/bin/.local/benchmarks/trusted/serial-handles-repeat" \
FREEFLIGHT_SERIAL_CANDIDATE_REF=c3ae753 \
FREEFLIGHT_SERIAL_COMPARE_STAGES=balanced,candidate-diagnostic \
FREEFLIGHT_GLIDER_CMAKE=/Users/jamie/Documents/Codex/2026-10-19/task/toolchains/cmake-3.31.8-macos-universal/CMake.app/Contents/bin/cmake \
FREEFLIGHT_GLIDER_DOTNET_ROOT=/Users/jamie/Documents/Codex/2026-10-19/task/toolchains/dotnet \
dockpipe --workflow benchmark.recovery.compare

FREEFLIGHT_SERIAL_COMPARE_LABEL=serial-recovery-repeat \
dockpipe --workflow benchmark.recovery.summary
```

The last executed comparison used `serial-recovery-only-v1`, candidate receipt
`serial-handles-v2`, and precisely the two selected stages above. Omitting the stage
selection additionally runs identical-binary controls, a focused small repeat and
a baseline profile. Those conditions were executed for the initial candidate, not
silently counted as additional refined-candidate sessions. The comparison refuses
timing unless the frozen source matches its passing strengthened root-replacement
proof. Explicit resume accepts only recorded failed orchestration with verified
completed conditions; an existing uncertain condition is not overwritten or rerun.

Final ordinary receipts:
`bin/.local/glider-comparison/serial-recovery-only-v1-balanced/{samples,summary}.json`.
Final combined review:
`bin/.local/glider-comparison/serial-recovery-only-v1/review.json`.
Separate source profiles live under the `*-diagnostic` condition directories.
`serial-handles-mcp-v1` retains the rejected experiment, controls, repeats and original
orchestration failure. The retained-ref proof was rerun after restoring the runtime,
under `bin/.local/benchmarks/serial-handles/serial-proof-retained-ref`.

No operation is denied, pending or uncertain. The remaining blocker to selecting a
winner is the measured ordinary-latency tradeoff, not permissions or missing tools.
No publication, active MCP/Biztraak, service, system-security or ML change occurred.
