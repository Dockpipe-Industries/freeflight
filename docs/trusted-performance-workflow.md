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
  The optional padding setting enlarges each file with a deterministic comment.
  These are simple source files with one controlled cross-project call, not a
  realistic business application. Graph loading includes awaited compilations.
- Run the existing `test_worker.py` and `test_trusted.py` suites for both variants,
  including exact semantics, resource limits, cancellation and external inputs.
  A reused mutation asset adds preserved-timestamp hashes, non-target ancestor
  replacement, missing input, additions/removals on reopen and overflow recovery.
  It also checks that an earlier resource failure precedes a later missing file.
- Build a test-only transaction guard from each immutable source snapshot. On a
  failed Refresh it compares the committed solution and all three dictionaries
  with their entry state. Exercise a late missing input after an earlier staged
  target update, ancestor replacement and missing-input recovery. This guard is
  never present in timed builds. A generated test-only seam also replaces the
  target ancestor after admission but before the uncached read check, asserting
  rejection with zero additional source bytes read and preserved committed state.
  `benchmark.trusted.transaction` can run this
  focused qualification on an existing label once; it does not overwrite results.
- Alternate fresh baseline/candidate processes for three paired sessions. Warm
  each process for at least five seconds and three complete operation rounds.
  Retain all warmup samples. Record twenty measured rounds and a distinct request
  set after 5.1 seconds of inactivity for expiry; retain every maximum/outlier.
- Run separately instrumented fresh processes. Diagnostic source copies time
  refresh admission/path/attributes, collection preparation, reads/hash/decoding,
  apply/rebuild and Invoke/reply, plus stream open/read/hash phases. Stages are
  nested: do not sum them blindly. Parallel stage totals aggregate worker work;
  `parallelAdmissionWall` records elapsed prepass time separately.
  Process CPU deltas and thread-pool counts are diagnostic observations too; CPU
  timer granularity can make individual short samples noisy, so retain totals.
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
`FREEFLIGHT_TRUSTED_BENCH_SIZES` (`433,5845` by default; allowed sizes are
16, 128, 256, 433, 1024, 2048 and 5845; 433 is required for mutation qualification).
`FREEFLIGHT_TRUSTED_BENCH_PADDING` sets minimum bytes per source file (0 by default,
maximum 65536); 4096 is useful for a roughly 24 MB full graph. Smaller graphs have
two projects; the 5845-file graph has 26. These are experiment parameters and appear in provenance. Keep
parameters/toolchain/fixture hashes identical across comparisons. Use a new label
for every run. Identical-source controls help reveal noise.

The profile injector fails on source anchor drift rather than silently omitting
stages. Update it with the changed implementation and review instrumentation
separately. Instrumented binaries are never the ordinary candidate. The current
workflow uses SDK-hosted worker assemblies, not self-contained release bundles;
packaged cross-platform and full-MCP qualification remain separate obligations.
Linux syscall receipts supplied by an operator must remain attributed to that
operator and platform; these scripts do not access another machine's `/tmp`.

Long runs cross snapshot expiry during ordinary sampling. `bulk-reads.json`
separately summarizes samples with more than one document read; the complete
steady-state summary still includes them. `tails.json` joins slow diagnostic
samples to actual read reasons, GC and runtime event observations. No outlier is
removed from the ordinary median/p90/max summaries. See the
[sprint record](rc2-refresh-sprint.md) for retained controls and failed attempts.

## Optional full MCP comparison

After `core.build` and a completed trusted comparison, reuse its immutable label:

```sh
FREEFLIGHT_TRUSTED_BENCH_LABEL=my-comparison \
FREEFLIGHT_TRUSTED_MCP_LABEL=mcp \
dockpipe --workflow benchmark.trusted.mcp
```

This reuses the existing `benchmark` MCP client, exact query assertions, frozen
workers and fixture hashes. It verifies the graph's file/project counts through
MCP, records the core binary hash, and runs fresh alternating processes with the
same warmup policy. Optional `FREEFLIGHT_TRUSTED_MCP_ROUNDS` overrides measured
rounds (at least 10). Results live in `LABEL/mcp`; use a new MCP label to retain a
failed attempt or repeat. All configuration files are disposable fixture-specific
startup files. Active MCP settings are never changed. The existing client's RSS
sampler is disabled to avoid periodic process enumeration during this comparison.

These are SDK-hosted workers through the actual C++ endpoint, not self-contained
release bundles. The core's cached refreshStats are intentionally not sampled as
live telemetry. MCP loading includes engine startup and awaited compilations;
startup discovery, steady state and idle-expiry samples remain separate. Do not
subtract separately run worker and MCP medians to claim an exact IPC cost.

The post-idle sequence starts with outline, followed by definition, references and
symbol search. The first request normally triggers bulk expiry reads; the later
requests observe that refreshed state. They are not four independent full-expiry
trials. Loading includes initial compilation; measured warmup remains separate.

Broader fixture controls are `FREEFLIGHT_TRUSTED_BENCH_CALLERS` (default 1, up to
1000, capped by available members in each fixture) and
`FREEFLIGHT_TRUSTED_BENCH_QUERY` (default C58; queries exceeding the worker's 1000
symbol limit are rejected during preparation). For example, 14 callers and C5
produce 14 exact cross-project references and 956 named-type results in the
5845-file graph. All locations and counts are checked. `FREEFLIGHT_TRUSTED_BENCH_FIRST`
can be baseline (default) or candidate to reverse the first pair in a repeat.

Current diagnostic builds use `GC.GetTotalAllocatedBytes(true)`. Older receipts
used the approximate `false` mode; do not compare those absolute values as though
the measurement were identical. The [API documentation](https://learn.microsoft.com/en-us/dotnet/api/system.gc.gettotalallocatedbytes?view=net-10.0)
notes that precise counting costs more and excludes native allocations. Ordinary
binaries never contain this instrumentation. `tail-observations.json` supplies a
compact view of each operation's five slowest steady samples per session, including actual reads
and available diagnostic observations; it does not assign speculative causes.
