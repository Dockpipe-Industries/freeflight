"""Unprivileged static activation using Cloud's bounded-bundle and atomic-link pattern."""
import base64
import gzip
import hashlib
import io
import json
import os
from pathlib import Path
import re
import signal
import sys
import tempfile
import time
from urllib.request import urlopen

HOSTS = {"staging": "freeflight-staging.dockpipe.com", "production": "freeflight.dockpipe.com"}
PUBLIC_FILES = {"NOTICES.txt", "freeflight-site.js", "freeflight-site.wasm", "index.html",
                "loader.js", "qtloader.js", "release.json", "review.html", "robots.txt", "styles.css"}
MAX_ARCHIVE = 64 * 1024 * 1024
MAX_DOCUMENT = 128 * 1024 * 1024
MAX_FILE = 48 * 1024 * 1024


def require(condition, message):
    if not condition:
        raise ValueError(message)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        require(key not in result, "Duplicate JSON field")
        result[key] = value
    return result


def decode(archive, expected, environment):
    require(environment in HOSTS and re.fullmatch("[a-f0-9]{64}", expected)
            and 0 < len(archive) <= MAX_ARCHIVE and digest(archive) == expected, "Invalid archive digest/size")
    with gzip.GzipFile(fileobj=io.BytesIO(archive)) as stream:
        raw = stream.read(MAX_DOCUMENT + 1)
    require(len(raw) <= MAX_DOCUMENT, "Expanded document exceeds limit")
    bundle = json.loads(raw, object_pairs_hook=unique_object)
    require(bundle.get("format") == 2 and bundle.get("product") == "freeflight"
            and bundle.get("mode") == "site", "Invalid product/schema")
    metadata = bundle["deployment"]
    require(metadata.get("schema") == 2 and metadata.get("environment") == environment
            and metadata.get("hostname") == HOSTS[environment]
            and metadata.get("prerelease") is (environment == "staging"), "Wrong deployment scope")
    for name in ("sourceCommit", "sourceTree", "promotedCommit"):
        require(re.fullmatch("[a-f0-9]{40}", metadata.get(name, "")), "Invalid source identity")
    version, tag = metadata.get("version", ""), metadata.get("releaseTag", "")
    require(re.fullmatch(r"\d+\.\d+\.\d+(?:-[A-Za-z0-9.-]+)?", version), "Invalid version")
    if environment == "production":
        require(re.fullmatch(r"\d+\.\d+\.\d+", version) and tag == "v" + version, "Stable production required")
    else:
        separator = ".staging." if "-" in version else "-staging."
        require(re.fullmatch(re.escape("v" + version + separator) + r"[1-9][0-9]*\." + metadata["sourceCommit"][:12], tag),
                "Invalid staging qualification tag")
    require(metadata.get("releaseUrl") == "https://github.com/Dockpipe-Industries/freeflight/releases/tag/" + tag,
            "Invalid release URL")
    expected_files = PUBLIC_FILES | ({"sitemap.xml"} if environment == "production" else set())
    files = bundle.get("files")
    require(isinstance(files, dict) and set(files) == expected_files, "Exact public file allowlist required")
    decoded = {}
    for name, entry in files.items():
        data = base64.b64decode(entry["content"], validate=True)
        require(0 < len(data) <= MAX_FILE and base64.b64encode(data).decode() == entry["content"]
                and digest(data) == entry["sha256"], "Invalid file bytes/hash")
        decoded[name] = data
    require(digest(decoded["release.json"]) == metadata.get("siteReleaseSha256"), "Site receipt changed")
    receipt = json.loads(decoded["release.json"], object_pairs_hook=unique_object)
    for name in ("sourceCommit", "sourceTree", "environment", "hostname"):
        require(receipt.get(name) == metadata[name], "Site source/scope mismatch")
    require(receipt.get("sourceDirty") is False, "Dirty source")
    assets = {name: digest(data) for name, data in decoded.items() if name != "release.json"}
    require(receipt.get("assets") == assets and metadata.get("assets") == assets, "Asset receipt mismatch")
    return metadata, decoded


def fetch(url, limit):
    with urlopen(url, timeout=3) as response:
        require(response.status == 200 and response.geturl() == url, "Unexpected health redirect/status")
        data = response.read(limit + 1)
    require(len(data) <= limit, "Oversized health response")
    return data


