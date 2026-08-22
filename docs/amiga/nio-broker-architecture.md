# FujiNet NIO Broker Architecture

*Status: design for review — not yet implemented*

This document defines the target architecture for the Amiga NIO transport
layer. The immediate motivation is a proven race: FLS and
`fujinet-disk.device` both call `OpenDevice("serial.device")` independently.
The deeper motivation is that serial.device is a temporary proving-ground
transport. Adding Zorro and other packet-native backends must not require
changes to any service, disk device, or application code.

**Locked decisions**

| Topic | Rule |
|---|---|
| Abort | `io_Error` = `IOERR_ABORTED`; `fn_nio_error` = `FN_ERR_ABORTED`. Never copy FN codes into `io_Error`. |
| Recovery | Backend may reopen after a defined failure/reset (or expunge). “Open once” is normal steady-state, not a resident-lifetime prohibition. |
| Concurrency | One `IORequest` per transport context / in-flight caller. No shared global `IORequest` across independent tasks. |

---

## 1. Responsibilities and dependency direction

```
  ┌────────────────────────────────────────────────────────┐
  │  Clients: apps (FLS, fujinet-mount, …) and             │
  │           fujinet-disk.device (TD_* only; lib client)  │
  └───────────────────────┬────────────────────────────────┘
                          │ call
  ┌───────────────────────▼────────────────────────────────┐
  │  fujinet-nio-lib  (fn_raw_call, fnsvc_*, fn_disk_*)    │
  │  public, platform-agnostic service API                 │
  └───────────────────────┬────────────────────────────────┘
                          │ Amiga platform transport shim
                          │ (fn_transport_init/exchange/close)
  ┌───────────────────────▼────────────────────────────────┐
  │  fujinet-nio.device                                    │
  │  generic NIO broker / sole transport arbitrator        │
  │  one FIFO worker, service-agnostic, backend-neutral    │
  └────────┬───────────────────────────────────────────────┘
           │ internal backend interface (not public ABI)
     ┌─────┴──────┬─────────────────────┐
     ▼            ▼                     ▼
  serial        Zorro              future hardware
  backend       backend               backend
  (owns         (owns                 (owns its
  serial.device) Zorro card)          resource)
```

### Component responsibilities

**fujinet-nio.device (broker)**
- Sole Amiga owner/arbitrator of the selected physical FujiNet transport.
- Serializes all NIO exchanges from any number of concurrent callers through
  a single FIFO worker.
- Service-agnostic: does not interpret DiskService, FileService, or any other
  FujiBus service. Payload bytes are opaque to the broker.
- Backend-neutral: the selected physical backend is an implementation detail.
  The public ABI has no serial, Zorro, or framing fields.

**Physical backends (serial, Zorro, future)**
- Each backend owns exactly one physical transport resource for the broker's
  resident lifetime.
- Responsible for framing (SLIP for stream transports; native framing for
  packet hardware).
- Isolated below the broker; no application or service code depends on a
  specific backend.

**fujinet-nio-lib Amiga transport shim (fn_transport.c)**
- The only component in the library that names `fujinet-nio.device`.
- Each independently usable transport context owns its broker `FujiNetNIORequest`,
  message port, and request/response state (§3).
- `fn_transport_init` opens the broker on that context;
  `fn_transport_exchange_buffers` submits that context's `FujiNetNIORequest`;
  `fn_transport_close` closes the broker on that context.
- All other library code (service, packet, session) is unchanged.

**fujinet-disk.device**
- Retains only Amiga TD_* disk semantics.
- Uses `fn_init` / `fn_transport_*` with no call-site change.
- Never opens `fujinet-nio.device` directly.
- Never owns any physical FujiNet transport.

**Applications (FLS, fujinet-mount, diskinspect, etc.)**
- Continue calling `fn_raw_call`, `fnsvc_*`, `fn_disk_*`, etc.
- Do not call `OpenDevice("fujinet-nio.device")` or any backend device
  directly.
- No Amiga-specific IORequest code required in application sources.

### Dependency rules

