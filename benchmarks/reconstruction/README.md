# Rejected candidate reconstruction

`manifest.json` records each patch's original SHA-256, exact94 base commit and hashes
of the reconstructed source files. The check workflow applies patches only in an
isolated temporary directory and verifies every resulting file. These six candidate
patches replace the need to retain their old build/source-copy trees. Their historical
performance rejection remains unchanged; do not install them as the accepted runtime.

The current frame-reader candidate already has a deterministic patch recipe in
`workflows/benchmark.reference.reader.prepare/assets/patch.py`. Other generated
diagnostic observers retain their recipes in their owning workflows. This archive
does not claim that every historical diagnostic binary has been rebuilt or that an
old binary checksum will survive a different toolchain, path or host.
