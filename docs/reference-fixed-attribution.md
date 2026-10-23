# Reference cost attribution under the fixed schedule

## Scope and predefined plan

The 2026-10-23 probe follows the [baseline reference context controls](reference-position-context.md).
Those ordinary controls showed a reference penalty when waiting moves before the
request, even with intended cycle rate and the other request starts held fixed.
The new question is where that extra observed cost appears: refresh/validation,
semantic stages or the surrounding process/client boundary.

Receipt root: `bin/.local/benchmarks/reference-context/fixed-schedule-attribution-v1/`.
The exact plan is frozen in `run-manifest.json` before collection. Four serial
baseline-only processes use an **ordinary, probe, probe, ordinary** sequence. Each
mode has both incoming arm orders; two processes/mode are limited replication,
not observer-equivalence qualification. A bounded Sol/high read-only scope review
finished before timing; its corrections are in `design-review.json`.

All processes retain the previous 250 ms absolute cycles: symbols at 0 ms,
references immediately after symbols verification or with a 25 ms return-to-start
floor, definition at 100 ms and search at 150 ms. Each process has 24 warmup cycles,
eight counterbalanced blocks, four acclimation and 16 measured cycles/block.
Adjacent blocks have opposite arms; PQQPPQQP and its complement balance order.
Every response checks the frozen exact oracle, both MCP content forms and complete
metadata. Every phase, actual gap, deadline/readiness miss and timer wake lateness
remains. No gap normalization, replacement cells or timing-based exclusions occur.

Ordinary processes use the frozen qualified exact94 core/worker. Probe processes
reuse the qualified generated baseline core and generated worker with existing
wall stages and invocation process-CPU clock reads. No production sources or
fresh-validation, cancellation, security, strict defaults or cooperative recovery
are changed. No new build is needed: core/worker binaries, generated source,
qualification logs and native-clock ABI/calibration receipts are verified by hash.
These are reused qualifications; no new platform build or calibration is claimed.

Probe collection also observes client JSON serialization/parsing, reader queueing
and Python GC callbacks. The original client class and callback list are restored
and asserted after each probe before another ordinary process. Full configurations
are hashed per mode because worker paths differ; common startup security policy is
independently identical. All processes use the same allowed environment/fixture.
No agent or other benchmark overlaps collection.

## Accounting and interpretation limits

Exact **per-request wall** identities are computed before arithmetic means/deltas:

```
client total = worker invocation + boundary residual
worker invocation = refresh + measured semantic stages + invocation residual
measured semantic stages = text + syntax + model + findSymbol + findReferences + referenceRender
```

The second identity applies to references. These measured semantic stages are
sequential siblings in this observer. Signed residuals are retained. Invocation
residual includes pre/post-refresh path validation, untimed work and observer
bookkeeping, including the process-CPU clock reads. It is not purely semantic or
purely validation work. Independent stage medians are descriptive and do not add.

`refresh` includes metadata admission, opening, bounded reads, memory copies,
resource checks and hashing. Global `pathCheck` crosses its boundary: some calls
occur inside refresh, others before/after. Metadata admission can contain path
checks. `openHandle` and `readHash` are refresh children, not extra terms to add;
hash finalization happens outside `readHash`. `referenceRender` includes location
conversion, sorting and JSON sort-key serialization.

Boundary residual contains queueing, scheduling, transport, core/client parsing and
serialization, observation and other unmeasured work. It is not pure transport.
Native core scopes overlap each other; they cannot all be summed. Worker process
CPU covers all worker threads, GC and background work during invocation and can
exceed wall time. It is neither foreground-only CPU nor retired instructions;
subtracting it from wall does not measure off-CPU time. No frequency, cache, GC or
scheduler mechanism is inferred from these timers.

Every probe phase must retain exactly one fresh 4,096-byte source read for symbols,
definition and references, zero for search and zero foreground full recoveries.
Those counters do not measure or deny successful background recovery sweeps.

The descriptive reproduction gate is fixed in advance: **both mean and median
reference latency must increase under wait-before in every ordinary/probe process**.
Every block-pair direction is reported, not selected. A failed gate or fixed-slot
readiness overrun prevents transferred localization and does not trigger a larger
matrix. Passing supports bounded directional attribution under this observer;
it does not prove ordinary/probe equivalence or accept a production optimization.

