# Release and registry boundaries

Promotion: js/dev -> dev -> staging -> master. master is production/default.
Use VERSION and release notes; draft PRs unless user says otherwise. Do not modify
organization security, branch protections, credentials or persistent permissions
without required action-time approval. Never publish untested production artifacts.

One standalone distribution includes C++ executable and internal runtimes/workers.
Publish qualified platform artifacts to GitHub Releases, then official MCP Registry
metadata pointing at actual supported distributions (for example validated MCPB).
Validate checksums, licensing, clean installation, real semantic invocation and
shutdown before publication. Verify metadata after publishing. Missing credentials
or hosting are explicit blockers; do not invent secrets, domains or artifact URLs.

DockPipe discovery/install is general integration in a separate scoped branch and
draft PR using existing package/process/dependency/lifecycle/security facilities.
No duplicate FreeFlight store package, new registry or package manager. Registry
metadata is untrusted discovery data, never authorization to execute. Normalize
local, registry, existing MCP-capable packages and remote endpoint configuration;
enforce transport/runtime/platform/version/workspace/permission boundaries and
secret isolation. Verify discover/install/start/invoke/stop/restart/update/remove
before calling integration complete. Do not block standalone progress on full gateway.
