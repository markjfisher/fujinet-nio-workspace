---
title: 'Refactor FujiBusTransport to accept IFramer'
type: 'refactor'
created: '2026-08-29'
status: 'done'
baseline_commit: 'e0df4bb2650be4f9bc0084803197eeda201974c1'
review_loop_iteration: 0
context: []
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** `FujiBusTransport` still owns `_rxBuffer`, `extractSlipFrame`, and all `0xC0`/`SlipByte::End` references, duplicating logic now in `SlipFramer` and blocking packet-native channels from reusing the FujiBus parser.

**Approach:** Inject `IFramer&` into `FujiBusTransport` via constructor; strip all SLIP logic from it; update `bootstrap.cpp` and all tests to wire `SlipFramer`. `FujiBusTransport` becomes responsible only for FujiBus packet parsing and encoding.

## Boundaries & Constraints

**Always:**
- After this story, `grep` over `fujibus_transport.cpp` and `fujibus_transport.h` must find zero SLIP references (`0xC0`, `SlipByte::End`, `extractSlipFrame`, `_rxBuffer`)
- The `test_embed_core.cpp` `InMemoryChannel` integration tests must remain unchanged and pass
- Full `fujibus-pty-debug` ctest suite must be green — zero regressions
- Framer selection is by construction (factory/test site), never `#ifdef`

**Ask First:**
- Any change to `IFramer` interface beyond what Story 1 defined

**Never:**
- Introduce `#ifdef` to select framer
- Remove or disable any existing test
- Touch the Amiga serial backend (`fujinet_nio_serial_backend.c` / `fn_session.c`)

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Normal receive | SLIP frame arrives, `poll` then `receive` called | `IORequest` populated correctly | — |
| Normal send | `IOResponse` passed to `send` | Serialized FujiBus packet written via `_framer.sendPacket` | — |
| Incomplete frame | Partial SLIP bytes, `poll` + `receive` | `receive` returns `false` | Wait for more |
| FujiBusTransport no SLIP refs | After refactor | `grep` over both transport files returns empty | — |

</frozen-after-approval>

## Code Map

- `repos/fujinet-nio/include/fujinet/io/transport/fujibus_transport.h:13-35` -- current class; add `IFramer& _framer` member, change constructor to `FujiBusTransport(Channel& channel, IFramer& framer)`, remove `_rxBuffer`
- `repos/fujinet-nio/src/lib/fujibus_transport.cpp:20-98` -- `poll` and `extractSlipFrame`; replace `poll` body with `_framer.poll(_channel)`; delete `extractSlipFrame`; replace `extractSlipFrame(_rxBuffer, frame)` calls in `receive` (line 109) and `receiveResponse` (line 207) with `_framer.nextPacket(frame)`; replace `_channel.write(...)` in `send` (line ~199) with `_framer.sendPacket(_channel, serialized)`; remove `SlipByte`/`to_byte`/`_rxBuffer` usages
- `repos/fujinet-nio/src/lib/fujibus_transport.cpp:40-45` -- `wait_for_work`: currently checks `!_rxBuffer.empty()` first; after refactor, remove that check and rely solely on `_channel.wait_for_readable(timeout)` (minor performance trade-off, functionally correct)
- `repos/fujinet-nio/src/lib/bootstrap.cpp:35` -- sole production construction site; change to `auto* framer = new io::SlipFramer(); auto* t = new io::FujiBusTransport(channel, *framer);` — framer is heap-allocated alongside transport (both owned by the core lifecycle)
- `repos/fujinet-nio/include/fujinet/io/transport/iframer.h` -- Story 1 output; `FujiBusTransport` gains a `IFramer& _framer` member
- `repos/fujinet-nio/include/fujinet/io/transport/slip_framer.h` -- Story 2 output; used in bootstrap and tests
- `repos/fujinet-nio/tests/test_fujibus_transport_framing.cpp:53-173` -- 7 tests constructing `FujiBusTransport t(ch)`; each needs a `SlipFramer` local and `FujiBusTransport t(ch, slipFramer)` — these become integration tests of transport + framer together
- `repos/fujinet-nio/tests/test_fujibus_transport_mapping.cpp:58,95` -- 2 tests constructing `FujiBusTransport t(ch)`; same `SlipFramer` injection needed
- `repos/fujinet-nio/tests/test_embed_core.cpp` -- uses `setup_transports` from bootstrap; must NOT be changed; will work automatically once bootstrap wires `SlipFramer`

