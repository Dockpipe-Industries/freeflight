# Opt-in background recovery investigation

Local M6 prototype, not a release or an overall performance win. Strict default
and ordinary `--incremental-validation` behavior remain available. Experimental
`--background-recovery` requires incremental trusted mode and is restricted to
macOS. No installed MCP configuration was changed.

## Design and preservation argument

One timer checks once per second and attempts maintenance when the previous full
recovery began at least four seconds ago. It owns the same semaphore as semantic
requests and calls the existing full Refresh transaction. There is no concurrent
workspace update, separate semantic cache, speculative answer or graph reduction.
The foreground five-second check is unchanged. Successful maintenance records its
**start** time, not its finish; an overlong sweep cannot extend the freshness age.
The timer may be delayed or cancelled without authorizing a stale response: a due
foreground request still performs recovery.

Target reads, external exact inputs, rename hashes, byte accounting, sorted failure
order and staged publication remain in the original Refresh path. A failed timer
attempt leaves committed state/time unchanged and invalidates recovery eligibility;
the next semantic request must retry full recovery. Captured watcher versions are
acknowledged only after publication. Events arriving during a sweep remain pending.
Maintenance is disabled until trusted open/compilation succeeds, and reset before
another open. Shutdown cancels and joins the timer before engine disposal.

This moves I/O into idle time; it does not eliminate I/O. A request arriving during
maintenance waits on the gate. The measured first candidate has a 107 ms definition
maximum from that contention, despite fast post-idle responses. Neither idle work
nor this unfavorable sample is excluded from the result.

## First candidate and negative gate

`218ef4c` preserves the first prototype. `background-screen-v1` completed the
strict worker/external/resource suites, sixteen incremental fault cases, five
failed transactions per variant, real suppressed-event timer tests and twelve
screen processes. Its original summary command rejected a changed test-driver
hash after timing completed. `summarize-failure.json` retains that failure. The
original adapter was restored from its frozen copy and only summary generation
was rerun; stronger follow-up proofs use a separate asset.

`background-full-mcp-v1` passed 1,920 steady and 48 post-idle semantic responses
across twelve fresh processes. Same full synthetic graph, pinned Glider 13.3.0,
balanced operation order, two reversed product orders and both zero/100-ms round
cadences. No Biztraak or Linux rerun is claimed. Glider's unavailable columns and
reference ends are not fabricated; the existing source-declaration oracle checks
the fields it exposes and FreeFlight's complete ranges.

The actual-worker FIFO negative control then **rejected** this candidate. A
workspace input was replaced with a FIFO after loading, with no semantic request.
Baseline idle EOF exited in 4.6 ms. Timer-triggered FileStream.Open blocked; EOF
did not drain within the two-second watchdog, which killed only that task-owned
probe. Receipt: `background-screen-v1/background-fifo-proof/result.json`.
Earlier cooperative cancellation tests did not establish this native-I/O case.

## Nonblocking repair

The repaired prototype uses the source-confirmed Darwin nonblocking/all-component
no-follow handle primitive from `c3ae753` for background reads only. Handle
metadata must identify a regular file before content reads. Unlike the rejected
serial performance experiment, background admission has **no blocking fallback**:
unsupported/open/metadata failures request foreground recovery instead. External
files still require exact catalogue membership and existing pre-read validation;
the handle path does not grant their directories edit or query authority.

This addresses the observed FIFO defect, not arbitrary kernel-call termination.
Regular-file network/device filesystem behavior can still block OS calls. The
existing native core owns worker process termination; no stronger cross-platform
or universal cancellation guarantee is claimed. A deployment policy requiring
bounded graceful shutdown for every filesystem would need a separately qualified
process-isolation design, not a token or timeout around an uninterruptible syscall.

Full-graph adversarial tests in `background-screen-v1/background-adversarial-5845`
also cover an edit after its background read, an ancestor swapped immediately
before the read, late missing input, overflow/cancellation before commit,
conditional event acknowledgment, preview hash freshness, queued-request
cancellation and EOF during active timer work. That pre-repair source's separate
FIFO failure remains decisive; those passes are not a replacement for it.

The repaired serialized candidate is `51bc4c7`, frozen in `background-safe-v2`.
Its FIFO/EOF gate exits normally in 22.7 ms, versus the pre-repair watchdog kill.
Worker, external-input, resource, mutation, handle, sixteen incremental and
transaction gates passed, followed by the full-graph adversarial cases. The first
5.2-second diagnostic idle interval read 23,941,120 bytes and consumed 781.7 ms of
process CPU, including post-load runtime activity; this is not a warmed sweep-only
CPU estimate. Nothing was inferred from cached core refresh counters.

