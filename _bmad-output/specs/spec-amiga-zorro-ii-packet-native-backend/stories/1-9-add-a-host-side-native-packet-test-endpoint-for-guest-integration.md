---
title: '1-9 Add a host-side native packet test endpoint for guest integration'
type: 'feature'
created: '2026-09-16'
status: 'done'
review_loop_iteration: 0
review_fix_baseline_commit: 31711adf21071c3f98969fbd1dbd36814d0f4693
review_fix_owner_baseline_commit: c55790c57f1e5954d51473817c592b8ad3c6b81f
review_fix_owner_commit: f9a430cebee652cf7308100b20a96f0ce2e0b016
baseline_commit: '06986c940adab46ac5977b59409a802e33d6ade5'
owner_baseline_commit: '337f5b3e00f79bbd0aa2e74c67095abeb906b3e1'
spec_checkpoint: false
done_checkpoint: false
context:
  - '{project-root}/docs/agent-test-policy.md'
  - '{project-root}/_bmad-output/implementation-artifacts/epic-1-context.md'
  - '{project-root}/repos/fujinet-nio/docs/native-packet-contract.md'
---

<frozen-after-approval reason="approved Story 1.9; routine checkpoints disabled by execution-gates.md">

## Intent

**Problem:** Stories 1.7–1.8 prove in-process native/serial parity, but there is no host endpoint an Amiga test backend can reach. The POSIX Zorro profile is a byte PTY stub that fails closed, and Amiberry’s TCP path is SLIP serial.

**Approach:** After checking guest facilities, use a temporary shared-directory record adapter (not sockets, not SLIP TCP, not the PTY Zorro placeholder). Implement the host runner plus an independent host client that exchange complete raw FujiBus records through the production core.

## Boundaries & Constraints

**Always:** Records are complete raw `serializeRaw()` packets; file size is the boundary. At most one exchange is in flight. Identify as `native-test`, never Zorro or SLIP. Real ClockDevice/FileDevice handlers; no canned replies. Timeouts and cleanup are explicit. Preserve FujiBus fields and the 1.6 packet contract.

**Ask First:** Switching to TCP/bsdsocket; implementing the Amiga guest half (1.10); any serial fallback or physical ABI; production service/retry changes.

**Never:** Advertise `FN_BUILD_ZORRO` / PTY placeholder as this endpoint. Reuse `fujibus-tcp` / `SlipFramer` as the native path. Add a correlation field, mailbox, or bridge protocol. Open a serial device or install `FujiBusSlip` when native-test is selected. Implement `fn_packet_io_t` or the guest broker.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Happy exchange | Independent host client writes one raw clock or file-list request record | Production handler runs; one raw response record; decoded status/payload independently asserted | N/A |
| Identity | Inspect runner banner, profile name, and directory `IDENTITY` | Exact token `native-test`; not Zorro, SLIP, or PTY placeholder | Mislabel fails the story |
| Disconnect | Directory removed or unusable mid-poll | `Unavailable`; no SLIP/serial open | Distinct from service errors |
| Stale record | Leftover `to-host.pkt` / `to-guest.pkt` from a prior session | Startup/reset discards them; they never complete a later request | No stale misattribution |
| Oversized | Record larger than adapter capacity | `Oversized`; no prefix delivered; file consumed/removed | Not treated as a valid packet |
| Cleanup | Runner shutdown after an exchange | Packet files gone or inert; no serial/TCP listen left behind | Process exit is enough if files are deleted |
| No fallback | PTY/TCP/serial config present in the environment | Native-test path never constructs `SlipFramer` or a byte serial channel | Fail closed, no failover |

</frozen-after-approval>

## Code Map

Workspace-relative. Guest broker/Amiberry injection is 1.10 read-only context.

