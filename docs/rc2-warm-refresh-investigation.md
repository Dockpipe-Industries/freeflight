# RC2 trusted warm-query investigation — M6, 2026-10-21

## Scope and provenance

Baseline source is `c2a55ddeed79a6130d75af6a50cf6b096bcc76d6`, copied into an
independent checkout on `m6.local` (Darwin ARM64). The installed SDK is
11.0.100-rc.2.26504.105. All builds and fixtures are native; Docker, Linux pop-os,
Biztraak, active MCP configuration, deployment and publication were not accessed
or changed. No merge or deployment is part of this investigation.

The supplied Linux report is external diagnostic evidence, **not our rerun**.
Its 31,015 versus 2,326 `lstat` calls and approximately 49 ms full-solution outline
latency are not local receipts. Linux `/tmp` receipts were not available here.
Our comparable fixture has 433 files/2 projects or 5,845 files/26 projects, all
explicitly authored dependency-free net11.0 SDK projects. Every source is loaded.
The graph is selected through its root project, which references the other
projects; it is not the private Architecture.sln or its source content. It has
no external compiler inputs; external input behavior is exercised separately by
the existing trusted suite.

## Source-confirmed cause

All supported semantic queries call `Refresh` before Roslyn work
(`workers/roslyn/Program.cs`, baseline lines 282–283). Trusted refresh copies
`documents.Keys`, sorts the list and stages dictionaries and a set (369–407).
Unlike safe-source mode it does not enumerate directories or reevaluate MSBuild.
Trusted membership changes require reopen; deletion of a loaded input fails
rather than silently removing it from the graph.

The loop at 415–435 calls `CheckCompilerInput` for every document **before** the
snapshot fast path. Ordinary workspace inputs reach `CheckPath` (514–520), whose
loop at 556–569 calls `File.GetAttributes` for each relative path component.
Then a new `FileInfo` fetches length and modification time. Thus all shared
ancestors are checked repeatedly, even with unchanged snapshots and a tiny target.
This is O(sum of document path depths), not O(target size). The supplied repeated
`source/`, `Application` and `Model` calls match this loop. The external catalogue
uses separate absolute-component validation; it is not bypassed by this analysis.

Snapshot reuse requires matching length/mtime, dirty sequence and invalidation
generation, an active watcher, age under five seconds and a non-forced target.
The queried file is always read and rename forces all source reads. Expiry,
watcher invalidation or unavailable watchers independently trigger bounded reads
and hashes (426–470). Watcher errors increment the generation, and more than
4,096 dirty entries also invalidate all snapshots (123–153). Whole-graph checks,
sorting and dictionary copies still run without invalidation.

The reported zero counters have a separate source-confirmed explanation:
`src/server.cpp` requests and stores capabilities **before open** (335–355), and
`engine.capabilities` returns that stored object (576–577). Workspace status uses
the same stored object (379). `bytesRead`, `reusedSnapshots` and generation update
in the shared worker refresh path, including trusted mode. Direct worker capability
requests in this investigation see those updates. The core's startup snapshot is
not live refresh telemetry. The investigation does not change that public API.

## Bounded candidate

Reuse the `FileInfo` metadata obtained when checking the workspace input's leaf
attributes for the immediately following length/mtime checks. Ancestor validation
still happens for every file on every request. The object is local to that loop
iteration; there is no cross-file or cross-request cache, no watcher-only admission,
and no change to the five-second interval. External inputs continue through their
existing validator and no-follow/nonblocking open. Target reads, resource limits,
cancellation, source hashes and all-or-nothing edit previews retain their paths.

This does **not** reinstate the reverted request-scoped ancestor cache described
in [hotpath-performance.md](hotpath-performance.md). It addresses the redundant
leaf metadata fetch; repeated ancestor validation remains the dominant cost.
Portable path checks retain the existing concurrent hostile-mutation limitation
in SECURITY.md. No race-free filesystem isolation claim is added.

## Measurement method

Uninstrumented builds use the same Debug build configuration and pinned dependency
lock; no runtime/JIT settings changed. Timings are direct worker JSON round trips,
including pipe framing and response parsing, but exclude C++ core routing and its
IPC/serialization. No Glider comparison was run. Open is timed separately and
already awaits each project's compilation in this RC2 source (240–250); it must
not be compared to a tool that returns before compilation. Each process then gets
three warmup rounds and twenty measured rounds of outline, cross-project definition
and references. Definition checks the exact declaration start and file; references
check the one expected call-site file; outlines check exact symbol names.

The comparison order is baseline, candidate, candidate, baseline, baseline,
candidate for each graph. There are three fresh processes/version/graph and 60
samples/operation/version/graph. p90 is nearest rank. All samples and maxima are
retained; process sessions, not individual sequential requests, are the meaningful
replication unit. Tests and builds were not run concurrently with the comparison.
Fresh processes do not imply cold OS caches or an otherwise idle host.

