---
title: 'Add NativeFramer and rename TransportKind::FujiBus → FujiBusSlip'
type: 'refactor'
created: '2026-08-29'
status: 'done'
baseline_commit: 'f09cc62918ad3c4c0ad0a8f817e2a638e4e6fc7f'
review_loop_iteration: 0
context: []
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** `TransportKind::FujiBus` implicitly meant "FujiBus over SLIP" before the IFramer split. Now that the framer is a separate concept, the name is misleading — and there is no `NativeFramer` implementation or build-profile entry for packet-native channels (Zorro, SPI, floppy/Pico).

**Approach:** Rename `TransportKind::FujiBus` → `FujiBusSlip` throughout; add `FujiBusNative`; implement `NativeFramer : IFramer` as a pass-through (packet-native channels deliver complete datagrams); wire it into a notional `FN_BUILD_ZORRO` build profile and a new bootstrap case. No `#ifdef` for framer selection.

## Boundaries & Constraints

**Always:**
- After this story, no source file may contain the identifier `TransportKind::FujiBus` — only `FujiBusSlip` or `FujiBusNative`
- Framer selection is by construction only — no `#ifdef` in any framer or bootstrap file to choose between SlipFramer and NativeFramer
- Full `fujibus-pty-debug` ctest suite must be green — zero regressions
- `NativeFramer` must have zero SLIP knowledge (`grep` for `0xC0\|SlipByte\|SLIP` in `native_framer.*` returns empty)

**Ask First:**
- Any change to the `IFramer` interface

**Never:**
- Touch `fujinet-nio-driver`, `fujinet-nio-lib`, or the Amiga serial backend (`fujinet_nio_serial_backend.c` / `fn_session.c`)
- Introduce real Zorro hardware integration — this is a build-profile stub only
- Add `#ifdef` anywhere to select which framer to use

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| NativeFramer single packet | Bytes pushed via `poll`, `nextPacket` called | Returns `true`, `outPacket` = all bytes received in that poll | — |
| NativeFramer no data | `poll` called on empty channel, then `nextPacket` | Returns `false` | — |
| NativeFramer send | `sendPacket(ch, packet)` called | Bytes written verbatim to channel | — |
| `FN_BUILD_ZORRO` profile | `current_build_profile()` compiled with `-DFN_BUILD_ZORRO` | Returns profile with `TransportKind::FujiBusNative` | — |
| Bootstrap FujiBusNative | Profile has `FujiBusNative`, `setup_transports` called | `NativeFramer` + `FujiBusTransport` wired; no SLIP framer allocated | — |

</frozen-after-approval>

## Code Map

- `repos/fujinet-nio/include/fujinet/build/profile.h:20-26` — `TransportKind` enum; rename `FujiBus` → `FujiBusSlip`, add `FujiBusNative`; update line-19 comment
- `repos/fujinet-nio/src/lib/build_profile.cpp:9,46,54,62,70,78,86,94,104` — 9 occurrences of `TransportKind::FujiBus`; rename all to `TransportKind::FujiBusSlip`; add `#elif defined(FN_BUILD_ZORRO)` entry with `FujiBusNative`
- `repos/fujinet-nio/src/lib/bootstrap.cpp:35` — `case TransportKind::FujiBus:` rename to `FujiBusSlip`; add new `case TransportKind::FujiBusNative:` wiring `NativeFramer`
- `repos/fujinet-nio/src/platform/posix/channel_factory.cpp:47` — `TransportKind::FujiBus` reference; rename to `FujiBusSlip`; decide whether `FujiBusNative` also needs a channel factory entry (it does if the Zorro channel is ever instantiated — add a comment stub)
- `repos/fujinet-nio/include/fujinet/io/transport/native_framer.h` — **new**; `NativeFramer : public IFramer` with `ByteBuffer _rxBuffer`
- `repos/fujinet-nio/src/lib/native_framer.cpp` — **new**; `poll` drains channel into `_rxBuffer`; `nextPacket` returns and clears `_rxBuffer` if non-empty; `sendPacket` writes verbatim
- `repos/fujinet-nio/tests/test_native_framer.cpp` — **new**; tests covering the I/O matrix above
- `repos/fujinet-nio/CMakeLists_posix.cmake` and `repos/fujinet-nio/src/CMakeLists.txt` — add `native_framer.cpp`; run `scripts/update_cmake_sources.py` after

## Tasks & Acceptance

