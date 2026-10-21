# Glider behavior and the remaining performance gap

This investigation compares official Glider 13.3.0 with shipped FreeFlight 97c1342
and the local expiry candidate. It uses disposable copies of the synthetic fixture,
not Biztraak, and does not edit active MCP configuration. The product server source
is not published in the linked public repository; no unpublished implementation
is asserted or decompiled.

## Documented versus observed evidence

The [official public repository](https://github.com/glidermcp/glidermcp) explicitly
contains support resources, plugins and configuration templates, not product server
implementations. Installed 13.3.0 NuGet metadata identifies that repository and
commit `57bd49d82acfb982278560e982e269f291f6bb0f`; this is not evidence that server
source exists there. Its package README/license and official NuGet archive were
inspected locally. The version remains pinned despite newer versions being listed.

The current [sync reference](https://glidermcp.com/glider/tools/sync) documents two
policies: named paths compare content, while an unnamed sweep trusts length and
timestamp. An unnamed call can do no work without pending watcher changes unless
forced. This is current documentation, not an assumption about installed 13.3.0;
the workflow records its actual tool schema and tests its behavior independently.

The [status reference](https://glidermcp.com/glider/tools/server-status) documents
cache revision, watcher activity and background compilation readiness. The
[tool reference](https://glidermcp.com/glider/tools) distinguishes workspace sync
from structural reload. Both products await compilation readiness in our ordinary
performance comparison. A faster load response alone is not counted as faster
steady state.

Existing unmodified full-graph Glider 13.3 receipts report watcher enabled,
revision 1, zero received events, zero sync runs and zero files considered after
many queries and a 5.1-second idle period. These are exposed watcher counters,
not a syscall trace or proof that no other internal work happens. Combined with
sub-millisecond unchanged queries, they motivate testing incremental/cached
workspace use rather than attributing the advantage to a faster whole-graph scan.

FreeFlight source confirms that every semantic query first admits the entire
graph, and expiry performs fresh uncached reads and hashes. Instrumented Roslyn
outline work is only about .02–.06 ms; admission and read scheduling dominate the
common floor. Its definition caller is read freshly, while dependencies can use
unexpired snapshots subject to dirty/generation invalidation. We do not claim
that this means every dependency is reread on every query.

## Reproducible diagnostic design

`benchmark.trusted.behavior` reuses the existing MCP transport and qualified
published/native binaries. It clones the immutable fixture into its own receipt,
changes only a target declaration to add two same-length method names, restores
with the pinned SDK, and loads all original projects/documents. It runs one
process at a time, with rotated product order and separate fresh sessions.

- Repeat one outline versus distinct targets, recording exact known names, raw
  responses and encoded JSON payload sizes. These timings are diagnostic, not a
  replacement for the uninstrumented head-to-head.
- Swap same-length method names in the target project and query definition from
  an unchanged caller project. Test ordinary mtime and restored same-size/mtime.
- Change one caller from Value to Other, then query references to Value. Compare
  the complete expected invocation location set, including FreeFlight end ranges.
- Observe immediately, then at scheduled 25/100/250/500/1000/5100 ms offsets.
  Actual elapsed times are recorded; slow queries can exceed requested offsets.
- Keep passive probes separate from a target outline, forced sweep and named-path
  sync. Record watcher/cache state alongside each observation. Never disable
  watchers, broaden trust, or modify live projects.

A stale but structurally valid response is evidence, not a harness assertion
failure. The oracle accepts only the exact old or new semantic state and records
which was returned. Explicit named sync must establish the new state. These tests
cannot prove behavior under every watcher overflow, filesystem or interleaving;
absence of a stale result in a bounded run is not a stronger contractual guarantee.

FreeFlight's core-level capability refresh counters are cached and do not represent
live worker reads; the behavior workflow preserves them as raw responses only.
Read/byte attribution uses the separately instrumented worker receipts. Glider's
watcher counters likewise describe their exposed subsystem, not every possible
filesystem call. Canonically encoded response JSON bytes are a payload diagnostic,
not a wire capture or a standalone serialization-cost measurement.

Package metadata also differs: installed Glider declares Roslyn
`5.8.0-1.26257.103` and ModelContextProtocol `2.2.0`; FreeFlight's qualified worker
declares Roslyn `5.9.0`. These `.deps.json` entries identify dependencies, not which
algorithms are used. The semantic stage in our profile is already much smaller
than admission, so a compiler-version explanation alone would not explain that
measured floor. No unpublished Glider algorithm is inferred from dependency names.

## Completed edit behavior repeat

`bin/.local/glider-comparison/freshness-qualified/` passed 12 fresh processes,
two sessions per product/graph, with all 36 edit scenarios returning the new
state by their final passive observation. Named sync controls also passed.

Cells below are first-observed-fresh completion times for the two sessions (ms).
They are observation bounds, not exact event latency: polling is discrete and
query execution takes time. Reference probes are the first reference operation in
each process, so their duration includes method warm-up as well as the edit.

| Files | Product | Ordinary target edit | Preserved metadata edit | Cross-project caller edit |
| --- | --- | ---: | ---: | ---: |
| 433 | freeflight | 13.34 / 7.79 | 38.93 / 39.89 | 79.01 / 77.88 |
| 433 | candidate | 7.88 / 7.34 | 40.71 / 38.41 | 88.28 / 81.73 |
| 433 | glider | 61.29 / 60.99 | 43.17 / 37.82 | 129.54 / 124.69 |
| 5845 | freeflight | 16.05 / 17.56 | 12.54 / 11.85 | 80.94 / 78.37 |
| 5845 | candidate | 14.84 / 14.61 | 9.16 / 11.66 | 77.37 / 74.94 |
| 5845 | glider | 57.50 / 64.56 | 45.72 / 40.90 | 166.51 / 167.44 |

Glider returned an old definition on the first ordinary and preserved-metadata
probe in these sessions, then returned the new definition. FreeFlight also returned
an old dependency definition on the first preserved-metadata probe in the small
graph; watcher invalidation subsequently refreshed it. Thus neither product is
claimed to guarantee instantaneous dependency updates for metadata-preserving
edits. FreeFlight retains its independent periodic revalidation path.

Glider watcher-counter deltas during each edit were 2–3 files considered and one
file synchronized, on both graph sizes. No sync failures or watcher errors were
reported. The restored timestamp edits were detected; the hypothesis that Glider
simply ignores all same-size/same-mtime edits is contradicted by these observations.
The no-path force sweep later considered the whole graph and skipped unchanged
metadata, as documented. This does not establish how lost watcher events recover.

Reset events can overlap the start of these multi-case sessions. The separately
labelled quiescent repeat below uses only one edit case per fresh process, skips
redundant reset writes and waits for zero pending/active watcher work.

### Own stage attribution

Full-graph instrumented steady-state medians from `expiry-inline-v2`, excluding
samples that expired documents (excluded samples remain in raw receipts):

| Operation | Refresh ms | Semantic ms | Samples |
| --- | ---: | ---: | ---: |
| Outline | 8.169 | .030 | 46 |
| Definition | 6.049 | .040 | 48 |
| References | 5.318 | .517 | 49 |
| Broad search | 5.124 | 2.341 | 49 |

This source-attributed common refresh floor explains much more of tiny-query cost
than Roslyn semantic work. It does not quantify Glider internals. Larger search
responses also differ in payload size; bytes alone cannot isolate serialization
or IPC time. Those are secondary investigation targets, not established causes.

### Retained pilot issues

`freshness-pilot` is excluded from product conclusions: its added target class
was mistakenly static despite existing instance callers, and its Glider sync
argument followed the website string example instead of the installed array
schema. `freshness-pilot-v2` corrected both and passed all products. The workflow
now builds each fixture first, checks Glider compiler diagnostics, and records
the actual tool schema. Original receipts remain local.

## Quiet-workspace confirmation

`bin/.local/glider-comparison/freshness-quiescent/` passed another 12 fresh
processes. Only the preserved-metadata edit ran in each process. Redundant reset
writes were skipped, both target methods were already compiled, and the workflow
waited 1.1 seconds with no pending/active watcher work before mutation.

Every Glider session began with zero events, queued paths, sync runs and files
considered. Each edit then produced exactly one queued path, one sync run, one file
considered and one file synchronized, for both 433 and 5,845 files. No watcher
error or sync failure was reported. This rules out prior reset events as the
reason this run detected metadata-preserving edits.

All products initially returned the old dependency definition in these 12 cases.
All returned the new definition by a later observation, before the five-second
check. First-observed-fresh completion times (ms):

| Files | Shipped | Candidate | Glider |
| --- | ---: | ---: | ---: |
| 433 | 57.53 / 59.62 | 59.06 / 64.83 | 99.51 / 84.17 |
| 5845 | 69.91 / 71.82 | 46.25 / 59.43 | 99.21 / 96.93 |

### Repeated versus distinct queries and payloads

These are diagnostic requests, interleaved in alternating order after three warm-up
rounds. Outline targets vary; repeated versus distinct searches have equal result
counts (one on the small graph, 111 on the full graph). Each cell below aggregates
40 observations across two fresh sessions: median / p90 / max ms, then median
canonical response JSON bytes. This is not the ordinary benchmark table.

| Files | Product | Repeated outline | Distinct outline | Repeated search | Distinct search |
| --- | --- | ---: | ---: | ---: | ---: |
| 433 | freeflight | 1.199 / 2.349 / 3.384; 2731 B | 1.274 / 2.094 / 4.000; 2101 B | 1.017 / 1.032 / 1.166; 831 B | 1.021 / 1.050 / 1.229; 831 B |
| 433 | candidate | 1.136 / 1.801 / 7.459; 2731 B | 1.186 / 1.779 / 9.983; 2101 B | 1.253 / 1.322 / 1.469; 831 B | 1.243 / 1.288 / 3.826; 831 B |
| 433 | glider | 0.825 / 1.196 / 1.692; 2640 B | 0.863 / 1.339 / 1.873; 2237 B | 0.815 / 0.962 / 1.041; 1235 B | 0.855 / 0.995 / 1.078; 1235 B |
| 5845 | freeflight | 7.329 / 8.260 / 12.951; 2739 B | 7.322 / 8.028 / 8.604; 2107 B | 14.198 / 16.208 / 21.765; 71833 B | 13.955 / 15.876 / 20.283; 71833 B |
| 5845 | candidate | 5.315 / 5.723 / 9.990; 2739 B | 5.441 / 5.858 / 13.469; 2107 B | 12.379 / 14.210 / 19.895; 71833 B | 12.360 / 13.750 / 22.681; 71833 B |
| 5845 | glider | 0.643 / 0.912 / 1.423; 2641 B | 0.772 / 1.213 / 1.337; 2238 B | 5.017 / 5.808 / 26.720; 41569 B | 5.072 / 6.231 / 27.137; 41569 B |

Glider remains fast when the target or equal-cardinality search changes. These
observations do not support a large same-query-answer-cache effect as the main
explanation. They cannot prove that no internal cache exists. Its larger workspace
does not create the same tiny-outline floor, while the outline payload remains
about 2.6 KB on either graph. FreeFlight outline payload is about 2.7 KB; this small
difference alone does not explain the measured multi-millisecond gap.

Broad C5 search responses contain 956 candidates on the full graph. Canonical JSON
is 617,037 bytes for FreeFlight and 351,239 for Glider in this fixture. That larger
payload is a plausible secondary search cost, but no serialization percentage or
causal attribution is claimed from bytes alone. Raw results and timings remain in
the receipt; they are not pooled into the ordinary benchmark.

## What gives Glider its observed edge

The strongest evidence is incremental workspace maintenance: unchanged queries
avoid the measured whole-graph refresh floor, and a single observed edit leads to
one-file synchronization even in the full solution. Our source/profile establishes
the opposite work pattern for FreeFlight: full leaf admission on every query and
full content revalidation when snapshots expire. Roslyn text reuse already exists
in FreeFlight; adding another result cache does not remove that preceding work.

This is an observed behavioral explanation supported by official sync/status
documentation, not a claim about unpublished implementation classes. Compilation
readiness was awaited in both tools. Same-size/same-mtime edits were successfully
detected by Glider when watcher events arrived; do not describe its speed as merely
returning stale answers. Both products showed brief pre-event stale dependency
answers in the focused test. Lost-event and overflow recovery guarantees for
Glider remain unproven; we did not disable its watcher or infer guarantees from
the absence of failures. No Glider five-second content-revalidation guarantee was
established from the documentation or these tests.

## Concrete contract boundary and next options

The qualified inline-read candidate reduces expiry CPU/latency while retaining
current behavior. It remains local; this does not achieve the goal of beating
Glider on tiny queries. Further constant-factor improvements are possible, but
these measurements do not establish that they can close the gap.

The direct incremental-admission design would stop stat-checking unchanged,
non-target graph leaves before every query, relying on invalidation plus periodic
revalidation instead. Even if uncached checks before every content read, external
input restrictions, edit hashes and the five-second content policy were retained,
an unrelated ancestor/leaf replacement would no longer be rejected by every query
before its next invalidation/revalidation. That changes the explicitly preserved
per-query graph-validation contract. It has not been implemented. A decision is
needed before pursuing that design. Keeping strict admission means retaining the
measured graph-sized query work while optimizing its implementation.

Background expiry maintenance is another design option, not a demonstrated free
win: it would reread the graph during idle periods and could contend with incoming
queries. Equivalent age/error guarantees and total idle CPU/I/O need qualification
before adoption. No background maintenance was added or hidden from these results.

## Repeat commands

Use a new label. This consumes the pinned, qualified native binaries and clones
the immutable fixture; it does not change the original fixture or user projects.

```sh
DOTNET_CLI_USE_MSBUILD_SERVER=0 \
FREEFLIGHT_BEHAVIOR_LABEL=freshness-repeat \
FREEFLIGHT_BEHAVIOR_COMPARISON="$PWD/bin/.local/glider-comparison/target-expiry-inline-v2" \
FREEFLIGHT_BEHAVIOR_SIZES=433,5845 FREEFLIGHT_BEHAVIOR_SESSIONS=2 \
dockpipe --workflow benchmark.trusted.behavior
```

For the focused one-edit confirmation also set
`FREEFLIGHT_BEHAVIOR_CASES=preserved-metadata-target-edit`. The current workflow
includes quiescent resets and interleaved repeated/distinct query phases for both
forms. Earlier driver versions are frozen through their receipt hashes and local
source history; raw prior receipts are retained.