Private instrumented source copies record refresh, path checks, metadata, reads,
apply/bookkeeping, engine invocation and worker reply timing. Reported semantic
residual includes admission and other work outside Refresh, not just Roslyn.
Allocation uses process-wide `GC.GetTotalAllocatedBytes(false)` deltas, including
other runtime threads; it is approximate. Counters count managed attribute calls,
**not kernel syscalls**. Traced production latency is not claimed.

## Results and disposition

**No runtime optimization is retained.** The candidate passed the local correctness
checks, but one full-graph candidate session regressed p90 to 77–79 ms while all
three baseline sessions stayed around 39–42 ms. A pooled p90 obscures this
session-level regression. The experimental runtime diff is preserved at
`bin/.local/perf/experimental-leaf-metadata.patch`; production Program.cs is byte
identical to the pinned baseline. Only regression tests and investigation docs
remain on the branch. This is an evidence-backed proposal, not a shipping fix.

Uninstrumented pooled results (milliseconds; 60 samples per cell):

| Files | Operation | Baseline median / p90 / max | Experiment median / p90 / max |
| ---: | --- | ---: | ---: |
| 433 | symbols | 2.487 / 2.792 / 5.670 | 2.000 / 2.238 / 5.284 |
| 433 | definition | 2.422 / 2.702 / 5.580 | 1.983 / 2.377 / 5.032 |
| 433 | references | 3.213 / 3.624 / 5.541 | 2.806 / 3.178 / 7.330 |
| 5845 | symbols | 36.314 / 40.973 / 47.735 | 30.269 / 37.053 / 81.959 |
| 5845 | definition | 35.758 / 40.957 / 46.710 | 29.867 / 34.901 / 84.214 |
| 5845 | references | 37.279 / 41.880 / 58.217 | 31.102 / 36.657 / 84.076 |

Per-session results are necessary to interpret those pooled numbers:

| Files | Operation | Version | Session: median / p90 / max (ms) |
| ---: | --- | --- | --- |
| 433 | symbols | baseline | 0: 2.621 / 2.792 / 4.464; 3: 2.409 / 2.709 / 5.670; 4: 2.468 / 2.757 / 3.478 |
| 433 | symbols | candidate | 1: 1.988 / 2.136 / 4.473; 2: 1.996 / 2.281 / 5.284; 5: 2.023 / 2.221 / 2.542 |
| 433 | definition | baseline | 0: 2.623 / 2.702 / 2.717; 3: 2.403 / 2.634 / 5.580; 4: 2.414 / 2.491 / 3.089 |
| 433 | definition | candidate | 1: 1.984 / 2.279 / 3.404; 2: 1.967 / 2.513 / 5.032; 5: 1.995 / 2.188 / 3.272 |
| 433 | references | baseline | 0: 3.375 / 3.686 / 5.541; 3: 3.221 / 3.442 / 4.363; 4: 3.194 / 3.397 / 4.738 |
| 433 | references | candidate | 1: 2.806 / 2.919 / 3.961; 2: 2.804 / 3.062 / 5.011; 5: 2.818 / 4.730 / 7.330 |
| 5845 | symbols | baseline | 6: 36.888 / 39.472 / 43.818; 9: 35.730 / 40.231 / 41.428; 10: 36.314 / 41.492 / 47.735 |
| 5845 | symbols | candidate | 7: 28.285 / 79.048 / 81.959; 8: 30.337 / 35.677 / 40.261; 11: 30.858 / 34.084 / 37.053 |
| 5845 | definition | baseline | 6: 36.953 / 40.957 / 46.710; 9: 35.758 / 40.083 / 41.674; 10: 35.615 / 41.627 / 43.658 |
| 5845 | definition | candidate | 7: 28.272 / 77.381 / 84.214; 8: 30.211 / 33.483 / 34.907; 11: 31.040 / 34.181 / 37.099 |
| 5845 | references | baseline | 6: 38.935 / 41.415 / 58.217; 9: 36.687 / 41.880 / 48.543; 10: 37.429 / 41.848 / 43.335 |
| 5845 | references | candidate | 7: 29.731 / 77.722 / 84.076; 8: 30.686 / 35.782 / 37.366; 11: 31.935 / 36.430 / 40.067 |

All 720 measured responses and 108 warmup responses in the comparison passed
the driver assertions. Candidate session 7 has twelve slow responses in rounds
4–7, not a single isolated outlier. Its direct worker counters show 403,236 reused
snapshots (69 × 5,844) and only 4,600 additional bytes read after initial load
(23 rounds × target lengths 60 + 80 + 60). This excludes whole-graph rereading
during that session’s warmup and measured requests. It does not establish JIT,
GC, scheduling or allocation as the cause.

Private profile medians for the 5,845-file graph (ms; diagnostic, not production
benchmark timings):

