# Standalone distribution

FreeFlight's complete standalone bundle contains a C++ server, a supplied Node
runtime and TypeScript Language Service worker, and a self-contained Roslyn worker.
Default safe-source analysis requires no separately installed DockPipe, Node or .NET runtime. The optional, explicitly authorized trusted-MSBuild mode needs an operator-installed compatible .NET SDK; a complete SDK is not bundled. See [capabilities and trust boundaries](capabilities.md).

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
| `FREEFLIGHT_NODE_VERSION` | Exact expected `node --version` output, for example `v24.22.0`. |
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
lib/freeflight/roslyn/BuildHost-netcore/ # optional trusted-mode host; SDK not bundled
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

The workflow also produces an MCP Bundle in the [official ZIP-based format](https://github.com/anthropics/mcpb/blob/2a788100a60db19a6b1c018fb1cf84ae85de9537/README.md). It uses Python's standard-library `zipfile` and validates manifest 0.3 against the unmodified official schema pinned by source commit and SHA-256 under `workflows/package.native/assets/schema/`. The schema and upstream validation fixtures retain their MIT license. The development environment needs the existing pinned `jsonschema` 4.25.1 dependency; no npm packaging tool is installed or shipped.

The [official manifest specification](https://github.com/anthropics/mcpb/blob/2a788100a60db19a6b1c018fb1cf84ae85de9537/MANIFEST.md) provides `server.type: binary`, `${__dirname}` installation paths and a required workspace directory picker. FreeFlight uses the same `bin/freeflight --workspace` command and native file layout. This is an alternate archive of one product, not a custom distribution format.

The workflow tests the vendored official valid/invalid examples, then writes all bundle files including TypeScript `.d.ts` semantic inputs. ZIP entries preserve Unix executable modes. Every archived file must match its staged original byte for byte, and a fresh extraction must pass the installed semantic checks using its own binaries and runtimes. Installation, workspace and extraction paths deliberately contain spaces and non-ASCII characters. No archive is retained if these checks fail. The bundle is unsigned. Public Registry submission still requires separately verified asset URLs and publisher authorization.

Windows packaging also inspects the core executable's regular and delay-load PE
imports and rejects dynamic VC++ runtime dependencies (`VCRUNTIME`, `MSVCP`,
`CONCRT`, `VCOMP`). The workflow-local standard-library parser follows the
[Microsoft PE specification](https://learn.microsoft.com/en-us/windows/win32/debug/pe-format)
and avoids a dependency on Visual Studio diagnostic tools in the runner PATH.
It fails closed on malformed or unsupported import tables and records the direct
DLL names in `verification.json`. This verifies the native C++ core's static CRT
configuration; it does not claim Node/.NET or transitive DLL dependencies are static.

The build-only official MCPB CLI dependency was removed because the latest reviewed CLI 2.1.2 includes unpatched `node-forge` high-severity vulnerability [GHSA-86w9-cpqp-85rv](https://github.com/advisories/GHSA-86w9-cpqp-85rv). This removes the unused dependency graph rather than suppressing its audit. The high audit threshold remains unchanged; historical CLI-based receipts below describe earlier artifacts only.

MCPB 0.3 declares operating systems but has no dedicated CPU architecture field.
The artifact filename and description state the exact RID; release discovery and
installers must select the matching architecture. This is not a universal macOS
binary. The local extraction test is not a claim that every MCPB desktop client has
been tested. The general DockPipe Registry integration must consume this standalone
distribution rather than publishing a duplicate FreeFlight store package.

## Historical local qualification — 2026-10-19 (before trusted mode)

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

These artifacts predate this qualification note and the trusted-MSBuild dependency update. They do not represent the current worker snapshot. Other platform artifacts, desktop
host installation, signing and public Registry submission remain unverified.

## Current local server qualification — 2026-10-19

The expanded 12-operation Roslyn worker, optional trusted-MSBuild loader and core
discovery fix passed `package.native` with checksum-verified official Node 24.22.0.
Evidence: `bin/.local/package-native-final.log`. Eight installed core protocol tests,
expanded native Roslyn safe-source suite, SDK-backed native trusted-project suite,
exact installed C#/TS/JS assertions and official MCPB validation passed. All 610
MCPB files matched the native bundle; fresh extraction preserved executable modes
and passed semantic checks. The TypeScript suite separately passed 17/17 under
Node 24.22.0 (`bin/.local/package-typescript-node24.22.log`).

- `freeflight-osx-arm64-d1bec6d953f07329.tar.gz`: SHA-256 `d0d00ed5ba7514c22c62630436f4e831f1c17ac16880aba5d55b9307c2d7afbe`
- `freeflight-osx-arm64-aee01a80832a71aa.mcpb`: SHA-256 `aee01a80832a71aa011f5f8803dcf1e723ccc5cd9c5f509b30ebdf32f64e612f`

The official Node archive checksum was
`6a9724d9b50a5f22b4816cded441b5a8d9ddae546191a5e5b7efa5a5e2ee26d5`
for `node-v24.22.0-darwin-arm64.tar.gz`, verified before extraction against the
vendor's versioned `SHASUMS256.txt`. Trusted native testing used an explicitly
installed SDK; the bundled default remains safe-source and SDK-independent.
These are local unsigned server artifacts, not a production release or deployed
website. They predate this note and the Qt website adaptation.