| Component | May depend on | Must not depend on |
|---|---|---|
| Physical backend | exec.library, its own hardware, framing helpers (fn_slip, fn_session) | fujinet-disk.device, fujinet-nio-lib service layer |
| fujinet-nio.device | exec, selected backend, framing helpers | fujinet-disk.device, service/protocol code |
| fujinet-nio-lib transport shim | fujinet-nio.device (via OpenDevice), exec | specific backends, serial.device directly |
| fujinet-disk.device | fujinet-nio-lib, exec | fujinet-nio.device directly, any backend |
| Applications | fujinet-nio-lib | fujinet-nio.device internals, any backend |

---

## 2. The `fujinet-nio.device` public IORequest ABI

The broker exposes one logical command. The payload is opaque: the broker does
not interpret it.

```c
/* repos/fujinet-nio-driver/amiga/include/fujinet_nio_device.h */

#define FUJINET_NIO_DEVICE_NAME    "fujinet-nio.device"
#define FUJINET_NIO_DEVICE_UNIT    0

/* The only command accepted by the broker worker */
#define FUJINET_NIO_CMD_EXCHANGE   (CMD_NONSTD + 0)

/* Current struct size; callers must set fn_struct_size to this value */
#define FUJINET_NIO_REQUEST_SIZE   (sizeof(struct FujiNetNIORequest))

struct FujiNetNIORequest {
    /*
     * Exec IORequest header. io_Command = FUJINET_NIO_CMD_EXCHANGE.
     * io_Error is Exec/device only (see §2.1). BeginIO clears IOF_QUICK
     * before any ReplyMsg.
     */
    struct IORequest fn_io;

    /* ABI size guard; must be FUJINET_NIO_REQUEST_SIZE (see §2.1 / §2.2) */
    UWORD        fn_struct_size;

    UWORD        fn_flags;          /* reserved; must be zero */

    /* Opaque FujiBus frame; caller-owned until reply (see §5) */
    const UBYTE *fn_request_data;
    UWORD        fn_request_length;  /* bounded by platform FN_MAX_PACKET_SIZE */ */

    /* Caller-owned response buffer; fn_response_length valid only on FN_OK */
    UBYTE       *fn_response_data;
    UWORD        fn_response_capacity;
    UWORD        fn_response_length;

    UBYTE        fn_nio_error;      /* FN-space result; see §2.1 */

    UBYTE        fn_pad[3];         /* alignment; must be zero */
};
```

Length fields are `UWORD` (ABI representational capacity 65535). Stage 1
validates `fn_request_length` against the platform's `FN_MAX_PACKET_SIZE`
(currently 1024 on Amiga; see `fn_protocol.h` when not `__CC65__`). The public
ABI does not hard-code 1024. If a future platform bound exceeds 65535, the
fields must become `ULONG`; that change is an ABI version bump tracked through
`fn_struct_size`.

### 2.1 Error domain

The struct carries **two independent error fields**. Conflating them has
caused real debugging confusion in this project and must not happen again.
Never copy one field into the other.

| Field | Domain | Must not contain |
|---|---|---|
| `fn_io.io_Error` | Native Exec/device completion status only | `FN_ERR_*` (`FN_ERR_TRANSPORT`, `FN_ERR_TIMEOUT`, `FN_ERR_ABORTED`, …) |
| `fn_nio_error` | FujiNet/NIO result only (`fujinet-nio.h`) | Exec `IOERR_*` |

**`fn_io.io_Error` — native Exec/device errors only**

Set by the broker to reflect the outcome of the Exec dispatch itself.
Use the symbols from `exec/errors.h`; do not hard-code their numeric values
in this architecture or in tests.

| Symbol (`exec/errors.h`) | Meaning |
|---|---|
| 0 | Dispatch succeeded; check `fn_nio_error` for NIO outcome |
| `IOERR_ABORTED` | Request was aborted before or during processing |
| `IOERR_NOCMD` | Unrecognized command (not `FUJINET_NIO_CMD_EXCHANGE`) |
| `IOERR_BADLENGTH` | `fn_struct_size` rejected (§2.2) or request length oversize |

Callers must not read `io_Error` to determine whether an NIO exchange
succeeded or failed.

**`fn_nio_error` — FN-space protocol errors**

