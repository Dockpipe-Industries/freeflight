# Trusted Roslyn performance workflow

`dockpipe --workflow benchmark.trusted` is a local, serial baseline/candidate
experiment. It complements `benchmark` (the full MCP endpoint) by isolating the
trusted Roslyn worker. It does not measure C++ routing or full MCP serialization,
and synthetic results are not a private-repository or Glider comparison.

Provision the SDK pinned by `global.json`, Python and DockPipe on PATH. `repo.check`
requires PyYAML in that Python environment. No Docker/service change is needed.
Run `dockpipe --workflow repo.check` first. Then set:

```sh
FREEFLIGHT_TRUSTED_BENCH_LABEL=my-comparison \
FREEFLIGHT_TRUSTED_BENCH_BASELINE=39c3cc83b04f21e352e7885c0589d39947b9efa4 \
FREEFLIGHT_TRUSTED_BENCH_CANDIDATE=WORKTREE \
dockpipe --workflow benchmark.trusted
```

Baseline and candidate accept local Git refs; `WORKTREE` snapshots the current
tracked worker inputs. Neither checkout nor remote refs are changed. New worker
files must be tracked before using WORKTREE. Existing receipt labels fail rather
than overwrite evidence. All output is under `bin/.local/benchmarks/trusted/LABEL`.
No generated receipt or source content is uploaded.

The workflow owns preparation, qualification, measurement and summarization:

- Snapshot the worker and pinned SDK selection; record source, binary, driver and
  fixture hashes, Git commits, host architecture and SDK identity. Build both
  variants with locked dependencies and Release configuration in private paths.
- Generate the same 433-file/two-project and 5,845-file/26-project dependency-free
  shapes used in the earlier investigation; explicitly restore test projects.
  These are small source files with one controlled cross-project call, not a
  realistic business application. Graph loading includes awaited compilations.
- Run the existing `test_worker.py` and `test_trusted.py` suites for both variants,
  including exact semantics, resource limits, cancellation and external inputs.
  A reused mutation asset adds preserved-timestamp hashes, non-target ancestor
  replacement, missing input, additions/removals on reopen and overflow recovery.
- Build a test-only transaction guard from each immutable source snapshot. On a
  failed Refresh it compares the committed solution and all three dictionaries
  with their entry state. Exercise a late missing input after an earlier staged
  target update, ancestor replacement and missing-input recovery. This guard is
  never present in timed builds. `benchmark.trusted.transaction` can run this
  focused qualification on an existing label once; it does not overwrite results.
- Alternate fresh baseline/candidate processes for three paired sessions. Warm
  each process for at least five seconds and three complete operation rounds.
  Retain all warmup samples. Record twenty measured rounds and a distinct request
  set after 5.1 seconds of inactivity for expiry; retain every maximum/outlier.
- Run separately instrumented fresh processes. Diagnostic source copies time
  refresh admission/path/attributes, collection preparation, reads/hash/decoding,
  apply/rebuild and Invoke/reply. Stages are nested: do not sum them blindly.
  Process-wide allocation and GC pause/count deltas include concurrent runtime
  activity. Runtime EventListener observations include asynchronously delivered JIT and GC events; absence
  of events is not proof of absence of tiering or scheduling effects.
- Read live worker capabilities before/after each query, outside its timed interval.
  This avoids the core's cached pre-open refreshStats, but the sampling itself can
  perturb execution. Both ordinary variants receive identical sampling treatment.
- Emit per-session median/p90/max, raw JSON, descriptive candidate/baseline ratios
  and unfavorable candidate sessions. No arbitrary statistical acceptance gate is
  encoded. Never discard an unfavorable run or equate a ratio with significance.

Optional settings are `FREEFLIGHT_TRUSTED_BENCH_SESSIONS` (at least 2, default 3),
`FREEFLIGHT_TRUSTED_BENCH_ROUNDS` (at least 10, default 20),
`FREEFLIGHT_TRUSTED_BENCH_WARMUP` (seconds, at least 2, default 5), and
`FREEFLIGHT_TRUSTED_BENCH_SIZES` (`433,5845` by default; 433 is required for mutation
qualification). These are experiment parameters and appear in provenance. Keep
parameters/toolchain/fixture hashes identical across comparisons. Use a new label
for every run. Identical-source controls help reveal noise.

The profile injector fails on source anchor drift rather than silently omitting
stages. Update it with the changed implementation and review instrumentation
separately. Instrumented binaries are never the ordinary candidate. The current
workflow uses SDK-hosted worker assemblies, not self-contained release bundles;
packaged cross-platform and full-MCP qualification remain separate obligations.
Linux syscall receipts supplied by an operator must remain attributed to that
operator and platform; these scripts do not access another machine's `/tmp`.
