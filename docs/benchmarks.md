# Reproducible MCP benchmarks

Run `dockpipe --workflow build` and then `dockpipe --workflow benchmark` from the repository root with the pinned Node and .NET toolchains available. The benchmark owns no build logic and performs no dependency downloads. Its workflow-local Python asset is required to generate controlled fixtures, time JSON-RPC requests, sample process-tree memory, and assert results; it is not a second task runner.

Generated sources, configuration, and stderr logs are retained under a unique `bin/.local/benchmarks/run-*` directory. Only that directory is created; existing runs or developer files are never deleted. The structured receipt is `bin/.local/reports/benchmark.json`, including a success/failure status and fixture hashes. Subsequent runs replace the receipt but retain fixture directories. Nothing generated belongs in tracked source.

The two fixed workloads use seed 481516:

| Workload | TypeScript | JavaScript | C# | Total source files |
| --- | ---: | ---: | ---: | ---: |
| Medium | 100 | 100 | 100 | 300 |
| Large synthetic | 1,000 | 1,000 | 1,000 | 3,000 |

Each small file contains a named function or class and a reference to it. TypeScript and JavaScript share one configured TypeScript project; C# uses the safe-source Roslyn engine. This is a mixed-language indexing workload, not a realistic large solution, dependency graph, or project-reference monorepo.