Carries the FujiNet/NIO result, using codes from `fujinet-nio.h`. When
`io_Error` is 0, this is the exchange outcome. When `io_Error` is
`IOERR_ABORTED`, this is `FN_ERR_ABORTED` (see AbortIO completion below).
A non-zero `io_Error` never means “ignore `fn_nio_error` and treat `io_Error`
as an FN code.”

| Symbol | Value | Meaning in broker context |
|---|---|---|
| `FN_OK` | 0x00 | Exchange completed, response written to buffer |
| `FN_ERR_NOT_FOUND` | 0x01 | Invalid unit at `OpenDevice`, or equivalent documented mapping |
| `FN_ERR_INVALID` | 0x02 | Bad ABI fields (size, flags/pad, pointers, length) |
| `FN_ERR_IO` | 0x05 | Backend setup or IO error |
| `FN_ERR_TIMEOUT` | 0x06 | No response received within the exchange timeout |
| `FN_ERR_TRANSPORT` | 0x10 | Physical layer failure (backend error) |
| `FN_ERR_ABORTED` | 0x13 | Request aborted via `AbortIO` (Stage 1; see below) |

**AbortIO completion**

- `fn_io.io_Error` is set to `IOERR_ABORTED`.
- `fn_nio_error` is set to `FN_ERR_ABORTED`.
- FN-space errors are never copied into `io_Error`.

This pair is used for both queued aborts (`AbortIO` replies) and in-progress
aborts (the worker overwrites the exchange result, then replies). There is
no `FN_ERR_TRANSPORT` placeholder for abort. On abort, `fn_response_length`
is 0.

**BeginIO / completion matrix**

Two-domain separation is the contract. Malformed broker `IORequest`s use:

- `io_Error` = the appropriate native Exec/device request-validation error
- `fn_nio_error` = `FN_ERR_INVALID`

Stage 1/2 inspects the Amiga GCC `exec/errors.h` in the build and chooses the
actual available symbol for unsupported flags/reserved fields and NULL +
nonzero length/capacity. Do not invent or hard-code guessed numeric
`IOERR_*` values in this document or in tests. Unit is checked at
`OpenDevice`, not in `BeginIO`.

| Condition | `io_Error` | `fn_nio_error` |
|---|---|---|
| Valid request accepted for queue | 0 until completion | undefined until `ReplyMsg` |
| Wrong command | `IOERR_NOCMD` | `FN_ERR_INVALID` |
| Bad `fn_struct_size` | `IOERR_BADLENGTH` | `FN_ERR_INVALID` |
| Non-zero reserved / unsupported `fn_flags` | native invalid-request error | `FN_ERR_INVALID` |
| Request pointer NULL with non-zero length | native invalid-request error | `FN_ERR_INVALID` |
| Response pointer NULL with non-zero capacity | native invalid-request error | `FN_ERR_INVALID` |
| Request too large (`fn_request_length` > `FN_MAX_PACKET_SIZE`) | `IOERR_BADLENGTH` | `FN_ERR_INVALID` |
| Invalid unit | suitable native device error | `FN_ERR_NOT_FOUND` or documented equivalent |
| Aborted | `IOERR_ABORTED` | `FN_ERR_ABORTED` |

Immediate rejects reply from `BeginIO` without queuing. On every failed
exchange path (BeginIO reject, abort, NIO/backend failure),
`fn_response_length` is 0.

**Stage 1 — `FN_ERR_ABORTED` in `fujinet-nio.h`**

`FN_ERR_ABORTED` does not exist yet. Stage 1 must add it with value **`0x13`**,
which is unused in the current `fujinet-nio.h` set (`FN_OK` `0x00`,
`FN_ERR_NOT_FOUND`…`FN_ERR_UNSUPPORTED` `0x01`–`0x08`, `FN_ERR_TRANSPORT`…
`FN_ERR_NO_HANDLES` `0x10`–`0x12`, `FN_ERR_UNKNOWN` `0xFF`). Do not use
`0xFF` or any other existing `FN_ERR_*` value. The broker must not define
new FN constants except by adding them to `fujinet-nio.h`.

### 2.2 ABI forward compatibility

`fn_struct_size` is the version/size guard.

