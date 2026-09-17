---
title: '1-7 Prove file-list and clock parity through the real core'
type: 'feature'
created: '2026-09-16'
status: 'in-progress'
baseline_commit: '8f2d4442aa960a419fd4e5dc60b83ed1d2a52eed'
owner_baseline_commit: 'da5b6fa415da6f8bcbf941485f6d537cf56bc279'
review_loop_iteration: 0
spec_checkpoint: false
done_checkpoint: false
context:
  - '{project-root}/docs/agent-test-policy.md'
  - '{project-root}/repos/fujinet-nio/AGENTS.md'
  - '{project-root}/_bmad-output/specs/spec-amiga-zorro-ii-packet-native-backend/SPEC.md'
  - '{project-root}/_bmad-output/specs/spec-amiga-zorro-ii-packet-native-backend/execution-gates.md'
---

<frozen-after-approval reason="approved Story 1.7; routine checkpoints disabled by execution-gates.md">

## Intent

**Problem:** FileDevice and ClockDevice tests talk to handlers via IORequest and never traverse serial SLIP vs native raw framing through production codecs, routing and handlers, so a framing change can alter ordinary file-list and clock replies undetected.

**Approach:** Drive two isolated core stacks—one SlipFramer + byte loopback, one NativeFramer + PacketIODouble—with production FujiBusTransport, IOService and real FileDevice/ClockDevice. Compare decoded statuses and payloads, and independently assert directory entries and controlled time.

## Boundaries & Constraints

**Always:** Use production codecs, FujiBusTransport, routing and the real FileDevice/ClockDevice. Isolate directory-cache effects with distinct URIs and equivalent MemoryFileSystem contents. Control time only at `fujinet::platform::unix_time_seconds`. Give PacketIODouble enough capacity for a list reply (default 64 is too small). Decode replies with production `FujiBusPacket` (`fromRaw` / `fromSerialized`). One stack must not seed the other.

**Ask First:** A production FileDevice/ClockDevice bug that must be fixed for these tests to pass, or any change to disk, broker/retry, native-packet-contract, or `tests/fake_fs.h`.

**Never:** Mock FileDevice/ClockDevice or return canned service payloads. Disk read/write parity (story 1.8). Sleeps. Sharing one core, FileDevice, cache URI, or time-format TZ mutation across configurations. Calling `set_unix_time_seconds` / SetTime in a way that changes the host clock. Edit `test_disk_device_protocol.cpp` or any 1.8 file.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| File-list happy path | Identical isolated trees, distinct URIs (`host-serial:/` vs `host-native:/`), ListDirectory through serial and native | Statuses and decoded payloads match; names/types/sizes independently equal the fixture (`alpha.txt`, `beta/`) | N/A |
| Clock happy path | Frozen POSIX unix time; GetTime and UTC ISO GetTimeFormat through both framings | Statuses and payloads match; unix seconds and ISO string equal the frozen value | N/A |
| Missing path | ListDirectory URI whose host exists but path does not | Both paths return existing FileDevice status (`IOError` when `listDirectory` fails) | Same status both framings |
| Unknown host | ListDirectory URI with unregistered filesystem name | Both paths `DeviceNotFound` | Same status both framings |
| Malformed file payload | Truncated ListDirectory body (bad version / missing maxPayload) | Both paths `InvalidRequest` | Same status both framings |
| Malformed clock payload | Truncated GetTimeFormat / trailing bytes (existing device cases) | Both paths `InvalidRequest` | Same status both framings |
| Unavailable time | Test override `unix_time_seconds() == 0`; GetTime | Both paths `NotReady`; no host clock change | Same status both framings |
| POSIX SetTime | Valid SetTime payload; do not apply host `clock_settime` | Both paths existing POSIX `IOError`; host unix time unchanged before/after | No canned Ok |

</frozen-after-approval>

## Code Map

Workspace-relative paths. Existing IORequest tests stay; this story adds framing-through-core coverage.

