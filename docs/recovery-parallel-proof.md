# Recovery parallelism: ordered failure and drain gate

This local M6 pass starts at `a74167f`; production runtime remains the accepted
`6a06b1d` cancellation-lifetime fix. No parallel recovery runtime change is accepted.
The new artifact is a repeatable negative qualification gate, not a performance
candidate or a claim that every parallel design is impossible.

## Source contract

`workers/roslyn/Program.cs:Refresh` checks sorted paths and metadata, then checks the
per-file size before opening content. Each actual read chunk is checked against
per-file and aggregate workspace limits before hashing/buffering. Publication,
recovery timestamp/generation advancement and dirty-version acknowledgment happen
only after all files, final cancellation and generation checks succeed. Recovery
still begins when the five-second deadline requires it; there is no deferred sweep.

`CheckPath` rejects reparse points but does not reject a FIFO's file type.
`OpenCompilerInput` uses ordinary `FileStream` construction for workspace files.
The POSIX nonblocking/no-follow open is confined to exact external compiler inputs.
`ReadCompilerBytes` observes cancellation before its synchronous Darwin read;
neither that check nor the accepted cancellation-source lifetime repair interrupts
an already-running synchronous open. These are separate concerns.

A proposed bounded pre-open queue could overlap the dominant open/path work while
leaving reads and actual-byte accounting serial. It must capture later errors and
consume them in sorted order, keep descriptors bounded, and drain every task before
returning a failed/cancelled request. Merely enforcing a queue width does not prove
that drain completes.

## Executed negative gates

`benchmark.recovery.proof` copies the current path-check and open methods into an
isolated .NET 11 probe. External-input code is retained but the probe selects only
the workspace branch. Two disposable files model an earlier oversized input and a
later FIFO. No live checkout or MCP process is used as the fixture.

Serial admission reports A's size error without opening B. At widths two and four,
the generated queue first lets later tasks validate B, then exposes A's ordered
size error, cancels, and waits for those tasks. In both cases the open does not
return or drain within the containing process's three-second deadline. The harness
kills only its own generated child and records exit -9 as expected containment,
not as a passing worker exit. This does not establish an infinite-time result.
The v2 proof uses dedicated tasks and a countdown barrier, replacing v1's scheduling
delay. Both receipts are retained; v2 is the deterministic ordering proof.

The second gate enumerates all six completion schedules of two 12 KiB inputs with
8+4 KiB chunks and a 20 KiB aggregate limit. Three schedules make a shared completion
counter report A rather than serial order's B at observed 24 KiB. An ordered ledger
returns B in every schedule. This is a finite accounting model, not a worker run.

Receipts:

- `bin/.local/benchmarks/recovery-proof/ordered-open-v1/result.json`
- `bin/.local/benchmarks/recovery-proof/ordered-open-v2/result.json`

Each retains source commit/hash, extracted helper hash, SDK, host, child outcomes
and every accounting schedule. Generated source, build output and child logs remain
beside it. Executed on macOS 27.0.1 arm64, SDK `11.0.100-rc.2.26504.105`.

```sh
PATH="$PWD/bin/.local/perf-venv/bin:/Users/jamie/Documents/Codex/2026-10-20/task/freeflight-dependabot/bin/.local/dotnet11:$PATH" \
DOTNET_CLI_USE_MSBUILD_SERVER=0 \
FREEFLIGHT_RECOVERY_PROOF_LABEL=ordered-open-repeat \
dockpipe --workflow benchmark.recovery.proof
```

Use a fresh label. The workflow refuses to overwrite receipts. The only host
special-file operation is a FIFO inside its generated disposable fixture.

## Decision and next constraints

Reject speculative workspace opens with the unchanged opening primitive. They can
introduce a blocking operation on a later file that serial admission would never
reach after an earlier error. Returning without draining would instead leave work
and resources alive after a failed request, which is not accepted. A successful
regular-file microbenchmark would not answer this failure case.

This does not show that ordinary serial recovery is immune to FIFO blocking: it
can encounter the same primitive when that file is actually reached. Nor does it
prove that every bounded parallel design is unsafe. The specific missing capability
for this design is safe termination of speculative filesystem operations, not an
unordered result queue.

A follow-up open primitive would need nonblocking open plus handle-based file-type
validation, preserve external-input flags, and qualify replacement races and
platform-specific behavior. Prechecking file type alone is insufficient because
replacement can occur before open. Nonblocking FIFO handling also does not prove
bounded completion for every regular file/filesystem syscall. Process isolation
could provide a stronger cancellation boundary but would add a substantial worker
lifecycle/IPC design; no such architecture is silently introduced here.

A narrower alternative keeps filesystem operations and byte charging ordered and
parallelizes only bounded CPU work after reads. It avoids this speculative-open
failure, but has a much smaller opportunity: the previously recorded diagnostic
hash-append stage is about 10.9 ms of 160.1 ms (roughly 6.8%, before scheduling or
copy costs). This is a ceiling estimate from older instrumentation, not a measured
speedup or a new profile. The dominant 70 ms open and 39 ms path stages remain.

No new recovery median/p90/CPU/allocation or ordinary MCP comparison is reported:
the proposed filesystem queue failed its prerequisite correctness gate. Repeating
unchanged timing matrices would not qualify it. Existing ordinary controls and
unfavorable samples remain in `docs/query-position-controls.md`; the last measured
post-idle full sweep remains around 158 ms. Existing security/mutation/transaction
qualification is historical evidence for the unchanged runtime, not newly rerun
qualification of a parallel candidate. The goal of reducing that cost is still open.

No permission action was denied or left pending. Initial repo.check used system
Python and failed for missing PyYAML; rerunning with the existing task-local Python
environment passed. No publication, remote job, installed MCP or service change.
