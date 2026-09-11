---
title: '1-4 Provide a bounded native packet adapter and deterministic I/O double'
type: feature
created: '2026-09-11'
status: done
review_loop_iteration: 0
baseline_commit: 88f4686c83eafe0eef86561899d6b741165fd0b6
owner_baseline_commit: ee17409ef2fd4d78b25fc8835deeb0177788f0f0
context:
  - '{project-root}/AGENTS.md'
  - '{project-root}/docs/agent-test-policy.md'
  - '{project-root}/repos/fujinet-nio/AGENTS.md'
---

<frozen-after-approval reason="approved Story 1.4; routine checkpoints disabled by execution-gates.md">

## Intent

**Problem:** NativeFramer merges arbitrary channel reads, has unbounded accumulation and hides send failures; it cannot establish packet correctness.

**Approach:** Add the minimum explicit packet source/sink capability, bounded NativeFramer storage/work and deterministic opaque packet/fault double. Implements CAP-2 and approved Story 1.4. Story 1.3 is accepted at the owner baseline with 324 passing cases.

## Boundaries & Constraints

**Always:** Preserve IFramer's raw boundary, ITransport/service semantics and serial behavior. Expose complete-packet ownership, capacity, receive/send/reset outcomes. You are not alone: worker owns listed production/test files; parent owns `docs/native-packet-contract.md` and story records, review and commits. Preserve others' edits. Coordinate final verification after parent documentation is ready.

**Ask First:** Required changes to broker/retry/service semantics, library/driver, or physical protocol.

**Never:** Infer boundaries from byte reads or timing. No silent send success, automatic replay/fallback, remote concurrency, hardware claims, new runtime framework, pushes or co-author trailers. Local reset cannot erase unknown remote completion; broker/retry recovery and explicit software acceptance remain 1.5/1.6.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Queue/order/delay | Two complete records, scheduled arrival, repeated polls | Exactly one packet each, no merging; delayed data unavailable | No-data observable |
| Partial transfer | Bounded incomplete assembly then completion or truncation | No partial delivery; completed packet once; truncated record discarded | Incomplete/truncated distinct |
| Size | Empty, exact-capacity, oversized record, invalid capacity | Explicit empty rejection, exact accepted, oversize discarded with no prefix | Observable failure, bounded storage |
| Backpressure | Occupied receive slot; full bounded adapter TX queue | No additional receive work; send rejected without replay/partial acceptance | Backpressure distinct |
| Transfer failure | Unavailable peer, definite send failure, unknown completion | No false success; one attempt; independent receive/send outcomes | Unknown completion stays latched across local reset |
| Local reset | Ready/queued/partial/scheduled local data; reset failure | Local stale buffers discarded; failure locks path until successful reset | Reset failure observable; no remote quiescence claim |
| Composition | Real transport send and unsupported byte channel | Send failure observable via native adapter/framer; no byte I/O fallback | Unsupported native bootstrap fails closed |

</frozen-after-approval>

## Code Map

Paths are workspace-relative. Read-only investigation established the Channel gap and all native callers.