- `repos/fujinet-nio/tests/test_file_device_protocol.cpp:94-101,180-188,746-763` -- IORequest ListDirectory builders and relative-spec `DeviceNotFound`; reuse payload layout, do not treat as framing coverage.
- `repos/fujinet-nio/tests/test_clock_device.cpp:27-90` -- IORequest GetTimeFormat invalid/UTC cases; same handlers must now run through framers.
- `repos/fujinet-nio/tests/fake_fs.h:69-75,214-222` -- READ-ONLY. `MemoryFileSystem::create_file` / `createDirectory` for isolated trees. Additive helpers go in a new header.
- `repos/fujinet-nio/src/lib/file_device.cpp:35-73,336-415` -- READ-ONLY. Process-global `g_list_directory_cache` keyed by canonical URI (120s TTL). Distinct URIs prevent cross-config seeding. Missing dir → `IOError`; unresolved host → `DeviceNotFound`; bad prefix → `InvalidRequest`.
- `repos/fujinet-nio/src/lib/clock_device.cpp:90-128,130-199` -- READ-ONLY. GetTime uses `unix_time_seconds()`; `0` → `NotReady`. POSIX SetTime → `set_unix_time_seconds` false → `IOError`. GetTimeFormat malformed → `InvalidRequest`.
- `repos/fujinet-nio/src/platform/posix/time.cpp:15-37` -- POSIX `unix_time_seconds` / no-op `set_unix_time_seconds`. Add the smallest test override here (not in ClockDevice). Do not `clock_settime`.
- `repos/fujinet-nio/include/fujinet/platform/time.h:8-12` -- boundary used by ClockDevice; override stays POSIX-test-only so ESP32 `time.cpp` need not change.
- `repos/fujinet-nio/tests/packet_io_double.h:18-23,25-27,139-146` -- native RX enqueue / TX `takeSent`. Construct with capacity ≥ list reply (e.g. 2048), not default 64.
- `repos/fujinet-nio/include/fujinet/io/transport/native_framer.h` and `src/lib/native_framer.cpp:32-77,78-107` -- whole-packet native IFramer; bind PacketChannel.
- `repos/fujinet-nio/tests/test_fujibus_transport_framing.cpp:16-43` -- LoopbackChannel pattern for SLIP bytes; copy into the new helper, do not share process state with native.
- `repos/fujinet-nio/src/lib/fujibus_transport.cpp:38-98,100-134,137-167` -- raw codec mapping; `send` uses `serializeRaw`; decode replies with `receiveResponse` after a host-side framer poll, or parse TX bytes with `fromRaw`/`fromSerialized`.
- `repos/fujinet-nio/include/fujinet/core/core.h:20-51` and `src/lib/io_service.cpp:5-26` -- `FujinetCore::tick` → `serviceOnce` → handleRequest → `send`. Register real FileDevice/ClockDevice on `WireDeviceId::FileService` (0xFE) and `Clock` (0x45).
- `repos/fujinet-nio/include/fujinet/io/protocol/fuji_bus_packet.h:88-96` -- `serializeRaw` (native) vs `serialize` (SLIP).
- `repos/fujinet-nio/include/fujinet/io/devices/file_commands.h:6-12` -- ListDirectory `0x02`.
- `repos/fujinet-nio/include/fujinet/io/devices/clock_commands.h:9-16` -- GetTime `0x01`, SetTime `0x02`, GetTimeFormat `0x03`.
- `repos/fujinet-nio/tests/CMakeLists.txt:4-11` -- `test_*.cpp` is globbed; a new parity test file is picked up. Run `scripts/update_cmake_sources.py` only if a production `.cpp` is added.
- `repos/fujinet-nio/tests/test_disk_device_protocol.cpp` -- READ-ONLY (story 1.8).

New files:

- `repos/fujinet-nio/tests/native_serial_core_parity.h` -- two-stack helper: isolated core+storage+devices; serial vs native exchange of one FujiBus command; no disk helpers.
- `repos/fujinet-nio/tests/test_file_clock_core_parity.cpp` -- matrix cases. Do not put disk tests here.

## Tasks & Acceptance

**Execution:**
- [x] `repos/fujinet-nio/src/platform/posix/time.cpp` -- add a POSIX-only test freeze/unavailable override for `unix_time_seconds` (RAII in the helper). Leave `set_unix_time_seconds` as the existing no-op. -- Controlled time without touching ClockDevice or the host clock.
- [x] `repos/fujinet-nio/tests/native_serial_core_parity.h` -- two independent stacks; serial Loopback+SlipFramer vs native PacketChannel+PacketIODouble+NativeFramer; production transport/core; distinct FS names; capacity for list replies; decode via production packets. -- Shared fixture without seeding cache or disk APIs.
- [x] `repos/fujinet-nio/tests/test_file_clock_core_parity.cpp` -- implement every I/O matrix row; assert serial/native status+payload equality and independent directory/time expectations. -- Closes the framing-through-core gap.
- [x] Existing `test_file_device_protocol.cpp` / `test_clock_device.cpp` -- keep IORequest coverage; do not replace it. Optional one-line comments pointing at the new parity file. -- Avoid duplicate device-only cases as the parity proof.

**Acceptance Criteria:**
- Given identical isolated directory contents and controlled time, when file-list/clock requests traverse serial and native framing through the core, then decoded replies and statuses match AND expected directory entries/time are independently asserted.
- Given missing paths, malformed service payloads or unavailable time, when handled, then both paths retain existing service error behavior AND neither test changes the host clock or merely returns canned service responses.

## Spec Change Log

## Design Notes

