# Fresh metadata batching feasibility and qualification

The candidate starts from shipped `97c1342d9234` and retains per-query leaf/ancestor
validation, uncached reads, five-second content expiry, cancellation, resource
accounting, external-input restrictions and transactional publication of snapshots.
It does not use watcher state as permission to skip metadata admission.

## Supported API and boundary

The installed Apple SDK's `getattrlistbulk(2)` manual specifies directory-relative
batched attributes, metadata for links themselves, unspecified enumeration order,
returned-attribute validity bits, and per-entry errors. `sys/attr.h` defines the
requested fields and `FSOPT_PACK_INVAL_ATTRS`. Those installed headers/manuals,
not a guessed private runtime layout, define the native boundary.

The prototype compared length and nanosecond-to-DateTime modification time with
fresh FileInfo for all 5,845 immutable fixture files: every value matched, with
26 bulk calls. This count excludes directory opens and identity calls; it is not
a traced total syscall count. Initial `O_NOFOLLOW_ANY` attempts returned EINVAL on
this host despite the SDK definition. The candidate instead walks each absolute
component using openat/O_NOFOLLOW and held directory handles. It then checks the
opened directory's filesystem ID, file ID and type against the current path after
batching. Replacement discards all prefetched entries and uses the existing path.

Windows has a potential analogous directory information API in
[FILE_ID_BOTH_DIR_INFO](https://learn.microsoft.com/en-us/windows/win32/api/winbase/ns-winbase-file_id_both_dir_info).
No Windows implementation or qualification is claimed. Linux
[getdents64](https://man7.org/linux/man-pages/man2/getdents.2.html) returns names,
inodes and types, not the size and modification time needed for snapshot admission;
a direct substitution would be insufficient. Linux and Windows keep existing
individual validation. The implementation is macOS-only and qualifies on this M6.

## Proof obligations and implementation

| Obligation | Mechanism | Evidence |
| --- | --- | --- |
| Freshness | New request-local batch, new directory handles and fresh API calls; no metadata survives Refresh | 5,845 exact FileInfo comparisons, changed length/time and negative timestamp tests |
| Ancestors | Existing CheckPath remains; native descriptor walk refuses symlink components; post-batch identity comparison | Existing ancestor mutations and deterministic directory replacement during batching |
| Leaf links and special objects | Only valid regular-file metadata without firmlink flag is admitted; everything else uses original FileInfo checks | Symlink/missing-file fallback and existing external-input/boundary tests |
| Uncached content reads | Original CheckPath/OpenCompilerInput/read/hash path is unchanged | Generated pre-read ancestor-swap guard, exact bytes-read and preview hash assertions |
| Failure precedence | Bulk entries only supply values; original sorted graph loop still applies per-file checks and resource limits | Earlier oversized source precedes later missing source |
| Transactionality | Request-local metadata and existing staged snapshot/solution updates | Five failed-refresh guards per variant |
| Bounded work | 64 KiB buffer; global maxDirectoryEntries; per-directory cap of twice declared members plus 256; missing values fall back | Zero/tiny/exhausted budgets and 600 unrelated entries |
| Bounded retention | Only declared graph member values retained, one directory at a time; pooled buffer returned on disposal | Sparse directory and descriptor lifetime tests |
| Cancellation | Before each directory component, native call and decoded record; native operations remain bounded synchronous metadata calls, as individual stat was | Cancellation injected immediately after native batch; existing worker cancellation tests |
| Malformed/unsupported data | Bounds, validity/error/type/flag/time checks; malformed records discard the batch; errors fall back | Corrupt lengths, offsets, timestamps and sizes; execute-only directory fallback |
| External inputs | Exact external catalogue never enters batch membership; original validation/read-only rules remain | Existing external compiler input and rename tests |

The OS may still block inside a metadata syscall; neither this implementation nor
the previous individual stat implementation promises interruption of an in-flight
kernel call. Directory changes concurrent with a query are not an atomic filesystem
snapshot. As with the earlier parallel-admission experiments, metadata is obtained
during the request and errors are consumed in original graph order. Target reads
still perform uncached path validation immediately before opening source bytes.

Batching is attempted for directories with at least 32 declared members; smaller
groups use the existing path. Unsupported filesystems, unavailable fields, missing
members, directory identity changes and exhausted enumeration budgets preserve the
individual-check fallback. The 32-member threshold is an implementation choice,
not a claimed statistical crossover or relaxation of scope.

The native proof harness injects cancellation/replace/corruption hooks only into a
generated helper copy. No such hook is compiled into the timed worker or proposed
runtime. `benchmark.metadata` runs that focused harness with a fresh
`FREEFLIGHT_METADATA_LABEL`; `benchmark.trusted` runs it for any macOS candidate
containing the helper before allowing measurements.

## Retained receipts

- `bin/.local/metadata-proof/`: first ABI/flags probes and exact 5,845-file comparison.
- `bin/.local/metadata-proof-darwin-v2/`: focused native proof suite, passed.
- `bin/.local/benchmarks/trusted/glider-target-bulk/`: first full preparation;
  worker/mutation suites passed, proof-harness compilation rejected missing platform
  annotations before any timing. The corrected harness explicitly requires macOS.
- `bin/.local/benchmarks/trusted/glider-target-bulk-v2/`: complete qualification and
  baseline/candidate timing run. Final results are appended after completion.

No publication, PR, push, deployment, active MCP configuration or private repository
change is authorized or performed. No Linux machine or Linux-local receipt is used.

## Revised request-local handle implementation

The first complete batch implementation opened every ancestor again for every
parent. A second version retains at most 64 directory handles until Refresh ends,
uses span-based name lookups, and still performs fresh batch calls plus a complete
uncached parent check after the identity comparison. It does not retain handles or
metadata between requests. The 100-loop helper diagnostic reduced its measured
median from 6.242 to 3.176 ms and allocation from 500,776 to 173,688 bytes. These
instrumented helper numbers exclude final request disposal and are not endpoint
latency claims.

The deterministic same-identity ancestor replacement test initially failed in
`metadata-proof-darwin-handles`: replacing an ancestor with a link to the same
original directory evaded identity comparison alone. Moving full uncached parent
validation after identity comparison fixed that case; the passing revised proof
is `metadata-proof-darwin-handles-v2`. This failure and the original candidate
remain in the local receipts. Descriptor bounds, cancellation disposal, malformed
native records, negative timestamps, unsupported directory access and replacement
fallback all passed. This is local APFS qualification, not proof of every supported
filesystem or concurrent filesystem schedule.

## Worker qualification and diagnostic costs

`bin/.local/benchmarks/trusted/glider-target-bulk-handles` contains the revised
candidate, frozen source/toolchain/fixture provenance, all raw samples and the
comparison. Three fresh sessions per variant and graph passed 4,800 ordinary
measured responses and 1,600 instrumented responses. Native and worker security,
mutation, cancellation, preview-hash and transactional-failure qualification
passed. Five deliberately failed refreshes per variant preserved the prior state.

Median session ratios, candidate/shipped (below one is faster):

| Graph | Operation | Median ratio | p90 ratio |
| --- | --- | ---: | ---: |
| 433 | Outline | .845 | .791 |
| 433 | Definition | .875 | .857 |
| 433 | References | .977 | .936 |
| 433 | Search | .877 | .892 |
| 5,845 | Outline | .963 | .990 |
| 5,845 | Definition | .970 | .968 |
| 5,845 | References | .955 | .960 |
| 5,845 | Search | 1.015 | .995 |

Instrumented full-graph outline steady-state medians (milliseconds):

| Stage/counter | Shipped | Candidate |
| --- | ---: | ---: |
| Admission | 9.678 | 7.658 |
| Individual metadata / batch metadata | 7.312 | 5.894 |
| Entire Refresh | 10.608 | 8.779 |
| Roslyn semantic operation | .023 | .028 |
| CPU ms | 10.781 | 9.059 |
| Allocated bytes | 265,312 | 455,120 |
| Instrumented individual attributes checks | 5,910 | 143 |
| Files read | 1 | 1 |

The attribute counter excludes native bulk/open/identity calls: it is not a syscall
trace or a claim that only 143 filesystem calls occur. Both steady-state samples
had zero GC collections. Batching reduces metadata cost but adds managed allocation.
At expiry both variants read all 5,845 files: Refresh medians 210.551 / 207.938 ms,
allocation 48,222,880 / 48,423,120 bytes, CPU 514.393 / 513.235 ms, GC pause
2.329 / 4.104 ms. Bulk admission does not remove the mandated content revalidation.

The first fully measured version (`glider-target-bulk-v2`) also passed, but achieved
only a .967 full-graph outline median ratio and allocated 767,720 steady-state
bytes. Its expiry Refresh was 191.034 versus 190.224 ms. It is retained as an
unselected earlier implementation; neither its samples nor the new search
regression are omitted.

## Reproduction

Run from this isolated checkout. Labels must be new; workflows refuse to overwrite
receipts. Keep timing runs serial. The first command requalifies and freezes the
candidate; the second consumes that frozen candidate and compares actual MCP
endpoints with the verified shipped bundle and official Glider 13.3.0 installation.
The local SDK paths below identify this M6, not a portable installation requirement.

```sh
PATH="/Users/jamie/Documents/Codex/2026-10-20/task/freeflight-dependabot/bin/.local/dotnet11:$PATH" \
FREEFLIGHT_TRUSTED_BENCH_LABEL=bulk-repeat \
FREEFLIGHT_TRUSTED_BENCH_BASELINE=97c1342d9234f9d2146cd209760d6af1ea125b6e \
FREEFLIGHT_TRUSTED_BENCH_CANDIDATE=WORKTREE \
FREEFLIGHT_TRUSTED_BENCH_SESSIONS=3 FREEFLIGHT_TRUSTED_BENCH_ROUNDS=100 \
FREEFLIGHT_TRUSTED_BENCH_WARMUP=10 FREEFLIGHT_TRUSTED_BENCH_INTERVAL=0.1 \
FREEFLIGHT_TRUSTED_BENCH_PADDING=4096 FREEFLIGHT_TRUSTED_BENCH_CALLERS=14 \
FREEFLIGHT_TRUSTED_BENCH_QUERY=C5 dockpipe --workflow benchmark.trusted

FREEFLIGHT_GLIDER_DOTNET_ROOT=/Users/jamie/Documents/Codex/2026-10-19/task/toolchains/dotnet \
FREEFLIGHT_GLIDER_CANDIDATE_RECEIPT="$PWD/bin/.local/benchmarks/trusted/bulk-repeat" \
FREEFLIGHT_GLIDER_LABEL=bulk-repeat \
FREEFLIGHT_GLIDER_SESSIONS=3 FREEFLIGHT_GLIDER_ROUNDS=50 \
FREEFLIGHT_GLIDER_WARMUP=10 FREEFLIGHT_GLIDER_INTERVALS=0,0.1 \
dockpipe --workflow benchmark.trusted.glider
```

To repeat only the native proof, use the same SDK PATH and
`FREEFLIGHT_METADATA_LABEL=bulk-proof-repeat dockpipe --workflow benchmark.metadata`.
For the already frozen candidate, skip the first command and point
`FREEFLIGHT_GLIDER_CANDIDATE_RECEIPT` at
`bin/.local/benchmarks/trusted/glider-target-bulk-handles` instead.

Interpretation retains the [head-to-head semantic limitations](glider-head-to-head.md):
Glider does not expose every range field, and its reference operation uses a cached
opaque key. Both graphs are synthetic, not Biztraak; fixtures, toolchains and
binaries are pinned in provenance. Loading and compilation readiness are measured
separately from requests. No instrumented duration is substituted for ordinary
endpoint timing, and differing freshness/security contracts remain material.

## Completed three-product MCP comparison

Receipt: `bin/.local/glider-comparison/target-bulk-handles/`. All 36 fresh processes,
7,200 steady-state measured semantic checks and 144 post-idle checks passed.
Three sessions per product/graph/cadence rotate execution order. Each session has
ten seconds of warm-up, fifty measured rounds, then 5.1 seconds idle. Spaced rounds
have a minimum 0.1-second interval; this is not a delay between each operation.

The candidate improves median and p90 versus shipped in all sixteen aggregate
graph/cadence/operation comparisons in this repeat. This is a qualified local
improvement, not a Glider win or statistical universality claim. Glider still leads
tiny queries and unpaced broad search; FreeFlight leads broad search when spaced.
Expiry remains unresolved and slightly regresses in aggregate. Worker-only paced
search also regressed 1.5%, as recorded above.

Cells are median of session medians / median of session p90 / maximum across all
three sessions, in milliseconds. All session tails are retained below.

| Files / round interval | Operation | Shipped 97c1342 | Batch candidate | Glider 13.3.0 |
| --- | --- | ---: | ---: | ---: |
| 433 / 0s | symbols | 0.563 / 0.573 / 0.588 | 0.494 / 0.502 / 0.726 | 0.190 / 0.201 / 1.071 |
| 433 / 0s | definition | 0.544 / 0.551 / 0.558 | 0.472 / 0.483 / 0.770 | 0.062 / 0.127 / 0.134 |
| 433 / 0s | references | 0.911 / 0.945 / 1.317 | 0.811 / 0.859 / 1.338 | 0.465 / 0.563 / 3.082 |
| 433 / 0s | workspaceSymbols | 0.645 / 0.653 / 0.899 | 0.579 / 0.586 / 0.875 | 0.449 / 0.510 / 0.624 |
| 433 / 0.1s | symbols | 3.989 / 4.310 / 38.650 | 3.595 / 4.060 / 38.714 | 1.120 / 1.404 / 2.276 |
| 433 / 0.1s | definition | 3.119 / 3.401 / 4.086 | 2.861 / 3.146 / 3.342 | 0.400 / 0.482 / 0.672 |
| 433 / 0.1s | references | 3.729 / 4.400 / 6.018 | 3.643 / 4.175 / 6.209 | 2.408 / 2.585 / 3.093 |
| 433 / 0.1s | workspaceSymbols | 2.841 / 3.000 / 4.084 | 2.607 / 2.905 / 4.446 | 2.949 / 3.410 / 3.823 |
| 5845 / 0s | symbols | 7.181 / 7.533 / 8.327 | 5.471 / 5.956 / 7.175 | 0.167 / 0.213 / 0.359 |
| 5845 / 0s | definition | 6.095 / 6.242 / 7.077 | 4.395 / 4.614 / 5.452 | 0.067 / 0.093 / 0.120 |
| 5845 / 0s | references | 6.429 / 6.631 / 8.787 | 4.728 / 5.133 / 7.156 | 0.581 / 0.678 / 0.796 |
| 5845 / 0s | workspaceSymbols | 14.168 / 14.698 / 17.096 | 12.769 / 13.186 / 15.681 | 7.184 / 8.141 / 12.196 |
| 5845 / 0.1s | symbols | 10.075 / 10.666 / 139.572 | 8.631 / 9.173 / 113.047 | 1.491 / 1.749 / 3.401 |
| 5845 / 0.1s | definition | 7.579 / 7.840 / 11.941 | 6.048 / 6.364 / 9.779 | 0.442 / 0.499 / 0.612 |
| 5845 / 0.1s | references | 7.152 / 7.513 / 8.208 | 5.767 / 6.162 / 28.278 | 2.779 / 2.978 / 4.293 |
| 5845 / 0.1s | workspaceSymbols | 14.233 / 14.896 / 25.370 | 13.955 / 14.633 / 17.223 | 28.250 / 29.686 / 31.996 |

Loading/compilation and expiry are separate. Six-process medians below combine
the two cadence sets only for these separately labelled phases. FreeFlight load
already awaits compilation; Glider reports background compilation separately.

| Files | Product | Load ms | Additional compilation ms | First post-idle outline median (min–max) ms |
| --- | --- | ---: | ---: | ---: |
| 433 | freeflight | 730.793 | included in load | 35.753 (31.978–39.859) |
| 433 | candidate | 727.615 | included in load | 36.722 (36.253–38.226) |
| 433 | glider | 621.178 | 277.500 | 2.196 (2.088–2.271) |
| 5845 | freeflight | 2942.639 | included in load | 179.481 (173.867–182.341) |
| 5845 | candidate | 2921.798 | included in load | 182.310 (162.525–186.243) |
| 5845 | glider | 1921.036 | 494.000 | 4.267 (2.169–7.729) |

### Every ordinary MCP session

Cells are median / p90 / maximum ms. No sessions or outliers were dropped.

| Session | Outline | Definition | References | Search |
| --- | ---: | ---: | ---: | ---: |
| 433-interval0-0-freeflight | 0.558 / 0.565 / 0.588 | 0.535 / 0.543 / 0.555 | 0.907 / 0.936 / 1.297 | 0.636 / 0.645 / 0.662 |
| 433-interval0-1-candidate | 0.488 / 0.500 / 0.715 | 0.467 / 0.477 / 0.714 | 0.801 / 0.850 / 1.196 | 0.564 / 0.574 / 0.586 |
| 433-interval0-2-glider | 0.132 / 0.197 / 0.206 | 0.062 / 0.127 / 0.130 | 0.462 / 0.519 / 3.082 | 0.439 / 0.499 / 0.587 |
| 433-interval0-3-candidate | 0.494 / 0.502 / 0.726 | 0.472 / 0.483 / 0.492 | 0.811 / 0.859 / 1.193 | 0.579 / 0.586 / 0.789 |
| 433-interval0-4-glider | 0.190 / 0.202 / 1.071 | 0.077 / 0.127 / 0.131 | 0.484 / 0.563 / 0.637 | 0.457 / 0.523 / 0.624 |
| 433-interval0-5-freeflight | 0.563 / 0.573 / 0.588 | 0.544 / 0.551 / 0.557 | 0.911 / 0.945 / 1.317 | 0.645 / 0.653 / 0.899 |
| 433-interval0-6-glider | 0.191 / 0.201 / 0.211 | 0.056 / 0.124 / 0.134 | 0.465 / 0.603 / 1.780 | 0.449 / 0.510 / 0.565 |
| 433-interval0-7-freeflight | 0.565 / 0.573 / 0.575 | 0.545 / 0.555 / 0.558 | 0.912 / 0.964 / 1.315 | 0.649 / 0.657 / 0.673 |
| 433-interval0-8-candidate | 0.502 / 0.513 / 0.517 | 0.479 / 0.489 / 0.770 | 0.819 / 0.875 / 1.338 | 0.585 / 0.605 / 0.875 |
| 5845-interval0-0-freeflight | 7.125 / 7.554 / 8.288 | 6.095 / 6.242 / 7.077 | 6.445 / 6.607 / 6.981 | 14.146 / 14.698 / 16.768 |
| 5845-interval0-1-candidate | 5.471 / 6.438 / 7.175 | 4.395 / 4.742 / 5.452 | 4.702 / 5.133 / 5.787 | 12.578 / 13.349 / 15.107 |
| 5845-interval0-2-glider | 0.167 / 0.218 / 0.359 | 0.067 / 0.094 / 0.120 | 0.584 / 0.678 / 0.695 | 7.108 / 7.677 / 12.196 |
| 5845-interval0-3-candidate | 5.361 / 5.728 / 6.586 | 4.384 / 4.458 / 4.975 | 4.728 / 5.160 / 7.156 | 12.769 / 13.137 / 15.519 |
| 5845-interval0-4-glider | 0.170 / 0.213 / 0.279 | 0.068 / 0.090 / 0.103 | 0.572 / 0.650 / 0.689 | 7.184 / 8.176 / 12.048 |
| 5845-interval0-5-freeflight | 7.254 / 7.533 / 8.327 | 6.149 / 6.264 / 6.800 | 6.429 / 6.631 / 7.004 | 14.322 / 14.755 / 16.745 |
| 5845-interval0-6-glider | 0.167 / 0.207 / 0.268 | 0.066 / 0.093 / 0.105 | 0.581 / 0.711 / 0.796 | 7.187 / 8.141 / 10.029 |
| 5845-interval0-7-freeflight | 7.181 / 7.484 / 8.181 | 6.095 / 6.175 / 6.600 | 6.428 / 6.684 / 8.787 | 14.168 / 14.637 / 17.096 |
| 5845-interval0-8-candidate | 5.586 / 5.956 / 6.820 | 4.447 / 4.614 / 4.858 | 4.733 / 4.912 / 5.281 | 12.769 / 13.186 / 15.681 |
| 433-interval0.1-0-freeflight | 4.054 / 4.310 / 34.640 | 3.119 / 3.401 / 3.627 | 3.729 / 4.400 / 5.471 | 2.860 / 3.000 / 3.094 |
| 433-interval0.1-1-candidate | 3.550 / 3.953 / 31.762 | 2.870 / 3.140 / 3.278 | 3.643 / 4.175 / 5.941 | 2.591 / 2.905 / 4.446 |
| 433-interval0.1-2-glider | 1.105 / 1.404 / 1.866 | 0.398 / 0.482 / 0.582 | 2.408 / 2.585 / 2.994 | 2.940 / 3.410 / 3.823 |
| 433-interval0.1-3-candidate | 3.656 / 4.352 / 34.321 | 2.861 / 3.162 / 3.342 | 3.806 / 4.412 / 6.209 | 2.672 / 2.975 / 3.985 |
| 433-interval0.1-4-glider | 1.121 / 1.730 / 2.276 | 0.402 / 0.491 / 0.672 | 2.438 / 2.887 / 3.093 | 2.984 / 3.507 / 3.750 |
| 433-interval0.1-5-freeflight | 3.950 / 4.308 / 38.650 | 3.098 / 3.393 / 4.086 | 3.686 / 4.282 / 6.018 | 2.819 / 2.990 / 4.084 |
| 433-interval0.1-6-glider | 1.120 / 1.256 / 1.429 | 0.400 / 0.476 / 0.577 | 2.398 / 2.553 / 2.754 | 2.949 / 3.327 / 3.531 |
| 433-interval0.1-7-freeflight | 3.989 / 4.640 / 31.608 | 3.159 / 3.634 / 3.734 | 3.867 / 4.602 / 5.195 | 2.841 / 3.080 / 3.433 |
| 433-interval0.1-8-candidate | 3.595 / 4.060 / 38.714 | 2.818 / 3.146 / 3.268 | 3.616 / 4.064 / 5.899 | 2.607 / 2.844 / 4.120 |
| 5845-interval0.1-0-freeflight | 10.058 / 10.666 / 139.572 | 7.579 / 7.840 / 8.149 | 7.152 / 7.414 / 7.849 | 14.071 / 14.487 / 17.307 |
| 5845-interval0.1-1-candidate | 8.574 / 9.173 / 106.864 | 6.041 / 6.413 / 7.420 | 5.767 / 6.105 / 6.390 | 13.955 / 14.572 / 16.876 |
| 5845-interval0.1-2-glider | 1.567 / 1.758 / 1.971 | 0.449 / 0.524 / 0.612 | 2.846 / 3.144 / 4.135 | 28.250 / 29.873 / 31.996 |
| 5845-interval0.1-3-candidate | 8.631 / 9.112 / 105.395 | 6.053 / 6.272 / 9.104 | 5.801 / 6.326 / 28.278 | 13.993 / 14.794 / 17.223 |
| 5845-interval0.1-4-glider | 1.467 / 1.625 / 1.700 | 0.424 / 0.481 / 0.515 | 2.705 / 2.935 / 3.178 | 28.027 / 29.294 / 31.375 |
| 5845-interval0.1-5-freeflight | 10.141 / 11.097 / 74.705 | 7.596 / 7.797 / 11.941 | 7.173 / 7.643 / 8.208 | 14.254 / 14.896 / 21.624 |
| 5845-interval0.1-6-glider | 1.491 / 1.749 / 3.401 | 0.442 / 0.499 / 0.600 | 2.779 / 2.978 / 4.293 | 28.299 / 29.686 / 31.964 |
| 5845-interval0.1-7-freeflight | 10.075 / 10.637 / 97.431 | 7.560 / 7.850 / 8.036 | 7.133 / 7.513 / 7.684 | 14.233 / 14.933 / 25.370 |
| 5845-interval0.1-8-candidate | 8.903 / 9.659 / 113.047 | 6.048 / 6.364 / 9.779 | 5.753 / 6.162 / 6.542 | 13.900 / 14.633 / 17.082 |

## Selection and remaining limits

Retain the revised helper as a local candidate: it has repeat-session MCP gains
without replacing fresh validation with watcher authority. Runtime files exactly
match the frozen `glider-target-bulk-handles/candidate/source` measurement inputs.
`benchmark.metadata` was also run end to end with label `darwin-final-workflow`;
zero build warnings/errors and all focused proofs passed. `repo.check` and native
workflow YAML validation passed. Initial sandboxed DockPipe closing checks stopped
before running because its existing durable state directory was outside the
sandbox; the authorized reruns passed. Both logs remain local.

The cost attribution comes from Program.cs `Refresh`/`CheckSnapshotPath`, helper
`TryGet`/`Load`/`OpenDirectory`, and the generated profiling wrapper around the
unchanged semantic invocation. The worker still admits every source, including
fallback leaf checks; it retains O(N) processing. Fresh directory metadata reduces
syscall crossings but is not an O(1) query design. At expiry the unchanged
`ReadSnapshot` path performs full uncached checks, asynchronous reads and hashing.
No source-confirmed claim is made that switching those reads to synchronous I/O
preserves cancellation on every packaged runtime; that change was not implemented.

Remaining qualification: other macOS filesystems and packaged architectures, Linux
and Windows builds/tests, and the real Linux/Biztraak fixture. Existing Linux/Windows
metadata execution remains individual checks; the new lexical member catalogue is
still constructed at trusted open on those platforms. No equivalent cross-platform
batch implementation is claimed. The candidate adds native parsing and request-local
handles, so its modest paced-search gain must be weighed against that maintenance
cost. The directory APIs do not provide an atomic filesystem snapshot; existing
uncached pre-read checks and transactional failure behavior remain essential.

No permission blocker remains for this local investigation. Beating Glider on tiny
queries is still an unmet goal. This evidence supports a bounded improvement over
shipped FreeFlight, not removing whole-graph validation, weakening the five-second
content guarantee, or publishing an unqualified platform build.
