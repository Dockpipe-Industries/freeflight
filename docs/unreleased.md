# Unreleased: one trusted source-folder configuration

This change follows the published
[`v0.1.0-preview.20261020.trusted.1997d38`](https://github.com/Dockpipe-Industries/freeflight/releases/tag/v0.1.0-preview.20261020.trusted.1997d38)
trusted-loading preview. **The new configuration and routing are not published.**
That preview still requires both `roots` and `trustedRoots`; use its release notes
when configuring it. No active client configuration or user session is changed by
this work. Qualification and promotion must precede a replacement distribution.

## Configure trusted source folders once

For a complete bundle built from this development branch:

```json
{
  "trustedRoots": ["/absolute/source-a", "/absolute/source-b"]
}
```

Launch bundled `bin/freeflight` with `--config /absolute/freeflight.json`.
Workers are located automatically. No separate `roots`, engine paths or mandatory
`csharp.project` setting is needed. Each entry grants access **and permission for
MSBuild design-time repository code execution** in its descendants. Use only
source folders whose projects you trust. This is not a sandbox; a compatible SDK,
targeting packs and restored dependencies remain prerequisites for trusted C#.

Startup does not scan every repository. A file query through a configured source
root lazily selects its repository/project workspace. Nested solutions are
discovered within that selected workspace. Workspace-wide queries require
`workspace.open` with the desired repository directory. Genuine ambiguity returns
structured `project_selection_required` candidates; choose one using
`workspace.open` with a relative `project` and `reload: true`. No client config edit
is needed. Source edits refresh incrementally; project graph changes require reload.
See [workspace behavior and compatibility](workspaces.md) for exact routing rules.

Legacy `roots`, `roots` plus a trusted subset, and `--workspace` remain supported.
The latter remains safe-source. Requests and repository configuration cannot
expand startup trust or filesystem boundaries.

## Repairs already in the published trusted-loading preview

- Confirmed NU1603/NU1903/NU1701 restore warnings no longer reject otherwise usable
  graphs merely because Roslyn reports them as Failure. Exact project/message
  warning evidence is required. Vulnerability warnings remain fully visible.
- Real MSBuild errors, warnings promoted to errors, unknown failures, missing
  evaluated restore assets and unusable graphs still reject loading. No blanket
  suppression or generic “restore first” recommendation is used.
- `engine.capabilities.analysis` exposes `mode`, `selectedProject`, `loadWarnings`,
  `degradedFidelity` and limitations. `workspace.list` distinguishes startup policy
  from initialized engine state. Empty engine state is not a successful load.
- Document outlines use the declaration in the requested document, fixing merged
  namespace and partial-type locations that could point into another file. Generic
  file-scoped and repeated block-namespace fixtures assert exact positions.

## Reload and troubleshooting

| Situation | Action |
| --- | --- |
| Source content edit | Incremental refresh; no MCP restart |
| Project/solution selection, graph, restore results or load-warning change | `workspace.open` with the same root and `reload: true`; next semantic/capability request reloads workers |
| Close/reopen | Also reloads, but close includes descendant workspaces and clears runtime project overrides |
| Startup trust/roots/resources or replacement application bundle | Operator restarts MCP; existing processes retain their startup policy and executable |
| `sdk_not_found` | Install/select a compatible SDK; bundled .NET runtime is not an SDK |
| `restore_required` | Inspect reported missing/malformed assets or restore errors; explicitly restore the selected trusted project before reload |
| `project_load_failed` | Inspect actual diagnostics, SDK/targeting packs and graph; restore is not presumed to solve it |
| `project_selection_required` | Choose an explicit relative `.sln`/`.csproj` from the reported candidates |

Temporary design-time logs omit project imports and use OS temporary storage (0700 on Unix; inherited temporary-directory ACLs on Windows); normal/error cleanup deletes them. A forced kill or crash can leave
metadata. Replay/source bounds do not sandbox MSBuild or impose total disk/RSS caps.
Standard SDK/PackageReference projects receive an additional bounded declarative
check when evaluated assets paths are absent. Customized paths without evidence
fail conservatively with inspection guidance. Only documented matching warning
evidence is recovered; other ambiguous failures
remain fatal. `.slnx`, linked source across projects, custom generator fidelity and
universal solution compatibility remain unqualified.

Validation results are recorded in [the task log](task-log.md). The reported Linux
installation and private project were not accessed during the trusted-loading repair; Mac fixture
results do not claim Linux reproduction or project-aware parity with another tool.
The separately measured warm-path work below does not establish performance parity with another tool.

## Historical warm-path experiment excluded

A bounded per-refresh ancestor-check optimization was investigated and then
reverted independently of the functional repairs. Original measurements showed
34–37% lower medians but 27–34% higher p90; diagnostic controls did not establish
a cause or a reliable correction. The retained Refresh/CheckPath methods match
57851e3. See [preserved measurement evidence](hotpath-performance.md); no runtime
speedup or competitor-win claim applies to the trusted-loading repair.
