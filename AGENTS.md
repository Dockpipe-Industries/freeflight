# FreeFlight contributor and agent guide

Machine-readable router: `docs/agents/index.yaml` (schema 1). Open tasks:
`docs/agents/task-index.yaml` (schema 2). Start with the matching route before edits.
Scoped instructions exist in src/AGENTS.md, workers/AGENTS.md, workflows/AGENTS.md
and site/AGENTS.md. Canonical documentation remains in docs/README.md.

## Prerequisite gate

Pause implementation/builds until the agent router, scoped instructions and
bootstrap inspection pass repo.check. Validate links and latest amendment
consistency whenever guidance changes. Do not erase implementation already present.

## Task routing

| Work | Read first |
| --- | --- |
| Core protocol/processes | docs/agents/core/architecture.md, verification.md |
| Language engines | workers/AGENTS.md and the relevant worker README |
| DockPipe tasks | docs/agents/workflows/development.md, workflows/README.md |
| Security/dependencies | SECURITY.md, docs/agents/core/dependencies.md |
| Release/Registry/DockPipe integration | docs/agents/release/distribution.md |
| Site/public claims | docs/agents/site/product.md, source-of-truth rules |
| Guidance/tasks | docs/agents/README.md and task-index.yaml |

The native Registry amendment supersedes dedicated DockPipe store publication.
One standalone distribution; no duplicate FreeFlight-specific DockPipe package.
Keep general DockPipe changes in a separate scoped branch and draft PR. No security
settings, credential generation or persistent permission expansion without approval.
Promote js/dev -> dev -> staging -> master only with verified gates.

FreeFlight is one C++23 MCP server with internal native language workers.
Use DockPipe workflows as the authoritative development interface. Keep native
CMake and worker manifests directly usable. Never duplicate task orchestration in
npm scripts or CI. Workflow layout follows DockPipe Cloud's inspected conventions.

Generated output belongs in bin/.local; DockPipe owns bin/.dockpipe. Never clean
untracked developer files indiscriminately. Keep source, credentials, telemetry and
private organization implementation details out of logs and public artifacts.

Opening a workspace must not execute repository code, MSBuild targets, language
plugins, analyzers or generators. Only explicitly configured absolute worker
executables may be launched. Workspace authorization comes from server startup.
Refactoring results are previews until a separately tested application contract exists.

Update docs/acceptance.md and docs/task-log.md with evidence. Do not mark authored
code, configured CI, or untested platform builds as passing. Preserve unrelated work.
