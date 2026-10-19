# Verification policy

Test exact semantic ranges, identities, reference counts, diagnostics and edit text;
nonempty output is insufficient. Use controlled TS/JS/C# fixtures plus authorized
real repositories. Test changed files, multiple roots/configurations, Unicode
UTF-16 locations, path traversal/symlinks, malformed protocol, request bounds,
cancellation while busy, worker crash/restart and EOF cleanup. No source mutation
is permitted by preview operations. Edits carry original file hashes.

Run focused DockPipe tasks, then composed checks when changes warrant them. Native
tests are reusable test assets, not alternate task runners. Log platform/toolchain,
command, result and limitations. CI configuration is not a passing run. Benchmark
startup, RSS and query latency with fixed fixtures and honest exclusions; never
claim large-repo performance from tiny fixtures. Do not disturb Nucleon benchmarks.
