"""Package only qualified Qt/Wasm assets; no host activation or ingress changes."""
import hashlib
import gzip
import json
import os
import pathlib
import re
import subprocess
import shutil
import tempfile
import time
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parents[3]
base = os.environ.get("FREEFLIGHT_SITE_BASE_IMAGE", "nginxinc/nginx-unprivileged:stable-alpine@sha256:f5116ed4606f3eb015dd4a8e28cb9b351476dc0ad4bc6e9f93b19cec130cdf03")
if not re.fullmatch(r"(?:docker.io/)?nginxinc/nginx-unprivileged[^@ ]*@sha256:[0-9a-f]{64}", base):
    raise RuntimeError("Set FREEFLIGHT_SITE_BASE_IMAGE to an immutable nginxinc/nginx-unprivileged Alpine digest")
site = ROOT / "bin/.local/site"
release = json.loads((site / "release.json").read_text())
if release.get("renderer") != "qt-quick-wasm":
    raise RuntimeError("Container requires compiled Qt/Wasm output, not the HTML preview alone")
for name, expected in release["assets"].items():
    path = site / name
    if path.parent != site or path.is_symlink() or hashlib.sha256(path.read_bytes()).hexdigest() != expected:
        raise RuntimeError("Unqualified or changed site asset: " + name)
tag = "freeflight-site:" + hashlib.sha256((site / "release.json").read_bytes()).hexdigest()[:16]
with tempfile.TemporaryDirectory(prefix="site-container-", dir=ROOT / "bin/.local") as temporary:
    context = pathlib.Path(temporary)
    staged = context / "bin/.local/site"
    staged.mkdir(parents=True)
    for name in (*release["assets"], "release.json"):
        shutil.copy2(site / name, staged / name)
    config = context / "site/container"
    config.mkdir(parents=True)
    for name in ("Dockerfile", "nginx.conf"):
        shutil.copy2(ROOT / "site/container" / name, config / name)
    nginx = config / "nginx.conf"
    nginx.write_text(nginx.read_text().replace("FREEFLIGHT_ROBOTS", release["robots"]))
    subprocess.run(["docker", "build", "--build-arg", "FREEFLIGHT_SITE_BASE_IMAGE=" + base, "--file", str(config / "Dockerfile"), "--tag", tag, str(context)], check=True, timeout=600)
container = subprocess.run(["docker", "run", "--detach", "--read-only", "--tmpfs", "/tmp:rw,noexec,nosuid,size=16m", "--cap-drop", "ALL", "--security-opt", "no-new-privileges", "--memory", "64m", "--pids-limit", "32", "-p", "127.0.0.1::8080", tag], check=True, capture_output=True, text=True).stdout.strip()
try:
    port = subprocess.run(["docker", "port", container, "8080"], check=True, capture_output=True, text=True).stdout.strip().split(":")[-1]
    base_url = "http://127.0.0.1:" + port
    for attempt in range(30):
        try:
            with urllib.request.urlopen(base_url + "/healthz", timeout=2) as response:
                if response.status == 200:
                    break
        except OSError:
            time.sleep(0.2)
    else:
        raise RuntimeError("Container did not become healthy")
    for name, expected in release["assets"].items():
        with urllib.request.urlopen(base_url + "/" + name, timeout=30) as response:
            if response.headers.get("X-Robots-Tag") != release["robots"]:
                raise RuntimeError("Container indexing header differs from build contract")
            if hashlib.sha256(response.read()).hexdigest() != expected:
                raise RuntimeError("Served asset differs: " + name)
    (ROOT / "bin/.local/site-container-verification.json").write_text(json.dumps({"image": tag, "base": base, "servedAssets": len(release["assets"]), "deployed": False}, indent=2) + "\n")
finally:
    subprocess.run(["docker", "rm", "--force", container], check=True)
output = ROOT / "bin/.local/site-container"
output.mkdir(parents=True, exist_ok=True)
image_id = subprocess.run(["docker", "image", "inspect", "--format", "{{.Id}}", tag], check=True, capture_output=True, text=True).stdout.strip()
with tempfile.TemporaryDirectory(prefix="image-save-", dir=output) as temporary:
    tar = pathlib.Path(temporary) / "image.tar"
    subprocess.run(["docker", "save", "--output", str(tar), tag], check=True, timeout=600)
    compressed = pathlib.Path(temporary) / "image.tar.gz"
    with tar.open("rb") as source, compressed.open("wb") as target:
        with gzip.GzipFile(filename="", mode="wb", fileobj=target, mtime=0) as archive:
            shutil.copyfileobj(source, archive)
    target = output / "freeflight-site-image.tar.gz"
    compressed.replace(target)
digest = hashlib.sha256()
with target.open("rb") as stream:
    for block in iter(lambda: stream.read(1024 * 1024), b""):
        digest.update(block)
sha256 = digest.hexdigest()
receipt = {key: release[key] for key in ("sourceCommit", "sourceTree", "sourceDirty", "workingSourceSha256", "environment", "hostname")}
receipt.update({"image": tag, "imageId": image_id, "base": base, "servedAssets": len(release["assets"]), "siteReleaseSha256": hashlib.sha256((site / "release.json").read_bytes()).hexdigest(), "deployed": False, "artifacts": {target.name: sha256}})
(output / "verification.json").write_text(json.dumps(receipt, indent=2) + "\n")
(output / "SHA256SUMS").write_text(sha256 + "  " + target.name + "\n")
print("Qualified image saved for docker load: " + str(target))
print("Local site image built and served assets verified; not deployed: " + tag)