`background-safe-mcp-v2` completed 24 fresh processes, 3,840 steady and 96 post-idle
semantic responses on both graph sizes. Its full-graph paced definition median is
0.473 ms versus Glider's 0.200 ms, and its maximum reaches 103.725 ms. Full-graph
post-idle candidate samples are 1.922–2.322 ms versus baseline 155.960–158.549 ms.
This is a real latency shift with a real idle-work/contended-query cost, not an
overall win or an elimination of recovery work. All samples remain in the receipt.

## Cooperative preparation

A subsequent candidate yields the existing semaphore between files when a request
is pending. At that point its current source stream/hash has been disposed. Only
one engine operation reads or mutates state at a time; the background transaction
retains private preparation while a foreground transaction runs. Foreground reads
use their normal admission mode. The semaphore is always reacquired before a
cancellation exception can leave the callback, preserving outer ownership.

A revision changes when a foreground commit changes exact-byte hashes, when open
starts, or when a foreground full recovery succeeds even with identical bytes.
After reacquiring the gate, stale preparation aborts before another read or commit.
The full-recovery case prevents an older sweep moving the recovery timestamp
backward. Unchanged partial foreground reads permit preparation to continue.
The five-second foreground fallback remains authoritative, including under a busy
request stream that prevents background work finishing early.

This keeps at most one pending background preparation and one foreground refresh;
it does not run filesystem calls concurrently. Their staged memory can coexist.
Input byte/document limits remain enforced separately by the original transactions;
those limits were never a total process/Roslyn RAM quota.

The V3 negative gate is preserved in `background-cooperative-v3`: an initial test
variable shadowing error failed compilation, then the old transaction guard falsely
attributed a legitimate foreground commit to background mutation. The revised
test-only guard takes its expected state after each foreground yield (also on
exception), while foreground Refresh retains its own failure guard. With that
correction, the unchanged-full-recovery test exposed the actual supersession bug:
zero aborts and two full recoveries. V4 advances the revision for that case.
No V3 performance result is claimed. No guard failure was discarded or described
as a passing runtime test.

## Resumed qualification — 2026-10-22

The instruction-only model-choice hook delivered its guidance on a real spawn; the bounded review child used `gpt-6.1-sol` / `medium`. No further agents overlapped benchmarks.

The linked worktree remains on `investigate/rc2-warm-refresh`. The rejected semantic-model reuse patch, complete source and raw screen receipts were copied under `bin/.local/perf-preservation/20261022-instruction-hook-resume`; original receipts remain. Only `Program.cs` was restored from this worktree's own `94eb4207c8ffd2d5544bca8a52dcb8d451285015`. All frozen worker source hashes match that commit. Main `js/dev` and its unrelated changes were untouched.

### Closed test gaps

- Actual production semaphore handoff: EOF arrives while a foreground operation owns the released gate. Cancellation releases it, maintenance reacquires without cancellation, and the main loop joins before disposal. Exit: 18.995 ms.
- Five-second fallback: production maintenance suspends at age 4500 ms; an ordinary `symbols` request performs full recovery at age 6013 ms, admits a same-size/restored-timestamp edit with watcher events suppressed, and the resumed older sweep aborts. No forced due timestamp or rename triggers this test.
- Idle accounting requires successful background completion, matching published full-recovery increments and exact all-file byte/read counts. Attempts alone are insufficient. All 12 windows pass; failures and aborts remain zero.

Handoff/fallback probes use the 433-file fixture; idle accounting uses the full 5,845-file graph. Receipts: `background-cooperative-v4/handoff-fallback-proof/result.json` and `background-cooperative-v4/idle-cost-qualified-v2/result.json` under `bin/.local/benchmarks/trusted`. Each proof retains its exact adapter and generated instrumented source.

### Idle resource costs

Three alternating foreground-only/background process pairs use the same frozen candidate, eight-second warmup, and two 5.2-second idle windows per process. This isolates maintenance cost rather than comparing different source versions. Diagnostic probes are excluded from ordinary MCP timing. Whole-process deltas include runtime activity and statistics responses.

