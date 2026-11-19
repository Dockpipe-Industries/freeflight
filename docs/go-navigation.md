# Go navigation and the next language

## Implementation

FreeFlight uses one persistent gopls stdio session per selected Go workspace.
The small Node worker translates FreeFlight's existing calls into standard LSP and
reduces LSP responses to workspace-relative file, line and character. Using the
gopls CLI would start a session for each query. Embedding lower-level Go compiler
libraries would make FreeFlight responsible for package loading, indexing and
invalidation. [gopls navigation](https://go.dev/gopls/features/navigation)

The TypeScript and JavaScript entries share the official TypeScript Language
Service worker. Roslyn has its own native .NET worker with safe-source and
startup-trusted MSBuild modes. All three use the C++ server for routing,
authorization, discovery, cancellation and process cleanup. Go uses the same
boundary and adds no public MCP tool. The initial implementation is opt-in
and locally qualified on Linux. [Go worker setup](../workers/go/README.md)

## DockPipe tasks

Tested on DockPipe `dfec510b4c38f81f1ce4784ca44446def30bb453`. The checkout
had unrelated local work. The three navigation sources, the application test and
the Go module/workspace manifests matched the named revision. Reference asks
select the application package subtree and include tests. Lines below start at
one. MCP uses zero-based UTF-16.

| Task | Exact expected locations |
| --- | --- |
| Look up the function named `DurableStateRoot` | `src/lib/infrastructure/durable_state.go:55` |
| Resolve `DurableStateRoot` from its application call at line 280 | `src/lib/infrastructure/durable_state.go:55` |
| Find application references to `DurableStateRoot` | `src/lib/application/project_build_cmd.go:280,365` and `src/lib/application/project_build_cmd_test.go:199,261` |
| Resolve `ValidateDisposableRemovalPath` from its application call at line 134 | `src/lib/infrastructure/removal_safety.go:20` |
| Find application references to `ValidateDisposableRemovalPath` | `src/lib/application/project_build_cmd.go:134,155` |

The MCP fixture additionally checks an aliased import, a same-name declaration
in the consumer package, same-line emoji and exact UTF-16 offsets, declaration inclusion,
truncation, on-disk refresh, close/reopen, external targets and symlinks, missing
backend and failed workspace indexing. The DockPipe tests validate both reference
sets and check that the inspected Go source and module/workspace metadata remain
byte-identical after navigation.

## Tool measurements

Linux x86-64, Node 24.11.1, Go 1.26.10, gopls 0.23.0 and ripgrep 13.
The fixed FreeFlight script sent one query per task and checked all five exact
answer sets. The lexical script ran the corresponding Go-only `rg` searches and
bounded `sed` reads to inspect declaration, call and import context. Counts use
`o200k_base` on tool payloads. MCP capabilities and transport framing, shell
headers and the agent prompt are excluded. The first FreeFlight query includes
startup and indexing. The offline module cache and OS page cache were retained.

| Fixed tool run | Calls | Payload tokens | Five-task wall time |
| --- | ---: | ---: | ---: |
| FreeFlight, fresh worker and empty Go/gopls caches | 5 | 610 | 2,501 ms (one run) |
| FreeFlight, fresh worker and reused disk caches | 5 | 610 | 1,466 ms median (four runs) |
| FreeFlight, warm worker | 5 | 610 | 563 ms median (five runs) |
| Search and reads, first pass | 13 | 1,232 | 44 ms median (five runs) |
| Search and reads, repeat pass | 13 | 1,232 | 43 ms median (five runs) |

FreeFlight returned 50.5% fewer payload tokens and required eight fewer tool
calls in this scripted comparison. Search was faster at the tool boundary.
The Go reference queries returned workspace-wide results and the scorer
selected answers in the requested application subtree. The first symbol lookup
returned fuzzy candidates and was larger than the exact lexical search for that
task.

## Same-model agent benchmark

Both arms ran offline on the same Qwen3-4B Q4_K_M weights with llama.cpp b10437
and deterministic decoding. Each task started a new conversation, used the same
question and returned an exact JSON array of one-based `file:line` citations.
The arms alternated order across tasks. The search arm could use bounded
ripgrep and line reads. It chose one search for each task.

The main run presented both arms with one-based positions. The FreeFlight
harness converted arguments to its native zero-based UTF-16 contract and rendered
returned positions as citations. It filtered reference locations to the
requested subtree before presenting them. The fixed measurements above used the
native API payloads. [Qwen model and weight checksum](https://huggingface.co/Qwen/Qwen3-4B-GGUF/blob/bc64014/Qwen3-4B-Q4_K_M.gguf)

| Metric across five tasks | FreeFlight | Search and reads available |
| --- | ---: | ---: |
| Exact answer sets | 5/5 | 2/5 |
| Agent tool calls | 5 | 5 |
| Tool payload tokens in Qwen's tokenizer | 325 | 637 |
| Model prompt tokens | 5,129 | 4,731 |
| Model completion tokens | 293 | 321 |
| Total model tokens | 5,422 | 5,052 |
| End-to-end time, summed across tasks | 85.2 s | 86.2 s |

Search found the two named definitions' call sites and returned them as answers.
In the second reference task its citations included source text and failed the
exact output contract. FreeFlight returned 49.0% fewer tool payload tokens in
the agent run. Total model tokens were 7.3% higher, including prompts, tool
schemas, repeated conversation context and completions. These end-to-end times
come from one paired run per task on a shared local model process. The fixed
tool measurements isolate the cold and warm navigation timings.

A preliminary run exposed the worker's native zero-based result and input
fields directly to the same model. FreeFlight scored 0/5 and search scored 2/5.
The semantic failures included wrong position conversion, off-by-one citations
and answering outside the requested reference scope. The main run measures the
effect of the normalized agent presentation, which is separate from the native
MCP contract.

Local receipts are under `bin/.local/go/benchmark` in the FreeFlight checkout.
`tool-results.json` holds fixed runs. `offline-agent-results.jsonl` and
`offline-agent-normalized-results.jsonl` hold the per-task agent results.

### Codex CLI run

The same five questions were also run through Codex CLI 0.144.1 in two
ephemeral turns, one per arm. Both used the same local Qwen3-4B weights through
llama.cpp and a private Responses adapter. The CLI and model ran in a network
namespace with loopback as its only interface. Automatic review declined the
hosted GPT run because the lexical arm sends real Go excerpts to its model.
The offline run kept those excerpts on the machine.

| Metric across five tasks | FreeFlight | Search and reads available |
| --- | ---: | ---: |
| Exact answer sets | 2/5 | 0/5 |
| Agent navigation tool calls | 5 | 5 |
| Tool payload tokens, `o200k_base` estimate | 150 | 1,262 |
| Total model tokens reported by Codex | 3,984 | 5,284 |
| Wall time, one CLI turn | 92.2 s | 153.7 s |

The agent used search only in the lexical arm and returned empty citation lists.
The semantic arm found exact locations but mixed up three task labels. This is
one small local model run through Codex with all questions in one turn. The
independent per-task Qwen run and direct MCP correctness checks give separate
evidence. Local receipts use the `codex-*` prefix in the benchmark directory.

## Go performance follow-up

The first worker queried disk-backed files without keeping any LSP documents
open. gopls retains typed package state for open files. FreeFlight now holds at
most four documents, refreshes their bounded bytes before queries, and lets
gopls invalidate its own package graph from file events. This reuses backend
semantic state without caching answers. Module preflight uses the already
configured offline Go executable to make unsupported-toolchain failures
deterministic.

The paired benchmark alternated the original worker and candidate order across
six sessions per arm and verified exact answers every time. Each new worker
ran a first pass followed by four warm passes. The two arms had separate
persistent Go/gopls caches. The first pass median spans the initial cache fill
and subsequent sessions that reuse their arm's disk cache. This is a
five-task latency measure in a real workspace.

| Configuration | First pass median | Warm median | Payload tokens |
| --- | ---: | ---: | ---: |
| Original worker, default output | 1,068 ms | 495 ms | 610 |
| Optimized worker, default output | 1,181 ms | 33.4 ms | 610 |
| Optimized worker, exact/scoped citations | — | 51.2 ms (six additional passes) | 151 |

Warm passes with the original output contract were about 15× faster. Median
warm definitions took 1.7–2.1 ms and reference queries took 8.5–9.2 ms. The
first pass remained about 11% slower. Compact mode cuts payload tokens by
75.2% using exact symbol lookup, reference scoping and one-based file-line
citations. Columns remain available in the default format. The benchmark
receipt is `bin/.local/go/benchmark/go-performance.json`.

The Go worker uses the C# engine's principle of reusing language-owned
semantic state and refreshing bounded input bytes before querying it. The
fixtures and project graphs for the two runtimes differ, so these measurements
establish Go's improvement on DockPipe.

## Follow-up language assessment

**PipeLang was the strongest next addition, starting with an explicitly selected
ordinary-model import closure.** Go supports the value of compact bound locations for agents
and shows why the next adapter needs a reusable workspace session. PipeLang
already has a working headless editor server and a direct DockPipe use case.
Its current scope is useful while project-wide coverage evolves. The follow-up
also adds opt-in Python and C++ navigation. Startup requirements are in the
[language-server worker guide](../workers/lsp/README.md).

| Language | Available backend | First integration work |
| --- | --- | --- |
| PipeLang | The owning compiler's versioned JSON index and analysis, plus its existing Node stdio LSP server | Use a pinned installed `pipelang-modelc`, explicit authorized source roots and a declared entry document. Report closure-scoped symbol and reference coverage. |
| Python | Pyright's Node language server implements workspace symbols, definitions and references | Prove cross-package identity through aliasing, relative imports and namespace packages. Supply controlled interpreter and stub roots. Pyright can invoke an interpreter to discover import paths, so repository configuration must have no executable authority. [Pyright LSP handlers](https://github.com/microsoft/pyright/blob/main/packages/pyright-internal/src/languageServerBase.ts), [import resolution](https://github.com/microsoft/pyright/blob/main/docs/import-resolution.md) |
| C++ | clangd uses LSP and background cross-reference indexing | Establish a pre-existing operator-approved compilation database, generated headers and explicit index readiness. Keep compiler probing off initially. Check macros, templates and overlapping build configurations against a real checkout. [clangd indexing](https://clangd.llvm.org/design/indexing), [compile commands](https://clangd.llvm.org/design/compile-commands) |

### What PipeLang already exposes

The owning repository is `pipelang`, inspected at
`751cd96b3741b4af6240ce521518ecf5f89ae93c`. The installed PipeLang Model SDK
exports runtime headers and a CMake runtime target, and installs
`pipelang-modelc`. It exposes the semantic compiler through the versioned
process contract. The internal static compiler library is outside the installed
SDK export. See `sdk/pipeview/model/CMakeLists.txt`,
`src/native/model-compiler/main.cpp`, and
`src/native/model-compiler/SemanticAnalysis.cpp` in the owning repository.

- `pipelang.native-model-index.v1` accepts explicit source fragments and returns
  module names and imports per fragment. It can select the entry's transitive
  import closure while preserving all fragments of split modules.
- `pipelang.native-model-analysis.v1` binds the selected source graph. It returns
  symbols, types, methods, calls, definition joins and diagnostics. Locations carry
  source-fragment paths with UTF-8 byte offsets and lengths. Local bindings use
  declaration paths and offsets, while checked calls carry method identities and
  source anchors across specialization variants.
- The existing headless editor server translates those offsets to UTF-16 and
  exposes LSP definition, references and workspace symbols. Its workspace symbols
  cover open documents and their explicit import closures. References cover
  locals, parameters and supported source methods. FreeFlight can consume those
  existing operations today through a pinned server and compiler. See
  `tooling/vscode-extensions/pipelang-language-support/{README.md,compiler-service.js,language-server.js,semantic-features.js}`.

### What to add upstream

For workspace-wide use, PipeLang needs a supported project snapshot operation
that takes verified project and source-library descriptors, enumerates an
authorized module graph, tracks dependencies and invalidates affected snapshots.
Its query contract should publish stable declaration identities, exact spans,
bounded symbol/reference results and coverage information for partial or invalid
graphs. Reverse references across sibling importing modules and broader
type/field reference coverage need their own compiler evidence. Keep module
resolution and identity ownership upstream. Publish the headless semantic server
or an equivalent versioned semantic executable with the SDK so FreeFlight can
select and qualify an installed artifact.

### Proposed PipeLang benchmark

Use DockPipe's `workflows/test/sdk-pipelang/config.yml` and its real harness entry
`workflows/test/sdk-pipelang/assets/harness/src/Entry.pipe`. Select
`Dockpipe.SDK.Proof` and the `Dockpipe.SDK` source library declared by the harness.
Resolve `client.Scope` from `Entry.pipe:13` into
`src/lib/sdkassets/pipelang/src/Client.pipe:42`. Find the six calls in
`Entry.pipe:13,29,37,46,130,134`, with and without the declaration. Search for
the qualified method and distinguish it from `StartScope`, `ScopeRequest` and
the transport callbacks.

A local preflight through the existing PipeLang LSP and an installed SDK compiler
returned that definition and all six calls with zero diagnostics. The FreeFlight
PipeLang MCP follow-up independently passed those same cross-module results.
Use the same model and answer format in the future
semantic and lexical arms, and record exact locations, tool calls, payload and
model tokens, fresh and warm latency. Once workspace-wide indexing exists, open
the library declaration and require discovery of callers in a separate importing
workflow module without opening that caller file first.
