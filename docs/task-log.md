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

### Approved branch protection applied

Jamie explicitly approved protection of dev/staging/master with no mandatory
reviewer approval. Read actual check runs before setting requirements: four
`Qualify (...)` platform checks and `cpp` from GitHub Actions app 15368, plus
`CodeQL` from app 57789. Applied and read back each branch: required pull requests,
strict/up-to-date checks, resolved conversations, enforce_admins=true,
required_approving_review_count=0, allow_force_pushes=false, allow_deletions=false.
js/dev and other repositories were not modified. Settings succeeded; no credential
expansion was necessary.

### Native, real-project and release-tool hardening

Windows qualification exposed UTF-8 fixture encoding and native-path comparison
assumptions; corrected tests without relaxing semantic assertions. Subsequent
qualification is tracked per exact commit; no old pass qualifies new edits.

Actual FreeFlight.Roslyn.csproj qualification now passes through the C++ MCP
endpoint on macOS ARM64: exact definition, all six references, the expected hidden
CS8019 import diagnostic, injected CS0029 and incremental removal, original source
hashes unchanged. It uses an explicitly trusted disposable project copy. This is
one actual project, not evidence for large solutions. It exposed a macOS spawn
bug that closed stderr; explicit stderr inheritance now preserves startup warnings
while unrelated descriptors remain isolated. Core/process CTest passed 2/2.

Initial SDK output reported HTTPS development-certificate initialization. Read-only
checks found no matching localhost certificate in the default login keychain or
.NET certificate-store files, so creation remains unconfirmed. No trust/cleanup
action occurred. Test restores and worker environments now explicitly disable
certificate generation and first-time behavior.

Expanded auditing found unpatched high-severity dependencies in the official MCPB
CLI build-time graph. Removed that CLI dependency instead of weakening the audit.
Packaging uses the documented standard ZIP format, pinned official MCPB 0.3 schema
and upstream MIT notices. Five schema/archive tests, eight installed protocol tests,
native and extracted semantic checks passed. Dependency audit passed with zero
TypeScript/client findings and no NuGet findings. Local dirty-source receipts are
correctly ineligible for release promotion.

Added release.prepare and registry.publish policy validation. Registry publication
requires verified real asset URLs, exact tag/source identity, and existing explicit
authentication. No tag, production release or Registry listing has been published.

A transient Mac transport disconnect interrupted a read-only Git-status call.
Fresh pwd, Git status/log and process-list reads confirmed shell continuity; the
interrupted call did not mutate files or push commits. Existing receipts preserved.

The Qt Quick/WebAssembly site passes actual Chromium desktop/mobile rendering
and navigation with no console errors, for staging and production SEO modes.
Pinned Qt source archives, original notices and relink source are retained.
Container build/smoke is authored for hosted CI; no Docker daemon or infrastructure
was started locally. Both proposed FreeFlight DNS names remain undeployed.

Added DockPipe dev/clean/development.test with explicit configuration, selective
preview-first cleanup and three policy tests. Existing generated site/package
receipts were not removed. Developer onboarding records native alternatives.

Hosted run 39326150685 at 33075a92f3d71ea66288046fe7e3d257661256f3 passed Linux
x64/ARM64 and macOS ARM64 including native bundles. Windows passed core, both
workers and integration but failed the SDK-client directory assertion because
Windows expanded an 8.3 path alias. A native realpath comparison preserves exact
directory identity; the next run must prove the fix.

A focused robustness check found JSON parsing had only byte bounds. Added early
128-container nesting rejection for requests, configuration and worker replies.
Tests reject 10,000-level input, accept the documented boundary, recover on the
next valid request, and stop a worker returning invalid nested data. DockPipe
core build, CTest 2/2 and formatting pass; hosted requalification remains required.

Qt dependency review found high-severity advisories affecting the original 6.8.3
pin. Earlier renderer checks remain historical functional evidence, not a clean
security qualification. Updating the website toolchain before production release;
no vulnerable site build has been deployed.

Qt 6.12.0/Emscripten 5.0.5 now build locally and pass actual staging/production
Chromium desktop/mobile navigation and SEO tests. Source and notice receipts were
regenerated. Container base scanning found zero HIGH/CRITICAL findings across
70 OS packages; exact built-image scanning remains a hosted gate. Release policy
tests pass (34), with provenance and audit binding. No deployment occurred.

Owner requested a pause on new hosted CI/release uploads while GitHub budget and
usage concerns are diagnosed read-only. Local implementation and evidence are
preserved; no artifact/cache deletion or spending-control change was made.

Read-only inspection found no quota error in the inspected failing runs; failures
were implementation/test issues and artifact uploads succeeded. Owner authorized
resuming bounded CI with existing zero-dollar overage budgets unchanged. To avoid
duplicating large candidate archives, PRs still build and qualify everything but
retain only diagnostic evidence; canonical push runs retain release artifacts.
No existing artifacts were deleted.

Candidate d30f780e9073e5f132cf9399038fec24886d2f3b PR CI 39329692409 passed
Linux x64, Linux ARM64 and macOS ARM64 complete native qualification. Both Qt
site modes passed actual browser navigation, serving-container smoke and exact
image vulnerability checks. CodeQL run 39329692386 passed. Windows passed core,
workers and mixed-engine integration but failed the actual Roslyn project load:
NuGet assets processing reported null path1. This is an unresolved Windows
runtime issue, not a passed release gate. No promotion or publication occurred.

Source-notice review added nine pinned Emscripten runtime license/AUTHORS files
to served notices and a hashed archive. Local site.sources and site.build passed;
next-candidate hosted requalification remains required. Closed completed routing
task and refreshed stale release/site task descriptions to reflect evidence.

Windows project-load fix preserves only APPDATA, which NuGet's lockfile reader
requires for its user-settings directory. Regression tests preserve that path
while rejecting NuGet credential and .NET startup-hook environment variables.
Local DockPipe core build, CTest 2/2, lint and actual-project integration passed;
Windows still requires hosted verification. Release-policy tests now pass 35
cases, including required pinned Emscripten notice archive/receipt integrity.
