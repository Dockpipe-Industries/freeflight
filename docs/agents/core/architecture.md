# Architecture and ownership

C++23 owns the single MCP endpoint, operator configuration, root authorization,
workspace routing, capability discovery, worker lifecycle and unified tool envelope.
Do not turn workers into separately configured user-facing MCP products. Mature
semantic services own language semantics; do not implement replacement parsers.

Keep protocol handling separate from engines and transport. Engine contract is
capabilities/open/query with bounded JSON and correlation IDs; cancellation must
reach the process or engine and suppress MCP replies after accepted cancellation.
RAII owns descriptors/handles/processes. Limit queues, frames, caches and workers.
Never retry a failed operation implicitly. Reuse workspaces and refresh changes.

Roslyn safe-source mode is intentionally limited. Any MSBuildWorkspace path needs
explicit workspace trust and no build/analyzer/plugin execution by ordinary open.
TypeScript must respect project boundaries without executing plugins. Future LSP
and Pipelang engines are optional registrations, not core protocol forks. Consume
stable native Pipelang semantic APIs only when public and available; no Qt coupling.
