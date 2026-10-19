# Agent guidance

Start at AGENTS.md, select a task in index.yaml, then read only its focused files.
The router uses DockPipe Cloud's actual schema 1: tasks keyed by category, with
read, optional, skills and validation lists. task-index.yaml uses its schema 2
open-only task records (id, topic, path, dispatch). These files route; canonical
product details remain in docs/README.md, worker README files and actual code.

Bootstrap inspection: DockPipe's public packages/dorkpipe/workflows/example.brain
seeds brain/index.md, source-of-truth-rules.md, repo-knowledge.md and open-gaps.md.
Its config declares windows/deb, Docker sidecars, Ollama and cloud agent lanes;
it does not generate a complete YAML router or scoped AGENTS files. Cloud's
reusable-product-repo-starter remains a proposed extraction. We reuse those
four baseline roles and the current Cloud schemas directly; we do not install
or duplicate its orchestrator merely to author repository instructions.

Validate every route and open task using repo.check before implementation resumes.
Agent instructions are an explicit prerequisite, not a retrospective checkbox.

Current-package follow-up: DorkPipe was extracted to Dockpipe-Industries/dorkpipe.
Inspected js/dev commit c284f0438b0d1c589cf2860742ffec7ba86c8678, package 0.6.5
(not the older DockPipe master embedded 0.6.2). Its example.brain still declares
windows/deb and configured Docker/provider access. software.dev supports selected
consumer task packs, not a complete deterministic router scaffold. No package
download or provider launch is needed merely to inspect these official files.