| Mode | Windows | CPU ms/window range | Allocated MB/window range | GC pause ms/window range | Observed one-core CPU % | Sampled RSS MB range |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| foreground-only | 6 | 1.140–22.677 | 0.010–0.094 | 0.000–0.000 | 0.203 | 357.6–358.8 |
| background | 6 | 188.735–429.611 | 57.617–115.310 | 2.456–7.461 | 5.861 | 363.6–369.2 |

9 successful sweeps average 203.437 ms process CPU and 57.642 MB allocated per sweep; each reads 23,941,120 bytes across 5,845 files. RSS is sampled before/after, not a measured peak. These short windows are local descriptive evidence, not a long-duration production estimate. Glider allocation/idle costs were not measured.

### Matched repeated MCP results

One matrix, 36 fresh processes, 5,904 measured exact-result semantic checks. Baseline is the noncooperative background candidate `51bc4c7`; candidate is cooperative `94eb420`; Glider is pinned 13.3.0. All use the existing matched synthetic .NET 10 graph/SDK 10.0.402. Both FreeFlight workers use the same published C++ MCP core. Frozen source/native hashes and product/operation ordering are retained in provenance. Three sessions per product per graph/cadence rotate products through all three positions; operation order uses the existing balanced design. Warmup is five seconds; 40 measured rounds contain four operations; a separate 5.1-second idle round follows. No diagnostic worker, RSS sampler or concurrent benchmark is present.

Cells below are median of the three session medians / median of session p90 values, in milliseconds. Raw samples, every session and all maxima remain in `bin/.local/glider-comparison/background-coop-matched-20261022`; no outliers were removed.

| Files | Round interval s | Operation | Baseline median / p90 | Candidate median / p90 | Glider median / p90 |
| ---: | ---: | --- | ---: | ---: | ---: |
| 433 | 0 | symbols | 0.154 / 0.169 | 0.150 / 0.159 | 0.301 / 0.323 |
| 433 | 0 | definition | 0.145 / 0.164 | 0.142 / 0.164 | 0.136 / 0.154 |
| 433 | 0 | references | 0.551 / 0.658 | 0.488 / 0.611 | 1.351 / 1.479 |
| 433 | 0 | workspaceSymbols | 0.262 / 0.286 | 0.248 / 0.285 | 0.968 / 1.074 |
| 433 | 0.1 | symbols | 1.078 / 2.006 | 1.031 / 1.939 | 1.110 / 2.067 |
| 433 | 0.1 | definition | 1.017 / 1.965 | 0.955 / 1.909 | 0.468 / 1.257 |
| 433 | 0.1 | references | 3.041 / 4.365 | 2.875 / 4.495 | 2.826 / 4.412 |
| 433 | 0.1 | workspaceSymbols | 2.194 / 3.240 | 2.185 / 3.122 | 3.551 / 5.093 |
| 5845 | 0 | symbols | 0.173 / 0.225 | 0.183 / 0.231 | 0.250 / 0.362 |
| 5845 | 0 | definition | 0.157 / 0.206 | 0.169 / 0.229 | 0.126 / 0.229 |
| 5845 | 0 | references | 0.635 / 0.724 | 0.669 / 0.824 | 1.378 / 1.730 |
| 5845 | 0 | workspaceSymbols | 7.921 / 8.417 | 8.006 / 8.671 | 11.065 / 16.288 |
| 5845 | 0.1 | symbols | 0.472 / 1.341 | 0.446 / 1.401 | 0.472 / 1.333 |
| 5845 | 0.1 | definition | 0.454 / 1.460 | 0.454 / 1.436 | 0.283 / 0.888 |
| 5845 | 0.1 | references | 1.272 / 3.307 | 1.303 / 3.431 | 1.398 / 3.177 |
| 5845 | 0.1 | workspaceSymbols | 23.707 / 27.818 | 24.083 / 28.347 | 18.828 / 26.772 |

Full-graph worst measured steady query per product (all operations, milliseconds):

| Round interval s | Baseline | Candidate | Glider |
| ---: | ---: | ---: | ---: |
| 0 | 10.398 | 11.051 | 26.931 |
| 0.1 | 112.407 | 31.555 | 32.634 |

First response after the separate 5.1-second idle interval (`symbols`), milliseconds. Each cell is the median [minimum–maximum] of three fresh-process observations:

