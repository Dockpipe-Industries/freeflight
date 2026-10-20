# Workspace selection and access

The `trustedRoots`-only source-folder workflow described here is **unreleased**.
The published [trusted-loading preview](https://github.com/Dockpipe-Industries/freeflight/releases/tag/v0.1.0-preview.20261020.trusted.1997d38)
still requires its documented `roots` plus `trustedRoots` configuration. Installing
that preview does not enable this newer routing behavior.

## Configure once within an explicit boundary

For a complete bundle built from this development branch, create an operator-owned
configuration file:

```json
{
  "trustedRoots": ["/absolute/source-a", "/absolute/source-b"]
}
```

Launch `bin/freeflight --config /absolute/freeflight.json` through the MCP client.
Bundled workers are located automatically. No `engines`, duplicate `roots`, or
per-project `.sln`/`.csproj` setting is needed. Each existing absolute directory
can contain multiple repositories, including repositories created later.

**Each entry grants both source access and permission for trusted C# design-time
MSBuild evaluation in its descendants.** Targets and imports can execute repository
code with the worker's OS privileges. This is not a sandbox. Choose directories
containing only projects you trust. A compatible installed .NET SDK, required
targeting packs and already-restored dependencies are still required; the bundled
runtime is not an SDK, and FreeFlight does not automatically restore projects.

Changing this startup boundary requires a configuration change and MCP restart.
Repository files and tool arguments cannot grant additional access or trust.

## Lazy document routing and workspace selection

Startup and `workspace.list` do not recursively scan or load all repositories.
A `semantic.query` can name a configured source directory as `root` and an absolute
`arguments.file` beneath it. The core inspects that file's ancestors, selecting the
nearest Git/Mercurial repository boundary. Without repository metadata, it prefers
an ancestor solution directory, then a project directory (or TS/JS configuration
or package directory). Loose files use their containing directory. Discovery is
bounded and checks cancellation; it does not enumerate sibling repositories.
The selected workspace gets a lazily initialized, reusable language worker.

For example, a file under `/absolute/source-a/app/source/Lib/Widget.cs` can route
to `app`, where the C# worker discovers `source/Architecture.sln`. Within the
selected workspace, discovery prefers solutions over projects. Multiple candidates
return structured `project_selection_required` details rather than guessing.

Workspace-wide queries and capability inspection use an explicitly selected
repository directory. Call `workspace.open` with that directory, then use it as
the query's `root`. A source-root request without a file or explicit workspace
selection returns `workspace_selection_required`, avoiding an accidental load of
the entire source directory. Project ambiguity is resolved through `workspace.open`
with a root-relative `project` and `reload: true`; it never requires a client
configuration edit. See the reload examples below.

| Tool | Arguments | Result |
| --- | --- | --- |
| `workspace.list` | `{}` | Access/trust roots, active workspaces and client candidates; no project scan |
| `workspace.open` | `{"root":"/absolute/source-a/app"}` | Canonical root and `active: true`; workers remain lazy |
| `workspace.close` | `{"root":"/absolute/source-a/app"}` | Root and `active: false`; descendant sessions also close |
| `workspace.clientRoots` | `{}` | Optional client-root discovery; suggestions never grant access |

List results identify `authorization: "startup-only"`, `allowedRoots`,
`trustedRoots`, `workspaces`, `candidates` and `dormant`. Closing releases workers
and runtime selections, not startup permission. A direct query against a closed
workspace requires reopening it; a new file query through an active authorized
source root can route to it again. Opening one sibling does not close another.

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

## Legacy safe-source configuration

`--workspace /absolute/project` and an explicit `roots` array retain safe-source
behavior unless separately trusted. Existing configurations with both `roots`
and a `trustedRoots` subset remain supported: each trust entry must be within
`roots`. This advanced form is useful when mixing read-only, untrusted source
areas with trusted projects. It is not required for the normal source-folder setup.
When `roots` is supplied, the legacy explicit workspace-routing contract remains
in effect. No-argument startup remains dormant.

See [security](../SECURITY.md) for process privileges and filesystem-race limits.

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
  "trustedRoots": ["/absolute/projects"],
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

## Trusted C# project selection and reload

The normal configuration is the single `trustedRoots` array above. Within the
selected repository, bounded discovery skips dependency/generated directories
and symlinks, and discovers nested solutions such as `source/Architecture.sln`.
One unique solution is selected ahead of individual projects. Multiple solutions
or projects return structured candidates and require a tool-level selection.

The optional legacy `csharp.project` startup default and `csharp.mode` settings
remain supported for existing advanced configurations. They are not required for
source-folder setup. Global legacy trusted mode cannot be mixed with `trustedRoots`.

To change a selection or reload changed project configuration without restarting
the MCP endpoint:

```json
{"root":"/absolute/source-a/app","project":"source/Architecture.sln","reload":true}
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
