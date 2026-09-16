---
title: '1-10 Build an Amiga native-test broker binary using the host endpoint'
type: 'feature'
created: '2026-09-16'
status: 'done'
review_loop_iteration: 0
baseline_commit: '9f18e8bc7a272b22600d28cd58dfd342612e03c4'
owner_baseline_commit: 'e6f9686797f6bae256342d362795c4b3fc5b3da1'
spec_checkpoint: false
done_checkpoint: false
context:
  - '{project-root}/docs/agent-test-policy.md'
  - '{project-root}/docs/amiga/cli-stack-and-iorequest.md'
  - '{project-root}/_bmad-output/implementation-artifacts/epic-1-context.md'
  - '{project-root}/repos/fujinet-nio/docs/native-packet-contract.md'
---

<frozen-after-approval reason="approved Story 1.10; routine checkpoints disabled by execution-gates.md">

## Intent

**Problem:** Story 1.9 gives a host-only shared-directory endpoint. No Amiga broker binary can reach it, so guest callers still need serial/SLIP.

**Approach:** Add a separate native-test broker that implements `fn_packet_io_t` over the 1.9 directory contract, links through the existing packet guard and EXCHANGE ABI, and omit serial framing objects. Prove it with host backend tests plus one Amiberry raw-exchange probe.

## Boundaries & Constraints

**Always:** Guest is Client-role (`to-host.pkt` send, `to-guest.pkt` receive). File size is the record boundary; `*.tmp` then rename; at most one exchange in flight. `IDENTITY` must already be `native-test\n` before `backend_open` succeeds. Preserve public `FUJINET_NIO_DEVICE_NAME` / `CMD_EXCHANGE` / request layout and 1.5 ownership (one completion, no stale reply). Serial controls return `FN_ERR_UNSUPPORTED`. Test artifact `$VER` / filename must say `native-test`.

**Ask First:** Guest TCP/`bsdsocket`; changing 1.9 record names; SET_BAUD fallback; exchange-tool option planning (1.11); production retry/service changes; claiming Zorro/hardware from the emulator.

**Never:** Link `fujinet_nio_serial_backend.o`, `fn_session.o`, or `fn_slip.o` into the native-test device. Open `serial.device` / `timer.device` for packet I/O. Reuse `nio-broker-isolated` (it asserts serial-busy). Change the production serial `fujinet-nio.device` object set. Invent a mailbox, correlation field, or bridge ABI. WaitIO an OpenDevice-only IORequest.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Happy EXCHANGE | Client writes one raw clock request; host runner ticks | One raw clock response; decoded status independently asserted | N/A |
| Identity | Missing or wrong `IDENTITY` | `backend_open` fails; no pkt files written | Distinct from transport timeout |
| Unsupported control | SET_BAUD / SET_SERIAL / GET_* | `FN_ERR_UNSUPPORTED`; no serial open | No fallback |
| Stale record | Leftover `to-guest.pkt` at open/reset | Discarded; cannot complete a later EXCHANGE | No stale misattribution |
| Backpressure | `to-host.pkt` already present | Send rejected; request not overwritten | Not treated as COMPLETE |
| Oversized | Record larger than adapter capacity | Oversized / REJECTED; no prefix delivered | File consumed or removed |
| Missing peer | Directory gone or unusable | Unavailable / TRANSPORT; no SLIP/serial | Distinct from service errors |
| Teardown | CloseDevice after an exchange | Leftover pkt/tmp gone or inert; no serial listen | Process/device exit is enough |

</frozen-after-approval>

## Code Map

Workspace-relative. 1.9 host runner is read-only unless temps fail on `filesystem2`.

