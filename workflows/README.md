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
