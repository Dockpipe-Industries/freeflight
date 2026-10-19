# Additional language engines: evaluation, not support

Evaluated 2026-10-19 against public upstream documentation and manifests. None of
these adapters is implemented, packaged, qualified, or advertised by FreeFlight.
Versions observed on upstream development branches are not release selections.

| Language | Candidate and license | Runtime and distribution implications |
| --- | --- | --- |
| Python | [Pyright](https://github.com/microsoft/pyright), MIT | Official npm package exposes `pyright-langserver`; its current manifest requires Node >=14. Reuse the bundled Node runtime after compatibility tests. Include typeshed/dependency notices; interpreter/environment discovery needs a controlled policy. |
| Go | [gopls](https://go.dev/gopls/), [BSD-3-Clause](https://github.com/golang/tools/blob/master/LICENSE) | Native Go executable; upstream documents `go install golang.org/x/tools/gopls@latest`. FreeFlight must instead pin and build/package per platform, with the required Go toolchain and module environment. Do not make source installation the end-user experience. |
| Rust | [rust-analyzer](https://rust-analyzer.github.io/book/installation.html), [MIT OR Apache-2.0](https://github.com/rust-lang/rust-analyzer/blob/master/Cargo.toml) | Native upstream binaries or rustup component; meaningful Cargo analysis also needs matching Rust tooling and standard-library sources. Pin compatible versions and retain notices. |
| C/C++ | [clangd](https://clangd.llvm.org/installation), [Apache-2.0 WITH LLVM-exception](https://github.com/llvm/llvm-project/blob/main/llvm/LICENSE.TXT) | Native binaries; package resource headers and required runtime libraries. Existing `compile_commands.json` supplies build flags; opening a project must not automatically run its build to generate one. |
| Java | [Eclipse JDT LS](https://github.com/eclipse-jdtls/eclipse.jdt.ls), EPL-2.0 | Upstream requires Java 21 minimum. Ship a qualified JRE/JDK and server distribution with separate license inventories. EPL-covered components retain their license and applicable source-availability obligations; do not relabel them Apache-2.0. Inspect every bundled Eclipse/Maven/Gradle dependency before redistribution. |
| HTML/CSS | Microsoft [HTML](https://github.com/microsoft/vscode-html-languageservice) and [CSS](https://github.com/microsoft/vscode-css-languageservice) language services, MIT | Node libraries, not standalone LSP executables. A small internal worker can call these existing services without writing parsers. Alternatively qualify their upstream VS Code language-server hosts and associated packaging separately. |
| JSON/YAML | Microsoft [JSON language service](https://github.com/microsoft/vscode-json-languageservice), MIT; Red Hat [YAML language server](https://github.com/redhat-developer/yaml-language-server), MIT | JSON is a Node library; YAML publishes `yaml-language-server`. Inspected YAML manifest requires Node >=22.13.0. Pin released packages and schema inputs; remote schema fetching must be opt-in. |

**Pyright is not Pylance.** The [Pylance repository](https://github.com/microsoft/pylance-release)
is documentation/feedback for a non-open-source product. Its repository documentation
license does not license the extension implementation for FreeFlight distribution.
Use the public Pyright server and measure its actual capabilities; never promise
Pylance feature parity or bundle the Pylance extension.

## Trust and qualification gates

An LSP process boundary is not a sandbox. Before enabling an adapter, inspect and
disable automatic repository execution and network access where feasible. Rust
[configuration](https://rust-analyzer.github.io/book/configuration.html) includes
build scripts, procedural macros and check commands: these require explicit trust,
not merely workspace-open consent. Java build import/plugins and Go toolchain/module
operations also require evaluation. For clangd, restrict
[query-driver](https://clangd.llvm.org/config#compiler) executable allowlists and
untrusted compilation flags/configuration. Do not load arbitrary local binaries,
plugins or commands from repository settings. Inert modes may have reduced accuracy;
report that limitation rather than silently escalating trust.

Implement one internal stdio LSP adapter with Content-Length framing, bounded
messages, lifecycle supervision, cancellation, document versions, workspace routing
and capability negotiation. This is protocol adaptation, not a networking framework.
Map only tested server operations into the existing MCP contract. Server-initiated
edits and commands must pass the same explicit-invocation, root-boundary and
concurrent-change checks as native workers. Test real semantic results, Unicode
position encodings, crash recovery and malicious project configuration before
shipping any engine. Lock all binaries, runtime dependencies, licenses and checksums
within the same FreeFlight distribution; no separate user-facing MCP setup.

Suggested order: Pyright and clangd first, then the small web-language services,
followed by gopls, rust-analyzer and JDT LS after their build-execution boundaries
and complete runtime packaging are qualified. This is a recommendation, not a
committed release scope.

## Future Pipelang integration

Public DockPipe references describe a
[versioned compiler semantic projection](https://github.com/Dockpipe-Industries/dockpipe/blob/master/docs/agents/tasks/pipelang-reactive-application-language/compiler-contract.md)
and a [Qt boundary](https://github.com/Dockpipe-Industries/dockpipe/blob/master/docs/concepts/pipelang-qt-boundary.md).
The prospective adapter should consume public, versioned semantic IDs, spans,
diagnostics and query results through an optional native C++ engine registration.
Keep compiler data layouts and Qt presentation internals outside FreeFlight's
contract. No stable public editor SDK/native ABI was established by this inspection;
therefore no Pipelang dependency or support claim is added. Analysis must remain
inert, and no compiler/resolver rewrite is proposed.
