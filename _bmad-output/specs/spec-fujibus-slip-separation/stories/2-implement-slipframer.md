---
title: 'Implement SlipFramer'
type: 'refactor'
created: '2026-08-29'
status: 'in-progress'
review_loop_iteration: 0
baseline_commit: '51a1f76f631468999b07b9611dc678314620b7c5'
context: []
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** SLIP framing logic (`extractSlipFrame`, `_rxBuffer`, `C0`-delimiter handling) lives inside `FujiBusTransport`, coupling two unrelated concerns and making SLIP-specific bugs hard to isolate.

**Approach:** Implement `SlipFramer : IFramer` (new files) carrying all existing SLIP logic verbatim from `FujiBusTransport`. Retarget every existing SLIP framing test to call `SlipFramer` directly. `FujiBusTransport` is not changed in this story.

## Boundaries & Constraints

**Always:**
- All existing SLIP framing test cases must survive and pass, retargeted to `SlipFramer::nextPacket` — not deleted, not left testing via `FujiBusTransport`
- The `C0`-consecutive-delimiter and stale-delimiter logic must be preserved exactly as in `extractSlipFrame` (the bug fix from the previous session)
- `SlipFramer` must have zero FujiBus knowledge — no `FujiBusPacket`, no `IORequest`, no `IOResponse`
- `FujiBusTransport` is read-only in this story — no changes to it

**Ask First:**
- Any dependency not already present in the codebase

**Never:**
- Touch `fujibus_transport.cpp` or `fujibus_transport.h`
- Introduce `#ifdef` for any purpose
- Remove or disable any existing test

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Normal frame | `[C0][payload][C0]` in channel | `nextPacket` returns `true`, `outPacket` = raw SLIP bytes | — |
| Stale leading C0 | `[C0][C0][payload][C0]` | Returns `true`, correct payload extracted | — |
| Multiple stale C0s | `[C0][C0][C0][payload][C0]` | Returns `true`, correct payload extracted | — |
| Only C0 bytes | `[C0][C0][C0]` | Returns `false`, no crash | Keep last C0; may be frame start |
| Incomplete frame | `[C0][partial-payload]` (no closing C0) | Returns `false` | Wait for more bytes |
| Two back-to-back frames | `[frame1][frame2]` in buffer | First call returns frame1; second call returns frame2 | — |
| Stale C0 then two frames | `[C0][frame1][frame2]` | Both frames extracted in order | — |

</frozen-after-approval>

## Code Map

- `repos/fujinet-nio/src/lib/fujibus_transport.cpp:57-98` -- `extractSlipFrame` static function — move this logic to `SlipFramer`; `_rxBuffer` is `std::vector<uint8_t>` member at transport; becomes `SlipFramer`'s `_rxBuffer`
- `repos/fujinet-nio/src/lib/fujibus_transport.cpp:20-33` -- `poll()` accumulates bytes from channel into `_rxBuffer` — same pattern goes into `SlipFramer::poll`
- `repos/fujinet-nio/include/fujinet/io/transport/iframer.h` -- the `IFramer` interface `SlipFramer` must implement (Story 1 output)
- `repos/fujinet-nio/include/fujinet/io/protocol/fuji_bus_packet.h:14-26` -- `SlipByte` enum and `to_byte()` helper; `ByteBuffer = std::vector<uint8_t>` — `SlipFramer` uses these, nothing else from this header
- `repos/fujinet-nio/include/fujinet/io/core/channel.h` -- `Channel` interface used in `poll` and `sendPacket`
- `repos/fujinet-nio/tests/test_fujibus_transport_framing.cpp` -- 7 test cases in `TEST_SUITE("FujiBusTransport SLIP framing")` to retarget; `LoopbackChannel` and `make_valid_frame` helpers can be reused; `feed()` helper must be rewritten to call `SlipFramer::poll` directly
- `repos/fujinet-nio/tests/CMakeLists.txt:3-6` -- `file(GLOB TEST_SOURCES ...)` auto-discovers new `test_slip_framer.cpp`; no manual registration needed

## Tasks & Acceptance

**Execution:**
- [ ] `repos/fujinet-nio/include/fujinet/io/transport/slip_framer.h` -- declare `SlipFramer : public IFramer` with `_rxBuffer` member and override declarations
- [ ] `repos/fujinet-nio/src/lib/slip_framer.cpp` -- implement `poll` (drain channel bytes into `_rxBuffer`), `nextPacket` (move `extractSlipFrame` logic here operating on `_rxBuffer`), `sendPacket` (write SLIP-framed bytes to channel via `ch.write`)
- [ ] `repos/fujinet-nio/tests/test_slip_framer.cpp` -- new test file: retarget all 7 existing cases from `test_fujibus_transport_framing.cpp` to use `SlipFramer` directly; add `feed()` helper that calls `framer.poll(ch)`; add new cases per I/O matrix (incomplete-frame recovery, only-C0-bytes-kept)
- [ ] `repos/fujinet-nio/scripts/update_cmake_sources.py` -- run after adding `slip_framer.cpp` to regenerate CMake source lists

**Acceptance Criteria:**
- Given `SlipFramer` with a normal SLIP frame pushed, when `poll` then `nextPacket` called, then returns `true` with the correct raw SLIP bytes
- Given stale leading `C0` bytes before a valid frame, when `poll` then `nextPacket` called, then frame is extracted correctly (no spurious empty frame)
- Given only `C0` bytes in the buffer, when `nextPacket` called, then returns `false` without crashing
- Given an incomplete frame (no closing `C0`), when `nextPacket` called, then returns `false`; when remaining bytes fed, then returns `true`
- Given two back-to-back frames, when `nextPacket` called twice, then each frame is returned once in order
- Given `FujiBusTransport` with `SlipFramer` not injected (unchanged), when existing `test_fujibus_transport_framing.cpp` runs, then all original tests still pass (no regression)
- Given the full `fujibus-pty-debug` ctest suite, when run after this story, then 0 failures

## Spec Change Log

## Design Notes

`sendPacket` in `SlipFramer` writes the already-SLIP-encoded bytes from `packet` directly to the channel — the bytes it receives are the output of `FujiBusPacket::serialize()`, which already applies SLIP encoding. `SlipFramer::sendPacket` is therefore a thin `ch.write(packet.data(), packet.size())` — no re-encoding.

The `IFramer::nextPacket` contract delivers the raw SLIP frame (including delimiters) rather than the decoded payload; `FujiBusTransport` (Story 3) will pass the frame to `FujiBusPacket::fromSerialized` which handles SLIP decoding. `SlipFramer` does not call `fromSerialized`.

## Verification

**Commands:**
- `cd repos/fujinet-nio && ./scripts/update_cmake_sources.py` -- expected: exits 0, no error
- `cd repos/fujinet-nio && ./build.sh -p fujibus-pty-debug` -- expected: compiles without error or warning
- `cd repos/fujinet-nio && ctest -V --test-dir build/fujibus-pty-debug --tests-regex fujinet-nio-tests` -- expected: all tests pass including new `SlipFramer` suite and unchanged `FujiBusTransport SLIP framing` suite
- `grep -r "0xC0\|SlipByte\|extractSlip\|_rxBuffer" repos/fujinet-nio/include/fujinet/io/transport/slip_framer.h repos/fujinet-nio/src/lib/slip_framer.cpp` -- expected: matches in SlipFramer files only (correct)
- `grep -r "FujiBusPacket\|IORequest\|IOResponse" repos/fujinet-nio/src/lib/slip_framer.cpp` -- expected: no matches (SlipFramer has zero FujiBus knowledge)