**v1 (current struct):** require exact size.
`fn_struct_size == sizeof(struct FujiNetNIORequest)`. Any other value is
`IOERR_BADLENGTH` + `FN_ERR_INVALID` without queuing.

**Once the ABI is extended** (new fields at the end), prefix compatibility:

| Caller `fn_struct_size` | Broker action |
|---|---|
| Less than the minimum supported prefix | Reject (`IOERR_BADLENGTH` + `FN_ERR_INVALID`) |
| Equal to a known older size | Accept if all fields required for that version are present; missing newer tail fields receive documented defaults |
| Greater than the driver-known size | Reject. An older driver cannot know whether new fields alter semantics |

One-way model: old caller → newer broker may be compatible; new caller → older
broker is rejected. Do not implement the compatibility table until the struct
actually grows.

`fn_flags` (and `fn_pad`) are reserved. They must be zero on submission;
non-zero is rejected per the BeginIO matrix in §2.1.

### 2.3 Other ABI invariants

Implications of §1 (opaque payload, backend-neutral ABI):

- No serial-specific fields (baud, SLIP, timers) on the public `IORequest`.
- No service-specific fields; DiskService/FileService live inside
  `fn_request_data`.
- The struct is identical for stream and packet-native backends.
- Base type is `IORequest`, not `IOStdReq` (`io_Length`/`io_Data`/`io_Actual`
  would collide with the explicit request/response fields).

---

## 3. `fn_transport_init / exchange / close` after the change

The Amiga platform transport shim (`src/platform/amiga/fn_transport.c`)
becomes a thin client of the broker. It no longer touches any physical device.

### Transport-shim ownership

- A `FujiNetNIORequest` belongs to one transport context.
- A transport context may have at most one exchange in flight.
- No `FujiNetNIORequest` may be concurrently used by two tasks.
- Different concurrently executing clients must use distinct transport
  contexts, unless a higher layer serializes all access to a shared context.
- The broker itself provides serialization between distinct client
  `IORequest`s. It does not make a shared shim `IORequest` safe.
- The Amiga transport shim must not use one globally shared `IORequest`
  across independent tasks.

Each independently usable Amiga transport context owns its own broker
`IORequest`, message port, and request/response state:

```
struct fn_amiga_transport {
    struct MsgPort *port;
    struct FujiNetNIORequest req;
    uint8_t device_open;
};
```

CLI programs may implement that as a process-local singleton: one context
per process is fine because Amiga CLI processes do not share that state
with other tasks. That is still one context, not a machine-global object.
`fujinet-disk.device` is resident and must own its own transport context
(not the CLI singleton). Its worker already serializes TD callers, so those
callers share the disk device's one context legally. Arbitrary tasks must
not share one `fn_transport` instance unless that higher-layer serialization
is explicit.

```
fn_transport_init(ctx)
    → CreateMsgPort → ctx->port; ctx->req.fn_io.mn_ReplyPort = ctx->port
    → OpenDevice(FUJINET_NIO_DEVICE_NAME, 0, &ctx->req.fn_io, 0)
    → ctx->device_open = 1

fn_transport_exchange_buffers(ctx, request, req_len, response, resp_cap, resp_len)
    → populate ctx->req (fn_request_data, lengths, response pointer)
    → DoIO(&ctx->req.fn_io)           // blocks until broker worker replies
    → if ctx->req.fn_io.io_Error != 0:
          *resp_len = 0
          return mapped local/device failure
          (must not return stale fn_nio_error from a previous request)
    → *resp_len = ctx->req.fn_response_length
    → return ctx->req.fn_nio_error

fn_transport_close(ctx)
    → if pending: WaitIO/AbortIO on ctx->req before CloseDevice
    → CloseDevice(&ctx->req.fn_io)
    → delete port; ctx->device_open = 0
```

`FN_AMIGA_EXPLICIT_LIFECYCLE` remains meaningful: the disk device manages
open/close of *its* context; CLI tools use `atexit(fn_transport_close)` on
the process-local context.

The `fn_transport_*` call sites stay the same. `fn_init`, `fn_raw_call`,
`fnsvc_*`, and `fn_disk_*` are unaffected as public APIs. The Amiga
implementation behind them must honor the ownership rule in this section.

