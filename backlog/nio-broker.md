# NIO Broker Migration

This is the backlog work for the [NIO Broker Architecture](../docs/amiga/nio-broker-architecture.md)

## Staged migration plan

Each stage ends with a testable invariant. Stages that share no dependency may
proceed in parallel.

### Stage 1 — Define public ABI and fix framing dependency

Deliverables:
- [ ] `repos/fujinet-nio-driver/amiga/include/fujinet_nio_device.h` with
      `struct FujiNetNIORequest`, `FUJINET_NIO_CMD_EXCHANGE`, `FUJINET_NIO_REQUEST_SIZE`,
      and error codes (coordinated with `fujinet-nio.h`).
- [ ] Add `FN_ERR_ABORTED` to `fujinet-nio.h` with a value outside `0x00`–`0x12`.
- [ ] Remove `#include "fn_internal.h"` from `fn_session.c` (§9 required fix).
      Verify that `fn_session.c` compiles without it and all existing tests pass.
- [ ] This document finalised after peer review.

**Testable invariant:** the header compiles cleanly against the Amiga GCC
toolchain with no warnings. The amiga and amiga-driver library builds continue
to pass. The existing integration suite is unaffected.

### Stage 2 — Implement `fujinet-nio.device` (serial backend)

Deliverables:
- [ ] New `repos/fujinet-nio-driver/amiga/nio.device/` directory.
- [ ] Broker device: `device_init`, `device_open`, `device_close`,
      `device_expunge`, `device_begin_io`, `device_abort_io`, FIFO worker,
      request state machine (§5.1). `BeginIO` validates `fn_struct_size`.
- [ ] Serial backend implementing the contract from §11: `backend_open`,
      `backend_close`, `backend_exchange`. Uses serial.device + timer.device;
      SLIP framing via `fn_session`/`fn_slip` compiled from source.
- [ ] Error recovery policy resolved per §7 TODO.
- [ ] Build system produces `fujinet-nio.device` binary.
- [ ] A dedicated broker test program (not a stub, see §13) validates FIFO,
      concurrency, buffer ownership, abort, and error propagation.

**Testable invariant:** a standalone test tool opens the broker, submits a
`FUJINET_NIO_CMD_EXCHANGE` with a known FujiBus frame, receives the correct
response, closes. The broker test suite passes (see §13).

### Stage 3 — Re-route `fn_transport.c` through the broker

Deliverables:
- [ ] `fn_transport.c` (Amiga) rewritten: `fn_transport_init` opens the broker,
      `fn_transport_exchange_buffers` submits `FUJINET_NIO_CMD_EXCHANGE`,
      `fn_transport_close` closes the broker.
- [ ] No application or service code changes.
- [ ] Remove debug instrumentation (`DBG_PRINTF` blocks) added in the race
      investigation.
- [ ] Update the Amiberry integration-test bootstrap to load `fujinet-nio.device`
      before any FujiNet tool. This is an environment change, not a test-logic
      change: assertions, startup sequences, and expected results are unchanged.

**Testable invariant:** the Amiberry integration suite passes with the same
test assertions and startup-sequence operations as before Stage 3.
`diskdevice-inspect-catalog` must pass reliably. No `OpenDevice("serial.device")`
call exists anywhere outside the broker's serial backend.

### Stage 4 — Simplify `fujinet-disk.device` worker

Deliverables:
- [ ] Remove the idle-close cycle from `device_worker_entry` (the
      `fn_transport_close` + `client_initialized` reset when the FIFO empties).
- [ ] The disk device calls `fn_transport_close` only in `device_expunge` (or
      equivalent explicit-lifecycle teardown).
- [ ] Worker inner loop is now: dequeue → `fn_init` (no-op) → exchange →
      `io_Error` → `ReplyMsg` → continue.

**Testable invariant:** all integration tests pass; the worker code is visibly
simpler; no test depends on the old idle-close behaviour.

### Stage 5 — Future backend (Zorro or other)

Deliverables:
- [ ] New backend module implementing the internal backend interface.
- [ ] New broker binary compiled with the new backend; installed as
      `fujinet-nio.device` for users with that hardware.
- [ ] No changes to `fujinet-disk.device`, `fujinet-nio-lib`, or applications.

**Testable invariant:** the full integration suite from Stage 3 passes against
the new backend without modification to test logic or assertions. Backend
parity with the serial baseline is required before a new backend is
production-ready.

---

## 13. Broker test suite (replaces Stage 5 stub-backend)

Rather than a static-response stub backend, the broker test suite validates
broker behaviour with a real serial backend and a controlled test environment.
The suite covers:

| Test | What it proves |
|---|---|
| Single-client exchange | Basic frame/response round-trip |
| Concurrent-client FIFO ordering | Multiple tasks submit simultaneously; responses are delivered to the correct caller in FIFO order |
| Buffer ownership | Response data is fully written before ReplyMsg; caller's buffer is not aliased |
| Backend lazy-open | First exchange opens serial.device; subsequent exchanges reuse it |
| Backend resident-lifetime | lib_OpenCnt reaching zero does not close serial.device; next exchange succeeds without reopen |
| `AbortIO` — queued request | Request aborted before worker dequeues it; error returned; no exchange performed |
| `AbortIO` — in-progress request | AbortIO arrives mid-exchange; exchange completes physically; result discarded; abort error returned; no double-reply |
| Backend error propagation | Backend forced into error state (by injecting a bad frame); `FN_ERR_TRANSPORT` returned; broker remains usable |
| Error recovery | After a backend error, a subsequent exchange either succeeds (lazy-reopen) or returns a consistent error (per resolved §7 policy) |
| No service interpretation | Arbitrary payloads that do not correspond to valid FujiBus service commands are exchanged without modification |

Real service integration tests continue to run against the real `fujinet-nio.device`
with the serial backend. No fake backend is required to validate service
behaviour.
