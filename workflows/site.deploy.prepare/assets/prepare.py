"""Offline delivery preparation. Input receipts never authorize remote activation."""
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[3]
HOSTS = {"staging": "freeflight-staging.dockpipe.com", "production": "freeflight.dockpipe.com"}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def digest(path):
    require(path.is_file() and not path.is_symlink(), "Expected a regular artifact file")
    value = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def git(*args):
    return subprocess.check_output(["git", "-C", str(ROOT), *args], text=True).strip()


def validate(plan):
    environment = plan["environment"]
    require(environment in HOSTS, "Unsupported environment")
    source = plan["sourceCommit"]
    require(re.fullmatch(r"[0-9a-f]{40}", source), "Invalid source identity")
    source_tree = git("rev-parse", source + "^{tree}")
    branch = "master" if environment == "production" else "staging"
    promoted = git("rev-parse", "refs/remotes/origin/" + branch)
    require(git("merge-base", source, promoted) == source, "Source is not promoted")
    require(git("rev-parse", promoted + "^{tree}") == source_tree, "Promoted tree differs")
    if environment == "production":
        version = git("show", source + ":VERSION")
        require(re.fullmatch(r"\d+\.\d+\.\d+", version), "Production requires a stable VERSION")
        tag = git("rev-parse", "refs/tags/v" + version + "^{commit}")
        require(git("merge-base", source, tag) == source, "Release tag lacks qualified source")
        require(git("rev-parse", tag + "^{tree}") == source_tree, "Release tag tree differs")
    port = plan["loopbackPort"]
    require(type(port) is int and 1024 <= port <= 65535, "Invalid loopback port")
    receipt = json.loads(Path(plan["containerReceipt"]).read_text())
    require(receipt["sourceCommit"] == source and receipt["sourceTree"] == source_tree
            and receipt["sourceDirty"] is False, "Container source mismatch")
    require(receipt["environment"] == environment and receipt["hostname"] == HOSTS[environment],
            "Container environment/hostname mismatch")
    image_id = receipt["imageId"]
    require(re.fullmatch(r"sha256:[0-9a-f]{64}", image_id), "Invalid image identity")
    archive = Path(plan["containerArchive"])
    archive_hash = digest(archive)
    require(archive_hash == plan["containerArchiveSha256"]
            == receipt["artifacts"].get(archive.name), "Container archive mismatch")
    audit = json.loads(Path(plan["auditReceipt"]).read_text())
    require(audit["status"] == "passed" and audit["imageArchiveSha256"] == archive_hash
            and set(audit["severity"]) == {"HIGH", "CRITICAL"} and audit["ignoreUnfixed"] is False,
            "Audit is not bound to this image or did not pass")
    require(digest(Path(plan["auditReport"])) == audit["reportSha256"], "Audit report mismatch")
    report = json.loads(Path(plan["auditReport"]).read_text())
    require(not any(v.get("Severity") in {"HIGH", "CRITICAL"}
                    for result in report.get("Results", [])
                    for v in result.get("Vulnerabilities", [])), "Audit contains blocking vulnerabilities")
    sources_hash = digest(Path(plan["correspondingSources"]))
    require(sources_hash == plan["correspondingSourcesSha256"], "Corresponding sources mismatch")
    return {
        "environment": environment, "hostname": HOSTS[environment],
        "sourceCommit": source, "sourceTree": source_tree, "promotedCommit": promoted,
        "imageId": image_id, "containerArchiveSha256": archive_hash,
        "correspondingSourcesSha256": sources_hash, "loopbackPort": port,
        "activated": False, "remotePreflightPassed": False, "deploymentAuthorized": False,
        "remainingGates": ["fresh hosted qualification and release evidence",
                           "verified host identity, capacity, runtime and free port",
                           "authorized artifact transfer and independent remote hashes",
                           "environment-specific ingress/DNS/TLS authorization",
                           "public corresponding sources and licenses",
                           "live HTTPS identity, asset and browser verification"],
    }


def main():
    plan = json.loads(Path(os.environ["FREEFLIGHT_DEPLOY_INPUT"]).read_text())
    result = validate(plan)
    base = ROOT / "bin/.local/site-delivery"
    base.mkdir(parents=True, exist_ok=True)
    output = Path(tempfile.mkdtemp(prefix=result["environment"] + "-", dir=base))
    compose = (ROOT / "site/container/compose.yaml").read_text()
    compose = compose.replace("name: freeflight-site", "name: freeflight-" + result["environment"])
    compose = compose.replace("${FREEFLIGHT_SITE_IMAGE:?Select the qualified immutable FreeFlight site image}",
                              result["imageId"])
    compose = compose.replace("${FREEFLIGHT_SITE_PORT:?Select a verified unused loopback port}",
                              str(result["loopbackPort"]))
    (output / "compose.yaml").write_text(compose)
    (output / "preparation.json").write_text(json.dumps(result, indent=2) + "\n")
    print("Prepared delivery inputs; no remote checks or deployment performed: " + str(output))


if __name__ == "__main__":
    main()