- `repos/fujinet-nio/tests/directory_packet_io.h:15-24` and `directory_packet_io.cpp:80-92,197-241` -- mirror Client paths, tmp+rename, Backpressure, capacity 65535. Host writes `IDENTITY` (`native_test_runner.cpp:161-170`).
- `repos/fujinet-nio-driver/amiga/include/fujinet_nio_backend.h:24-38` -- export these `backend_*` symbols from the new object; serial `fujinet_nio_serial_backend.c` is the production link only.
- `repos/fujinet-nio-driver/amiga/nio.device/fujinet_nio_packet_backend.h:17-56` -- implement `fn_packet_io_t`; wrap EXCHANGE with `fn_packet_backend_exchange`. Quiesce = discard leftover records and prove both directions empty (file mailbox proof).
- `repos/fujinet-nio-driver/amiga/nio.device/fujinet_nio_device.c:317-324,216-249` -- production `device_init` binds linked `backend_*`; NULL/unsupported control hooks already return `FN_ERR_UNSUPPORTED`. Prefer Makefile-only swap; do not add a second `#ifdef` unless symbols cannot match.
- `repos/fujinet-nio-driver/amiga/Makefile:20-24,72-73` -- add `NIO_NATIVE_TEST_OBJECTS` + `$(BUILD_DIR)/fujinet-nio-native-test.device`. Drop serial/session/slip; add packet backend + directory adapter. Keep `NIO_DEVICE` serial.
- `repos/fujinet-nio-driver/amiga/tests/test_fujinet_nio_packet_backend.c:273-316` -- pattern: guard + `fujinet_nio_native_test_set_backend(..., NULL, NULL, NULL, NULL)`. New sibling `test_fujinet_nio_directory_backend.c` + `amiga/tests/Makefile` target.
- `repos/fujinet-nio-driver/amiga/include/fujinet_nio_device.h:6-63` -- read-only public ABI.
- `repos/fujinet-nio-driver/amiga/tests/test_fujinet_nio_device.c` -- must still pass (V-BROKER).
- `integration-tests/amiberry/conftest.py:353-370,777-878,960-961` -- TCP NIO + serial `fujinet-nio.device` today. Add a `nio_native_test` case flag: build/run `fujinet-nio-native-test --dir <record>`, `filesystem2` mount as `NATIVE:`, inject `fujinet-nio-native-test.device` as `DEVS:fujinet-nio.device`, do not start `fujibus-tcp`.
- `configs/amiga/workbenches.yaml:7-12` and `tools/build/nio_build/amiga_config.py:214-226` -- `filesystem2=rw` pattern. Default volume `NATIVE:`; override via `GetVar("FN_NATIVE_TEST_DIR")`.
- `integration-tests/amiberry/test_nio_broker.py:1-20` and `startup/nio-broker-isolated.sequence` -- serial-busy assertions; do not reuse. New sequence + pytest node + tiny probe under `amiga/tools/` (STACK per `docs/amiga/cli-stack-and-iorequest.md`).
- Proposed `repos/fujinet-nio-driver/amiga/nio.device/fujinet_nio_directory_backend.c` (header beside it) -- POSIX `#else` for host tests; Amiga `dos.library` in the m68k device. Directory from `NATIVE:` / `FN_NATIVE_TEST_DIR`.

## Tasks & Acceptance

**Execution:**
- [x] `repos/fujinet-nio-driver/amiga/nio.device/fujinet_nio_directory_backend.c` -- Client-role directory `fn_packet_io_t` + `backend_*` wrappers; unsupported serial controls; no session/slip.
- [x] `repos/fujinet-nio-driver/amiga/Makefile` -- second device artifact; serial `NIO_OBJECTS` unchanged.
- [x] `repos/fujinet-nio-driver/amiga/tests/test_fujinet_nio_directory_backend.c` -- host matrix rows plus unsupported controls.
- [x] `repos/fujinet-nio-driver/amiga/tools/` raw probe + Amiberry case -- one guest EXCHANGE through the host runner; identity and no-serial checks.
- [x] `repos/fujinet-nio/docs/native-packet-contract.md` and this story -- record the guest artifact and mount contract.

**Acceptance Criteria:**
- Given the native-test broker installed as `fujinet-nio.device`, when a real guest probe submits EXCHANGE, then the 1.9 host runner processes a raw packet and the probe asserts the service response without `fn_session`/`fn_slip` or serial/timer stream setup.
- Given serial control commands, missing peer, or guest teardown, when requested, then unsupported/error outcomes and resource ownership are tested, and the binary cannot be mistaken for deployable Zorro firmware.

## Spec Change Log

