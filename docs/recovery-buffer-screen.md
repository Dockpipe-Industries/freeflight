# Recovery buffer screening, 2026-10-22

Local M6 continuation from runtime `6a06b1d`. Saved serial-handle evidence and
runtime restoration are committed as `77304a7`. The resumed `repo.check` passed.
The previous denied process-list operation was not retried or bypassed. Previous
benchmark receipts were complete; current workflows are tracked through their
tool-owned process sessions and run sequentially.

## One-shot buffer hash — rejected

Candidate `8a43cb2` hashes the already bounded fresh byte buffer once, replacing
the per-file incremental hash object. Reads, byte admission, paths, external input
handling, strict default and transactional publication are unchanged. A token
check precedes hashing. This is not a cache, TTL extension or background read.

`bin/.local/benchmarks/trusted/buffer-hash-screen-v1` contains source hashes,
toolchains, full raw samples, summaries and separate profiles. Existing worker,
trusted/external, mutation, Darwin metadata/read proofs, sixteen incremental fault
checks and five failed-refresh transaction cases per variant passed. Eight plain
and four diagnostic fresh worker processes passed all semantic assertions.
This is direct-worker screening, not an MCP or new Glider comparison.

Full 5,845-file ordinary recovery samples in ms: baseline 158.689 / 170.095;
candidate 152.014 / 166.218. Small 433-file samples: baseline 39.346 / 38.885;
candidate 40.068 / 39.904. Only two ordinary samples per variant/size; these do
not establish a tail improvement.

Full steady candidate/baseline median and p90 ratios:

| Operation | Median | p90 |
| --- | ---: | ---: |
| Outline | 1.339 | 1.335 |
| Definition | 1.135 | 1.285 |
| References | 1.284 | 1.352 |
| Search | 1.222 | 1.294 |

Both full-graph candidate sessions had unfavorable p90s in every operation.
The screen rejects this candidate without spending a larger MCP matrix on it.
These are descriptive measurements, not proof that hashing caused every timing
change. Fixed query order and short warmup limit causal interpretation.

Separate full-recovery diagnostics: old hash create/append/finish total 15.787 ms;
new single hash 13.293 ms. Refresh 171.025 to 167.060 ms; CPU 171.566 to 173.433 ms;
allocation 45,115,640 to 44,422,432 bytes; GC pause 2.651 to 2.428 ms. Nested stages
are not disjoint. One-shot hashing saves much less than eliminating the hash cost.

## Request-local buffer reuse — rejected

Retained candidate `e9c5ab3` restores original hashing and reuses one MemoryStream
within each Refresh call. SetLength(0) and Position=0 precede every fresh file read;
no bytes or authority survive the request. Target: repeated source-byte buffer
allocation, not filesystem validation. Receipt: `buffer-reuse-screen-v1` under
the same trusted benchmark directory. Acceptance requires all fault gates, an
ownership proof for retained SourceText after buffer mutation/disposal, then matched
ordinary MCP measurements against local baseline and Glider if screening warrants
them. No new platform or overall-win claim follows from worker screening.

All qualification/fault/transaction gates passed again. The ownership proof passed
nine ascending/descending byte sizes, chunk boundaries and Unicode cases, retaining
all earlier text/checksums through overwrite and disposal. It tests the pinned
Roslyn assembly, not a universal stream ownership claim. Its receipt is
`buffer-reuse-screen-v1/buffer-ownership-proof/result.json`.

Full ordinary recovery samples: baseline 157.762 / 173.916 ms; candidate
168.443 / 187.291 ms. Steady median/p90 ratios:

| Operation | Median | p90 |
| --- | ---: | ---: |
| Outline | 1.172 | 1.136 |
| Definition | 1.084 | 1.064 |
| References | 1.007 | 1.161 |
| Search | 0.999 | 0.980 |

Small graph search also regressed (median 1.027, p90 1.024); its other operations
improved. This is another mixed candidate, rejected before a larger MCP matrix.

Separate full-recovery diagnostic allocation fell from 45,324,112 to 20,666,448
bytes. Buffer writes fell 2.993 to 0.111 ms, refresh 174.176 to 168.293 ms and GC
pause 2.145 to 1.883 ms. CPU remained 174.860 / 174.694 ms; opens 67.255 / 67.674 ms
and uncached pathname checking 42.280 / 43.120 ms. Both read exactly 5,845 inputs
and 23,941,120 bytes. Halving allocations did not solve filesystem or CPU cost,
and the ordinary measurements remain unfavorable despite the instrumented gain.

## Decision and next constraint

Both screens completed 24 fresh processes in total, 960 measured steady responses
and 96 post-idle responses, with exact semantic assertions. Eight of those processes
are diagnostic and are not pooled into ordinary timing. The screens use `C58`
search, 10 rounds and two-second warmup; they are inexpensive rejection screens,
not the final broad `C5`, balanced MCP/Glider qualification. No expensive final
matrix was justified. The runtime is restored to `6a06b1d` exactly. No active MCP,
service, publication or other host was changed. Current task-owned commands have
reported terminal success; the historical global process inspection remains denied.

The prior profiles put ordinary declaration discovery near 8.36 ms, versus about
0.45 ms ordering and 0.46 ms rendering. The guarded compilation shortcut and
response-copy experiments are already rejected and were not repeated. Definition
has negligible core parse/envelope costs; there is no measured persistent queue
backlog to remove. The new screens reject allocating fewer byte buffers or changing
hash APIs as a route to an overall win; they do not prove all possible allocation
optimizations ineffective.

Recovery still requires a complete fresh content sweep before a response after the
five-second deadline. The measured serial open stage alone is roughly 67 ms versus
the previously measured Glider idle response of a few milliseconds. This is an
observed implementation constraint, not a theoretical lower bound. Repeated minor
allocation matrices are poor value now. A materially different approach would need
either a proven faster fresh filesystem primitive, or an explicit decision to
evaluate idle/background recovery (total CPU/I/O, age, fault and contention costs
included). Background maintenance changes the current no-background-work behavior;
it was not implemented or assumed authorized. Neither candidate is a Glider win.

## Reproduce the retained screens

Use the existing M6 SDK and Python environment recorded in each `provenance.json`.
Choose a fresh label and candidate commit (the retained one-shot hash or reuse
commit), then invoke the existing workflow:

```sh
FREEFLIGHT_TRUSTED_BENCH_LABEL=buffer-repeat \
FREEFLIGHT_TRUSTED_BENCH_BASELINE=6a06b1d \
FREEFLIGHT_TRUSTED_BENCH_CANDIDATE=<retained-candidate-commit> \
FREEFLIGHT_TRUSTED_BENCH_BASELINE_INCREMENTAL=1 \
FREEFLIGHT_TRUSTED_BENCH_INCREMENTAL=1 \
FREEFLIGHT_TRUSTED_BENCH_SIZES=433,5845 \
FREEFLIGHT_TRUSTED_BENCH_SESSIONS=2 FREEFLIGHT_TRUSTED_BENCH_ROUNDS=10 \
FREEFLIGHT_TRUSTED_BENCH_WARMUP=2 FREEFLIGHT_TRUSTED_BENCH_PADDING=4096 \
FREEFLIGHT_TRUSTED_BENCH_CALLERS=14 \
dockpipe --workflow benchmark.trusted
```

For the reuse candidate only, after timing exits:
`FREEFLIGHT_BUFFER_RECEIPT=buffer-repeat dockpipe --workflow benchmark.recovery.buffer`.
Do not rerun either negative experiment without a new causal hypothesis.
