# TASK-005: Website and remaining release gates

Status: open. Follow docs/agents/index.yaml and docs/acceptance.md.

Qt 6.12.0/Emscripten 5.0.5 website passes hosted staging/production browser,
container smoke and exact-image vulnerability gates at candidate d30f780.
Additional Emscripten runtime notices passed local source/build verification and
require next-candidate qualification. Production/staging hostnames are configured;
no DNS, ingress or deployment has been performed. Existing-host operator target,
profile, artifact transfer and rollback contract remain unverified; see
docs/site-deployment.md. Do not replace the Qt renderer or invent infrastructure.
