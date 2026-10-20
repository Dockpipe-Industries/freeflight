"""Restricted host-side activation. No arbitrary command, Compose, paths or mounts accepted."""
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import shutil
import socket
import subprocess
import sys
import tarfile
import tempfile
import time
from urllib.request import urlopen

HOSTS = {"staging": "freeflight.staging.dockpipe.com", "production": "freeflight.dockpipe.com"}
FILES = {"deployment.json", "image.tar.gz", "audit.json", "vulnerabilities.json"}


def require(value, message):
    if not value:
        raise ValueError(message)


def digest(path):
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def validate(directory, environment):
    metadata = json.loads((directory / "deployment.json").read_text())
    require(metadata.get("schema") == 1 and environment in HOSTS and
            metadata.get("environment") == environment and metadata.get("hostname") == HOSTS[environment],
            "Deployment environment mismatch")
    require(metadata.get("prerelease") is (environment == "staging"), "Wrong release channel")
    for key in ("sourceCommit", "sourceTree", "promotedCommit"):
        require(re.fullmatch("[a-f0-9]{40}", metadata.get(key, "")), "Invalid source identity")
    require(re.fullmatch(r"sha256:[a-f0-9]{64}", metadata.get("imageId", "")), "Invalid image ID")
    require(re.fullmatch("[a-f0-9]{64}", metadata.get("siteReleaseSha256", "")), "Invalid site hash")
    version, tag = metadata.get("version", ""), metadata.get("releaseTag", "")
    require(re.fullmatch(r"\d+\.\d+\.\d+(?:-[A-Za-z0-9.-]+)?", version), "Invalid version")
    if environment == "production":
        require(re.fullmatch(r"\d+\.\d+\.\d+", version) and tag == "v" + version, "Production needs stable release")
    else:
        require(re.fullmatch(r"v[0-9A-Za-z.-]+\.staging\.[1-9][0-9]*\.[a-f0-9]{12}", tag),
                "Staging tag lacks qualification identity")
    require(metadata.get("releaseUrl") == "https://github.com/Dockpipe-Industries/freeflight/releases/tag/" + tag,
            "Invalid published release URL")
    require(digest(directory / "image.tar.gz") == metadata.get("imageSha256"), "Image bytes changed")
    audit = json.loads((directory / "audit.json").read_text())
    require(audit.get("status") == "passed" and audit.get("imageArchiveSha256") == metadata["imageSha256"]
            and audit.get("ignoreUnfixed") is False and audit.get("severity") == ["HIGH", "CRITICAL"],
            "Image audit mismatch")
    require(digest(directory / "vulnerabilities.json") == audit.get("reportSha256"), "Audit report changed")
    results = json.loads((directory / "vulnerabilities.json").read_text()).get("Results")
    require(isinstance(results, list) and results and not any(
        v.get("Severity") in ("HIGH", "CRITICAL") for result in results for v in (result.get("Vulnerabilities") or [])),
        "Missing scan results or blocking vulnerabilities")
    assets = metadata.get("assets")
    require(isinstance(assets, dict) and assets and len(assets) <= 32, "Invalid site asset set")
    for name, expected in assets.items():
        require(re.fullmatch(r"[a-zA-Z0-9._-]+", name) and name not in (".", "..") and
                re.fullmatch("[a-f0-9]{64}", expected), "Invalid site asset")
    return metadata


def extract(archive, destination):
    with tarfile.open(archive, "r:") as bundle:
        entries = bundle.getmembers()
        require(len(entries) == len(FILES) and {e.name for e in entries} == FILES, "Unexpected delivery members")
        for entry in entries:
            limit = 512 * 1024 ** 2 if entry.name == "image.tar.gz" else 32 * 1024 ** 2
            require(entry.isfile() and 0 < entry.size <= limit, "Nonregular or oversized delivery member")
        for entry in entries:
            with bundle.extractfile(entry) as source, (destination / entry.name).open("xb") as output:
                shutil.copyfileobj(source, output)


