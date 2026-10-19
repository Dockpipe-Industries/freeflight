"""DockPipe-owned native bundle assembly; no downloads, promotion or publication."""
import hashlib
import json
import os
import pathlib
import platform
import queue
import shutil
import subprocess
import tarfile
import tempfile
import threading
import zipfile

REPO = pathlib.Path(__file__).resolve().parents[3]


def run(argv, **kwargs):
    return subprocess.run([str(arg) for arg in argv], check=True, timeout=600, **kwargs)


def required(name):
    value = os.environ.get(name)
    if not value:
        raise RuntimeError("Required explicit packaging input: " + name)
    return value


def digest(path):
    with path.open("rb") as source:
        return hashlib.file_digest(source, "sha256").hexdigest() if hasattr(hashlib, "file_digest") else hashlib.sha256(source.read()).hexdigest()


def copy_file(source, destination):
    if not source.is_file() or source.is_symlink():
        raise RuntimeError("Missing regular packaging input: " + str(source))
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)


def copy_tree(source, destination):
    if not source.is_dir() or any(p.is_symlink() for p in source.rglob("*")):
        raise RuntimeError("Package tree missing or contains unreviewed symlinks: " + str(source))
    shutil.copytree(source, destination)


def find_license(root, names):
    for name in names:
        candidate = root / name
        if candidate.is_file():
            return candidate
    raise RuntimeError("Required redistribution notice missing in " + str(root))


