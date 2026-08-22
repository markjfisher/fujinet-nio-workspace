---
title: Amiga NIO broker — implementation requirements
---

# Implementation requirements

Normative layout, diagrams, and the BeginIO matrix live in the adopted companion `docs/amiga/nio-broker-architecture.md`. This file states SHALL rules for implementation.

## R1 Layering and ownership

1. `fujinet-nio.device` SHALL be the sole Amiga arbitrator of the selected physical FujiNet transport.
2. The selected backend SHALL be the sole owner of that physical resource (serial.device today; Zorro/other later).
3. Applications and `fujinet-disk.device` SHALL go through `fujinet-nio-lib` only. They SHALL NOT `OpenDevice("fujinet-nio.device")` or any backend device.
4. Only `src/platform/amiga/fn_transport.c` in the library MAY name `fujinet-nio.device`.
5. `fujinet-disk.device` SHALL retain TD_* disk semantics only and SHALL own its own transport context (not a CLI or machine-global `IORequest`).
6. Dependency direction SHALL match architecture §1. No backend or broker dependence on disk/service code.

## R2 Public ABI

1. Stage 1 SHALL emit `repos/fujinet-nio-driver/amiga/include/fujinet_nio_device.h` matching architecture §2 (`FUJINET_NIO_DEVICE_NAME`, unit 0, `FUJINET_NIO_CMD_EXCHANGE`, `FUJINET_NIO_REQUEST_SIZE`, `struct FujiNetNIORequest`).
2. Payload bytes SHALL be opaque. No baud, SLIP, timer, or service fields on the public struct.
3. Base type SHALL be `IORequest`, not `IOStdReq`.
4. Callers SHALL own `fn_request_data` / `fn_response_data` until reply (architecture §5).
5. The broker SHALL NOT copy or retain payload beyond one exchange.
6. `fn_flags` and `fn_pad` MUST be zero on submit; nonzero is a BeginIO reject.
7. Oversize: `fn_request_length` > platform `FN_MAX_PACKET_SIZE` SHALL reject as `IOERR_BADLENGTH` + `FN_ERR_INVALID`. Do not hard-code 1024 in the public ABI; Amiga’s current platform bound is 1024.
8. v1: `fn_struct_size` SHALL equal `sizeof(struct FujiNetNIORequest)`. Future prefix policy is architecture §2.2; do not implement the compatibility table until the struct grows.
9. Stage 1 SHALL add `FN_ERR_ABORTED` = `0x13` to `fujinet-nio.h` only. SHALL NOT reuse `0xFF` or any existing `FN_ERR_*`.
10. Stage 1 SHALL delete `#include "fn_internal.h"` from `fn_session.c` with no intended behavioral change.

## R3 Error domains

1. `io_Error` SHALL be Exec/device only. SHALL NOT contain `FN_ERR_*`. Malformed requests: native request-validation `io_Error` + `FN_ERR_INVALID`. Stage 1/2 SHALL pick the symbol from the build’s `exec/errors.h` (source-check). Tests SHALL NOT use guessed numeric `IOERR_*` literals.
2. `fn_nio_error` SHALL be FN-space only. SHALL NOT contain `IOERR_*`.
3. Callers MUST NOT treat `io_Error` as NIO success/failure.
4. Abort completion SHALL set both `IOERR_ABORTED` and `FN_ERR_ABORTED`.
5. On every failed path (BeginIO reject, abort, NIO/backend failure), `fn_response_length` SHALL be 0.
6. If shim `DoIO` returns `io_Error != 0`, the shim SHALL return a mapped local/device failure and SHALL NOT return a stale `fn_nio_error`.
7. Tests and comments SHALL use `exec/errors.h` symbols, not numeric `IOERR_*` literals.
8. Invalid unit SHALL fail at `OpenDevice` (`FN_ERR_NOT_FOUND` or documented equivalent), not in `BeginIO`.

## R4 Concurrency, FIFO, ReplyMsg