---

## 4. How `fujinet-disk.device` submits NIO calls through the broker

The disk device is a lib client with its own transport context (§3). After
Stage 3 (backlog), that context opens the broker, not `serial.device`. The
worker serializes TD callers onto that one context. Stage 4 (backlog) removes
idle-close; the worker must not `fn_transport_close` when its FIFO empties.

---

## 5. Concurrency and lifetime rules

One FIFO worker, one atomic exchange per request, AbortIO never double-replies.
Transport-context ownership is in §3; this section is the broker's queue and
abort protocol.

### Atomicity invariant

`FUJINET_NIO_CMD_EXCHANGE` is one atomic NIO transaction: the complete send of
the request frame followed by the complete receipt of the response frame.

The broker worker never interleaves the send and receive phases of two
different callers' requests. While the worker is executing an exchange for
caller A — regardless of how long the remote device takes to respond — caller
B's request remains in the FIFO. Caller B's send does not begin until caller
A's response has been fully received and written to caller A's buffer.

This invariant must hold even when multiple Amiga tasks submit requests
concurrently. It is what makes the single worker essential: each physical
transport operation is serialized end-to-end, not interleaved between
callers.

### Multiple simultaneous callers

Each concurrently executing client uses a distinct transport context and
therefore a distinct `FujiNetNIORequest` plus its own request/response
buffers (§3). Multiple tasks may `DoIO` those distinct requests at the same
time. Exec's message queue serializes them: each `IORequest` is appended to
the FIFO inside `BeginIO` under `Disable`. The broker worker dequeues and
processes one at a time over a single open physical transport handle.

The broker serializes *between* those `IORequest`s. It does not serialize
two tasks that share one `FujiNetNIORequest`. Sharing a transport context
requires an explicit higher-layer lock or a single-threaded worker (as
`fujinet-disk.device` already has).

### IORequest buffer ownership

`fn_request_data` and `fn_response_data` remain caller-owned. The caller must
keep them valid and unmodified from `DoIO`/`SendIO` until `WaitIO`/reply.
Rules:
- Synchronous callers (`DoIO`): buffers are safe to read/free as soon as
  `DoIO` returns.
- Asynchronous callers (`SendIO`): buffers must not be read, written, or freed
  until `WaitIO` or `CheckIO` confirms the IORequest has been replied.
- The broker worker never copies or retains payload data beyond the duration of
  one exchange. It writes the response in place, sets `fn_response_length` and
  `fn_nio_error`, and calls `ReplyMsg`.

### Worker FIFO ordering

FIFO within unit 0. Requests are appended by `BeginIO` under `Disable`. The
worker processes requests head-to-tail with no priority. There is no priority
queuing within the broker; callers that need ordering guarantees must implement
them at a higher layer.

### ReplyMsg semantics

`ReplyMsg` is called by the worker after the exchange is complete and the
response buffer has been written. The physical transport remains open.
`ReplyMsg` is called exactly once per request; see §5.1 for abort races.

### Quick requests

`IOF_QUICK` is not supported for `FUJINET_NIO_CMD_EXCHANGE`. Every accepted
exchange requires the worker. **Before any immediate `ReplyMsg` from
`BeginIO` (reject or queue), clear `IOF_QUICK`.** Do not inline-complete
an exchange.

### Failed length and shim mapping

- On any failed exchange path, `fn_response_length` is 0 (and the shim
  writes `*resp_len = 0`).
- If `DoIO` returns with `io_Error != 0`, `fn_transport_exchange` returns a
  mapped local/device failure and must not return stale `fn_nio_error` from
  a previous request.

### 5.1 AbortIO and request state machine

A request is in one of four states:

```
  [queued] --dequeue--> [in-progress] --complete--> [completing] --ReplyMsg--> [replied]
      |
  AbortIO
      |
  [aborting] --ReplyMsg--> [replied]
```

