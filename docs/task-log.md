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
