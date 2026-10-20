import hashlib
import json
import os
from pathlib import Path
import tempfile
import unittest
from remote import FILES, OLD, NEW, migrate, replacement


class HostnameTest(unittest.TestCase):
    def test_reviewed_bytes_required(self):
        original = (OLD + '\n').encode()
        digest = hashlib.sha256(original).hexdigest()
        self.assertEqual(replacement(original, digest, 1), (NEW + '\n').encode())
        for data, expected, count in [(original + b'foreign', digest, 1),
                                       (original, '0' * 64, 1), (original, digest, 3)]:
            with self.assertRaises(ValueError):
                replacement(data, expected, count)

    @unittest.skipUnless(os.name == 'posix', 'Linux origin requires POSIX modes, ownership and atomic file APIs')
    def test_scope_and_rollback(self):
        for mode in ('success', 'modified', 'active', 'invalid-nginx', 'reload-failure'):
            with self.subTest(mode=mode), tempfile.TemporaryDirectory() as directory:
                root = Path(directory).resolve()
                marker = root / 'var/lib/freeflight-bootstrap/owner.json'
                marker.parent.mkdir(parents=True)
                marker.write_text(json.dumps({'product': 'freeflight', 'environment': 'staging'}))
                snapshots = {}
                for name, count in zip(FILES, (3, 1)):
                    path = root / name.lstrip('/')
                    path.parent.mkdir(parents=True)
                    path.write_text((OLD + '\n') * count)
                    path.chmod(0o644)
                    snapshots[path] = path.read_bytes()
                payload = {'hashes': {name: hashlib.sha256((root / name.lstrip('/')).read_bytes()).hexdigest() for name in FILES}}
                if mode == 'modified':
                    payload['hashes'][FILES[0]] = '0' * 64
                if mode == 'active':
                    current = root / 'srv/freeflight-staging/current'
                    current.parent.mkdir(parents=True)
                    current.symlink_to('/nonexistent')
                calls = []
                def run(command, **kwargs):
                    calls.append(command)
                    if (mode == 'invalid-nginx' and len(calls) == 2) or (mode == 'reload-failure' and len(calls) == 3):
                        raise RuntimeError('fixture failure')
                if mode == 'success':
                    migrate(payload, root, run)
                    for path, data in snapshots.items():
                        self.assertEqual(path.read_bytes(), data.replace(OLD.encode(), NEW.encode()))
                else:
                    with self.assertRaises((ValueError, RuntimeError)):
                        migrate(payload, root, run)
                    for path, data in snapshots.items():
                        self.assertEqual(path.read_bytes(), data)
                    if mode in ('modified', 'active'):
                        self.assertEqual(calls, [])


if __name__ == '__main__':
    unittest.main()
