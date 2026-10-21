"""Package only verified published site bytes for the FreeFlight-specific receiver."""
import hashlib
import base64
import gzip
import json
import os
from pathlib import Path
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "workflows/release.verify/assets"))
from policy import require, verify_extra


def main():
    directory = ROOT / "bin/.local/site-pipeline"
    published = json.loads((directory / "published.json").read_text())
    environment = os.environ["FREEFLIGHT_DEPLOY_ENVIRONMENT"]
    require(environment in ("staging", "production") and published["channel"] == environment, "Wrong delivery channel")
    source = published["sourceCommit"]
    # The API adapter checked remote qualification; repeat archive and receipt validation.
    import subprocess
    tree = subprocess.check_output(["git", "rev-parse", source + "^{tree}"], text=True).strip()
    receipts = {}
    for name in ("qt-wasm-site-" + environment, "qt-site-container-" + environment,
                 "qt-site-audit-" + environment, "qt-corresponding-sources"):
        receipts[name] = verify_extra(directory / (name + ".zip"), name, source, tree)
    image = receipts["qt-site-container-" + environment]
    audit = receipts["qt-site-audit-" + environment]
    site = receipts["qt-wasm-site-" + environment]
    require(audit["imageArchiveSha256"] == image["artifacts"]["freeflight-site-image.tar.gz"],
            "Scan does not qualify image bytes")
    with zipfile.ZipFile(directory / ("qt-wasm-site-" + environment + ".zip")) as archive:
        site_hash = hashlib.sha256(archive.read("release.json")).hexdigest()
    require(site_hash == image["siteReleaseSha256"], "Container/site mismatch")
    hostname = "freeflight-staging.dockpipe.com" if environment == "staging" else "freeflight.dockpipe.com"
    require(site["hostname"] == image["hostname"] == hostname, "Unexpected published hostname")
    deployment = {
        "schema": 2, "environment": environment, "hostname": hostname,
        "sourceCommit": source, "sourceTree": tree, "promotedCommit": published["promotedCommit"],
        "version": published["version"], "releaseTag": published["tag"],
        "prerelease": environment == "staging", "releaseUrl": published["releaseUrl"],
        "siteReleaseSha256": site_hash, "assets": site["assets"],
    }
    (directory / "deployment.json").write_text(json.dumps(deployment, indent=2) + "\n")
    files = {}
    with zipfile.ZipFile(directory / ("qt-wasm-site-" + environment + ".zip")) as archive:
        for name in archive.namelist():
            data = archive.read(name)
            files[name] = {"sha256": hashlib.sha256(data).hexdigest(),
                           "content": base64.b64encode(data).decode()}
    document = {"format": 2, "product": "freeflight", "mode": "site",
                "deployment": deployment, "files": files}
    encoded = gzip.compress(json.dumps(document).encode(), mtime=0)
    sys.path.insert(0, str(ROOT / "workflows/site.deploy.receive/assets"))
    from receive import decode
    digest = hashlib.sha256(encoded).hexdigest()
    decode(encoded, digest, environment)
    destination = directory / "site.bundle.gz"
    with destination.open("xb") as output:
        output.write(encoded)
    (directory / "site.bundle.gz.sha256").write_text(digest + "  site.bundle.gz\n")
    print("Verified delivery bundle prepared; no host contacted")


if __name__ == "__main__":
    main()