| Files | Round interval s | Baseline | Candidate | Glider |
| ---: | ---: | ---: | ---: | ---: |
| 433 | 0 | 2.219 [2.200–2.281] | 2.319 [2.264–2.359] | 2.732 [2.664–3.135] |
| 433 | 0.1 | 1.888 [1.724–2.324] | 2.023 [1.774–2.353] | 2.197 [2.003–2.478] |
| 5845 | 0 | 2.068 [2.051–2.528] | 2.364 [2.253–2.661] | 1.987 [1.611–2.417] |
| 5845 | 0.1 | 2.258 [2.211–2.305] | 2.380 [2.320–2.389] | 2.558 [2.406–2.910] |

### Interpretation, failures and limits

This closes the three identified test gaps and supplies repeated local cost/latency qualification. It does not establish an overall FreeFlight performance win. Definition latency and background allocation/CPU remain explicit acceptance concerns; individual favorable cells do not override regressions. Default safe-source/strict behavior and missed-event recovery are unchanged. Existing worker/security/transaction qualification is retained; the comparison also reruns both native worker semantic suites and rejects crash logs. No new cross-platform execution or real-repository performance is claimed.

The first resumed repo.check invocation failed because system Python lacked PyYAML; the existing perf-venv invocation passed. The first idle probe failed before measurement because historical provenance used a symlinked worktree alias; its failure is preserved under `idle-cost-qualified/failure.json`. The adapter now resolves the fixture root to a canonical path without weakening authorization. The rejected model-reuse full-graph p90 ratios remain 1.372 outlines, 0.998 definitions, 1.442 references and 1.756 workspace search; that experiment is not accepted or rerun.

Next: profile the remaining ordinary definition path with a narrow matched screen before another expensive matrix, and assess whether the measured idle resource tradeoff is acceptable. Keep the opt-in candidate and all negative receipts; no publication, merge or deployment is authorized.

### Replay

Use the existing perf-venv Python and pinned .NET 11 SDK on PATH. Choose fresh labels; workflows refuse to overwrite receipts. Restore the worker source from candidate 94eb420, not the archived model-reuse experiment. The proof workflows accept:

```sh
FREEFLIGHT_BACKGROUND_RECEIPT=background-cooperative-v4 FREEFLIGHT_BACKGROUND_GAP_LABEL=handoff-fallback-repeat dockpipe --workflow benchmark.recovery.background.gaps
FREEFLIGHT_BACKGROUND_RECEIPT=background-cooperative-v4 FREEFLIGHT_BACKGROUND_IDLE_LABEL=idle-cost-repeat dockpipe --workflow benchmark.recovery.background.idle
```

For `benchmark.trusted.glider`, set a fresh `FREEFLIGHT_GLIDER_LABEL`; set `FREEFLIGHT_GLIDER_DOTNET_ROOT` to the recorded SDK 10.0.402 root; `FREEFLIGHT_GLIDER_FIXTURE_PROVENANCE` to the background-cooperative-v4 provenance; `FREEFLIGHT_GLIDER_CANDIDATE_RECEIPT` to that receipt directory; `FREEFLIGHT_GLIDER_LOCAL_BASELINE_RECEIPT` to the retained background-safe-mcp-v2 comparison; and `FREEFLIGHT_GLIDER_LOCAL_BASELINE_REF=51bc4c7`. Use `FREEFLIGHT_GLIDER_QUALIFIED_WORKER_ONLY=1`, `FREEFLIGHT_GLIDER_PRODUCTS=local-baseline,candidate,glider`, `FREEFLIGHT_GLIDER_PRODUCT_ORDER=balanced`, `FREEFLIGHT_GLIDER_ROUNDS=40`, `FREEFLIGHT_GLIDER_SESSIONS=3`, `FREEFLIGHT_GLIDER_WARMUP=5`, `FREEFLIGHT_GLIDER_INTERVALS=0,0.1`, `FREEFLIGHT_GLIDER_SIZES=433,5845`, and `FREEFLIGHT_GLIDER_QUERY_ORDER=balanced`. The driver-source snapshot, complete configuration and hashes are retained in the timing receipt.

## Definition/search and idle-allocation screening — 2026-10-22

Continued in the preserved linked worktree, with serial runs and no new agents.
The starting tracked patch and untracked files are preserved under
`bin/.local/perf-preservation/20261022-definition-idle-focus`. Both new experiments
were screened against this worktree's own 94eb420 with incremental validation and
background recovery enabled on both sides. No branch reset or js/dev replacement
was used. Neither experiment is accepted; production worker files are restored
byte-for-byte to 94eb420. Existing qualification changes remain uncommitted.

