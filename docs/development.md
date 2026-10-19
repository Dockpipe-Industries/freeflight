# Local development operations

DockPipe owns repeatable operations; the underlying native toolchains remain usable.
Build with `dockpipe --workflow build`, test with `dockpipe --workflow test`, and
validate repository health with `dockpipe --workflow repo.check`.

## Starting a development server

Build the core and desired workers first. Author an absolute-path configuration
using the configuration examples in [the documentation](README.md). Set
`FREEFLIGHT_CONFIG` to that file, then run `dockpipe --workflow dev`.
The workflow starts the built core and preserves stdin/stdout/stderr. It does not
select a workspace or enable trusted MSBuild automatically. EOF shuts the server
down. DockPipe may print its own status messages: this is a development console
entry point, **not** an MCP client executable configuration.

For an MCP client, invoke the native executable directly:

```sh
bin/.local/build/freeflight --config /absolute/path/freeflight.json
```

Windows Release builds use `bin/.local/build/Release/freeflight.exe`. Native build
alternatives are `cmake -S . -B bin/.local/build -DCMAKE_BUILD_TYPE=Release`,
`cmake --build bin/.local/build --config Release`, and
`ctest --test-dir bin/.local/build -C Release --output-on-failure`.
Worker native commands are documented in their READMEs.

MSVC builds link the C++ core and process test executable to the static CRT
(`/MT`, or `/MTd` for Debug), using CMake policy CMP0091. This removes the core
executable's separate VC++ redistributable requirement; it does not change the
independently supplied Node or self-contained .NET worker runtimes. Windows
release qualification must still inspect the actual PE imports and exercise the
complete extracted bundle.

## Selected cleanup

Stop servers/builds using the selected output before cleanup. Set
`FREEFLIGHT_CLEAN_TARGET` to exactly one of `core`, `typescript`, or `roslyn` and
run `dockpipe --workflow clean`. The default mode previews the exact directory
without removing it. Review that output, then set `FREEFLIGHT_CLEAN_MODE=apply`
and invoke the same workflow to remove only the selected generated directory.
There is no `all` option and no arbitrary path argument.

| Generated location | Owner / cleanup policy |
| --- | --- |
| `bin/.local/build` | CMake core; target `core` |
| `bin/.local/typescript` | Staged worker and npm dependencies; target `typescript` |
| `bin/.local/roslyn` | .NET build/publish intermediates; target `roslyn` |
| `bin/.local/packages`, release/Registry receipts | Distribution evidence; excluded |
| `bin/.local/site*` | Site build, staged output, SDK/cache and browser evidence; excluded |
| `bin/.local/benchmarks`, real-project fixtures, other local files | Test evidence/developer state; excluded |
| `bin/.dockpipe` | DockPipe-owned state; excluded |

Symlinks/junctions in selected paths or their contents are rejected. Apply also
requires Python's descriptor-based, symlink-resistant recursive removal; runtimes
without that protection support preview only. This is an explicit limitation,
including Python/platform combinations on Windows where that API is unavailable.
Cleanup is not safe to run concurrently with a process replacing its ancestor
paths; do not mutate the selected output or generated root during cleanup.
No active output was deleted when qualifying this workflow.

`dockpipe --workflow development.test` verifies cleanup using disposable fixtures,
including exact selection, preview, external-link refusal and preservation of
unselected package receipts. Small Python assets exist only for cross-platform
executable selection and guarded deletion that native YAML commands cannot safely
express. They are invoked through DockPipe and do not introduce another task runner.
