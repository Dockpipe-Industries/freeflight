"""Capture Git-visible source provenance; ignored generated outputs never participate."""
import hashlib
import os
import pathlib
import subprocess
import stat


def capture(root):
    def git(*args):
        return subprocess.run(['git', '-C', str(root), *args], check=True, capture_output=True).stdout
    dirty = bool(git('status', '--porcelain', '--untracked-files=normal').strip())
    if os.environ.get('CI', '').lower() in ('true', '1') and dirty:
        raise RuntimeError('CI website qualification requires a clean source checkout')
    digest = hashlib.sha256()
    paths = set(git('ls-files', '-z', '--cached', '--others', '--exclude-standard').split(b'\0'))
    for name in sorted(paths - {b''}):
        path = pathlib.Path(root) / os.fsdecode(name)
        digest.update(name + b'\0')
        if path.exists() or path.is_symlink():
            digest.update(str(stat.S_IMODE(path.lstat().st_mode)).encode() + b'\0')
        if path.is_symlink():
            digest.update(b'link\0' + os.fsencode(os.readlink(path)))
        elif path.is_file():
            digest.update(b'file\0' + path.read_bytes())
        else:
            digest.update(b'missing\0')
        digest.update(b'\0')
    return {'sourceCommit': git('rev-parse', 'HEAD').decode().strip(),
            'sourceTree': git('rev-parse', 'HEAD^{tree}').decode().strip(),
            'sourceDirty': dirty, 'workingSourceSha256': digest.hexdigest()}


def finish(root, before):
    if capture(root) != before:
        raise RuntimeError('Source changed during website qualification; rerun from a stable checkout')
    return before
