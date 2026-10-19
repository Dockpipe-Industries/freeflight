"""Audit the exact saved image, without Docker access or publishing anything."""
import hashlib
import json
import os
from pathlib import Path
import platform
import subprocess
import tarfile
import urllib.request

ROOT = Path(__file__).resolve().parents[3]
VERSION = "0.76.0"
PACKAGES = {
    ("Linux", "x86_64"): ("Linux-64bit", "e24b1c51293c1b15e4ba8d45bbc7891ba053f90278ec2698f3562c993e145fe7"),
    ("Darwin", "arm64"): ("macOS-ARM64", "e7ec0d21fe842553f59af99aba2efbcc822369fbaed27019c575408b6d135fce"),
}


def sha(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main():
    directory = ROOT / "bin/.local/site-audit"
    directory.mkdir(parents=True, exist_ok=True)
    receipt_path = directory / "verification.json"
    receipt_path.unlink(missing_ok=True)
    image = ROOT / "bin/.local/site-container/freeflight-site-image.tar.gz"
    receipt = json.loads((image.parent / "verification.json").read_text())
    image_hash = sha(image)
    if image.is_symlink() or receipt["artifacts"].get(image.name) != image_hash:
        raise RuntimeError("Container archive differs from the qualified image")
    package, expected = PACKAGES[(platform.system(), platform.machine())]
    archive = directory / f"trivy_{VERSION}_{package}.tar.gz"
    url = f"https://github.com/aquasecurity/trivy/releases/download/v{VERSION}/{archive.name}"
    if not archive.exists() or sha(archive) != expected:
        with urllib.request.urlopen(url, timeout=120) as response, archive.open("wb") as target:
            while block := response.read(1024 * 1024):
                target.write(block)
    if sha(archive) != expected:
        raise RuntimeError("Official Trivy archive checksum mismatch")
    binary = directory / "trivy"
    with tarfile.open(archive) as bundle:
        entry = bundle.getmember("trivy")
        if not entry.isfile():
            raise RuntimeError("Scanner archive executable is not a regular file")
        with bundle.extractfile(entry) as source, binary.open("wb") as target:
            target.write(source.read())
    binary.chmod(0o755)
    # No repository ignore file, config, environment override or VEX suppression.
    ignore = directory / "empty-ignore"
    ignore.write_text("")
    config = directory / "empty-config.yaml"
    config.write_text("{}\n")
    environment = {key: value for key, value in os.environ.items() if not key.startswith("TRIVY_")}
    report = directory / "vulnerabilities.json"
    command = [str(binary), "image", "--config", str(config), "--cache-dir", str(directory / "cache"),
               "--input", str(image), "--scanners", "vuln", "--severity", "HIGH,CRITICAL",
               "--ignorefile", str(ignore), "--ignore-unfixed=false", "--exit-code", "1",
               "--timeout", "15m", "--format", "json", "--output", str(report)]
    subprocess.run(command, env=environment, cwd=directory, check=True, timeout=960)
    receipt_path.write_text(json.dumps({"scanner": "Trivy", "version": VERSION,
        "scannerArchiveSha256": expected, "imageArchiveSha256": image_hash,
        "reportSha256": sha(report), "severity": ["HIGH", "CRITICAL"],
        "ignoreUnfixed": False, "status": "passed"}, indent=2) + "\n")


if __name__ == "__main__":
    main()
