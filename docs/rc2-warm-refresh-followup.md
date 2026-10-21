# RC2 trusted refresh follow-up — bounded combined fix

## Outcome

A 24-line runtime change is retained for review on the isolated M6 branch. It
deduplicates ancestor validation only within one trusted Refresh while admitting
cached snapshots, and reuses that iteration’s leaf metadata. Any content read
under that optimization first performs an uncached full-path check. It does not
change public trust policy, graph membership, warnings, expiry, external-input
handling, cancellation, edit hashes or runtime configuration.

The leaf-only and ancestor-only experiments remain rejected as standalone fixes.
Their per-session p90 regressions and original receipts are retained. The combined
version improved full-graph p90 in all three short candidate sessions and all
three longer candidate sessions (early and later windows). It is not uniformly
faster on every measured workload: one 433-file reference session regressed p90
to 4.305 ms versus baseline sessions 3.479–3.627 ms. No promotion, deployment or
cross-platform performance guarantee is implied.

This follows [the initial investigation](rc2-warm-refresh-investigation.md). Its
initial “no runtime optimization retained” disposition remains the historical
record for the leaf-only experiment; this follow-up records the new combined fix.

## What explains the earlier 77–79 ms session?

Equivalent follow-up uses the same 5,845-file/26-project fixture, pinned RC2 SDK,
Debug builds, awaited open/compilation, three warmup rounds, twenty measured rounds
and baseline/candidate/candidate/baseline/baseline/candidate process order.
Diagnostic and ordinary runs are separate. The uninstrumented leaf-only regression
reproduced in another session (p90 approximately 79–82 ms); a later baseline
session also reached approximately 100–103 ms p90. This is not exclusive to the
leaf patch.

Six diagnostic sessions record stage wall time, process CPU time, GC cumulative
pause deltas, gen0/1/2 counts, allocation deltas and managed thread IDs. Both
versions have an early slow mode which usually ends roughly 1.1–1.3 seconds
after the first query starts. Short fixed-count warmup can leave different numbers
of slow requests in the measured window: the faster candidate finishes its nine
warmup requests sooner. This explains why equal warmup counts do not guarantee
equivalent runtime warm-up state. It does not erase the measured user-visible
early latency or justify removing those samples.

Measured slow diagnostic requests generally spent about 73–98 ms in Refresh.
GC pauses were only 0.34–0.80 ms for those measured slow samples. CPU time was
roughly equal to wall time or higher due to other process threads (up to about
2× in some samples), and thread IDs changed both during and outside the slow
mode. All those requests read only 60/80 target bytes and reused 5,844 snapshots.
The large work remains in path validation, including the managed File.GetAttributes
call chain. The evidence argues against full-content revalidation or GC pauses
as the main cause of this mode; it does not provide per-thread scheduler or CPU
core residency traces, nor does process-wide CPU time exclude every scheduling
effect.

Two separate diagnostic-only runtimeconfig controls used unchanged baseline/leaf
DLLs: System.Runtime.TieredCompilation=false and System.Runtime.TieredPGO=false.
Each control ran three fresh sessions/version. Neither reproduced measured
requests above 60 ms. Tiering-off measured maxima were approximately 37–44 ms;
PGO-off maxima approximately 36–45 ms. Ordinary default-runtime follow-up still
contained 16 measured leaf requests above 60 ms in one session. These interventions
support a tiered/dynamic-PGO warm-up contribution, but do not identify the exact
JITted methods or prove the causal history of the earlier untraced session.