**Queued state:** the request is in the FIFO, not yet dequeued by the worker.
`AbortIO` sets an abort flag on the request under `Disable` and attempts to
remove the request from the FIFO (also under `Disable`). If removal succeeds,
the broker applies AbortIO completion (§2.1): `fn_io.io_Error = IOERR_ABORTED`,
`fn_nio_error = FN_ERR_ABORTED`, `fn_response_length = 0`, and `ReplyMsg`
from `AbortIO`'s context. The request does not enter the worker.

**In-progress state:** the worker has dequeued the request and is executing the
exchange. `AbortIO` sets the abort flag but cannot interrupt an in-progress
exchange safely (mid-SLIP-frame interruption is not reliable on all backends).
The worker completes the physical exchange, then on transition to completing
state checks the abort flag. If set, it discards the physical response and
applies the same AbortIO completion (§2.1), including `fn_response_length = 0`,
before `ReplyMsg`. Abort is completion-status only; it is not a remote
rollback of the FujiBus transaction.

**Completing and replied states:** `AbortIO` after the worker has set the
completing state has no effect. `ReplyMsg` is called exactly once by the worker;
`AbortIO` never calls `ReplyMsg` if the worker has already taken responsibility
(flag-check protocol under `Disable` prevents double-reply).

The synchronization protocol between `AbortIO` and the worker is:
1. `AbortIO` and the worker both access the abort flag and queue manipulation
   under `Disable`/`Enable`.
2. After dequeue, the worker sets a "dispatched" flag under `Disable` before
   `Enable`. If `AbortIO` runs after that flag is set, it must not call
   `ReplyMsg`; the worker owns the request.
3. This prevents the race: AbortIO removes from FIFO and calls ReplyMsg;
   worker simultaneously dequeues and calls ReplyMsg → double completion.

---

## 6. Physical backend lifetime

Lazy-open, keep open, reopen only after a defined close (expunge or §7 reset).
`OpenCnt` hitting zero does not close the backend.

### Chosen policy: lazy-open, keep open, reopen only after close

The backend is normally opened lazily once (first `FUJINET_NIO_CMD_EXCHANGE`)
and kept open. “Open once” is that **steady-state** behavior, not a
resident-lifetime prohibition on `backend_open`. `backend_close` /
`backend_open` may occur again only for:

- explicit broker expunge/shutdown, or
- recovery after a backend failure that requires reset (see §7).

That is exclusive ownership of the transport, not a once-per-lifetime open
count. Reopen after a defined close gives recovery for serial now and for
removable or failable hardware later.

`lib_OpenCnt` reaching zero does **not** trigger a backend close.

### Expunge while work remains

Ordinary expunge must not abort or destroy live requests. If Amiga Exec has
delayed-expunge conventions, Stage 2 follows them. The semantic contract:

```
device_expunge():
  if lib_OpenCnt != 0:           defer/refuse
  if queue not empty:            defer/refuse
  if request in progress:        defer/refuse
  otherwise:
    stop worker
    close backend if open
    release worker/resources
    remove resident state
```

Active work finishes and clients close first. Expunge is not an implicit
`AbortIO` of the queue.

### Why this is a policy choice, not the only race-free option

The broker's single worker could in principle serialize backend reopen even
with multiple concurrent callers: a `lib_OpenCnt 0→1` transition that triggers
a reopen would be queued like any other operation, and the worker would reopen
before dispatching the first exchange. This is architecturally sound.

The resident-lifetime policy is chosen instead for the following reasons:

1. **Predictable latency.** Reopen on `lib_OpenCnt 0→1` adds backend
   initialization cost (serial port setup, baud rate negotiation) to the first
   exchange after an idle period. For packet hardware this may include driver
   load time. Resident-lifetime open avoids this entirely.
2. **Simpler error handling.** A backend that needs to be reopened after a
   transient error is already addressed by the error-recovery policy (§7).
   Tying reopen to `lib_OpenCnt` would create a second reopen path.
3. **Hardware exclusivity is expected.** Choosing to load the NIO broker is
   the user's declaration that the hardware belongs to FujiNet. Holding
   `serial.device` open for the broker's lifetime is the same model used by
   every other exclusive Amiga hardware driver (e.g. `printer.device` holds
   the parallel port while loaded).