- `repos/fujinet-nio/src/lib/bootstrap.cpp:43-52` -- `FujiBusNative` requires `channel.packet_io()` with nonzero capacity; reuse this seam. Do not change serial `FujiBusSlip`.
- `repos/fujinet-nio/src/lib/build_profile/zorro.cpp:7-11` and `docs/native-packet-contract.md:47-48` -- PTY Zorro stub; fail-closed evidence only. Do not select `FN_BUILD_ZORRO` for this runner.
- `repos/fujinet-nio/src/platform/posix/channel_factory.cpp:25-37` and `src/lib/build_profile/fujibus_tcp.cpp` -- SLIP byte channels; read-only. Do not route native-test through them.
- `repos/fujinet-nio/include/fujinet/io/core/packet_io.h:8-51` and `include/fujinet/io/core/channel.h:19-21` -- implement `IPacketIO` + `packet_io()`; byte `read`/`write` must not invent boundaries (count accidental use like `tests/packet_io_double.h:184-193`).
- `repos/fujinet-nio/src/app/main_posix.cpp:97-287` -- embed pattern: `FujinetCore`, host FS, `setup_transports`, tick. Copy the device-registration subset needed for clock/file; do not reuse `current_build_profile()` if that yields SLIP or Zorro-PTY.
- `repos/fujinet-nio/tests/native_serial_core_parity.h:186-233` -- proven in-process native stack; 1.9 replaces `PacketIODouble` with the directory adapter, not a second FujiBus codec.
- `repos/fujinet-nio/tests/test_file_clock_core_parity.cpp` -- reuse clock/file-list request builders and independent assertions; do not reopen 1.7/1.8 disk parity files.
- `integration-tests/amiberry/conftest.py:353-370,800-807` and `configs/amiga/workbenches.yaml:207-221` -- serial TCP + optional `filesystem2` host-dir mounts. Document that 1.10 can mount this record directory writable; do not change the Amiberry harness in 1.9.
- `repos/fujinet-nio-driver/amiga/nio.device/fujinet_nio_packet_backend.h` -- 1.10 consumer; read-only. No guest sockets exist today (`bsdsocket` unused in the driver).
- Proposed `repos/fujinet-nio/tests/directory_packet_io.cpp` (header beside it) -- core-side adapter: receive `to-host.pkt`, send `to-guest.pkt`; client-side helper inverts the names. Atomic write via `*.tmp` + rename. Capacity immutable. Startup/`reset()` deletes leftover pkt files.
- Proposed `repos/fujinet-nio/tests/native_test_runner.cpp` -- host endpoint binary `fujinet-nio-native-test`: writes `IDENTITY`=`native-test`, constructs `FujiBusNative` + directory channel, ticks the real core. Directory from argv or `FN_NATIVE_TEST_DIR`.
- Proposed `repos/fujinet-nio/tests/native_test_records.h` and `tests/test_native_test_endpoint.cpp` -- independent host client + every matrix row. `tests/CMakeLists.txt` GLOBs `test_*.cpp`.
- `repos/fujinet-nio/tests/CMakeLists.txt` -- build `fujinet-nio-native-test` and compile `directory_packet_io.cpp` only into that runner and `fujinet-nio-tests`. Do not add the adapter to `FUJINET_NIO_SOURCES`. Keep existing POSIX presets on SLIP.
- `repos/fujinet-nio/docs/native-packet-contract.md` -- short harness subsection: shared-directory records are a test facility, not a Zorro/bridge ABI.

## Tasks & Acceptance

**Execution:**
- [x] `repos/fujinet-nio/tests/directory_packet_io.cpp` -- bounded directory `IPacketIO` with atomic records, stale discard, oversized/unavailable/backpressure outcomes.
- [x] `repos/fujinet-nio/tests/native_test_runner.cpp` -- host endpoint binary with `native-test` identity and production core; no SLIP/serial/Zorro-PTY channel.
- [x] `repos/fujinet-nio/tests/test_native_test_endpoint.cpp` -- independent host client covers every matrix row, including process-level identity if the runner is spawned.
- [x] `repos/fujinet-nio/docs/native-packet-contract.md` and this story -- record the selected facility (shared-directory) and why sockets/SLIP/PTY were rejected.
- [x] This story -- run the V-CXX commands below; do not run Amiberry or every POSIX preset.

**Acceptance Criteria:**
- Given the selected test-only directory mechanism and an independent host client, when records are exchanged, then real core handlers process raw packets with bounded complete-record delivery, and disconnect, stale record, oversized input and cleanup are tested without the guest implementation.
- Given runner startup, when configuration is inspected, then it identifies itself as native-test, not real Zorro or SLIP, and no automatic serial fallback or new physical ABI is introduced.

