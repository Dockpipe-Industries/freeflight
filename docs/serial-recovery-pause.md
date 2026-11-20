# Paused at user request — 2026-10-22

Resumed by explicit user instruction on 2026-10-22. The saved state below records
the pause, rather than a current execution restriction. Repository prerequisite
`repo.check` passed on resume. Completed comparison receipts were inspected;
the denied global process inspection was not retried or bypassed.

HEAD is c3ae753f1322e9f146a342e7cdda9c0aab4e9508 on the isolated performance
checkout. Twelve staged files preserve the report, workflow additions, and runtime
restoration. The working worker sources match 6a06b1d exactly; neither serial
handle candidate is selected. No closing commit was made before this pause.

Results and repeat commands: `docs/serial-recovery-handles.md`. Final receipt:
`bin/.local/glider-comparison/serial-recovery-only-v1/final-audit.json`.
54 fresh processes completed 8,856 semantic checks. Full recovery improved from
158.8 to 143.2 ms unpaced and 158.0 to 134.4 ms paced, but small reference p90
regressed 11.2% and 7.3%. All unfavorable evidence remains.

No benchmark was known to be running at the completed measurement checkpoint.
The closing repo.check session 7895 is no longer available; its terminal result
was truncated and is unconfirmed. A final process-list inspection was denied by
the sandbox (`ps: operation not permitted`), so absence of surviving processes
was not independently verified. No process was killed and no service changed.

After explicit resume: first inspect any surviving task-owned processes and
recover the closing repo.check result; if unavailable, rerun only that repository
check. Review staged scope and commit the retained evidence/runtime restoration
locally. Do not launch another benchmark matrix without a specific hypothesis.
