---
title: Amiga NIO broker — staged acceptance
---

# Staged acceptance

Workspace checkbox tracking remains `backlog/nio-broker.md`. This companion is the acceptance contract. Each stage is an independently verifiable delivery checkpoint, with the stated dependencies between stages. A stage is not done if its invariant fails.

## Gates

| Stage | Blocks | Isolation |
| --- | --- | --- |
| 1 ABI + `FN_ERR_ABORTED` + `fn_session.c` include | Stage 2 | Existing integration unchanged |
| 2 Broker + serial backend | Stage 3 | **Must not** load `fujinet-nio.device` on a machine whose `fn_transport` still opens `serial.device` |
| 3 Shim cut-over | Stage 4 (idle-close still allowed until 4) | After this, `serial.device` open only in serial backend |
| 4 Remove disk idle-close | — | Integration must not depend on idle-close |
| 5 Future backend binary | After ABI is stable; does not depend on Stages 3–4 | Same higher-level assertions as Stage 3 |

Do not run Stage 2 in parallel with Stage 1.

## Stage 1 — Public ABI and framing dependency

**Capabilities:** CAP-1.

Deliverables:

- Header `repos/fujinet-nio-driver/amiga/include/fujinet_nio_device.h` as architecture §2.
- `FN_ERR_ABORTED` (`0x13`) in `fujinet-nio.h`.
- Remove `#include "fn_internal.h"` from `fn_session.c`; session compiles; existing tests pass.
- Header validates lengths against platform `FN_MAX_PACKET_SIZE`, not a hard-coded 1024 in the ABI.
- Source-check Amiga GCC `exec/errors.h` and record the native symbol for malformed-request `io_Error` (flags/pad, NULL+nonzero). Do not guess numerics.

**Invariant:** Header compiles warning-clean with Amiga GCC. Amiga and amiga-driver library builds pass. Existing integration suite unaffected.

## Stage 2 — `fujinet-nio.device` (serial)

**Capabilities:** CAP-2, CAP-3, CAP-4, CAP-5, CAP-7.

Deliverables:

- `repos/fujinet-nio-driver/amiga/nio.device/` with init/open/close/expunge/BeginIO/AbortIO, FIFO worker, §5.1 state machine, `fn_struct_size` check.
- Serial backend implementing §11 signatures; `serial.device` + `timer.device`; path-compiled `fn_session`/`fn_slip`. Baud, units, poll interval, and timeout are named serial-backend constants/config.
- Recovery per architecture §7; `backend_close` idempotent and leaves framing clean.
- Expunge per architecture §6: refuse while open/queued/in-progress; no implicit abort.
- Build produces `fujinet-nio.device`.
- Dedicated broker test program (not a stub) in an isolated image: no FLS, no `fujinet-disk.device`, no serial-direct `fn_transport`.

**Invariant:** Standalone tool opens broker, exchanges a known FujiBus frame, gets the correct response, closes. Suite below passes. Old shim not loaded.

### Stage 2 broker test suite

| Test | Passes when |
| --- | --- |
| Single-client exchange | Known frame/response round-trip |
| Concurrent-client FIFO ordering | Simultaneous tasks; correct caller; FIFO order |
| Buffer ownership | Response fully written before `ReplyMsg`; caller buffer not aliased |
| Backend lazy-open | First exchange opens `serial.device`; later exchanges reuse it |
| Backend resident-lifetime | `lib_OpenCnt` 0 does not close `serial.device`; next exchange succeeds without reopen |
| AbortIO queued | Aborted before dequeue; abort completion; no exchange |
| AbortIO in-progress | Physical exchange completes; result discarded; abort completion; no double-reply |
| Backend error propagation | Forced backend error → `FN_ERR_TRANSPORT`; broker still usable |
| Error recovery | Fatal → close/reset, current fails; next lazy-reopens or fails with backend still closed |
| No service interpretation | Arbitrary non-service payloads exchanged unmodified |
| BeginIO ABI reject | Wrong command, bad size, reserved flags/pad, NULL+nonzero, oversize: `IOF_QUICK` cleared, two-domain errors, `fn_response_length` = 0 |
| Expunge while busy | Expunge deferred/refused while opens or queued/in-progress remain; live requests are not aborted by expunge |

Malformed-request `io_Error` is the `exec/errors.h` symbol recorded in Stage 1/2; FN side is `FN_ERR_INVALID`. Tests use that symbol, not a guessed number.

## Stage 3 — Cut-over

**Capabilities:** CAP-6, CAP-8.

Deliverables:

- Amiga `fn_transport.c` per architecture §3.
- No application or service code changes.
- Remove race-investigation `DBG_PRINTF`.
- README sentences that say the lib uses `serial.device` directly.
- Amiberry bootstrap loads `fujinet-nio.device` before any FujiNet tool (environment only).

**Invariant:** Amiberry integration suite passes with the same assertions and startup-sequence operations as before Stage 3. `diskdevice-inspect-catalog` passes reliably. No `OpenDevice("serial.device")` outside the broker serial backend.

## Stage 4 — Disk idle-close removal

**Capabilities:** CAP-9.

Deliverables:

- Remove `fn_transport_close` + `client_initialized` reset when the disk worker FIFO empties.
- `fn_transport_close` only in `device_expunge` (or equivalent explicit teardown).
- Worker loop: dequeue → `fn_init` (no-op if open) → exchange → `io_Error` → `ReplyMsg` → continue.

**Invariant:** All integration tests pass; worker is visibly simpler; no test depends on idle-close.

## Stage 5 — Future backend (not this cut-over’s implementation)

**Capabilities:** CAP-10.

Deliverables when a second backend is actually built:

- New backend module on the internal §11 contract.
- New broker binary, installed as `fujinet-nio.device` for that hardware.
- No changes to `fujinet-disk.device`, `fujinet-nio-lib`, or applications.

**Invariant:** Stage 3 integration suite passes without changing test logic or assertions. Parity with the serial baseline is required before production.

Zorro/packet-native hardware design itself is out of this spec.
