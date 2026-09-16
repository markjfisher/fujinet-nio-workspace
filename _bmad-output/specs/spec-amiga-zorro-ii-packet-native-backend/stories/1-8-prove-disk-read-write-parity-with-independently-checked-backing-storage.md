---
title: '1-8 Prove disk read/write parity with independently checked backing storage'
type: feature
created: '2026-09-16'
status: done
review_loop_iteration: 0
baseline_commit: 8f2d4442aa960a419fd4e5dc60b83ed1d2a52eed
owner_baseline_commit: da5b6fa415da6f8bcbf941485f6d537cf56bc279
context:
  - '{project-root}/docs/agent-test-policy.md'
  - '{project-root}/_bmad-output/implementation-artifacts/epic-1-context.md'
---

<frozen-after-approval reason="approved Story 1.8; routine checkpoints disabled by execution-gates.md">

## Intent

**Problem:** DiskDevice tests call `handle(IORequest)` and never independently check disposable backing bytes after the same operations traverse serial SLIP versus native raw framing, so a matching transport bug can look like correct storage.

**Approach:** Drive production DiskDevice/DiskService through both framers against separate equivalent in-memory images; assert responses and resulting bytes against independently computed expectations, and distinguish service errors from transport effects with transmission/effect counts.

## Boundaries & Constraints

**Always:** Use independent disposable copies (no production media). Expected bytes come from seed image plus the applied operation, not from “serial equals native” alone. Neighbor sectors must stay unchanged. Count transmissions separately from write/flush effects; a unique per-attempt write marker is required so identical leftover sector contents cannot prove a write ran only once. Reuse Story 1.5 backend retry-containment evidence; do not weaken those tests. Prefer leaving production disk code unchanged.

**Ask First:** Any production change to DiskDevice, DiskService, `fake_fs.h`, broker/retry design, or expansion into file-list/clock parity.

**Never:** Create `native_serial_core_parity.h` (reserved for 1.7). Reopen 1.5/1.6 contract, broker/retry production, or catalogue/media lifecycle. Claim physical persistence from in-memory fixtures. Push or add Co-authored-by.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Read / write / flush parity | Twin disposable raw images; equivalent Mount, ReadSector, WriteSector, Flush via SLIP and native raw | Each path’s response and backing bytes match the independently computed image; neighbor sectors unchanged | N/A |
| Write protection | Same twins mounted read-only, then WriteSector | `StatusCode::InvalidRequest`; backing unchanged; write-effect count 0 | Service error, not a transport fault |
| Out of range | LBA or count beyond geometry | `InvalidRequest`; backing unchanged; write-effect count 0 | Service error, not a transport fault |
| Failed transfer before handle | Native `PacketIODouble` rejects/unavailable the request before `DiskDevice::handle` | Zero write effects; transmissions stay at the failed send; no service success | Transport outcome distinct from ReadOnly/OOR |
| Lost/ambiguous reply after write | Unique marker written; response send fails or `UnknownCompletion` | Exactly one write effect; one request transmission; marker present in backing | Do not treat identical leftover bytes as once-only proof |
| Replay exposure | Second attempt with a different unique marker after a completed write | Effect count increments only when a write executes; prior marker remains unless a second write ran | Counts, not content equality, expose unsafe replay |

</frozen-after-approval>

## Code Map

Workspace-relative. Production disk sources are read-only evidence unless a proven bug blocks these tests.

- `repos/fujinet-nio/tests/test_disk_device_protocol.cpp:1111-1317` -- existing Mount/Read/Write/Flush coverage via `IORequest` only; keep it; do not treat it as framing+backing parity.
- `repos/fujinet-nio/tests/fake_fs.h:14-226` -- `MemoryFileSystem` / `file_bytes` / `flush_count`; shared with 1.7, read-only. Put additive write-effect counting in the new header.
- `repos/fujinet-nio/tests/packet_io_double.h:18-193` -- 1.4 opaque double: `sendCalls`, `acceptedCount`, `setNextSendResult`, `UnknownCompletion`. Reuse; do not alter retry production.
- `repos/fujinet-nio/src/lib/fujibus_transport.cpp:38-134` -- `fromRaw` + `serializeRaw`; serial uses `SlipFramer` + `serialize()`, native uses `NativeFramer` + `PacketChannel`.
- `repos/fujinet-nio/tests/test_fujibus_transport_framing.cpp:299-318` and `tests/test_native_framer.cpp:438-467` -- request-mapping and native send-failure patterns to reuse, not file-list/clock work.
- `repos/fujinet-nio/include/fujinet/io/devices/disk_commands.h:8-21` -- Mount `0x01`, ReadSector `0x03`, WriteSector `0x04`, Flush `0x0E`.
- `repos/fujinet-nio/src/lib/disk_device.cpp:487-520,702-713` and `src/lib/disk/disk_service.cpp:433-566` -- RO maps to `InvalidRequest`; OOR is `DiskError::OutOfRange` → `InvalidRequest`; Flush `0x0E`. Exercise unchanged.
- `repos/fujinet-nio-driver/amiga/tests/test_fujinet_nio_packet_backend` and `test_fujinet_nio_client_retry` -- 1.5/1.6 retry-containment evidence; read only. Disk-path tests here only need transmission/effect distinction, not a new broker retry harness.
- Proposed `repos/fujinet-nio/tests/disk_serial_native_parity.h` -- twin fixtures, FujiBus encode/exchange for both framers, independent expected-image compare, neighbor-sector check, write-effect counter wrapping `IFile`/`IFileSystem`.
- Proposed `repos/fujinet-nio/tests/test_disk_serial_native_parity.cpp` -- every matrix row. `tests/CMakeLists.txt` GLOBs `test_*.cpp`; no `update_cmake_sources.py` unless a production `.cpp` is added.

