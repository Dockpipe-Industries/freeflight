"""Retain exact upstream source archives and their original license/notice files."""
import hashlib
import json
import pathlib
import tarfile
import urllib.request
import sys
import os

ROOT = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'workflows/site.build/assets'))
from provenance import capture, finish
PROVENANCE = capture(ROOT)
OUT = ROOT / 'bin/.local/site-sources'
OUT.mkdir(parents=True, exist_ok=True)
TOOLCHAIN = json.loads((ROOT / 'site/toolchain.json').read_text())
QT = TOOLCHAIN['qt']
PINS = TOOLCHAIN['qtSources']
notices = [f'FreeFlight Qt{QT} corresponding source and original notices.\nApplication: Apache-2.0; Qt and bundled dependencies retain their original licenses.\n']
for module, expected in PINS.items():
    name = module + '-everywhere-src-' + QT + '.tar.xz'
    target = OUT / name
    if not target.exists():
        temporary = OUT / (name + '.part')
        urllib.request.urlretrieve('https://download.qt.io/official_releases/qt/' + '.'.join(QT.split('.')[:2]) + '/' + QT + '/submodules/' + name, temporary)
        if hashlib.sha256(temporary.read_bytes()).hexdigest() != expected:
            raise RuntimeError('Qt source archive checksum mismatch: ' + name)
        temporary.rename(target)
    if hashlib.sha256(target.read_bytes()).hexdigest() != expected:
        raise RuntimeError('Cached Qt source checksum mismatch: ' + name)
    with tarfile.open(target, 'r:xz') as archive:
        for item in archive:
            basename = pathlib.PurePosixPath(item.name).name.lower()
            if item.isfile() and item.size < 2_000_000 and (basename.startswith(('license', 'copying', 'copyright')) or '/LICENSES/' in item.name):
                data = archive.extractfile(item).read().decode('utf-8', errors='replace')
                notices.append('\n===== ' + item.name + ' =====\n' + data)
# Runtime code is emitted into JS/WASM; Qt archive notices do not cover this SDK code.
receipt_path = ROOT / 'bin/.local/site-toolchain/toolchain.json'
if os.environ.get('FREEFLIGHT_EMSDK_ROOT'):
    sdk_root = pathlib.Path(os.environ['FREEFLIGHT_EMSDK_ROOT']).resolve()
else:
    receipt = json.loads(receipt_path.read_text())
    if receipt['emsdk'] != TOOLCHAIN['emsdk'] or receipt['emsdkCommit'] != TOOLCHAIN['emsdkCommit']:
        raise RuntimeError('Runtime notice collection requires the pinned Emscripten SDK')
    sdk_root = pathlib.Path(receipt['emsdkRoot'])
runtime = sdk_root / 'upstream/emscripten'
if (runtime / 'emscripten-version.txt').read_text().strip().strip('"') != TOOLCHAIN['emsdk']:
    raise RuntimeError('Emscripten runtime notice version differs from pinned toolchain')
with tarfile.open(OUT / 'emscripten-runtime-notices.tar.gz', 'w:gz') as archive:
    for name, expected in TOOLCHAIN['runtimeNotices'].items():
        path = runtime / name
        if path.is_symlink() or not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != expected:
            raise RuntimeError('Missing or altered pinned Emscripten runtime notice: ' + name)
        archive.add(path, arcname='emscripten/' + name)
        notices.append('\n===== Emscripten ' + TOOLCHAIN['emsdk'] + '/' + name + ' =====\n' + path.read_text())
(OUT / 'runtime-notice-checksums.json').write_text(json.dumps({'emscriptenVersion': TOOLCHAIN['emsdk'], 'sourceCommit': TOOLCHAIN['emscriptenSourceCommit'], 'files': TOOLCHAIN['runtimeNotices']}, indent=2) + '\n')
(OUT / 'NOTICES.txt').write_text('\n'.join(notices))
(OUT / 'source-checksums.json').write_text(json.dumps(PINS, indent=2) + '\n')
with tarfile.open(OUT / 'freeflight-site-relink-source.tar.gz', 'w:gz') as archive:
    for path in (ROOT / 'site', ROOT / 'workflows/site.build', ROOT / 'workflows/site.toolchain', ROOT / 'workflows/site.sources', ROOT / 'LICENSE', ROOT / '.gitignore'):
        archive.add(path, arcname=str(path.relative_to(ROOT)), filter=lambda item: None if '__pycache__' in item.name else item)
(OUT / 'verification.json').write_text(json.dumps({**finish(ROOT, PROVENANCE), 'qtVersion': QT, 'artifacts': {path.name: hashlib.sha256(path.read_bytes()).hexdigest() for path in [OUT / (module + '-everywhere-src-' + QT + '.tar.xz') for module in PINS] + [OUT / name for name in ('NOTICES.txt', 'source-checksums.json', 'freeflight-site-relink-source.tar.gz', 'emscripten-runtime-notices.tar.gz', 'runtime-notice-checksums.json')]}}, indent=2) + '\n')
print('Qt corresponding source, original notices, and application relink source retained: ' + str(OUT))