**Execution:**
- [ ] `repos/fujinet-nio/include/fujinet/build/profile.h` -- rename `FujiBus` → `FujiBusSlip` in the enum; add `FujiBusNative`; update the comment on line 19 to remove the "(FujiBus is SLIP + FujiBus header framing)" parenthetical (that is no longer true in general)
- [ ] `repos/fujinet-nio/src/lib/build_profile.cpp` -- rename all 9 `TransportKind::FujiBus` → `TransportKind::FujiBusSlip`; add `#elif defined(FN_BUILD_ZORRO)` profile block with `FujiBusNative` and a notional `ChannelKind` (use `Pty` as a placeholder until Zorro has a real channel kind)
- [ ] `repos/fujinet-nio/src/lib/bootstrap.cpp` -- rename `case TransportKind::FujiBus:` → `FujiBusSlip`; add `case TransportKind::FujiBusNative:` that heap-allocates `NativeFramer` and injects into `FujiBusTransport`; add `#include "fujinet/io/transport/native_framer.h"`
- [ ] `repos/fujinet-nio/src/platform/posix/channel_factory.cpp` -- rename `TransportKind::FujiBus` → `FujiBusSlip`; add a comment-stub for `FujiBusNative` noting that Zorro channel selection belongs here when the channel kind is defined
- [ ] `repos/fujinet-nio/include/fujinet/io/transport/native_framer.h` -- new file; declare `NativeFramer : public IFramer` with `_rxBuffer`; include `iframer.h` and `channel.h`
- [ ] `repos/fujinet-nio/src/lib/native_framer.cpp` -- new file; implement `poll` (drain channel into `_rxBuffer`), `nextPacket` (return and clear `_rxBuffer` if non-empty; return `false` if empty), `sendPacket` (verbatim write to channel)
- [ ] `repos/fujinet-nio/tests/test_native_framer.cpp` -- new file; test the I/O matrix: single-packet round-trip, no-data returns false, send writes verbatim
- [ ] `repos/fujinet-nio/scripts/update_cmake_sources.py` -- run to regenerate CMake source lists after adding `native_framer.cpp`

**Acceptance Criteria:**
- Given `grep -rn "TransportKind::FujiBus[^SN]"` over all repo source files, when run, then output is empty (only `FujiBusSlip` and `FujiBusNative` exist)
- Given `grep -r "0xC0\|SlipByte\|SLIP"` over `native_framer.h` and `native_framer.cpp`, when run, then output is empty
- Given `grep -r "#ifdef"` over `native_framer.cpp`, `slip_framer.cpp`, `fujibus_transport.cpp`, when run, then output is empty (no framer-selection guards)
- Given the full `fujibus-pty-debug` ctest suite, when run, then all tests pass, 0 fail
- Given `NativeFramer` with bytes pushed via `poll`, when `nextPacket` called, then returns `true` and outPacket equals the pushed bytes
- Given `NativeFramer` with no bytes, when `nextPacket` called, then returns `false`

## Spec Change Log

## Design Notes

`NativeFramer::nextPacket` returns and clears the entire `_rxBuffer` as one packet. This is correct for packet-native channels (Zorro, SPI) where the channel itself delivers complete datagrams — there is no byte-level framing to extract. Contrast with `SlipFramer` which scans for `C0` delimiters.

The `FN_BUILD_ZORRO` profile uses `ChannelKind::Pty` as a placeholder — there is no `ChannelKind::Zorro` yet. This is intentional: the profile stubs the transport-level wiring without requiring a real channel implementation. When Zorro gets its own `ChannelKind`, only `build_profile.cpp` and `channel_factory.cpp` change; `NativeFramer` and `FujiBusTransport` are untouched.

`TransportKind::FujiBus` is renamed (not just aliased) because aliasing would defeat the purpose — callers would still write the misleading name.

## Verification

**Commands:**
- `cd repos/fujinet-nio && ./scripts/update_cmake_sources.py` -- expected: exits 0
- `cd repos/fujinet-nio && ./build.sh -p fujibus-pty-debug` -- expected: compiles without error or warning
- `cd repos/fujinet-nio && ctest -V --test-dir build/fujibus-pty-debug --tests-regex fujinet-nio-tests` -- expected: all tests pass including new NativeFramer suite
- `grep -rn "TransportKind::FujiBus[^SN]" repos/fujinet-nio/` -- expected: no output
- `grep -r "0xC0\|SlipByte\|SLIP" repos/fujinet-nio/include/fujinet/io/transport/native_framer.h repos/fujinet-nio/src/lib/native_framer.cpp` -- expected: no output
- `grep -r "#ifdef" repos/fujinet-nio/src/lib/native_framer.cpp repos/fujinet-nio/src/lib/slip_framer.cpp repos/fujinet-nio/src/lib/fujibus_transport.cpp` -- expected: no output
