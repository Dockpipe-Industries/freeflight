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

Candidate a9e37ca99a021853cf2e50eaea1d5f3578498812 PR CI 39330975608 passed
Linux x64/ARM64, macOS ARM64 and both Qt site modes. Windows passed actual
project semantics and official-client compatibility, confirming the NuGet path
fix, then failed Python's attempt to launch the npm command shim. Moved that
audit invocation into a native DockPipe step; all six local dependency-audit
steps now pass, with zero npm findings and no NuGet findings.

Focused Windows review found ANSI/UTF-8 conversions could corrupt non-ASCII
workspace and environment paths. Windows now reads the allowlisted environment
through its wide API; wide CLI arguments normalize to UTF-8, and filesystem/JSON
boundaries explicitly convert UTF-8. Unicode protocol fixtures and exact-path
assertions pass locally with core CTest 2/2, lint and repo.check. Windows-specific
execution remains a hosted gate. CMake selects the static MSVC CRT for the C++
core/tests so ordinary standalone users do not need a separate VC++ runtime for
that executable; Node/.NET runtime closure is a separate qualification concern.

After a reported 21:59 UTC transient environment disconnect, fresh pwd, Git status
and process inspection verified shell continuity and preserved edits. No external
action was uncertain and no push or deployment was repeated.

Separate DockPipe PR #168 at 98867e03 passed CI 39329758384 (Linux, Windows and
Cockpit) and CodeQL 39329758498. Flatpak qualification was still in progress when
checked. This verifies the scoped discovery/configuration changes, not an
implemented MCPB installer or gateway lifecycle.

Full local package.native qualification passed after the Unicode changes:
10 installed protocol tests, Roslyn safe/trusted suites, bundled TS/JS/C# semantic
assertions, and fresh MCPB extraction from Unicode/space paths. Five PE policy
tests and five MCPB tests pass. The Windows core import gate rejects dynamic
VC++ runtime dependencies and records actual import names; real Windows execution
remains pending. Evidence: bin/.local/package-native-unicode-pe.log. Generated
local artifacts contain dirty-source provenance and are not release candidates.

Candidate 122237f46bef1b9e177caef4bcadddc70ea1de68 Windows run
39332231466 passed Unicode workspace discovery and process tests, but a Python
echo fixture decoded raw UTF-8 using the Windows legacy code page. Corrected
the fixture to read bytes and retain exact Unicode assertions. MCP test clients
now explicitly use UTF-8 and send raw non-ASCII JSON. Roslyn independently uses
strict UTF-8 standard-pipe readers/writers with no BOM; new tests verify Greek
and Japanese filenames/symbols, exact UTF-16 definition positions after an emoji,
and controlled rejection of invalid/truncated UTF-8.

DockPipe worker build/safe/trusted suites, actual-project integration and core
tests passed locally. Complete package.native qualification passed again with
the updated bundled worker, Unicode installation paths and fresh MCPB extraction;
evidence is bin/.local/package-native-strict-utf8.log. Windows remains pending
next-candidate qualification. Distribution docs now state the actual runner
baselines rather than implying older-OS or musl compatibility.

Website and README installation copy now points to GitHub Releases and
candidate-specific qualification evidence instead of stale local-macOS-only
claims. Capability/security limits remain explicit. Content/link checks passed;
next-candidate hosted Qt builds and browser tests will qualify the changed copy.

Candidate 9da055b47931e9f9d7e4fb15e60f21ada5e7eeb8 Windows run
39333345879 passed core, raw UTF-8 workers, actual Roslyn project and official
MCP client checks, then failed the pinned MCPB schema checksum after Git
converted LF to CRLF. Added repository attributes for LF source text and exact
vendored schema bytes, without changing the hash or weakening verification.
An isolated Git autocrlf=true checkout regression reproduces the original
failure and verifies the policy preserves the exact upstream bytes.

Full local DockPipe package.native qualification passed: six MCPB tests, five
PE policy tests, installed protocol and worker/semantic checks, and fresh bundle
extraction. Evidence: bin/.local/package-native-attributes.log. repo.check now
requires the attributes file. Windows hosted qualification remains pending.

Candidate 27985882677e61c14269df413ef18f5579b9a0d0 passed all four native
platforms and both Qt site browser/container/audit jobs in push run 39334371543
and PR run 39334378171. CodeQL analysis workflows completed, but the separate
CodeQL alert check failed on tests/process.cpp:106 (alert #4, user-supplied crash
marker path). PR #2 was marked ready; its merge was rejected with HTTP 405 and
remains unmerged. No protection bypass or alert dismissal was attempted. Fixing
the test helper and rerunning qualification is required before promotion.

