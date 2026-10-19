# Contributing

Use Apache-2.0-compatible contributions. Do not copy Glider/TGlider proprietary
implementations or private organization source. Read AGENTS.md and docs/README.md.

Provision the documented native toolchains, run `dockpipe --workflow build`, then
`dockpipe --workflow test` and `dockpipe --workflow repo.check`. Open draft PRs from
integration branches. Promotion is js/dev → dev → staging → master; changes to
protection or credentials need separate owner action. No production artifact may
be published on an unverified platform.

New adapters implement capability/open/query lifecycle behind the single core.
Use mature semantic engines, exact-result fixtures and negative path/cancellation
tests. Unsupported operations must not appear in capability discovery. Keep
workflow logic under workflows and all generated state under bin/.local.
