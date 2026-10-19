# Verified development toolchain

On 2026-10-19, the owner requested a Homebrew DockPipe refresh on the Mac.
Only the existing official tap's dockpipe-staging formula and
dockpipe-desktop-staging cask were upgraded; unrelated outdated packages were not.

- Candidate: `0.6.20-staging.39285769512.1.0399bb37bb7d`
- CLI output (Homebrew and app): `0.6.20`
- Official tap: `dockpipe-industries/dockpipe`
- ARM64 CLI archive SHA-256: `3dd04f078bf32077e0d98a1a0736806298db5141be48976ede5f11ef3eef88a0`
- ARM64 desktop archive SHA-256: `5835b4c6e283db2227a58d380dea9918331a591506c722c5623b56eb2e9ccf78`
- Core archive SHA-256: `f4ed4d89dc2202ac5f9638bd534a2e238df901dfe0c1b8e963796adf73fe7b33`
- Lightweight verification: workflow validate + repo.check passed under 0.6.20.

CI now pins this exact 0.6.20 candidate's platform assets and compiled core;
isolated macOS download/hash/workflow/router/registry checks passed. Hosted
cross-platform results remain pending. Never silently choose latest in CI.
No app launch, security warning bypass, credentials
or organization permissions were changed. Homebrew noted a changed app signer;
normal OS prompts remain intact.

Instruction source inspection: current DorkPipe package 0.6.5 at public commit
`c284f0438b0d1c589cf2860742ffec7ba86c8678`; current DockPipe staging
`0399bb37bb7d795ca55fc240bcfa4928fe3f1c14`. The older embedded package was 0.6.2.
No shared DorkPipe package installation was changed; official source inspection
established that example.brain is not a complete router bootstrap on this platform.
