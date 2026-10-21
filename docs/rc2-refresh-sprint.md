# RC2 trusted-refresh optimization sprint

This is the local M6 follow-up to [the residual investigation](rc2-residual-refresh-investigation.md).
The named baselines are shipped `39c3cc83b04f21e352e7885c0589d39947b9efa4`
and local `80ea256263699b9efed0917cf0e10ac81f4d2c61`. Measurements here use
synthetic dependency-free projects and the pinned RC2 SDK on Darwin ARM64.
They are not a rerun of the operator's Linux/Biztraak/Glider measurements.

## Iterations and retained evidence

Every label below lives under `bin/.local/benchmarks/trusted/`; provenance records
source and fixture hashes, SDK identity and driver hashes. Ordinary and diagnostic
processes are separate. Baseline/candidate processes never run concurrently.

| Receipt | Change / interpretation |
| --- | --- |
| `sprint-read-reuse` | `74b3bc6`: one request-local read buffer; avoid decoding when the freshly read SHA-256 equals the committed hash. Steady-state timings essentially flat; expiry allocation decreased, expiry timings mixed. |
| `sprint-lexical` | `8d9007d`: retain sorted canonical graph identity and lexical parent strings until reopen. All measured median/p90 pairs improved in this run. No filesystem authority is retained. |
| `sprint-fresh-info` | Preparation failed on an ambiguous diagnostic anchor; no timing used. |
| `sprint-fresh-info-v2` | `3084d82`: retain FileInfo objects, explicitly Refresh before every use of their metadata. All measured median/p90 pairs improved in this run. |
| `sprint-padded-control` | Identical `3084d82` sources, 4 KiB files, three sessions each, 2,000 rounds. Near-parity medians/p90; small-graph reference p90 ratio 1.048 is retained as noise evidence. |
| `sprint-parallel-metadata` | Preliminary bounded four-way metadata admission, 4 KiB files, 2,000 rounds. Full-graph median ratios 0.478–0.565, p90 0.492–0.588 against `3084d82`. Not the final candidate: error timing needed refinement. |
| `sprint-parallel-crossover` | Qualification stopped on unchanged baseline: the new resource-order test used a limit too low for project loading. No timing used. |
| `sprint-parallel-eight` | Eight versus four workers with 14 reference sites and C5 search. Full outline median/p90 ratios 0.872/0.932, but diagnostic mean CPU rose from 12.006 to 18.592 ms per outline and small-graph tails regressed. Rejected as the default; retained as a latency/CPU tradeoff. |
| `sprint-parallel-two` | Four versus two workers at 256/433/5845 files. Two reduced diagnostic mean process CPU but worsened every measured p90 pair (full outline ratio 1.411); rejected. Source snapshot and patch retained. |
| `sprint-parallel-crossover-v2` | Corrected serial error ordering passed qualification/transaction guards and all six graph sizes. Parallelism regressed 16-file median/p90 on every operation; 128-file outline p90 ratio 1.019, definition 1.001. All median/p90 pairs from 433 files upward improved. This motivates a serial small-graph path, with the 256-file boundary tested separately. |

Old rejected leaf-only/ancestor-only experiments and their unfavorable p90 evidence
remain in `bin/.local/perf*`. None is silently reinstated by this work.

## Source and security reasoning

`SourceEngine.Invoke` serializes engine work through the protocol gate and runs
Refresh before semantic operations. Trusted membership is fixed until reopen;
therefore immutable canonical ordering/parent strings can be reused. The semantic
maps and Roslyn solution remain staged until all checks succeed. FileInfo identity
can be reused only because `Refresh()` is called on every request before metadata
is consumed. The [documented API contract](https://learn.microsoft.com/en-us/dotnet/api/system.io.filesysteminfo.refresh?view=net-10.0)
explicitly distinguishes updating that snapshot from reading cached attributes.

The parallel experiment partitions metadata admission into at most four contiguous
ranges. Each partition owns a request-local ancestor set and distinct FileInfo
objects. Snapshot/external-input maps are read-only during the joined prepass.
There are no parallel content reads or Roslyn mutations. Cancellation is checked
per file and after joining. A metadata error is retained with its sorted index and
reported when the serial loop reaches it; earlier resource/read errors retain
precedence. No failed prepass grants permission to consume unrefreshed metadata.
The first-error index stops the serial loop before any unvalidated suffix.

Every content read still performs uncached path validation immediately before
open, including external inputs on the parallel path. Fresh target reads, external
input read-only restrictions, bounded reads and aggregate resource checks, watcher
generations, five-second expiry, and edit-preview hashes remain required. Parent
strings and FileInfo objects are bounded by the loaded graph and cleared on reopen.
This does not create an atomic filesystem sandbox; the existing concurrent-hostile
filesystem race limitation remains. No watcher-only admission is introduced.

## Diagnostic observations and limits

At `3084d82`, the padded full-graph control's outline expiry Refresh was about
183–186 ms: opening streams accounted for about 76 ms, uncached path checks about
38 ms, read I/O about 18 ms, hash append about 12 ms and hash construction about
1.8 ms. These stages overlap/nest; do not add them as independent percentages.
Hash-context reuse was not implemented because measured construction was a small
part of expiry. Open-handle caching would undermine replacement freshness and is
not proposed. Parallel content reads would require additional proofs for bounds,
cancellation, resource/error ordering and transactional failure, so remain deferred.

The preliminary parallel diagnostic full-graph outline Refresh median was 3.364 ms
versus 7.037 ms serial, with admission wall time 2.723 ms. Aggregate metadata-refresh
time rose from 4.547 to 7.368 ms: reduced latency trades for concurrent work.
Managed attribute-call counts rose from 5,910 to 5,919 due to partition-local
ancestor checks; these are not OS syscall counts. Both read the target's 4,096 bytes
and reused 5,844 snapshots. Approximate process allocation deltas were 270,504 versus 89,608
bytes in those instrumented builds; instrumentation and concurrent runtime activity
are included. Median GC pause was zero, which does not exclude individual pauses.
All raw tails and runtime event observations remain in the receipts.

The final boundary run additionally passed five failed-refresh guards per variant,
including a deterministic ancestor swap after admission and before read. The swap
was rejected with zero additional source bytes read, and recovery succeeded. This
seam exists only in generated qualification binaries, never production or timing
builds. Final qualification and release status will be recorded after the sprint. These
intermediate observations alone do not qualify Linux/Windows packages or establish
a Glider performance win.
