# FreeFlight public site

The product renderer is an independently authored Qt Quick/QuickControls2 application
compiled to WebAssembly, following the inspected DockPipe site's production architecture.
No private Cloud source or branding is copied. The landing and installation views are structured QML; `index.html` retains an accessible
six-section overview. Languages, configuration and contribution navigation open the
source-backed semantic documentation reader. Maintained Markdown remains authoritative.

There are no accounts, authentication, telemetry, database, API, billing or external fonts.
Qt assets are delivered by one unprivileged static container. No server-side Qt process is
required. Hosting must reuse the existing VPC; these files do not activate infrastructure.

## Development

Run `dockpipe --workflow site.toolchain`, `site.sources`, `site.build`, `site.test`, then `site.container`.
The first explicitly provisions Qt6.12.0 and Emscripten5.0.5 beneath `bin/.local`.
The browser test provisions pinned Playwright and Chromium there, without system dependency
installation. Container checks require an already-running Docker daemon. Native CMake
remains usable with the same Qt host/WASM kit, SDK chainload and generated content file.

Output is `bin/.local/site`; browser screenshots and results are `bin/.local/site-test`.
`release.json` records asset hashes. The container copies only these named assets, uses
an immutable nginx-unprivileged base, and tests a disposable loopback instance before
removing it. Deployment is separate and has not occurred.

## Environments

`FREEFLIGHT_SITE_ENV` is `staging` by default or explicitly `production`.
`FREEFLIGHT_SITE_HOSTNAME` overrides the chosen defaults `freeflight-staging.dockpipe.com`
and `freeflight.dockpipe.com`. Environment/hostname conflicts fail the build.
Staging has robots Disallow:/, page noindex and the matching container X-Robots-Tag.
Production has crawlable robots, canonical URLs and an environment-specific sitemap.
Robots directives are not access controls. No authentication is provided.
The deployment manifest records selected hostnames; compose requires an explicit image
and unused loopback port. Existing ingress owns TLS/routing. Nested staging requires its
own applicable certificate; *.dockpipe.com does not cover it.

## Qt licensing and rebuilding

FreeFlight's original application is Apache-2.0. Qt Quick, Qt QuickControls2, Qt SVG and Qt base
retain their own LGPLv3/commercial licensing and third-party notices; the application
license does not relicense Qt. The linked Qt component inventory also includes bundled FreeType, HarfBuzz, JPEG, PNG, PCRE2 and zlib. Their original notices must accompany redistribution.
See https://doc.qt.io/qt-6.12/qtquick-index.html and
https://doc.qt.io/qt-6.12/qtquickcontrols-index.html for module licensing.
Qt6.12.0 corresponding source is available from https://download.qt.io/official_releases/qt/6.12/6.12.0/.
All application source, CMake, QML, content extraction and pinned provisioning instructions
are public and permit rebuilding/relinking with a modified compatible Qt. Before public
binary deployment, retain exact Qt component source archives, license texts and bundled
third-party notices alongside the release; `site.sources` retains these archives, original notices, and a relink-source tar under `bin/.local/site-sources`. Publish that source bundle alongside the binary site artifact; it has not been publicly deployed.

## Container provenance

The default nginxinc/nginx-unprivileged stable-alpine multi-platform index digest is
`sha256:f5116ed4606f3eb015dd4a8e28cb9b351476dc0ad4bc6e9f93b19cec130cdf03`, resolved
from Docker Registry's authenticated public manifest endpoint. Upstream source and license:
https://github.com/nginx/docker-nginx-unprivileged. `FREEFLIGHT_SITE_BASE_IMAGE` permits
another immutable digest from that repository. No credentials are embedded.

Verified Qt6.12.0 source archive filenames at the official archive index:
`submodules/qtbase-everywhere-src-6.12.0.tar.xz`,
`submodules/qtdeclarative-everywhere-src-6.12.0.tar.xz`, and
`submodules/qtsvg-everywhere-src-6.12.0.tar.xz`. These correspond to the Qt modules
seen in the actual WASM linker response file. Preserve their LICENSES and source
third-party notices; a pointer alone is not a substitute for completing the
redistribution bundle before public deployment.


## Rebuilding without DockPipe

From the relink-source archive's root, with Python3, Git, CMake3.25+, a C++23 host
compiler and standard build tools available, run the same underlying tools directly:

```sh
python3 workflows/site.toolchain/assets/provision.py
python3 workflows/site.sources/assets/sources.py
python3 workflows/site.build/assets/build.py
```

These helpers require Git provenance. For a standalone extracted relink archive,
initialize and commit that source locally with `git init`, `git add .` and
`git commit -m "Local FreeFlight relink source"` before invoking them. That local
commit identifies your rebuild, not an official FreeFlight release. Alternatively
use the published repository checkout at the receipt's sourceCommit.

To relink manually after content generation, set `QT_HOST_PATH`, `EMSDK`, `EM_CONFIG`
and `EM_CACHE` from `bin/.local/site-toolchain/toolchain.json`, then run:

```sh
"$FREEFLIGHT_QT_WASM_ROOT/bin/qt-cmake" -S site/qt -B bin/.local/relink \
  -DCMAKE_BUILD_TYPE=Release \
  -DFREEFLIGHT_SITE_CONTENT="$PWD/bin/.local/site-qt-build-6.12.0/content.json" \
  -DQT_CHAINLOAD_TOOLCHAIN_FILE="$EMSDK/upstream/emscripten/cmake/Modules/Platform/Emscripten.cmake"
cmake --build bin/.local/relink --parallel 2
```

`FREEFLIGHT_QT_WASM_ROOT` may point to your modified Qt6.12-compatible WASM kit;
its matching host tools must be in `QT_HOST_PATH`. Original Qt component archives
and notices are included alongside the application source. No DockPipe runtime is
required by the generated website or these underlying build commands.

Both website receipts record Git commit/tree, dirty status and a fingerprint of
all Git-visible source files. Qualification rejects source changes during the run
and rejects dirty checkouts in CI. Local dirty receipts are development evidence.


The qualified container is retained as `bin/.local/site-container/freeflight-site-image.tar.gz`
with SHA256SUMS and a provenance receipt including Docker image ID. Load this exact tested
image using `docker load --input freeflight-site-image.tar.gz`; deployment should not
rebuild from source or a mutable tag. The workflow saves only after the disposable
container's served bytes and indexing headers pass. Hosting activation remains separate.


### Emscripten runtime notices

The emitted JavaScript and WASM also contain Emscripten runtime and C/C++ support
code. `site.sources` validates and includes the pinned SDK LICENSE/AUTHORS, musl
COPYRIGHT, and original libc++, libc++abi, compiler-rt, libunwind, llvm-libc and
mimalloc license texts in both served NOTICES.txt and
`emscripten-runtime-notices.tar.gz`. The latter is a conservative SDK notice set;
it does not assert that every listed runtime component survives linking.
`runtime-notice-checksums.json` identifies the exact upstream Emscripten source
commit and per-file hashes, also pinned in `site/toolchain.json`. Installed texts
were compared byte-for-byte with the official5.0.5 source tag. Missing or altered
texts fail source qualification. This closes the identified runtime-notice gap,
not a blanket legal clearance for every dependency or future build configuration.
See https://emscripten.org/docs/introducing_emscripten/emscripten_license.html.

## Design and source-backed documentation review

The follow-up typography review inspected actual browser-rendered Nucleon and
DockPipe Cloud QML applications, built locally from Nucleon `654d66d4` and Cloud
`5ca7fbd2`. The comparison builds used the existing Qt 6.12 / Emscripten 5.0.5
Mac toolchain; they do not qualify those repositories' pinned Linux release kits.
FreeFlight now embeds the same unmodified Inter and DejaVu Sans Mono font assets,
retains their licenses in `NOTICES.txt`, and uses Qt Basic controls with consistent
46-pixel primary actions. Its light-blue and dark-blue palettes remain independent.

Credential-free loopback profiling did not reproduce a prolonged startup: the
initial three-site samples reached loader completion in 217–442 ms, with repeated
loads mostly 91–127 ms. These are local Chromium/software-rendering observations,
not production network, full-stack cold-start, or input-latency acceptance results.

Repeated browser captures exposed an intermittent blank workflow example while
the rest of the Qt page remained visible. Compositing that fixed-color panel as
one Qt layer retained its text in twelve repeated desktop/mobile light/dark loads.
The browser smoke check now verifies visible glyph pixels inside the panel in
both themes, in addition to saving screenshots. This is a repaint correction,
not evidence of a startup-speed improvement.

The local correction provides light-blue and dark-blue palettes with System/Light/Dark
selection, saved in browser local storage. The Qt landing page uses a bounded hero,
workflow panel and feature columns; small screens stack the content.

`workflows/site.build/assets/documents.py` imports only the seven public guides in
its explicit catalog. It records the exact checkout revision, per-file SHA-256,
and whether guide bytes differ from that revision. Agent guidance, private state
and arbitrary directories are excluded. The generated bundle is embedded in the
existing `loader.js`; the deployed reader cannot browse the repository filesystem.

The reader uses pinned Marked, DOMPurify and highlight.js packages, bundled locally
without a CDN. Raw HTML is escaped, output is sanitized and external Markdown
images are disabled. It supports title/body search, versioned source links,
allowlisted in-app document links, browser history, selectable code and Copy buttons.
Tables and code blocks scroll within their containers. Unsupported diagram fences
remain readable source; this does not claim Cloud's complete renderer feature set.
Library notices are appended to the served NOTICES.txt.

Company destinations are selected from `FREEFLIGHT_SITE_ENV` at build time:
`https://staging.dockpipe.com/#company` for staging and
`https://dockpipe.com/#company` for production. No hostname inference occurs in the browser.

After `dockpipe --workflow site.build`, `dockpipe --workflow site.preview` serves
`http://127.0.0.1:4174/` only on loopback. This workflow does not deploy, enable
delivery or modify infrastructure. `site.test` exercises both themes at desktop
and mobile sizes, persistence, docs search/history/copy, Company routing, source
integrity, contrast pairs, indexing and the accessible overview. Screenshots and
receipts remain under `bin/.local/site-test`. Full screen-reader acceptance of
Qt controls remains a separate limitation; the documentation body is semantic HTML.