## Tasks & Acceptance

**Execution:**
- [x] `repos/fujinet-nio/tests/disk_serial_native_parity.h` -- add disk-only twin-fixture, serial/native exchange, independent backing compare, and write-effect counter helpers.
- [x] `repos/fujinet-nio/tests/test_disk_serial_native_parity.cpp` -- cover every I/O matrix row through production DiskDevice after each framer; keep `test_disk_device_protocol.cpp` as existing IORequest coverage.
- [x] This story -- run the focused V-CXX command below and record results; do not run Amiberry or every POSIX preset.

**Acceptance Criteria:**
- Given independent disposable copies, when equivalent read/write/flush operations traverse both paths, then responses and backing bytes match independently computed values and surrounding sectors stay unchanged.
- Given write protection, invalid ranges, or injected failed/ambiguous delivery, when exercised, then service errors stay distinct from transport effects and transmission/effect counts expose any unsafe replay. No production media is used.

## Spec Change Log

## Design Notes

Build one raw request packet, then deliver `serialize()` through `SlipFramer` and `serializeRaw()` through `NativeFramer`/`PacketIODouble`. After `FujiBusTransport::receive`, call production `DiskDevice::handle` and `send` the response on the same path. Compute the expected image from the seed plus the intended sector write; compare each copy to that image. Wrap opens so each successful `IFile::write` increments an effect counter independent of leftover sector bytes. Pre-handle send faults must not call `handle`. In-memory fixtures do not prove physical persistence.

## Verification

**Commands:**
- `source /home/markf/dev/nio/fujinet-nio-workspace/scripts/env.sh && cd /home/markf/dev/nio/fujinet-nio-workspace/.kilo/worktrees/story-1-8-disk-parity/repos/fujinet-nio && ./build.sh -cp fujibus-pty-debug && ./build/fujibus-pty-debug/tests/fujinet-nio-tests --test-suite='Disk serial*' && ./build/fujibus-pty-debug/tests/fujinet-nio-tests --test-case='*Disk*'` -- expected: new parity suite and existing Disk* protocol cases pass. CTest `-R` cannot select doctest names (`fujinet-nio-tests` is the only C++ test).

**Manual checks:**
- Confirm no edits to `fake_fs.h`, file-list/clock tests, `native_serial_core_parity.h`, or broker/retry production. Confirm each matrix row has an executed test. Firmware `git diff --check` on touched files.

## Execution results

Clean configure required initializing nested `third_party/yaml-cpp` and `third_party/cjson` in this worktree’s firmware clone (not present after the submodule checkout). No production `.cpp` was added, so `update_cmake_sources.py` was not required; `tests/CMakeLists.txt` GLOBs `test_*.cpp`.

Focused run on 2026-09-16 (worktree firmware `da5b6fa4` plus new tests):

- `--test-suite='Disk serial*'`: **6/6 cases, 126/126 assertions**, 0 failed.
- `--test-case='*Disk*'`: **36/36 cases, 733/733 assertions**, 0 failed.

Matrix coverage that ran: read/write/flush parity (serial+native); write protection; out-of-range; failed request delivery; lost/ambiguous reply (`SendFailed` and `UnknownCompletion`); replay vs blocked second write. Firmware `git diff --check` passed. Touched files are only `tests/disk_serial_native_parity.h` and `tests/test_disk_serial_native_parity.cpp`.

## Suggested Review Order

**Independent expected image**

- Seed plus intended write is the expected image, not serial-equals-native
  [`disk_serial_native_parity.h:58`](../../../../repos/fujinet-nio/tests/disk_serial_native_parity.h#L58)

- Neighbor sectors are compared against the seed, not the written copy
  [`disk_serial_native_parity.h:73`](../../../../repos/fujinet-nio/tests/disk_serial_native_parity.h#L73)

**Write-effect counting**

- Each successful `IFile::write` increments independently of leftover sector bytes
  [`disk_serial_native_parity.h:90`](../../../../repos/fujinet-nio/tests/disk_serial_native_parity.h#L90)

**Serial vs native exchange**

- One raw request; SLIP `serialize()` vs native `serializeRaw()` then production `handle`
  [`disk_serial_native_parity.h:254`](../../../../repos/fujinet-nio/tests/disk_serial_native_parity.h#L254)

- Native request/reply fates expose transport vs service and transmission/effect counts
  [`disk_serial_native_parity.h:295`](../../../../repos/fujinet-nio/tests/disk_serial_native_parity.h#L295)

**Matrix tests**

- Happy-path read/write/flush on both framers against independent copies
  [`test_disk_serial_native_parity.cpp:12`](../../../../repos/fujinet-nio/tests/test_disk_serial_native_parity.cpp#L12)

- Service errors stay distinct from injected failed/ambiguous delivery
  [`test_disk_serial_native_parity.cpp:68`](../../../../repos/fujinet-nio/tests/test_disk_serial_native_parity.cpp#L68)

- Unique markers plus effect counts expose a second write versus a blocked replay
  [`test_disk_serial_native_parity.cpp:184`](../../../../repos/fujinet-nio/tests/test_disk_serial_native_parity.cpp#L184)
