# Current repository map

- src/main.cpp: MCP modern/legacy stdio and bounded dispatch.
- src/server.cpp: authorized roots, discovery and internal engine routing.
- src/process.cpp: shell-free worker IPC, cancellation and cleanup.
- workers/typescript: official TypeScript Language Service; source and exact fixtures.
- workers/roslyn: safe-source Roslyn AdhocWorkspace; no MSBuild evaluation.
- workflows: authoritative developer operations; bin/.local generated output.
- site: static product site linking repository-authoritative documentation.
- server.json: draft registry metadata, not a published listing.
- docs/acceptance.md and docs/task-log.md: pending release gates and evidence.

The repository exists remotely with required branches. Pre-gate Mac tests passed
for core/process, baseline language workers and mixed-language navigation. Later
TS capability extensions now pass 17 exact-result tests after corrections.
The runtime lock is fixed; native/MCPB qualification is underway. No release is published.
