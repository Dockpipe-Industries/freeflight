# FreeFlight public site

This static, dependency-free entry point has six navigable sections: home,
installation, documentation, language support, MCP configuration and contributing.
It requires no JavaScript, external fonts, telemetry, npm scripts or runtime
framework. Repository documentation remains authoritative; the page links to it
rather than maintaining a second copy of detailed instructions.

The DockPipe Cloud public-site conventions informed source-authoritative docs,
explicit release state and production/staging separation. Existing Nucleon authoring
guidance informed honest capability labeling. No private source, assets or product
implementation was copied.

## Building and hosting

The parent CMake/DockPipe workflow can stage `index.html` and `styles.css` unchanged.
Serve that directory with any static host. All site asset and navigation URLs are
relative, so deployment works at a configurable hostname and subpath. No production
hostname, canonical URL, deployment service or credentials have been invented.

The preview is deliberately `noindex, nofollow`. Before a verified production
release, update tested capabilities and exact installation/configuration links from
repository docs, remove that preview robots directive, and configure canonical URL
and sitemap against the chosen production hostname in the deployment workflow.
Do not advertise a download until its release artifacts have been verified.

Publication, domain selection, TLS, hosting and live browser acceptance remain
separate release gates. Use DockPipe as the development-facing staging and validation
entry point; do not add a competing site task runner.
