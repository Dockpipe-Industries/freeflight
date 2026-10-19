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
