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
The worker opens its pipe streams explicitly as strict UTF-8, independently of
Windows console code pages, and never emits a BOM. Malformed or truncated UTF-8
returns `Invalid UTF-8 input` with a null ID and closes the worker stream safely;
ordinary malformed JSON retains the existing recoverable error behavior.
Tests send unescaped UTF-8 Greek/Japanese filenames and symbols, verify exact
definition positions after a supplementary-plane character, and reject invalid bytes.
Call `capabilities`, then `open` with an absolute authorized `root`.
Supported operations are `symbols`, `definition`, `references`, `hover`,
`diagnostics`, `rename`, `implementations`, `typeInfo`, `signatureHelp`,
`workspaceSymbols`, `callHierarchy`, and `typeHierarchy`. All except
`workspaceSymbols` take `file`; positional operations also take
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
or runs analyzers/generators. A request for another mode is rejected. The default worker rejects attempts to change mode through an `open` request.

Safe-source results are semantic Roslyn results for this source view, not necessarily the
repository's real build. Multiple projects are combined; dependency assemblies,
project defines, generated code, language-version settings and implicit usings
are not inferred. Duplicate types or unresolved dependencies can produce extra
diagnostics. Analyzer diagnostics, code actions and import organization are not advertised.
The safe-source parser uses C# 12.

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

## Explicitly trusted project mode

The operator can add `--trusted-msbuild` to the configured absolute worker argv.
This is startup authorization for every root that worker opens. No request can
turn it on or switch modes; normal bundled `--workspace` startup remains safe-source.
Capabilities report `fidelity` and `mode` as `safe-source` or `trusted-msbuild`.
A warning is written to stderr at trusted startup.

**MSBuildWorkspace runs design-time project evaluation, which can execute arbitrary
repository code, custom targets, SDK resolvers, and imports. This is not a sandbox.**
Root checks constrain the returned project/document graph, not MSBuild's execution:
external imports and referenced projects can already have been evaluated before a
path is rejected. Only opt in for repositories and SDKs the operator trusts, under
appropriately limited OS permissions and environment. Do not expose this mode to
untrusted remote users. A 60-second request cancellation is best effort for the
MSBuild host; process supervision remains the final timeout boundary.

Trusted mode uses Microsoft.CodeAnalysis.Workspaces.MSBuild 4.14.0 and
Microsoft.Build.Locator 1.7.8. MSBuild references are pinned to 17.14.28 with runtime
assets excluded; Locator selects the operator's installed SDK. Explicit crypto
10.0.13 pins replace vulnerable transitive versions. NuGet vulnerability warnings
remain errors. The trusted mode requires a compatible .NET SDK and the repository's
necessary targeting packs/workloads. The standalone bundle remains SDK-free for
safe-source mode; it does not contain a complete SDK for trusted evaluation.

`open` accepts an optional root-relative `project` ending in `.csproj` or `.sln`.
Without it, the root must contain exactly one solution, or exactly one C# project.
The worker never requests restore or a production build. Restore dependencies
explicitly before opening. Design-time settings disable compiler/analyzer execution
and NET analyzers; all analyzer/generator references are removed before semantic
compilation, and validated options, references and source documents are copied into
AdhocWorkspace. Preview refactorings never use MSBuildWorkspace.TryApplyChanges.

Project and document paths must remain under the authorized root and cannot traverse
symlinks. Limits also include 256 projects. Unsupported/missing files fail loading;
linked documents shared between projects currently fail rather than picking a
project silently. Multi-targeted projects, generated sources, arbitrary custom SDKs,
VB projects and large real solutions are not qualified. Content edits refresh;
changes to project configuration or the project graph require reopening. No analyzer
diagnostics or source-generator output are provided.

`dockpipe --workflow workers.roslyn` runs both suites. The trusted test creates and
explicitly restores a locally authored pair of dependency-free SDK projects under
`bin/.local`, then checks a conditional project define, exact cross-project definition
and reference locations, clean diagnostics, changed-file type errors, and root/mode
rejections. This verifies a small SDK project graph, not universal solution fidelity.

## Additional semantic queries

- `workspaceSymbols` takes `query` (1–256 characters) and performs a case-insensitive
  substring search over Roslyn source declarations. Results have name, kind,
  display and source locations. Queries exceeding 1,000 symbols return an error;
  no incomplete result is silently returned.
- `implementations` uses Roslyn implementation, override and derived-class APIs.
  Interface member results include overrides of the implementing member.
