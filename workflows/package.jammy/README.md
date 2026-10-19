# Ubuntu 22.04 preview qualification

The existing CI qualification matrix additionally runs Ubuntu 22.04 with the
preinstalled GCC 12.3.0 compiler selected by `dockpipe --workflow core.jammy`.
GitHub's [runner manifest](https://github.com/actions/runner-images/blob/main/images/ubuntu/Ubuntu2204-Readme.md)
records this compiler. The C++23 requirement and all existing native tests remain.

After `package.native`, run `dockpipe --workflow package.jammy` on Ubuntu 22.04 x64.
The workflow-local Python helper reuses release archive/checksum validation,
inspects consumer ELF symbol versions, then tests the extracted tar in a clean
runtime image. Python is necessary for bounded archive inspection and disposable
container orchestration; it is not a second developer task runner.

The official Ubuntu 22.04 amd64 manifest digest was resolved from Docker Hub's
`library/ubuntu:22.04` on 2026-10-19 and is pinned in `assets/check.py`.
Image construction installs only the documented Ubuntu runtime packages from the
distribution repositories. Package versions are recorded in the result; this is
not a claim of reproducible apt resolution. The runtime test uses only bundled
Node/.NET, the pinned official MCP SDK fixture, an unprivileged user, a read-only
root filesystem, a writable temporary directory and no network or host mounts.
It verifies TypeScript definition/references/diagnostics, JavaScript symbols,
C# diagnostics/symbols and actual engine capabilities. No external SDK is supplied,
so this clean-container check covers default safe-source operation only.

The ABI ceilings are GLIBC 2.35, GLIBCXX 3.4.30 and CXXABI 1.3.13. The additional
container test detects libraries missing from a normal updated Ubuntu installation
that may be present on a hosted development runner. This is not a Pop!_OS execution
test, nor a claim that an unupdated installation has every required dependency.

Only success emits `bin/.local/jammy-compatibility.json`; CI retains it beside the
archives in `preview-ubuntu-22.04-linux-x64`. Existing `native-ubuntu-24.04` output
and production release requirements are unchanged. No package is published by
this workflow. Its offline policy tests also run through `release.policy`.

## Fedora runtime compatibility

The same archive is also tested with the same isolated SDK invocation in Fedora 44.
The [official release metadata](https://fedoraproject.org/releases.json) listed 44
as the newest non-beta release on 2026-10-19 (45 was beta). The image digest is the
linux/amd64 manifest from the official
[registry](https://registry.fedoraproject.org/v2/fedora/manifests/44), pinned in the
helper. Fedora's runtime packages are `ca-certificates`, `glibc`, `libgcc`,
`krb5-libs`, `libicu`, `openssl-libs`, `libstdc++`, `tzdata` and `zlib-ng-compat`.
They follow [Microsoft's Fedora dependencies](https://learn.microsoft.com/en-us/dotnet/core/install/linux-fedora#dependencies),
with Fedora's [binary-compatible zlib provider](https://packages.fedoraproject.org/pkgs/zlib-ng/zlib-ng-compat/).
DNF installs no SDK/Node and disables weak dependencies. Exact RPM versions are
recorded separately; repository package resolution is not claimed reproducible.

`fedoraRuntime` in the existing compatibility receipt identifies its pinned image,
exact tar hash/source, semantic test result and package inventory. The original
Ubuntu receipt fields remain unchanged. Both runtime tests must pass before the
workflow emits a receipt. This does not qualify previously published bytes,
Bazzite's immutable host, its sandbox integration, or any particular MCP desktop
client. Bazzite execution remains explicitly untested.
