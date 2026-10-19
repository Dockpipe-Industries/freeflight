"""Fixed generated-output cleanup; no arbitrary paths or recursive repo cleaning."""
import json
import os
from pathlib import Path
import shutil
import sys

REPO = Path(__file__).resolve().parents[3]
TARGETS = {"core": "build", "typescript": "typescript", "roslyn": "roslyn"}


def reject_link(path):
    if path.is_symlink() or (hasattr(path, "is_junction") and path.is_junction()):
        raise ValueError("Cleanup refuses symlinks or junctions: " + str(path))


def clean(repo, selection, apply=False):
    if selection not in TARGETS:
        raise ValueError("Select exactly one FREEFLIGHT_CLEAN_TARGET: core, typescript, roslyn")
    repo = Path(repo).resolve(strict=True)
    target = repo / "bin" / ".local" / TARGETS[selection]
    for path in (repo / "bin", repo / "bin/.local", target):
        reject_link(path)
        if path.exists() and not path.is_dir():
            raise ValueError("Cleanup target ancestors must be directories")
    if target.resolve().parent != (repo / "bin/.local").resolve():
        raise ValueError("Cleanup path escaped generated root")
    exists = target.exists()
    if exists:
        for base, directories, files in os.walk(target, followlinks=False):
            for name in directories + files:
                reject_link(Path(base) / name)
    if apply and exists:
        # Refuse platforms without Python's descriptor-based deletion protection.
        if not shutil.rmtree.avoids_symlink_attacks:
            raise ValueError("Safe recursive removal unavailable; preview only on this Python")
        shutil.rmtree(target)
    return {"target": str(target), "exists": exists, "applied": apply and exists}


if __name__ == "__main__":
    try:
        mode = os.environ.get("FREEFLIGHT_CLEAN_MODE", "preview")
        if mode not in ("preview", "apply"):
            raise ValueError("FREEFLIGHT_CLEAN_MODE must be preview or apply")
        print(json.dumps(clean(REPO, os.environ.get("FREEFLIGHT_CLEAN_TARGET", ""), mode == "apply")))
    except (ValueError, OSError) as error:
        print(str(error), file=sys.stderr)
        sys.exit(2)
