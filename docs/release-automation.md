# Qualified GitHub Release workflow

The manual `Qualified release` workflow runs only from the canonical repository's
`master` branch after normal promotion. See [Actions](https://github.com/Dockpipe-Industries/freeflight/actions/workflows/release.yml)
and [Releases](https://github.com/Dockpipe-Industries/freeflight/releases) for live
verification and publication outcomes; configuration alone does not establish either.

Select an exact successful **CI push run on js/dev** and choose `verify` first.
This reads GitHub evidence and artifacts, then calls `dockpipe --workflow release.verify`.
The latter replaces obsolete core-only CPack verification and composes complete
archive validation from `release.prepare`. No binary is rebuilt or repacked.
`release.policy` runs disposable promotion, preparation and Registry policy tests
without credentials or publication.

The candidate must satisfy these gates:

- Successful completed canonical CI and CodeQL push runs for the exact source SHA.
- Four native artifacts: Linux x64/ARM64, Windows x64, macOS ARM64; no expired or
  mismatched run artifacts. GitHub's archive digest is checked before extraction.
- Merged same-repository PR chain `js/dev → dev → staging → master`, with merge
  ancestry connecting each step. Squash/rebase promotions that lose source ancestry
  are deliberately ineligible. Tested source must be an ancestor of dispatched
  master and have its identical Git tree.
- Complete native and MCPB pairs, checksum coverage, installation/semantic receipts,
  and clean embedded source commit/tree matching hosted qualification.
- Same-run staging and production site bundles, saved container archives and
  successful HIGH/CRITICAL scans bound to those exact image hashes, plus
  corresponding Qt/relink sources. Inner receipts match the same clean source,
  environment and per-file checksums.
  Emscripten's exact pinned runtime notices and checksum receipt are also required;
  every original notice must be present in the archive and combined served notices.

Explicit `mode=publish` first runs a read-only verification job. A separate
publication job independently reacquires and revalidates the candidate, checks
master and successful runs again, and refuses existing tags or releases. It creates
a draft Release targeting promoted master, uploads exactly the tested bytes,
verifies GitHub's uploaded asset digests, then marks the Release public. Native
artifacts, aggregate `SHA256SUMS`, release metadata, and the seven original
site/container/source ZIPs are retained as Release assets. Corresponding sources
therefore outlive Actions' 14-day retention. Website deployment and Registry
submission are separate operations.

GitHub Actions owns event selection, API reads/downloads and publication; the small
`.github/release/api.py` adapter delegates artifact/promotion validation to DockPipe.
Official checkout/setup actions are pinned. Checkout does not persist credentials.
Default permissions are `contents: read`, `actions: read`, `pull-requests: read`;
only the explicitly selected publication job receives `contents: write`, using
the job's ephemeral `GITHUB_TOKEN`. No secrets, OIDC permissions, organization
settings, environments or persistent access are created. Organization policy may
still restrict the token.

After a failure following draft creation, inspect the existing Release and tag.
The workflow never deletes, replaces or automatically retries an existing release.
`publication-attempt.json` records the known draft/release ID, and an always-run
artifact step retains available evidence and checksum manifests for 30 days, even
when publication fails. GitHub's current state must resolve an uncertain request
outcome before another attempt. These integrity checks are not signed attestations.

The first hosted verification reached artifact acquisition after a successful
qualification and promotion chain, then stopped on an incorrect API Accept header.
Artifact API requests must accept GitHub JSON even when the response redirects to
a ZIP. Collector unit tests enforce that contract and redirect credential isolation.
Local tests cover policy rejection and receipt integrity, not live Release writes. Registry preflight accepts a promoted tag only
when the qualified source is its ancestor and both commit trees match exactly;
artifact hash verification remains mandatory.

For developer builds, provision Qt/Emscripten through `dockpipe --workflow site.toolchain`
before the composed `build` workflow, which includes `site.build`. Native tools,
worker dependencies and Python requirements must also be provisioned. Release
verification consumes already qualified artifacts instead of repeating builds.

References: [GitHub artifact API](https://docs.github.com/en/rest/actions/artifacts),
[GitHub releases API](https://docs.github.com/en/rest/releases/releases). The current
official API examples specify the pinned `2026-03-10` REST API version used here.

Native artifact collection accepts the historical flat layout and the current
`packages/` prefix produced by the CI multi-path upload. Only native archive and
checksum basenames are accepted after removing that one exact prefix. Traversal,
other directories, normalized collisions and special files are rejected before any
files are extracted; existing outputs are never overwritten. The release-policy
suite covers this layout contract. Hosted verification 39374125749 exposed the
previous mismatch before publication; a successful later run must establish repair.
