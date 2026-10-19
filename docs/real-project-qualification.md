# Real C# project qualification

Run `dockpipe --workflow integration.real` after `core.build` and `workers.roslyn`,
with the pinned .NET SDK available on PATH. This opt-in workflow exercises the C++
MCP endpoint and its explicitly trusted MSBuild worker against a disposable copy of
FreeFlight's own `FreeFlight.Roslyn.csproj`, lock file and C# sources. It restores
that known project with locked dependencies. Its temporary project and generated
MSBuild outputs remain under `bin/.local`; original source hashes must stay unchanged.
The temporary project is removed after success or failure.

The test verifies the exact `SemanticQueries` declaration range, all six references
from `Program.cs` and their ranges, and no errors or warnings in original source
files. It verifies the exact existing hidden `CS8019` unused-import diagnostic in
`TrustedProjectLoader.cs`. It injects an incompatible return expression only in the copy, requires one
`CS0029` at the exact expression location, then verifies diagnostics disappear after
restoring that source. MCP responses and process shutdown have bounded waits.

Successful runs write `bin/.local/reports/real-project.json`, containing original
source hashes, exact assertion descriptions and measured query durations. This is
one real project with NuGet dependencies, not qualification of large enterprise
solutions or a large-repository benchmark. MSBuild evaluation is explicitly trusted
and remains capable of executing project logic; the workflow accepts no arbitrary
user project path. SDK telemetry and development-certificate generation are disabled
in the test process before restore.

macOS ARM64 qualification passed on 2026-10-19 using .NET SDK 10.0.402 and the
compiled C++ MCP server. All exact assertions and graceful shutdown passed; the
three original C# source files and their project/lock files retained their hashes.
Full output is saved in `bin/.local/reports/real-project-run.log`.

Initial macOS execution restored the copied project but stopped at worker startup
with `worker pipe closed`; it did not pass semantic qualification. The SDK printed a
development-certificate initialization message before the explicit environment flags
were added. Read-only inspection found no matching localhost certificate in the
default login keychain; actual creation was not confirmed. No certificate trust or
cleanup command was run. Command and output excerpts are preserved in the generated
`bin/.local/reports/real-project-initial-run.txt` evidence file.
