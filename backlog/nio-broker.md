# NIO Broker Migration

This is the backlog work for the [NIO Broker Architecture](../docs/amiga/nio-broker-architecture.md).

Locked decisions (full text in the architecture): abort is `IOERR_ABORTED` +
`FN_ERR_ABORTED`; backend reopen after defined failure/reset is allowed
(“open once” = steady-state); one `IORequest` per transport context, never a
machine-global request shared by independent tasks.

## Staged migration plan

Each stage is an independently verifiable delivery checkpoint, with the
stated dependencies between stages. Each stage ends with a testable invariant.

| Order | Gate |
|---|---|
| Stage 1 | Blocks Stage 2. ABI, `FN_ERR_ABORTED`, and the `fn_session.c` include fix must exist first. |
| Stage 2 | Broker + serial backend. Tests are **isolated** from the old serial-direct shim: do not load `fujinet-nio.device` on a system whose `fn_transport` still `OpenDevice("serial.device")`. |
| Stage 3 | **Cut-over:** `fn_transport` stops opening `serial.device` and opens the broker instead. |
| Stage 4 | Removes `fujinet-disk.device` idle-close (`fn_transport_close` when the FIFO empties). |
| Stage 5 | Future backend. After the broker ABI is stable; does not depend on Stages 3–4. |

Do not run Stage 2 in parallel with Stage 1. Do not install the Stage 2 broker beside the pre-Stage-3 shim on a shared serial port.

### Stage 1 — Define public ABI and fix framing dependency

**Blocks Stage 2.**

Deliverables:
- [x] `repos/fujinet-nio-driver/amiga/include/fujinet_nio_device.h` with
      `struct FujiNetNIORequest`, `FUJINET_NIO_CMD_EXCHANGE`, `FUJINET_NIO_REQUEST_SIZE`,
      and error codes (coordinated with `fujinet-nio.h`).
- [x] Add `FN_ERR_ABORTED` (`0x13`) to `fujinet-nio.h`. The value must not
      collide with existing `FN_ERR_*` codes, including `FN_ERR_UNKNOWN`
      (`0xFF`).
- [x] Remove `#include "fn_internal.h"` from `fn_session.c` (§9 required fix).
      Verify that `fn_session.c` compiles without it and all existing tests pass.
- [x] Source-check Amiga GCC `exec/errors.h` and record the native symbol for
      malformed-request `io_Error` (unsupported flags/pad, NULL+nonzero).
      Do not guess numeric values. `fn_nio_error` remains `FN_ERR_INVALID`.
- [ ] Finalize this document after peer review.

**Testable invariant:** the header compiles cleanly against the Amiga GCC
toolchain with no warnings. The amiga and amiga-driver library builds continue
to pass. The existing integration suite is unaffected.

### Stage 2 — Implement `fujinet-nio.device` (serial backend)

**Blocked on Stage 1.** Broker tests must be isolated from the old serial-direct
shim (no dual `OpenDevice("serial.device")`).

Deliverables:
- [ ] New `repos/fujinet-nio-driver/amiga/nio.device/` directory.
- [ ] Broker device: `device_init`, `device_open`, `device_close`,
      `device_expunge`, `device_begin_io`, `device_abort_io`, FIFO worker,
      request state machine (§5.1). `BeginIO` validates `fn_struct_size`.
- [ ] Serial backend implementing the contract from §11: `backend_open`,
      `backend_close`, `backend_exchange`. Uses serial.device + timer.device;
      SLIP framing via `fn_session`/`fn_slip` compiled from source.
      Baud, serial/timer units, poll interval, and timeout are named
      constants or config (not magic numbers). `backend_exchange` returns
      `FN_ERR_TIMEOUT` when that deadline is exceeded.
- [ ] `device_expunge` refuses while OpenCnt, queued, or in-progress work
      remains; does not abort live requests.
- [ ] Error recovery per §7: fatal failure → `backend_close`/reset → fail
      the current request → next exchange may lazy-reopen. Serial
      `backend_close` must leave framing/session state clean for reopen.
- [ ] Build system produces `fujinet-nio.device` binary.
- [ ] A dedicated broker test program (not a stub, see the broker test suite)
      validates FIFO, concurrency, buffer ownership, abort, and error
      propagation. Run it in an isolated image/environment that does **not**
      start FLS, `fujinet-disk.device`, or any tool whose `fn_transport` still
      opens `serial.device` directly.

