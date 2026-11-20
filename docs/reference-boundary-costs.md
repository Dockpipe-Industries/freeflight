# Reference latency and definition/search boundaries

Local macOS arm64 diagnostics, 2026-10-22. The preserved worktree remains
`/Users/jamie/Source/freeflight-perf`, branch `investigate/rc2-warm-refresh`, HEAD
`94eb4207c8ffd2d5544bca8a52dcb8d451285015`. Production runtime is byte-identical to
that commit. These are generated diagnostic changes only. Fresh validation, strict
defaults, root authorization, resource limits and cooperative recovery remain.
No commit, publication, push, merge or deployment occurred. Runs were serial;
no additional agents were started. There is no accepted optimization or overall win.

## Session variation in the preceding native candidate

The retained matched MCP run's reference median ratio of session medians was 1.097
(candidate/baseline). The three session-cycle ratios are 0.945, 1.133, 0.945. The median
of those ratios is 0.945, a different estimand. Both views remain; selecting the
favorable view would not establish a stable improvement. Three cycles do not establish
significance, equivalence or a causal allocation-to-latency link. The native source
remains unaccepted. `operations-boundaries-v1/prior-session-contrast.json` retains
cycle identities and the original sample hash; `session_contrast.py` reproduces it.
Original adverse cells and [native candidate results](native-attribute-screen.md)
are unchanged.

## Extended boundary probe

`bin/.local/benchmarks/definition-cost/operations-boundaries-v1` freezes the 94eb 420
worker from `background-cooperative-v4` and a 94eb 420 C++ core. It extends the earlier
[definition probe](allocation-definition-costs.md) to definition, references, search
and a generated fixed no-op. The same framework-dependent .NET 11 worker/SDK and
allowlisted environment are used directly and through MCP. The graph contains 5,845
files of 4,096 bytes each, with fourteen reference callers and C5 search.

Two sessions per transport/cadence cover direct/MCP and burst/100 ms round cadence:
eight fresh processes, at least five seconds warmup, forty measured rounds and 1,280
request-ID-joined responses. The measured phase resets to zero. A four-operation
Williams design gives ten observations per operation/position/session and ten per
directed within-round predecessor pair. Transport process order reverses in the
second session. Exact fixture-derived semantic oracles pass for all 960 measured
ordinary requests;320 controls return their exact fixed value. All 640 definition/
reference requests read exactly one fresh 4,096-byte target. Search reads no source
bytes in these measured requests; missed-event recovery policy is still enabled.
Fixture source hashes are verified after timing.

The generated core passes protocol/process tests 2/2. Generated worker semantic,
security, UTF-8, cancellation, mutation and trusted-project tests pass. No unhandled
worker exceptions occur. ID joins, unique samples, position/predecessor balance and
fresh-read accounting also pass the separate receipt-only audit workflow. Raw logs,
all sessions/outliers, source/binaries, driver snapshots/hashes, per-position and
per-session summaries remain. There are no excluded measured sessions.

Selected pooled paced MCP medians, milliseconds (eighty observations per operation):

| Operation | Client total | Worker invocation | Refresh | Semantic work | Outside invocation |
| --- | ---: | ---: | ---: | ---: | ---: |
| definition | 0.4696 | 0.2043 | 0.1170 | find symbol 0.0396 | 0.2769 |
| references | 1.4367 | 1.0632 | 0.1157 | find references 0.8226 | 0.4004 |
| workspaceSymbols | 23.1430 | 10.2295 | 0.0067 | declarations 9.0378 | 12.5616 |
| fixed no-op | 0.2367 | 0.0012 | — | — | 0.2358 |

Definition's open-handle and buffered-read/hash phase medians are 0.0523/0.0226 ms;
reference equivalents are 0.0492/0.0207 ms. `pathCheck` aggregates all component-walk
calls in a request, including checks outside Refresh and nested checks inside handle
admission; its medians are 0.0450/0.0496 ms. These scopes overlap and cannot be added.
The read/hash phase includes bounded reads, resource checks, incremental hash updates
and MemoryStream writes, ending before final hash/snapshot publication. No path,
attribute or content validation is skipped in ordinary requests.

Reference time is concentrated in Roslyn FindReferences, rather than semaphore wait
or snapshot bytes alone. Median gate wait is 0.0001 ms. Pacing/position still affects
both semantics and boundary: paced MCP definition client median is 1.5675 ms first
versus 0.3106 ms fourth; references 3.0973 versus 1.2730 ms. This is an association,
not a measured CPU-frequency/power-state explanation. The four-operation workload
is different from the earlier definition/no-op pair; do not call their difference
an optimization or pool their samples.