Protection readback for master/staging/dev confirms strict/up-to-date checks for
four native jobs, both Qt jobs, cpp and CodeQL; administrator enforcement and
conversation resolution enabled; zero required approving reviews; force pushes
and deletions disabled. DockPipe PR #168 also passed its Flatpak job, completing
its currently observed CI set. Registry publisher authentication is absent locally;
site deployment still needs the existing operator host/profile/transfer contract.

The crash helper now accepts only a fully parsed unsigned integer token. The
parent atomically reserves a unique private temporary directory; the worker
derives a fixed marker name and rejects symlinks. Seven invalid/missing/path-like
token cases preserve a sentinel, while the exact one-invocation and explicit
recovery assertions remain. Local DockPipe core.build, core.test (2/2), lint and
repo.check passed. The alert is not dismissed; hosted reanalysis must clear it.
Acceptance milestones now distinguish implemented/tested work from publication,
gateway lifecycle and broad language/project fidelity still pending.

Candidate 2c29369a3a5132d14204d7153f05985b5bea7a64 passed push CI
39335341348, CodeQL 39335341377, and the separate CodeQL alert check. Alert #4
was marked fixed without dismissal, then its bot thread was resolved. Promotion
PRs #2, #1 and #3 merged normally; master 70af9b1780ae516b71a94e967da077f5ba54a18b
has identical tree 56d04adba67d3d7cd73d0910e3d213b6bf6edd9f.

Verification-only release run 39337332446 stopped before publication because the
artifact API rejected Accept: application/octet-stream (HTTP 415). A read-only
reproduction confirmed that header fails while application/vnd.github+json returns
the expected HTTPS artifact redirect. No tag or release was created. The API
adapter needs a focused correction and another protected qualification/promotion.

A pinned macOS trial was downloaded from CI 39335341348, with GitHub ZIP digest,
inner archive digest and every installed file checksum verified. Source provenance
is clean 2c29369. Bundled Node 24.22.0 ran official MCP SDK 1.32.1 against the
packaged FreeFlight 0.1.0 and a disposable fixture: exact TS2322, definition range,
two references, JavaScript increment symbol, Roslyn CS0029/Widget symbol and clean
shutdown passed. Trial/configuration/receipt files are isolated under
bin/.local/trial-2c29369; no client configuration or existing workspace was modified.

The API collector now uses GitHub JSON Accept for all API calls; binary mode only
controls response consumption. Six offline regressions cover request headers,
binary/JSON handling, POST encoding and credential-stripping/host-restricted
redirects. DockPipe release.policy passes 41 tests; workflow validation, repo.check
and diff checks pass. No permission, pin, provenance or promotion rule changed.


The Linux-download priority adds official MCP SDK semantic qualification to
package.native for both assembled and freshly extracted bundles, using their own
Node and internal workers. Local package.native passed. Hosted Linux qualification
and public preview upload remain pending; no download is advertised yet.

GitHub API 2026-03-10 also removed merge_commit_sha from all PR payloads. The
collector now normalizes authoritative merged timeline commit IDs with exact
repository/timestamp validation and bounded pagination. DockPipe release.policy
passes 46 tests. A read-only rehearsal verified all 11 source artifacts, 8 native
archives, 7 supplementary artifacts and promotion chain #2 -> #1 -> #3. No tag,
release, permissions or promotion gates changed.


Linux x64 preview v0.1.0-preview.20261019.1ecf18d was published from clean source
1ecf18d. Push CI 39338684956 and PR CI 39338692303 passed all native/site targets;
CodeQL passed. All three published assets were anonymously downloaded and hashes
verified. Native archive SHA256 is
b144080a4488925ccb562fccf4712c4672b01302212dd7429865f5d913b92f2f.

Follow-up ELF inspection proves this Ubuntu24.04-built core needs GLIBC_2.38 and
GLIBCXX_3.4.32, incompatible with stock Ubuntu22.04's glibc2.35. A separately
qualified22.04 candidate is pending. The local Docker daemon is unavailable and
was not started; runtime execution must use isolated hostedCI. Branch-protection
readback confirms strict checks, admin enforcement, resolved conversations, no
force/deletion on master/staging/dev; zero approving reviews required. js/dev has
no branch protection.

Automatic approval review denied marking PR12 ready, treating draft-to-ready as
an external workflow commitment needing explicit approval. No bypass or retry
performed. Production promotion remains paused pending that approval.