**Trade-off:** the physical transport is unavailable to other software for the
broker's resident lifetime. For serial.device this means terminal emulators
cannot use the serial port while the broker is loaded. This is acceptable and
expected; the user unloads the broker to release the port. For Zorro hardware
there is no shared-resource conflict.

---

## 7. Physical backend error recovery

Reopen after a fatal/reset condition is allowed. Policy:

```
fatal/unrecoverable backend error
  → backend_close (reset hardware and framing/session state)
  → fail the current request (fn_nio_error = FN_ERR_TRANSPORT)
  → next exchange may attempt lazy backend_open
  → if reopen fails, fail that request too and leave the backend closed
  → repeat on each subsequent attempt (never permanently give up until expunge)
```

`backend_close` must leave framing and session state fully reset so the next
`backend_open` starts clean (§11). For the serial backend, Stage 2 must make
`fn_stream_session_close` / `fn_stream_session_open` (or an additional reset)
satisfy that; a dirty SLIP session after close is a backend defect, not a
reason to forbid reopen.

---

## 8. Broker residency and load ordering

The environment loads `fujinet-nio.device` before any `fn_transport_init`.
The library does not auto-load the broker.

### Who loads `fujinet-nio.device`

`fujinet-nio.device` must be resident in `DEVS:` before any component calls
`fn_transport_init`. The broker is not self-loading; `fn_transport_init`
expects `OpenDevice("fujinet-nio.device")` to succeed immediately.

Responsibility belongs to the environment that owns the startup:

| Context | Responsible loader |
|---|---|
| Amiga Startup-Sequence | `Startup-Sequence` loads the broker before any FujiNet tool |
| Amiberry integration tests | The test bootstrap script/sequence |
| User interactive shell | User types `LoadResident DEVS:fujinet-nio.device` or adds it to `S:User-Startup` |

`fujinet-nio-lib` does not attempt to load the broker automatically. Silently
loading resident devices from a library would be surprising and fragile on
AmigaOS (no error path, race with multiple initializers, no unload owner).

### Required ordering

```
1. fujinet-nio.device loaded (resident)
2. [optional] fujinet-disk.device loaded
3. Any application or tool calling fn_transport_init
```

`fujinet-disk.device` does not need to be loaded before `fujinet-nio.device`.
The disk device's first NIO call opens the broker lazily via `fn_transport_init`
and `fn_init`.

### What happens if the broker is absent

`OpenDevice("fujinet-nio.device")` returns `IOERR_OPENFAIL`.
`fn_transport_init` maps this to `FN_ERR_NOT_FOUND`. That is a transport-
unavailable error (broker not in `DEVS:`), not a crash or silent failure, and
not the same as `serial.device` busy.

### Test bootstrap

The Amiberry integration test harness must ensure `fujinet-nio.device` is
resident before any sequence step that triggers NIO. This is an environment
concern, not a test-logic concern; the test assertions and startup sequences
are unchanged (backlog Stage 3).

---

## 9. Dependency graph and SLIP/session code placement

Framing (`fn_slip.c`, `fn_session.c`) must compile into the broker serial
backend with no library-symbol dependency.

**Required before Stage 2:** remove `#include "fn_internal.h"` from
`fn_session.c`. Session framing does not use those library globals; the
include is leftover. After removal, framing is pure computation (no behavioral
change).

### Source organization after the fix

The broker serial backend compiles `fn_slip.c` and `fn_session.c` by path
from the library tree. No source file movement is required. If path-sharing
proves unwieldy, extract a `fujinet-nio-framing` static library later.

### No-cycle guarantee (after fix)

```
fn_slip.c, fn_session.c          (framing/session; after fix: no library deps)
  compiled separately into:
  ├── fujinet-nio-lib  (part of the library build)
  └── fujinet-nio.device serial backend  (referenced by path)

fujinet-nio-lib transport shim (fn_transport.c)
  → OpenDevice("fujinet-nio.device")   [runtime string, not a link dep]

fujinet-disk.device
  → fujinet-nio-lib              [link dep]
  [no dep on fujinet-nio.device source]
```

No code dependency cycle exists. The only reference from the library to the
broker is a runtime `OpenDevice` string.

---

## 10. Backend implementation and selection strategies

