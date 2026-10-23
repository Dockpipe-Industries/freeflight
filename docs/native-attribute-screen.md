# Fresh native attribute screen, 2026-10-22 local

The native candidate reduces measured managed allocations and successful-sweep cost,
but remains unaccepted because latency tails are mixed across all-operation screens.
Production source is restored exactly to `94eb4207c8ffd2d5544bca8a52dcb8d451285015`
in `/Users/jamie/Source/freeflight-perf`, branch `investigate/rc2-warm-refresh`.
No commit, publication, push, merge or deployment occurred. Main js/dev and unrelated
local changes are untouched. All runs were serial; no additional agents were started.

## Design and fresh-authority guarantees

Only the reparse-flag expression in the existing CheckPath component walk changes.
On macOS, a fresh `getattrlist` syscall requests returned-attribute validity and vnode
type, with NOFOLLOW and packed-invalid flags. A 28-byte cleared stack buffer is
accepted only for its exact length, exact common mask, empty other groups and a known
vnode type. A symlink is rejected. Errors, invalid/incomplete/unsupported records,
unknown types and non-macOS paths use a fresh original `File.GetAttributes` read.
Only the reparse flag is consumed; other attributes keep their existing readers.
No stat result, path string, file content, authority or semantic answer is cached.
The original containment normalization, component order, content reads, resource
checks, transaction publication, recovery deadlines and descriptor admission remain.

