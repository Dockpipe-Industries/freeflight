# Standalone distribution

FreeFlight's complete standalone bundle contains a C++ server, a supplied Node
runtime and TypeScript Language Service worker, and a self-contained Roslyn worker.
End users do not need DockPipe, Node or .NET installed separately.

No public release or production package is implied by these workflow definitions.
A release candidate must pass its native installed-bundle checks on each advertised
platform. Only the core executable is produced by the current bare CPack target;
that output is not a complete standalone release.

## Native packaging through DockPipe

First use the repository's DockPipe build/test workflows. Provision the official
Node archive for the target platform yourself, verify its published checksum before
extraction, and explicitly supply its extracted directory. No package workflow
fetches runtimes or executes a downloaded installer automatically.

Set these environment variables before `dockpipe --workflow package.native`:

| Variable | Meaning |
| --- | --- |
| `FREEFLIGHT_RID` | Explicit native RID: `osx-arm64`, `osx-x64`, `linux-x64`, `linux-arm64`, `win-x64` or `win-arm64`; must match the running host. |
| `NODE_DISTRIBUTION_ROOT` | Absolute path to the verified extracted official Node distribution; includes `LICENSE` and `bin/node` (or `node.exe` on Windows). |
| `FREEFLIGHT_NODE_VERSION` | Exact expected `node --version` output, for example `v24.11.1`. |
| `DOTNET_LICENSE_ROOT` | Absolute path to the provisioned .NET distribution containing `LICENSE.txt` and `ThirdPartyNotices.txt`. |
| `NUGET_PACKAGES` | Absolute path to restored NuGet packages, containing the exact versions in the Roslyn lockfile. |

CMake, Python 3, the .NET SDK and DockPipe must be on `PATH`. The C++ Release build
must be available at `bin/.local/build`; the TypeScript staging directory must have
`bin/.local/typescript/worker.mjs` and its pinned `node_modules/typescript` dependency.
The RID-specific locked restore must already be satisfiable. If .NET rejects the
lockfile for that RID, explicitly update and review the lockfile using the native
SDK, then repeat validation; packaging does not silently rewrite dependency locks.

The minimal Python asset under `workflows/package.native/assets/` exists because
cross-platform layout assembly, license collection and installed MCP semantic
verification are project-specific operations. DockPipe owns its invocation; there
is no parallel task runner, shell wrapper or npm script. It performs CMake install,
self-contained `dotnet publish`, copies only the required Node runtime and
TypeScript service, and collects redistribution notices. It rejects missing inputs,
unknown host/RID pairs and unreviewed symlinks in copied dependency trees.

## Installed layout and launch

```text
bin/freeflight[.exe]
lib/freeflight/node/bin/node           # Unix
lib/freeflight/node/node.exe           # Windows
lib/freeflight/typescript/worker.mjs
lib/freeflight/typescript/node_modules/typescript/
lib/freeflight/roslyn/FreeFlight.Roslyn[.exe]
lib/freeflight/roslyn/...              # self-contained .NET dependencies
share/freeflight/licenses/
verification.json
SHA256SUMS
```

After extracting a verified archive, launch the bundled executable with:

```text
/absolute/install/bin/freeflight --workspace /absolute/workspace
```

This authorizes that workspace and discovers the supplied workers relative to the
installation. MCP clients use that executable as `command` and the two elements
`--workspace`, `/absolute/workspace` as `args`. Use native absolute Windows paths
and the `.exe` executable on Windows. A source development setup may instead use
`--config`; release users should not need to configure independent workers.

## Verification and artifacts

Before producing an archive, the workflow runs the protocol test suite against the
installed executable. It then starts that executable using only `--workspace` and
checks exact TypeScript diagnostic `2322`, the JavaScript `increment` symbol,
Roslyn diagnostic `CS0029`, the C# `Widget` symbol and graceful shutdown. These
checks exercise actual bundled runtime discovery, not external worker commands.
Each request has a timeout. A failed gate produces no release archive.

The bundle includes `verification.json` and per-file SHA-256 checksums. A tar.gz
archive and its checksum are emitted under ignored `bin/.local/packages/`. Archive
names include a content digest; existing outputs are never overwritten. Assembly
uses a newly created temporary directory and cleans only that directory. Archives
are not claimed bit-reproducible: native toolchains and gzip/tar metadata still
need reproducibility work. Host-independent cross-compilation cannot substitute
for execution checks on the actual target platform.

Signing, notarization, installer formats, official MCP Registry publication, gateway
validation and GitHub Releases promotion are separate release gates. The workflow
does not publish anything. No domain, hosting credential or new registry is used.

## MCPB from the same native application

The workflow also produces an MCP Bundle using the official
[`@anthropic-ai/mcpb` tooling](https://github.com/modelcontextprotocol/mcpb), pinned
to 2.1.2 in the workflow-local npm lockfile. Tool installation uses `npm ci
--ignore-scripts` under `bin/.local/mcpb-tools`; these are build-time tools, never
application dependencies. The official Node distribution must retain its npm CLI
for this packaging step. Native CLI users still do not need npm.

The [official manifest specification](https://github.com/modelcontextprotocol/mcpb/blob/main/MANIFEST.md)
provides `server.type: binary`, `${__dirname}` installation paths and a required
workspace directory picker. FreeFlight uses manifest version 0.3 and the same
`bin/freeflight --workspace` command. The original native file layout and licenses
are preserved; this is an alternate archive format of one product.

The official CLI validates and packs the manifest. A workflow-generated `.mcpbignore` explicitly includes TypeScript `.d.ts` files, which the official packer otherwise excludes despite their being runtime semantic input. The workflow then verifies
that every archived file matches the native bundle byte for byte, extracts it into
a fresh directory, checks executable permissions and reruns the installed semantic
checks. Missing/excluded files or changed hashes fail qualification. The bundle
is unsigned; no signing keys or credentials are generated. Official Registry
publication remains a separate authenticated action, permitted only with verified
artifact URLs and matching checksums.

MCPB 0.3 declares operating systems but has no dedicated CPU architecture field.
The artifact filename and description state the exact RID; release discovery and
installers must select the matching architecture. This is not a universal macOS
binary. The local extraction test is not a claim that every MCPB desktop client has
been tested. The general DockPipe Registry integration must consume this standalone
distribution rather than publishing a duplicate FreeFlight store package.

## Local qualification — 2026-10-19

`dockpipe --workflow package.native` passed on macOS ARM64 with Node v24.11.1
and .NET SDK 10.0.402. Evidence: `bin/.local/package-native.log` (generated, ignored).
The installed executable passed seven protocol tests; the installed worker paths
passed the exact C#/TypeScript/JavaScript semantic assertions above; the native
Roslyn suite additionally verified preview hashes, refresh, boundaries, no-MSBuild,
malformed input and cancellation. Official MCPB schema validation passed. All 455
MCPB files matched their staged originals, and a fresh extraction passed semantic
checks using its own executable and worker runtimes.

Local artifacts, not published releases:

- `freeflight-osx-arm64-bdb3e394239f625a.tar.gz`: SHA-256 `33d2ea127049d3d39035eaa4a1ab22d80c4be59f9d88e13200693b655ed55eff`
- `freeflight-osx-arm64-eb5057c9ec156aa2.mcpb`: SHA-256 `eb5057c9ec156aa27980275c2503b95e9a483eb091cf82e357849e6cb7927fb7`

These artifacts predate this qualification note. Other platform artifacts, desktop
host installation, signing and public Registry submission remain unverified.