def probe(metadata, base):
    require(fetch(base + "/healthz", 32).strip() == b"ok", "Health failed")
    require(digest(fetch(base + "/release.json", 1024 * 1024)) == metadata["siteReleaseSha256"], "Wrong served receipt")
    for name, expected in metadata["assets"].items():
        require(digest(fetch(base + "/" + name, MAX_FILE)) == expected, "Wrong served asset")


def current_target(root):
    current = root / "current"
    if not current.is_symlink():
        require(not current.exists(), "Unowned current path")
        return None
    target = current.resolve(strict=True)
    require(target.parent == root / "releases" and target.is_dir(), "Current target outside owned releases")
    return target


def replace_link(root, target):
    temporary = root / "current.next"
    require(not temporary.exists() and not temporary.is_symlink(), "Unreconciled next link")
    temporary.symlink_to(target)
    os.replace(temporary, root / "current")


def activate(config, archive, expected, health=probe):
    metadata, files = decode(archive, expected, config["environment"])
    root = Path(config["root"])
    require(root.is_absolute() and root.resolve() == root and root.is_dir()
            and root.stat().st_uid == os.geteuid() and root.stat().st_mode & 0o022 == 0, "Unsafe serving root")
    releases = root / "releases"
    require(releases.is_dir() and not releases.is_symlink() and releases.stat().st_uid == os.geteuid()
            and releases.stat().st_mode & 0o022 == 0, "Unsafe releases directory")
    lock = root / "deploy.lock"
    descriptor = os.open(lock, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    reconciled = False
    try:
        os.write(descriptor, str(os.getpid()).encode())
        previous = current_target(root)
        candidate = Path(tempfile.mkdtemp(prefix="site-", dir=releases))
        for name, data in files.items():
            with (candidate / name).open("xb") as output:
                output.write(data)
            (candidate / name).chmod(0o644)
        (candidate / "activation.json").write_text(json.dumps({**metadata, "artifact": expected}) + "\n")
        (candidate / "activation.json").chmod(0o600)
        candidate.chmod(0o755)
        replace_link(root, candidate)
        base = "http://127.0.0.1:" + str(config["loopbackPort"])
        try:
            for attempt in range(5):
                try:
                    health(metadata, base)
                    break
                except Exception:
                    if attempt == 4:
                        raise
                    time.sleep(1)
        except Exception:
            if previous:
                replace_link(root, previous)
                old = json.loads((previous / "activation.json").read_text())
                health(old, base)
            else:
                (root / "current").unlink()
            reconciled = True
            raise
        reconciled = True
        return {**metadata, "artifact": expected, "status": "activated", "verifiedLocal": True}
    finally:
        os.close(descriptor)
        # Retain the lock for a failed rollback, interrupted write or uncertain state.
        if reconciled:
            lock.unlink()


def receive(config_path):
    require(os.geteuid() != 0, "Receiver must be unprivileged")
    path = Path(config_path)
    require(path.is_file() and not path.is_symlink() and path.stat().st_uid == 0
            and path.stat().st_mode & 0o022 == 0, "Configuration must be root-owned")
    config = json.loads(path.read_text())
    require(config.get("activationEnabled") is True and config["environment"] in HOSTS, "Receiver disabled")
    environment = config["environment"]
    require(config["root"] == "/srv/freeflight-" + environment and config["loopbackPort"] == 18080,
            "Fixed service scope required")
    command = re.fullmatch("deploy ([a-f0-9]{64})", os.environ.get("SSH_ORIGINAL_COMMAND", ""))
    require(command, "Only digest-selected static delivery accepted")
    def timeout(signum, frame):
        raise TimeoutError("Upload deadline exceeded")
    signal.signal(signal.SIGALRM, timeout)
    signal.alarm(60)
    archive = sys.stdin.buffer.read(MAX_ARCHIVE + 1)
    signal.alarm(0)
    signal.signal(signal.SIGHUP, signal.SIG_IGN)
    print(json.dumps(activate(config, archive, command[1])))


if __name__ == "__main__":
    try:
        require(len(sys.argv) == 3 and sys.argv[1] == "--receive", "Invalid receiver invocation")
        receive(sys.argv[2])
    except Exception:
        print("Static deployment failed; inspect retained candidate and lock before retrying.", file=sys.stderr)
        sys.exit(1)
