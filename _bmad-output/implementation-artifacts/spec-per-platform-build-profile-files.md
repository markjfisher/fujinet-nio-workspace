---
title: 'Replace build_profile.cpp #ifdef chain with per-platform source files'
type: 'refactor'
created: '2026-08-29'
status: 'done'
baseline_commit: '1d483364b0cf7c89bf50dbd2fbf70a2ee9cf3ce7'
review_loop_iteration: 0
context: []
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** `src/lib/build_profile.cpp` selects the active `BuildProfile` via a 10-branch `#elif defined(FN_BUILD_*)` preprocessor chain. This buries platform decisions inside application code and means adding a new build target requires touching one monolithic file — the same problem the IFramer separation solved for transport framing.

**Approach:** Split `build_profile.cpp` into per-variant source files under `src/lib/build_profile/`. POSIX CMake presets select exactly one file via an `if/elseif` block in `CMakeLists_posix.cmake` — no `#ifdef` needed in those files. ESP32 variants are consolidated into `build_profile/esp32.cpp`, which retains `#ifdef` because the IDF build compiles all sources together. The `FN_BUILD_*` compile definitions are kept for legitimate feature gating elsewhere (`bootstrap.cpp`, `legacy_network_adapter.cpp`, `channel_factory.cpp`).

## Boundaries & Constraints

**Always:**
- All existing POSIX presets (`fujibus-pty-debug`, `fujibus-tcp-debug`, `fujibus-rs232-debug`, `atari-pty-debug`, `atari-netsio-debug`, `atari-fujibus-netsio-debug`, `lib-only`) must build and pass the full ctest suite
- `FN_BUILD_*` compile definitions are still passed to the compiler — they are used for feature gating in `bootstrap.cpp`, `legacy_network_adapter.cpp`, `channel_factory.cpp`; only their use in `build_profile.cpp` is eliminated
- The new per-variant POSIX files must contain zero `#ifdef` / `#elif` / `#if defined(...)` preprocessor conditionals
- `src/lib/build_profile.cpp` is deleted

**Ask First:**
- Any change to `BuildProfile`, `TransportKind`, `ChannelKind`, or `Machine` types in `profile.h`

**Never:**
- Touch `bootstrap.cpp`, `channel_factory.cpp`, or `legacy_network_adapter.cpp` feature-gate `#ifdef`s — those are correct and stay
- Change ESP32 platformio.ini or sdkconfig.defaults
- Alter any existing preset name or behavior

</frozen-after-approval>

## Code Map

- `repos/fujinet-nio/src/lib/build_profile.cpp` — **delete**; the 10-branch `#elif` chain being replaced; POSIX branches go to per-file, ESP32 branches go to `build_profile/esp32.cpp`
- `repos/fujinet-nio/src/lib/build_profile/` — **new directory**; one `.cpp` per POSIX variant + `esp32.cpp` + `default.cpp`
  - `fujibus_pty.cpp` — `FN_BUILD_FUJIBUS_PTY` branch; also used by `lib-only` preset
  - `fujibus_tcp.cpp` — `FN_BUILD_FUJIBUS_TCP` branch
  - `amiga_rs232.cpp` — `FN_BUILD_AMIGA_RS232` branch
  - `atari_pty.cpp` — `FN_BUILD_ATARI_PTY` branch
  - `atari_netsio.cpp` — `FN_BUILD_ATARI_NETSIO` branch
  - `atari_fujibus_netsio.cpp` — `FN_BUILD_ATARI_FUJIBUS_NETSIO` branch
  - `esp32.cpp` — consolidates `FN_BUILD_ATARI_SIO`, `FN_BUILD_ATARI_FUJIBUS_SIO`, `FN_BUILD_ESP32_USB_CDC`, `FN_BUILD_ESP32_FUJIBUS_GPIO` with `#ifdef` (IDF compiles all sources)
  - `default.cpp` — the current `#else` branch (POSIX PTY, no macro set)
- `repos/fujinet-nio/CMakeLists_posix.cmake:39-47,105-112` — options + compile_definitions for `FN_BUILD_*`; add an `if/elseif/else` block after the options to append the right `build_profile/*.cpp` to `FUJINET_NIO_SOURCES`; remove `src/lib/build_profile.cpp` from the source list (line ~161 in the existing file)
- `repos/fujinet-nio/src/CMakeLists.txt:19` — replace `lib/build_profile.cpp` with `lib/build_profile/esp32.cpp`
- `repos/fujinet-nio/include/fujinet/build/profile.h` — read-only reference; `current_build_profile()` is the function all per-variant files implement
- `repos/fujinet-nio/tests/test_build_profile.cpp` — existing tests use `#if defined(FN_BUILD_AMIGA_RS232)` and `#if defined(FN_BUILD_ZORRO)` — these remain valid since `FN_BUILD_*` compile definitions are still passed

## Tasks & Acceptance