## Replay

Use perf-venv on PATH. Collection requires a fresh label; the audit issues no
semantic requests and refuses different derived data:

```sh
FREEFLIGHT_REFERENCE_ATTRIBUTION_LABEL=NEW_LABEL dockpipe --workflow benchmark.reference.attribution
FREEFLIGHT_REFERENCE_ATTRIBUTION_LABEL=fixed-schedule-attribution-v1 dockpipe --workflow benchmark.reference.attribution.audit
```

Raw samples, per-process core/worker stderr, joined IDs, both observer configurations,
frozen oracle, copied adapters/review, fresh-byte accounting and immutable derived
summaries remain with the receipt. Replaying documents reproducibility, not a reason
to repeat unchanged measurements seeking favorable results.

## Results

All four serial processes exit successfully. **2,048 measured +512 acclimation
+384 warmup +16 initial oracle =2,960 exact checked responses** pass. The primary
audit and receipt-only replay pass. The frozen reproduction gate passes in all
four processes for both arithmetic mean and median; every one of the 16 nested
block pairs also has a positive reference mean/median wait penalty. No fixed-slot
readiness overrun occurs; actual wake lateness and cycle jitter remain.

| Mode | Operation | Session median ratio | Session p90 ratio | Within-process median ratios |
| --- | --- | ---: | ---: | --- |
| ordinary | symbols | 1.0222 | 1.0438 | 1.0059, 1.0391 |
| ordinary | definition | 1.0066 | 0.9942 | 1.0049, 1.0083 |
| ordinary | references | 1.5814 | 1.4956 | 1.5071, 1.6560 |
| ordinary | workspaceSymbols | 0.9956 | 0.9983 | 1.0046, 0.9866 |
| probe | symbols | 0.9828 | 0.9816 | 0.9779, 0.9878 |
| probe | definition | 0.9940 | 0.9661 | 1.0043, 0.9842 |
| probe | references | 1.5240 | 1.5390 | 1.4940, 1.5504 |
| probe | workspaceSymbols | 1.0090 | 1.0013 | 1.0146, 1.0032 |

Ratios are wait-before/immediate. Ordinary reference session ratios are 1.507 and
1.656; probe ratios are 1.494 and 1.550. This agreement supports directional
reproduction, without treating two processes/mode as an equivalence test. The
unfavorable/non-reference cells and every block remain; no source candidate is
being accepted or re-screened.

### Exact reference mean wall decomposition

Each cell is **wait-before minus immediate**, in ms, using per-request arithmetic
means. The final column is the equal-weight average of the two session deltas,
not a median subtraction or a fraction of an ordinary uninstrumented result.

| Component | Probe 1 delta | Probe 2 delta | Mean of probe deltas |
| --- | ---: | ---: | ---: |
| Client total | 1.2367 | 1.4618 | 1.3493 |
| Refresh/admission | 0.2004 | 0.2014 | 0.2009 |
| Measured semantic stages | 0.4833 | 0.5758 | 0.5295 |
| Invocation residual | 0.0554 | 0.0661 | 0.0607 |
| Boundary residual | 0.4977 | 0.6185 | 0.5581 |

These disjoint components account for the complete added probe wall time. Refresh/
admission is about 14.9% of that mean delta, measured semantic stages 39.2%, invocation
residual 4.5% and boundary residual 41.4%. These percentages describe this observer
and workload; refresh is not a complete isolated validation total, and boundary is
not an isolated transport total. All four components grow in every one of the eight
probe block pairs. No negative per-request residual occurs.

Within semantic stages, `findReferences` adds 0.4083/0.4989 ms in the two sessions:
most of the measured semantic increment. Other named increments remain below.

| Cross-cutting/nested observation | Probe 1 mean delta ms | Probe 2 mean delta ms |
| --- | ---: | ---: |
| worker.processCpuInvoke | 1.4497 | 1.5712 |
| worker.pathCheck | 0.0412 | 0.0546 |
| worker.metadataAdmission | 0.0122 | 0.0105 |
| worker.openHandle | 0.0900 | 0.0836 |
| worker.readHash | 0.0429 | 0.0439 |
| worker.model | 0.0086 | 0.0088 |
| worker.findSymbol | 0.0334 | 0.0480 |
| worker.findReferences | 0.4083 | 0.4989 |
| worker.referenceRender | 0.0295 | 0.0168 |
| worker.queue | 0.0188 | 0.0219 |
| worker.gate | 0.0020 | 0.0018 |
| worker.serialize | 0.0101 | 0.0089 |
| worker.write | 0.0043 | 0.0041 |
| coreThreadCpu.coreTotal | 0.2180 | 0.2544 |
| clientProfile.serializeMs | 0.0525 | 0.0673 |
| clientProfile.readerQueueMs | 0.0293 | 0.0235 |
| clientProfile.parseMs | 0.0309 | 0.0309 |

