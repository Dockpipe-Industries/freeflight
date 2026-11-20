# Cancellation-source lifetime correction

The EOF failure found during native attribution is a production race, amplified
but not introduced by diagnostic plumbing. `Program.Main` can capture an active
cancellation source while its job removes and disposes that source. Calling
`Cancel()` afterward throws. EOF/explicit shutdown escape the request-level catch;
a late explicit cancel instead produces a spurious error response.

The same vulnerable cancellation/disposal statements are present in shipped
`97c1342` source. The deterministic executable proof here targets local ordinary
and diagnostic source builds, not an injected or rerun shipped package. Earlier
ordinary qualification did not prove absence of this race.

`RequestCancellation` gives each in-progress `Cancel` call a lifetime lease.
Completion prevents new cancellation calls and defers source disposal until the
last existing call finishes. Cancellation callbacks execute outside the lifetime
lock; a callback can therefore complete the request itself or wait for completion
on another thread. The token is captured at construction, timeout remains 60
seconds, and queue membership/limits, gate ordering, error handling and task drain
are unchanged. No broad exception suppression is used.

The correction does not change strict defaults, incremental recovery deadlines,
path admission/pre-open validation, external-input handling, byte budgets, Roslyn
transactions or edit hashes. No response-copy or recovery-parallelism experiment
is included.

## Deterministic proof

`dockpipe --workflow benchmark.shutdown` with a fresh
`FREEFLIGHT_SHUTDOWN_LABEL` generates source-only barriers around the actual
`Program` paths. A job waits after its reply; the input loop captures its active
source; the job then removes/disposes it; only then does cancellation proceed.
The same interleaving is forced in ordinary and diagnostic builds, for EOF,
explicit shutdown and explicit cancel. Hooks never enter production/timing builds.

`bin/.local/benchmarks/shutdown/lifetime-v2` confirms all 12 expected outcomes:
before source `6636d94` fails each forced case (crash for EOF/shutdown, extra error
for cancel), while the fixed source exits zero without an extra response in all
six cases. Five additional lifetime contracts cover idempotence, cancellation
delivery, completion during an in-flight callback, cross-thread callback completion
without a lock cycle, and callback-exception propagation with eventual disposal.
`lifetime-v1` is retained as the earlier interleaving-only proof.

Both existing worker test scripts now assert worker EOF exit status. The native
benchmark's crash-log rejection is retained; a Python test's successful exit alone
is not enough to qualify a crashed worker. Earlier failing diagnostic receipts
remain failed and are not retroactively relabeled clean.

## Worker qualification

`bin/.local/benchmarks/trusted/shutdown-lifetime-v1` passed ordinary worker semantics,
strict/trusted boundary and external-input checks, mutation tests, Darwin metadata
and read proofs, all 16 incremental fault cases, and five failed-refresh state
preservation cases per variant. No unhandled-exception log appeared in this run.
The baseline can pass ordinary tests while still failing the deterministic race
proof; that is not evidence its shutdown implementation was safe.

Commands use the pinned SDK and existing Python environment:

```sh
PATH="$PWD/bin/.local/perf-venv/bin:/Users/jamie/Documents/Codex/2026-10-20/task/freeflight-dependabot/bin/.local/dotnet11:$PATH" \
DOTNET_CLI_USE_MSBUILD_SERVER=0 FREEFLIGHT_SHUTDOWN_LABEL=lifetime-v2 \
dockpipe --workflow benchmark.shutdown

PATH="$PWD/bin/.local/perf-venv/bin:/Users/jamie/Documents/Codex/2026-10-20/task/freeflight-dependabot/bin/.local/dotnet11:$PATH" \
DOTNET_CLI_USE_MSBUILD_SERVER=0 FREEFLIGHT_TRUSTED_BENCH_LABEL=shutdown-lifetime-v1 \
FREEFLIGHT_TRUSTED_BENCH_BASELINE=6636d94 \
FREEFLIGHT_TRUSTED_BENCH_BASELINE_INCREMENTAL=1 FREEFLIGHT_TRUSTED_BENCH_INCREMENTAL=1 \
FREEFLIGHT_TRUSTED_BENCH_PADDING=4096 FREEFLIGHT_TRUSTED_BENCH_CALLERS=14 \
dockpipe --workflow benchmark.trusted.qualification
```

Choose unused receipt labels for repeats. Toolchain paths are M6-local; substitute
equivalent pinned installations elsewhere. These are local checks, not new remote
platform qualification or a performance claim. Ordinary matched timing and native
diagnostic qualification follow separately.

The corrected native diagnostic qualification subsequently passed in
`bin/.local/glider-comparison/position-lifetime-v2-fixed-diagnostic-qualification`,
including native protocol/process tests and both worker suites with exit-status
checks and crash-log rejection. No unhandled shutdown exception appeared. See
[ordinary controls and their retained mixed results](query-position-controls.md).
