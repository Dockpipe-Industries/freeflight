"""Generate the Qt product view from authored HTML, build WASM and stage public files."""
import hashlib
import html
from html.parser import HTMLParser
import json
import os
import pathlib
import re
import shutil
import subprocess
import sys
from provenance import capture, finish

REPO = pathlib.Path(__file__).resolve().parents[3]
TITLES = {"home": "Home", "installation": "Installation", "documentation": "Documentation", "languages": "Languages", "configuration": "MCP setup", "contributing": "Contributing"}


class Sections(HTMLParser):
    def __init__(self):
        super().__init__()
        self.pages = []
        self.current = None
        self.allowed = {"h1", "h2", "h3", "h4", "p", "b", "strong", "i", "em", "ul", "ol", "li", "pre", "code", "br"}

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "section":
            key = attrs.get("id")
            if key not in TITLES or self.current is not None:
                raise RuntimeError("Unexpected site section")
            self.current = {"id": key, "title": TITLES[key], "html": ""}
        elif self.current is not None:
            if tag in self.allowed:
                self.current["html"] += "<" + tag + ">"
            elif tag == "a":
                url = attrs.get("href", "")
                if not (url.startswith("https://github.com/") or url.startswith("#")):
                    raise RuntimeError("Unexpected product link")
                self.current["html"] += '<a style="color:#c3ef88" href="' + html.escape(url, quote=True) + '">'
            elif tag == "div":
                self.current["html"] += "<br>"
            elif tag == "tr":
                self.current["html"] += "<p>"
            elif tag == "th":
                self.current["html"] += "<b>"

    def handle_endtag(self, tag):
        if self.current is None:
            return
        if tag == "section":
            self.pages.append(self.current)
            self.current = None
        elif tag in self.allowed and tag != "br":
            self.current["html"] += "</" + tag + "> "
        elif tag == "a":
            self.current["html"] += "</a> "
        elif tag == "th":
            self.current["html"] += "</b> · "
        elif tag == "td":
            self.current["html"] += " · "
        elif tag in ("div", "span"):
            self.current["html"] += " "
        elif tag == "tr":
            self.current["html"] += "</p>"

    def handle_data(self, data):
        if self.current is not None:
            self.current["html"] += html.escape(data)


def run(args, **kwargs):
    subprocess.run([str(arg) for arg in args], check=True, timeout=1800, **kwargs)