The actual C++ executable is launched once per workload. Startup measures process creation through MCP discovery, excluding lazy workers. First diagnostics are measured separately and include lazy initialization where applicable. Five subsequent sequential samples measure diagnostics, document symbols, and references for each language; the receipt includes raw samples, median, minimum, and maximum. Semantic assertions require no fixture diagnostics, expected named symbols, and exact reference counts (two TS/JS references including declaration; one C# usage). All timings include MCP serialization, C++ routing, IPC, filesystem refresh, and engine analysis. They do not isolate C++ overhead.

On macOS and Linux, a background sampler invokes `ps` approximately every 100 ms and records peak RSS for the C++ core and the sum of its process tree. Shared pages may be counted more than once, short peaks may be missed, and the sampler adds overhead. Windows results explicitly mark RSS unavailable; they must not report it as zero.

A separate local-source qualification opens FreeFlight's own worker source through the same C++ endpoint and verifies that the test's `Worker` constructor resolves to the exact class declaration in `worker.mjs`, and that document symbols include the class. This uses the inferred JavaScript project; it does not claim a full repository typecheck, an external real-repository test, or real large-repository performance. The source hash identifies the qualified version.

These measurements are evidence, not a release performance budget. Cross-platform results, realistic dependency-heavy repositories, trusted MSBuild solutions, concurrency, cache eviction, and sustained memory growth remain separate qualification work.

## Recorded macOS ARM64 run

On 2026-10-19, DockPipe 0.6.20 completed both workloads and own-source qualification on macOS 27.0.1 ARM64, Node 24.11.1, .NET SDK 10.0.402 and Python 3.9.6. The core binary SHA-256 was `016fae10621dbdf8714340a3a38a821a97bfb828c3fc160e9a9f6d44c7470a35`. These measurements describe that local binary, not an independently reproduced release artifact.

Warm round-trip medians in milliseconds (five samples each):

| Workload | Language | Diagnostics | Symbols | References |
| --- | --- | ---: | ---: | ---: |
| 300 files | TypeScript | 27.815 | 16.283 | 30.600 |
| 300 files | JavaScript | 26.679 | 12.244 | 26.440 |
| 300 files | C# | 2.254 | 2.150 | 2.632 |
| 3,000 files | TypeScript | 131.458 | 71.652 | 128.275 |
| 3,000 files | JavaScript | 125.341 | 70.162 | 123.801 |
| 3,000 files | C# | 21.627 | 21.479 | 29.430 |

The latest discovery startup samples were 112.651 ms (medium) and 2.413 ms (large); a preceding run recorded 2.039 and 2.315 ms. This variability and the single startup sample per workload are insufficient for a startup percentile claim. First diagnostics in the latest large workload took 426.491 ms for TypeScript and 599.906 ms for C#, including lazy engine initialization. JavaScript shares the already-started TypeScript engine.

Peak sampled core/tree RSS was 2,816/635,552 KiB for medium and 2,848/626,368 KiB for large. These sampled totals are not guaranteed peak private memory; the lower large-fixture total must not be interpreted as a scaling improvement.

Both executed runs generated identical fixture hashes: medium `74838222c628272f29d67a51d6a64cc4f85dc3755107c1230f8fd1a6fe35edc4`, large `98d24f11e2b06ef71aad496ab185ed99dfea411ca04b06998b6c5920593a8a29`. The large fixture contains only 343,714 bytes including configuration despite its file count. Own-source constructor navigation and class symbols passed; the measured definition and symbols requests took 251.313 and 219.760 ms respectively. No full own-source diagnostics claim is made.

## Preview comparison: 2026-10-20

Compared baseline `ba0c4ce6e7f6294419aeffb4bf0893c20c7f8495` with candidate runtime `986b60b6f6261befaddad885957ca7613cc8ad16` on one Apple M6 Mac with 24 GiB RAM, macOS 27.0.1, Node 24.22.0, .NET SDK 10.0.402/runtime 10.0.13, CMake 3.31.8 and Python 3.9.6. Both used Release C++ and Debug Roslyn builds. The baseline is a macOS rebuild of the published preview source, not its Linux release executable; all 192 baseline tracked files were verified against their Git blob hashes.

Use the existing `benchmark` workflow with `FREEFLIGHT_BENCHMARK_BASELINE` set to the absolute baseline build directory (see workflows/README.md). Runs were serial, with two fresh sessions per version and language on the compatible fixture, reversing version order on the second pass. Both versions used identical fixture roots, explicit worker configuration and their default resource policy. The fixtures contain 100 real declarations per generated file plus comment padding: these are controlled byte-heavy workloads, not representative real solutions.

All 12 compatible runs passed exact symbol, definition-coordinate, reference-location, diagnostic and changed-file/restore checks. Warm round-trip medians below pool ten observations per cell; changed-file medians use two observations. Units are milliseconds.

| Language | Operation | Preview | Candidate |
| --- | --- | ---: | ---: |
| csharp | diagnostics.warm | 27.220 | 0.357 |
| csharp | symbols.warm | 24.927 | 0.361 |
| csharp | definition.warm | 24.837 | 0.344 |
| csharp | references.warm | 35.185 | 0.542 |
| csharp | changed-file.diagnostics | 62.092 | 27.440 |
| typescript | diagnostics.warm | 49.169 | 5.297 |
| typescript | symbols.warm | 17.312 | 2.736 |
| typescript | definition.warm | 32.678 | 3.939 |
| typescript | references.warm | 48.410 | 5.229 |
| typescript | changed-file.diagnostics | 76.611 | 14.561 |
| javascript | diagnostics.warm | 49.019 | 5.417 |
| javascript | symbols.warm | 17.552 | 2.764 |
| javascript | definition.warm | 32.795 | 3.904 |
| javascript | references.warm | 48.649 | 5.185 |
| javascript | changed-file.diagnostics | 77.288 | 14.353 |

The compatible workload contains 24 one-MiB generated files plus a small target. Startup discovery across these sessions ranged from 2.33–5.37 ms for the preview and 4.39–6.29 ms for the candidate. Root registration took 0.13–0.23 ms; source loading happens at first diagnostics. C# first diagnostics were 424–438 ms versus 448–455 ms; TS 312–318 versus 310–311 ms; JS 315–319 versus 311–318 ms. These small samples do not establish a startup improvement; the C# cold path was slightly slower.

| Language | Preview peak tree RSS MiB (two runs) | Candidate peak tree RSS MiB | Preview steady tree RSS MiB | Candidate steady tree RSS MiB |
| --- | --- | --- | --- | --- |
| csharp | 462.0, 445.3 | 341.5, 341.5 | 401.5, 398.5 | 341.5, 341.5 |
| typescript | 352.2, 335.3 | 355.8, 355.7 | 333.1, 315.2 | 355.8, 355.7 |
| javascript | 344.7, 347.4 | 340.0, 342.7 | 318.3, 331.1 | 340.0, 342.7 |

RSS is sampled about every 100 ms and sums core/worker resident pages, potentially double-counting shared pages or missing peaks. Steady RSS is a 600 ms post-query window. C# memory fell in this fixture; retained TypeScript snapshots trade memory for faster queries, so this is not a universal memory reduction.

All six candidate stress runs passed exact semantic and edit-refresh assertions. The preview failed C# at a nine-MiB source file (old two-MiB limit) and at 72 one-MiB files (old aggregate limit). Its TS/JS nine-MiB source was omitted, producing incorrect missing-module/declaration diagnostics; those are recorded failures, not usable latency measurements. Preview TS/JS did pass the 72-MiB aggregate case. Their warm reference medians fell from 116.790/117.055 ms to 8.654/8.714 ms, while sampled peak RSS rose from 474.4/466.1 MiB to 529.8/518.9 MiB.

The candidate defaults remain bounded: 32 MiB per file, 512 MiB workspace bytes, 50,000 files and 500,000 directory entries. Higher operator-configured limits are validated. TS project references remain explicitly unsupported; C# safe-source analysis is not a full MSBuild solution. No competitor, trusted-project, concurrency or long-duration memory claim follows from this comparison.

Raw observations, configurations, fixture hashes, source/binary hashes, stderr and RSS samples were retained locally under `bin/.local/benchmarks/comparison-zpwg47l6/`; report SHA-256: `4cf71519b1c38ee92e7b4bf36bff1b371784e0bc602cdcd6e2ce7ecd3c1db07d`. The initial hardware-probe setup failure is retained in `bin/.local/before-after-benchmark-setup-failure.log`; no semantic measurements ran in that failed attempt. Generated evidence stays untracked.
