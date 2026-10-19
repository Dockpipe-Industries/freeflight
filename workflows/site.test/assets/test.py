"""Provision isolated browser tooling and test the built site, without system installs."""
import functools
import http.server
import os
import pathlib
import shutil
import subprocess
import threading

ROOT = pathlib.Path(__file__).resolve().parents[3]
TOOLS = ROOT / 'bin/.local/site-test-tools'
OUT = ROOT / 'bin/.local/site-test'
TOOLS.mkdir(parents=True, exist_ok=True)
OUT.mkdir(parents=True, exist_ok=True)
for name in ('package.json', 'package-lock.json'):
    shutil.copy2(pathlib.Path(__file__).parent / 'tooling' / name, TOOLS / name)
shutil.copy2(pathlib.Path(__file__).parent / 'smoke.mjs', TOOLS / 'smoke.mjs')
env = dict(os.environ, PLAYWRIGHT_BROWSERS_PATH=str(TOOLS / 'browsers'))
subprocess.run(['npm', 'ci', '--ignore-scripts', '--no-fund', '--no-audit'], cwd=TOOLS, env=env, check=True, timeout=300)
subprocess.run(['node', TOOLS / 'node_modules/playwright/cli.js', 'install', 'chromium'], env=env, check=True, timeout=600)
handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(ROOT / 'bin/.local/site'))
with http.server.ThreadingHTTPServer(('127.0.0.1', 0), handler) as server:
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        subprocess.run(['node', TOOLS / 'smoke.mjs', f'http://127.0.0.1:{server.server_port}', OUT], env=env, check=True, timeout=240)
    finally:
        server.shutdown()
