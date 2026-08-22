---
title: 'Amiga NIO broker Stage 2A — Exec core'
type: 'feature'
created: '2026-08-22'
status: 'done'
baseline_commit: '97bd677695848a94e9dce70eaa05f7d844d3cba5'
review_loop_iteration: 0
context:
  - docs/amiga/nio-broker-architecture.md
  - docs/agent-test-policy.md
  - backlog/nio-broker.md
  - _bmad-output/implementation-artifacts/spec-amiga-nio-broker-stage-2.md
  - _bmad-output/implementation-artifacts/spec-amiga-nio-broker-stage-1.md
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** There is no `fujinet-nio.device` resident, BeginIO validation, AbortIO state machine, FIFO worker, or lifecycle/expunge, so Stage 2 cannot proceed to a real serial backend.

**Approach:** Build the broker Exec/resident skeleton and host-test it with an injectable backend. Path-compile readiness: shared `fn_slip` declarations. Align host `exec/errors.h` with NDK 47.1. Serial.device integration is **2B**; do not mark parent Stage 2 complete after 2A.

## Boundaries & Constraints

**Always:**
- Architecture §2/§2.1, §5/§5.1, §6. Two error domains never mix. Clear `IOF_QUICK` before any BeginIO `ReplyMsg`. One FIFO worker; unit 0; one `IORequest` per context.
- BeginIO first-match: wrong command → bad `fn_struct_size` → non-zero `fn_flags`/`fn_pad` → NULL request + nonzero length → NULL response + nonzero capacity → `fn_request_length` > `FN_MAX_PACKET_SIZE` → `fn_response_capacity` > `FN_MAX_PACKET_SIZE`.
- NULL + zero request length and NULL + zero response capacity are **not** `IOERR_BADADDRESS`.
- `fn_response_capacity` > `FN_MAX_PACKET_SIZE` → `IOERR_BADLENGTH` + `FN_ERR_INVALID`, `fn_response_length` = 0, not queued.
- Tests use `IOERR_*` symbols. Stub `IOERR_NOCMD` = -3, `IOERR_BADLENGTH` = -4 (NDK 47.1).
- Shared `fn_slip` header; `fn_session.c` includes it (no local prototype, no `fn_internal.h` in session).
- Host tests may inject a backend (canned/delay) so FIFO/abort/expunge/OpenCnt/fatal sequencing do not need RS-232.
- Run the named Verification commands. 2A accepted ≠ Stage 2 done.

**Ask First:**
- Changing public `FujiNetNIORequest` or `FUJINET_NIO_CMD_EXCHANGE`.
- A public/stub backend ABI or multi-adapter support.

**Never:**
- Implement or require `serial.device` / `timer.device` / `backend_exchange` over the wire in 2A.
- Edit `fn_transport.c`. Involve FLS or `fujinet-disk.device`. Create epics/stories.
- Check Stage 2 backlog boxes. Run `scripts/amiga-tests` or DiskDevice pytest as the 2A gate.
- Start 2B in this spec.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Happy (injected) | Valid exchange; injectable backend returns bytes | Worker calls backend; `io_Error` 0; `fn_nio_error` from backend; write then one `ReplyMsg` | N/A |
| Empty request | NULL `fn_request_data`, length 0 | Not `IOERR_BADADDRESS`; queued/exchanged | Injected FN error only if backend fails |
| Overlapping malformed | Wrong command and bad size and flags | First-match `IOERR_NOCMD` + `FN_ERR_INVALID`; not queued | `fn_response_length` 0; `IOF_QUICK` cleared |
| Response oversize | capacity > `FN_MAX_PACKET_SIZE` | `IOERR_BADLENGTH` + `FN_ERR_INVALID` | `fn_response_length` 0 |
| Abort queued | AbortIO before dequeue | Removed; `IOERR_ABORTED` + `FN_ERR_ABORTED`; no backend call | No double-reply |
| Abort in-progress | AbortIO after dequeue (delaying backend) | Backend may finish; result discarded; abort pair; one `ReplyMsg` | N/A |
| OpenCnt zero | Last CloseDevice; injected backend “open” | Backend not closed; next exchange reuses it | N/A |
| Fatal backend | Injected transport/fatal | Current fails FN-space; close/reset; next may lazy-reopen | Do not copy FN into `io_Error` |
| Expunge busy | OpenCnt or queue or in-progress | Expunge refused; live requests not aborted | N/A |

</frozen-after-approval>

## Code Map

- `docs/amiga/nio-broker-architecture.md` §2, §5.1, §6 — validation, abort states, expunge; §11 signatures exist so the injectable backend matches; do not implement serial here.
- `repos/fujinet-nio-driver/amiga/include/fujinet_nio_device.h` — **read-only ABI**.
- `repos/fujinet-nio-driver/amiga/disk.device/fujinet_disk_device.c` — **pattern only** (`FN_REGISTER`, `FUJINET_DISK_NATIVE_TEST`). No trackdisk coupling.
- `repos/fujinet-nio-driver/amiga/common/fujinet_io_queue.c` — FIFO append/detach/next; broker unit 0 only.
- `repos/fujinet-nio-driver/amiga/nio.device/` — **create** resident + BeginIO/AbortIO/worker; backend is a test hook in 2A.
- `repos/fujinet-nio-driver/amiga/tests/Makefile` — new host binary, `FUJINET_NIO_NATIVE_TEST`, `-Istubs`, run from `make tests`.
- `repos/fujinet-nio-driver/amiga/tests/stubs/exec/errors.h` — **fix** swapped `IOERR_NOCMD`/`IOERR_BADLENGTH`; disk resident tests keep using symbols.
- `repos/fujinet-nio-lib/include/fn_internal.h` L103–111 — move slip prototypes to `include/fn_slip.h`; include from `fn_internal.h` and `fn_session.c`.
- `repos/fujinet-nio-lib/src/common/fn_session.c` L6 — drop local `fn_slip_decode` prototype.
- `repos/fujinet-nio-lib/include/fn_protocol.h` — `FN_MAX_PACKET_SIZE` oversize bound (not a literal 1024 in the ABI).
- `repos/fujinet-nio-lib/src/platform/amiga/fn_transport.c` — **do not edit**.
- `_bmad-output/implementation-artifacts/spec-amiga-nio-broker-stage-2.md` — parent gate; 2A does not close it.