## Spec Change Log

- 2026-09-16: Implemented the shared-directory harness (`native-test`) under `tests/`. Sockets were rejected because the guest broker has no `bsdsocket` client; SLIP TCP and the PTY Zorro stub have the wrong semantics. The adapter and runner live in `fujinet::native_test` and link only into `fujinet-nio-tests` and `fujinet-nio-native-test`. `scripts/update_cmake_sources.py` was not run: it overwrites `CMakeLists_posix.cmake` from a stale template.

## Design Notes

Guest-facility check (SPEC open question at 1.9): Amiberry already bridges SLIP over TCP and can mount a host directory via `filesystem2`. The resident broker has DOS I/O and no `bsdsocket` client. Therefore the harness is a **shared-directory record adapter**. TCP sockets would force 1.10 to add a guest network stack; SLIP TCP and the PTY Zorro stub are the wrong semantics.

Protocol (harness only): one directory; file `IDENTITY` contains `native-test\n`; at most one `to-host.pkt` and one `to-guest.pkt`. A complete record is the whole file after `rename` from `*.tmp`. Capacity is the adapter constructor argument (≤ 65535). Polling is nonblocking; tests use a deadline, not `sleep` as the pass condition. 1.10 may mount the same directory writable; that is not required to accept 1.9.

## Verification

**Commands:**
- `source /home/markf/dev/nio/fujinet-nio-workspace/scripts/env.sh && cd /home/markf/dev/nio/fujinet-nio-workspace/repos/fujinet-nio && ./build.sh -cp fujibus-pty-debug && ./build/fujibus-pty-debug/tests/fujinet-nio-tests --test-suite=native_test_endpoint` -- expected: every matrix row passes. CTest registered name is `fujinet-nio-tests`.
- `ctest --test-dir build/fujibus-pty-debug -R '^fujinet-nio-tests$' --output-on-failure` -- expected: 1/1, including existing 1.7/1.8 suites.

**Manual checks:**
- Runner `--help` or startup log contains `native-test` and does not claim Zorro or SLIP.
- `git diff` does not edit `zorro.cpp`, `fujibus_tcp.cpp`, `fake_fs.h`, or Amiga guest sources.

**Results (2026-09-16):** `--test-suite=native_test_endpoint` 8/8 passed. `ctest -R '^fujinet-nio-tests$'` 1/1 passed (366 cases in the binary).

## Suggested Review Order

**Selected facility**

