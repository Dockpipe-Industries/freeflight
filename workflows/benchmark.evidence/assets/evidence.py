"""Compact historical evidence; never builds, benchmarks, uploads or deletes inputs."""
import argparse
import gzip
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import subprocess

REPO = Path(__file__).resolve().parents[3]
MAX_BLOB = 1024 * 1024
MAX_SET = 10 * 1024 * 1024
MAX_RAW = 256 * 1024 * 1024
PRUNE = {'bin', 'obj', 'node_modules', '.git', '_deps', 'source', 'build',
         'profile-source', 'profile-build', 'baseline-source', 'candidate-source',
         'core-source', 'worker-source', 'driver-source'}
PRUNE_PARTS = ('fixture', '-build', '-source', 'sdk', 'toolchain', 'cache', 'collector')
PRIVATE_KEY = re.compile(rb'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----')


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def safe_relative(name):
    p = PurePosixPath(name)
    if not p.parts or p.as_posix() != name or p.is_absolute() or '..' in p.parts or '\\' in name:
        raise ValueError('Unsafe evidence path')
    return p


def discover(root):
    """JSON measurements/metadata only; no generated inputs, binaries or bulk logs."""
    for base, dirs, files in os.walk(root, followlinks=False):
        dirs[:] = sorted(n for n in dirs if not (Path(base, n).is_symlink()
                        or n in PRUNE or any(s in n for s in PRUNE_PARTS)))
        for name in sorted(files):
            p = Path(base, name)
            if p.suffix in ('.json', '.jsonl') and not p.is_symlink():
                yield p


def pack(path, objects):
    if path.stat().st_size > MAX_RAW:
        raise ValueError('Evidence input exceeds bounded reader: ' + str(path))
    temporary = objects / 'pending.gz'
    h = hashlib.sha256()
    count = 0
    tail = b''
    with path.open('rb') as source, temporary.open('wb') as raw:
        with gzip.GzipFile(filename='', mode='wb', fileobj=raw, mtime=0, compresslevel=6) as target:
            for chunk in iter(lambda: source.read(1024 * 1024), b''):
                count += len(chunk)
                if count > MAX_RAW or PRIVATE_KEY.search(tail + chunk):
                    raise ValueError('Oversized input or private-key marker')
                tail = chunk[-128:]
                h.update(chunk)
                target.write(chunk)
    key = h.hexdigest()
    target = objects / (key + '.gz')
    if target.exists():
        if digest(temporary) != digest(target):
            raise ValueError('Non-deterministic compressed object')
        temporary.unlink()
    else:
        temporary.rename(target)
    return dict(sha256=key, bytes=count, gzipSha256=digest(target), gzipBytes=target.stat().st_size)


def priority(entry):
    name = PurePosixPath(entry['path'])
    # Summaries/provenance first, then recent raw measurements. Never sample within a file.
    raw = name.name in ('samples.json', 'tails.json') or name.suffix == '.jsonl'
    recent = name.parts[0] in ('reference-context', 'response-copies', 'definition-cost', 'allocations')
    return (not recent, raw, entry['gzipBytes'], entry['path'])


def capture(source, output, git_output, max_blob=MAX_BLOB, max_set=MAX_SET):
    if source.is_symlink():
        raise ValueError('Source directory is a symlink')
    source = source.resolve()
    if not source.is_dir():
        raise ValueError('Missing source directory')
    for dest in (output, git_output):
        if dest.exists() or source in dest.resolve().parents or dest.resolve() == source:
            raise ValueError('Outputs must be fresh and outside source')
    output.mkdir(parents=True)
    objects = output / 'objects'
    objects.mkdir()
    entries = []
    for path in discover(source):
        relative = path.relative_to(source).as_posix()
        safe_relative(relative)
        entries.append(dict(path=relative, **pack(path, objects)))
    chosen, selected = set(), 0
    # Reserve space for the complete catalog, which includes external objects too.
    reserve = len(json.dumps(entries).encode()) + len(entries) * 100 + 65536
    for entry in sorted(entries, key=priority):
        key = entry['sha256']
        fits = entry['gzipBytes'] <= max_blob and selected + entry['gzipBytes'] + reserve <= max_set
        if key in chosen or fits:
            if key not in chosen:
                chosen.add(key)
                selected += entry['gzipBytes']
            entry['storage'] = 'git'
        else:
            entry['storage'] = 'external'
    manifest = dict(schema=1, sourceCommit=subprocess.check_output(
        ['git', 'rev-parse', 'HEAD'], cwd=REPO, text=True).strip(), sourceRoot=str(source),
        limits=dict(blobBytes=max_blob, setBytes=max_set, decodedBytes=MAX_RAW),
        selection='Whole JSON/JSONL files, all phases intact; no individual observation exclusions',
        exclusions='Build/source/fixture/SDK/cache trees, bulk text logs, binaries and diagnostic traces',
        external='Unchanged original measurements: not reconstructible from source; optional external archive, not required to build/run',
        entries=sorted(entries, key=lambda x: x['path']))
    git_output.mkdir(parents=True)
    (git_output / 'objects').mkdir()
    for key in sorted(chosen):
        shutil.copyfile(objects / (key + '.gz'), git_output / 'objects' / (key + '.gz'))
    data = (json.dumps(manifest, indent=2) + '\n').encode()
    (git_output / 'manifest.json').write_bytes(data)
    (output / 'manifest.json').write_bytes(data)
    if len(data) + selected > max_set:
        raise ValueError('Complete Git evidence set exceeds budget')
    return verify(git_output, output)


