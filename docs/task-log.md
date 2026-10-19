# Execution log

## 2026-10-19

- Created isolated workspace; active DockPipe, Nucleon and Biztraak worktrees untouched.
- Verified organization via GitHub repository metadata. Created public freeflight,
  Apache-2.0 initial commit, four required branches and master default.
- Inspected actual Cloud workflow organization, repo.check and pinned CI toolchain.
- Found installed DockPipe 0.6.14; provisioned isolated official native toolchains.
- Current DockPipe manifest has no typed general MCP gateway contract. `kind: mcp`
  alone is insufficient proof of installation/federation. Integration remains pending.
- No protection changes, credentials generated, production release or deployment.

### Instruction prerequisite and requested tool upgrade

Implementation/builds paused immediately when the prerequisite arrived; existing
code preserved. Inspected actual Cloud router/task schemas and current extracted
DorkPipe 0.6.5 package at c284f043 (older embedded package was 0.6.2). example.brain
only seeds four brain docs and still declares windows/deb with Docker/providers;
software.dev selects task packs rather than generating the full router.
Reused schema-1 routes, schema-2 open task index, four baseline brain roles and
scoped AGENTS instructions, covering all current amendments. No duplicate package.

Homebrew refresh and specifically authorized DockPipe-only upgrade completed to
0.6.20-staging.39285769512.1.0399bb37bb7d. Both CLI locations report 0.6.20.
`dockpipe workflow validate workflows/repo.check/config.yml` passed. Actual
`dockpipe --workflow repo.check` passed: required files/tracked hygiene, eight
routes and five open tasks. PyYAML 6.0.2 used from isolated validation environment.
Gate verified; see docs/toolchain-verification.md for pins and remaining CI distinction.

Pre-gate evidence: core/process CTest 2/2; TS baseline 10/10; Roslyn semantic,
malformed-input and cancellation checks; mixed C++ MCP-to-real-worker integration
passed. New TS extension edits subsequently had 13/15 tests and remain unqualified.
Native bundle stopped at NU1004 (osx-arm64 missing from locked NuGet graph).

### Subsequent qualification and branch correction

Resolved locked RID graphs; TS worker suite 17/17, Roslyn safe-source suite,
real-worker MCP integration and official MCP SDK client compatibility passed on
macOS ARM64. Native and MCPB bundles passed extracted semantic checks and archive
file/hash verification. These are local evidence, not a production release.

Published implementation d00f257f7df250839478b687b79a2db9ca47b250 to dev via the
existing authorized GitHub app after the local PAT rejected workflow-file pushes
for missing workflow scope. No credentials or access permissions were expanded.
Draft PR #1 is dev -> staging. Hosted CI revealed Xcode15 libc++ limitations,
Windows test header order, and a Linux JSON temporary lifetime defect. Fixes are
being qualified; local core/process CTest passed 2/2 after the lifetime fix.

Jamie's immediate correction moves ALL implementation to js/dev. Switched local
branch preserving edits and fast-forwarded remote js/dev to the existing dev
commit without rewriting either branch. Future changes use js/dev -> dev ->
staging -> master promotion PRs. The prior dev commit remains accurately recorded.
Read-only GitHub inspection found master/dev/staging protected=false, protection
endpoints returned 'Branch not protected', and inherited/repository rulesets list
was empty. No protection settings changed; proposed protections await action-time
approval.
