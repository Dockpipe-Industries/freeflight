# Language capabilities and evidence

The capabilities below have semantic fixture evidence. Hosted candidate qualification
passed Linux x64/ARM64, Windows x64 and macOS ARM64 at candidate 2c29369.
Every changed candidate must be requalified before release. See [distribution evidence](distribution.md) and [current CI](https://github.com/Dockpipe-Industries/freeflight/actions/workflows/ci.yml)
for candidate-specific results. This matrix does not announce a production release. The
C++ endpoint exposes `workspace.discover`, `engine.capabilities` and
`semantic.query`. Clients must inspect the selected engine's advertised operations.

| Operation | TypeScript | JavaScript | C# / Roslyn |
| --- | --- | --- | --- |
| Document symbols | Fixture-tested | Installed-bundle smoke-tested | Fixture-tested |
| Definitions and references | Exact location/count fixtures | Available through the shared TypeScript engine; dedicated JS coverage pending | Exact location/count fixtures |
| Hover | Fixture-tested | JSDoc hover fixture-tested | Fixture-tested |
| Compiler diagnostics | Fixture-tested | JSDoc type-error fixture-tested | Clean/error fixtures in safe and trusted modes |
| Implementations | Concrete method fixture-tested | Shared engine; dedicated JS coverage pending | Interface implementation and override positions fixture-tested |
| Type information | QuickInfo alias fixture-tested | Shared engine; dedicated JS coverage pending | Semantic/converted types and UTF-16 positions fixture-tested |
| Function signature help | Fixture-tested | Shared engine; dedicated JS coverage pending | Invocation overload selection/argument position fixture-tested |
| Workspace symbol search | Fixture-tested within selected project | Shared engine; dedicated JS coverage pending | Source declaration location and result limit fixture-tested |
| Call hierarchy | Incoming/outgoing identity fixtures | Shared engine; dedicated JS coverage pending | Static incoming/outgoing, constructor and nested-callable fixtures |
| Rename | Hash/range/no-write previews tested | Shared engine; dedicated JS coverage pending | Hash/range/no-write previews tested |
| Import organization | No-write preview fixture-tested | Shared engine; dedicated JS coverage pending | Not supported |
| Code actions | Diagnostic quick-fix preview fixture-tested | Shared engine; dedicated JS coverage pending | Not supported |
| Type hierarchy | Not supported | Not supported | Immediate class/interface relationships fixture-tested |
| Analyzer diagnostics | Not supported | Not supported | Not supported |

All edits are previews. There is no application API that writes source files.
Callers applying edits must check workspace boundaries, original-file hashes and
concurrent changes. Code actions are alternatives, not one combined edit set;
commands, package installation and new-file fixes are excluded.

## TypeScript and JavaScript

The official TypeScript 5.9.3 Language Service supports nearest in-root
`tsconfig.json`/`jsconfig.json` configuration, incremental content updates and a
bounded project cache. It does not run plugins or project scripts. Search is
scoped to the project selected by `file`; project-reference solution builds and
cross-project aggregation are not implemented. Type information is a QuickInfo
projection, not a type graph. Worker cancellation is enforced by terminating the
process through the core, since synchronous TypeScript calls cannot process a
cancellation notification mid-call.

Evidence: [`workers.typescript`](../workflows/workers.typescript/config.yml),
[semantic tests](../workers/typescript/test/worker.test.mjs), and
[worker contracts](../workers/typescript/README.md). Dedicated JavaScript fixtures
verify JSDoc hover and type errors; installed-bundle checks verify a JavaScript
function symbol. Shared implementation alone is not evidence of every operation
on every JavaScript project configuration.

## C# default: safe source analysis

Roslyn's default `safe-source` mode analyzes a bounded source view without MSBuild,
repository assemblies, analyzers or generators. It combines source files into one
project using worker runtime references. This does not reproduce arbitrary .NET
solution settings, external dependencies, defines, generated source or project
boundaries. The parser uses C# 12. Results are semantic analysis of that source
view and may differ from the repository's build.

C# exposes 12 operations: `symbols`, `definition`, `references`, `hover`,
`diagnostics`, `rename`, `implementations`, `typeInfo`, `signatureHelp`,
`workspaceSymbols`, `callHierarchy` and `typeHierarchy`. Signature help supports
ordinary invocation expressions only, not constructors/indexers/attributes. Type
hierarchy reports immediate class/interface relationships only. Incoming calls
retain Roslyn’s direct/indirect flag; outgoing calls cover explicit statically bound
invocations and construction, not implicit property/event access, operators,
dynamic dispatch or reflection. Nested callable bodies belong to separate callers.
Symbol searches are bounded at 1,000 results and call edges at 500 per direction;
excess fails instead of silently returning partial data. These limits and recovery
are fixture-tested. See the worker README for the complete contract.

## C# opt-in: trusted project evaluation

An operator may explicitly configure the internal Roslyn worker with
`--trusted-msbuild` at startup. Requests cannot enable it. The bundled default
`--workspace` launch remains safe-source and requires no separately installed SDK.
Trusted evaluation needs an operator-installed compatible .NET SDK and explicitly
restored project dependencies. The bundle includes Roslyn's `BuildHost-netcore`,
not a complete .NET SDK.

**MSBuild design-time evaluation can execute arbitrary repository code, imports,
custom targets and SDK resolvers. Only enable this mode for trusted repositories.**
Path checks constrain returned data; they do not sandbox evaluation or prevent
external project imports from executing before rejection. Repository analyzers
and source generators are disabled. See [security guidance](../SECURITY.md).

Local trusted-mode fixtures verify a conditional compilation define, a two-project
SDK graph, exact cross-project definitions/references, clean diagnostics, changed
source errors and root/mode rejection. This does not qualify large solutions,
custom SDKs, multi-targeting, generated sources, VB or shared linked documents.
Configuration and graph changes require reopening the workspace.

Evidence: [`workers.roslyn`](../workflows/workers.roslyn/config.yml),
[safe-source tests](../workers/roslyn/test_worker.py),
[trusted project tests](../workers/roslyn/test_trusted.py), and
[worker contracts](../workers/roslyn/README.md).

## Other languages and release status

No Python, Go, Rust, C/C++, Java, HTML/CSS, JSON/YAML or Pipelang adapter is currently
advertised. LSP and future native Pipelang integration are extension points.
See [distribution evidence](distribution.md) for exact qualified bundle snapshots.
A local package pass does not establish signed installers, Registry publication,
desktop-host compatibility or execution on other operating systems.