- `typeInfo` returns the semantic type, converted type when available, nullable
  annotation and fully qualified type. Literal and declaration positions work;
  positions remain UTF-16, including after supplementary Unicode characters.
- `signatureHelp` supports ordinary invocation expressions. It returns overloads,
  Roslyn's selected overload, parameter names/types/optionality and the syntactic
  argument index/count. Constructors, indexers and attribute signatures are not
  implemented; their empty result must not be interpreted as absence of overloads.
- `typeHierarchy` returns immediate class/interface supertypes and immediate source
  subtypes, with symbol details and source locations. Metadata parents can have no
  source locations. Structs, enums and other symbol kinds return an empty result.
- `callHierarchy` applies to method symbols, with incoming callers from Roslyn and
  outgoing statically bound invocations and object construction from Roslyn's
  operation tree. Incoming edges retain `isDirect`; related-symbol/override callers
  are marked false and are not proof of runtime dispatch. Outgoing edges do not
  include implicit property/event access, operators, dynamic dispatch or reflection.
  Nested lambda/local-function bodies belong to separate callers. One response has
  at most 500 incoming edges/locations and 500 outgoing edges; excess returns an
  error. This is static semantic navigation, not a whole-program runtime call graph.

The extended fixture verifies interface implementations plus override positions,
integer versus string overload selection, active argument index, exact workspace
symbol location, direct type relationships, direct and indirect incoming calls,
constructor/method outgoing calls, nested callable ownership, UTF-16 positions,
and symbol/edge limits with recovery. The shared per-request cancellation token
flows into Roslyn query APIs and operation traversal. These queries use the selected
safe-source or trusted project model and inherit its fidelity limitations.

## Provisional Windows .NET Framework qualification

The intended legacy C# support floor is .NET Framework 4.7, through 4.8.1.
This remains provisional until Windows CI supplies passing semantic evidence.
`dockpipe --workflow legacy.dotnet` tests 4.7, 4.8 and 4.8.1 separately using
one controlled two-project non-SDK solution. The source fixture targets 4.8;
each test changes only its disposable copy beneath `bin/.local` to its selected
framework. No developer project is changed. The workflow fails on non-Windows
hosts or missing targeting packs instead of recording a skipped test as success.

Prerequisites are built C++/Roslyn outputs (`core.build`, `workers.roslyn`), the
pinned .NET SDK on PATH, and each selected .NET Framework developer/targeting
pack under the standard Windows Reference Assemblies location. A runtime alone
is insufficient. The worker uses the SDK MSBuild selected by Microsoft.Build.Locator;
this test deliberately determines whether that toolset can load these simple
non-SDK projects. Visual Studio-only project types/tasks are not qualified.
No dependency restore or build occurs for this package-free fixture.

The test uses the actual C++ MCP endpoint and explicitly configured
`--trusted-msbuild` worker. It checks project-defined conditional compilation,
System.Xml.Linq framework-reference resolution, exact cross-project definition
and reference positions, clean diagnostics, and an exact introduced CS0029 that
then clears on edit. Passing those cases would qualify these controlled project
shapes only: packages.config, custom targets, web applications, COM, VB, and large
legacy solutions still require separate evidence. Intermediate versions 4.7.1
and 4.7.2 are not directly tested by this representative matrix. MSBuild evaluation
can execute repository code; explicit trust is mandatory and this is not a sandbox.

The coordinated dependency update pins both Roslyn workspace packages to 5.9.0
and MSBuild.Locator to 1.11.2. Microsoft.NET.StringTools 17.14.28 is explicitly
excluded from runtime assets and private to the worker project to honor Locator's
assembly-loading guard. Do not suppress that guard or mix Roslyn workspace versions.
All changed package metadata declares MIT; preserve distribution notices.

Each passing legacy receipt records the worker's actual .NET runtime, Locator
instance/discovery type, selected MSBuild assembly file version and location,
plus hashes of the selected targeting pack's mscorlib, System.Xml.Linq and
FrameworkList.xml. These distinguish selected tooling from the target framework.
Microsoft documents that [.NET Locator discovers SDK MSBuild, not Visual Studio
MSBuild](https://learn.microsoft.com/en-us/visualstudio/msbuild/find-and-use-msbuild-versions?view=vs-2022).
The [.NET Framework developer guide](https://learn.microsoft.com/en-us/dotnet/framework/install/guide-for-developers)
explains the separate targeting/developer packs; installing only a later runtime
does not supply every older target's reference assemblies.
