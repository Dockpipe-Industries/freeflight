# Expiry read scheduling investigation

This local candidate starts from `d0342d41bd5559068397ffb5a5ad7cc2fbfc8e39`.
That metadata candidate remains recoverable. The five-second snapshot deadline,
uncached pre-read path checks, sorted failure order, staged publication, resource
accounting, bytes/hash semantics and external-input handling are unchanged.

## Source and cost

`SourceEngine.Refresh` checks the snapshot age before each file, then performs
uncached `CheckPath`, `OpenCompilerInput`, bounded reads, accounting, SHA-256 and
snapshot staging. A hash match reuses Roslyn text only after the bytes are freshly
read and hashed. No earlier hash can establish freshness of content whose metadata
was preserved. Watcher generation and dirty state are additional invalidators,
not sufficient authority to skip expiry.

The prior full-graph candidate's instrumented expiry outline read all 5,845 inputs
(23,941,120 bytes). Its stage times were: open 95.817 ms, uncached path 48.104 ms,
read I/O 17.945 ms, hash creation 2.118 ms, append 11.665 ms, finish 4.306 ms,
buffer write 2.918 ms, total Refresh 207.938 ms. These nested stage durations are
not production latency and do not account for all scheduling in their nominal
stage names. The earlier scratch-reuse candidate is not reinstated.

## Pinned runtime evidence

The locally installed .NET 11 RC2 `System.Private.CoreLib.dll` was inspected using
reflection and an IL decoder. The complete IL and assembly hash are retained by
`benchmark.expiry`, not inferred from a different public runtime version.

On this Darwin runtime, `OSFileStreamStrategy.ReadAsync` calls
`RandomAccess.ReadAtOffsetAsync`, which queues a `SafeFileHandle.ThreadPoolValueTaskSource`.
Its `ExecuteInternal` checks cancellation before calling synchronous
`RandomAccess.ReadAtOffset`; completion returns the result/error without an
in-flight cancellation registration. The synchronous FileStream path calls the
same read routine. That routine uses PRead or its existing non-offset fallback.
The file streams here are private to a single refresh; no other task shares their
position or buffering. Worker invocation already runs inside `Task.Run`, while the
protocol input loop handles cancel messages independently.

The candidate therefore performs internal-file reads on that existing worker task
on macOS. Each read is still at most 8,192 bytes and checks the token before the
read. Existing resource checks and cancellable memory writes follow the read in
the same order. Neither old nor proposed implementation interrupts an in-flight
kernel read on this runtime. External inputs and other platforms retain ReadAsync.
There is no background maintenance, extra reader, extended TTL or hidden idle I/O.
This is a pinned-runtime argument, not a universal claim about all operating
systems or future .NET implementations.

## Proof and retained setup failure

`benchmark.expiry` exercises the exact extracted helper body: exact bytes and EOF,
pre-cancel with no read, cancellation during a read followed by cancellable buffer
write, I/O failure precedence, cancellation between bounded chunks, and the async
fallback. It records source, SDK and corelib hashes plus IL. Existing worker and
transaction tests remain required; this helper proof does not replace them.

`expiry-inline-v1` passed ordinary qualification but its generated transaction
build failed: the injector's method boundary included the new helper. The helper
was moved before Refresh to preserve that existing boundary. No timing ran in this
failed attempt. `expiry-proof-inline-preflight` passed the focused proof, initially
with a test-only nullable-annotation warning; the harness annotation was corrected.
All of these receipts remain in `bin/.local`.

The inspected framework and prior self-contained macOS candidate bundle contain
identical corelib bytes, SHA-256
`efbd28e6caa106316440b0793d31d51352f132f15de0e358ef7e7f81f2ac4781`.
The pinned SDK is `11.0.100-rc.2.26504.105`, runtime
`11.0.0-rc.2.26504.105`. Repeat the IL review when changing the runtime; an API name
alone does not establish its cancellation implementation.

## Repeat commands