**Execution:**
- [ ] Create `repos/fujinet-nio/src/lib/build_profile/fujibus_pty.cpp` — implement `current_build_profile()` returning `{Machine::Generic, TransportKind::FujiBusSlip, ChannelKind::Pty, "POSIX + FujiBus over PTY"}` with no `#ifdef`
- [ ] Create `repos/fujinet-nio/src/lib/build_profile/fujibus_tcp.cpp` — `TransportKind::FujiBusSlip, ChannelKind::TcpSocket, "POSIX + FujiBus over TCP serial"` — no `#ifdef`
- [ ] Create `repos/fujinet-nio/src/lib/build_profile/amiga_rs232.cpp` — `Machine::Generic, TransportKind::FujiBusSlip, ChannelKind::SerialPort, "POSIX + FujiBus over RS-232 (Amiga prototype)"` — no `#ifdef`
- [ ] Create `repos/fujinet-nio/src/lib/build_profile/atari_pty.cpp` — `Machine::Atari8Bit, TransportKind::SIO, ChannelKind::Pty, "Atari + SIO over PTY (POSIX)"` — no `#ifdef`
- [ ] Create `repos/fujinet-nio/src/lib/build_profile/atari_netsio.cpp` — `Machine::Atari8Bit, TransportKind::SIO, ChannelKind::UdpSocket, "Atari + SIO over NetSIO (UDP)"` — no `#ifdef`
- [ ] Create `repos/fujinet-nio/src/lib/build_profile/atari_fujibus_netsio.cpp` — `Machine::Atari8Bit, TransportKind::FujiBusSlip, ChannelKind::UdpSocket, "Atari + FujiBus over NetSIO (POSIX)"` — no `#ifdef`
- [ ] Create `repos/fujinet-nio/src/lib/build_profile/default.cpp` — `Machine::Generic, TransportKind::FujiBusSlip, ChannelKind::Pty, "POSIX + FujiBus over PTY (default)"` with a `// Default: ...` comment — no `#ifdef`
- [ ] Create `repos/fujinet-nio/src/lib/build_profile/esp32.cpp` — consolidate `FN_BUILD_ATARI_SIO`, `FN_BUILD_ATARI_FUJIBUS_SIO`, `FN_BUILD_ESP32_USB_CDC`, `FN_BUILD_ESP32_FUJIBUS_GPIO` branches from old `build_profile.cpp` verbatim, plus an `#else` fallback; retain `#ifdef` since IDF compiles all sources
- [ ] `repos/fujinet-nio/CMakeLists_posix.cmake` — add `if/elseif/else` block (after the option declarations) that appends exactly one `src/lib/build_profile/*.cpp` to `FUJINET_NIO_SOURCES`; remove `src/lib/build_profile.cpp` from the source list
- [ ] `repos/fujinet-nio/src/CMakeLists.txt` — replace `lib/build_profile.cpp` with `lib/build_profile/esp32.cpp` on line 19
- [ ] Delete `repos/fujinet-nio/src/lib/build_profile.cpp`

**Acceptance Criteria:**
- Given `grep -r "#ifdef\|#elif\|#if defined" repos/fujinet-nio/src/lib/build_profile/` excluding `esp32.cpp`, when run, then output is empty
- Given `fujibus-pty-debug` ctest suite, when run, then all tests pass, 0 fail
- Given each POSIX preset (`fujibus-pty-debug`, `fujibus-tcp-debug`, `fujibus-rs232-debug`, `atari-pty-debug`, `atari-netsio-debug`, `atari-fujibus-netsio-debug`, `lib-only`), when built with `./build.sh -p <preset>`, then each compiles without error
- Given `ls repos/fujinet-nio/src/lib/build_profile.cpp`, when run, then file does not exist

## Spec Change Log

## Design Notes

`esp32.cpp` retains `#ifdef` because PlatformIO/IDF builds compile all `lib/` sources into one component. Eliminating `#ifdef` from that file would require per-variant IDF component files, which is a different and larger change. The comment in `src/CMakeLists.txt:158` explicitly documents this build-system constraint.

The POSIX `CMakeLists_posix.cmake` already conditionally compiles sources (e.g., legacy transport). The new `if/elseif` block follows the same pattern — it is build-system configuration code where `if/elseif` on CMake variables is idiomatic, not a C++ preprocessor smell.

The commented-out `FN_BUILD_LINUX_PI_USB` profile at the top of old `build_profile.cpp` is not carried forward — it was already dead code.

## Verification

**Commands:**
- `grep -r "#ifdef\|#elif\|#if defined" repos/fujinet-nio/src/lib/build_profile/ --include="*.cpp" | grep -v esp32.cpp` — expected: no output
- `cd repos/fujinet-nio && ./build.sh -p fujibus-pty-debug && ctest -V --test-dir build/fujibus-pty-debug --tests-regex fujinet-nio-tests` — expected: all tests pass
- `cd repos/fujinet-nio && for p in fujibus-tcp-debug fujibus-rs232-debug atari-pty-debug atari-netsio-debug atari-fujibus-netsio-debug lib-only; do echo "=== $p ===" && ./build.sh -p $p || echo "FAILED: $p"; done` — expected: all presets compile without error
- `ls repos/fujinet-nio/src/lib/build_profile.cpp 2>&1` — expected: "No such file or directory"
