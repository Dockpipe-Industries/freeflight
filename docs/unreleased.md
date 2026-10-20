# Unreleased: trusted project loading and document outlines

These repairs follow published source `57851e3`. They are **not** in the scaling
preview and require a newly built and qualified complete bundle. Commit/push for
cross-platform CI is authorized; protected promotion and publication remain pending. No active client
configuration or running user session is changed by this repair.

## One operator choice per folder

In an operator-owned FreeFlight configuration:

```json
{
  "roots": ["/absolute/workspace", "/absolute/read-only-project"],
  "trustedRoots": ["/absolute/workspace"],
  "csharp": {"project": "source/Architecture.sln"}
}
```

Launch the bundled `bin/freeflight` with
`--config /absolute/freeflight-trusted.json`. Omit `engines`: workers and runtimes
are located automatically. `trustedRoots` means “Trust projects in this folder.”
Project-aware C# loading is the default for selected workspaces inside that folder.
The read-only sibling remains safe-source. Trust entries cannot expand `roots`.
MSBuild design-time evaluation may execute repository targets/imports with the
operator's privileges; it is not a sandbox. Trusted mode needs an installed SDK
and restored dependencies; no automatic restore/build is requested.

The optional `csharp.project` accepts a relative `.sln` or `.csproj`. Without it,
bounded discovery finds nested solutions, prefers solutions over projects, and
requires one unambiguous candidate. Ambiguity returns candidates and selection
guidance. Set a workspace-specific project using `workspace.open` with `project`
and `reload: true`; no trust flag is accepted in semantic requests.

## Correctness and visible status

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
installation and private project were not accessed during this repair; Mac fixture
results do not claim Linux reproduction or project-aware parity with another tool.
The separately measured warm-path work below does not establish performance parity with another tool.

## Warm-path experiment excluded

A bounded per-refresh ancestor-check optimization was investigated and then
reverted independently of the functional repairs. Original measurements showed
34–37% lower medians but 27–34% higher p90; diagnostic controls did not establish
a cause or a reliable correction. The retained Refresh/CheckPath methods match
57851e3. See [preserved measurement evidence](hotpath-performance.md); no runtime
speedup or competitor-win claim applies to this repair.
