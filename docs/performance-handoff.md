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

## Small Git assets and rebuildable local output

The blanket requirement to transfer all18GB is superseded by the
[small benchmark asset policy](../benchmarks/README.md). Git now retains a bounded,
lossless evidence set (under10MiB), the complete catalog of discovered JSON receipts,
and six tiny rejected-candidate patches. The patches reconstruct from exact94 with
verified resulting source hashes. Authored workflows, deterministic fixture generators,
commits, dependency locks and toolchain versions already live in Git.

Build directories, SDK/dependency caches, copied source trees and generated fixtures
remain ignored under `bin/.local` and should be rebuilt when needed. They are not
mandatory migration assets. Exact historical executable hashes remain provenance;
a rebuild on a different path/toolchain/host is not guaranteed byte-identical.

Large original observations are a different category from builds. The catalog marks
133 unique compressed JSON objects external (about108MiB). They remain local under
`bin/.local/evidence/20261023-arm64/objects` for optional later R2 archiving. They are
not required to compile or run new experiments, but recompilation cannot recreate
old measurements. Bulk diagnostic logs/traces are excluded from the JSON export;
retain selected originals externally only when their investigation needs them.
No original receipt, log, trace, build or cache was deleted in this change.

```sh
dockpipe --workflow benchmark.evidence.check
```

This verifies the Git objects and reconstructs six rejected source candidates without
the original18GB tree. It checks archived bytes, not new runtime correctness or a new
benchmark pass. Historical binary-dependent audits retain their original limitations.

Historical metadata has absolute Mac paths. Keep original bytes/hashes; use a separate
remote adapter with equivalent pinned tools and fresh labels rather than rewriting old
receipts to appear portable. SDK11 is11.0.100-rc.2.26504.105; historical Glider fixtures
use SDK10.0.402. Record native architecture, OS, runtime/tool versions and all options.
No remote adapter or x86 qualification is claimed by this storage change.

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
