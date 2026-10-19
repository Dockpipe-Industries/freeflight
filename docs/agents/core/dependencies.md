# Dependencies and generated state

Use maintained permissively licensed libraries and official language SDKs. Pin
versions and immutable download hashes, retain third-party notices, use npm lock
and NuGet locked restore. No install hooks from untrusted repository packages.
Runtime provisioning belongs to the complete standalone distribution, not manual
worker installation for end users. Package-manager/SDK manifests remain native.

Place generated builds, dependency installs, test receipts and packages under
bin/.local; DockPipe owns bin/.dockpipe. Do not commit binaries, caches, secrets,
private configuration or stale generated code. Clean only explicit generated
locations after checking symlinks/ownership; preserve developer work and data.
