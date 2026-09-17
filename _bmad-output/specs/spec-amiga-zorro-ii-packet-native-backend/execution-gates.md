# Execution gates and story contract mapping

The approved epic companion contains every story's scope, files, acceptance criteria, risks and planned test commands. This companion makes the readiness rules explicit for spec derivation and dispatch; it does not declare any story completed. No production or hardware work has been performed by creating this package.

## Identity, order and dispatch limits

Approved story `1.5` maps to dispatch ID `1-5`, and likewise throughout. IDs are quoted, unpadded and prefix-free; list order, not filename sorting, determines sequential dispatch. The dispatch schema has no dependency or hardware-state fields: a runner must honor the contract below and the approved story before starting. Listing a hardware story does not authorize it to run without evidence.

The default list follows the approved epic/story order and is a valid sequential topological order. This is not a new dependency forcing bridge setup or feasibility to wait for Epic 1. A separately selected 2-1/2-2/2-3 run may proceed alongside Epic 1 if its own prerequisites, hardware and ownership are satisfied. This package does not create a parallel scheduler or launch any run.

Before starting a story, establish acceptance of all actual prerequisites, required toolchain/guest/hardware availability, and its exact execution/verification procedure. Stop if any is absent; do not skip it silently or substitute a mock pass for physical evidence. An implementation plan and focused tests are prepared when the story becomes ready, not guessed now for every future hardware story.

When dispatching, read the prerequisite decision records as well as story status.
For 1-6, require `contract_acceptance: accepted` and its cited technical review;
`done_checkpoint: false` never bypasses this evidence check. The same coverage
rule applies to 1-5 even though its historical implementation status is done.

