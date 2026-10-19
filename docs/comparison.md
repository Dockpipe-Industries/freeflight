# Public capability comparison

Reviewed public publisher documentation on 2026-10-19; no proprietary implementation
was inspected. This is a prioritization guide, not a parity or performance claim.

| Area | Public Glider / TGlider documentation | FreeFlight preview |
| --- | --- | --- |
| C# semantic navigation | Glider documents navigation, diagnostics and refactoring | Safe-source Roslyn fixtures pass; full project fidelity pending |
| TS/JS navigation | TGlider documents project-aware navigation, references and implementations | Official TS service navigation fixtures pass |
| Diagnostics | Both document analysis/diagnostics | Compiler diagnostics; repository analyzers intentionally disabled |
| Rename/editing | TGlider documents preview/live document/save operations | Preview edits only; source is not modified |
| Hierarchies/callers | TGlider documents hierarchy/caller tools | See actual worker capabilities; no blanket parity claim |
| Transport | TGlider documents stdio and Streamable HTTP | stdio; HTTP pending |
| Distribution | Language products documented separately | One C++ server and internal workers; release verification pending |
| Licensing | Public support resources do not establish product source licensing | FreeFlight source Apache-2.0 |

Sources: [Glider](https://glidermcp.com/glider),
[TGlider](https://glidermcp.com/tglider),
[compatibility](https://glidermcp.com/tglider/compatibility),
[tool documentation](https://glidermcp.com/tglider/installation).