1. One FIFO worker, unit 0, append under `Disable`, no priority.
2. One `FUJINET_NIO_CMD_EXCHANGE` = complete send then complete receive. The worker SHALL NOT interleave two callers.
3. Each independently usable transport context SHALL own its `FujiNetNIORequest`, message port, and open flag. At most one in-flight exchange per context.
4. The broker serializes distinct `IORequest`s. It does NOT make a shared shim request safe.
5. `ReplyMsg` exactly once per request. `IOF_QUICK` SHALL be cleared before any BeginIO `ReplyMsg`. Exchanges SHALL NOT complete inline.
6. AbortIO vs worker SHALL follow architecture §5.1 (queued remove+reply from AbortIO; in-progress flag then worker owns ReplyMsg; completing/replied AbortIO is a no-op).

## R5 Backend lifetime and recovery

1. Lazy-open on first exchange; keep open. “Open once” is steady-state, not a lifetime ban on `backend_open`.
2. `backend_close` then later `backend_open` ONLY for expunge/shutdown or §7 fatal reset (or after a failed open that left the backend closed).
3. `lib_OpenCnt` reaching 0 SHALL NOT close the backend.
4. Client `CloseDevice` on the broker SHALL NOT be `backend_close` and SHALL NOT reset framing.
5. After `backend_close`, next `backend_open` SHALL start with clean framing/session. Serial Stage 2 MUST make session close/open (or extra reset) satisfy that.
6. Fatal path: `backend_close` → fail current request `FN_ERR_TRANSPORT` → next exchange may lazy-open → if reopen fails, fail that request and leave closed → never permanently give up until expunge.
7. Ordinary `device_expunge` SHALL NOT abort or destroy live requests. If `lib_OpenCnt != 0` or the queue is nonempty or an exchange is in progress, defer/refuse. Otherwise stop the worker, `backend_close` if open, release resources. Stage 2 SHALL follow Exec delayed-expunge conventions if present.

## R6 Transport shim (Stage 3)

1. `fn_transport_init` / `exchange_buffers` / `close` SHALL match architecture §3 (port, OpenDevice unit 0, DoIO, WaitIO/AbortIO before CloseDevice).
2. CLI MAY use a process-local singleton. Resident disk device MUST use its own context.
3. `FN_AMIGA_EXPLICIT_LIFECYCLE` remains: disk manages its context; CLI may `atexit(fn_transport_close)`.
4. Public APIs `fn_init`, `fn_raw_call`, `fnsvc_*`, `fn_disk_*` SHALL NOT change.
5. Remove race-investigation `DBG_PRINTF` blocks at cut-over.
6. Update Amiga `nio-core-apps` / `nio-apps` READMEs that still claim the lib opens `serial.device` directly — only at Stage 3, not before.

## R7 Load ordering

1. Environment loads `fujinet-nio.device` before any `fn_transport_init`. Library SHALL NOT auto-load.
2. Missing broker: `IOERR_OPENFAIL` → shim `FN_ERR_NOT_FOUND`.
3. Disk device need not load before the broker; its first NIO call opens the broker via the lib.

## R8 Future backends

1. Current phase: one serial-backed binary installed as `DEVS:fujinet-nio.device`.
2. Stage 5: new binary, identical public ABI, Option A. Callers still `OpenDevice("fujinet-nio.device")`.
3. Higher-level integration assertions SHALL stay backend-agnostic; only environment/backend selection changes.

## R9 Backend interface (v1)

1. Signatures SHALL match architecture §11. SHALL NOT take broker/device objects unless implementation proves they are required.
2. Stage 2 MAY add a private context pointer without changing these semantics. SHALL NOT solve multi-adapter before one adapter exists.
3. `backend_open` SHALL return `FN_OK` or an FN-space transport/setup error.
4. `backend_close` SHALL be idempotent when already closed and SHALL leave framing/session fully reset.
5. `backend_exchange` SHALL run only while open; one complete transaction; set `*response_len = 0` before work; never retain caller buffers after return; terminate in bounded time with `FN_ERR_TIMEOUT` on deadline.
6. Serial baud, `serial.device` unit, `timer.device` unit, poll interval, and timeout SHALL be named constants or config in the serial backend only.