Run serially from this checkout with a fresh label. The proof is included in
trusted qualification when the candidate contains `ReadCompilerBytes`.

```sh
PATH="/Users/jamie/Documents/Codex/2026-10-20/task/freeflight-dependabot/bin/.local/dotnet11:$PATH" \
FREEFLIGHT_TRUSTED_BENCH_LABEL=expiry-inline-repeat \
FREEFLIGHT_TRUSTED_BENCH_BASELINE=d0342d41bd5559068397ffb5a5ad7cc2fbfc8e39 \
FREEFLIGHT_TRUSTED_BENCH_CANDIDATE=WORKTREE \
FREEFLIGHT_TRUSTED_BENCH_SESSIONS=3 FREEFLIGHT_TRUSTED_BENCH_ROUNDS=50 \
FREEFLIGHT_TRUSTED_BENCH_WARMUP=10 FREEFLIGHT_TRUSTED_BENCH_INTERVAL=0.1 \
FREEFLIGHT_TRUSTED_BENCH_PADDING=4096 FREEFLIGHT_TRUSTED_BENCH_CALLERS=14 \
FREEFLIGHT_TRUSTED_BENCH_QUERY=C5 dockpipe --workflow benchmark.trusted
```

Focused proof only: with the same SDK PATH,
`FREEFLIGHT_EXPIRY_LABEL=inline-repeat dockpipe --workflow benchmark.expiry`.
No active MCP configuration, other service, deployment or remote repository state
is changed. Linux/Biztraak measurements are not inferred from this synthetic test.

## Worker qualification results

`bin/.local/benchmarks/trusted/expiry-inline-v2/` passed all worker/native security,
mutation, resource, cancellation and generated runtime/read proofs. Each variant
preserved state through five failed refreshes, including the pre-read ancestor
swap. Three ordinary sessions per variant/graph passed 2,400 measured responses;
four separate diagnostic sessions passed 800. All samples, warm-up, startup,
expiry, outliers and instrumented stages remain in the receipt.

The baseline is the previous metadata candidate d0342d41, so this comparison
isolates read scheduling. It is not the shipped/Glider endpoint comparison.


| Files | Operation | Baseline medians ms | Candidate medians ms | Baseline p90 ms | Candidate p90 ms | Median ratio | p90 ratio |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 433 | symbols | 4.668, 4.223, 4.310 | 4.614, 2.361, 3.787 | 5.425, 5.016, 4.965 | 5.090, 4.601, 4.765 | 0.879 | 0.950 |
| 433 | definition | 2.900, 2.557, 2.637 | 2.918, 1.529, 2.540 | 3.552, 3.237, 3.112 | 3.288, 2.810, 3.154 | 0.963 | 0.974 |
| 433 | references | 3.630, 3.313, 3.475 | 3.590, 2.093, 3.427 | 4.550, 4.213, 4.332 | 4.481, 3.896, 4.497 | 0.986 | 1.034 |
| 433 | workspaceSymbols | 2.825, 2.484, 2.689 | 2.882, 1.566, 2.618 | 3.472, 2.877, 2.980 | 3.440, 2.620, 3.176 | 0.974 | 1.066 |
| 5845 | symbols | 9.585, 9.620, 9.468 | 9.151, 9.511, 9.657 | 10.339, 10.535, 10.443 | 10.479, 10.339, 10.844 | 0.992 | 1.003 |
| 5845 | definition | 7.075, 6.912, 7.132 | 6.715, 7.007, 7.098 | 7.652, 7.591, 7.741 | 7.568, 7.517, 7.738 | 0.990 | 0.989 |
| 5845 | references | 6.662, 6.591, 6.641 | 6.401, 6.639, 6.635 | 7.206, 7.171, 7.123 | 6.938, 7.220, 7.224 | 0.999 | 1.007 |
| 5845 | workspaceSymbols | 9.574, 9.343, 9.459 | 9.299, 9.635, 9.634 | 10.407, 10.104, 10.578 | 10.480, 10.375, 10.591 | 1.019 | 1.007 |