- `repos/fujinet-nio/include/fujinet/io/core/channel.h`: available/read expose bytes only, write returns void. Add default null packet-capability accessor with forward declaration; existing channels remain source-compatible.
- `repos/fujinet-nio/include/fujinet/io/core/packet_io.h`: new minimal interface with immutable capacity, nonblocking receive into caller-bounded storage returning status+size, single-attempt send returning status, and local reset returning status. No service logic or wire encoding.
- `repos/fujinet-nio/include/fujinet/io/transport/native_framer.h`, `src/lib/native_framer.cpp`: replace stub. One owned receive slot, at most one adapter receive per poll, no receive while slot occupied. Bound effective raw capacity by adapter capacity and 65535; zero invalid. Expose receive/send/reset outcomes separately and clear output on failed extraction.
- `repos/fujinet-nio/src/lib/bootstrap.cpp`: native selection requires explicit packet capability and usable capacity before registering transport. Existing Zorro profile is PTY placeholder only and must fail closed. Serial branch unchanged.
- `repos/fujinet-nio/tests/packet_io_double.h`: reusable bounded opaque queue/event fixture, explicit delivery steps, partial staging, faults and local reset; no sleeps or FujiBus service emulation.
- `repos/fujinet-nio/tests/test_native_framer.cpp`: replace byte-stream-stub tests with every matrix case, including real transport send and native bootstrap capability checks. Reuse literal fixtures where testing transport.
- `repos/fujinet-nio/src/lib/fujibus_transport.cpp`: ensure raw serialization failure is forwarded as empty rejected input to the framer, so native status cannot remain an earlier success; serial empty-send behavior stays unchanged.
- `repos/fujinet-nio/docs/protocol_reference.md`: worker updates stale native-stub paragraph and links contract.
- `repos/fujinet-nio/docs/native-packet-contract.md`: parent documents public adapter contract, limits, outcomes, ownership and scope/gates.

## Tasks & Acceptance

**Execution:**
- [x] Packet capability and NativeFramer — bounded whole-packet delivery, explicit outcomes, reset and unsupported-channel behavior.
- [x] Bootstrap — fail closed for missing capability without touching serial composition.
- [x] Double/tests — deterministic coverage of all matrix rows and executed work/queue bounds.
- [x] Protocol reference and native contract — document software guarantees and deferred recovery/hardware gates.
- [x] This story — record exact verification, review and acceptance evidence.

**Acceptance Criteria:**
- Given queued complete packets, delayed delivery and repeated polls, when extracting, then boundaries survive and empty/exact/oversize/truncated outcomes are tested.
- Given full queues, send failure or reset, when progressing I/O, then storage/work are bounded, failures observable and stale local buffers cannot become later valid packets.

## Spec Change Log

- Planning refinement: transport currently skips the framer when raw serialization fails, leaving a previous native send success visible. Add the narrow failure forwarding and regression to the code map; preserve ITransport and valid serial behavior.

## Design Notes

Adapter owns partial assembly and queue storage; caller buffers are borrowed only during a call. Receive success means one complete nonempty opaque record; malformed/oversized records are consumed without prefixes. Send success means local acceptance, not remote effect or response. Backpressure/definite rejection accepts nothing; unknown completion must be distinct and remain blocked across local reset. Do not add remote recovery API before Story 1.5 evidence. Reset drops local receive/transmit/partial/scheduled state; failure keeps framer unusable. A successful local reset neither proves remote quiescence nor permits retry after ambiguous completion. No automatic retries exist here. Keep capability identity stable per framer so changing adapters cannot expose a prior slot. Test double bounds apply to both record count and bytes; oversize injection may use bounded data plus length metadata.

## Verification

From workspace root: `source scripts/env.sh && cd repos/fujinet-nio && ./build.sh -cp fujibus-pty-debug && ctest --test-dir build/fujibus-pty-debug -R '^fujinet-nio-tests$' --output-on-failure`.

Expected: complete host gate including native packet faults and unchanged serial/SIO cases passes. Run firmware `./scripts/update_cmake_sources.py` if adding production sources. Run workspace and firmware `git diff --check`; docs contract must map to exercised tests. No library/driver/guest edits or physical profile means no extra owner/hardware gate. Parent records any environment blocker rather than skipping.

## Execution results

Clean V-CXX build and required explicit host CTest passed on 2026-09-11. Initial C++ suite: 335/335 cases, 6740/6740 assertions, zero skipped. Build's automatic Python suite also passed 23 tests. After disabling unsafe NativeFramer copy/move, the affected code was incrementally rebuilt and host CTest passed again with static assertions for all four operations. Final host output is retained for review in `/tmp/story-1-4-tests.log` (copied from firmware `build/fujibus-pty-debug/Testing/Temporary/LastTest.log`). Workspace and firmware diff checks passed.

