# Security

Report reproducible security problems privately to the repository maintainers
through GitHub's available security reporting interface; do not publish credentials
or sensitive source. No dedicated reporting address is invented here.

FreeFlight has no mandatory account, telemetry, upload or runtime network feature.
Startup configuration explicitly authorizes workspace roots and trusted absolute
worker executables. Default source loading never invokes MSBuild targets, TypeScript
plugins, repository scripts, Roslyn generators or repository analyzers. Third-party
dependencies are installed during explicit development/provisioning only.

Runtime workspace selection cannot expand startup authorization. No-argument
startup grants no filesystem access; client roots are informational candidates,
not grants. Closing a runtime workspace releases its workers but does not erase
the immutable startup policy, so an explicit authorized reopen remains possible.
Removing a client-root suggestion closes only analysis workspaces explicitly
associated with that suggestion. See docs/workspaces.md for scope and revocation
semantics. No unrestricted local-access mode is enabled.

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

In the development branch, a startup-only `trustedRoots` array is the normal
bundled configuration. Every entry grants both filesystem access and trusted
C# project loading for descendant repositories, including future projects.
No separate `roots` array is required. This source-folder interface is unreleased;
published preview `v0.1.0-preview.20261020.trusted.1997d38` requires both arrays.
Legacy configurations with explicit `roots` retain safe-source access unless a
contained directory is separately trusted; `--workspace` remains safe-source.
Tool calls cannot add trust. The internal worker also retains its advanced
`--trusted-msbuild` argument. It uses MSBuildWorkspace design-time evaluation, which can execute
repository targets and imports with the worker's OS privileges. Do not enable it
for untrusted repositories. Opening a normal workspace cannot enable this mode.
No restore or ordinary build is requested; that does not prevent design-time code
execution. Project/document root validation occurs after evaluation and cannot
undo side effects or sandbox imports. Analyzer and generator references are removed
before semantic compilation. Trusted mode requires a compatible installed .NET SDK;
default safe-source mode remains self-contained. See workers/roslyn/README.md for
the explicit configuration, tested project scope and remaining fidelity limitations.

Trusted project warning recovery is narrow: NU1603/NU1701/NU1903 require exact,
project-bound Warning evidence from restore assets; warnings, including vulnerability
advisories, remain visible with degraded fidelity. Unknown load failures remain
fatal. Restore assets are untrusted data and are size/depth bounded; reading them
does not grant execution authority. See docs/workspaces.md for policy and reload.

Trusted design-time logging uses Roslyn's supported MSBuild BinaryLogger with
project imports omitted, in an temporary directory (0700 on Unix; inherited temporary-directory ACLs on Windows). Replay limits are
checked after evaluation; this is not a hard disk/RSS quota on repository code.
Normal/error completion deletes temporary logs; forced termination or a crash can
leave evaluated project metadata. Logs are never uploaded. Error events remain
fatal even when their text matches a recorded NuGet warning.
