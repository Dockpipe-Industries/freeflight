"""Cross-platform executable selection; DockPipe owns the development entry point."""
import os
from pathlib import Path
import subprocess
import sys

REPO = Path(__file__).resolve().parents[3]


def command(config):
    path = Path(config)
    if not config or not path.is_absolute() or not path.is_file():
        raise ValueError("Set FREEFLIGHT_CONFIG to an absolute existing configuration file")
    executable = REPO / "bin/.local/build" / ("Release/freeflight.exe" if os.name == "nt" else "freeflight")
    if not executable.is_file():
        raise ValueError("Build the core first: dockpipe --workflow core.build")
    return [str(executable), "--config", str(path)]


if __name__ == "__main__":
    try:
        sys.exit(subprocess.call(command(os.environ.get("FREEFLIGHT_CONFIG", ""))))
    except (ValueError, OSError) as error:
        print(str(error), file=sys.stderr)
        sys.exit(2)