Ubuntu22.04 candidate b22a53a passed job118359090816 in pushCI39340039835,
including exact bundled semantic tests inside a pinned clean Ubuntu22.04 container
with no network/host runtimes and unprivileged user65532. All18 ELF requirements
passed (core GLIBC2.34/GLIBCXX3.4.30). Published separate preview
v0.1.0-preview.20261019.jammy.b22a53a; all4assets anonymously downloaded and
SHA256 verified. Archive7253390795ee026cec2581f6a7184a4d0912fb0e65fcd3adec982462d1826668.
Prior incompatible preview notes link this replacement baseline. PopOS/Fedora/
Bazzite runtime testing remains pending; no host-image or client settings changed.
Current-client-root ergonomics assessment found MCP2026 roots deprecated and
informational; no authorization expansion or workspaceAPI change implemented.


Fedora44 clean-runtime qualification was added to the existing DockPipe Jammy
packaging gate, using the same native archive and a separately pinned official
Fedora image. It reuses bundled officialSDK tests under unprivileged/network-none
execution, records RPMversions and binds evidence to the exact archive/source.
Bazzite remains explicitly untested. Local release.policy passes52tests and
repo.check passes; actual Fedora runtime execution awaits hostedCI.

Follow-up verification: source009a9c1 passed pushCI39341090754 and PRCI39341094941
on all five native targets and both site configurations; both CodeQL runs passed.
Downloaded artifact12228657320 matches its GitHub outer digest. Its tar archive
005cd976a380d0c60a0d92cf3ea91d1f84607efaf7d4b438457f1d4f0d733fa8 passed exact
source/tree, native/MCPB payload, license, ABI and clean Ubuntu22/Fedora44 semantic
receipt checks. This candidate was not published; public b22a53a remains unchanged.

Workspace lifecycle follow-up is in progress: dormant no-argument startup, explicit
open/list/close inside immutable startup permissions, optional informational client
roots and candidate-associated session revocation. No unrestricted access policy
is introduced. MCP2026 roots are deprecated, so this is isolated compatibility
support; ordinary project tools do not depend on it. Cross-platform qualification
is required before publishing this new UX. Fresh branch-protection readback
confirmed strict/admin-enforced checks on master/staging/dev, eight required
contexts, zero required reviews, no force/deletion, and no inherited rulesets;
js/dev remains unprotected. No protection changes were made.

Local workspace lifecycle qualification passed: DockPipe format/core.build/lint,
16 protocol tests plus process tests, official MCP SDK clients with/without roots,
real TS/Roslyn integration and the explicitly trusted own-project C# test. The
native macOS ARM64 tar/MCPB package also passed extracted semantic and workspace
lifecycle checks (local dirty-source test artifacts, not publication candidates).
Legacy roots-change notifications invalidate associations before refresh; stale,
malformed and unresponsive replies are tested. Canonical path alias handling was
preserved. Exact-head hosted qualification remains required for these changes.

Independent review caught queued cancelled lifecycle calls still mutating state
and MRTR roots discovery bypassing duplicate in-flight ID validation. Dispatch now
skips cancelled jobs before state changes and validates IDs before early results.
A controlled-worker regression proves cancelled open/close/root updates preserve
state and release request IDs. Windows CI at78a6f46 also exposed locale decoding
in the synthetic Python worker; its IPC is now explicitly UTF-8 and the exact
Unicode assertion is unchanged. Local 17 protocol tests, process tests, lint and
official MCP SDK compatibility pass; the correction still requires hosted CI.

## 2026-10-19 — Dependabot integration-branch correction

The user requested all FreeFlight Dependabot ecosystems target `dev`. Updated
GitHub Actions, npm and NuGet configuration on `js/dev`; promotion remains through
the existing reviewed branch sequence. No dependency versions were changed and
no dependency PR was merged. Existing PRs #4–#11 are under individual review for
base-change contamination, compatibility and exact-head CI before disposition.
The separately qualified workspace UX remains commit `a617399`; this configuration
change must not be confused with an already published artifact.

## 2026-10-20 — Dependabot review and retargeting evidence

PRs #4, #5, #6, #7, #9, #10 and #11 were verified to contain only one dependency
commit relative to dev and retargeted to dev without changing their heads.
#6 is a draft: isolated DockPipe TypeScript qualification passed 2/17 tests and
failed 15 because TypeScript 7 no longer exports the classic Language Service API.
#10 is a draft: locked restore passed, but Locator 1.11.2's MSBL001 check rejects
the copied Microsoft.NET.StringTools runtime assembly. #11 is a draft: locked
restore fails NU1608 because Roslyn Workspaces.MSBuild 4.14 requires Common 4.14
while CSharp.Workspaces 5.9 requires Common 5.9. No checks were suppressed.