def verify_semantics(binary):
    """Exercise bundled runtime discovery with no external worker configuration."""
    with tempfile.TemporaryDirectory(prefix="freeflight-installed-test-") as directory:
        root = pathlib.Path(directory).resolve()
        (root / "tsconfig.json").write_text(json.dumps({"compilerOptions": {"strict": True, "allowJs": True, "checkJs": True}, "include": ["*.ts", "*.js"]}))
        (root / "sample.ts").write_text("export const typed: string = 42;\n")
        (root / "sample.js").write_text("export function increment(value) { return value + 1; }\n")
        (root / "Sample.cs").write_text("public class Widget { public int Count = \"wrong\"; }\n")
        requests = [{"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": "2025-11-25", "capabilities": {}, "clientInfo": {"name": "freeflight-package-check", "version": "1"}}}, {"jsonrpc": "2.0", "method": "notifications/initialized"}]
        for language, file, operation in [("typescript", "sample.ts", "diagnostics"), ("javascript", "sample.js", "symbols"), ("csharp", "Sample.cs", "diagnostics"), ("csharp", "Sample.cs", "symbols")]:
            requests.append({"jsonrpc": "2.0", "id": len(requests), "method": "tools/call", "params": {"name": "semantic.query", "arguments": {"root": str(root), "language": language, "operation": operation, "arguments": {"file": str(root / file)}}}})
        # EOF would cancel work in an asynchronous server: send one request at a time.
        process = subprocess.Popen([str(binary), "--workspace", str(root)], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        replies = queue.Queue()
        def read_replies():
            for line in process.stdout:
                replies.put(line)
        reader = threading.Thread(target=read_replies, daemon=True)
        reader.start()
        results = []
        try:
            for request in requests:
                process.stdin.write(json.dumps(request) + "\n")
                process.stdin.flush()
                if "id" not in request:
                    continue
                response = json.loads(replies.get(timeout=90))
                if response.get("id") != request["id"] or "error" in response:
                    raise RuntimeError("Installed MCP request failed: " + str(response))
                result = response["result"]
                if result.get("isError"):
                    raise RuntimeError("Installed semantic request failed: " + str(result))
                results.append(result)
            ts, js, cs, symbols = [r["structuredContent"]["items"] for r in results[1:]]
            if not any(str(d["code"]) == "2322" for d in ts):
                raise RuntimeError("TypeScript did not diagnose the known type mismatch")
            if not any(s["name"] == "increment" for s in js):
                raise RuntimeError("JavaScript did not resolve the known function")
            if not any(d["code"] == "CS0029" for d in cs):
                raise RuntimeError("Roslyn did not diagnose the known type mismatch")
            if not any(s["name"] == "Widget" for s in symbols):
                raise RuntimeError("Roslyn did not resolve the known class")
            process.stdin.close()
            process.wait(timeout=15)
            if process.returncode:
                raise RuntimeError("Installed server failed graceful shutdown")
        finally:
            if process.poll() is None:
                process.kill()
                process.wait(timeout=15)
            reader.join(timeout=5)
            process.stdout.close()
            process.stderr.close()
        return ["legacy MCP initialization", "TypeScript TS2322", "JavaScript increment symbol", "Roslyn CS0029", "Roslyn Widget symbol", "graceful shutdown"]


def pack_mcpb(bundle, node, node_root, system, rid, temporary):
    """Use the official pinned CLI; validate the exact extracted bundle before retaining it."""
    tooling = REPO / "bin/.local/mcpb-tools"
    tooling.mkdir(parents=True, exist_ok=True)
    for name in ("package.json", "package-lock.json"):
        copy_file(pathlib.Path(__file__).parent / "tooling" / name, tooling / name)
    npm = node_root / ("node_modules/npm/bin/npm-cli.js" if system == "win" else "lib/node_modules/npm/bin/npm-cli.js")
    run([node, npm, "ci", "--ignore-scripts", "--no-audit", "--prefix", tooling])
    cli = tooling / "node_modules/@anthropic-ai/mcpb/dist/cli/cli.js"
    suffix = ".exe" if system == "win" else ""
    entry = "bin/freeflight" + suffix
    manifest = {
        "manifest_version": "0.3", "name": "freeflight", "display_name": "FreeFlight",
        "version": (REPO / "VERSION").read_text().strip(),
        "description": "Local language intelligence for C#, TypeScript and JavaScript.",
        "long_description": "Development preview for " + rid + ". Includes native server and workers. Select the matching CPU architecture; no separate Node or .NET installation is required.",
        "author": {"name": "Dockpipe Industries Inc.", "url": "https://github.com/Dockpipe-Industries"},
        "repository": {"type": "git", "url": "https://github.com/Dockpipe-Industries/freeflight"},
        "license": "Apache-2.0",
        "server": {"type": "binary", "entry_point": entry,
            "mcp_config": {"command": "${__dirname}/" + entry, "args": ["--workspace", "${user_config.workspace}"]}},
        "compatibility": {"platforms": [{"osx": "darwin", "win": "win32", "linux": "linux"}[system]]},
        "user_config": {"workspace": {"type": "directory", "title": "Authorized workspace", "description": "Choose the local workspace FreeFlight may inspect.", "required": True}},
        "tools_generated": True
    }
    (bundle / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    # Type declarations are runtime input to the TypeScript language service.
    (bundle / ".mcpbignore").write_text("!lib/freeflight/typescript/**/*.d.ts\n!.mcpbignore\n")
    files = sorted(p for p in bundle.rglob("*") if p.is_file() and p.name != "SHA256SUMS")
    (bundle / "SHA256SUMS").write_text("".join(digest(p) + "  " + p.relative_to(bundle).as_posix() + "\n" for p in files))
    run([node, cli, "validate", bundle / "manifest.json"])
    archive = pathlib.Path(temporary) / (bundle.name + ".mcpb")
    run([node, cli, "pack", bundle, archive])
    extracted = pathlib.Path(temporary) / "mcpb-installed"
    extracted.mkdir()
    expected = {p.relative_to(bundle).as_posix(): p for p in bundle.rglob("*") if p.is_file()}
    with zipfile.ZipFile(archive) as source:
        members = {member.filename: member for member in source.infolist() if not member.is_dir()}
        if set(members) != set(expected):
            raise RuntimeError("MCPB packer omitted or added bundle files: " + str(set(members) ^ set(expected)))
        for name, member in members.items():
            destination = extracted / name
            if pathlib.PurePosixPath(name).is_absolute() or ".." in pathlib.PurePosixPath(name).parts:
                raise RuntimeError("Unsafe MCPB member")
            destination.parent.mkdir(parents=True, exist_ok=True)
            with source.open(member) as incoming, destination.open("wb") as outgoing:
                shutil.copyfileobj(incoming, outgoing)
            if digest(destination) != digest(expected[name]):
                raise RuntimeError("MCPB content mismatch: " + name)
            mode = (member.external_attr >> 16) & 0o777
            if system != "win":
                destination.chmod(mode)
        if system != "win" and not os.access(extracted / entry, os.X_OK):
            raise RuntimeError("MCPB did not retain executable permissions")
    verify_semantics(extracted / entry)
    return archive


def main():
    os.environ["DOTNET_CLI_TELEMETRY_OPTOUT"] = "1"
    os.environ["DOTNET_GENERATE_ASPNET_CERTIFICATE"] = "false"
    os.environ["DOTNET_SKIP_FIRST_TIME_EXPERIENCE"] = "1"
    rid = required("FREEFLIGHT_RID")
    system = {"Darwin": "osx", "Linux": "linux", "Windows": "win"}.get(platform.system())
    arch = {"arm64": "arm64", "aarch64": "arm64", "x86_64": "x64", "AMD64": "x64"}.get(platform.machine())
    if not system or not arch or rid != system + "-" + str(arch):
        raise RuntimeError("Native packaging requires a host matching FREEFLIGHT_RID; cross-built bundles cannot pass execution gates")
    suffix = ".exe" if system == "win" else ""
    node_root = pathlib.Path(required("NODE_DISTRIBUTION_ROOT")).resolve()
    node_version = required("FREEFLIGHT_NODE_VERSION")
    dotnet_licenses = pathlib.Path(required("DOTNET_LICENSE_ROOT")).resolve()
    nuget = pathlib.Path(required("NUGET_PACKAGES")).resolve()
    node = node_root / ("node.exe" if system == "win" else "bin/node")
    actual = run([node, "--version"], capture_output=True, text=True).stdout.strip()
    if actual != node_version:
        raise RuntimeError("Node version mismatch: " + actual)
    stage = REPO / "bin/.local/typescript"
    if json.loads((stage / "node_modules/typescript/package.json").read_text())["version"] != json.loads((REPO / "workers/typescript/package.json").read_text())["dependencies"]["typescript"]:
        raise RuntimeError("Staged TypeScript differs from the declared pinned dependency")
    output = REPO / "bin/.local/packages"
    output.mkdir(parents=True, exist_ok=True)
    # Only this invocation's temporary directory is cleaned; existing developer output is preserved.
    with tempfile.TemporaryDirectory(prefix="assemble-", dir=output) as temporary:
        bundle = pathlib.Path(temporary) / ("freeflight-" + rid)
        run(["cmake", "--install", REPO / "bin/.local/build", "--config", "Release", "--prefix", bundle])
        lib = bundle / "lib/freeflight"
        bundled_node = lib / "node" / ("node.exe" if system == "win" else "bin/node")
        copy_file(node, bundled_node)
        copy_tree(stage / "node_modules/typescript", lib / "typescript/node_modules/typescript")
        copy_file(stage / "worker.mjs", lib / "typescript/worker.mjs")
        run(["dotnet", "publish", REPO / "workers/roslyn/FreeFlight.Roslyn.csproj", "--configuration", "Release", "--runtime", rid, "--self-contained", "true", "-p:RestoreLockedMode=true", "--artifacts-path", REPO / "bin/.local/roslyn", "--output", lib / "roslyn", "-p:PublishSingleFile=false"])
        roslyn = lib / ("roslyn/FreeFlight.Roslyn" + suffix)
        for executable in (bundle / ("bin/freeflight" + suffix), bundled_node, roslyn):
            if not executable.is_file() or (system != "win" and not os.access(executable, os.X_OK)):
                raise RuntimeError("Expected executable missing: " + str(executable))
        notices = bundle / "share/freeflight/licenses"
        copy_file(find_license(node_root, ["LICENSE"]), notices / "node-LICENSE")
        copy_file(find_license(dotnet_licenses, ["LICENSE.txt", "LICENSE.TXT", "LICENSE"]), notices / "dotnet-LICENSE")
        copy_file(find_license(dotnet_licenses, ["ThirdPartyNotices.txt", "THIRD-PARTY-NOTICES.TXT", "THIRD-PARTY-NOTICES.txt"]), notices / "dotnet-THIRD-PARTY-NOTICES")
        copy_file(stage / "node_modules/typescript/LICENSE.txt", notices / "typescript-LICENSE")
        copy_file(REPO / "bin/.local/build/_deps/json-src/LICENSE.MIT", notices / "nlohmann-json-LICENSE")
        lock = json.loads((REPO / "workers/roslyn/packages.lock.json").read_text())
        for package, info in lock["dependencies"]["net10.0"].items():
            package_root = nuget / package.lower() / info["resolved"]
            metadata = package_root / (package.lower() + ".nuspec")
            copy_file(metadata, notices / "nuget" / package / metadata.name)
            for notice in package_root.iterdir():
                if notice.is_file() and ("license" in notice.name.lower() or "thirdpartynotices" in notice.name.lower()):
                    copy_file(notice, notices / "nuget" / package / notice.name)
        for name in ("roslyn-LICENSE", "humanizer-LICENSE", "SOURCES.md"):
            copy_file(pathlib.Path(__file__).parent / "licenses" / name, notices / name)
        binary = bundle / ("bin/freeflight" + suffix)
        run([os.environ.get("PYTHON", "python3"), REPO / "tests/protocol.py", binary])
        checks = verify_semantics(binary)
        run([os.environ.get("PYTHON", "python3"), "-B", REPO / "workers/roslyn/test_worker.py", "--native", roslyn])
        receipt = {"rid": rid, "nodeVersion": actual, "nodeExecutableSha256": digest(node), "checks": checks, "productionPublication": False}
        (bundle / "verification.json").write_text(json.dumps(receipt, indent=2) + "\n")
        mcpb = pack_mcpb(bundle, node, node_root, system, rid, temporary)
        # No archive is emitted until every verification gate succeeds. Unique output avoids overwriting artifacts.
        archive = output / (bundle.name + "-" + digest(bundle / "SHA256SUMS")[:16] + ".tar.gz")
        if archive.exists():
            raise RuntimeError("Verified archive already exists; refusing overwrite: " + str(archive))
        with tarfile.open(archive, "w:gz") as target:
            target.add(bundle, arcname=bundle.name)
        (archive.with_name(archive.name + ".sha256")).write_text(digest(archive) + "  " + archive.name + "\n")
        mcpb_output = output / (bundle.name + "-" + digest(mcpb)[:16] + ".mcpb")
        if mcpb_output.exists():
            raise RuntimeError("MCPB output already exists; refusing overwrite")
        shutil.move(mcpb, mcpb_output)
        mcpb_output.with_name(mcpb_output.name + ".sha256").write_text(digest(mcpb_output) + "  " + mcpb_output.name + "\n")
        print("Verified local package: " + str(archive))
        print("Verified local MCPB: " + str(mcpb_output))


if __name__ == "__main__":
    main()