**Current acceptance, 2026-09-15:** the
[1.6 technical acceptance](stories/1-6-accept-the-canonical-software-packet-contract-for-bridge-design.md#technical-acceptance-record--2026-09-15)
closes the prior F1–F3 hold through the reviewed retry-containment follow-up.
Both actual callers now establish software backend containment under ambiguity.
This satisfies the 1-5 and 1-6 software prerequisites; direct dependents
1-8/1-10 and 1-9/1-14/2-4 still require every other prerequisite below.
No downstream story is declared ready or done by this decision. Story 2-4 still
needs positive 2-2/2-3 physical evidence and explicit human ABI approval;
physical implementation still requires accepted 1-14. Historical 1-5 completion
is preserved and supplemented by the exact revised evidence in this record.

**Software guest acceptance, 2026-09-17:** the
[1.14 technical acceptance](stories/1-14-accept-end-to-end-native-guest-parity-and-fault-isolation.md#technical-acceptance--2026-09-17)
records passing serial/native guest media and real-service parity, actual queued
and retrying caller containment, and the explicitly approved test-only
peer-acknowledged recovery repair. This satisfies the 1.14 prerequisite only;
2.4 approval, physical evidence and all other hardware gates remain required.

## Required prerequisites

| Dispatch ID | Accepted prerequisites | Evidence/environment gate | Capability |
| --- | --- | --- | --- |
| 1-1 | None | Host tests; independent fixtures | CAP-1 |
| 1-2 | 1-1 | Host codec/compatibility tests | CAP-1 |
| 1-3 | 1-2 | Framer/transport compatibility tests | CAP-1, CAP-2 |
| 1-4 | 1-3 | Explicit packet boundaries and bounded fault tests | CAP-2 |
| 1-5 | 1-4 | Evidence-backed technical review of real broker/retry-path coverage | CAP-3 |
| 1-6 | 1-1, 1-2, 1-3, 1-4, 1-5 | Explicit software packet-contract acceptance | CAP-3, CAP-6 |
| 1-7 | 1-4 | Real file/clock handlers, isolated storage/time | CAP-4 |
| 1-8 | 1-4, 1-5 | Real disk handlers, independent backing-byte and effect checks | CAP-3, CAP-4 |
| 1-9 | 1-6, 1-7, 1-8 | Verified host endpoint and test-only guest connection design | CAP-4 |
| 1-10 | 1-5, 1-9 | Amiga toolchain/guest and actual test broker | CAP-3, CAP-4 |
| 1-11 | 1-10 | Actual guest exchange tool; no serial setup on native path | CAP-4 |
| 1-12 | 1-8, 1-11 | Guest disk tool and explicit disposable write fixtures | CAP-4 |
| 1-13 | 1-7, 1-8 | Host media/catalogue lifecycle parity | CAP-4 |
| 1-14 | 1-6, 1-10, 1-11, 1-12, 1-13 | Actual guest/resident-driver and real-core acceptance | CAP-3, CAP-4 |
| 2-1 | None | Verified standalone toolchain/build; no hardware needed | CAP-5 |
| 2-2 | 2-1 | Independent RP2040/Core2350B 3.3 V bench first; instruments and buffered actual-host fixture for timing/real-bus evidence | CAP-5 |
| 2-3 | 2-1 | RP2350B/ESP32-S3 link hardware and instruments; independent of 2-2 | CAP-5 |
| 2-4 | 1-6, 2-2, 2-3 | Accepted software contract, positive relevant feasibility and explicit ABI agreement | CAP-6 |
| 3-1 | 1-14, 2-4 | Suitable Zorro hardware and ABI-conforming access fixture | CAP-3, CAP-7 |
| 3-2 | 1-14, 2-4 | Hardware, conforming peers and post-ABI sizing review | CAP-7 |
| 3-3 | 1-14, 2-4 | ESP32-S3 and conforming link fixture | CAP-7 |
| 3-4 | 3-1, 3-2, 3-3 | Complete working physical chain | CAP-7 |
| 3-5 | 3-4 | Physical media/catalogue acceptance | CAP-8 |
| 3-6 | 3-4 | Human review before fault injection and after physical evidence | CAP-3, CAP-8 |
| 3-7 | 3-5, 3-6 | Accepted physical parity/recovery plus actual measurements/install validation | CAP-8 |

## Story 2.2 staged hardware gate

Read the mandatory [experiment plan](../../../repos/fujinet-nio/bridges/rp2350-zorro/docs/story-2-2-experiment-plan.md) before dispatch. Host tests and target implementation may proceed before later hardware arrives. Initial independent RP2040/Core2350B capture uses USB diagnostics; externally measured timing and release require adequate instruments. The available TZT RP2040 clone needs verified pinout/flash configuration, and the available eight-channel USB analyzer/HANMATEK DOS1102 scope need verified measurement settings and input/probe configuration; a simple multimeter is also available. W0 wiring is in progress, not yet verified. Real-bus work additionally requires the passive breakout, A500 adapter/host and reviewed buffering. Missing equipment blocks its dependent experiments only. Separate partial bench progress from the positive relevant real-bus evidence required by 2-4; synthetic success cannot release that gate. No ESP project or final physical ABI is part of 2-2. E0–E7 are work packages within the existing dispatch ID, not new stories.

## Technical acceptance and human checkpoints

The user confirmed no routine checkpoints for ordinary stories, with the following exceptions. These dispatch settings do not weaken any acceptance or hardware gate in the contract.

- **1-5 and 1-6 — user amendment, 2026-09-14:** both checkpoint booleans are false. The agent owns technical coverage review and may explicitly accept the software contract on sufficient evidence. Review actual callers, ambiguous completion, ownership, stale responses, and transmission/effect counts; record full revisions and the technical verdict. Passing a suite or an implementation “done” label alone is insufficient. Ask the user only for an unresolved limitation, scope change or meaningful tradeoff. This changes the decision owner, not the safety criteria, and does not retroactively certify missing 1.5 evidence.
- **3-6:** both `spec_checkpoint: true` and `done_checkpoint: true`. Pause before implementation/physical fault injection and after results for human review of safety, disposable-media protections, ownership, actual retries, transmission/effect counts and unresolved gaps.
- **2-4:** `done_checkpoint: true`, `spec_checkpoint: false`. Present the completed ABI contract/evidence for explicit human approval before releasing dependents.
- **All others:** both checkpoint booleans are false. Required hardware, explicit acceptance criteria and the 3-2 sizing condition still apply; missing prerequisites or unsafe findings always stop work.

Routine `invoke_dev_with` notes only point to the matching approved story and this gate companion; they contain no hidden requirements. A dispatcher must pass the SPEC and all mandatory companions to the implementing skill. No per-story implementation files or runtime state are generated by this package.

## Critical gates that must survive later derivation

**Software-to-hardware ABI:** 1-6 must explicitly accept the canonical raw FujiBus representation, packet-boundary semantics, ownership rules and relevant failure behavior. Codec tests alone do not qualify. Positive 2-2/2-3 feasibility can be recorded independently, but cannot finalize/approve 2-4 before that software acceptance. Unrelated unfinished Epic 1 guest/tool work does not block ABI approval once 1-6 is accepted. Actual hardware implementation still waits for 1-14 as well as 2-4.

**Retry safety:** existing disk retries include some writes, and `fn_raw_call` can replay failures. Unknown completion cannot be erased by close/open or an arbitrary delay. Exercise the actual callers. If safe containment cannot be achieved behind the existing backend, withhold 1-6/physical recovery acceptance and obtain a specific scope decision; do not silently change higher-layer semantics.

**3-2 subdivision:** after ABI design, assess size against the agreed state machine. If split, preserve scope, acceptance criteria and traceability; update the dispatch list and require every necessary replacement slice before 3-4. Do not create overlapping IDs such as `3-2` and `3-2-a` in the same list. Apply the installed schema's pinned-ID/retirement rules if a story spec already exists. No split is selected now.

**No physical failover or remote concurrency:** native deployment never switches to an assumed serial backend. Locally queued requests execute remotely one at a time until a future approved safe-correlation design; no transaction field is invented by a test runner or bridge.

**Release:** missing physical evidence, unreviewed faults or unmet media assertions keep readiness blocked. The 25-story planning approval and this package's validation are not acceptance records for 1-6, 1-14, 2-4 or any hardware story.