#8 could not be safely retargeted: its ancestry adds six unrelated development
commits and an 18-file diff. Draft replacement #13 preserves only upload-artifact
7.0.2's pinned action changes in the two existing dev workflows; #8 is closed
unmerged and its original branch remains intact. #13's promotion gate fails as
expected because the existing policy allows only js/dev into dev; compilation
is skipped by that gate. The other bot PRs' previous CI runs were cancelled,
except #8, whose green old-base run does not qualify #13. No dependency PR is
merge-ready. CodeQL init/analyze versions also require coordinated review for #7.

The target configuration is committed on js/dev and takes effect for future
Dependabot updates only after promotion to the default branch. No protected branch
was directly updated, no promotion exception or protection setting was changed,
and no dependency upgrade was merged. Reconciling dependency PRs into dev with
the js/dev-only promotion policy remains an explicit pending decision.

Separately, workspace UX commit a617399 passed push and PR CI/CodeQL. Its exact
Ubuntu 22.04 artifact, freeflight-linux-x64-35f6ef0b42563319.tar.gz, has SHA-256
b4e491d48a7b2b4dcc24b5ddd8256adc71668a5c31a0f445061df891a46e4028.
Independent archive inspection and clean Ubuntu 22.04/Fedora 44 runtime receipts
verify workspace switching, dormant startup and client-root revocation. It remains
unpublished; the public b22a53a compatibility preview and its notes are unchanged.

## 2026-10-20 — Narrow Dependabot promotion validator

Explicit follow-up authorization permits genuine Dependabot dependency-only PRs
into dev while retaining the normal promotion chain. Added DockPipe promotion.check
and positive/negative cases covering authentic identity, spoofed actor/author,
foreign head/base, invalid branch, unrelated ancestry/files, action commands and
permissions, package scripts/sources and dependency relocation. Independent review
found action/PackageReference swapping between unchanged steps/conditions; full
normalized-source positional comparison and regressions now reject both. Local
DockPipe development.test passes 11 promotion tests plus three lifecycle tests.
Repository protection settings and release qualification remain unchanged.

Reviewed action updates against primary upstream release documentation: checkout
7.0.1, setup-node 7.1.0, setup-dotnet 6.0.0, upload-artifact 7.0.2 and coordinated
CodeQL init/analyze 4.39.0 retain the existing inputs and SHA pinning. Explicitly
disable setup-node's automatic package-manager cache; retain upload-artifact's
default ZIP archive behavior required by release evidence verification. Dependabot
groups only the coupled CodeQL actions and Roslyn packages to avoid split upgrades.
Full hosted qualification is pending; no dependency PR is merged.

The supported Roslyn repairs are applied together on js/dev: both Workspaces
packages 5.9.0, Locator 1.11.2, and StringTools excluded from runtime alongside
MSBuild assemblies. Combined safe/trusted worker tests and self-contained macOS
ARM64 tests pass locally. TypeScript 7 remains incompatible and held.

## 2026-10-20 — Hosted dependency and legacy qualification

Implementation a6456c2 passed all five native push-CI jobs and both website jobs
in run 39346076164; both CodeQL runs passed. Windows qualification exercised
non-SDK C# projects targeting 4.7, 4.8 and 4.8.1 through actual C++ MCP, selected
SDK 10.0.402 / runtime 10.0.13 / MSBuild 18.9.15.50611, and emitted targeting-pack
hashes plus exact semantic assertions. Downloaded artifact 12230623607's ZIP
SHA-256 af7ce89f80ccce7c7981f01ff8590e3be841b6786cd019522665884b72b4d20b
was verified independently. Intermediate framework versions and additional legacy
project types remain unqualified. Updated earlier dependency-version prose to match
the repaired manifests. No dependency PR was merged.

The new upload-artifact action retained the required ZIP semantics. Independently
verified Linux tar freeflight-linux-x64-64b8711f25d8ceae.tar.gz has SHA-256
43030e2d097924f35e018489d7ebf707fd22575735edd33ccdc97ffd15db067a and matches
the native/MCPB source receipts and clean Ubuntu/Fedora tests. It is not published.
DockPipe Flatpak run 39342951155 completed successfully at 15eafc8.

## 2026-10-20 — Real Dependabot branch-prefix regression

