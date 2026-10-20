# Scaling candidate readiness

This review covers PR #20 and its focused correctness follow-up. Historical
timings remain tied to runtime `986b60b`; the follow-up has not been timed again.
See [benchmarks](benchmarks.md) for all raw observations and limitations.

## Freshness and retained state

Unchanged queries do **not** promise zero source reads. The requested source is
always content-validated. The C# large-source test measures exactly 56 bytes read
for its target and three unrelated large snapshots reused. The TS aggregate test
measures one source read and one content hash for an unchanged direct query.
An unchanged C# `workspaceSymbols` query has no direct target: its regression test
verifies zero source bytes read and all four snapshots reused.
Configuration reads, directory enumeration and metadata checks are additional
work; these counters are not a claim of zero filesystem I/O.

| Case | Contract and evidence |
| --- | --- |
| Single-file edit | Both worker suites and the paired MCP benchmark verify changed diagnostics and restoration. |
| Same-size, preserved timestamp | Direct-target tests verify fresh semantic results. Unrelated C# files can remain stale until a watcher notification or the five-second content-revalidation interval. TS also checks inode/device/ctime, with five-second content revalidation. |
| Explicit full refresh | Invoke `workspace.close` then `workspace.open` for the authorized project root. Repeating `workspace.open` alone is not a forced reload. No separate refresh operation is advertised. Closing also releases descendant workspaces and workers. |
| C# source membership | Safe-source mode enumerates source paths each query; add/remove/rename reconciliation does not depend solely on watcher delivery. Tests verify exact definition paths after rename, CS0103 after deletion, and correct definitions after re-addition. Trusted project membership is fixed until close/reopen. |
| TS resolution changes | Retained TypeScript services previously kept failed imports after a file appeared, and stale package resolution after a package manifest changed. Both defects reproduce on the preview. The follow-up tracks bounded metadata for paths actually probed by resolution and rebuilds the affected service when those paths change. Unchanged queries retain the service. |
| Watcher loss/overflow | C# watcher Error increments a full-invalidation generation. More than 4,096 dirty paths also invalidates and clears bounded bookkeeping. The suite generates 4,200 distinct events and asserts a complete source reread, then verifies the periodic fallback. Actual OS buffer overflow and a disabled watcher are not deterministically injected; those branches are inspected, not claimed as fault-injection coverage. TS has no watcher dependency. |
| Configuration changes | TS reparses the selected tsconfig and extends chain on queries; changed compiler options/root membership replaces the service. Package resolution metadata is separately tracked. Safe-source C# intentionally ignores MSBuild configuration. Trusted project/solution/configuration changes require close/reopen; startup resource/authorization changes require a server restart. |
| Cancellation | C++ process tests interrupt hung reads and blocked writes within three seconds and prevent reuse of the stopped process. MCP tests verify cancellation responsiveness and suppressed canceled responses. Roslyn has an in-worker cancellation/recovery test. Synchronous TS work is stopped at the process boundary, not cooperatively interrupted inside the TypeScript API. |
| Failure recovery | The core erases a worker after a query/open error; a later explicit call starts a fresh worker, without replaying the failed request. Tests cover process crash/no replay, fresh process recovery, and real C#/TS limit-error recovery through MCP. A full real-language crash-and-resume scenario is not separately fault-injected. |

Rename operations remain previews with content hashes; they do not rename files
on disk. A filesystem rename is a distinct source-membership change.

## Resource policy and failure behavior

Use one operator-owned startup configuration, for example:

```json
{
  "roots": ["/absolute/projects"],
  "resources": {
    "maxFileBytes": 33554432,
    "maxWorkspaceBytes": 536870912,
    "maxFiles": 50000,
    "maxDirectoryEntries": 500000
  }
}
```

Launch the installed executable with `--config /absolute/freeflight.json`.
Bundled workers are discovered automatically when `engines` is omitted.
The ordinary `--workspace /absolute/projects` form uses these same defaults.
No client reconfiguration is required merely to obtain the larger defaults after
replacing the installation and restarting its MCP process.

The core and workers validate positive integral values, known field names and
`maxFileBytes <= maxWorkspaceBytes`. Ceilings are 256 MiB/file, 2 GiB/workspace,
200,000 files and 2,000,000 directory entries. Query arguments cannot override
operator policy. The core forwards the validated policy on worker initialization.
Limits apply per engine workspace, not to total server RSS. TS keeps at most eight
projects and a separate text cache of at most 64 MiB charged by UTF-16 storage;
compiler objects, runtime libraries and process overhead are additional memory.
Resolution-probe bookkeeping is separately bounded by the directory-entry policy.

C# checks source counts/stat sizes and counts actual bytes during bounded reads.
Its snapshot/document replacement is committed only after reconciliation succeeds.
The trusted-loader follow-up removes the initial lazy filesystem text loader so
first snapshot comparison cannot trigger another unbounded source read. MSBuild
evaluation itself remains explicitly trusted, may execute project code, and is
not sandboxed by these limits.

TS preflights configured sources and accounts for retained project/source loads.
Its bounded reader detects growth and changes during reads. Required unreadable
or missing sources fail explicitly instead of being quietly omitted; optional
missing resolution probes are allowed.

A rejected MCP operation returns `isError` and structured error detail, including
resource/path/observed/limit/remediation for resource failures. It does not return
a successful partial result from the failed refresh. The core disposes that
worker, so its previous snapshot cannot be served on the next successful retry.
Previously returned answers can still become stale after a filesystem edit;
bounded eventual revalidation is not a transactional snapshot of a concurrently
changing repository.

## TypeScript project references

Nonempty `projectReferences` are rejected with
`unsupported_project_references`, before semantic results are returned. This is
an explicit tool failure, not a successful result marked complete or partial.
The preview parsed reference metadata but did not provide a complete reference
graph to its Language Service host; full graph support was already absent.
The new rejection makes that limitation visible and can therefore reject projects
that previously received misleading partial results. Ordinary cross-directory
imports are separately tested and supported. This is not complete monorepo support.

## Existing measurements and tradeoffs

No timing rerun was used for this review. Medians from the two compatible sessions
in the retained comparison report:

| Measurement | Preview | Measured scaling runtime | Change |
| --- | ---: | ---: | ---: |
| C# first diagnostics | 430.865 ms | 451.476 ms | +20.611 ms / +4.78% |
| TS first diagnostics | 314.985 ms | 310.808 ms | -1.33% |
| JS first diagnostics | 316.844 ms | 314.469 ms | -0.75% |
| C# sampled peak tree RSS | 453.695 MiB | 341.500 MiB | -24.73% |
| TS sampled peak tree RSS | 343.781 MiB | 355.711 MiB | +3.47% |
| JS sampled peak tree RSS | 346.062 MiB | 341.344 MiB | -1.36% |
| C# steady tree RSS | 399.961 MiB | 341.500 MiB | -14.62% |
| TS steady tree RSS | 324.117 MiB | 355.711 MiB | +9.75% |
| JS steady tree RSS | 324.711 MiB | 341.344 MiB | +5.12% |

At 72 MiB aggregate, sampled peak TS RSS rose 474.4 to 529.8 MiB and JS rose
466.1 to 518.9 MiB. Warm references improved, but retained state has a memory cost.
These are sampled process-tree totals, not private-memory peaks or statistically
established regression budgets. Fresh process startup does not flush OS caches.
No claim is made that the subsequent correctness fixes preserve identical timings.