def verify_image_archive(path, image_id, site_hash):
    """Reject unrelated tags/images before Docker's privileged import operation."""
    with tarfile.open(path, "r:gz") as archive:
        entries = archive.getmembers()
        names = [entry.name for entry in entries]
        require(len(names) == len(set(names)) and len(names) <= 256 and
                sum(entry.size for entry in entries) <= 2 * 1024 ** 3, "Invalid Docker archive size/layout")
        for entry in entries:
            allowed_file = entry.name in ("manifest.json", "index.json", "oci-layout", "repositories") or re.fullmatch(
                r"blobs/sha256/[a-f0-9]{64}", entry.name)
            require((entry.isdir() and entry.name in ("blobs", "blobs/sha256")) or
                    (entry.isfile() and allowed_file), "Unsafe Docker archive entry")
        def read_json(name):
            entry = archive.getmember(name)
            require(entry.size <= 4 * 1024 ** 2, "Oversized Docker metadata")
            return json.load(archive.extractfile(entry))
        manifest = read_json("manifest.json")
        tag = "freeflight-site:" + site_hash[:16]
        config_name = "blobs/sha256/" + image_id.removeprefix("sha256:")
        require(len(manifest) == 1 and manifest[0].get("RepoTags") == [tag]
                and manifest[0].get("Config") == config_name, "Docker archive targets unrelated image/tags")
        index = read_json("index.json")
        require(index.get("schemaVersion") == 2 and len(index.get("manifests", [])) == 1, "Multiple OCI images")
        descriptor = index["manifests"][0]
        require(re.fullmatch(r"sha256:[a-f0-9]{64}", descriptor.get("digest", "")), "Invalid OCI image descriptor")
        annotations = descriptor.get("annotations", {})
        require(annotations.get("io.containerd.image.name") == "docker.io/library/" + tag
                and annotations.get("org.opencontainers.image.ref.name") == site_hash[:16], "Unrelated OCI image alias")
        oci = read_json("blobs/sha256/" + descriptor["digest"][7:])
        require(oci.get("config", {}).get("digest") == image_id, "OCI config differs from expected image")
        require(manifest[0].get("Layers") == ["blobs/sha256/" + layer["digest"][7:] for layer in oci["layers"]],
                "Docker and OCI layers differ")
        if "repositories" in names:
            require(oci["layers"] and read_json("repositories") == {
                "freeflight-site": {site_hash[:16]: oci["layers"][-1]["digest"][7:]}},
                "Unrelated legacy Docker image alias")
        for entry in entries:
            if entry.isfile() and entry.name.startswith("blobs/sha256/"):
                value = hashlib.sha256()
                with archive.extractfile(entry) as stream:
                    for block in iter(lambda: stream.read(1024 * 1024), b""):
                        value.update(block)
                require(value.hexdigest() == entry.name.rsplit("/", 1)[1], "Docker blob checksum mismatch")


def fetch(url, limit):
    with urlopen(url, timeout=3) as response:
        require(response.status == 200 and response.geturl() == url, "Unexpected health redirect/status")
        data = response.read(limit + 1)
    require(len(data) <= limit, "Oversized health response")
    return data


def probe(metadata, base):
    require(fetch(base + "/healthz", 32).strip() == b"ok", "Health check failed")
    raw = fetch(base + "/release.json", 1024 * 1024)
    require(hashlib.sha256(raw).hexdigest() == metadata["siteReleaseSha256"], "Served release receipt differs")
    receipt = json.loads(raw)
    require(receipt.get("sourceCommit") == metadata["sourceCommit"] and receipt.get("sourceTree") == metadata["sourceTree"]
            and receipt.get("sourceDirty") is False and receipt.get("environment") == metadata["environment"]
            and receipt.get("hostname") == metadata["hostname"], "Served source identity differs")
    for name, expected in metadata["assets"].items():
        require(hashlib.sha256(fetch(base + "/" + name, 128 * 1024 ** 2)).hexdigest() == expected,
                "Served site asset differs: " + name)


def command(*args):
    return subprocess.check_output(list(args), text=True, stderr=subprocess.STDOUT, timeout=180)


def compose_text(environment, port, image):
    require(environment in HOSTS and type(port) is int and 1024 <= port <= 65535
            and re.fullmatch(r"sha256:[a-f0-9]{64}", image), "Invalid host service selection")
    return f"""name: freeflight-{environment}
services:
  site:
    image: {image}
    restart: unless-stopped
    ports: ["127.0.0.1:{port}:8080"]
    read_only: true
    tmpfs: ["/tmp:size=16m,mode=1777"]
    user: "101:101"
    cap_drop: [ALL]
    security_opt: ["no-new-privileges:true"]
    mem_limit: 64m
    cpus: 0.25
    pids_limit: 32
"""


def host_preflight(root, port, previous, archive):
    require(platform.system() == "Linux" and platform.machine() in ("x86_64", "AMD64"), "Receiver requires Linux x64")
    require(shutil.disk_usage(root).free >= 2 * archive.stat().st_size + 256 * 1024 ** 2, "Insufficient staging disk space")
    available = next((int(line.split()[1]) for line in Path("/proc/meminfo").read_text().splitlines()
                      if line.startswith("MemAvailable:")), 0)
    require(available >= 256 * 1024, "Insufficient host memory headroom")
    if previous is None:
        with socket.socket() as listener:
            listener.bind(("127.0.0.1", port))


