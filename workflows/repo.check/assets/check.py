"""Repository-local repo.check asset, following DockPipe Cloud's workflow layout."""
from pathlib import Path
import subprocess
import re
import yaml

root = Path(__file__).resolve().parents[3]
required = [".gitattributes", "AGENTS.md", "LICENSE", "README.md", "VERSION", "CMakeLists.txt",
            "dockpipe.config.json", "docs/acceptance.md", "docs/task-log.md",
            "src/main.cpp", "site/index.html", "workflows/core.build/config.yml"]
required += ["docs/agents/index.yaml", "docs/agents/task-index.yaml", "docs/agents/README.md",
             "docs/agents/brain/index.md", "src/AGENTS.md", "workers/AGENTS.md",
             "workflows/AGENTS.md", "site/AGENTS.md"]
for item in required:
    if not (root / item).is_file():
        raise SystemExit(f"Missing required file: {item}")
tracked = subprocess.check_output(["git", "ls-files", "-z"], cwd=root).decode().split("\0")
for item in filter(None, tracked):
    path = Path(item)
    if path.parts[0] in {"bin", "build"} or any(
            part in {"node_modules", "obj", "__pycache__"} for part in path.parts):
        raise SystemExit(f"Tracked generated output: {item}")
    if path.suffix in {".exe", ".dll", ".dylib", ".so", ".o", ".a", ".pyc"}:
        raise SystemExit(f"Tracked binary: {item}")
    file = root / path
    if file.is_file():
        data = file.read_bytes()
        if re.search(rb"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----", data):
            raise SystemExit(f"Private-key marker: {item}")
routes = yaml.safe_load((root / "docs/agents/index.yaml").read_text())
backlog = yaml.safe_load((root / "docs/agents/task-index.yaml").read_text())
assert routes.get("schema") == 1 and isinstance(routes.get("tasks"), dict)
assert backlog.get("schema") == 2 and isinstance(backlog.get("tasks"), list)

def require_reference(reference):
    assert isinstance(reference, str), "Reference must be a string"
    path = (root / reference).resolve()
    assert root in path.parents and path.is_file(), f"Missing/external reference: {reference}"

for name, route in routes["tasks"].items():
    assert isinstance(route.get("read"), list) and route["read"], name
    assert isinstance(route.get("skills"), list), name
    for reference in route["read"] + route.get("optional", []):
        require_reference(reference)
ids, paths = set(), set()
for task in backlog["tasks"]:
    identifier, path = task["id"], task["path"]
    assert identifier.startswith("TASK-") and identifier not in ids
    assert path not in paths and "/closed/" not in path
    require_reference(path)
    assert set(task["dispatch"]) >= {"readiness", "ownership"}
    ids.add(identifier)
    paths.add(path)
assert set(routes["tasks"]) >= {"core_protocol", "language_engines", "dockpipe_workflows",
    "security_or_dependencies", "release_or_registry", "website_or_marketing", "agent_guidance_or_tasks"}
assert "no duplicate FreeFlight-specific DockPipe package" in (root / "AGENTS.md").read_text()
print(f"Required files, tracked hygiene, {len(routes['tasks'])} routes and {len(ids)} open tasks passed")
