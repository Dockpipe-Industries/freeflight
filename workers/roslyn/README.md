# Internal Roslyn worker

This internal .NET 10 worker uses Microsoft.CodeAnalysis.CSharp.Workspaces 4.14.0
(MIT). Its pinned transitive dependencies are recorded in `packages.lock.json`.
The repository pins SDK 10.0.402 in `global.json`. The lockfile includes
osx-arm64, osx-x64, linux-x64, linux-arm64 and win-x64 restore graphs; this is not
evidence of execution on all five platforms.
It is owned and launched by the C++ server, not configured as a separate MCP endpoint.

Run `dockpipe --workflow workers.roslyn` to build with locked NuGet dependencies
and execute `test_worker.py`. Generated outputs stay in `bin/.local/roslyn`.
The workflow checks for `dotnet` and `python3` on PATH; the test also accepts an
explicit .NET executable path.
That Python file is a semantic test, not a development task runner; it takes the
`dotnet` executable and built worker DLL as arguments. Native fallback:
`dotnet build workers/roslyn/FreeFlight.Roslyn.csproj --artifacts-path bin/.local/roslyn`.
Production packaging must publish self-contained per-platform workers and include
their complete output. This source project alone is not a complete distribution.
The same semantic test can validate a self-contained publish without launching
`dotnet`: `python3 -B workers/roslyn/test_worker.py --native /absolute/path/FreeFlight.Roslyn`.

## Contract

UTF-8 newline-delimited JSON on stdin/stdout: `{id,method,params}` and
`{id,result}` or `{id,error:{message}}`. Positions are zero-based UTF-16.
Call `capabilities`, then `open` with an absolute authorized `root`.
Supported operations are `symbols`, `definition`, `references`, `hover`,
`diagnostics`, and `rename`. All take `file`; positional operations also take
`line` and `character`; rename takes `newName`. Locations contain an absolute
`file` and `{start,end}` range. Symbols include name, kind and display detail.
`cancel` with `{id}` cancels an outstanding request without a response;
`shutdown` or EOF cancels work and exits. Requests have a 60-second deadline.
The core must await workspace opening before sending dependent operations.

Rename always returns a preview. Each document contains structured edits and an
`expectedSha256` of the original file bytes. No file-writing operation exists.
The eventual caller applying a preview must revalidate root boundaries, compare
the hash, and apply the complete set atomically or abort on conflicts.

## Trust and correctness limits

`safe-source` mode builds one AdhocWorkspace project from C# source files and
references only the worker runtime's platform assemblies. It never evaluates
MSBuild, reads project imports, restores packages, loads repository assemblies,
or runs analyzers/generators. A request for another mode is rejected. There is
currently **no MSBuildWorkspace/full-solution mode**, even with trust opt-in.
MSBuild evaluation can execute project-supplied tasks; a future trusted mode needs
an explicit authorization and isolation contract before it can be implemented.

Results are semantic Roslyn results for this source view, not necessarily the
repository's real build. Multiple projects are combined; dependency assemblies,
project defines, generated code, language-version settings and implicit usings
are not inferred. Duplicate types or unresolved dependencies can produce extra
diagnostics. Analyzer diagnostics, code actions, import organization, workspace
symbols and hierarchies are not advertised. The parser uses C# 12.

Each request rescans the bounded workspace, reuses unchanged Roslyn documents,
and applies changed text incrementally. This detects added/deleted files but is
not a filesystem watcher. Limits are 10,000 C# files, 2 MiB per file, 64 MiB of
source, 100,000 directory entries, 1 MiB requests and 32 queued operations.
`.git`, `.hg`, `node_modules`, `bin`, `obj`, and `.freeflight` are excluded.
Symlink/reparse descendants are skipped and explicitly requested links rejected;
workspace root links are resolved once. This is path validation, not an OS
sandbox: an adversary concurrently replacing filesystem ancestors can race
portable checks. Run inside OS isolation for actively hostile repositories.

The controlled fixture verifies exact definition/reference positions, symbol
names, hover, clean and erroneous compiler diagnostics, incremental file updates,
rename edit count with unchanged source, traversal and symlink rejection, and
rejection of project-evaluation mode. The malicious project fixture is inert.
Protocol checks cover malformed JSON and non-object requests with recovery, and
cancellation during workspace loading followed by a successful new workspace.
Large real solution fidelity and performance remain release blockers.
