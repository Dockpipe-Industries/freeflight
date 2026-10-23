# Recovery allocation stacks and definition boundary costs

Local macOS arm64 diagnostics, 2026-10-22. The preserved worktree stays on
`investigate/rc2-warm-refresh` at `94eb4207c8ffd2d5544bca8a52dcb8d451285015`.
All tracked production C++ and Roslyn worker files remain byte-identical to that
commit. No runtime optimization, trust change, publication or performance acceptance
is claimed. Runs are serial; no additional agent/model usage was needed.

The evidence identifies two substantial allocation sources and separates observable
worker time from MCP/client time. It does not establish an overall win over Glider.
The prior matched competitor results remain in [background recovery](background-recovery.md).

## Allocation stacks inside successful sweeps

`bin/.local/benchmarks/allocations/successful-sweeps-v1` retains two raw EventPipe
traces, derived ETLX files, all allocation events and managed stacks, generated source,
collector dependency lock, build logs, category summary and SHA-256 manifest. Each
fresh process warms for eight seconds, then collects twelve seconds of idle activity.
Only allocations between Begin and successful Success markers are analyzed. Six
completed sweeps (three per process) each verify 5,845 files and 23,941,120 bytes.
Both traces report zero lost events; all 3,227 selected allocation samples have stacks.
The generated marker wraps the existing production recovery call and records success
only after it returns. Startup, foreground warmup and rundown allocations remain in
the raw trace but outside the selected intervals.

Actual process-wide allocation deltas total 345,638,848 bytes: 57.606 MB/sweep.
Sample-weighted allocation ticks total 345,773,224 bytes, close to that total but not
an exact object census. The table uses exclusive first-matching stack categories.
JIT inlining can place path helper allocations in callers; native allocation stacks
are not captured. These percentages are approximate byte attribution, not object sizes
or exact allocation counts by type.

| Stack category | Sample-weighted MB | Share | Sample events |
| --- | ---: | ---: | ---: |
| Compiler path/attribute validation | 175.227 | 50.68% | 1644 |
| MemoryStream growth | 130.101 | 37.63% | 1221 |
| Other | 15.246 | 4.41% | 143 |
| Darwin handle opening | 12.578 | 3.64% | 118 |
| Hashing | 7.141 | 2.07% | 67 |
| Staged dictionaries | 5.479 | 1.58% | 34 |

Representative leaf stacks are `MemoryStream.set_Capacity -> WriteAsync -> Refresh`
for byte arrays, and `CheckCompilerInput` / `FileSystem.GetAttributes` / string path
construction for path and FileInfo allocations. Darwin descriptor admission accounts
for a smaller separate share. Hashing is not the dominant source. Per-sweep measured
CPU averages 181.775 ms under this observer; it must not be substituted for ordinary
unobserved CPU benchmarks or interpreted as an optimization over earlier runs.

