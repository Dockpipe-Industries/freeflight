# Release preparation without publication

`dockpipe --workflow release.prepare` validates already-qualified native artifacts from CI or local packaging. It does not compile, publish assets, create tags, acquire credentials, change `server.json`, or submit to the MCP Registry. The workflow-local standard-library Python adapter is needed to inspect both archive formats, enforce internal/external hashes and receipts, and verify downloaded asset bytes; DockPipe remains the sole task entry point.

Set `FREEFLIGHT_RELEASE_INPUT` to a reviewed JSON file under `bin/.local/release-inputs/` containing:

- `version`: exact artifact semantic version, such as `0.1.0`.
- `tag`: exactly `v` followed by that version.
- `expectedRids`: explicit complete list for this preparation; supported values are `osx-arm64`, `osx-x64`, `linux-x64`, `linux-arm64`, `win-x64`, `win-arm64`.
- `registryRid`: one explicitly selected RID from that list.
- `artifacts`: absolute paths to exactly one `package.native` tar.gz and one MCPB for each RID. Their original `.sha256` receipts must be adjacent. Do not glob a directory containing old versions or duplicate candidates.
- `mode`: `draft` (default, no network) or `verify-urls` (read-only public HTTPS downloads).

The workflow first runs its tests, then checks filenames and digest prefixes, adjacent checksums, safe unique archive member paths, complete per-file SHA256SUMS coverage, receipt RID/runtime/check names, manifest version/platform/entry point, and byte-identical native/MCPB contents. Nothing is extracted or executed. It rejects missing or dirty Git provenance and requires identical source commit/tree IDs across all selected artifacts. It bounds expanded archive sizes and rejects links and special files. These checks establish internal consistency; unsigned embedded receipts and checksums are **not authenticated CI provenance**. Maintainers must independently verify the originating CI run and intended tag commit. A clean-source receipt does not prove a tag already points there.

After all checks pass, a new unique directory under `bin/.local/release-prepared/vVERSION-*` receives:

- `SHA256SUMS`: checksums of the original selected release archives.
- `release-manifest.json`: selected platforms, source paths, exact candidate GitHub tag URLs, hashes, sizes, verification receipts, mode and limitations.
- In `draft` mode, `server.template-not-publishable.json`: explicitly unpublished metadata **without a packages array**. Candidate URLs in the release manifest are plans, not availability claims.
- In `verify-urls` mode, `server.draft.json`: an unpublished Registry draft with one selected MCPB package, emitted only after downloading every selected artifact from `https://github.com/Dockpipe-Industries/freeflight/releases/download/TAG/FILENAME` and matching its full SHA-256. No credential or token is sent. A missing URL, HTTP failure, or byte mismatch fails preparation before output is created.

Artifacts themselves are not copied into that output directory. Publication tooling must consume their validated paths and hashes, and reverify before an external write. Existing output is never overwritten. Authenticated release creation, Registry publication, signing and notarization remain separate approval and verification steps.

## Architecture selection

MCPB manifest 0.3 declares operating systems but has no CPU architecture selector. The filename and receipt contain the RID; `registryRid` chooses exactly one package for the draft. This is not automatic multiarchitecture resolution or a universal binary. An installer or operator must ensure the chosen RID matches the host before executing it. Do not publish multiple architecture-specific packages under an assumption that Registry clients will select correctly.

## Validation evidence

The adapter has controlled archive tests for missing receipts/platforms, tampered external and internal hashes, version/RID incompatibility, native/MCPB mismatch, dirty/missing source provenance, cross-platform commit disagreement, traversal, and remote verification failure. Draft tests prohibit any network calls; URL verification tests inject a verifier and confirm exact tag URL/hash propagation. Mocked URL checks are not evidence that release URLs exist.

Existing local 2026-10-19 archives predating Git provenance receipts are intentionally ineligible; new clean-source packaging and successful hosted CI artifacts are needed for actual release preparation. No public release or registry publication is implied by implementing this workflow.