## Search payload boundary and identical-result control

In the first probe, the search worker line is 274,025 bytes and MCP response 578,834
bytes. Production sends both text content and structured content. Paced core search
thread CPU median is 10.2855 ms, including 4.1730 ms in bounded worker JSON parsing.
Other overlapping core scope medians include 0.9516 ms value serialization, 1.2238 ms
response construction, 2.6197 ms result envelope and 1.6532 ms MCP serialization.
The parser still enforces nesting 128, response-size limits and correlation IDs.
These stages identify a CPU cost; their nested medians must not be summed.

`bin/.local/benchmarks/definition-cost/search-replay-boundaries-v1` is one bounded
follow-up. Only its generated worker adds `test.replaySearch`, primed by a correct
ordinary search. It returns that fixed object through the same normal reply path;
this is a control, never a fresh production answer. Ordinary search, definition and
reference operations retain their original validation and recovery. The control
replaces the no-op in the balanced workload; normal search runs twice as often when
counting the replay payload, so this is a different observer/workload condition.

Four serial processes (two sessions per transport, paced only) pass 640 joined
responses, including 480 ordinary semantic checks and 160 exact replay equivalence
checks. All 320 definition/reference requests read one fresh 4,096-byte target.
The replay hashes exactly equal ordinary search hashes in both transports. Response
sizes are identical within each transport. Protocol/process tests 2/2 and generated
worker/trusted suites pass again, along with the independent accounting/balance audit.

| Transport / operation | Client median ms | Invocation median ms | Per-request residual median ms |
| --- | ---: | ---: | ---: |
| direct / ordinary search | 10.8096 | 8.1916 | 2.6017 |
| direct / replay | 2.6598 | 0.0014 | 2.6586 |
| MCP / ordinary search | 13.5021 | 3.9705 | 9.6707 |
| MCP / replay | 9.6294 | 0.0009 | 9.6287 |

The replay MCP core thread CPU median is 7.7884 ms; bounded worker response parsing
alone is 3.1905 ms. Removing semantic work in this generated control leaves substantial
boundary cost. This is not a pure pipe measurement: worker serialization, parsing,
JSON copying/construction, dual payload serialization, client parsing and scheduling
remain. Compare ordinary/replay within this condition; do not subtract values across
the two probes or infer a production speedup from their different total latencies.

## Decision, limits and next step

The evidence supports a narrow response-ownership/copy experiment before another
worker cache or validation change. The source has copies when returning worker result
JSON, building the dual-content envelope, and passing it to the result sender. A
future candidate should reduce only redundant ownership transfers, retaining both
MCP content forms, malformed/deep JSON rejection, size/ID limits, cancellation/delivery
locking, errors, root authorization and every semantic result. Parsing remains a
measured cost, not permission to remove its security checks. No such candidate has
been implemented in this work.

References still need stable ordinary per-session/position confirmation before treating
the native candidate's aggregate regression as causal. Definition retains meaningful
fresh-input and outer-boundary costs; search has both declaration and large-response
costs. These generated SDK 11 synthetic diagnostics do not measure Glider internals,
production latency, native allocator costs, real repositories or other platforms.
Instrumentation perturbs execution; empty worker scope median is at most 0.0002 ms,
not a full observer-overhead bound. Core CPU includes its profiling calls. Per-request
residuals are calculated before summary; independently summarized medians are never
subtracted to reconstruct missing work. Every session and unfavorable observation
remains in `operation-analysis.json` and the original receipts.

## Replay

Use the existing perf-venv and pinned dotnet 11 PATH. Fresh labels refuse overwrite:

```sh
FREEFLIGHT_DEFINITION_LABEL=NEW_LABEL FREEFLIGHT_DEFINITION_EXTENDED=1 dockpipe --workflow benchmark.definition.cost
FREEFLIGHT_DEFINITION_LABEL=NEW_REPLAY_LABEL FREEFLIGHT_DEFINITION_EXTENDED=1 FREEFLIGHT_DEFINITION_REPLAY_SEARCH=1 dockpipe --workflow benchmark.definition.cost
FREEFLIGHT_DEFINITION_LABEL=COMPLETED_LABEL dockpipe --workflow benchmark.definition.cost.audit
```

The default definition/no-op workflow is retained when both options are omitted.
The audit issues no new timed requests and refuses to replace differing derived
receipts. It retains pooled and per-session metrics alongside the original raw data.

Follow-up: [JSON ownership screen, CPU benefit and ordinary-latency rejection](json-response-copies.md).