The runtimeconfig controls exist only beneath bin/.local/perf-followup. The pinned
SDK targets explicitly map TieredPGO to System.Runtime.TieredPGO. See Microsoft’s
[compilation settings](https://learn.microsoft.com/en-us/dotnet/core/runtime-config/compilation)
for the supported tiering controls and dynamic-PGO behavior. No production switch
is disabled, no environment setting is silently stripped, and no longer/favorable
run replaces the earlier p90 regressions.

## Source and trust argument

The retained code is in workers/roslyn/Program.cs: Refresh and CheckPath. Its
request-scoped set is created inside Refresh only for trusted mode, with an
active watcher, and when forceAll is false. Rename and watcher-unavailable fallback
therefore retain their original full-validation path. The safe-source enumeration
algorithm is unchanged.

The preservation argument is:

1. Every path still performs full-path normalization and the root-relative escape
   rejection. An ancestor cache hit cannot grant a new root or external path.
2. The set contains only successfully checked non-leaf components and is discarded
   when Refresh returns. Each leaf is freshly checked; its FileInfo exists only
   for that loop iteration. No cross-request trust or metadata cache is introduced.
3. A snapshot can be reused only under the existing length/mtime, dirty sequence,
   invalidation generation, five-second age, watcher and force-target conditions.
4. If reuse fails, the optimized in-root path invokes CheckPath without the set
   immediately before OpenCompilerInput. Thus cached ancestor checks cannot authorize
   source bytes. Full validation is at least as close to the read as before.
5. External catalogue entries bypass the set and leaf optimization entirely. Their
   exact-path catalogue, absolute-component validation, guarded opens and read-only
   edit policy remain unchanged. All-or-nothing rename still forces fresh hashes.
6. All graph inputs remain visited. Missing inputs reject; additions/removals still
   require trusted graph reopen. Cancellation and resource accounting remain in
   their existing loop/read locations.

This preserves the documented local single-user, nontransactional path-check
model. It does not prove race-free behavior under arbitrary concurrently hostile
filesystem mutation. In particular, cached snapshot admission may observe an
ancestor checked earlier in the same request, while content reads do not use that
cached authority. Stronger atomic pathname semantics would require a separately
designed handle-relative/openat or Windows handle/reparse policy and its own
cross-platform proof; persistent unchecked path caching is not proposed.

## Correctness and mutation evidence

The combined production worker passed both existing native suites, including
safe-source mutation/expiry/overflow, exact semantics, cancellation/protocol, trusted
graph loading/warning handling and resource checks. The supplemental trusted fixture
passed target reads and preview hashes with preserved metadata, non-target ancestor
replacement/recovery, missing-member rejection, additions/removals on reopen and
whole-graph rereading after watcher bookkeeping overflow.

Permanent trusted regressions now additionally check external-input rename refusal
without a partial preview and external-file symlink replacement on refresh/recovery.
Existing non-target leaf/ancestor symlink and missing-input tests pass. Unix symlink
coverage does not constitute Windows reparse-point qualification.

A diagnostic-only copy injected a deterministic ancestor swap after snapshot
admission and immediately before the production uncached read check. It replaced
the target directory with a link to a disposable outside directory. The request
failed with the symlink error, bytesRead remained exactly 20 before/after, and
restoring the directory recovered the expected target symbol. The test hook exists
only in generated source; no product hook or environment bypass was added.

## Uninstrumented comparison

All default-runtime performance results use direct worker pipes, not complete MCP
routing. Small/full graph fixtures remain synthetic; neither Linux Biztraak nor
Glider was rerun. Builds/tests did not run concurrently with these measurements.
The short full comparison, longer full comparison and small comparison together
contain 2,880 measured semantic responses plus 162 warmup responses, all passing
driver assertions. Each comparison has three fresh processes/version.

The long comparison retains the same first twenty measured rounds separately
from the next hundred; it does not redefine or discard early samples. Longer
runs include periodic revalidation. Faster versions finish equal request counts
sooner, so their wall-time exposure to five-second expiry differs. Raw counters,
all timings, open/compilation time and all maxima are retained.

Each table cell is median / nearest-rank p90 / maximum in milliseconds. Session
numbers are local to each comparison. No pooled result is used to hide a session.

### Full graph, original 20 measured rounds

| Session / version / window | Outline | Definition | References |
| --- | ---: | ---: | ---: |
| 0 / baseline / measured | 35.495 / 40.016 / 41.049 | 35.575 / 41.441 / 42.539 | 36.565 / 43.712 / 44.587 |
| 1 / combined / measured | 14.596 / 36.268 / 37.561 | 14.489 / 36.481 / 39.848 | 15.933 / 37.401 / 39.054 |
| 2 / combined / measured | 14.329 / 37.281 / 38.034 | 14.100 / 37.250 / 38.158 | 15.092 / 38.724 / 39.093 |
| 3 / baseline / measured | 36.650 / 100.611 / 106.563 | 36.034 / 99.805 / 105.409 | 36.927 / 102.695 / 107.384 |
| 4 / baseline / measured | 35.277 / 40.501 / 41.334 | 35.197 / 40.159 / 40.791 | 36.084 / 41.955 / 42.917 |
| 5 / combined / measured | 15.089 / 37.109 / 40.429 | 15.384 / 36.425 / 37.718 | 15.837 / 37.356 / 39.535 |

### Full graph, 120 measured rounds split into windows

| Session / version / window | Outline | Definition | References |
| --- | ---: | ---: | ---: |
| 0 / baseline / early20 | 35.450 / 41.096 / 46.247 | 35.353 / 39.712 / 40.586 | 35.754 / 43.236 / 45.879 |
| 0 / baseline / later100 | 33.414 / 34.958 / 65.209 | 33.250 / 34.460 / 60.950 | 33.756 / 34.867 / 62.777 |
| 1 / combined / early20 | 14.174 / 35.971 / 39.355 | 13.705 / 36.560 / 37.985 | 14.802 / 36.923 / 38.462 |
| 1 / combined / later100 | 13.808 / 19.400 / 23.621 | 13.628 / 18.723 / 29.689 | 14.034 / 21.526 / 40.556 |
| 2 / combined / early20 | 16.255 / 34.587 / 37.304 | 15.792 / 24.969 / 40.163 | 17.323 / 24.158 / 39.132 |
| 2 / combined / later100 | 12.551 / 18.205 / 24.658 | 12.393 / 17.279 / 28.400 | 13.015 / 18.253 / 28.121 |
| 3 / baseline / early20 | 38.115 / 41.686 / 97.113 | 37.964 / 40.921 / 52.771 | 39.198 / 42.131 / 48.063 |
| 3 / baseline / later100 | 34.507 / 36.602 / 58.219 | 34.334 / 37.068 / 56.603 | 34.888 / 38.372 / 59.754 |
| 4 / baseline / early20 | 36.895 / 39.830 / 40.886 | 36.454 / 41.417 / 42.025 | 37.914 / 42.573 / 47.962 |
| 4 / baseline / later100 | 34.604 / 36.340 / 55.775 | 34.444 / 37.784 / 55.344 | 34.890 / 37.264 / 63.791 |
| 5 / combined / early20 | 15.745 / 37.524 / 38.112 | 15.097 / 36.828 / 37.591 | 16.549 / 39.412 / 39.921 |
| 5 / combined / later100 | 13.420 / 20.155 / 25.892 | 12.925 / 17.821 / 27.465 | 13.232 / 19.537 / 25.545 |

### 433 files / 2 projects, 20 measured rounds

| Session / version / window | Outline | Definition | References |
| --- | ---: | ---: | ---: |
| 0 / baseline / measured | 2.491 / 2.753 / 3.537 | 2.470 / 2.761 / 3.266 | 3.357 / 3.483 / 5.144 |
| 1 / combined / measured | 0.893 / 1.077 / 1.689 | 0.880 / 0.943 / 1.042 | 1.687 / 3.218 / 4.910 |
| 2 / combined / measured | 0.875 / 1.011 / 1.213 | 0.863 / 0.924 / 3.532 | 1.654 / 2.111 / 5.038 |
| 3 / baseline / measured | 2.479 / 2.740 / 5.938 | 2.480 / 2.678 / 5.643 | 3.277 / 3.476 / 4.504 |
| 4 / baseline / measured | 2.521 / 2.823 / 6.393 | 2.483 / 2.597 / 2.779 | 3.267 / 3.627 / 5.146 |
| 5 / combined / measured | 0.887 / 1.061 / 1.740 | 0.876 / 0.941 / 1.178 | 1.713 / 4.305 / 5.379 |

## Diagnostic stage and count observations

A separate 123-round combined profile measured a first-twenty-round Refresh median
of 16.359 ms: path checks 11.883 ms, cached length/mtime 0.001 ms, read/hash/text
including uncached pre-read validation 0.090 ms, apply/bookkeeping 0.794 ms.
Median process allocation was about 9.62 MB/refresh, and GC pause 0.479 ms.
These instrumented stage numbers are not production latency results.

Each unchanged full-graph Refresh made exactly 5,902 managed attribute checks:
5,845 fresh leaves, 53 distinct ancestors, and four uncached pre-read components
for the target. The original profile counted 23,380 managed attribute checks plus
fresh FileInfo metadata. This is a managed-call reduction, **not** a measured
kernel syscall count. Target bytes remained 60/80 and reused snapshots 5,844.

The longer combined profile retained expiry requests too: twelve adjacent requests
reread subsets of 16–40 KB, with Refresh about 18–28 ms. Snapshots have per-file
validation times, so expiry can be distributed across requests; an explicit idle
wait can instead make the entire graph expire at once. Neither pattern is hidden
or relabeled as ordinary target-only refresh.

## Remaining obligations and disposition

- Retained as a locally tested, bounded source fix for review; not pushed, merged
  or deployed. No universal tail-latency improvement is claimed, especially given
  the small-graph reference p90 regression.
- Exact tiering-method attribution needs runtime/JIT event traces aligned to query
  boundaries. CPU observations are process-wide; per-thread scheduling, CPU core
  residency and frequency were not traced. Do not claim the historical slow mode
  has been proven to a single runtime method.
- Linux/Windows qualification, kernel syscall before/after tracing, the complete
  packaged Test SDK external-input matrix and complete core/MCP timing remain.
  The trusted external-input worker tests are narrower than that packaged matrix.
- Broad workspace searches were not benchmarked. Public core capabilities still
  expose the pre-open refreshStats snapshot; a live telemetry repair remains separate.
- Snapshot/watcher semantics and the documented concurrent-mutation limitation
  remain. No durable path cache or watcher-only authority is introduced.

Receipts: bin/.local/perf-followup/{diagnostic-equivalent,plain-equivalent,
tiering-off,pgo-off,ancestor-equivalent,combined-equivalent,combined-long,
combined-small}.json; session-summary.json; diagnostic-equivalent-*.stderr;
combined-profile-parsed.json; race-check.json; boundaries-combined.json;
test-safe-combined.log; test-trusted-final.log; and receipt-manifest.json.
All earlier bin/.local/perf receipts and rejected patches remain intact. The
follow-up adds no Docker, service, Linux-host, Biztraak, active MCP, publication
or deployment changes. No pending approval blocker remains.
