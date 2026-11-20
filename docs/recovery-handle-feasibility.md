# macOS recovery handle feasibility

Local continuation from `7f57cc7`. Runtime remains `6a06b1d`; this pass changes only
workflow tests and documentation. It demonstrates a native primitive that avoids
the earlier FIFO drain hazard, but does not qualify a parallel Roslyn reader.

## Supported APIs and observed behavior

Apple documents nonblocking opens and leaf no-follow behavior in
[open(2)](https://developer.apple.com/library/archive/documentation/System/Conceptual/ManPages_iPhoneOS/man2/open.2.html),
and handle-based metadata in
[fstat(2)](https://developer.apple.com/library/archive/documentation/System/Conceptual/ManPages_iPhoneOS/man2/fstat.2.html).
The installed SDK and Apple's
[fcntl header](https://github.com/apple-oss-distributions/xnu/blob/main/bsd/sys/fcntl.h)
define `O_NOFOLLOW_ANY` for all path components. Public source is explanatory, not
an assertion that its current main branch exactly matches the running kernel.
The receipt pins the installed header hash and host version.

On this macOS 27.0.1 arm64 host, the tested flags are
`O_RDONLY | O_NONBLOCK | O_CLOEXEC | O_NOFOLLOW_ANY` (`0x21000004`). Combining
`O_NOFOLLOW_ANY` with `O_NOFOLLOW` instead fails with `EINVAL`, including for a
regular file. The failed `handles-v1` attempt is retained; the corrected primitive
must not silently retry a security rejection with weaker flags.

After open, `fstat` admits only regular files. Cancellation is checked before open
and again after acquiring the descriptor. Every acquired descriptor is closed in
`finally`, including injected metadata failure and cancellation. The probe checks
current pathname device/inode identity before reading, but this is explicitly not
an atomic namespace guarantee. Its reads are limited to 8192 bytes; no background
work or persistent handle cache is introduced.

`benchmark.recovery.handles` passes 24 cases, including negative controls:

- Exact regular-file bytes, nonblocking and close-on-exec flags.
- FIFO, directory, Unix socket, leaf symlink and `/dev/null` rejected before content
  reads. Only `/dev/null` is opened for the character-device test; no devices are
  created, and arbitrary devices are not exercised.
- Leaf-only no-follow opens a disposable synthetic file through an ancestor
  symlink; all-component no-follow rejects it. An ancestor replaced with a symlink
  immediately before open is also rejected.
- Regular input replaced before open with a symlink, FIFO or directory is rejected.
- Replacement/deletion after open is detected by the identity check; same-size,
  restored-timestamp edits on the same inode return the changed bytes.
- Pre-cancel, cancel after open, and injected `fstat` failure release owned handles.
- Width-two/four FIFO batches and cancellation batches drain with exactly two/four
  peak owned descriptors, zero retained descriptors and zero content reads. Sorted
  result selection preserves the modeled earlier resource error. This is a queue
  model, not full worker error-precedence qualification.
- A replacement after the final identity check still permits reading the old,
  already-open regular inode. The test records this race instead of claiming that
  identity checks make namespace mutation atomic. It does not read the replacement
  symlink target. SECURITY.md already disclaims hostile-mutation race freedom.

## Rejected assumption and termination limit

The `handles-v3` extension incorrectly expected an `O_EVTONLY` descriptor to reject
regular-file reads. The assertion failed: this host can read its bytes both before
and after `F_SETFL`; the event-only bit remains set. The corrected probe preserves
that observation. Apple's [event-only documentation](https://developer.apple.com/documentation/system/filedescriptor/openoptions/eventonly)
describes a notification use, not a capability boundary. This pass therefore does
not use it as a metadata-only security mechanism or assert an impossible upgrade.
`handles-v2`, `handles-v4`, `handles-final` and the final frozen-source run are retained.

Nonblocking FIFO success is not proof that all filesystem operations can be forcibly
terminated. Cancellation checks in this prototype run between syscalls. They cannot
execute inside an in-flight open/fstat/read. The inspected APIs offer no per-call
CancellationToken or elapsed-time deadline. Even the separate asynchronous API has
an explicit [AIO_NOTCANCELED result](https://developer.apple.com/library/archive/documentation/System/Conceptual/ManPages_iPhoneOS/man2/aio_cancel.2.html);
it does not supply a guaranteed cancellation boundary for speculative opens.
No filesystem stall, raw disk, remote mount or kernel-fault experiment was induced.
This is a concrete capability limit of the tested design, not a measured claim
that ordinary APFS regular-file calls stall or a proof against every design.

`fstat` also occurs after the object's open operation. Rejecting device content does
not establish that opening every possible device is free of effects. A pathname
file-type precheck would add a replacement window, not remove that ordering.

## Decision

The FIFO-specific gate is resolved for this native macOS primitive. General safely
terminating speculative filesystem work is not established, so there is no runtime
parallelization or performance candidate in this commit. A failure in an earlier
sorted file must not leave unowned later operations alive; returning before drain
is not an accepted shortcut. The existing serial runtime also lacks hard syscall
cancellation, and this report does not invent such a guarantee for it.

Recommended next design is to port and qualify regular-handle admission **serially**
first, preserving exact existing external-input handling, uncached pre-read checks,
resource accounting and error mapping. That provides a separate fault-hardening
benefit, not a promised recovery speedup. For parallel filesystem work, either prove
an explicit supported-filesystem drain contract or design a disposable process
boundary with owned request lifetime and bounded transport. That is a larger design
decision; killing the stateful Roslyn worker would discard the committed workspace
and is not an equivalent transaction-preserving optimization. Serial fallback must
remain available on unsupported platforms and capability failures; it cannot undo
an already-issued speculative call. CPU-only parallel work avoids speculative opens
but has the smaller opportunity recorded in the preceding report.

No freshness deadline, strict-default setting, cancellation-source lifetime,
publication or active configuration changed. No new median/p90/CPU/allocation or
MCP result is claimed. .NET interop, full worker mutation/transaction tests and
cross-platform qualification remain unexecuted for this proposed primitive.

## Reproduce

```sh
PATH="$PWD/bin/.local/perf-venv/bin:$PATH" \
FREEFLIGHT_RECOVERY_HANDLES_LABEL=handles-repeat \
dockpipe --workflow benchmark.recovery.handles
```

Use a fresh label. The workflow runs a contained child with a 30-second outer test
limit. That test containment is not production cancellation behavior. It freezes
its exact Python source beside the final receipt, records SDK header hash, host,
Python version, source commit, cases and descriptor counts. The final result is
`bin/.local/benchmarks/recovery-handles/handles-qualified/result.json`.
Earlier failed attempts retain logs; they are not relabeled successful. No operation
was denied, left pending or of uncertain outcome. Final repo.check and Python syntax
validation pass. No runtime or ordinary timing process was started.
