# Release qualification

FreeFlight uses `js/dev → dev → staging → master`. Promote with reviewed pull
requests. `master` is the production/default branch. Keep the numeric `VERSION`
and release notes synchronized; a production promotion must describe its changes.
Do not publish a tag or artifact merely because a build succeeded.

## Current automation

`.github/workflows/ci.yml` invokes the repository's authoritative DockPipe tasks
for C++ compilation, protocol/process tests, both workers, MCP integration,
repository health, site generation and complete native/MCPB bundle verification. The matrix covers
Linux x64/ARM64, Windows x64 and macOS ARM64. These are configured targets; hosted
results, not the presence of YAML, establish support. GitHub-hosted compiler and
OS image revisions remain runner-managed; this is not a bit-reproducibility claim.

The manual **Qualified release** workflow validates exact successful hosted CI and
CodeQL evidence, promotion ancestry and complete prebuilt artifacts. Default mode
is read-only; explicitly selected publication has scoped ephemeral write permission.
See [release-automation.md](release-automation.md) for gates and external status.
CodeQL uses the same `core.build`
DockPipe task under manual C++ tracing. Dependabot tracks Actions, npm and NuGet
updates into `js/dev`; it does not replace vulnerability scanning.

## Pinned DockPipe bootstrap

The local composite action acquires the official
[DockPipe 0.6.20 staging candidate](https://github.com/Dockpipe-Industries/dockpipe/releases/tag/v0.6.20-staging.39285769512.1.0399bb37bb7d).
CLI platform archives and the compiled core archive are pinned by SHA-256 from
the release API. Every archive is checked before extraction. Core assets and the
CLI live in the runner's temporary directory; they are never committed.

CI compiles only FreeFlight workflow packages with
`dockpipe package compile workflows --from workflows`, then sets
`DOCKPIPE_COMPILE_DEPS=0`. This narrowly avoids the CLI's automatic source-core
recompilation, which otherwise requires a core authoring tree and invokes its
source build hook. It does not bypass FreeFlight task compilation or tests.
`DOCKPIPE_GLOBAL_ROOT` points at the isolated runner installation. The exact candidate CLI and core archive downloads passed checksum validation on
macOS ARM64. Workflow compilation, repo.check (8 routes/5 open tasks) and
registry.check passed using that isolated installation. Linux and Windows bootstrap passed hosted verification. The local smoke used Python 3.9
with manual archive validation; the composite action uses Python 3.13 extraction
filters in CI.

Node 24.22.0, .NET SDK 10.0.402 and CMake 3.31.6 are selected explicitly. Official
GitHub Actions use immutable commit references. Python uses its 3.13 release line; CI provisions PyYAML 6.0.2 for repository
routing checks and jsonschema 4.25.1 for Registry metadata checks.
The composite action contains only acquisition, checksum validation and DockPipe
initialization; project build/test logic stays in `workflows/`.

## Publication gates still open

A native CPack archive is a development candidate until installation tests prove
it contains both workers and their runtime dependencies. macOS ARM64 complete bundles have passed local installation/semantic tests;
updated bundles and all other platforms require exact-commit qualification.
Official MCP Registry publication, signing identity and production deployment
remain pending. Store/gateway
availability is not a prerequisite for the standalone product.

Before enabling publication: qualify the complete bundle on each advertised
platform; retain checksums, dependency/license inventory and installation smoke
results; pass protocol/semantic/security tests; verify a staging candidate; then
publish the same tested bytes to GitHub Releases. Official MCP Registry metadata
must reference a real supported artifact and use explicitly authorized publisher
authentication. No credentials or permanent access are created by these workflows.

## Official MCP Registry

`server.json` is draft metadata using the official
[2025-12-11 server schema](https://static.modelcontextprotocol.io/schemas/2025-12-11/server.schema.json).
`dockpipe --workflow registry.check` validates its schema and VERSION consistency.
It fetches a checksum-pinned schema into `bin/.local/registry`; Python jsonschema
4.25.1 is a development dependency provisioned in CI. Draft validation is not
publication readiness: no package is declared until an actual bundle is qualified.

The [official package types](https://modelcontextprotocol.io/registry/package-types)
include MCPB bundles hosted in GitHub Releases. This can retain one GitHub Release
artifact source without adding npm or a DockPipe store. A plain native tarball
must not be mislabeled MCPB. Build a real MCPB manifest/archive containing the
complete native server and worker runtimes; test installation and launch; then add
`registryType: mcpb`, its exact HTTPS release asset URL, `fileSha256` and stdio
transport to server.json. The URL must contain `mcp` (the `.mcpb` extension does).

Publisher authentication and namespace ownership must be verified through the
official publisher flow when the artifact exists. CI has no Registry publishing
token, login action or secret. Manual GitHub Release publication uses only the
existing ephemeral GitHub token. General DockPipe discovery/configuration contracts are reviewable in DockPipe
PR #168. Installation and gateway lifecycle remain separate platform work; no
duplicate FreeFlight store package is created.
