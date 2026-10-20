# DockPipe workflow rules

Actual reference: Cloud workflows/<dotted-name>/config.yml, schema-1
 dockpipe.config.json compile.workflows and packages.namespace, host steps with
id/kind/cwd/cmd, optional dependency declarations. Use those fields, not a new DSL.
DockPipe owns build, tests, format/lint, repository health, cleanup, site and release
verification. Compose tasks without duplicating native command definitions.
GitHub Actions owns triggers/matrices/credentials/approvals/artifact publication.

repo.check is an existing repository-authored workflow pattern, not a built-in
universal validator. Extend the current workflow for required files, YAML indexes,
diff/layout/dependency/docs consistency, binaries/secrets and safe generated state.
Focused unavoidable helper assets belong beneath their workflow and must explain
why YAML/native tooling is insufficient. No root Make/npm/PowerShell wrappers.
Validate YAML with dockpipe workflow validate. Pin CI toolchains and document any
runner fallback; native builds remain possible without DockPipe.
# Branch discipline

Implement on js/dev only. Use promotion pull requests js/dev -> dev -> staging ->
master; never push implementation directly to the three promotion branches.
Keep master default. Preserve prior commits without force pushes. Security-sensitive
branch protection changes require separately approved settings.


The promotion.check workflow permits authentic Dependabot dependency-only PRs to
dev: GitHub bot actor/author IDs, same-repository head, recognized bot branch and
bounded allowed-file diff are required. Action and PackageReference replacements
preserve identity, position and surrounding build policy. Ordinary development
still uses js/dev -> dev -> staging -> master. No protection or qualification check
is bypassed. A maintainer-created replacement or maintainer-triggered bot event
does not impersonate Dependabot; it remains outside this exception.

Lockfile JSON is accepted as dependency metadata, not proof of integrity or registry
trust. Locked installs, vulnerability checks, semantic tests and full platform CI
remain required. Incompatible major upgrades stay held.

GitHub's `target-branch` setting routes version-update PRs to dev once the
configuration reaches the default branch. Security updates still use the default
branch under [GitHub's documented service behavior](https://docs.github.com/en/code-security/reference/supply-chain-security/dependabot-options-reference#target-branch).
This repository does not disable security updates or automatically bypass the
protected-branch policy for them.
