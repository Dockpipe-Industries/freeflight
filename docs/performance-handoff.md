# Performance checkpoint handoff — 2026-10-23

The preserved performance worktree is `/Users/jamie/Source/freeflight-perf`, originally
`investigate/rc2-warm-refresh` at `94eb4207c8ffd2d5544bca8a52dcb8d451285015`.
This checkpoint consolidates its committed history and remaining authored performance
work onto `js/dev`, at the user's explicit request. It is a development checkpoint,
not acceptance of rejected candidates or release/platform qualification.

The active runtime retains the exact94 candidate. Strict defaults, startup authority,
fresh validation and opt-in cooperative recovery remain. Rejected model/buffer/path/
attribute/JSON-copy/frame-reader experiments remain unaccepted in their reports and
local frozen source/binary receipts. Do not install a rejected snapshot as the baseline.

Start with [the structural review](reference-structural-review.md),
[counter qualification failures](reference-work-qualification.md),
[fixed-schedule attribution](reference-fixed-attribution.md), and
[background recovery evidence](background-recovery.md). No reproducible overall win
against Glider has been established. Last reader screen:2,304 exact measured responses;
reference p90+56.3% on the large fixture and call-hierarchy p90+15.0% on the small fixture.
Both trigger the predeclared stop gate; one candidate session concentrates the reference
tail. Two-session screening does not establish that the source change caused it.

## Data that must move separately

Git contains authored source/workflows, test assets and detailed reports. Raw benchmark
receipts, generated snapshots/binaries, traces, fixtures, SDKs and caches remain ignored
under `bin/.local`, as repository policy requires. They are not uploaded by a Git push.
Preserve and transfer these local paths before retiring the Mac/worktree:

- `bin/.local/benchmarks/` (approximately18GiB, includes successful and failed receipts).
- `bin/.local/perf-preservation/` (approximately88MiB, includes the rejected model reuse).
- `bin/.local/perf-handoff/20261023-js-dev-checkpoint/` (pre-commit dirty-file/patch backup).

Retain exact bytes, relative layout and existing manifests/checksums; logs/manifests have
historical absolute Mac paths. Do not rewrite historical receipts in place to make a
remote replay appear portable. The existing workflows also contain local fixture/SDK
paths; author a separate remote adapter using equivalent pinned tools and fresh output
labels. No remote execution adapter or x86 qualification is claimed by this checkpoint.
SDK11 is11.0.100-rc.2.26504.105; historical Glider fixtures use SDK10.0.402. Record native
architecture, OS, runtime/tool versions and all options in each new run.

## Next work

Pause small candidate screens until unchanged-binary A/A controls characterize process,
position and tail variability under the recorded schedules. If native x86 execution is
available through DockPipe, run the same bounded controls there and on ARM. Compare
FreeFlight and Glider within each host. Different CPU/OS hosts cannot isolate ISA alone;
x86 emulation on ARM does not substitute for native x86. Do not silently change power,
affinity, trust or runtime configuration to obtain a favorable result. Keep all samples.

Remaining: reference work-versus-runtime attribution, definition/search versus Glider,
matched idle cost, native allocations, long memory runs, real repositories and other
platforms. A later worker ownership/dispatch review must retain the independent control
reader, queue bounds, cancellation, cooperative gate handoff and shutdown. Existing
correctness evidence is scoped to its recorded sources/binaries/platforms.

The main checkout's pre-existing local packaging/hotpath files are unrelated to this
performance checkpoint and are preserved separately rather than silently committed.
Pushing `js/dev` does not authorize promotion to dev/staging/master, package publication,
site deployment, or acceptance of performance claims.
