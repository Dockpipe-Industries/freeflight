"""Audit the locked browser-test graph in an isolated generated directory."""
import pathlib
import shutil
import subprocess

root = pathlib.Path(__file__).resolve().parents[3]
stage = root / 'bin/.local/audit-site-tooling'
stage.mkdir(parents=True, exist_ok=True)
for name in ('package.json', 'package-lock.json'):
    shutil.copy2(root / 'workflows/site.test/assets/tooling' / name, stage / name)
subprocess.run(['npm', 'audit', '--prefix', str(stage), '--package-lock-only', '--audit-level=high'], check=True, timeout=120)
