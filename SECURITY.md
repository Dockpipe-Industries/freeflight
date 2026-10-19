# Security

Report reproducible security problems privately to the repository maintainers
through GitHub's available security reporting interface; do not publish credentials
or sensitive source. No dedicated reporting address is invented here.

FreeFlight has no mandatory account, telemetry, upload or runtime network feature.
Startup configuration explicitly authorizes workspace roots and trusted absolute
worker executables. Opening source never invokes MSBuild targets, TypeScript
plugins, repository scripts, Roslyn generators or repository analyzers. Third-party
dependencies are installed during explicit development/provisioning only.

The process boundary provides cancellation and fault isolation, not an OS security
sandbox. Workers retain the server's OS privileges. Their environment is reduced
to runtime search, OS/temp/locale and .NET root settings; unrelated credentials,
NODE_OPTIONS and DOTNET_STARTUP_HOOKS are not forwarded. Run with only the OS
permissions needed; filesystem access is not constrained by this environment filter.
Canonical path checks reject ordinary traversal/symlink escape but do not make
concurrently hostile filesystem mutation race-free. This limitation blocks claims
of secure multitenant hosting. Only local single-user stdio is implemented.

Rename/import edits are previews. Original hashes help callers detect stale edits;
FreeFlight never silently applies them. Arbitrary repository configuration must not
be promoted into executable commands. Do not add trusted MSBuild evaluation without
explicit authorization, threat-model review and tests demonstrating its boundary.
