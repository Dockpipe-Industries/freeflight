# FreeFlight

**Code intelligence. No subscriptions. No nonsense.**

FreeFlight is an independent Apache-2.0 language intelligence server from
[Dockpipe Industries Inc.](https://github.com/Dockpipe-Industries). One C++23 MCP
endpoint routes authorized workspaces to internal Roslyn and official TypeScript
Language Service workers. No account, subscription or source telemetry.

Release availability, checksums and qualified platforms are recorded in
[GitHub Releases](https://github.com/Dockpipe-Industries/freeflight/releases).
All required gates must pass on the same candidate before production release.
Use [current CI](https://github.com/Dockpipe-Industries/freeflight/actions/workflows/ci.yml),
[platform and artifact evidence](docs/distribution.md), and the
[acceptance checklist](docs/acceptance.md) to check a checkout's qualification status.
Install using the published artifact's checksum and platform record.

## Development

Provision DockPipe, CMake 3.25+, a C++23 compiler, Node 24.22.0, .NET SDK 10.0.402,
and Python 3.9+. From this checkout:

```sh
dockpipe --workflow build
dockpipe --workflow test
dockpipe --workflow repo.check
dockpipe --workflow site.build
```

DockPipe is the development entry point; it is not a dependency of the standalone
server. Workflows live under `workflows/<name>/config.yml`; generated output lives
under `bin/.local/`. Native toolchain instructions and configuration are in
[the documentation](docs/README.md).

## Run

For a verified complete native bundle:

```sh
/absolute/freeflight/bin/freeflight --workspace /absolute/project
```

Development builds use `--config /absolute/freeflight.json` to select explicitly
trusted worker executables. Only roots authorized at startup can be opened.
Do not treat a configured worker as sandboxed: it runs with the user's OS identity.

No public release or registry listing is claimed until its artifact is published
and verified. DockPipe Registry integration is separate work; there is no duplicate
FreeFlight-specific package-store distribution.

## Capabilities

| Operation | C# safe-source | TypeScript / JavaScript |
| --- | --- | --- |
| Symbols, definitions, references, hover | Implemented, fixture-tested | Implemented, fixture-tested |
| Compiler diagnostics and incremental changes | Implemented, fixture-tested | Implemented, fixture-tested |
| Rename preview with file hashes | Implemented, fixture-tested | Implemented, fixture-tested |
| Signature help | Invocation signatures, fixture-tested | Implemented, fixture-tested |
| Import organization and code-action previews | Not supported | Implemented, fixture-tested |
| Project dependencies | Explicit trusted MSBuild mode; SDK required | Configured/inferred projects; see worker limitations |

Workers report their actual operation lists through `engine.capabilities`.
`semantic.query` invokes those operations; `workspace.discover` lists authorized
roots and projects. Position coordinates are zero-based UTF-16. No mutation is
applied to source files. Dedicated JavaScript coverage is narrower than TypeScript;
consult the [capability matrix](docs/capabilities.md) for exact scope. Optional
trusted MSBuild mode can execute repository code and requires explicit startup
authorization. Analyzer execution and large-repository scale are not qualified.
Code signing and notarization are not currently provided.

Read [security](SECURITY.md), [contributing](CONTRIBUTING.md), and
[release gates](docs/acceptance.md) before extending or distributing FreeFlight.