def main():
    provenance = capture(REPO)
    source = REPO / "site"
    pins = json.loads((source / "toolchain.json").read_text())
    build = REPO / ("bin/.local/site-qt-build-" + pins["qt"])
    stage = REPO / "bin/.local/site"
    for output in (build, stage):
        if output.is_symlink():
            raise RuntimeError("Generated site directory cannot be a symlink")
        output.mkdir(parents=True, exist_ok=True)
    parser = Sections()
    parser.feed((source / "index.html").read_text())
    if {page["id"] for page in parser.pages} != set(TITLES) or len(parser.pages) != 6:
        raise RuntimeError("Expected exactly six source sections")
    content = build / "content.json"
    serialized = json.dumps(parser.pages, ensure_ascii=False, indent=2) + "\n"
    if not content.exists() or content.read_text() != serialized:
        content.write_text(serialized)
    receipt = REPO / "bin/.local/site-toolchain/toolchain.json"
    if all(os.environ.get(key) for key in ("FREEFLIGHT_QT_WASM_ROOT", "QT_HOST_PATH", "FREEFLIGHT_EMSDK_ROOT")):
        sdk_root = pathlib.Path(os.environ["FREEFLIGHT_EMSDK_ROOT"]).resolve()
        toolchain = {"qt": pins["qt"], "emsdk": pins["emsdk"], "hostRoot": os.environ["QT_HOST_PATH"], "wasmRoot": os.environ["FREEFLIGHT_QT_WASM_ROOT"], "emsdkRoot": str(sdk_root), "emConfig": os.environ.get("EM_CONFIG", str(sdk_root / ".emscripten")), "emCache": os.environ.get("EM_CACHE", str(REPO / "bin/.local/site-qt-cache"))}
    elif receipt.is_file():
        toolchain = json.loads(receipt.read_text())
    else:
        raise RuntimeError("Run dockpipe --workflow site.toolchain or supply an explicit Qt host/WASM and Emscripten kit")
    if toolchain["qt"] != pins["qt"] or toolchain["emsdk"] != pins["emsdk"]:
        raise RuntimeError("Provisioned site toolchain does not match authoritative site/toolchain.json")
    env = dict(os.environ, QT_HOST_PATH=toolchain["hostRoot"], EM_CONFIG=toolchain["emConfig"], EM_CACHE=toolchain["emCache"])
    sdk = pathlib.Path(toolchain["emsdkRoot"])
    env["EMSDK"] = str(sdk)
    env["EMSDK_PYTHON"] = toolchain.get("python", os.environ.get("EMSDK_PYTHON", sys.executable))
    env["PATH"] = str(sdk) + os.pathsep + str(sdk / "upstream/emscripten") + os.pathsep + env.get("PATH", "")
    run([pathlib.Path(toolchain["wasmRoot"]) / "bin/qt-cmake", "-S", source / "qt", "-B", build, "-DCMAKE_BUILD_TYPE=Release", "-DFREEFLIGHT_SITE_CONTENT=" + str(content), "-DQT_CHAINLOAD_TOOLCHAIN_FILE=" + str(sdk / "upstream/emscripten/cmake/Modules/Platform/Emscripten.cmake")], env=env)
    run(["cmake", "--build", build, "--parallel", "2"], env=env)
    notices = REPO / "bin/.local/site-sources/NOTICES.txt"
    if not notices.is_file():
        raise RuntimeError("Run dockpipe --workflow site.sources to preserve Qt license notices")
    shutil.copy2(notices, stage / "NOTICES.txt")
    files = ("index.html", "loader.js", "freeflight-site.js", "freeflight-site.wasm", "qtloader.js")
    for name in files:
        if not (build / name).is_file():
            raise RuntimeError("Expected Qt build output missing: " + name)
        shutil.copy2(build / name, stage / name)
    shutil.copy2(source / "index.html", stage / "review.html")
    shutil.copy2(source / "styles.css", stage / "styles.css")
    environment = os.environ.get("FREEFLIGHT_SITE_ENV", "staging")
    if environment not in ("staging", "production"):
        raise RuntimeError("FREEFLIGHT_SITE_ENV must be staging or production")
    default_host = "freeflight.dockpipe.com" if environment == "production" else "freeflight.staging.dockpipe.com"
    hostname = os.environ.get("FREEFLIGHT_SITE_HOSTNAME", default_host)
    if not re.fullmatch(r"[a-z0-9]+(?:[.-][a-z0-9]+)+", hostname):
        raise RuntimeError("Invalid site hostname")
    if (environment == "production" and ("staging" in hostname or "localhost" in hostname)) or (environment == "staging" and hostname == "freeflight.dockpipe.com"):
        raise RuntimeError("Site environment and hostname conflict")
    robots = "index, follow" if environment == "production" else "noindex, nofollow"
    for name in ("index.html", "review.html"):
        page = (stage / name).read_text()
        page = re.sub(r'<meta name="robots"[^>]*>', '', page)
        page = page.replace("</head>", '<meta name="robots" content="' + robots + '"><link rel="canonical" href="https://' + hostname + '/' + ("" if name == "index.html" else name) + '"></head>')
        (stage / name).write_text(page)
    (stage / "robots.txt").write_text("User-agent: *\n" + ("Allow: /\nSitemap: https://" + hostname + "/sitemap.xml\n" if environment == "production" else "Disallow: /\n"))
    sitemap = stage / "sitemap.xml"
    if environment == "production":
        sitemap.write_text('<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"><url><loc>https://' + hostname + '/</loc></url><url><loc>https://' + hostname + '/review.html</loc></url></urlset>\n')
    elif sitemap.exists():
        sitemap.unlink()  # Owned generated sitemap only; never retained in staging.
    assets = files + ("review.html", "styles.css", "robots.txt", "NOTICES.txt") + (("sitemap.xml",) if environment == "production" else ())
    hashes = {name: hashlib.sha256((stage / name).read_bytes()).hexdigest() for name in assets}
    (stage / "release.json").write_text(json.dumps({**finish(REPO, provenance), "renderer": "qt-quick-wasm", "qt": toolchain["qt"], "emsdk": toolchain["emsdk"], "preview": True, "environment": environment, "hostname": hostname, "robots": robots, "assets": hashes}, indent=2) + "\n")
    print("Qt WebAssembly site staged with asset hashes: " + str(stage))


if __name__ == "__main__":
    main()