This is a documented OS interface, with no new package dependency or persistent
permission change. Apple specifies final-component NOFOLLOW and explicit returned
attribute validity: [getattrlist manual](https://github.com/apple-oss-distributions/xnu/blob/main/bsd/man/man2/getattrlist.2).
The existing complete walk still checks earlier components separately. The baseline
limitation around concurrent hostile filesystem mutation is unchanged; this is not
an OS sandbox or race-free authorization claim.

Starting state is preserved under `bin/.local/perf-preservation/20261022-native-attributes-start`.
The unaccepted source/patch/decision is under `20261022-native-attributes-unaccepted`.
Frozen source, SDK, flags, every session/outlier and all gate logs remain in
`bin/.local/benchmarks/trusted/native-attributes-screen-v1`.

Candidate Program.cs SHA-256: `f6d374e2f23f88a7f0a9529912dee8e01d78dffb0f77619c3dbc9aaffd44d9b4`.

## Proofs and correctness

`bin/.local/benchmarks/attributes/fresh-native-proof-v2` passes thirty real/fault
checks: regular/Unicode/long paths, directory, missing file, symlink, dangling link,
FIFO, native failure, short/oversized record, missing/extra attribute bits, invalid/
unknown type, fresh replacement before fallback and the portable original path.
All malformed metadata uses the fresh .NET reader; original errors remain observable.
For 2,000 warmed reads of one regular file, the current-thread counter records zero
managed bytes for the native path versus 480,000 bytes for the .NET path. This is not
a claim of zero native allocation or a per-workload latency improvement.

The initial `fresh-native-proof-v1` has a retained assertion mistake: the race probe
compared pre-replacement original attributes with post-replacement fallback attributes.
The candidate correctly observed the new symlink. The corrected probe explicitly
requires the fresh replacement to be seen; production code did not change.

The frozen workers pass existing semantic/security/trusted/external/mutation suites,
Darwin metadata/handle/expiry checks, sixteen incremental faults, background recovery
and five failed-refresh rollback cases per variant. All twelve APIs have exact-result
comparisons, including complete rename preview fixture-hash verification. No weakened
fallback, error suppression, generator/plugin/analyzer execution or ML was introduced.
Actual other-platform execution and non-local filesystem qualification remain open;
the forced portable-path proof is not a Windows/Linux run.

Actual handoff EOF shutdown passes: 17.501 ms, including foreground ownership,
uncancellable maintenance reacquisition and join before disposal. The suspended sweep
starts at age 4504 ms; an ordinary foreground request at age 6021 ms performs
five-second recovery of the suppressed same-size/restored-timestamp edit, and the older
sweep aborts. No forced due timestamp or rename triggers this proof.

## Initial four-operation screen

Both variants use incremental validation and background recovery. Two sessions per
variant/size alternate process order, with five-second warmup, twenty measured rounds,
100 ms cadence, C5 search, 4096-byte padding and fourteen callers. Eight ordinary and
four separate diagnostic processes pass: 640 ordinary measured semantic checks plus
320 diagnostic checks. All raw samples, maxima and outliers remain. Fixed query order
and limited session count prevent strong causal inference. Ratios are candidate /
baseline, using medians of session metrics; smaller is faster. This is direct-worker
screening, not MCP/Glider or production latency.

| Files | Operation | Median ratio | p90 ratio |
| ---: | --- | ---: | ---: |
| 433 | symbols | 0.992 | 1.092 |
| 433 | definition | 0.942 | 1.100 |
| 433 | references | 1.056 | 1.059 |
| 433 | workspaceSymbols | 1.019 | 1.055 |
| 5845 | symbols | 0.973 | 0.979 |
| 5845 | definition | 1.004 | 1.086 |
| 5845 | references | 1.051 | 0.982 |
| 5845 | workspaceSymbols | 0.967 | 0.971 |

Full-graph definition p90 is unfavorable in both candidate sessions. These mixed
results require more evidence before accepting the native managed-allocation reduction.

## Initial all-operation screen

Two sessions per variant/size, five-second warmup and ten rotating-order measured
rounds pass 960 exact comparisons across twelve operations. Rename forces full fresh
validation and intentionally affects following operations. Starting measured rotation
can differ after time-based warmup; short-tail estimates and this workload must not
be pooled with the four-operation screen.

| Operation | 433 median ratio | 433 p90 ratio | 5845 median ratio | 5845 p90 ratio |
| --- | ---: | ---: | ---: | ---: |
| symbols | 0.875 | 1.141 | 0.980 | 0.912 |
| definition | 0.879 | 1.196 | 0.926 | 0.896 |
| references | 0.892 | 0.612 | 0.978 | 1.014 |
| workspaceSymbols | 0.984 | 0.621 | 0.931 | 1.101 |
| hover | 0.810 | 0.470 | 0.919 | 0.837 |
| diagnostics | 0.808 | 0.808 | 0.985 | 1.062 |
| rename | 0.948 | 0.940 | 0.922 | 0.936 |
| implementations | 0.967 | 0.936 | 0.959 | 1.016 |
| typeInfo | 0.878 | 0.772 | 0.931 | 0.962 |
| signatureHelp | 1.030 | 0.858 | 0.926 | 0.961 |
| callHierarchy | 1.035 | 0.790 | 1.012 | 1.892 |
| typeHierarchy | 0.926 | 0.882 | 0.961 | 1.005 |

## Predefined balanced confirmation

Because idle allocation/CPU improved while initial tails conflicted, one confirmation
reused the same frozen binaries, SDK, fixture and flags. No new implementation was
substituted. It uses only the 5,845-file graph, four sessions per variant, at least
five-second warmup and 48 measured rounds over twelve operations. The measured phase
resets to zero for both variants. A Williams design covers every operation in each
position four times per process and every one of the 132 directed within-round
predecessor pairs four times. Process order is baseline/candidate/candidate/baseline,
repeated once. Eight processes pass 4,608 measured exact-result checks. Rename still
forces full validation; this is an all-operation workload, not the earlier definition/
no-op or four-operation workload.

The new confirmation writer had a bookkeeping defect: its position-assertion loop
appended each completed session twelve times. It did not issue extra requests.
Original `samples.json`, `result.json` and the exact as-run adapter are retained.
An independent validator proves all twelve copies of each session are identical,
all 576 actual response slots per process are unique, and positions/predecessors are
balanced. `validated-samples.json` and `validated-summary.json` count each physical
session once. All timing ratios exactly match the original; only record counts and
repeated session-stat arrays are corrected. No physical sample or outlier is removed.
The validator is retained as `validation-adapter.py`. The future writer is corrected
and now rejects duplicate session identities. This correction did not rerun timing.

| Operation | Full-graph median ratio | Full-graph p90 ratio |
| --- | ---: | ---: |
| symbols | 0.985 | 1.056 |
| definition | 0.969 | 0.985 |
| references | 0.996 | 1.057 |
| workspaceSymbols | 0.975 | 0.953 |
| hover | 0.970 | 0.979 |
| diagnostics | 0.979 | 1.030 |
| rename | 0.918 | 0.920 |
| implementations | 1.004 | 0.910 |
| typeInfo | 0.981 | 0.990 |
| signatureHelp | 0.957 | 0.971 |
| callHierarchy | 0.989 | 0.961 |
| typeHierarchy | 0.964 | 1.028 |

The broader confirmation improves definition/search tails and reduces the initial
call-hierarchy outlier's influence, but symbols/references p90 remain about 6% worse;
diagnostics and type hierarchy also have unfavorable tails. All maxima/session
variation remain. These observations do not establish that the native syscall caused
each regression, nor do favorable median cells establish a reproducible overall win.
No post-hoc acceptance threshold is introduced. The follow-up control and bounded MCP
comparison below retain these adverse observations.

## Identical-binary balanced control

`native-attributes-screen-v1/all-operations-balanced-aa-v1` repeats the confirmation
shape with both labels mapped to the exact same 94eb420 DLL, SDK, flags and command.
The pre-timing manifest records that mapping and adapter hash. Eight fresh processes
pass 4,608 exact responses. The retained independent `validate-control.py` verifies
unique sessions/response slots, equal operation positions and all 132 predecessor
pairs; the earlier duplicate-row bug is absent.

Ratios compare the arbitrary candidate label to the arbitrary baseline label; both
execute baseline code. They describe run variation, not an optimization effect.

| Operation | A/A median ratio | A/A p90 ratio |
| --- | ---: | ---: |
| symbols | 0.989 | 0.998 |
| definition | 1.005 | 1.012 |
| references | 0.993 | 0.627 |
| workspaceSymbols | 1.074 | 1.031 |
| hover | 0.983 | 1.021 |
| diagnostics | 0.982 | 0.992 |
| rename | 1.000 | 1.000 |
| implementations | 0.988 | 0.957 |
| typeInfo | 0.986 | 0.962 |
| signatureHelp | 0.987 | 0.963 |
| callHierarchy | 1.002 | 0.590 |
| typeHierarchy | 0.960 | 0.950 |

References session p90 spans 0.592–1.544 ms and call hierarchy 0.650–1.608 ms
with identical code. Search label medians differ 7.4%. Symbols vary less (label p90
ratio0.998), so this control does not erase the earlier symbols regression. No
post-hoc cutoff, statistical equivalence or causal explanation is claimed. The
observed variation plus measured allocation benefit justifies one bounded repeated
full-graph paced MCP comparison against94eb420 and Glider; it does not accept the
candidate or justify changing production source.

## Matched MCP follow-up

`bin/.local/glider-comparison/native-attributes-matched-20261022` uses the frozen
native candidate, retained94eb420 worker and pinned Glider13.3.0 through real MCP.
Both FreeFlight variants use the same shipped C++ core. The common .NET10.0.402
fixture SDK, five-second warmup, 5,845-file graph, 100 ms round cadence, forty measured
rounds and balanced product/query positions are matched. Three sessions per product
run serially (nine processes); 1,440 measured exact semantic responses pass, with
3,220 responses including warmup and post-idle queries. Native publish and generated
worker/trust tests pass before timing. Source, executable identities, adapters,
startup configs, every sample and outlier remain in the receipt.

Metrics below are medians of session metrics, in milliseconds. This is a bounded
single-machine follow-up, not a general workload or platform qualification.

| Operation | 94 median / p90 | Native median / p90 | Glider median / p90 |
| --- | ---: | ---: | ---: |
| symbols | 0.4833 / 1.3141 | 0.4506 / 1.3145 | 0.4764 / 1.3369 |
| definition | 0.4535 / 1.3811 | 0.4435 / 1.3940 | 0.2697 / 0.8984 |
| references | 1.2647 / 3.2211 | 1.3872 / 2.9280 | 1.4058 / 3.1523 |
| workspaceSymbols | 23.7049 / 26.7382 | 23.3406 / 27.4059 | 22.1553 / 26.4542 |

Against94eb420, references median worsens9.7% while p90 improves9.1%; search p90
worsens2.5%. Definition p90 is0.9% worse. Against Glider, native definition median
is64.4% slower and p9055.2% slower; search median is5.4% slower and p903.6% slower.
Symbols and references have favorable cells, but the definition/search gap and mixed
all-operation behavior remain. The A/A variation is not grounds to discard adverse
cells or accept the optimization. Position-stratified medians retain a definition gap in every query position;
`position-summary.json` includes all session strata (ten samples per cell). These
are descriptive observations, without a causal inference. No further expensive
latency matrix is warranted for this unchanged candidate.

## Verified idle costs

`idle-native-attribute-cost-v1` uses two alternating foreground-only/background
process pairs, eight-second warmup and two 5.2-second idle windows per process.
All eight windows pass. Six successful background sweeps require matching successful
completion/publication counters and exactly 5,845 files / 23,941,120 bytes per sweep.
Idle-window failures and aborts are zero.

| Metric | Native candidate |
| --- | ---: |
| Allocated MB/sweep | 46.888 |
| Process CPU ms/sweep | 184.375 |
| Observed one-core CPU % | 5.313 |
| GC pause ms/sweep | 3.802 |
| Sampled background RSS MB | 364.5–369.3 |

Allocation is descriptively 18.7% below the earlier 94eb420 observation of 57.642
MB/sweep; CPU is about 9% below its 203.437 ms/sweep. Those source versions were
measured in separate runs, not a matched statistical idle cost comparison. Each idle
run matches maintenance off/on only for its own source. RSS is sampled, not peak,
and native allocator costs are not isolated. This short synthetic macOS evidence
does not qualify long-duration memory, real repositories, Glider idle or other platforms.

## Matched idle follow-up

`native-attributes-screen-v1/idle-native-attribute-matched-v1` builds both frozen
sources before timing. Two maintenance-off/on pairs per source reverse source order
in the second pair. Eight serial processes produce sixteen checked windows. Each
source completes six successful full sweeps with matching completion/publication
counts and exactly5,845 files /23,941,120 bytes per sweep. Failures/aborts are zero;
maintenance-off windows show no recovery attempts or reads. The pre-timing manifest,
source/DLL hashes, generated instrumentation, adapter, raw observations and retained
`validate-idle.py`/`validated-summary.json` make accounting reproducible.

| Metric | 94eb420 | Native candidate |
| --- | ---: | ---: |
| Managed allocated MB/sweep | 57.643 | 46.889 |
| Process CPU ms/sweep | 206.820 | 189.148 |
| Observed one-core CPU % | 5.959 | 5.449 |
| GC pause ms/sweep | 2.975 | 3.508 |
| Sampled background RSS MB | 364.1–365.4 | 362.7–364.7 |

Managed allocation falls18.7% and CPU/sweep8.5%, with favorable direction in both
pairs. GC pause/sweep increases17.9%; that adverse observation is retained. This
short diagnostic sample does not establish statistical significance, peak memory,
native allocation, long-duration behavior, Glider idle cost or another platform.
It strengthens the allocation result without resolving mixed latency or proving
an overall performance win. Production source stays94eb420.

## Decision, next step and replay

Keep the native source as an unaccepted candidate, with production restored to94eb420.
The experiment achieves a measured managed-allocation reduction while preserving
all executed correctness/recovery checks; it does not pass the overall latency objective.
The identical-binary control and one bounded matched MCP comparison are complete.
The remaining latency regressions and definition/search gap keep this source
unaccepted. Further repeats of this unchanged candidate are not justified by the
current evidence. Next isolate the reference median and search/definition boundary
costs before choosing a different allocation change. Do not silently drop adverse cells or combine incompatible workloads.
The original definition/search gap against Glider remains unclosed.

The matched idle replay uses the existing frozen receipt, without installing the
archived source:

```sh
FREEFLIGHT_BACKGROUND_RECEIPT=native-attributes-screen-v1 FREEFLIGHT_BACKGROUND_IDLE_LABEL=NEW_LABEL FREEFLIGHT_BACKGROUND_IDLE_VARIANT=both FREEFLIGHT_BACKGROUND_IDLE_SESSIONS=2 dockpipe --workflow benchmark.recovery.background.idle
FREEFLIGHT_OPERATION_RECEIPT=native-attributes-screen-v1 FREEFLIGHT_OPERATION_LABEL=NEW_LABEL FREEFLIGHT_OPERATION_SIZES=5845 FREEFLIGHT_OPERATION_ROUNDS=48 FREEFLIGHT_OPERATION_SESSIONS=4 FREEFLIGHT_OPERATION_ORDER=balanced FREEFLIGHT_OPERATION_IDENTICAL=baseline dockpipe --workflow benchmark.trusted.operations
```

The helper proof expects the archived native candidate installed in Program.cs and
a fresh `FREEFLIGHT_ATTRIBUTE_LABEL`:

```sh
FREEFLIGHT_ATTRIBUTE_LABEL=fresh-native-repeat dockpipe --workflow benchmark.recovery.attributes
FREEFLIGHT_OPERATION_RECEIPT=NEW_FROZEN_RECEIPT dockpipe --workflow benchmark.trusted.operations
FREEFLIGHT_OPERATION_RECEIPT=NEW_FROZEN_RECEIPT FREEFLIGHT_OPERATION_LABEL=balanced-repeat FREEFLIGHT_OPERATION_SIZES=5845 FREEFLIGHT_OPERATION_ROUNDS=48 FREEFLIGHT_OPERATION_SESSIONS=4 FREEFLIGHT_OPERATION_ORDER=balanced dockpipe --workflow benchmark.trusted.operations
```

Use the existing perf-venv and pinned dotnet11 PATH. First freeze/gate a new receipt
with the retained `benchmark.trusted` provenance settings and a fresh label. The
all-operation default remains ten rotating-order rounds, two sessions per variant
and both graphs. Output labels refuse overwrite. Existing handoff and idle workflows
accept `FREEFLIGHT_BACKGROUND_RECEIPT=NEW_FROZEN_RECEIPT` with fresh sub-labels.
The independent raw confirmation validator accepts `FREEFLIGHT_OPERATION_RECEIPT`
and `FREEFLIGHT_OPERATION_LABEL` naming this preserved run; it only validates and
copies its own adapter, leaving original measurements unchanged.