Full-graph ordinary expiry outlines, all reading 5,845 files:

- Baseline: 181.727, 198.889, 179.581 ms; median 181.727.
- Candidate: 158.112, 156.306, 160.295 ms; median 158.112.

Small graph, all reading 433 files:

- Baseline: 36.651, 35.590, 34.382 ms.
- Candidate: 33.414, 32.029, 22.526 ms. The unusually low third sample is retained,
  not selected as the representative median.

Instrumented full-graph expiry (one diagnostic session each, not ordinary timings):

| Counter/stage | Baseline | Candidate |
| --- | ---: | ---: |
| CPU ms | 486.965 | 177.438 |
| Refresh ms | 190.284 | 177.071 |
| Open ms | 76.649 | 87.435 |
| Path validation ms | 47.102 | 42.057 |
| Read I/O ms | 19.710 | 7.427 |
| Hash create/append/finish ms | 18.915 | 15.523 |
| Allocated bytes | 47,859,056 | 44,785,800 |
| GC pause ms | 3.367 | 2.420 |
| Gen0 / Gen1 / Gen2 | 5 / 1 / 0 | 4 / 0 / 0 |
| Files read | 5,845 | 5,845 |
| Bytes read | 23,941,120 | 23,941,120 |

CPU reduction is substantial, but elapsed gains are modest and several steady-state
worker p90s regress. No background CPU or I/O was introduced. Byte counters measure
application reads, not physical disk traffic or kernel cache misses. No syscall
trace is claimed. The remaining open/path costs dominate the expiry budget.

Native MCP preparation `target-expiry-inline` exited 1 after compilation with no
reported error and an empty native output directory. No timing process started and
no surviving build/benchmark process was found. A fresh-labelled retry,
`target-expiry-inline-v2`, with process-local `DOTNET_CLI_USE_MSBUILD_SERVER=0`
published successfully. The original failure log is retained; its cause is not
asserted. No service restart or persistent SDK configuration change was made.

## Completed native MCP comparison

`bin/.local/glider-comparison/target-expiry-inline-v2/` passed 36 fresh processes,
7,200 steady-state semantic checks and 144 post-idle checks. Candidate includes
the metadata batching candidate plus inline internal reads; shipped is 97c1342.
The d0342 worker comparison above isolates inline reads. Glider remains 13.3.0.

Cells are median of session medians / median of session p90 / maximum across
three sessions, milliseconds. All sessions are retained below.

