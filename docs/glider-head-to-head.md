# Same-machine Glider comparison

This workflow compares the published FreeFlight source `97c1342d9234f9d2146cd209760d6af1ea125b6e`
with official Glider 13.3.0 on the operator's Darwin ARM64 machine. It is a synthetic
comparison, not a rerun of the Linux/Biztraak report. No active MCP configuration,
runtime implementation, remote branch, release or deployment is changed.

## Reproducible workflow

`benchmark.trusted.glider` reuses the `benchmark` MCP client and
`benchmark.trusted` fixture oracle/statistics. It requires an existing trusted
fixture provenance receipt, the published native FreeFlight bundle and manifest,
and an isolated official Glider 13.3.0 installation. Local preparation is recorded
under `bin/.local/glider-comparison`; generated packages/receipts are not committed.

The package is available from [official NuGet](https://www.nuget.org/packages/glider/13.3.0).
Install to a disposable directory using `dotnet tool install glider --version 13.3.0
--tool-path <directory>` with the official NuGet source. Do not update a global
installation or active MCP connection. Record the actual `.nupkg` archive hash,
not NuGet's metadata content hash: signed archive bytes can have a different hash.
The local archive was compared with a fresh download from the official flat-container
URL. The packaged license permits evaluation; no activation/login was performed.

Use the published macOS ARM64 bundle and verify it against the release SHA256SUMS.
The bundle's own SHA256SUMS is checked again by the workflow. Place a `global.json`
pinning SDK 10.0.402 in its disposable parent directory, outside the verified bundle,
so MSBuild discovery does not inherit the FreeFlight implementation repository's
SDK 11 pin. Both products use SDK 10.0.402. FreeFlight retains its shipped bundled
runtime; Glider uses the installed .NET 10.0.13 runtime. No binary is rebuilt or
patched for the comparison.

Example on this M6, with a fresh immutable label:

```sh
FREEFLIGHT_GLIDER_DOTNET_ROOT=/Users/jamie/Documents/Codex/2026-10-19/task/toolchains/dotnet \
FREEFLIGHT_GLIDER_LABEL=head-to-head-repeat \
FREEFLIGHT_GLIDER_SESSIONS=3 \
FREEFLIGHT_GLIDER_ROUNDS=100 \
FREEFLIGHT_GLIDER_WARMUP=10 \
FREEFLIGHT_GLIDER_INTERVALS=0,0.1 \
dockpipe --workflow benchmark.trusted.glider
```

Optional paths: `FREEFLIGHT_GLIDER_COMMAND`, `FREEFLIGHT_GLIDER_FREEFLIGHT_BUNDLE`,
`FREEFLIGHT_GLIDER_FIXTURE_PROVENANCE`, and `FREEFLIGHT_GLIDER_RELEASE_MANIFEST`.
`FREEFLIGHT_GLIDER_SIZES` defaults to `433,5845`. The source fixture receipt defaults
to the previous `sprint-winner-shipped` run. Python and the existing workflow
requirements must be on PATH. New labels fail if already present; no receipts are
overwritten. Preparation and failed smoke probes remain separate from final runs.

## Fixture and protocol equivalence

Both tools load the identical conventional `.sln`: 433 sources/two projects and
5,845 sources/26 projects, 4 KiB per C# file, 14 cross-project calls, and broad C5
search returning 11/956 classes. Every original C# source byte and project reference
is preserved. Project target frameworks change from the earlier `net11.0` fixture
to `net10.0`; shared SDK selection and solution files are explicitly hashed.

The first Glider net11 probe loaded the expected counts but lacked framework
references and failed semantic resolution. It was rejected, not timed as a valid
comparison. FreeFlight rejected `.slnx` startup configuration, so both use `.sln`.
Initial SDK-selection and response-adapter failures are retained in probe/smoke
logs and excluded from the final comparison.

Both endpoints use MCP 2026-07-28 discovery and stdio. Startup/discovery, solution
load, Glider background compilation, query warmup, measured queries and post-idle
requests are separate receipts. FreeFlight awaits compilation inside load and does
not expose a separate background duration. Glider status is polled until warmup
completes; project/document counts and compiler diagnostics must pass first.

Fresh processes alternate FreeFlight/Glider, then Glider/FreeFlight, then
FreeFlight/Glider. There are no concurrent timing processes. Unpaced and minimum
100 ms four-operation-round cadence run in separate fresh processes. Validation,
result hashing and pacing are outside each request timer. Client JSON parsing is
included. Neither instrumented binaries nor RSS process sampling are used.

Every response is validated against the fixture, not merely a candidate count:

- FreeFlight's existing oracle checks exact names, kinds, file paths and all
  start/end ranges for outline, definition, references and broad search.
- Glider outline declaration ranges are checked exactly, including namespace,
  type and method. Its full declaration ranges differ from FreeFlight name spans.
- Every Glider search key is resolved through `get_source` before timing and checked
  against exact source bytes and declaration spans. Timed results must match the
  complete validated name/key/path/line/kind set with complete coverage and no paging.
- Glider's cross-project definition key is resolved to the exact target declaration
  before timing. Each timed lookup must return that key, path, line and kind.
- All 14 Glider reference file/line/start-column coordinates and invocation kinds
  are checked against the immutable source. Reference ends are absent from this
  API and are not presented as returned data.

Glider search/definition replies omit columns that FreeFlight returns. Reference
keys are discovered before timing because Glider requires opaque keys; FreeFlight
accepts a source position. These payload/interaction differences remain limitations
of an operation-level comparison, not hidden normalization. Glider response size is
bounded at 2,000,000 characters so broad results are not silently truncated.

## Freshness and interpretation

FreeFlight still validates every source leaf each semantic request, freshly reads
targets, and periodically revalidates snapshots. Glider's documented outline uses
the workspace snapshot and its default watcher auto-sync; pending edits can require
`sync`. The benchmark does not disable either tool's normal freshness behavior or
claim equivalent path-security contracts. Both use unchanged synthetic files.
Glider telemetry and new local error journaling are disabled per process only.

A 5.1-second idle interval is applied to both. It exercises FreeFlight's known
expiry behavior; it is not evidence that Glider implements the same expiry policy.
The following definition/reference/search requests see the outline's refreshed
state, rather than four independent expiry trials. All outliers and maxima remain
in raw samples and per-session summaries. No hard statistical win threshold is used.

## Completed M6 result — 2026-10-21

Official Glider 13.3.0 versus the published FreeFlight `97c1342d9234` bundle:
24 fresh processes, three sessions per product/graph/cadence, 100 measured rounds
per session after at least ten seconds of warmup. All 9,600 measured responses
passed the semantic oracle; warmup and all 96 post-idle responses also passed.
Both tools loaded 2/26 projects and 433/5,845 documents respectively. No runtime
optimization was made during this comparison.

Glider wins outline, definition and reference latency in every tested session.
Broad search changes with cadence: Glider is faster unpaced, while FreeFlight is
faster in all three paced full-graph sessions. This is an observed reversal, not
a diagnosed scheduler/GC effect. No profiling was mixed into these measurements.
Three sessions are bounded evidence, not statistical qualification across machines.

### Unpaced

Cells show median of the three session medians / median of session p90s /
maximum across all three sessions, in milliseconds. These are not pooled percentiles.

| Files | Operation | FreeFlight | Glider |
| --- | --- | --- | --- |
| 433 | Outline | 0.560 / 0.572 / 0.652 | 0.134 / 0.202 / 0.222 |
| 433 | Definition | 0.539 / 0.550 / 0.860 | 0.056 / 0.125 / 0.137 |
| 433 | References | 0.914 / 0.964 / 3.323 | 0.463 / 0.538 / 3.013 |
| 433 | Broad search | 0.638 / 0.653 / 0.888 | 0.438 / 0.467 / 1.416 |
| 5845 | Outline | 6.864 / 7.792 / 11.497 | 0.167 / 0.221 / 3.059 |
| 5845 | Definition | 5.975 / 6.354 / 10.344 | 0.066 / 0.092 / 0.218 |
| 5845 | References | 6.377 / 6.657 / 11.008 | 0.572 / 0.689 / 1.831 |
| 5845 | Broad search | 14.215 / 15.355 / 17.920 | 7.042 / 7.966 / 19.360 |

### Paced: minimum 100 ms per four-operation round

Cells show median of the three session medians / median of session p90s /
maximum across all three sessions, in milliseconds. These are not pooled percentiles.

| Files | Operation | FreeFlight | Glider |
| --- | --- | --- | --- |
| 433 | Outline | 4.015 / 4.445 / 35.183 | 1.119 / 1.245 / 2.117 |
| 433 | Definition | 3.169 / 3.485 / 4.834 | 0.402 / 0.454 / 0.693 |
| 433 | References | 3.755 / 4.574 / 6.165 | 2.400 / 2.565 / 4.100 |
| 433 | Broad search | 2.838 / 2.985 / 4.362 | 2.955 / 3.295 / 3.767 |
| 5845 | Outline | 9.941 / 10.675 / 139.035 | 1.495 / 1.669 / 4.607 |
| 5845 | Definition | 7.567 / 7.876 / 88.334 | 0.442 / 0.496 / 0.589 |
| 5845 | References | 7.151 / 7.620 / 26.654 | 2.760 / 3.013 / 3.607 |
| 5845 | Broad search | 14.195 / 15.165 / 24.154 | 28.113 / 29.204 / 32.337 |

### Load and post-idle

Startup/discovery and load medians below use six fresh sessions per graph/product.
FreeFlight load includes awaited compilation. Glider background duration is its
reported compilation duration; polling wait is separately retained in raw receipts.

| Files | Product | Startup/discovery ms | Load ms | Background compilation ms |
| --- | --- | --- | --- | --- |
| 433 | freeflight | 2.87 | 719.40 | Included in load |
| 433 | glider | 125.86 | 614.95 | 273.00 |
| 5845 | freeflight | 3.10 | 2940.68 | Included in load |
| 5845 | glider | 126.62 | 1914.93 | 491.50 |

First outline after 5.1 seconds idle (six samples/product/graph; median / min / max ms):

| Files | Product | Post-idle outline |
| --- | --- | --- |
| 433 | freeflight | 36.518 / 35.811 / 37.078 |
| 433 | glider | 2.187 / 2.111 / 2.220 |
| 5845 | freeflight | 186.679 / 166.797 / 194.448 |
| 5845 | glider | 2.256 / 2.022 / 6.207 |

FreeFlight paced full-graph outline maxima reach 139.035 ms; definition reaches
88.334 ms. Those samples remain included. Post-idle delays are consistent with
additional refresh work, but this uninstrumented comparison does not attribute
individual tail samples to expiry, GC or scheduling. Watcher generations and
Glider readiness/final status are retained; no watcher authority was substituted
for FreeFlight validation. Mutation/security behavior is not newly qualified by
unchanged-file benchmarking; the shipped qualification remains the relevant evidence.

### All measured sessions

Each cell is median / p90 / max in ms; session order matches the receipts.

| Session | Outline | Definition | References | Broad search |
| --- | --- | --- | --- | --- |
| 433-interval0-0-freeflight | 0.557 / 0.563 / 0.570 | 0.532 / 0.538 / 0.584 | 0.914 / 0.944 / 1.308 | 0.633 / 0.644 / 0.888 |
| 433-interval0-1-glider | 0.127 / 0.188 / 0.215 | 0.056 / 0.125 / 0.133 | 0.453 / 0.505 / 2.268 | 0.432 / 0.458 / 0.665 |
| 433-interval0-2-glider | 0.186 / 0.202 / 0.222 | 0.055 / 0.122 / 0.137 | 0.471 / 0.569 / 3.013 | 0.441 / 0.499 / 1.416 |
| 433-interval0-3-freeflight | 0.560 / 0.572 / 0.627 | 0.539 / 0.550 / 0.860 | 0.912 / 0.964 / 2.124 | 0.638 / 0.653 / 0.729 |
| 433-interval0-4-freeflight | 0.570 / 0.614 / 0.652 | 0.545 / 0.591 / 0.859 | 0.928 / 0.986 / 3.323 | 0.642 / 0.657 / 0.741 |
| 433-interval0-5-glider | 0.134 / 0.202 / 0.210 | 0.056 / 0.125 / 0.130 | 0.463 / 0.538 / 1.800 | 0.438 / 0.467 / 0.487 |
| 5845-interval0-0-freeflight | 6.889 / 7.830 / 10.246 | 5.975 / 6.425 / 10.344 | 6.331 / 6.860 / 10.009 | 13.933 / 15.459 / 17.920 |
| 5845-interval0-1-glider | 0.167 / 0.214 / 0.284 | 0.065 / 0.080 / 0.116 | 0.572 / 0.689 / 1.831 | 7.120 / 7.966 / 19.113 |
| 5845-interval0-2-glider | 0.171 / 0.221 / 0.362 | 0.069 / 0.093 / 0.118 | 0.575 / 0.704 / 0.848 | 7.042 / 8.156 / 19.360 |
| 5845-interval0-3-freeflight | 6.864 / 7.792 / 11.497 | 5.989 / 6.354 / 10.259 | 6.377 / 6.657 / 11.008 | 14.215 / 15.355 / 17.655 |
| 5845-interval0-4-freeflight | 6.816 / 7.249 / 8.620 | 5.954 / 6.103 / 7.316 | 6.388 / 6.646 / 7.509 | 14.217 / 14.872 / 16.481 |
| 5845-interval0-5-glider | 0.167 / 0.221 / 3.059 | 0.066 / 0.092 / 0.218 | 0.566 / 0.656 / 1.794 | 7.041 / 7.945 / 18.050 |
| 433-interval0.1-0-freeflight | 4.040 / 4.445 / 35.101 | 3.183 / 3.485 / 3.842 | 3.737 / 4.606 / 6.165 | 2.838 / 2.985 / 4.362 |
| 433-interval0.1-1-glider | 1.135 / 1.346 / 2.117 | 0.399 / 0.454 / 0.693 | 2.400 / 2.607 / 4.100 | 3.069 / 3.477 / 3.767 |
| 433-interval0.1-2-glider | 1.119 / 1.245 / 1.808 | 0.404 / 0.455 / 0.637 | 2.423 / 2.564 / 2.849 | 2.955 / 3.277 / 3.702 |
| 433-interval0.1-3-freeflight | 4.007 / 4.319 / 34.930 | 3.169 / 3.568 / 4.834 | 3.755 / 4.487 / 6.086 | 2.843 / 2.988 / 4.291 |
| 433-interval0.1-4-freeflight | 4.015 / 4.488 / 35.183 | 3.160 / 3.477 / 4.793 | 3.765 / 4.574 / 6.093 | 2.831 / 2.979 / 3.221 |
| 433-interval0.1-5-glider | 1.111 / 1.232 / 1.996 | 0.402 / 0.439 / 0.612 | 2.397 / 2.565 / 3.178 | 2.925 / 3.295 / 3.614 |
| 5845-interval0.1-0-freeflight | 9.941 / 10.675 / 116.766 | 7.567 / 7.804 / 88.334 | 7.173 / 7.557 / 8.435 | 14.195 / 14.857 / 16.766 |
| 5845-interval0.1-1-glider | 1.478 / 1.604 / 1.815 | 0.442 / 0.497 / 0.536 | 2.752 / 2.999 / 3.383 | 28.550 / 29.856 / 31.799 |
| 5845-interval0.1-2-glider | 1.495 / 1.669 / 3.744 | 0.445 / 0.496 / 0.589 | 2.760 / 3.013 / 3.607 | 28.113 / 29.191 / 31.505 |
| 5845-interval0.1-3-freeflight | 9.879 / 10.571 / 113.587 | 7.468 / 7.876 / 67.344 | 7.121 / 7.620 / 26.654 | 14.128 / 15.165 / 24.154 |
| 5845-interval0.1-4-freeflight | 10.052 / 10.866 / 139.035 | 7.583 / 7.935 / 8.777 | 7.151 / 7.654 / 8.958 | 14.355 / 15.303 / 17.914 |
| 5845-interval0.1-5-glider | 1.506 / 1.681 / 4.607 | 0.436 / 0.495 / 0.573 | 2.777 / 3.035 / 3.326 | 28.037 / 29.204 / 32.337 |

### Receipts and identity

Local receipts: `bin/.local/glider-comparison/head-to-head-1/` contains
`provenance.json`, `samples.json`, `summary.json`, frozen `driver-source/`, and
per-process discovery/load/readiness/validated-result/stderr/status files.
The full DockPipe log is `bin/.local/glider-head-to-head-1.log`.
Earlier failed probes and smoke runs remain alongside the final run; none are pooled.

Fixture aggregate SHA256 (all source/project/solution/SDK-pin inputs):

- 433 files: `a4fd64fe569183e649aa78ea4aca574131127e11cc7b5c2b18708697875a1b7b`.
- 5,845 files: `4d509fb473bbe9a8527d719f2339d86b3b2322490ed85333979588396063793e`.

Published archive SHA256:
`6e862340f2f08b1f028504ad2ca47d99c07cbf5efa9e8b6d13c2ea222215b3db`.
Official Glider archive byte verification is recorded separately in
`bin/.local/glider-comparison/official-package-verification.json`.
No Linux receipts were accessed, and these synthetic results cannot be presented
as a Biztraak rerun. No active MCP configuration or remote state changed.


## Local candidate comparison

After a completed `benchmark.trusted` receipt, set
`FREEFLIGHT_GLIDER_CANDIDATE_RECEIPT` to its absolute directory to add a third
product. The workflow verifies frozen candidate source hashes and passing semantic
and transaction receipts, publishes that worker locally as self-contained macOS
ARM64 using the recorded SDK, then runs both existing native worker suites before
timing. The core remains the verified published FreeFlight core. All native files
and qualification receipts are hashed in provenance. This is local preparation,
not release publication. Active configuration is never edited.

Three-product sessions rotate order to balance positions: shipped/candidate/Glider,
candidate/Glider/shipped, Glider/shipped/candidate. All use the same .NET 10 fixture
and readiness/oracle requirements. Results retain comparisons of candidate to both
shipped FreeFlight and Glider. Native candidate preparation currently targets macOS
ARM64; do not treat this local adapter as portable platform qualification.