One serial-backed broker binary for the current phase. When a second backend
is needed, use Option A (separate binaries, identical public ABI) until
backends must coexist without a reboot.

### Near-term (single backend, current phase)

One broker binary compiled with the serial backend. Installed as
`DEVS:fujinet-nio.device`. No runtime selection; no loadable modules.

### When a second backend is needed

**Recommendation:** Option A — separate broker binaries, identical public ABI.
Move to Option B only if backends must coexist or be selected at runtime
without a reboot. Callers do not change if the strategy changes.

**Option A: multiple broker binaries, identical public ABI**

Separate binaries are built: `fujinet-nio-serial.device`,
`fujinet-nio-zorro.device`. The installer or user places the correct one in
`DEVS:` as `fujinet-nio.device`. All callers use
`OpenDevice("fujinet-nio.device")`; the struct and command code are identical.
Multiple variants can be packaged in an LHA archive with a selector script.

Advantages: each binary is self-contained; no dynamic loading complexity;
straightforward to build and test each variant independently.

Disadvantages: switching backends requires a reboot or explicit unload/load.

**Option B: one broker binary with a loadable backend module**

The broker opens a backend library (e.g.,
`LIBS:fujinet-serial-backend.library`) selected by a preference file. The
backend library exports a fixed callback table
(`init`, `open_physical`, `exchange`, `close_physical`).

Advantages: single broker binary; a backend can be swapped without replacing
the broker binary.

Disadvantages: more complexity; requires a stable backend callback ABI; two
installed files per configuration.

---

## 11. Internal physical-backend contract

The broker's internal backend interface is not part of the public ABI (callers
never see it). Serial baud, `serial.device` unit, `timer.device` unit, poll
interval, and exchange timeout are **serial-backend private configuration**
(named constants or config, not magic numbers, not public ABI). A Zorro
backend may have none of those concepts.

v1 C contract (Stage 2 may add a private context pointer without changing
semantics; do not add multi-adapter support before there is one adapter):

```c
uint8_t backend_open(void);

void backend_close(void);

uint8_t backend_exchange(
    const uint8_t *request,
    uint16_t request_len,
    uint8_t *response,
    uint16_t response_capacity,
    uint16_t *response_len
);
```

Do not pass broker/device objects into this interface unless implementation
proves they are necessary.

**`backend_open`**
- Opens and initializes the physical hardware resource.
- Performs configuration required to start clean.
- Returns `FN_OK` or an FN-space transport/setup error.
- Called when the backend is currently closed and an exchange requires it.
- Normally called once after broker startup (lazy, first exchange). That
  “once” is steady-state, not a lifetime cap.
- May be called again after `backend_close` during defined error recovery
  (§7) or after a failed open (backend stayed closed).
- Must never be called concurrently. Not called per-request while open.

**`backend_close`**
- Idempotent and safe when already closed.
- Releases the physical hardware resource if open.
- Leaves backend/session/framing state fully reset so a later `backend_open`
  starts clean.
- Called on expunge/shutdown or after a backend failure that requires reset
  (§7).

**`backend_exchange`**
- Called only while the backend is open.
- Exactly one complete request → response transaction. Framing is entirely
  inside this function (SLIP for stream; native packets otherwise).
- Sets `*response_len = 0` before doing work. On success, sets the actual
  length. The broker copies that to `fn_response_length`.
- Returns FN-space status (`FN_OK`, `FN_ERR_TRANSPORT`, `FN_ERR_TIMEOUT`,
  `FN_ERR_IO`, …).
- Must terminate in bounded time and return `FN_ERR_TIMEOUT` when the
  selected backend's response deadline is exceeded.
- Never retains caller buffers after return.
- The broker calls `ReplyMsg` only after this function returns.
- May be called again after it returns, but never concurrently.

### Invariants the contract enforces across backends

- **Service-agnostic.** Raw bytes in and out; no FujiBus or disk parsing.
- **Transport-neutral.** Stream backends apply SLIP; packet backends do not.
- **No disk semantics** in the backend interface.
- **Private backend state** between calls (partial frames are not the broker's).
- **Deterministic completion.** Bound time internally; do not block the FIFO
  forever.