Post-publication comparison with actual PR #6 exposed that npm's Dependabot branch
prefix is npm_and_yarn, while the package ecosystem key is npm. Added an explicit
branch-to-ecosystem mapping and tests using the real npm/nuget branch shapes; fake
npm-prefixed branches remain rejected. This workflow-only correction does not
change the published ba0c4ce runtime. It follows the ordinary protected promotion
chain with fresh checks; no permission or branch-protection exception was added.
# 2026-10-20 — Resource limits and incremental source reuse

- Diagnosed the published preview's hard-coded 2 MiB per-C#-file and 64 MiB
  aggregate cap; a user-supplied test summary confirms whole-repository loading
  was blocked while narrower-folder semantic queries worked. No private source
  was needed or copied into fixtures.
- Added one validated operator-owned resource policy forwarded by the C++ core,
  shared by safe/trusted C# and TS/JS. Runtime queries cannot raise it. Bundles
  retain automatic internal-worker discovery when configuration omits engines.
- Resource failures retain path, observed count/size, limit and remediation as
  structured MCP errors. Native package verification exercises this configuration.
- C# retains stable Roslyn documents with watcher/metadata invalidation and a
  five-second full-content fallback. Direct targets and rename sources remain
  freshly checked. TS retains bounded source snapshots and content versions.
- Local C# fixture: 71,725,175 source bytes, 25,587,657-byte largest file,
  55,000 generated constants; exact semantic checks pass. Warm query reads 56
  bytes and reuses three large files. Single open sample 0.124 seconds; this is
  not a latency distribution or production memory budget. Trusted 3 MiB fixture,
  cancellation, boundaries, recovery and watcher-bookkeeping overflow pass.
- Local core protocol/process and real-worker MCP resource/recovery tests pass.
  Real-project and official MCP client checks pass. TS/JS fixtures cover 9 MiB
  sources and a 72 MiB configured project; independent version metadata avoids
  text-LRU eviction causing repeated dependency reads/hashes. Unreadable configured
  sources and unsupported project-reference graphs now fail explicitly.
  Hosted CI and legacy Windows qualification pending at this entry. No release,
  merge, branch-protection change or unrelated DockPipe change was performed.

## 2026-10-20 — Paired scaling benchmark

Candidate runtime 986b60b passed all five hosted native targets, both site builds and CodeQL (CI 39357377175). Ran the existing DockPipe benchmark in comparative mode against a verified same-source macOS rebuild of published ba0c4ce. All 12 compatible baseline/candidate runs and all six candidate stress runs passed exact semantics and edit-refresh checks; old C# limits and TS/JS source omission were retained as failures. Results and memory tradeoffs are documented in docs/benchmarks.md. Benchmark tooling/documentation changes do not change the measured runtime. PR20 remains draft; no release or protected merge performed.

## 2026-10-20 — Pre-promotion correctness review

Focused review found and fixed retained TypeScript resolution after dependency creation/package metadata changes (also reproducible in the preview), plus an initial trusted Roslyn filesystem loader that could bypass the guarded snapshot read. Roslyn safe/trusted suites and all 34 TS tests passed locally. New assertions cover source add/remove/rename, inherited settings, package metadata, preserved timestamps, retained services and zero-byte C# workspace-symbol queries. docs/scaling-readiness.md distinguishes tested behavior, bounded freshness, limits and un-injected watcher failures. Historical timing observations are unchanged; correctness follow-up timings were not compared. Jamie authorized gated promotion and a fresh Linux preview after exact-head qualification; publication remains pending.


## 2026-10-20 — Local trusted-loading repair after 57851e3

This round is local and uncommitted. No push, publication, active client change,
private project edit, Linux access or user-session restart was performed.

- Reproduced Roslyn 5.9 warning-to-Failure behavior with controlled fixtures.
  Exact project/message-bound NU1603/NU1701/NU1903 warning evidence now permits
  useful graphs while preserving warnings. Supported binary-log replay rejects
  actual errors, same-message error collisions and warnings promoted to errors.
  Missing standard restore assets remain fatal; ambiguous custom layouts fail
  conservatively. No automatic restore or repository execution in safe mode.
- Added operator-owned `trustedRoots`, nested project discovery/selection,
  structured load errors, truthful loaded capabilities, and explicit workspace
  reload. Read-only sibling roots and query-time trust escalation remain blocked.
- Corrected document symbols to select declarations in the requested document,
  including merged namespaces and partial types.
- DockPipe core protocol/process, Roslyn worker, mixed-worker integration,
  lint and repository checks passed locally. The complete macOS ARM64 packaging
  gate passed 22 protocol tests, official MCP SDK checks, trusted worker tests,
  and a packaged C++ MCP-to-Roslyn .NET 8 fixture with exact semantic positions,
  warning status, reload, trust/root boundaries and runtime-only SDK diagnostics.
  Extracted tar and MCPB smoke checks passed.
