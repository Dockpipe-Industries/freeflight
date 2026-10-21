"""Bounded hostname replacement; no bootstrap, identities, activation or access changes."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

OLD = 'freeflight.staging.dockpipe.com'
NEW = 'freeflight-staging.dockpipe.com'
FILES = ('/etc/nginx/conf.d/freeflight-staging.conf', '/usr/local/lib/freeflight/receive.py')


def replacement(data, expected, count):
    if hashlib.sha256(data).hexdigest() != expected or data.count(OLD.encode()) != count:
        raise ValueError('Existing file differs from reviewed hostname-only input')
    return data.replace(OLD.encode(), NEW.encode())


def replace_file(path, data):
    metadata = path.stat()
    descriptor, temporary = tempfile.mkstemp(prefix='.freeflight-hostname-', dir=path.parent)
    try:
        with os.fdopen(descriptor, 'wb') as output:
            output.write(data)
            output.flush()
            os.fsync(output.fileno())
            os.fchmod(output.fileno(), metadata.st_mode & 0o777)
            if os.geteuid() == 0:
                os.fchown(output.fileno(), metadata.st_uid, metadata.st_gid)
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def migrate(payload, root=Path('/'), run=subprocess.run):
    if set(payload) != {'hashes'} or set(payload['hashes']) != set(FILES):
        raise ValueError('Unexpected migration scope')
    marker = root / 'var/lib/freeflight-bootstrap/owner.json'
    if marker.is_symlink() or json.loads(marker.read_text()) != {'product': 'freeflight', 'environment': 'staging'}:
        raise ValueError('Unowned receiver')
    current = root / 'srv/freeflight-staging/current'
    if current.exists() or current.is_symlink():
        raise ValueError('Hostname migration requires an inactive site')
    snapshots = {}
    updates = {}
    for name, count in zip(FILES, (3, 1)):
        path = root / name.lstrip('/')
        if path.is_symlink() or path.resolve() != path or path.stat().st_mode & 0o022:
            raise ValueError('Unsafe receiver file')
        data = path.read_bytes()
        snapshots[path] = data
        updates[path] = replacement(data, payload['hashes'][name], count)
    run(['nginx', '-t'], check=True, capture_output=True)
    try:
        for path, data in updates.items():
            if path.read_bytes() != snapshots[path]:
                raise ValueError('Concurrent receiver modification')
            replace_file(path, data)
        run(['nginx', '-t'], check=True, capture_output=True)
        run(['systemctl', 'reload', 'nginx'], check=True, capture_output=True)
    except Exception:
        for path, data in snapshots.items():
            # Never overwrite an unrelated concurrent modification during rollback.
            if path.read_bytes() in (data, updates[path]):
                replace_file(path, data)
            else:
                raise RuntimeError('Concurrent change prevents safe rollback')
        run(['nginx', '-t'], check=True, capture_output=True)
        run(['systemctl', 'reload', 'nginx'], check=True, capture_output=True)
        raise
    for path, data in updates.items():
        if path.read_bytes() != data:
            raise RuntimeError('Hostname migration readback mismatch')
    print(json.dumps({'hostname': NEW, 'files': {str(p): hashlib.sha256(v).hexdigest() for p, v in updates.items()},
                      'site_activated': False}))


if __name__ == '__main__':
    try:
        if os.geteuid() != 0:
            raise ValueError('Existing operator authority required')
        migrate(json.load(sys.stdin))
    except Exception:
        print('Hostname migration failed; inspect live files before retry.', file=sys.stderr)
        sys.exit(1)
