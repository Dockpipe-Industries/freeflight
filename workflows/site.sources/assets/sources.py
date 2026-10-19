"""Retain exact upstream source archives and their original license/notice files."""
import hashlib
import json
import pathlib
import tarfile
import urllib.request
import sys

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
(OUT / 'NOTICES.txt').write_text('\n'.join(notices))
(OUT / 'source-checksums.json').write_text(json.dumps(PINS, indent=2) + '\n')
with tarfile.open(OUT / 'freeflight-site-relink-source.tar.gz', 'w:gz') as archive:
    for path in (ROOT / 'site', ROOT / 'workflows/site.build', ROOT / 'workflows/site.toolchain', ROOT / 'workflows/site.sources', ROOT / 'LICENSE', ROOT / '.gitignore'):
        archive.add(path, arcname=str(path.relative_to(ROOT)), filter=lambda item: None if '__pycache__' in item.name else item)
(OUT / 'verification.json').write_text(json.dumps({**finish(ROOT, PROVENANCE), 'qtVersion': QT, 'artifacts': {path.name: hashlib.sha256(path.read_bytes()).hexdigest() for path in [OUT / (module + '-everywhere-src-' + QT + '.tar.xz') for module in PINS] + [OUT / name for name in ('NOTICES.txt', 'source-checksums.json', 'freeflight-site-relink-source.tar.gz')]}}, indent=2) + '\n')
print('Qt corresponding source, original notices, and application relink source retained: ' + str(OUT))