| Files / round interval | Operation | Shipped | Candidate | Glider |
| --- | --- | ---: | ---: | ---: |
| 433 / 0s | symbols | 0.572 / 0.659 / 2.307 | 0.510 / 0.527 / 1.008 | 0.139 / 0.204 / 0.235 |
| 433 / 0s | definition | 0.556 / 0.570 / 1.157 | 0.488 / 0.506 / 0.578 | 0.118 / 0.126 / 0.194 |
| 433 / 0s | references | 0.935 / 1.143 / 1.807 | 0.869 / 0.983 / 2.977 | 0.459 / 0.547 / 3.509 |
| 433 / 0s | workspaceSymbols | 0.661 / 0.688 / 1.342 | 0.605 / 0.626 / 1.053 | 0.447 / 0.476 / 0.649 |
| 433 / 0.1s | symbols | 6.147 / 6.610 / 35.044 | 5.850 / 6.380 / 36.737 | 2.085 / 2.370 / 2.739 |
| 433 / 0.1s | definition | 3.685 / 4.180 / 5.658 | 3.451 / 3.981 / 5.059 | 0.649 / 0.785 / 1.040 |
| 433 / 0.1s | references | 4.337 / 5.082 / 6.420 | 4.251 / 4.944 / 6.584 | 3.157 / 3.773 / 4.163 |
| 433 / 0.1s | workspaceSymbols | 3.170 / 3.705 / 4.622 | 3.137 / 3.939 / 5.498 | 3.744 / 4.130 / 4.802 |
| 5845 / 0s | symbols | 8.842 / 9.439 / 12.535 | 7.203 / 7.615 / 8.365 | 0.201 / 0.281 / 2.995 |
| 5845 / 0s | definition | 7.268 / 7.606 / 9.722 | 5.351 / 5.638 / 6.580 | 0.079 / 0.102 / 0.186 |
| 5845 / 0s | references | 7.489 / 7.901 / 9.350 | 5.551 / 6.074 / 7.176 | 0.622 / 0.711 / 0.908 |
| 5845 / 0s | workspaceSymbols | 15.633 / 16.356 / 18.376 | 13.992 / 15.029 / 17.074 | 7.440 / 8.644 / 18.810 |
| 5845 / 0.1s | symbols | 11.163 / 11.481 / 122.337 | 9.629 / 10.029 / 52.404 | 1.630 / 1.858 / 3.333 |
| 5845 / 0.1s | definition | 8.198 / 8.541 / 26.901 | 6.464 / 6.974 / 64.103 | 0.445 / 0.556 / 0.886 |
| 5845 / 0.1s | references | 7.724 / 8.160 / 17.211 | 6.256 / 6.844 / 100.392 | 2.450 / 2.857 / 3.926 |
| 5845 / 0.1s | workspaceSymbols | 15.897 / 16.846 / 52.995 | 14.078 / 16.059 / 46.216 | 23.737 / 25.785 / 29.938 |

### Separate load and post-idle phases

Six-session medians combine the cadence groups only for these separate phases.
Glider compilation is additional to load; FreeFlight awaits it inside load.

| Files | Product | Load ms | Additional compilation ms | Post-idle outline median (min–max) ms |
| --- | --- | ---: | ---: | ---: |
| 433 | freeflight | 762.513 | included | 35.301 (27.258–39.260) |
| 433 | candidate | 760.453 | included | 33.943 (32.950–34.557) |
| 433 | glider | 652.886 | 286.500 | 2.284 (1.986–2.418) |
| 5845 | freeflight | 2972.201 | included | 180.549 (177.233–184.037) |
| 5845 | candidate | 3019.248 | included | 158.335 (156.489–176.629) |
| 5845 | glider | 2073.456 | 513.000 | 3.469 (1.390–8.473) |

The full-graph post-idle medians are 180.549 ms shipped, 158.335 ms candidate,
and 3.469 ms Glider. The candidate outlier of 176.629 ms remains included. This
does not close the Glider gap. A 487-to-177 ms diagnostic CPU reduction and lower
expiry latency support retaining the local candidate, while the worker p90/search
regressions above remain limitations. There is no universal speed or platform claim.

### Every steady-state session

