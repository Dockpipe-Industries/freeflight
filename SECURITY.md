# Security

Report reproducible security problems privately to the repository maintainers
through GitHub's available security reporting interface; do not publish credentials
or sensitive source. No dedicated reporting address is invented here.

FreeFlight has no mandatory account, telemetry, upload or runtime network feature.
Startup configuration explicitly authorizes workspace roots and trusted absolute
worker executables. Default source loading never invokes MSBuild targets, TypeScript
plugins, repository scripts, Roslyn generators or repository analyzers. Third-party
dependencies are installed during explicit development/provisioning only.

The process boundary provides cancellation and fault isolation, not an OS security
sandbox. Workers retain the server's OS privileges. Their environment is reduced
to runtime search, OS/temp/locale and .NET root settings, plus Windows APPDATA
required by NuGet project loading. Windows values are read and passed as Unicode
without a lossy ANSI-codepage conversion; this does not expand the allowlist. Unrelated credentials,
NODE_OPTIONS and DOTNET_STARTUP_HOOKS are not forwarded. Run with only the OS
permissions needed; filesystem access is not constrained by this environment filter.
MCP and worker paths use UTF-8 at the protocol boundary; Windows CLI paths enter
through the wide-character entry point. Filesystem authorization uses native paths.
Canonical path checks reject ordinary traversal/symlink escape but do not make
concurrently hostile filesystem mutation race-free. This limitation blocks claims
of secure multitenant hosting. Only local single-user stdio is implemented.

Rename/import edits are previews. Original hashes help callers detect stale edits;
FreeFlight never silently applies them. Arbitrary repository configuration must not
be promoted into executable commands.

The Roslyn worker has an explicit startup-only `--trusted-msbuild` mode for trusted
projects. It uses MSBuildWorkspace design-time evaluation, which can execute
repository targets and imports with the worker's OS privileges. Do not enable it
for untrusted repositories. Opening a normal workspace cannot enable this mode.
No restore or ordinary build is requested; that does not prevent design-time code
execution. Project/document root validation occurs after evaluation and cannot
undo side effects or sandbox imports. Analyzer and generator references are removed
before semantic compilation. Trusted mode requires a compatible installed .NET SDK;
default safe-source mode remains self-contained. See workers/roslyn/README.md for
the explicit configuration, tested project scope and remaining fidelity limitations.
