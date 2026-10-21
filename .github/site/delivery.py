"""Acquire published, verified site assets. DockPipe owns bundling and activation."""
import importlib.util
import json
import os
from pathlib import Path
import re
import subprocess
import sys
from urllib.parse import quote

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("release_api", ROOT / ".github/release/api.py")
api = importlib.util.module_from_spec(spec)
spec.loader.exec_module(api)
from policy import check_run, require


def download(release, name, directory):
    assets = [a for a in release["assets"] if a["name"] == name]
    require(len(assets) == 1, "Missing or duplicate published asset: " + name)
    asset = assets[0]
    require(asset.get("state") == "uploaded" and re.fullmatch(r"sha256:[a-f0-9]{64}", asset.get("digest", "")),
            "Published asset digest/state missing")
    output = directory / name
    with api.request("/releases/assets/" + str(int(asset["id"])), binary=True, asset=True) as incoming, output.open("xb") as stream:
        total = 0
        while block := incoming.read(1024 * 1024):
            total += len(block)
            require(total <= 1024 ** 3, "Published asset exceeds limit")
            stream.write(block)
    require(total == asset["size"] and api.digest(output) == asset["digest"][7:], "Published asset checksum mismatch")
    return output


def main():
    environment = os.environ["FREEFLIGHT_DEPLOY_ENVIRONMENT"]
    require(environment in ("staging", "production"), "Invalid environment")
    branch = "staging" if environment == "staging" else "master"
    event = "push" if environment == "staging" else "workflow_dispatch"
    require(os.environ.get("GITHUB_REPOSITORY") == api.REPO and
            os.environ.get("GITHUB_REF") == "refs/heads/" + branch and
            os.environ.get("GITHUB_EVENT_NAME") == event, "Invalid deployment event")
    tag = os.environ["FREEFLIGHT_DEPLOY_RELEASE_TAG"]
    require(re.fullmatch(r"v[0-9A-Za-z.-]+", tag), "Invalid release tag")
    release = api.request("/releases/tags/" + quote(tag, safe=""))
    require(release.get("draft") is False and release.get("prerelease") is (environment == "staging"),
            "Wrong publication channel")
    promoted = os.environ["GITHUB_SHA"]
    require(api.request("/git/ref/heads/" + branch)["object"]["sha"] == promoted, "Deployment branch moved")
    require(api.request("/commits/" + quote(tag, safe=""))["sha"] == promoted, "Release tag does not match promoted commit")
    directory = ROOT / "bin/.local/site-pipeline"
    directory.mkdir(parents=True, exist_ok=False)
    manifest = json.loads(download(release, "release-manifest.json", directory).read_text())
    require(manifest["tag"] == tag and manifest["channel"] == environment
            and manifest["promotedCommit"] == promoted, "Release manifest identity mismatch")
    if environment == "production":
        require(re.fullmatch(r"\d+\.\d+\.\d+", manifest["version"]) and tag == "v" + manifest["version"],
                "Production requires a published stable release")
    source = manifest["sourceCommit"]
    require(re.fullmatch("[a-f0-9]{40}", source), "Invalid source")
    check_run(api.request("/actions/runs/" + str(int(manifest["qualificationRun"]))), ".github/workflows/ci.yml", source)
    check_run(api.request("/actions/runs/" + str(int(manifest["codeqlRun"]))), ".github/workflows/codeql.yml", source)
    require(subprocess.run(["git", "merge-base", "--is-ancestor", source, promoted]).returncode == 0,
            "Qualified source ancestry mismatch")
    tree = subprocess.check_output(["git", "rev-parse", source + "^{tree}"], text=True).strip()
    require(subprocess.check_output(["git", "rev-parse", promoted + "^{tree}"], text=True).strip() == tree,
            "Qualified source tree mismatch")
    names = ["qt-wasm-site-" + environment, "qt-site-container-" + environment,
             "qt-site-audit-" + environment, "qt-corresponding-sources"]
    for name in names:
        path = download(release, name + ".zip", directory)
        expected = [a for a in manifest["additionalAssets"] if a["filename"] == path.name]
        require(len(expected) == 1 and api.digest(path) == expected[0]["sha256"], "Release manifest asset mismatch")
    manifest["releaseUrl"] = release["html_url"]
    (directory / "published.json").write_text(json.dumps(manifest, indent=2) + "\n")
    subprocess.run(["dockpipe", "--workflow", "site.deploy.bundle"], check=True)


if __name__ == "__main__":
    main()