| Version | Operation | Refresh | Path checks | Metadata | Read/hash/text | Apply/bookkeeping | Outside Refresh | Reply |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| profile | symbols | 37.2138 | 27.8896 | 4.8150 | 0.0998 | 0.6978 | 0.1492 | 0.0163 |
| profile | definition | 37.0968 | 27.6358 | 4.8049 | 0.1200 | 0.6926 | 0.2026 | 0.0137 |
| profile | references | 36.9869 | 27.6843 | 4.8884 | 0.0486 | 0.6634 | 1.6313 | 0.0173 |
| candidate-profile | symbols | 32.0266 | 27.6675 | 0.0021 | 0.0955 | 0.6937 | 0.1470 | 0.0175 |
| candidate-profile | definition | 31.3263 | 26.9885 | 0.0010 | 0.1155 | 0.6883 | 0.1964 | 0.0129 |
| candidate-profile | references | 31.7606 | 27.1286 | 0.0013 | 0.0518 | 0.6885 | 1.6039 | 0.0175 |

Remaining Refresh time includes sorting, collection staging, budget checks,
snapshot decisions, Roslyn text comparison and instrumentation overhead. Stage
medians need not sum. The baseline profile’s maximum warm Refresh was 98.158 ms
and the candidate’s was 78.198 ms; every measured profile request reused 5,844
snapshots and read only its target. Baseline refresh allocated approximately
14.93–14.99 MB/request versus 13.58–13.63 MB for the experiment, with median one
generation-zero collection in either profile. These are process-wide allocation
observations, not proof of tail causation.

Separate five-second-expiry requests reread the entire graph. Original baseline
sessions took 46.6–48.1 ms for 433 files (27,511 bytes) and 181.5–184.7 ms for
5,845 files (383,568 bytes). The full baseline periodic profile spent 182.338 ms
in Refresh, of which 113.698 ms was reading/hashing/text creation. Periodic reads
are real but do not explain all warm tails.

In the alternating comparison, full-graph open/compilation times are reported
separately below; no startup improvement is established:

| Version | Session | Open including awaited compilation (ms) | Explicit post-expiry request (ms) |
| --- | ---: | ---: | ---: |
| baseline | 6 | 3862.779 | 180.100 |
| baseline | 9 | 3668.004 | 177.090 |
| baseline | 10 | 3473.902 | 179.976 |
| candidate | 7 | 2983.019 | 180.667 |
| candidate | 8 | 3622.991 | 177.746 |
| candidate | 11 | 3507.683 | 176.662 |

The next bounded experiment should investigate this isolated leaf-metadata
patch without adding an ancestor cache: capture low-overhead runtime/GC and
filesystem traces around the slow mode, retain per-session results across longer
alternating sessions, then run the packaged external-input and platform matrix.
Expose live worker refresh counters through a separately tested core query or
telemetry seam before relying on public capability counters. Do not expand trust,
relax freshness or suppress warnings to obtain lower latency. Neither the old
reverted optimization nor this experiment is ready for promotion.

## Correctness and limitations

The unchanged baseline and candidate both passed the repository's safe-source and
trusted worker suites natively. These include exact semantic navigation, changed
files, safe-source additions/removals, preserved metadata, watcher bookkeeping
overflow and fallback, preview hashes, protocol/cancellation, project warning
classification, resource limits, and external-input direct-query rejection.
A supplemental trusted fixture passed fresh-target/preview hashes, non-target
ancestor symlink replacement and recovery, deletion failure, membership on reopen,
and whole-graph rereading after watcher bookkeeping overflow for both versions.
The trusted suite adds permanent non-target leaf/ancestor symlink and missing-input
regressions (Unix only). Windows reparse points remain unqualified locally.

The full packaged external-input integration matrix, Windows/Linux builds and
kernel-level before/after syscall traces are not claimed. The measured graph has
no Test SDK inputs. No before/after syscall count is available: managed path checks
remain four per file in this fixture (1,732 / 23,380); the candidate reuses the leaf
metadata for length/mtime instead of requesting another FileInfo stat. The expected
one-stat-per-workspace-input saving needs target-platform syscall confirmation.

The core capability caching issue is identified, not fixed. Broad workspace symbol
searches and complete MCP round-trip timing remain to be measured. Allocation and
GC counts establish pressure, not causation for any specific uninstrumented tail.
The existing MSBuild warning and external-input security policies are unchanged.

## Receipts and reproduction

Local-only receipts live under `bin/.local/perf/` in this checkout: `prepare.py`,
`measure.py`, `results.json`, `summary.json`, `*-profile-0.stderr`,
`compare.py`, `compare-results.json`, `compare.log`, `candidate-profile.py`,
`candidate-profile-results.json`, `trusted-boundaries*.py`, `boundaries*.json`,
and `test-*.log`. Generated output is intentionally not committed. The original
sandbox failure logs are retained rather than reported as product failures.
Use the private fixture generator with the pinned SDK; measurement drivers record
all raw request timings and IDs. They are local diagnostics, not a new official
workflow or benchmark promise.

`dockpipe --workflow repo.check` could not chmod its shared state directory in the
filesystem sandbox. The identical repository validation asset passed using the
checkout-local PyYAML environment, and `git diff --check` passed. The initial native
trusted run failed because the sandbox denied the MSBuild host's named-pipe bind;
the initial safe-source watcher-overflow check also failed there. Host-authorized
native runs passed. NuGet audit access was allowed for the pinned build; no warning
was suppressed. No Docker cleanup, resize, restart or data removal was attempted.