- Qualified local tar: `freeflight-osx-arm64-2181a6b38a40fe55.tar.gz`, SHA-256
  `a63e9f15abb367b60d22c80bbefbdd19e4b44ac7420c1c21579e1577c7450dd5`.
  Generated receipt/log: `bin/.local/trusted-repair-package.log`.
  These dirty-source artifacts are local test outputs, not releases.
- Four full-bundle paired sessions against a verified same-source Mac rebuild
  of 57851e3 passed exact semantics, immediate add/remove/freshness and ancestor
  symlink boundary checks. Per-refresh ancestor-check deduplication reduced
  pooled medians 34–37%, but p90 regressed; startup improvement is unproven and
  sampled RSS is effectively unchanged. The slower Refresh mode is unresolved.
  See [hot-path evidence](hotpath-performance.md); this is not a competitor win
  or production performance qualification.
- Windows/Linux and the reported private solution were not tested this round.
  Hosted CI and release qualification are pending. The existing published
  preview does not contain these repairs. See [unreleased notes](unreleased.md)
  for configuration, reload behavior and security/fidelity limitations.


## 2026-10-20 — Bounded hot-path disposition and repair requalification

- Retained the original two-session-per-version comparison: 40 correlated warm
  samples per operation per version. Outline/definition/reference p90 increased
  2.091/2.211/2.035 ms (31.8%/34.1%/27.2%). Both experimental sessions were slower
  at p90 than either baseline session, but this small experiment does not establish
  population significance or a cause. Diagnostic controls did not consistently
  reproduce the slow Refresh mode; no additional favorable timing run replaces it.
- With no evidence-backed correction, reverted only the per-refresh ancestor-check
  optimization. Refresh and CheckPath match 57851e3 exactly. Functional trusted-load,
  trust/configuration, reload/status and document-outline changes remain intact.
  Preserved the isolated experiment in `bin/.local/experimental-hotpath-only.patch`.
- Ran DockPipe package.native once after the revert: passed 22 protocol tests,
  official MCP SDK checks, bundled safe/trusted Roslyn suites, exact definitions,
  references/outlines, file add/remove/rename and preserved-metadata refresh,
  cancellation/recovery, trust/root boundaries and controlled net8.0 project tests.
  Extracted tar and MCPB verification passed. No post-revert speedup is claimed.
- New local tar: `freeflight-osx-arm64-4e5ae6a0724f4d09.tar.gz`; MCPB:
  `freeflight-osx-arm64-feb9fea0aee8279d.mcpb`. Exact hashes and evidence are in
  `bin/.local/trusted-repair-without-optimization-receipt.json`; package log is
  `bin/.local/trusted-repair-without-optimization-package.log`.
  Earlier experimental artifacts remain preserved but are not the retained repair.
- Read-only inspection found an existing local Colima ARM64 VM, stopped. Its local
  Docker daemon is unreachable, so cached Linux images/toolchains were not verified.
  There is no currently usable verified local Linux qualification route. No VM
  start, installation, provisioning, remote-host access or active config change
  occurred. ARM64 container availability alone would not establish Linux x64
  qualification or compatibility with the operator's private solution.
- Work remains uncommitted/unpublished; Linux/Windows/hosted CI and operator project
  checks remain pending. No automatic approval denial or uncertain mutation occurred.


## 2026-10-20 — Functional repair CI authorization

Jamie authorized committing/pushing the reviewed functional repair on js/dev and
opening a draft PR to dev for exact-head Linux/Windows/macOS checks. Protected
merges, releases, package publication and credential/client changes remain on hold.
The unfinished NuGet/npm proof and local diagnostic benchmark tooling are excluded
from the repair commit. Rejected experimental runtime changes remain reverted.


## 2026-10-20 — Windows project-path CI correction

Repair 5d74198 was pushed to js/dev and draft PR #23 opened to dev. Exact-head
Windows CI exposed two protocol failures: `/App.csproj` is rooted but not absolute
on Windows, and missing project paths in a Unicode workspace could terminate the
server while reporting a native filesystem error. Startup and request selections
now reject any root component (including drive-relative paths); canonicalization
uses an error code and a controlled UTF-8 message. Tests cover Windows drive,
root-directory and UNC forms and retain missing-file/recovery checks. This narrow
fix follows the authorized repair/CI scope; packaging experiments stay excluded.

### Trusted repair promotion and release collector regression (2026-10-20)