def verify(directory, external=None):
    if directory.is_symlink() or (directory / 'manifest.json').is_symlink():
        raise ValueError('Evidence directory is a symlink')
    manifest = json.loads((directory / 'manifest.json').read_text())
    limits = manifest['limits']
    if manifest['schema'] != 1 or limits['blobBytes'] > MAX_BLOB or limits['setBytes'] > MAX_SET or limits['decodedBytes'] > MAX_RAW:
        raise ValueError('Invalid evidence budget/schema')
    seen, git_keys, external_keys = set(), set(), set()
    verified, identities = set(), {}
    for entry in manifest['entries']:
        safe_relative(entry['path'])
        if entry['path'] in seen or not re.fullmatch('[0-9a-f]{64}', entry['sha256']):
            raise ValueError('Duplicate/invalid evidence identity')
        seen.add(entry['path'])
        if entry['storage'] not in ('git', 'external') or not 0 <= entry['bytes'] <= limits['decodedBytes']:
            raise ValueError('Invalid evidence entry')
        key = entry['sha256']
        identity = tuple(entry[k] for k in ('bytes', 'gzipSha256', 'gzipBytes', 'storage'))
        if key in identities and identities[key] != identity:
            raise ValueError('Inconsistent duplicate object metadata')
        identities[key] = identity
        (git_keys if entry['storage'] == 'git' else external_keys).add(key)
        if key in verified:
            continue
        root = directory if entry['storage'] == 'git' else external
        if root is None:
            continue
        p = root / 'objects' / (key + '.gz')
        if p.is_symlink() or p.parent.is_symlink() or digest(p) != entry['gzipSha256'] or p.stat().st_size != entry['gzipBytes']:
            raise ValueError('Compressed evidence identity mismatch')
        if entry['storage'] == 'git' and p.stat().st_size > limits['blobBytes']:
            raise ValueError('Git blob exceeds budget')
        h, count = hashlib.sha256(), 0
        with gzip.open(p, 'rb') as f:
            for chunk in iter(lambda: f.read(1024 * 1024), b''):
                count += len(chunk)
                if count > limits['decodedBytes']:
                    raise ValueError('Decoded evidence exceeds budget')
                h.update(chunk)
        if count != entry['bytes'] or h.hexdigest() != key:
            raise ValueError('Decoded evidence identity mismatch')
        verified.add(key)
    actual = {p.stem for p in (directory / 'objects').iterdir()}
    if actual != git_keys or git_keys & external_keys:
        raise ValueError('Unlisted or inconsistently placed evidence object')
    size = sum(p.stat().st_size for p in directory.rglob('*') if p.is_file())
    if size > limits['setBytes']:
        raise ValueError('Git evidence set exceeds budget')
    return dict(status='passed',files=len(seen),gitObjects=len(git_keys),externalObjects=len(external_keys),
                verifiedObjects=len(verified),gitBytes=size,externalVerified=external is not None)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=('capture', 'verify'))
    args = parser.parse_args()
    if args.mode == 'capture':
        label = os.environ['FREEFLIGHT_EVIDENCE_LABEL']
        if not re.fullmatch('[A-Za-z0-9_-]+', label):
            raise ValueError('Invalid evidence label')
        result = capture(Path(os.environ['FREEFLIGHT_EVIDENCE_SOURCE']),
                         REPO / 'bin/.local/evidence' / label,
                         REPO / 'benchmarks/evidence' / label)
    else:
        result = [dict(label=p.parent.name, **verify(p.parent))
                  for p in sorted((REPO / 'benchmarks/evidence').glob('*/manifest.json'))]
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