def activate(config, directory, runner=command, verifier=probe):
    environment = config["environment"]
    metadata = validate(directory, environment)
    root = Path(config["root"])
    require(root.is_absolute() and root.is_dir() and root.resolve() == root, "Invalid operator-owned root")
    port = config["loopbackPort"]
    compose = root / "compose.yaml"
    current = root / "current.json"
    require(not compose.is_symlink() and not current.is_symlink(), "Unsafe activation state")
    previous = json.loads(current.read_text()) if current.exists() else None
    if previous:
        require(previous.get("environment") == environment and previous.get("loopbackPort") == port,
                "Previous service scope differs")
        compose_text(environment, port, previous.get("imageId", ""))
    compose_text(environment, port, metadata["imageId"])
    host_preflight(root, port, previous, directory / "image.tar.gz")
    require(not (root / "current.next.json").exists() and not (root / "current.next.json").is_symlink(),
            "Unreconciled activation state")
    project = "freeflight-" + environment
    prefix = ("docker", "compose", "-p", project, "-f", str(compose))
    # Existing service labels must match a recorded activation; never commandeer another project.
    existing = runner("docker", "ps", "-aq", "--filter", "label=com.docker.compose.project=" + project).strip()
    require(not existing or previous is not None, "Existing project has no activation receipt")
    runner("docker", "compose", "version")
    verify_image_archive(directory / "image.tar.gz", metadata["imageId"], metadata["siteReleaseSha256"])
    runner("docker", "load", "--input", str(directory / "image.tar.gz"))
    inspected = json.loads(runner("docker", "image", "inspect", metadata["imageId"]))
    require(len(inspected) == 1 and inspected[0]["Id"] == metadata["imageId"] and
            inspected[0]["Architecture"] == "amd64" and inspected[0]["Os"] == "linux", "Loaded image identity/platform differs")
    old_compose = compose.read_text() if compose.exists() else None
    require(previous is not None or old_compose is None, "Unowned Compose file exists")
    compose.write_text(compose_text(environment, port, metadata["imageId"]))
    try:
        runner(*prefix, "up", "-d", "--no-build", "--pull", "never")
        error = None
        for attempt in range(5):
            try:
                verifier(metadata, "http://127.0.0.1:" + str(port))
                verifier(metadata, "https://" + HOSTS[environment])
                error = None
                break
            except Exception as failure:
                error = failure
                if attempt < 4:
                    time.sleep(1)
        if error:
            raise error
    except Exception:
        if previous:
            compose.write_text(compose_text(environment, port, previous["imageId"]))
            runner(*prefix, "up", "-d", "--no-build", "--pull", "never")
            verifier(previous, "http://127.0.0.1:" + str(port))
            verifier(previous, "https://" + HOSTS[environment])
        else:
            runner(*prefix, "down", "--timeout", "10")
            compose.unlink()
        raise
    result = {**metadata, "loopbackPort": port, "status": "activated", "verifiedHttps": True}
    temporary = root / "current.next.json"
    require(not temporary.exists() and not temporary.is_symlink(), "Unreconciled activation state")
    temporary.write_text(json.dumps(result, indent=2) + "\n")
    temporary.replace(current)
    return result


def receive(path):
    require(path.is_file() and not path.is_symlink() and path.stat().st_uid == os.geteuid()
            and path.stat().st_mode & 0o022 == 0, "Receiver configuration must be owner-controlled")
    config = json.loads(path.read_text())
    environment = config["environment"]
    require(environment in HOSTS and config.get("activationEnabled") is True, "Receiver activation is disabled")
    match = re.fullmatch(r"deploy (staging|production) ([a-f0-9]{64})", os.environ.get("SSH_ORIGINAL_COMMAND", ""))
    require(match and match[1] == environment, "Only the configured environment deploy command is permitted")
    root = Path(config["root"])
    require(root.is_absolute() and root.is_dir() and root.resolve() == root and
            root.stat().st_uid == os.geteuid() and root.stat().st_mode & 0o022 == 0, "Unsafe receiver root")
    lock = root / "deploy.lock"
    descriptor = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    os.close(descriptor)
    completed = False
    try:
        directory = Path(tempfile.mkdtemp(prefix="candidate-", dir=root))
        archive = directory / "delivery.tar"
        with archive.open("xb") as output:
            total = 0
            while block := sys.stdin.buffer.read(1024 * 1024):
                total += len(block)
                require(total <= 600 * 1024 ** 2, "Oversized delivery stream")
                output.write(block)
        require(digest(archive) == match[2], "Transferred delivery checksum mismatch")
        extract(archive, directory)
        result = activate(config, directory)
        (directory / "activation.json").write_text(json.dumps(result, indent=2) + "\n")
        print(json.dumps(result))
        completed = True
    finally:
        # A failed/uncertain activation requires inspection, even when rollback ran.
        # Never automatically retry over an unresolved deployment.
        if completed:
            lock.unlink()


if __name__ == "__main__":
    if len(sys.argv) == 3 and sys.argv[1] == "--receive":
        receive(Path(sys.argv[2]))
    elif len(sys.argv) == 3 and sys.argv[1] == "--verify-public":
        metadata = json.loads(Path(sys.argv[2]).read_text())
        require(metadata["environment"] in HOSTS and metadata["hostname"] == HOSTS[metadata["environment"]],
                "Invalid public verification target")
        probe(metadata, "https://" + metadata["hostname"])
        print("Published site HTTPS identity and asset checks passed")
    else:
        raise SystemExit("Expected --receive CONFIG or --verify-public DEPLOYMENT")
