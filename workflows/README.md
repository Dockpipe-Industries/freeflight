# Development workflows

DockPipe is the authoritative developer interface. Invoke dockpipe --workflow NAME.
Small tasks live at workflows/NAME/config.yml and compose through DockPipe commands.
core.build/core.test own C++; workers.typescript and workers.roslyn own internal
workers; integration.test validates the one endpoint; site.build stages the site;
repo.check validates guidance/layout; package.native qualifies complete artifacts;
registry.check validates registry metadata. build/test/check compose those tasks.

Generated output is bin/.local; engine state is bin/.dockpipe. Helper scripts are
workflow-local assets for validation, cross-platform staging or artifact inspection,
not alternate entry points. Do not introduce duplicate npm scripts or CI build logic.
See docs/agents/workflows/development.md and docs/README.md for requirements.

The website follows the Qt/WASM renderer architecture: `site.toolchain` provisions
pinned task-local SDKs, `site.build` compiles and stages environment-specific assets,
`site.test` runs real Chromium at desktop/mobile widths, and `site.container` builds
and smoke-tests a disposable unprivileged container.
`site.deploy.prepare` validates environment-specific delivery receipts and emits
isolated Compose wiring without accessing hosts or credentials. Production inputs
must have a stable version and matching qualified source, release-tag and master
trees. See `docs/site-deployment.md` for remaining activation gates.
`site.deploy.bundle`, `site.deploy.send` and the host-installed `site.deploy.receive`
implement published-byte verification, scoped transfer, activation, health checks
and rollback. Receiver installation/access are separately authorized infrastructure
steps. `release.policy` tests their rejection and rollback behavior without hosts.

To compare a locally built pinned baseline with the current source, set
`FREEFLIGHT_BENCHMARK_BASELINE` to its absolute checkout/archive directory and run
`dockpipe --workflow benchmark`. Both trees must first pass their native build and
worker workflows using the same provisioned toolchains. The comparison reuses the
MCP benchmark driver, runs fresh processes serially against identical generated
C#/TS/JS fixtures, alternates order for two compatible runs, and retains raw
semantic failures, timings and sampled process-tree RSS beneath
`bin/.local/benchmarks/comparison-*`. The archived baseline source receipt is read
from `bin/.local/baseline-provenance.json`; retain and verify it before comparison.
The compatible fixture contains 24 one-MiB generated files; additional cases
exercise a nine-MiB file and 72 one-MiB files. Each generated file has 100 real
declarations plus explicit comment padding. These controlled byte-budget workloads
are not representative real solutions. First diagnostics includes lazy engine
loading; subsequent query timings and changed-file diagnostics verify exact results.
Default `benchmark` behavior is unchanged when the variable is unset.
