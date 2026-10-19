"""Stage the locked browser-test graph for DockPipe's native npm audit step."""
import pathlib
import shutil

root = pathlib.Path(__file__).resolve().parents[3]
stage = root / 'bin/.local/audit-site-tooling'
stage.mkdir(parents=True, exist_ok=True)
for name in ('package.json', 'package-lock.json'):
    shutil.copy2(root / 'workflows/site.test/assets/tooling' / name, stage / name)
