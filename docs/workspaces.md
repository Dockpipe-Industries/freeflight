# Workspace selection and access

The configure-once workspace lifecycle and scaling controls are available in the
scaling preview. The trusted-loading configuration and reload changes documented
below are local development changes and require a new qualified distribution.

FreeFlight separates permission to access a directory from selecting a project
for analysis. A project path supplied by an AI is a selection, not permission.
One server can serve all supported languages and switch between projects inside
an explicitly authorized parent directory. It does not need a separate MCP
configuration for each language or each descendant project.

## Configure once within an explicit boundary

Configure the installed binary once with `--workspace /absolute/projects`, or use
an operator-owned `--config` file listing the allowed roots. That parent authorizes
all descendants, including projects added later, so choose its scope deliberately.
Changing the access boundary requires changing startup configuration and restarting.
The server does not look for access configuration in repository files.

Runtime `workspace.open`, `workspace.list` and `workspace.close` manage active
analysis workspaces within that startup boundary. Closing releases the associated
workers. It does not remove the operator's underlying permission: an explicit
subsequent open inside the same boundary is still permitted. There is no implicit
global active project; semantic requests identify their workspace.

| Tool | Arguments | Result |
| --- | --- | --- |
| `workspace.list` | `{}` | Allowed roots, active workspaces and client candidates; no project scan |
| `workspace.open` | `{"root":"/absolute/projects/app"}` | Canonical root and `active: true` |
| `workspace.close` | `{"root":"/absolute/projects/app"}` | Root and `active: false`; descendant sessions also close |
| `workspace.clientRoots` | `{}` | Optional client-root discovery; unsupported clients retain normal workspace tools |

List results identify `authorization: "startup-only"`, `allowedRoots`,
`workspaces`, `candidates` and `dormant`. A semantic request for a closed workspace
fails until an explicit open. Opening one sibling project does not close another.

## No-argument startup

Launching the executable without arguments starts a dormant MCP endpoint with no
authorized workspace. Protocol discovery and workspace metadata are available;
source analysis is not. This mode does not authorize the current directory, the
home directory, a path in a tool call, or a client-reported folder. Workers remain
lazy. No-argument startup alone is not a filesystem consent mechanism.

## Optional client-root compatibility

MCP client roots are informational candidates. They cannot expand FreeFlight's
startup access policy. A client without roots can select an authorized project
directly using workspace tools. A client with roots can provide suggestions, and
an explicitly opened workspace can be associated with one of those suggestions.
Removing that suggestion closes its associated analysis workspace; it does not
revoke or expand the independent startup permission.
Association is explicit through `workspace.open`'s optional `candidateUri` field.
Pinned startup workspaces are not associated with transient suggestions.

