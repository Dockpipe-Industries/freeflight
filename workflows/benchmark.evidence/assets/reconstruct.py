"""Reconstruct rejected source candidates using Git plus patches; no compiler/build."""
import hashlib
import json
from pathlib import Path
import re
import subprocess
import tempfile

from evidence import REPO, safe_relative


def verify():
    root = REPO / 'benchmarks/reconstruction'
    manifest = json.loads((root / 'manifest.json').read_text())
    if manifest['schema'] != 1:
        raise ValueError('Unknown reconstruction schema')
    seen = set()
    for entry in manifest['candidates']:
        relative = safe_relative(entry['path'])
        patch = root / relative
        if str(relative) in seen or patch.is_symlink() or patch.stat().st_size > 1024 * 1024:
            raise ValueError('Duplicate/invalid candidate patch')
        seen.add(str(relative))
        if hashlib.sha256(patch.read_bytes()).hexdigest() != entry['sha256']:
            raise ValueError('Candidate patch identity mismatch')
        if not entry['appliesToBase'] or not re.fullmatch('[0-9a-f]{40}', entry['baseCommit']):
            raise ValueError('Candidate reconstruction unqualified')
        with tempfile.TemporaryDirectory() as directory:
            temp = Path(directory)
            for name in entry['resultHashes']:
                p = temp / safe_relative(name)
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_bytes(subprocess.check_output(
                    ['git', 'show', entry['baseCommit'] + ':' + name], cwd=REPO))
            subprocess.run(['git', 'apply', '--check', str(patch)], cwd=temp, check=True)
            subprocess.run(['git', 'apply', str(patch)], cwd=temp, check=True)
            for name, expected in entry['resultHashes'].items():
                if hashlib.sha256((temp / name).read_bytes()).hexdigest() != expected:
                    raise ValueError('Reconstructed candidate identity mismatch')
    if seen != {p.relative_to(root).as_posix() for p in root.glob('*/*.patch')}:
        raise ValueError('Unlisted candidate patch')
    print('Source reconstruction passed:', len(seen), 'rejected candidates; no old builds needed')


if __name__ == '__main__':
    verify()