**Testable invariant:** a standalone test tool opens the broker, submits a
`FUJINET_NIO_CMD_EXCHANGE` with a known FujiBus frame, receives the correct
response, closes. The broker test suite passes. The old serial-direct shim is
not loaded in that environment.

### Stage 3 — Cut-over: `fn_transport` stops opening `serial.device`

This is the cut-over. After this stage, `fn_transport` opens the broker only;
`OpenDevice("serial.device")` exists solely in the broker's serial backend.

Deliverables:
- [ ] `fn_transport.c` (Amiga) rewritten per §3: each transport context owns
      its `FujiNetNIORequest`, message port, and open flag.
      `fn_transport_init` opens the broker on that context,
      `fn_transport_exchange_buffers` submits `FUJINET_NIO_CMD_EXCHANGE`,
      `fn_transport_close` closes the broker. CLI may use a process-local
      context; `fujinet-disk.device` must use its own, not a machine-global
      `IORequest`.
- [ ] No application or service code changes.
- [ ] Remove debug instrumentation (`DBG_PRINTF` blocks) added in the race
      investigation.
- [ ] Update Amiga `nio-core-apps` / `nio-apps` READMEs that still say the
      lib uses `serial.device` directly; those sentences stay true until this
      cut-over and should change with it.
- [ ] Update the Amiberry integration-test bootstrap to load `fujinet-nio.device`
      before any FujiNet tool. This is an environment change, not a test-logic
      change: assertions, startup sequences, and expected results are unchanged.

**Testable invariant:** the Amiberry integration suite passes with the same
test assertions and startup-sequence operations as before Stage 3.
`diskdevice-inspect-catalog` must pass reliably. No `OpenDevice("serial.device")`
call exists anywhere outside the broker's serial backend.

### Stage 4 — Remove disk-device idle-close

Removes `fujinet-disk.device` idle-close: the worker must not
`fn_transport_close` when its FIFO empties. Transport close happens only on
explicit teardown (`device_expunge` or equivalent).

Deliverables:
- [ ] Remove the idle-close cycle from `device_worker_entry` (the
      `fn_transport_close` + `client_initialized` reset when the FIFO empties).
- [ ] The disk device calls `fn_transport_close` only in `device_expunge` (or
      equivalent explicit-lifecycle teardown).
- [ ] Worker inner loop becomes: dequeue → `fn_init` (no-op if already open) →
      exchange → `io_Error` → `ReplyMsg` → continue.

**Testable invariant:** all integration tests pass; the worker code is visibly
simpler; no test depends on the old idle-close behavior.

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

## Broker test suite

Stage 2 only. Isolated from the old serial-direct shim (see Stage 2). Replaces
an earlier stub-backend Stage 5 idea.

Rather than a static-response stub backend, the broker test suite validates
broker behavior with a real serial backend and a controlled test environment.
The suite covers:

| Test | What it proves |
|---|---|
| Single-client exchange | Basic frame/response round-trip |
| Concurrent-client FIFO ordering | Multiple tasks submit simultaneously; responses are delivered to the correct caller in FIFO order |
| Buffer ownership | Response data is fully written before ReplyMsg; the caller's buffer is not aliased |
| Backend lazy-open | First exchange opens serial.device; subsequent exchanges reuse it |
| Backend resident-lifetime | lib_OpenCnt reaching zero does not close serial.device; next exchange succeeds without reopen |
| `AbortIO` — queued request | Request aborted before worker dequeues it; error returned; no exchange performed |
| `AbortIO` — in-progress request | AbortIO arrives mid-exchange; exchange completes physically; result discarded; abort error returned; no double-reply |
| Backend error propagation | Backend forced into error state (by injecting a bad frame); `FN_ERR_TRANSPORT` returned; broker remains usable |
| Error recovery | After a fatal backend error: close/reset, current request fails; the next exchange lazy-reopens or fails consistently with the backend still closed (§7) |
| No service interpretation | Arbitrary payloads that do not correspond to valid FujiBus service commands are exchanged without modification |
| BeginIO ABI reject | Wrong command, bad size, reserved flags/pad, NULL+nonzero, oversize: IOF_QUICK cleared, two-domain errors per §2.1, `fn_response_length` = 0 |
| Expunge while busy | Expunge deferred/refused while opens or queued/in-progress requests remain |

Real service integration tests continue to run against the real `fujinet-nio.device`
with the serial backend. No fake backend is required to validate service
behavior.