The [2026-07-28 MCP specification](https://modelcontextprotocol.io/specification/2026-07-28/client/roots)
deprecates roots and recommends tool parameters or server configuration for new
integrations. Compatibility support is optional; FreeFlight's workspace contract
does not depend on a particular client exposing this feature. Current roots use
the protocol's input-required/retry exchange; older negotiated clients use their
legacy roots exchange. Neither is an authorization channel.

## Broader local access is a separate decision

A possible future trusted-local mode could let runtime project selection use a
broader operator-approved filesystem scope. Such a mode would need explicit
consent describing the accessible directories, whether future descendants are
included, how long the grant lasts, and how to revoke it. It is not enabled by
this change. Trusting a client to choose directories would also be a separate,
explicit policy choice; merely advertising roots is insufficient.

Filesystem access and repository code execution remain separate permissions.
Opening a workspace does not enable MSBuild evaluation, plugins, generators or
analyzers. See [security](../SECURITY.md) for worker privilege and filesystem-race
limitations.

## Source resources and incremental refresh

Normal analysis retains language-service state between requests. C# keeps stable
Roslyn document IDs and source snapshots; TypeScript keeps language services and
a bounded source-snapshot cache. The requested document is content-checked on each
query. Unchanged unrelated sources reuse snapshots, with metadata checks and a
five-second content-revalidation fallback. C# also watches changes and invalidates
on watcher overflow. File enumeration still occurs; these changes do not make
safe-source C# a project-aware solution loader or promise constant-time queries.
Rename/edit previews revalidate source contents before emitting original hashes.

Default source budgets apply automatically, without per-project configuration:

| Startup setting | Default | Maximum accepted override |
| --- | ---: | ---: |
| `maxFileBytes` | 32 MiB | 256 MiB |
| `maxWorkspaceBytes` | 512 MiB | 2 GiB |
| `maxFiles` | 50,000 | 200,000 |
| `maxDirectoryEntries` | 500,000 | 2,000,000 |

These are source/admission budgets, not a process RSS guarantee: semantic trees,
metadata and compiler state consume additional memory. They replace the preview's
2 MiB C# file/64 MiB workspace limits. C# safe and explicitly trusted project modes
use the same policy; TS/JS uses it for its retained projects. Worker concurrency,
message sizes and cache counts remain independently bounded. No analyzer, plugin
or MSBuild execution permission is granted by raising a resource budget.

Operators who need a different budget may launch `freeflight --config` with an
absolute path to an explicitly selected configuration file, for example:

```json
{
  "roots": ["/absolute/projects"],
  "resources": {
    "maxFileBytes": 67108864,
    "maxWorkspaceBytes": 1073741824
  }
}
```

Installed bundles discover their internal workers when `engines` is omitted.
Development builds may explicitly supply absolute engine commands as before.
Settings must be positive integers within the documented bounds, with file budget
no greater than workspace budget. Unknown settings are rejected. Tool requests
and repository files cannot change this startup policy.

Resource failures are explicit MCP tool errors: `isError: true` and
`structuredContent.error` contains `code: resource_limit_exceeded`, the resource,
root-relative path, observed size/count, limit and remediation. Files are not
silently dropped to fit a budget. After correcting the source or restarting with
an appropriate operator policy, an explicit retry can recover. The published
preview's error omits this detail and has no supported resource override.

Unrelated-file changes are eventually reconciled: watcher delivery can lag and
metadata alone cannot prove unchanged contents. Direct targets are read afresh;
the fallback bounds persistent stale unrelated snapshots. Trusted project graph
changes still require closing/reopening the workspace. Full large-solution and
long-running memory qualification remain separate from generated-source tests.

TypeScript retains lightweight content versions independently of its 64 MiB text
cache, so text eviction does not force rereading every unchanged dependency.
Its budget includes configured sources and loaded dependency/configuration files.
Project-reference graphs are not yet fully supported: configurations declaring
them fail with `unsupported_project_references` instead of returning apparently
complete partial results. Ordinary imports within a configured project remain
supported. This fix does not introduce a solution builder or run repository builds.

## Explicit trusted C# configuration (development repair)

Use the complete bundled application with an operator-owned configuration file;
no internal executable paths or separate worker installations are required:

```json
{
  "roots": ["/absolute/workspace"],
  "trustedRoots": ["/absolute/workspace"],
  "csharp": {
    "project": "source/Architecture.sln"
  }
}
```

For a Linux installation, set the MCP command to
`/absolute/install/freeflight-linux-x64/bin/freeflight`,
with arguments `["--config", "/absolute/freeflight-trusted.json"]`.
These are operator instructions, not configuration applied by the application. The existing
published `57851e3` binary does **not** implement this new configuration; a rebuilt,
qualified bundle is required. This repair has not been published.

Omit `engines` to use bundled workers. Reading an authorized `roots` directory
remains safe-source by default. Adding a directory to `trustedRoots` is the one-time
operator choice **“Trust projects in this folder.”** Selected workspaces inside
that directory use project-aware MSBuild loading by default; sibling read-only
roots remain safe-source. Each trust entry must be an absolute existing directory
within the independent `roots` boundary. A parent workspace that merely contains
a trusted descendant remains safe-source: explicitly select the trusted child.
Use narrow trust entries; every selected descendant inherits execution trust.
The advanced legacy `csharp.mode: "trusted-msbuild"` or internal trusted worker
argv authorizes all startup roots, and cannot be mixed with `trustedRoots`. Prefer
the per-root setting above. A compatible installed .NET SDK, targeting packs, and already-restored
project dependencies are still needed for trusted evaluation. The bundled runtime
is sufficient for safe-source mode, but is not an SDK. No automatic restore is run.
MSBuild imports/targets may execute repository code; this is not a sandbox.

`csharp.project` is an optional root-relative `.sln` or `.csproj` selection. When
omitted, bounded recursive discovery skips generated/dependency directories and
symlinks, preferring solutions over individual projects. One unique candidate is
selected, including a nested `source/Architecture.sln`. Multiple candidates fail
with explicit selection guidance instead of silently choosing one. With multiple
startup roots, the default relative project applies independently to each root;
select per-workspace projects with `workspace.open` when needed.

To change a selection or reload changed project configuration without restarting
the MCP endpoint:

```json
{"root":"/absolute/workspace","project":"source/Architecture.sln","reload":true}
```

Pass this to `workspace.open`. `reload: true` stops only that exact workspace's
internal workers; the next capability/semantic request reloads them. It retains
startup authorization, selections and other workspace sessions. A live C# project
selection change requires this explicit reload. Without reload, repeated open is
idempotent. Close/reopen also reloads, but close includes descendant workspaces and
clears runtime selection overrides. Source content refreshes incrementally;
project graphs, restore results, SDK selection and load-warning status refresh on
reload. Changing startup roots, trust mode, resource policy, or installed executable
requires an operator restart of the MCP process. Query arguments and repository
configuration cannot enable trust.

`engine.capabilities.analysis` reports the active mode, selected project,
`loadWarnings`, `degradedFidelity`, and limitations after successful opening.
`workspace.list` reports configured C# mode/selection and initialized engine state.
An empty engine map means no graph has loaded yet. Startup policy and loaded graph
status are deliberately distinct. Warnings remain visible until reload; source
compiler diagnostics remain available through the diagnostics operation.

Roslyn 5.9 can report NuGet warnings as workspace failures. The repair accepts only
NU1603, NU1701 and NU1903 messages that exactly match Warning records in the same
project's standard `obj/project.assets.json`. Vulnerability advisories remain
visible and set degraded fidelity; they are not suppressed or fixed. Unknown
failures, restore Error records, missing metadata references and empty/unusable
graphs still fail. Other incorrectly classified warning codes or missing/unmatched evidence fail
conservatively rather than being guessed harmless. SDK discovery errors,
concrete missing/malformed restore evidence, and other project-load errors receive
distinct structured codes and remediation. An ordinary project-load failure alone
no longer receives generic restore advice.

For trusted loads, FreeFlight uses Roslyn's supported MSBuild binary logger to
retain genuine error severity and evaluated restore-asset paths. A real error,
including a warning promoted to an error, remains fatal even if its text matches
a recorded warning. SDK design-time loading can skip absent assets without raising
an error, so missing evaluated assets are checked independently. Temporary logs
use an OS temporary directory (0700 on Unix; inherited temporary-directory ACLs on Windows) with project imports omitted; bounded
replay follows evaluation and normal/error cleanup deletes the directory. A force
kill or crash can leave evaluated build metadata behind. Neither logging bounds
nor source budgets sandbox MSBuild execution or impose a total disk/RSS ceiling.

When MSBuild omits evaluated assets-path evidence, a bounded, DTD-disabled read of
the project recognizes standard declarative SDK/PackageReference restore needs.
Missing standard assets then produce `restore_required`. Customized or inherited
intermediate paths without evaluated evidence fail conservatively with inspection
guidance; FreeFlight does not implement its own MSBuild evaluator or guess that
restore will repair every failure. Custom layouts need separate qualification.