- Shared-directory harness, not SLIP TCP or the PTY Zorro stub
  [`native-packet-contract.md:191`](../../../../repos/fujinet-nio/docs/native-packet-contract.md#L191)

**Record adapter**

- File size is the boundary; receive never copies a prefix on failure
  [`directory_packet_io.cpp:119`](../../../../repos/fujinet-nio/tests/directory_packet_io.cpp#L119)

- Occupied dest is Backpressure; publish is `*.tmp` then rename
  [`directory_packet_io.cpp:182`](../../../../repos/fujinet-nio/tests/directory_packet_io.cpp#L182)

**Host runner**

- Local `FujiBusNative` profile; never `current_build_profile()` or the channel factory
  [`native_test_runner.cpp:97`](../../../../repos/fujinet-nio/tests/native_test_runner.cpp#L97)

- IDENTITY is written only after transports are up
  [`native_test_runner.cpp:167`](../../../../repos/fujinet-nio/tests/native_test_runner.cpp#L167)

**Independent client and matrix**

- Host client inverts record names and talks to the real core
  [`native_test_records.h:81`](../../../../repos/fujinet-nio/tests/native_test_records.h#L81)

- Process-level identity, listing payload, stale discard, oversized, cleanup, no fallback
  [`test_native_test_endpoint.cpp:89`](../../../../repos/fujinet-nio/tests/test_native_test_endpoint.cpp#L89)

## Review Findings — 2026-09-17

Findings from the initial review of the delivered story. The checked items below were subsequently corrected and verified; the correction evidence follows.

- [x] [Review][Patch] Contain unresolved client exchanges across timeout — tests/native_test_records.h:87–118 has no outstanding-exchange state; wait_record timeout permits another send as soon as the host consumed the prior request file. A standalone adapter probe confirmed a second request is accepted before the first reply, and a late old reply is accepted after local reset/new send. Add client ownership/containment and delayed-response coverage; local file cleanup alone is not remote quiescence.
- [x] [Review][Patch] Require fresh runner readiness on directory reuse — tests/native_test_records.h:239–247 accepts any existing IDENTITY before checking the child, while tests/native_test_runner.cpp:181 leaves IDENTITY after shutdown. Restart can report ready before constructor cleanup, which can discard a newly submitted request. Establish readiness from the current launch and test restart in the same directory.

Verification: fresh `./build.sh -cp fujibus-pty-debug` passed (366 C++ cases, 7186 assertions; 23 Python tests); native Amiga driver `make test` passed. Passing existing tests does not close the gaps above.


### Review correction evidence — 2026-09-17

- The host client retains ownership after the request file is consumed; a second
  send reports `Backpressure`. Timeout or abandoned receive latches lifetime
  quarantine (`UnknownCompletion`) for sends and receives, including after
  local adapter reset. Clients are noncopyable. No remote recovery is inferred.
- Launch removes old readiness before fork; readiness requires the exact token
  and a live child from this launch. Runner signal handlers precede publication,
  and orderly shutdown removes `IDENTITY`. Reuse requires exclusive directory
  ownership and termination/reaping of the previous runner.
- Red: added delayed-peer/reset, stale-identity/failed-exec and same-directory
  restart regressions; unpatched endpoint suite failed 3/11 cases (9 assertions).
- Green: `source scripts/env.sh && cd repos/fujinet-nio && ./build.sh -cp fujibus-pty-debug`
  passed all three registered tests, including Python. Focused
  `./build/fujibus-pty-debug/tests/fujinet-nio-tests --test-suite=native_test_endpoint`
  passed 11/11 cases, 154 assertions; the specified focused CTest passed 1/1.
- Limits: a fresh client against a still-running uncertain peer is unsupported;
  local file cleanup never proves remote quiescence. No guest, serial, service,
  packet ABI, or production retry changes were made for these corrections.

### Combined corrective acceptance — 2026-09-17

The corrective changes passed the combined review. Firmware revision: `f9a430cebee652cf7308100b20a96f0ce2e0b016`. All review findings for this story are closed.

Final verification after all corrections (source workspace `scripts/env.sh` first):

- `cmake --build repos/fujinet-nio/build/fujibus-pty-debug --target fujinet-nio-tests -j4` — passed; the target also builds the production application inspected by the isolation check.
- `repos/fujinet-nio/build/fujibus-pty-debug/tests/fujinet-nio-tests --test-suite=native_test_endpoint` — 15 cases / 184 assertions passed.
- `ctest --test-dir repos/fujinet-nio/build/fujibus-pty-debug -V` — 3/3 passed: 374 C++ cases / 7695 assertions, production clock isolation, and 23 Python tests.
- Workspace and firmware `git diff --check` — passed. No library, Amiga driver, application CLI, or production disk-handler changes.

Combined review also added regressions for the separate in-process exchange deadline, accepted-request receive failure, incorrect identity from a live child, and failed startup record cleanup. The runner checks the adapter initialization result before publishing identity; it does not retry failed cleanup. The client exposes local cleanup without exposing raw send/receive around its ownership guard. A valid delayed reply is used in the timeout test.

## Suggested Review Order — corrective changes

- Retain exchange ownership and quarantine after uncertainty.
  [native_test_records.h:91](../../../../repos/fujinet-nio/tests/native_test_records.h#L91)

- Publish readiness only after successful startup cleanup.
  [native_test_runner.cpp:143](../../../../repos/fujinet-nio/tests/native_test_runner.cpp#L143)

- Exercise timeout, late reply, receive failure and launch lifecycle.
  [test_native_test_endpoint.cpp:392](../../../../repos/fujinet-nio/tests/test_native_test_endpoint.cpp#L392)