The collector uses official EventPipe/TraceEvent APIs with runtime keyword
`0x40000001`, a 64 MB session buffer and managed rundown. Collection attaches only
to tool-owned synthetic workers; it does not alter persistent diagnostics settings.
The diagnostic-only package graph pins TraceEvent 4.0.0 and Diagnostics.NETCore.Client
0.2.750501, with NuGet content hashes, locked restore and retained MIT notices. No
application package reference changed. Method references: [Microsoft diagnostics client](https://learn.microsoft.com/en-us/dotnet/core/diagnostics/diagnostics-client-library)
and [runtime trace keywords](https://github.com/dotnet/diagnostics/blob/main/documentation/dotnet-trace-instructions.md).

## Definition validation versus the surrounding boundary

`bin/.local/benchmarks/definition-cost/boundaries-v3` contains frozen generated core
and worker source, binaries, toolchain/driver manifest, qualification logs and every
request-ID-correlated observation. The same framework-dependent worker DLL and SDK
11.0.100-rc.2.26504.105 are used directly and through a C++ core frozen from 94eb420.
Both worker environments match the core's allowlist, including diagnostics disabled.
Existing root authorization and fresh-target validation remain. Instrumentation adds
wall-clock scopes only; it has no allocation counters or runtime event listener.
The generated no-op operation returns a fixed value through the normal request/gate/
reply path and skips worker refresh/semantics. Through MCP it still passes normal
core routing/path handling. This control exists only in generated diagnostic source.

Twelve fresh processes cover direct/MCP transports, zero/100 ms round intervals,
and three sessions per cell. Transport process order alternates by session. After
at least five seconds of warmup, forty rounds each alternate definition/no-op order:
960 joined measured responses, including 480 exact-result definition checks and 480
fixed-result controls. Each table cell pools 120 observations; per-session records
and every outlier remain. The native protocol and process tests pass (2/2), as do the
generated worker's existing semantic/security and trusted project suites.

Median / p90 client durations in ms:

| Transport | Round interval s | Definition | No-op control |
| --- | ---: | ---: | ---: |
| direct | 0 | 0.0619 / 0.0731 | 0.0258 / 0.0606 |
| direct | 0.1 | 1.1967 / 1.5845 | 0.2232 / 0.4767 |
| mcp | 0 | 0.1403 / 0.1491 | 0.1201 / 0.1317 |
| mcp | 0.1 | 1.7913 / 2.4498 | 0.7734 / 1.2506 |

Selected definition-stage medians, in ms. Refresh includes target validation/read
and maintenance coordination; invocation includes refresh and semantics. Nested
scopes overlap. The final residual is computed per request as client duration minus
worker invocation, then summarized; it includes scheduling, core work, serialization,
pipes and client handling, and is not synonymous with pipe or network time.

| Transport | Interval s | Worker invoke | Refresh | Find symbol | Worker queue | Gate | Outside invoke |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| direct | 0 | 0.0401 | 0.0251 | 0.0034 | 0.0017 | 0.0000 | 0.0216 |
| direct | 0.1 | 0.8989 | 0.4566 | 0.1919 | 0.0144 | 0.0003 | 0.2444 |
| mcp | 0 | 0.0425 | 0.0256 | 0.0035 | 0.0020 | 0.0000 | 0.0979 |
| mcp | 0.1 | 0.8542 | 0.4509 | 0.1869 | 0.0208 | 0.0005 | 0.8950 |

Paced definitions stratified by pair position (60 samples each):

| Transport | Position | Client median / p90 ms | Invoke median ms | Refresh median ms | Outside invoke median ms |
| --- | --- | ---: | ---: | ---: | ---: |
| direct | first after round gap | 1.4239 / 1.7325 | 0.9422 | 0.4729 | 0.4682 |
| direct | second after no-op | 1.0770 / 1.3256 | 0.8715 | 0.4375 | 0.1954 |
| mcp | first after round gap | 2.1885 / 2.7349 | 0.8744 | 0.4688 | 1.2975 |
| mcp | second after no-op | 1.6203 / 1.8732 | 0.8425 | 0.4424 | 0.7259 |

In burst traffic, worker invocation stays near 0.04 ms in both transports; the MCP
client boundary adds a visible cost. With round pacing, both worker invocation
and the surrounding boundary rise. Refresh and symbol lookup both slow, while gate
wait remains sub-microsecond at the median and worker queue medians are tens of
microseconds. The fixed-result control also slows. This does not support attributing
the whole definition gap to semaphore contention or just semantic-model acquisition.
It shows an association with pacing and pair position; CPU frequency, power state
and OS scheduler causation were not directly measured.

These are instrumented, definition/control-only SDK 11 observations, not the prior
four-operation SDK 10 Glider benchmark. Instrumentation and diagnostic logging perturb
execution. Each worker/core record uses one atomic POSIX write; logging occurs after
reply delivery and its previous duration is retained in raw records. Client/core/worker
clocks are compared as local elapsed durations and joined by IDs, not synchronized
absolute timestamps. Do not subtract independently summarized medians or add nested
scope medians to construct an unmeasured total. Source contract and existing tests
verify fresh target reads; this lightweight run does not collect per-request byte deltas.

## Failed diagnostics and remaining work

`boundaries-v1` preserves a generated startup mistake: explicit legacy trusted-worker
arguments were combined with per-root trust, and the core correctly rejected startup.
The generated config was corrected to use its existing per-root form, which appends
exactly the same worker trust flag. No actual application trust setting changed.
`boundaries-v2` preserves concurrent stderr record interleaving during high-rate
warmup; its fail-closed JSON join rejected the run. Atomic generated-worker records
fix this in v3. Neither failed run contributes accepted timing samples.
Earlier buffer/model/search rejection receipts remain untouched.

Next, narrowly examine repeated path construction/attribute allocations while retaining
fresh validation of every component and fresh target contents. The buffer reduction
already regressed reference tails and is not reinstated. Any runtime candidate must
pass missed-event recovery, rollback/security gates and all-operation narrow screens
before a new matched MCP/Glider matrix. Definition refresh also needs finer path/read
and CPU-versus-wait attribution before changing transport or validation policy.
Glider idle resources, long-duration RSS, real-repository and cross-platform cost
qualification remain open. There is no accepted runtime improvement in this work.

## Replay

Use the existing perf-venv and pinned dotnet11 on PATH. Fresh labels refuse overwrite:

```sh
FREEFLIGHT_ALLOCATION_LABEL=successful-sweeps-repeat dockpipe --workflow benchmark.recovery.allocations
FREEFLIGHT_DEFINITION_LABEL=boundaries-repeat dockpipe --workflow benchmark.definition.cost
```

Both use the retained `background-cooperative-v4` frozen source/fixture receipt.
The allocation workflow restores its collector with the checked-in diagnostic lock;
output, nettraces, ETLX, dependency builds and synthetic source remain under `bin/.local`.
The definition workflow runs its deterministic position-summary step after collection.
Neither workflow touches production source or publishes artifacts.

Follow-up: [lexical-only path-string reuse screen and rejection](path-string-screen.md).

Follow-up: [fresh native attribute allocation and all-operation screens](native-attribute-screen.md).

Follow-up: [reference latency, finer fresh-read scopes and identical search-payload control](reference-boundary-costs.md).
