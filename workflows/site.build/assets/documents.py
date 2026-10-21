"""Allowlisted, source-versioned public guides; no filesystem access at runtime."""
import hashlib
import json
import pathlib
import subprocess

PAGES = [
    ('Start here', 'README.md', 'Overview'),
    ('Start here', 'docs/README.md', 'Configuration'),
    ('Start here', 'docs/workspaces.md', 'Workspaces and trust'),
    ('Reference', 'docs/capabilities.md', 'Language capabilities'),
    ('Reference', 'SECURITY.md', 'Security boundaries'),
    ('Development', 'docs/development.md', 'Build and contribute'),
    ('Development', 'docs/distribution.md', 'Distribution'),
]

def collect(root):
    revision = subprocess.check_output(['git', '-C', str(root), 'rev-parse', 'HEAD'], text=True).strip()
    result = []
    modified = False
    for group, name, title in PAGES:
        path = (root / name).resolve(strict=True)
        if root.resolve() not in path.parents or path.stat().st_size > 2 * 1024 * 1024:
            raise ValueError('Unsafe documentation source')
        raw = path.read_bytes()
        committed = subprocess.check_output(['git', '-C', str(root), 'show', revision + ':' + name])
        modified = modified or raw != committed
        result.append({'id': name, 'group': group, 'title': title, 'markdown': raw.decode(),
                       'sha256': hashlib.sha256(raw).hexdigest(),
                       'source': 'https://github.com/Dockpipe-Industries/freeflight/blob/' + revision + '/' + name})
    return {'revision': revision, 'workingTreeChanges': modified, 'pages': result}

def bundle(root, stage, run, env):
    tools = root / 'bin/.local/site-docs-tools'
    tools.mkdir(parents=True, exist_ok=True)
    source = root / 'workflows/site.build/assets/browser'
    for name in ('package.json', 'package-lock.json'):
        (tools / name).write_bytes((source / name).read_bytes())
    run(['npm', 'ci', '--ignore-scripts', '--no-audit', '--no-fund'], cwd=tools, env=env)
    (tools / 'reader.mjs').write_bytes((source / 'reader.mjs').read_bytes())
    (tools / 'documents.json').write_text(json.dumps(collect(root)))
    run(['node', tools / 'node_modules/esbuild/bin/esbuild', tools / 'reader.mjs', '--bundle', '--format=iife', '--minify', '--outfile=' + str(tools / 'reader.js')], env=env)
    loader = stage / 'loader.js'
    loader.write_text((tools / 'reader.js').read_text() + '\n' + loader.read_text())
    with (stage / 'NOTICES.txt').open('a') as notices:
        for package, filename in [('marked', 'LICENSE'), ('dompurify', 'LICENSE'), ('dompurify', 'LICENSE-MPL'), ('highlight.js', 'LICENSE')]:
            notices.write('\n\nDocumentation renderer: ' + package + '\n')
            notices.write((tools / 'node_modules' / package / filename).read_text())