### Calibrated definition/search attribution

`bin/.local/benchmarks/focus/semantic-stages-v3` contains the generated diagnostic
source, adapter snapshot and complete samples. Two fresh full-graph worker processes
use balanced operation positions, 100 ms cadence, at least five seconds of warmup,
and 25 explicitly post-warmup rounds each: 200 exact-result checked responses,
50 samples per operation. All retained records assert the post-warmup flag.
The median empty timer scope is 0.0001 ms. Process-wide allocation counters include
runtime activity and probes; scopes are not ordinary MCP or Glider latency.

| Operation | Stage | Median ms | Median allocated bytes |
| --- | --- | ---: | ---: |
| definition | refresh | 0.14185 | 18432 |
| definition | text | 0.00090 | 128 |
| definition | syntax | 0.00165 | 288 |
| definition | model | 0.00400 | 208 |
| definition | findSymbol | 0.04865 | 1304 |
| definition | sourceDefinition | 0.00585 | 232 |
| workspaceSymbols | refresh | 0.00495 | 552 |
| workspaceSymbols | declarations | 5.89895 | 984648 |
| workspaceSymbols | order | 0.52035 | 211480 |
| workspaceSymbols | render | 0.41345 | 344288 |

The evidence directs attention to fresh validation and symbol lookup for definitions,
and declaration discovery for search. Cached model acquisition is small; the rejected
model-reuse experiment was not repeated. Fresh target reads, path authorization,
recovery deadlines and Roslyn semantics were retained.

Two diagnostic mistakes are recorded rather than silently replacing receipts.
`semantic-stages-v1` included allocation-counter synchronization inside timer scopes;
`semantic-stages-v2` fixed the timer but selected rounds before its five-second warmup
finished. Both retain validity-review notes and raw samples. Only v3 supplies the
post-warmup attribution above. Diagnostic timing is descriptive and perturbs execution.

### Narrow matched screens — both rejected

Each screen uses two sessions per variant/size (433 and 5,845 files), five-second
warmup, twenty measured four-operation rounds, 100 ms cadence, and alternating
baseline/candidate process order. Eight ordinary and four separate diagnostic worker
processes per screen pass exact-result assertions. Each has 640 ordinary measured
checks plus 320 diagnostic measured checks, excluding warmup and expiry queries.
The query is C5, source padding 4096 bytes, reference callers 14. These direct-worker
screens have fixed query order and limited samples; all sessions/outliers remain,
and ratios do not establish causation or competitor performance.

| Experiment | Files | Operation | Median ratio | p90 ratio |
| --- | ---: | --- | ---: | ---: |
| background-only buffer | 433 | symbols | 0.974 | 0.957 |
| background-only buffer | 433 | definition | 0.959 | 1.054 |
| background-only buffer | 433 | references | 1.054 | 1.023 |
| background-only buffer | 433 | workspaceSymbols | 0.959 | 0.897 |
| background-only buffer | 5845 | symbols | 0.980 | 1.028 |
| background-only buffer | 5845 | definition | 0.955 | 0.926 |
| background-only buffer | 5845 | references | 0.958 | 1.226 |
| background-only buffer | 5845 | workspaceSymbols | 0.890 | 0.943 |
| two-project search | 433 | symbols | 1.294 | 1.023 |
| two-project search | 433 | definition | 1.389 | 1.043 |
| two-project search | 433 | references | 1.231 | 1.301 |
| two-project search | 433 | workspaceSymbols | 0.850 | 0.794 |
| two-project search | 5845 | symbols | 1.144 | 1.015 |
| two-project search | 5845 | definition | 1.121 | 1.135 |
| two-project search | 5845 | references | 1.114 | 0.909 |
| two-project search | 5845 | workspaceSymbols | 0.831 | 0.830 |

Ratios are candidate/baseline; smaller is faster. Background-only buffer reuse
reduced allocations but full-graph reference p90 regressed 22.6%, with both candidate
sessions unfavorable. This differs from the earlier foreground buffer experiment:
only the private background transaction reuses memory, while foreground reads retain
fresh buffers. Nine pinned-Roslyn overwrite/disposal ownership cases pass. Actual
handoff EOF and suspended-maintenance five-second fallback also pass against the
frozen buffer candidate (19.033 ms shutdown; suspension age 4494 ms, fallback age
6007 ms). It remains rejected on ordinary latency, not on a semantic failure.