| Session | Outline med/p90/max | Definition | References | Search |
| --- | ---: | ---: | ---: | ---: |
| 433-interval0-0-freeflight | 0.585 / 0.787 / 2.307 | 0.560 / 0.696 / 1.157 | 0.955 / 1.340 / 1.807 | 0.665 / 0.911 / 1.342 |
| 433-interval0-1-candidate | 0.510 / 0.580 / 0.858 | 0.488 / 0.519 / 0.574 | 0.860 / 0.984 / 1.426 | 0.605 / 0.742 / 1.053 |
| 433-interval0-2-glider | 0.130 / 0.204 / 0.218 | 0.121 / 0.127 / 0.194 | 0.457 / 0.547 / 0.651 | 0.447 / 0.472 / 0.542 |
| 433-interval0-3-candidate | 0.509 / 0.527 / 1.008 | 0.488 / 0.506 / 0.543 | 0.870 / 0.939 / 1.347 | 0.600 / 0.618 / 0.773 |
| 433-interval0-4-glider | 0.139 / 0.202 / 0.214 | 0.057 / 0.126 / 0.136 | 0.460 / 0.547 / 0.677 | 0.447 / 0.477 / 0.615 |
| 433-interval0-5-freeflight | 0.571 / 0.584 / 0.791 | 0.552 / 0.567 / 0.677 | 0.930 / 1.094 / 1.408 | 0.653 / 0.670 / 0.719 |
| 433-interval0-6-glider | 0.188 / 0.204 / 0.235 | 0.118 / 0.126 / 0.129 | 0.459 / 0.543 / 3.509 | 0.440 / 0.476 / 0.649 |
| 433-interval0-7-freeflight | 0.572 / 0.659 / 0.975 | 0.556 / 0.570 / 0.819 | 0.935 / 1.143 / 1.438 | 0.661 / 0.688 / 0.847 |
| 433-interval0-8-candidate | 0.513 / 0.525 / 0.645 | 0.491 / 0.501 / 0.578 | 0.869 / 0.983 / 2.977 | 0.608 / 0.626 / 1.025 |
| 5845-interval0-0-freeflight | 8.744 / 9.439 / 12.535 | 7.181 / 7.606 / 8.348 | 7.489 / 7.901 / 8.267 | 15.633 / 16.356 / 18.172 |
| 5845-interval0-1-candidate | 7.203 / 7.615 / 7.894 | 5.391 / 5.722 / 6.126 | 5.623 / 6.089 / 6.352 | 13.865 / 14.693 / 16.121 |
| 5845-interval0-2-glider | 0.230 / 0.296 / 0.638 | 0.084 / 0.118 / 0.186 | 0.635 / 0.730 / 0.908 | 7.601 / 8.646 / 12.777 |
| 5845-interval0-3-candidate | 7.034 / 7.599 / 7.997 | 5.291 / 5.638 / 5.922 | 5.538 / 6.002 / 6.537 | 13.992 / 15.082 / 17.074 |
| 5845-interval0-4-glider | 0.201 / 0.281 / 2.995 | 0.079 / 0.101 / 0.115 | 0.622 / 0.711 / 0.829 | 7.440 / 8.644 / 18.810 |
| 5845-interval0-5-freeflight | 9.000 / 9.480 / 12.472 | 7.375 / 7.968 / 9.722 | 7.619 / 8.049 / 9.350 | 15.587 / 16.638 / 18.271 |
| 5845-interval0-6-glider | 0.194 / 0.244 / 0.311 | 0.077 / 0.102 / 0.115 | 0.612 / 0.665 / 0.850 | 7.268 / 7.746 / 14.101 |
| 5845-interval0-7-freeflight | 8.842 / 9.202 / 12.366 | 7.268 / 7.538 / 7.927 | 7.393 / 7.860 / 7.917 | 15.668 / 16.292 / 18.376 |
| 5845-interval0-8-candidate | 7.330 / 7.827 / 8.365 | 5.351 / 5.638 / 6.580 | 5.551 / 6.074 / 7.176 | 14.141 / 15.029 / 16.919 |
| 433-interval0.1-0-freeflight | 6.116 / 6.605 / 35.044 | 3.436 / 4.123 / 5.658 | 4.337 / 5.045 / 5.994 | 3.257 / 3.705 / 4.622 |
| 433-interval0.1-1-candidate | 5.799 / 6.380 / 35.421 | 3.350 / 3.981 / 4.873 | 4.283 / 5.187 / 6.021 | 3.107 / 4.128 / 4.629 |
| 433-interval0.1-2-glider | 2.098 / 2.277 / 2.575 | 0.659 / 0.785 / 1.008 | 3.129 / 3.853 / 4.163 | 3.776 / 4.174 / 4.525 |
| 433-interval0.1-3-candidate | 5.850 / 6.452 / 25.364 | 3.451 / 3.916 / 4.240 | 4.187 / 4.944 / 6.220 | 3.153 / 3.801 / 4.751 |
| 433-interval0.1-4-glider | 2.085 / 2.370 / 2.540 | 0.623 / 0.752 / 1.040 | 3.157 / 3.773 / 4.057 | 3.688 / 4.126 / 4.802 |
| 433-interval0.1-5-freeflight | 6.215 / 6.678 / 34.548 | 3.698 / 4.180 / 4.918 | 4.376 / 5.082 / 6.420 | 3.170 / 3.821 / 4.468 |
| 433-interval0.1-6-glider | 2.079 / 2.393 / 2.739 | 0.649 / 0.789 / 0.938 | 3.283 / 3.643 / 3.922 | 3.744 / 4.130 / 4.542 |
| 433-interval0.1-7-freeflight | 6.147 / 6.610 / 33.813 | 3.685 / 4.231 / 4.775 | 4.267 / 5.188 / 6.413 | 3.086 / 3.547 / 3.888 |
| 433-interval0.1-8-candidate | 5.856 / 6.339 / 36.737 | 3.530 / 4.262 / 5.059 | 4.251 / 4.759 / 6.584 | 3.137 / 3.939 / 5.498 |
| 5845-interval0.1-0-freeflight | 11.163 / 11.481 / 29.218 | 8.208 / 8.646 / 26.901 | 7.701 / 8.239 / 16.257 | 15.453 / 17.628 / 52.995 |
| 5845-interval0.1-1-candidate | 9.629 / 10.029 / 19.212 | 6.419 / 6.888 / 64.103 | 6.256 / 6.844 / 17.357 | 14.078 / 16.059 / 21.213 |
| 5845-interval0.1-2-glider | 1.630 / 1.863 / 3.333 | 0.445 / 0.575 / 0.886 | 2.450 / 2.798 / 3.926 | 23.737 / 25.785 / 26.696 |
| 5845-interval0.1-3-candidate | 9.623 / 10.027 / 10.727 | 6.497 / 6.974 / 8.517 | 6.237 / 6.788 / 100.392 | 13.725 / 14.940 / 40.596 |
| 5845-interval0.1-4-glider | 1.591 / 1.780 / 2.162 | 0.435 / 0.554 / 0.646 | 2.353 / 2.857 / 3.477 | 23.431 / 25.342 / 29.938 |
| 5845-interval0.1-5-freeflight | 11.211 / 11.522 / 88.212 | 8.198 / 8.473 / 9.193 | 7.799 / 8.151 / 10.091 | 16.116 / 16.846 / 18.480 |
| 5845-interval0.1-6-glider | 1.632 / 1.858 / 3.262 | 0.455 / 0.556 / 0.705 | 2.537 / 2.929 / 3.599 | 23.910 / 26.080 / 27.241 |
| 5845-interval0.1-7-freeflight | 11.093 / 11.370 / 122.337 | 8.159 / 8.541 / 17.213 | 7.724 / 8.160 / 17.211 | 15.897 / 16.571 / 18.591 |
| 5845-interval0.1-8-candidate | 9.657 / 10.154 / 52.404 | 6.464 / 7.484 / 14.109 | 6.310 / 6.907 / 10.578 | 14.178 / 16.968 / 46.216 |

Repeat the native comparison against the already qualified frozen source:

```sh
DOTNET_CLI_USE_MSBUILD_SERVER=0 \
FREEFLIGHT_GLIDER_DOTNET_ROOT=/Users/jamie/Documents/Codex/2026-10-19/task/toolchains/dotnet \
FREEFLIGHT_GLIDER_CANDIDATE_RECEIPT="$PWD/bin/.local/benchmarks/trusted/expiry-inline-v2" \
FREEFLIGHT_GLIDER_LABEL=target-expiry-repeat \
FREEFLIGHT_GLIDER_SESSIONS=3 FREEFLIGHT_GLIDER_ROUNDS=50 \
FREEFLIGHT_GLIDER_WARMUP=10 FREEFLIGHT_GLIDER_INTERVALS=0,0.1 \
dockpipe --workflow benchmark.trusted.glider
```