## Tasks & Acceptance

**Execution:**
- [x] `repos/fujinet-nio/include/fujinet/io/transport/fujibus_transport.h` -- add `#include "fujinet/io/transport/iframer.h"`; change constructor to `FujiBusTransport(Channel& channel, IFramer& framer)`; add `IFramer& _framer` member; remove `std::vector<std::uint8_t> _rxBuffer`
- [x] `repos/fujinet-nio/src/lib/fujibus_transport.cpp` -- delete `extractSlipFrame`; delete `_rxBuffer` usages; update `poll` to call `_framer.poll(_channel)`; update `wait_for_work` to remove `_rxBuffer.empty()` check; update `receive` and `receiveResponse` to call `_framer.nextPacket(frame)`; update `send` to call `_framer.sendPacket(_channel, serialized)` instead of `_channel.write`; remove `SlipByte`/`to_byte` usages and the `#include "fujinet/io/protocol/fuji_bus_packet.h"` if SLIP is the only reason it is included (keep if still needed for packet parsing)
- [x] `repos/fujinet-nio/src/lib/bootstrap.cpp` -- heap-allocate `SlipFramer`; inject into `FujiBusTransport` constructor; add `#include` for `slip_framer.h`
- [x] `repos/fujinet-nio/tests/test_fujibus_transport_framing.cpp` -- add `SlipFramer slipFramer;` local before each `FujiBusTransport` construction; update all 7 `FujiBusTransport t(ch)` to `FujiBusTransport t(ch, slipFramer)`; add `#include "fujinet/io/transport/slip_framer.h"`
- [x] `repos/fujinet-nio/tests/test_fujibus_transport_mapping.cpp` -- same `SlipFramer` injection for both test cases

**Acceptance Criteria:**
- Given `grep -r "0xC0\|SlipByte::End\|extractSlipFrame\|_rxBuffer" fujibus_transport.cpp fujibus_transport.h`, when run, then output is empty
- Given the full `fujibus-pty-debug` ctest suite, when run, then 282 (or more) tests pass, 0 fail
- Given `test_embed_core.cpp` file on disk, when compared to its state before this story, then it is byte-for-byte identical (unchanged)
- Given a `FujiBusTransport` constructed with a `SlipFramer`, when a valid SLIP-framed FujiBus packet is pushed and `poll` + `receive` called, then `IORequest` is populated correctly
- Given `FujiBusTransport` sending an `IOResponse`, when `send` is called, then bytes are written via the injected framer's `sendPacket`, not directly to the channel

## Spec Change Log

## Design Notes

`fuji_bus_packet.h` is still needed in `fujibus_transport.cpp` for `FujiBusPacket::fromSerialized`, `FujiBusPacket::serialize`, `WireDeviceId`, and `ByteBuffer` — only the `SlipByte` and `to_byte` uses are removed.

The `wait_for_work` simplification (dropping the `_rxBuffer.empty()` early-return) is intentional: the early-return was an optimization that required direct buffer access. Removing it means an extra channel-wait call when data is already buffered in `SlipFramer`. This is a known minor performance trade-off accepted to keep `IFramer` minimal.

Bootstrap heap-allocates `SlipFramer` because `FujiBusTransport` is also heap-allocated there (`new io::FujiBusTransport`). Both are owned by the core lifecycle; neither has a separate `delete` path today.

## Verification

**Commands:**
- `cd repos/fujinet-nio && ./build.sh -p fujibus-pty-debug` -- expected: compiles without error or warning
- `cd repos/fujinet-nio && ctest -V --test-dir build/fujibus-pty-debug --tests-regex fujinet-nio-tests` -- expected: all tests pass, 0 failures
- `grep -rn "0xC0\|SlipByte::End\|extractSlipFrame\|_rxBuffer" repos/fujinet-nio/src/lib/fujibus_transport.cpp repos/fujinet-nio/include/fujinet/io/transport/fujibus_transport.h` -- expected: no output
- `diff <(git show e0df4bb2:tests/test_embed_core.cpp) repos/fujinet-nio/tests/test_embed_core.cpp` -- expected: no differences