Repair e2c4379 passed CI 39371768117 and CodeQL 39371768265, then promoted
through PRs #23, #24 and #25 with all required checks. Master ea139ac preserves
source tree c4540b8d9afce40e4388822dae855baa47f6802f. Explicitly approved preview
publication has not occurred. Read-only release verification 39374125749 failed
before publication because native artifact collection expected flat ZIP entries,
while the current CI multi-path upload places archives under `packages/`.

The collector now accepts that exact prefix or the historical flat layout, rejects
normalized collisions/traversal/special files, validates all entries before writes,
and refuses existing outputs. Release-policy regression tests cover both layouts
and rejection paths. This automation-only correction requires fresh hosted
qualification and normal promotion; it does not change the language runtime.
Local NuGet/npm proof and profiling tooling remain excluded. Existing preview
artifacts and tags are preserved; no client configuration or private project changed.

### Promotion event recording delay (2026-10-20)

Collector correction ad8acd5 passed full push/PR CI and CodeQL and promoted through
PRs #26, #27 and #28. The targeted production website rerun resolved a stuck
required-check record without bypassing protections. Hosted release verification
39376995721 then rejected PR #28's merge evidence: merged_at was 05:49:54Z and the
single timeline merge event was recorded at 05:49:55Z. The event's SHA and URL
correctly identify feb3393; its canonical commit response has ea139ac and the exact
PR head 013811b as ordered parents. Failed logs and original records were retained.

The follow-up accepts nonnegative event-recording delay up to a conservative
60-second audit limit and corroborates the merge through the canonical commit API:
exact SHA/repository URL, two canonical parents, and the PR head as second parent.
This is not a claim that GitHub guarantees that latency bound; larger/invalid delays
still stop for review. Unique timeline evidence, same-repository branch identity,
qualified-source ancestry and identical-tree gates remain. Regression fixtures
include the observed public PR #28 record shape and wrong-repository/commit/parent
cases. Publication remains pending fresh qualification and protected promotion.


### Trusted preview publication and source-folder follow-up (2026-10-20)

Source 1997d38 passed hosted release verification 39379428880 after normal protected
promotion through PRs #29, #30 and #31. The public prerelease
`v0.1.0-preview.20261020.trusted.1997d38` and all four assets were anonymously
retrieved and verified. Linux x64 archive SHA256:
`ab4d7f2312b56ed54870f688384f86b2dde470a42889f3820657c4384aa21048`.
No production website was activated by that promotion.

The follow-up implements a single startup `trustedRoots` array as both access and
trusted project-loading permission. Existing `roots` policies remain compatible.
File routing examines only ancestors to identify a repository or project boundary;
startup does not scan or evaluate every repository. Workspace-wide requests require
an explicit workspace selection. Ambiguous solutions/projects expose candidate paths
and their workspace root, resolved with `workspace.open`, not MCP config changes.

DockPipe core.build/core.test and lint/repo.check pass locally. The packaged MCP
fixture verifies two source roots, a nested Architecture.sln, identical symbol names
in different repositories, new projects without restart, changed-file diagnostics,
TS/JS navigation, explicit ambiguity selection and unauthorized/symlink boundaries.
The official SDK client and existing worker semantic/cancellation/resource checks
also pass. Evidence is retained under bin/.local/source-roots-package*.log.
This is local macOS ARM64 evidence; new hosted platform qualification and a report
checkpoint precede any promotion/publication. Client configuration and private
repositories remain untouched; website work and performance experiments are excluded.

### Windows routing fixture encoding (2026-10-20)

Hosted run 39381056310 exposed a Windows-only failure in the new protocol fixture:
its Python echo worker decoded UTF-8 JSON through the default Windows text encoding,
corrupting the Unicode workspace name. The fixture now explicitly configures both
streams as UTF-8, matching existing worker fixtures. The exact path assertion remains
unchanged. This correction changes no server/worker implementation. Local DockPipe
core.test passes; fresh hosted Windows qualification is required. Original CodeQL
run 39381056453 passed. No promotion/publication is authorized by this test correction.

### Read-only external compiler inputs (2026-10-20, unreleased)

The reported Linux preview failure remained applicable after source-folder routing:
trusted graph construction applied the workspace path check to every compiler source.
An authored nested-solution fixture reproduces the old bundle's Path escapes workspace
failure with Test SDK 16.0.1 and 17.8.0; ordinary sibling-reference controls load.
Independent MSBuild Compile-item evaluation identifies each SDK Program source as
its sole external input. The old error itself does not report the rejected path;
the receipt preserves this distinction instead of overstating the evidence.

