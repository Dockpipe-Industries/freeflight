# Workflow instructions

Read README.md and root docs/agents/workflows/development.md. Reuse DockPipe Cloud's
actual named-step schema and workflow-local assets. No alternative task runner.
Keep generated dependencies/builds under bin/.local, avoid broad cleanup and never
add credentials. CI calls workflows; a workflow must not claim a release succeeded
merely because an artifact was authored. repo.check owns agent-router validation.
