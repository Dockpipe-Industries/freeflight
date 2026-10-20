# Workspace selection and access

This describes the development-branch workspace lifecycle. The published Ubuntu
22.04 preview retains its original startup-root interface until a replacement is
qualified and explicitly published.

FreeFlight separates permission to access a directory from selecting a project
for analysis. A project path supplied by an AI is a selection, not permission.
One server can serve all supported languages and switch between projects inside
an explicitly authorized parent directory. It does not need a separate MCP
configuration for each language or each descendant project.

## Configure once within an explicit boundary

Configure the installed binary once with `--workspace /absolute/projects`, or use
an operator-owned `--config` file listing the allowed roots. That parent authorizes
all descendants, including projects added later, so choose its scope deliberately.
Changing the access boundary requires changing startup configuration and restarting.
The server does not look for access configuration in repository files.

Runtime `workspace.open`, `workspace.list` and `workspace.close` manage active
analysis workspaces within that startup boundary. Closing releases the associated
workers. It does not remove the operator's underlying permission: an explicit
subsequent open inside the same boundary is still permitted. There is no implicit
global active project; semantic requests identify their workspace.

| Tool | Arguments | Result |
| --- | --- | --- |
| `workspace.list` | `{}` | Allowed roots, active workspaces and client candidates; no project scan |
| `workspace.open` | `{"root":"/absolute/projects/app"}` | Canonical root and `active: true` |
| `workspace.close` | `{"root":"/absolute/projects/app"}` | Root and `active: false`; descendant sessions also close |
| `workspace.clientRoots` | `{}` | Optional client-root discovery; unsupported clients retain normal workspace tools |

List results identify `authorization: "startup-only"`, `allowedRoots`,
`workspaces`, `candidates` and `dormant`. A semantic request for a closed workspace
fails until an explicit open. Opening one sibling project does not close another.

## No-argument startup

Launching the executable without arguments starts a dormant MCP endpoint with no
authorized workspace. Protocol discovery and workspace metadata are available;
source analysis is not. This mode does not authorize the current directory, the
home directory, a path in a tool call, or a client-reported folder. Workers remain
lazy. No-argument startup alone is not a filesystem consent mechanism.

## Optional client-root compatibility

MCP client roots are informational candidates. They cannot expand FreeFlight's
startup access policy. A client without roots can select an authorized project
directly using workspace tools. A client with roots can provide suggestions, and
an explicitly opened workspace can be associated with one of those suggestions.
Removing that suggestion closes its associated analysis workspace; it does not
revoke or expand the independent startup permission.
Association is explicit through `workspace.open`'s optional `candidateUri` field.
Pinned startup workspaces are not associated with transient suggestions.

The [2026-07-28 MCP specification](https://modelcontextprotocol.io/specification/2026-07-28/client/roots)
deprecates roots and recommends tool parameters or server configuration for new
integrations. Compatibility support is optional; FreeFlight's workspace contract
does not depend on a particular client exposing this feature. Current roots use
the protocol's input-required/retry exchange; older negotiated clients use their
legacy roots exchange. Neither is an authorization channel.

## Broader local access is a separate decision

A possible future trusted-local mode could let runtime project selection use a
broader operator-approved filesystem scope. Such a mode would need explicit
consent describing the accessible directories, whether future descendants are
included, how long the grant lasts, and how to revoke it. It is not enabled by
this change. Trusting a client to choose directories would also be a separate,
explicit policy choice; merely advertising roots is insufficient.

Filesystem access and repository code execution remain separate permissions.
Opening a workspace does not enable MSBuild evaluation, plugins, generators or
analyzers. See [security](../SECURITY.md) for worker privilege and filesystem-race
limitations.
