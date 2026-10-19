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
