# TASK-003: Standalone release and registry qualification

Status: open. Follow docs/agents/index.yaml and docs/acceptance.md.

Hosted candidate d30f780 passed Linux x64/ARM64 and macOS ARM64 native bundle
qualification. Windows failed actual-project MSBuild loading; investigate and
requalify the exact corrected source before promotion. Release verification and
publication policy have 34 passing local tests; no production tag, release or
Registry listing exists. Registry authentication and actual asset URLs remain
publication prerequisites. See docs/task-log.md for run IDs and current evidence.