These are **not extra disjoint terms** to add to the partition. For example open/
readHash are inside refresh; pathCheck crosses refresh; core thread CPU overlaps
core wall scopes. Worker process CPU rises 1.4497/1.5712 ms during invocation,
across all worker threads. It already exceeds invocation wall in both arms because
parallel work is included. This establishes more process CPU time in that window,
not more retired instructions, a foreground-only cost, or an off-CPU estimate.
No Python GC pause/collection is recorded during measured probe reference requests;
this does not measure .NET GC or deny background work.

### Boundary expansion without another benchmark

A separately retained `boundary-result.json` adds receipt-only algebra after
collection, using every reference phase and every measured block pair. The original
reproduction gate and timings remain unchanged. Logical nested request durations
give these exact per-request identities:

```
boundary residual = worker envelope + core routing + outer MCP/client
worker envelope = core workerRoundTrip - worker invoke
core routing = core serverCall - core workerRoundTrip
outer MCP/client = client total - core serverCall
```

Only durations are subtracted; cross-process clock origins are not compared. Every
one of 368 recorded probe reference requests satisfies the identity and has
nonnegative residuals. The helper and derived result refuse replacement by different
data and run as the second step of the receipt-only audit workflow.

| Boundary component | Probe 1 mean delta ms | Probe 2 mean delta ms |
| --- | ---: | ---: |
| workerEnvelope | 0.1212 | 0.1238 |
| coreRouting | 0.1330 | 0.1628 |
| outerMcpClient | 0.2435 | 0.3319 |

Worker envelope includes worker request/reply processing, queueing/scheduling,
parsing, serialization and transport. Core routing includes authorization/path
checks/native dispatch and observation. Outer MCP/client includes envelopes,
queueing, serialization/parsing, scheduling and observation. These names identify
logical interval scopes, not pure subsystems. All three increments are positive in
both sessions; each block pair remains available. There is a boundary contribution
outside the worker round trip as well as a real invocation contribution.

### Cadence and fresh-read evidence

Every mode/arm measured symbol-start period has a median within about 0.003 ms of
250 ms. Individual periods span roughly 240–260 ms, with timer lateness recorded.
Configuration policy matches across modes despite different observer DLL paths.
The callback/client-class restoration assertions pass before the final ordinary
control. No source or sleep setting is changed based on observed timings.

Across all recorded probe phases, 1,104 targeted responses read exactly one
4,096-byte file each, and 368 searches read none; no foreground full recovery is
recorded. The measured subset includes 768 targeted reads and 256 searches. These
counts check unchanged fresh reads, not successful background sweep accounting.
Before/after fixture/driver/binary/qualification hashes match.

## Decision and next step

Keep production exact94 and the JSON-copy candidate archived/unaccepted. The
additional reference cost is distributed: refresh/admission, Roslyn reference
execution, core routing and the MCP/client boundary all contribute. Removing fresh
validation would violate the contract and would not remove most of this increment.
The results do not support a transport-only diagnosis or a production remedy yet.

Next isolate instruction/work growth from execution-rate/runtime-state effects
within `FindReferences` and the core routing interval, with one narrow separate
profile under this reproduced schedule. Do not transfer these process-CPU counters
into a frequency, cache, GC or scheduler claim. Keep all validation/recovery and
ordinary all-operation screening for any genuinely new optimization. No larger
Glider matrix or unchanged rejected candidate repeat is justified. Glider definition/
search and idle gaps, native allocation attribution, real repositories, long-duration
memory and other platforms remain open. No commit, push, merge or publication.

Follow-up: [short work-counter qualification](reference-work-qualification.md) preserves
failed managed/native precision gates; no new FreeFlight probe or matrix was run.
