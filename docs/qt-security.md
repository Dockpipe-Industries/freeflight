# Qt website dependency review

Review date: 2026-10-19. Scope: the website's statically linked Qt/WASM runtime,
not the standalone FreeFlight language server. Authoritative selected versions and
source hashes are in `site/toolchain.json`.

The initial Qt6.8.3 pin matched the inspected DockPipe Cloud build. It is not a
security-cleared production dependency. Official advisories published since that
release cover modules present in the actual FreeFlight linker inventory: Qt Core,
Network, Quick/QML and SVG. Successful rendering and npm/NuGet audits do not audit
these native libraries.

| Official advisory | Old pin affected | Fixed public line relevant to upgrade |
| --- | --- | --- |
| [CVE-2025-10728 / CVE-2025-10729](https://www.qt.io/blog/security-advisory-uncontrolled-recursion-and-use-after-free-vulnerabilities-in-qt-svg-module-impact-qt), SVG recursion/use-after-free, CVSS9.4 |6.8.3 within6.7.0–6.8.4|6.9.3+|
| [CVE-2025-12385](https://www.qt.io/blog/security-advisory-improper-validation-of-img-tag-size-in-text-component-parser), Quick Text image-size allocation, CVSS8.7 |6.8.3 within6.6.0–6.8.5|6.10.1+|
| [CVE-2025-14576](https://www.qt.io/blog/security-advisory-qml-code-injection-in-vectorimage), VectorImage QML injection, CVSS7.4 |6.8.0–6.8.6|6.10.2+|
| [CVE-2026-6210](https://www.qt.io/blog/security-advisory-type-confusion-and-heap-buffer-overflow-vulnerability-in-qt-svg-marker-handling), SVG marker/mask type confusion, CVSS8.7 |6.7.0 before6.8.8|6.11.1+|
| [CVE-2026-8168](https://www.qt.io/blog/security-advisory-cve-2026-8168), SVG deep-recursion denial of service, CVSS7.1 |through6.8.8|6.11.2 or6.12.0+|
| [CVE-2026-78253](https://www.qt.io/blog/security-advisory-cve-2026-78253), Qt Core XML readElementText stack exhaustion |through6.8.8|6.11.2+|
| [CVE-2026-79616](https://www.qt.io/blog/security-advisory-cve-2026-79616), Quick path parser out-of-bounds read |through6.8.8|6.11.2+|
| [CVE-2026-76151](https://www.qt.io/blog/security-advisory-cve-2026-76151), Network cache-header over-read |version range includes6.8.3; advisory explicitly excludes32-bit builds|6.11.2+|

The site currently reads only embedded authored content. Its conversion whitelist
excludes image elements; it exposes no upload, XML input, external QML, VectorImage,
or remote data-loading feature. These constraints limit demonstrated reachability;
they are not a reason to retain vulnerable dependencies or assert that dead-code
elimination removed every affected function. Qt XML/QDom, NFC, Multimedia and
Core5Compat are not in the observed linker inventory; their advisories must be
reassessed if those modules are introduced. The runtime is wasm32; the Network
advisory's32-bit exclusion is distinct from general module-version exposure.

## Selected remediation

[Qt6.12.0 was released2026-09-30](https://www.qt.io/blog/qt-6.12-released).
The official [WASM documentation](https://doc.qt.io/qt-6.12/wasm.html) specifies
Emscripten5.0.5 for its prebuilt ABI. Both public macOS/Linux host kits and the
single-thread WASM kit were verified in Qt's public package repository metadata.
The existing pinned aqt3.3.0 installer recognizes that repository layout.

The upgrade retains the same Qt Quick/QuickControls2, QML, CMake, single-thread
WebAssembly and static-container architecture. It does not replace the renderer.
All three corresponding-source hashes come from official Qt6.12.0 `.sha256`
files; notices and source/relink artifacts must be regenerated. Old6.8.3 artifacts
remain historical development evidence and must not be published as the final
qualified website. Fresh build, responsive browser and container evidence are
required for the changed runtime.

This is an advisory review, not an exhaustive vulnerability scan of every bundled
third-party component. Qt's bundled FreeType, HarfBuzz, JPEG, PNG, PCRE2 and zlib
retain their licenses and should be included in release SBOM/advisory monitoring.
Recheck the official Qt security feed before production publication and after
any pin change. Never interpret a successful npm audit as Qt runtime clearance.
