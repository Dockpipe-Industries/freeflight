# Small benchmark assets

Git retains reports, workflows, fixture generators, dependency/toolchain pins,
candidate patches and bounded evidence. Builds, SDK/dependency caches and generated
fixtures stay ignored under `bin/.local` and are recreated when needed. Do not upload
or transfer entire build trees as a normal benchmark handoff.

`evidence/20261023-arm64` contains a catalog plus losslessly compressed historical
JSON/JSONL objects. SHA-256 addresses deduplicate identical files. Each compressed
Git object is at most 1 MiB and a checkpoint at most 10 MiB, enforced by repo.check.
The capture preserves complete files: no failed runs, warmup phases or adverse
observations are trimmed within a selected file to make it fit. Original paths,
bytes and hashes remain in the catalog; decompressing an object reproduces its input.

The catalog explicitly distinguishes `git` from `external` entries. Larger historical
measurement files remain ignored in `bin/.local/evidence/20261023-arm64/objects`, with
their hashes/size recorded in Git. They are optional inputs for deeper historical
analysis or later R2 archiving, not requirements to build or run new benchmarks.
They are original observations and cannot be recovered by recompiling. A new run
produces new observations; never label it a recreation of an old measurement.
Bulk text diagnostics and traces also stay local/optional external; they are outside
this JSON evidence export and are not claimed to be captured or rebuildable.

All six preserved rejected source candidates reconstruct from the exact94 Git commit
plus the tiny patches in `reconstruction/`. Their resulting source hashes are checked.
They remain rejected. Compilers/toolchains and dependencies still need provisioning;
the source reconstruction check does not compile or requalify runtime behavior.

```sh
dockpipe --workflow benchmark.evidence.check
```

This verifies Git evidence without the old benchmark/build directories, checks
corruption/budget/path contracts, and reconstructs candidate source in temporary
directories. It does not rebuild historical binaries or rerun timing. Existing
historical benchmark audits may require their original ignored artifacts; this
portable evidence check does not pretend to satisfy those old binary-hash gates.

To capture a new completed run collection, choose a fresh label and explicit source:

```sh
FREEFLIGHT_EVIDENCE_LABEL=NEW_LABEL \
FREEFLIGHT_EVIDENCE_SOURCE=/absolute/path/to/completed/receipts \
  dockpipe --workflow benchmark.evidence
```

Review the catalog before staging. Capture refuses existing destinations, reads only
JSON/JSONL outside generated trees, enforces a 256 MiB decoded-file bound and never
executes run inputs, benchmarks, uploads or deletes originals. New runs should emit
small standalone sample/provenance files alongside ignored verbose diagnostics.
Do not freeze entire SDK/source/build trees as permanent assets; use a commit,
patch/generator and pinned build workflow. Keep only genuinely irreplaceable large
diagnostics externally when the investigation warrants them.

No existing files were deleted by this migration. Removal of local build/cache/fixture
trees is a separate scoped cleanup; original external observations are a different
retention decision. This policy supersedes the prior blanket 18 GB transfer advice.
