# Internal engine instructions

Read docs/agents/core/architecture.md, verification.md and SECURITY.md from root.
Native Roslyn and official TypeScript services own semantics. Advertise only
operations with passing exact-result tests. No repository plugin/generator/analyzer
execution. Safe source mode must be labeled as such; full solution claims require
project-aware tests. Positions are zero-based UTF-16. Preview edits include original
hashes and never write files. Preserve root checks and bounded caches/frames.
