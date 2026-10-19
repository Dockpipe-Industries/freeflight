"""Explicit DockPipe toolchain provisioning, isolated beneath bin/.local."""
import json
import os
import pathlib
import platform
import subprocess
import sys

REPO = pathlib.Path(__file__).resolve().parents[3]
ROOT = REPO / "bin/.local/site-toolchain"
PINS = json.loads((REPO / "site/toolchain.json").read_text())
QT = PINS["qt"]
EMSDK = PINS["emsdk"]
EMSDK_COMMIT = PINS["emsdkCommit"]


def run(args, **kwargs):
    return subprocess.run([str(arg) for arg in args], check=True, timeout=1800, **kwargs)


def main():
    host = {"Darwin": ("mac", "clang_64", "macos"), "Linux": ("linux", "linux_gcc_64", "gcc_64")}.get(platform.system())
    if not host:
        raise RuntimeError("Website toolchain provisioning currently supports macOS and Linux hosts")
    if ROOT.is_symlink():
        raise RuntimeError("Toolchain root cannot be a symlink")
    ROOT.mkdir(parents=True, exist_ok=True)
    logs = ROOT / "logs"
    logs.mkdir(exist_ok=True)
    venv = ROOT / "aqt-venv"
    if not (venv / "bin/python").exists():
        run([sys.executable, "-m", "venv", venv])
    python = venv / "bin/python"
    run([python, "-m", "pip", "install", "--disable-pip-version-check", "aqtinstall==" + PINS["aqt"]], cwd=logs)
    qt_root = ROOT / "Qt"
    host_root = qt_root / QT / host[2]
    wasm_root = qt_root / QT / "wasm_singlethread"
    if not (host_root / "bin/qt-cmake").exists():
        run([python, "-m", "aqt", "install-qt", "-O", qt_root, host[0], "desktop", QT, host[1]], cwd=logs)
    if not (wasm_root / "bin/qt-cmake").exists():
        run([python, "-m", "aqt", "install-qt", "-O", qt_root, "all_os", "wasm", QT, "wasm_singlethread"], cwd=logs)
    for relative in ("bin/qt-cmake", "bin/qt-cmake-create", "libexec/qt-cmake-private", "libexec/qt-cmake-standalone-test"):
        script = wasm_root / relative
        if script.exists():
            script.chmod(script.stat().st_mode | 0o111)
    sdk = ROOT / ("emsdk-" + EMSDK)
    if not sdk.exists():
        run(["git", "clone", "--branch", EMSDK, "--depth", "1", "https://github.com/emscripten-core/emsdk.git", sdk], cwd=logs)
    revision = run(["git", "-C", sdk, "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
    if revision != EMSDK_COMMIT:
        raise RuntimeError("Emscripten SDK checkout differs from the pinned reference commit")
    env = dict(os.environ, EM_CONFIG=str(sdk / ".emscripten"), EM_CACHE=str(ROOT / ("emscripten-cache-" + EMSDK)))
    run([sdk / "emsdk", "install", EMSDK], cwd=sdk, env=env)
    run([sdk / "emsdk", "activate", EMSDK], cwd=sdk, env=env)
    for path in (host_root / "bin/qt-cmake", wasm_root / "bin/qt-cmake", sdk / "upstream/emscripten/em++"):
        if not path.is_file():
            raise RuntimeError("Provisioned toolchain missing " + str(path))
    sdk_python = sorted((sdk / "python").glob("*/bin/python3"))
    emsdk_python = str(sdk_python[-1]) if sdk_python else sys.executable
    run([emsdk_python, "-c", "import sys; assert sys.version_info >= (3, 10), 'Emscripten requires Python3.10+'"])
    receipt = {"python": emsdk_python, "qt": QT, "emsdk": EMSDK, "emsdkCommit": revision, "hostRoot": str(host_root), "wasmRoot": str(wasm_root), "emsdkRoot": str(sdk), "emConfig": env["EM_CONFIG"], "emCache": env["EM_CACHE"]}
    (ROOT / "toolchain.json").write_text(json.dumps(receipt, indent=2) + "\n")
    print("Task-local Qt site toolchain ready: " + str(ROOT))


if __name__ == "__main__":
    main()
