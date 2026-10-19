# Official MCP Registry publication

FreeFlight uses the official MCP Registry publisher, pinned to **v1.8.1**
(upstream release 2026-08-06, commit `f52dc8525a441a3abf5fedc9912152d95af5aab1`).
This workflow is prepared infrastructure. No Registry publication or authentication
setup has been performed by its implementation.

## Prerequisites

Follow the promotion and artifact qualification requirements in [release.md](release.md).
Publish qualified assets to the real FreeFlight GitHub Release first. Run
`dockpipe --workflow release.prepare` in `verify-urls` mode. Its generated directory
must contain `server.draft.json` and `release-manifest.json`. Offline draft templates
are deliberately ineligible. The version must match repository `VERSION`; the
GitHub release tag must resolve to the embedded clean-source commit or a promoted
descendant with the identical Git tree. Unrelated ancestry or changed trees fail.
Checksums and
embedded test receipts remain unsigned provenance, not an independent attestation.

Provision an appropriate archive from the [official v1.8.1 release](https://github.com/modelcontextprotocol/registry/releases/tag/v1.8.1).
Verify its SHA256 against the reviewed pins in
`workflows/registry.publish/assets/publish.py` before extracting the publisher.
The workflow independently checks the archive pin and compares the executable
bytes with its archive member before running it. It never downloads or replaces
an executable automatically. Python's existing `jsonschema` development dependency
is required, as for `registry.check`.

On the implementation Mac, the checksum-verified archive and binary were provisioned
under the task-local `toolchains/mcp-publisher-1.8.1/` directory:

| Artifact | SHA256 |
| --- | --- |
| darwin arm64 archive | `e45e520892460732a4bdf37255576415d4a53ec171f8b913faf15bb1aef7cb77` |
| extracted publisher | `9bb851e40b648245e3ba74b0c03443bad8660b56acfc6855dc09817f67783341` |

`mcp-publisher --version` verified version 1.8.1. This is checksum verification,
not a claim of signature or Sigstore verification. Other platform archive pins
are recorded; their executables have not been run locally.

## DockPipe interface

Set the following environment configuration, then run
`dockpipe --workflow registry.publish`:

| Variable | Value |
| --- | --- |
| `FREEFLIGHT_REGISTRY_INPUT` | Absolute directory produced by URL-verified `release.prepare` |
| `FREEFLIGHT_PUBLISHER` | Absolute path to the pinned official publisher executable |
| `FREEFLIGHT_PUBLISHER_ARCHIVE` | Path to its original checksum-pinned release archive |
| `FREEFLIGHT_REGISTRY_MODE` | `verify` (default), or explicitly `publish` |

The default verifies the pinned official schema, namespace, version, package
contract, release tag, and freshly downloaded release asset hash. Redirects are
limited to HTTPS GitHub release infrastructure. It does not read authentication.
`publish` performs those checks and invokes the official publisher with a temporary
snapshot of the validated metadata. It requires existing authentication targeting
`https://registry.modelcontextprotocol.io` in the official publisher's existing
`~/.config/mcp-publisher/token.json`. It never creates this file, logs in, refreshes
credentials, adds GitHub permissions, or modifies namespace ownership. A failed or
ambiguous submission must be checked against the Registry before retrying.

The selected MCPB represents one explicitly chosen architecture. MCPB 0.3 does not
provide CPU architecture selection; publication must not imply universal automatic
platform resolution. The workflow rejects unexpected remote endpoints and extra
packages. Live URL and Registry submission validation remain blocked until qualified
release assets, matching tags, and approved authentication exist.

## Authentication and approval boundary

The official CLI supports GitHub login and GitHub Actions OIDC, plus DNS and HTTP
ownership methods. FreeFlight's namespace is `io.github.Dockpipe-Industries/freeflight`.
GitHub organization publishing requires appropriate organization ownership/membership
verification; no credential scopes should be expanded implicitly.

For future CI, upstream supports `mcp-publisher login github-oidc` with an explicitly
approved job `id-token: write` permission. No OIDC login or workflow permission change
is included here. An authorized job may establish authentication separately and then
invoke this same workflow. Do not enable publishing automatically on validation or
pull request workflows. Existing auth is not evidence that a particular release is
authorized; use protected release approvals and explicit invocation.

Sources: [official authentication guidance](https://github.com/modelcontextprotocol/registry/blob/v1.8.1/docs/modelcontextprotocol-io/authentication.mdx),
[official GitHub Actions guide](https://github.com/modelcontextprotocol/registry/blob/v1.8.1/docs/modelcontextprotocol-io/github-actions.mdx),
[publisher implementation](https://github.com/modelcontextprotocol/registry/tree/v1.8.1/cmd/publisher).