Initially sixteen native cases replaced five stub cases. Matrix coverage includes queued/delayed packets and exact call counts; partial completion/truncation; empty, exact, metadata-only oversize and canonical 65535 cap; RX/TX count and byte budgets; no automatic replay; unavailable/definite send errors; uncertainty from send and receive across local resets; clearing ready/queued/partial/scheduled/TX buffers; failed reset locking; missing/zero capacity; adapter mutation before direct extraction; literal real transport response bytes and failure; serialization rejection; native bootstrap and retained serial bootstrap. Noncopyable ownership is compile-checked. No new production source unit requires source-list generation; headers and an existing test source changed.

Parent review during implementation added three narrow guards: receive-reported uncertainty also latches, extraction rechecks capability identity, and the transport forwards empty serialization to make native failure observable. NativeFramer copy/move are deleted to prevent duplicated ownership or moved-from buffer/length inconsistency. None supplies remote recovery or hardware evidence.

## Review outcome and final verification

All three review layers completed. The verification-gap reviewer found no gaps. Blind/edge findings were triaged and resolved with narrow patches: uncertainty returned by reset stays latched, and adapter receive/send ResetRequired invalidates the slot and locks I/O. The contract now enumerates legal operation results and requires exclusive active-framer use instead of promising synchronization among interleaved framers.

Validated send fault injection replaces the unrestricted status field. Additional tests cover local acceptance before ambiguity, failed reset retaining adapter state, independent send/extracted-buffer ownership, defensive invalid receive lengths, smaller native response capacity and serial oversized-serialization recovery. Parent inspected the state guards and these regressions after patching. No blocker or deferred scope remains in this story.

Final exact command: `source scripts/env.sh && cd repos/fujinet-nio && ./build.sh -cp fujibus-pty-debug && ctest --test-dir build/fujibus-pty-debug -R '^fujinet-nio-tests$' --output-on-failure`. Clean build passed **344/344 cases, 6856/6856 assertions, zero skipped**, plus the build's **23 Python tests**. Explicit host CTest passed **1/1**. Logs: `/tmp/story-1-4-build.log`, `/tmp/story-1-4-tests.log`. Both workspace and firmware `git diff --check` passed. Twenty-five native cases now replace the original five stub cases; all matrix rows and review patches have executed coverage. Durable evidence is this command/count record, the committed tests and the accepted owner revision below.

Story 1.4 is accepted. Stories 1.2, 1.3 and 1.4 are complete; no library, driver, service, guest or physical hardware implementation changed. Actual broker/retry recovery remains gated by Story 1.5's human checkpoints; Story 1.6 still requires explicit acceptance of the complete software contract. No physical readiness or remote-quiescence claim follows from these host tests.

## Suggested Review Order

- Read ownership, legal outcomes and the explicit limits of local reset.
  [native-packet-contract.md:1](../../../../repos/fujinet-nio/docs/native-packet-contract.md#L1)
  [packet_io.h:8](../../../../repos/fujinet-nio/include/fujinet/io/core/packet_io.h#L8)
- Follow bounded receive delivery and fault latching.
  [native_framer.cpp:32](../../../../repos/fujinet-nio/src/lib/native_framer.cpp#L32)
- Check fail-closed bootstrap and observable serialization rejection.
  [bootstrap.cpp:43](../../../../repos/fujinet-nio/src/lib/bootstrap.cpp#L43)
  [fujibus_transport.cpp:130](../../../../repos/fujinet-nio/src/lib/fujibus_transport.cpp#L130)
- Inspect the bounded opaque double and fault regressions.
  [packet_io_double.h:15](../../../../repos/fujinet-nio/tests/packet_io_double.h#L15)
  [test_native_framer.cpp:1](../../../../repos/fujinet-nio/tests/test_native_framer.cpp#L1)

Accepted firmware commit: `fd965f5ec8609bacead86b94a23f73093da98de2`.