- 2026-09-16: Native-test device pumps EXCHANGE on the caller Process. `dos.library` record I/O is unsafe on the serial `AddTask` worker. Control hooks stay NULL so GET_*/SET_* return `FN_ERR_UNSUPPORTED`.
- 2026-09-16: First Amiberry run Gurus (AddTask + DOS). Replaced caller-pump with `CreateNewProc`. Harness fails on a second DH0 remount so a Guru cannot be scored as success.
- 2026-09-16: Review patches: stop a CreateNewProc worker on init/expunge failure; discard `to-host.pkt` after a timed-out transfer; require `NATIVE:complete` to contain `PASS\n`; inspect the native-test map for omitted serial/session/slip objects.

## Design Notes

`filesystem2` on wb32 maps a host directory (long names). Keep 1.9 names including `to-host.pkt.tmp`. If guest Open/Rename fails, HALT rather than inventing new record names.

`quiesce` for a file mailbox is: discard leftovers, then both `.pkt`/`.tmp` absent. That is the only channel an old reply can use.

Do not change `fujinet-nio-exchange` option planning. Isolation suite asserts serial occupancy; 1.10 needs a smaller probe.

Directory I/O uses `dos.library`, so the native-test worker is a `CreateNewProc` Process. An `AddTask` worker Gurus on the first DOS call; pumping on the caller Process was not a substitute. The Amiberry monitor treats a second DH0 HDF mount as a guest reset (Guru) and fails the case even if a completion marker appears.

## Verification

**Commands:**
- `source /home/markf/dev/nio/fujinet-nio-workspace/scripts/env.sh && cd /home/markf/dev/nio/fujinet-nio-workspace/repos/fujinet-nio-driver/amiga/tests && make build/test_fujinet_nio_device && ./build/test_fujinet_nio_device` -- expected: existing V-BROKER still passes.
- `make build/test_fujinet_nio_directory_backend && ./build/test_fujinet_nio_directory_backend` -- expected: every matrix row except the guest-only happy EXCHANGE.
- `cd /home/markf/dev/nio/fujinet-nio-workspace/repos/fujinet-nio-driver/amiga && make ../build/amiga/fujinet-nio-native-test.device` -- expected: links without `fn_session`/`fn_slip`/`fujinet_nio_serial_backend`.
- `nm ../build/amiga/fujinet-nio-native-test.device` -- expected: no `fn_stream_session_*` / `fn_slip_*` / `backend_open` from the serial TU; `$VER` contains `native-test`.
- `source /home/markf/dev/nio/fujinet-nio-workspace/scripts/env.sh && uv run pytest --run-amiga --amiga-env wb32 --amiga-machine a1200-030 integration-tests/amiberry/test_nio_native_test.py::test_native_test_clock_exchange` -- expected: one node, host runner + `NATIVE:` + injected device; `EXCHANGE io=0 nio=0` and a clock payload. Report an environment blocker instead of skipping silently.

**Manual checks:**
- `git diff` does not edit `fujinet_nio_serial_backend.c`, `fn_session.c`, public `fujinet_nio_device.h`, or production `NIO_OBJECTS`.
- Guest probe never WaitIOs an OpenDevice-only IORequest.

## Suggested Review Order

**Link set**

- Second device artifact omits serial, session, and SLIP objects
  [`Makefile:28`](../../../../repos/fujinet-nio-driver/amiga/Makefile#L28)

**Directory adapter**

- Client-role send/receive, IDENTITY gate, timeout discard
  [`fujinet_nio_directory_backend.c:625`](../../../../repos/fujinet-nio-driver/amiga/nio.device/fujinet_nio_directory_backend.c#L625)

**DOS-safe worker**

- CreateNewProc worker is stopped on init failure and expunge
  [`fujinet_nio_device.c:130`](../../../../repos/fujinet-nio-driver/amiga/nio.device/fujinet_nio_device.c#L130)

**Guest probe**

- One clock EXCHANGE; FAIL if NATIVE:complete cannot be written
  [`fujinet-nio-native-test-probe.c:158`](../../../../repos/fujinet-nio-driver/amiga/tools/fujinet-nio-native-test-probe.c#L158)

**Harness**

- Host runner, NATIVE: mount, host_file PASS, Guru remount fail
  [`conftest.py:1025`](../../../../integration-tests/amiberry/conftest.py#L1025)

- Guest clock asserts plus native-test map scan
  [`test_nio_native_test.py:8`](../../../../integration-tests/amiberry/test_nio_native_test.py#L8)