Build each stack as: `FujinetCore` + `StorageManager.registerFileSystem(MemoryFileSystem)` + `FileDevice(core.storageManager())` + `ClockDevice` + `FujiBusTransport` + `core.addTransport` + `core.tick()`. Do not call `device.handle` in the parity cases.

Native request: `FujiBusPacket::serializeRaw()` → `PacketIODouble::enqueue` → tick → `takeSent` → `fromRaw`. Serial request: `serialize()` (SLIP) → LoopbackChannel push → tick → SLIP-decode TX → `fromRaw` on the inner packet (or `fromSerialized` on the frame). Compare `param[0]` status and payload bytes.

Cache isolation example: both trees contain `/alpha.txt` and `/beta/`; URIs `host-serial:/` vs `host-native:/`. Do not list the same canonical URI on both stacks.

Time: freeze to a known unix second (e.g. `1700000000`) for happy-path equality; set `0` for NotReady. Restore the override after each case. Capture `std::time(nullptr)` around SetTime to prove the host clock did not move because of the test (POSIX already refuses SetTime).

Do not `sleep`. Do not share `g_list_directory_cache` keys.

## Verification

**Commands:**
- `source /home/markf/dev/nio/fujinet-nio-workspace/scripts/env.sh && cd /home/markf/dev/nio/fujinet-nio-workspace/repos/fujinet-nio && ./build.sh -cp fujibus-pty-debug` -- expected: POSIX debug preset builds, including globbed `tests/test_file_clock_core_parity.cpp`.
- `./build/fujibus-pty-debug/tests/fujinet-nio-tests --test-suite=file_clock_core_parity` -- expected: 8/8 matrix cases pass (CTest `-R file_clock_core_parity` does not match; the registered test name is `fujinet-nio-tests`).
- `ctest --test-dir build/fujibus-pty-debug -R '^fujinet-nio-tests$' --output-on-failure` -- expected: full C++ unit binary passes, including existing FileDevice/ClockDevice IORequest cases.

**Manual checks:**
- Confirm parity tests construct `FileDevice`/`ClockDevice`, not test doubles, and that serial and native stacks use different MemoryFileSystem names.
- Confirm no `sleep`, no `clock_settime`, and no edits to `fake_fs.h`, disk tests, or production file/clock handlers unless Ask First fired.

**Results (2026-09-16):** `file_clock_core_parity` 8 cases / 86 assertions passed. `ctest -R '^fujinet-nio-tests$'` 1/1 passed. Production `file_device.cpp` / `clock_device.cpp` / `fake_fs.h` / disk tests unchanged. `scripts/update_cmake_sources.py` not required (no new production `.cpp`). Combined master land at firmware `337f5b3e` re-ran `file_clock_core_parity` (8/8), `Disk serial*` (6/6), and `ctest -R '^fujinet-nio-tests$'` (1/1).

## Suggested Review Order

**Two-stack framing through real handlers**

- Entry point: serial SlipFramer vs native PacketIODouble, each with its own core and FileDevice/ClockDevice.
  [`native_serial_core_parity.h:170`](../../../../repos/fujinet-nio/tests/native_serial_core_parity.h#L170)

- One FujiBus command is framed, ticked through IOService, and decoded with production packets.
  [`native_serial_core_parity.h:208`](../../../../repos/fujinet-nio/tests/native_serial_core_parity.h#L208)

**Controlled time without touching ClockDevice or the host clock**

- POSIX `unix_time_seconds` freeze/unavailable override; `set_unix_time_seconds` stays a no-op.
  [`time.cpp:20`](../../../../repos/fujinet-nio/src/platform/posix/time.cpp#L20)

- RAII restores the override so one configuration cannot leak time into another.
  [`native_serial_core_parity.h:47`](../../../../repos/fujinet-nio/tests/native_serial_core_parity.h#L47)

**Matrix coverage**

- Distinct `host-serial` / `host-native` URIs, independent name/type/size checks, and error-path parity.
  [`test_file_clock_core_parity.cpp:49`](../../../../repos/fujinet-nio/tests/test_file_clock_core_parity.cpp#L49)


## Review Findings — 2026-09-17

Review of the delivered story against its requirements; implementation is unchanged. These findings reopen acceptance pending correction.

- [ ] [Review][Patch] Keep the test clock override out of production builds — src/platform/posix/time.cpp:16–29 unconditionally compiles the freeze state, setter and runtime branch into the production POSIX library. Confirmed both symbols in the production fujinet-nio executable with nm -C. The story promises a POSIX-test-only override; isolate it at the test build/link boundary.

Verification: fresh `./build.sh -cp fujibus-pty-debug` passed (366 C++ cases, 7186 assertions; 23 Python tests); native Amiga driver `make test` passed. Passing existing tests does not close the gaps above.