## Tasks & Acceptance

**Execution:**
- [x] `repos/fujinet-nio-lib/include/fn_slip.h` -- encode/decode declarations; session + `fn_internal.h` use them -- Stage 1 deferred slip surface
- [x] `repos/fujinet-nio-driver/amiga/tests/stubs/exec/errors.h` -- NDK 47.1 numerics -- host tests must not use swapped stub values
- [x] `repos/fujinet-nio-driver/amiga/nio.device/` -- init/open/close/expunge/BeginIO/AbortIO/FIFO worker/§5.1 -- Exec core
- [x] Host native tests with injectable backend covering the I/O matrix -- cheapest driver gate; no RS-232
- [x] `repos/fujinet-nio-driver/amiga/tests/Makefile` -- `make tests` builds and **runs** the new binary -- policy

**Acceptance Criteria:**
- Given overlapping malformations, when BeginIO runs, then only the first-match `io_Error` applies, `fn_nio_error` is `FN_ERR_INVALID`, and the request is not queued.
- Given NULL request pointer and length 0, when BeginIO runs, then it is not `IOERR_BADADDRESS`.
- Given `fn_response_capacity` > `FN_MAX_PACKET_SIZE`, when BeginIO runs, then `IOERR_BADLENGTH` + `FN_ERR_INVALID` and `fn_response_length` is 0.
- Given OpenCnt reaches 0, when a later exchange is issued, then the injected backend was not closed solely because OpenCnt hit 0.
- Given 2A Verification passed, when Stage 2 status is considered, then Stage 2 is still incomplete.

## Spec Change Log

## Design Notes

Injectable backend implements architecture §11 call shape so 2B can swap in serial without changing BeginIO/FIFO. Do not compile `fn_transport.c` into the device. Worker stack should allow later SLIP wait; 2A need not allocate serial buffers.

## Verification

2A is incomplete if these were not run. Do not use guest pytest or `make native` as the 2A gate.

**Commands (after `source "$NIO_WORKSPACE/scripts/env.sh"`):**
- `cd "$NIO_WORKSPACE/repos/fujinet-nio-lib" && make check` -- expected: all configured targets and host tests pass (`fn_slip.h` / session)
- `cd "$NIO_WORKSPACE/repos/fujinet-nio-driver/amiga" && make tests` -- expected: existing tests plus new broker host tests pass (BeginIO matrix, abort, FIFO, expunge, aligned stubs)

## Suggested Review Order

**Resident and worker**

- Device base, injectable §11 backend hooks, and unit-0 FIFO worker.
  [`fujinet_nio_device.c:44`](../../repos/fujinet-nio-driver/amiga/nio.device/fujinet_nio_device.c#L44)

- Lazy-open; OpenCnt 0 does not close the backend.
  [`fujinet_nio_device.c:116`](../../repos/fujinet-nio-driver/amiga/nio.device/fujinet_nio_device.c#L116)

- Completing-state: abort vs result, clamp length, clear in_progress, then ReplyMsg.
  [`fujinet_nio_device.c:141`](../../repos/fujinet-nio-driver/amiga/nio.device/fujinet_nio_device.c#L141)

**BeginIO, AbortIO, expunge**

- First-match validation; clear IOF_QUICK before any ReplyMsg.
  [`fujinet_nio_device.c:348`](../../repos/fujinet-nio-driver/amiga/nio.device/fujinet_nio_device.c#L348)

- Queued abort replies here; in-progress only sets the abort flag.
  [`fujinet_nio_device.c:405`](../../repos/fujinet-nio-driver/amiga/nio.device/fujinet_nio_device.c#L405)

- Busy expunge refused; idle path closes backend and unloads AUTOINIT.
  [`fujinet_nio_device.c:290`](../../repos/fujinet-nio-driver/amiga/nio.device/fujinet_nio_device.c#L290)

**Shared SLIP surface**

- Encode/decode live in the shared header session can include.
  [`fn_slip.h:22`](../../repos/fujinet-nio-lib/include/fn_slip.h#L22)

- Internal header re-exports the same declarations.
  [`fn_internal.h:99`](../../repos/fujinet-nio-lib/include/fn_internal.h#L99)

**Host tests and stubs**

- Injectable backend plus I/O-matrix cases invoked from main.
  [`test_fujinet_nio_device.c:168`](../../repos/fujinet-nio-driver/amiga/tests/test_fujinet_nio_device.c#L168)

- Isolated first-match rows beyond the overlapping-malformed case.
  [`test_fujinet_nio_device.c:243`](../../repos/fujinet-nio-driver/amiga/tests/test_fujinet_nio_device.c#L243)

- NDK 47.1 `IOERR_NOCMD` / `IOERR_BADLENGTH` numerics.
  [`errors.h:6`](../../repos/fujinet-nio-driver/amiga/tests/stubs/exec/errors.h#L6)

- `make tests` builds and runs the new binary.
  [`Makefile:57`](../../repos/fujinet-nio-driver/amiga/tests/Makefile#L57)