The search candidate uses the same public Roslyn per-project declaration API as the
pinned solution implementation, with at most two projects active. It retains project
order, every declaration query, cold negative prechecks, global exact sorting and the
1000-symbol limit. Started tasks drain before cancellation/error returns. The 104
unchanged differential oracle checks pass, including Unicode, partials, shared files,
edits/removal, limits and cold misses. Additional generated probes prove the two-task
bound, in-flight cancellation/draining, and original project error precedence when a
later project fails first. Full-graph search p90 improves 17.0%, but definition p90
regresses 13.5% in both candidate sessions; small reference p90 regresses 30.1%.
These regressions rule out acceptance and a larger MCP matrix for this candidate.

Both screens also pass existing worker, trusted-MSBuild/external-input, mutation,
Darwin metadata/handle/expiry, sixteen incremental fault cases, background recovery,
and five failed-refresh transaction cases per variant. Generated probes remain outside
shipping runtime. No default, trust, analyzer/plugin, resource or missed-event policy
was relaxed.

Receipts live under `bin/.local/benchmarks/trusted/background-buffer-screen-v1`
and `project-search-screen-v1`, including frozen candidate source, toolchains, driver
snapshots, raw timings, qualification logs and summaries. Separate rejection archives
are `bin/.local/perf-preservation/20261022-background-buffer-rejected` and
`20261022-project-search-rejected`; both contain source, patch and decision.

### Successful-sweep idle accounting for rejected buffer candidate

`background-buffer-screen-v1/idle-buffer-cost-v1` adds two alternating foreground-only/
background process pairs, eight-second warmup and two 5.2-second idle windows each.
All eight windows pass. Four background windows prove six successful full sweeps,
matching completion/publication counters and exactly 5,845 files / 23,941,120 bytes
per sweep; idle-window failure/abort deltas are zero. Process CPU averages
199.817 ms/sweep, allocations 33.194 MB/sweep, observed one-core CPU 5.757%, and
sampled background RSS 359.8–363.5 MB. These are short local synthetic observations,
not peaks or production estimates.

Compared descriptively with the prior qualified 94eb420 idle run (57.642 MB/sweep),
allocation falls 42.4%, while CPU remains near 200 ms/sweep. These two source versions
were measured in separate runs, so this is not a matched statistical cost comparison.
Each individual idle run matches maintenance off/on for its own frozen source.
The lower allocation result does not override the latency regression. Glider idle
CPU/allocation remains unqualified; no parity claim is made.

### Current decision and next step

Keep cooperative runtime 94eb420 and all negative receipts. The earlier 36-process
matched MCP/Glider matrix remains the latest competitor comparison; neither rejected
screen justifies rerunning it. Full-graph paced candidate/Glider median and p90 remain
0.454/1.436 versus 0.283/0.888 ms for definition, and 24.083/28.347 versus
18.828/26.772 ms for search. There is still no reproducible overall win.

Next work should attribute allocation stacks during an isolated, verified successful
sweep and separate wakeup/transport costs from fresh-file validation in definition
queries, then require a narrow matched screen to pass all operations before another
MCP/Glider matrix. Keep strict/default behavior and recovery semantics. Long-duration
idle/RSS, Glider resource costs, real-repository and cross-platform qualification remain
open. Nothing was published, pushed, merged or deployed.

Replay the focus probe with a fresh `FREEFLIGHT_FOCUS_LABEL` using
`dockpipe --workflow benchmark.trusted.focus`; `FREEFLIGHT_FOCUS_RECEIPT` defaults
to the frozen cooperative-v4 receipt. For either narrow screen, use the retained
provenance environment fields with a fresh label and the archived source; set
`FREEFLIGHT_TRUSTED_BENCH_BASELINE_BACKGROUND=1` in addition to baseline incremental
mode so both variants run the same flags. The idle workflow accepts optional
`FREEFLIGHT_BACKGROUND_IDLE_VARIANT=baseline|candidate` (default candidate) and
`FREEFLIGHT_BACKGROUND_IDLE_SESSIONS` (minimum two, default three). Do not overwrite
existing receipts. Use the existing perf-venv and pinned dotnet11 PATH recorded above.

The follow-up [allocation-stack and definition-boundary diagnostics](allocation-definition-costs.md) identify path/attribute validation and buffer growth as major allocation sources, and separate direct/MCP worker and boundary costs. Production source remains 94eb420.
