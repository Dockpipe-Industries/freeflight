# TASK-002: Core and language semantic hardening

Status: open. The full acceptance ledger is docs/acceptance.md; execution evidence
is docs/task-log.md. Follow the matching route in docs/agents/index.yaml.

Baseline Mac semantic tests passed. New TypeScript operations now pass 17 tests;
hosted cross-platform qualification is still required before publication.
Full C# project fidelity and large-repository validation remain pending.

Current work adds explicit runtime workspace lifecycle within startup authorization,
dormant no-argument startup and optional informational client-root compatibility.
See docs/workspaces.md. Source access must not be granted by tool paths or client
suggestions. Published previews retain the old interface until a new candidate
passes its full qualification gates.