Trusted graph loading now catalogues exact external compiler sources for bounded
read-only analysis. Query roots and editable paths remain unchanged. Shared external
sources retain/update all compilation contexts. Rename that would touch an external
source refuses the complete preview. Symlinks/reparse components are rejected;
Unix nonblocking/no-follow opens reject nonseekable inputs without waiting on a FIFO.
Structured rejection details include operation and path without source contents.

DockPipe workers.roslyn and complete native package qualification pass locally on
macOS ARM64, including both real Test SDK versions, automatic trustedRoots routing,
explicit nested selection/reload, legacy startup project, exact generated-source
navigation, semantic refresh in two contexts, external rename/query refusal,
symlink/FIFO tests, existing safe-source/trusted tests and official SDK compatibility.
Artifacts: freeflight-osx-arm64-9115485187654f4f.tar.gz and
freeflight-osx-arm64-fe6471cd983e100e.mcpb (local only). Logs/receipts remain under
bin/.local/external-*.log and bin/.local/reports/external-input-*.json.

Local Linux container execution was unavailable because the existing Docker daemon
was not running; no daemon/infrastructure reconfiguration was attempted. Ubuntu22 CI
runs the existing package.native workflow, which now invokes DockPipe
integration.external.baseline on Linux x64 against the checksum-pinned public
1997d38 preview before testing the corrected fixture. Other native matrices run the
corrected fixture through the same package.native operation. Hosted evidence is pending at
this commit. No private project, dependency, MCP config or active session changed;
no promotion/publication is included in this fix. Operator verification against the
original Linux solution and failing test project remains an acceptance step.

The initial development push was rejected because the existing GitHub credential
cannot update workflow YAML. It did not update the remote branch. The unpublished
commit was amended to leave CI YAML unchanged and invoke the baseline from existing
DockPipe package.native composition instead. No credential scope was expanded.

## 2026-10-20 — Consolidated dependency compatibility review

The user requested an isolated consolidated draft PR. The review branch starts at
`a446d375906134ad88ff38fad0720d21bae5e9ba`, preserving the qualified external compiler
input repair. TypeScript 6.0.3 retains the classic JavaScript Language Service API
and passes all 34 current worker tests on macOS ARM64 with Node 24.22.0 through
`dockpipe --workflow workers.typescript`. The pinned manifest and lockfile use the
official registry tarball and SHA-512 integrity. Combined qualification is pending.

PR #6 (`0b9be272f755910fb793c1a0b9e16c59232abf7f`) remains held: TypeScript 7.0.2
exports version metadata at its root and separate unstable native APIs, not the
classic Language Service consumed by this worker. No backend migration is included.
PR #18 (`f2e4c0e2ebd64a0483da79e276d2529dd42509e3`) remains held: the official
StringTools 18.11.0 buildTransitive target explicitly warns that net10.0 is unsupported
and requests net11.0. Job 118403733498 confirms build/basic worker tests pass but
`integration.real` rejects that unsupported framework warning during trusted loading.
Retain StringTools 17.14.28 with the aligned Microsoft.Build 17.14.28 references,
ExcludeAssets=runtime and PrivateAssets=all; no warning suppression or target bump.

PR #19 (`5297978a530e56933cb214cb608ffb9003b2e25d`) has ten successful checks. Its
five setup-python replacements use the verified v7.0.0 commit
`5fda3b95a4ea91299a34e894583c3862153e4b97`. Those changes are prepared locally for
combined testing but publication is pending the existing workflow-write permission
boundary. No credential or permission change, merge, closure or release is authorized.

Local combined qualification completed on macOS ARM64 with Node 24.22.0, .NET
SDK 10.0.402 / runtime 10.0.13: core tests, 34 TypeScript tests, Roslyn safe/trusted
suites, real MCP integration, real-project integration, official MCP SDK, lint,
strict dependency audits (no findings) and registry schema validation passed.
The native package exercised both external compiler-input fixtures (Test SDK
16.0.1 and 17.8.0), including routing, read-only definitions and selection/reload;
both passed. Local site compilation lacks Qt/WASM tooling; hosted site jobs remain
required. A separate current-baseline TypeScript 7.0.2 probe passed 6/34 and failed
28/34 tests (missing classic API, including ts.sys).

Draft PR #32 targets js/dev and is textually mergeable. Hosted five-platform/site
qualification is pending; promotion policy and CodeQL passed on its initial head.
No remote js/dev changes were made. The unpublished setup-python patch remains a
separate local deliverable pending an authorized workflow writer.
