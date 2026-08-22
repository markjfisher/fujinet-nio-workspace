# FujiNet NIO Broker Architecture

*Status: design for review — not yet implemented*

This document defines the target architecture for the Amiga NIO transport
layer. The immediate motivation is a proven race condition between FLS and
`fujinet-disk.device` both independently calling `OpenDevice("serial.device")`.
The deeper motivation is that serial.device is a temporary proving-ground
transport; Zorro and other packet-native backends must be addable without
touching any service, disk device, or application code.

---

## 1. Responsibilities and dependency direction

```
  ┌────────────────────────────────────────────────────────┐
  │  Applications  (FLS, fujinet-mount, future NIO tools)  │
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

  ┌────────────────────────────────────────────────────────┐
  │  fujinet-disk.device                                   │
  │  Amiga TD_* disk semantics only                        │
  │  client of fujinet-nio-lib (same path as applications) │
  └────────────────────────────────────────────────────────┘
```

### Component responsibilities

**fujinet-nio.device (broker)**
- Sole Amiga owner/arbitrator of the selected physical FujiNet transport.
- Serialises all NIO exchanges from any number of concurrent callers through
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
- `fn_transport_init` opens the broker; `fn_transport_exchange_buffers`
  submits one `FujiNetNIORequest`; `fn_transport_close` closes the broker.
- All other library code (service, packet, session) is unchanged.

**fujinet-disk.device**
- Retains only Amiga TD_* disk semantics.
- Uses `fn_init` / `fn_transport_*` exactly as it does today. The transport
  shim change is transparent.
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
     * Standard Exec IORequest header. io_Command must be
     * FUJINET_NIO_CMD_EXCHANGE. The broker worker never supports IOF_QUICK
     * for this command; BeginIO clears it before queuing.
     *
     * io_Error carries native Exec/device-level completion errors only
     * (e.g. IOERR_ABORTED, IOERR_NOCMD). It is set to zero on a successful
     * dispatch to the worker, regardless of the NIO-level outcome.
     * Do not read NIO protocol results from io_Error; use fn_nio_error.
     */
    struct IORequest fn_io;

    /*
     * ABI version/size guard. Caller must set this to FUJINET_NIO_REQUEST_SIZE
     * before submitting. The broker rejects requests with a mismatched size
     * with io_Error = IOERR_BADLENGTH and fn_nio_error = FN_ERR_INVALID.
     * This allows the struct to grow in future versions without silent
     * misinterpretation by older callers or older brokers.
     */
    UWORD        fn_struct_size;

    UWORD        fn_flags;          /* reserved; must be zero */

    /*
     * NIO request frame — a complete, already-encoded FujiBus frame ready to
     * be handed to the physical transport. The broker does not construct,
     * inspect, or modify the frame. For stream backends (serial) the backend
     * applies SLIP framing around this payload. For packet-native backends
     * (Zorro) the payload is delivered directly in the hardware packet format.
     *
     * Caller owns this buffer. It must remain valid and unmodified from
     * the time DoIO/SendIO is called until the IORequest is replied.
     */
    const UBYTE *fn_request_data;
    UWORD        fn_request_length;  /* bounded by FN_MAX_PACKET_SIZE (≤ 512 today) */

    /*
     * Response buffer, caller-allocated. On a successful NIO exchange the
     * broker writes the decoded response payload here (framing stripped).
     * The caller must supply fn_response_capacity >= the maximum expected
     * response size. fn_response_length is set by the broker and is valid
     * only when fn_nio_error == FN_OK.
     *
     * Caller owns this buffer. The same lifetime rule as fn_request_data
     * applies.
     */
    UBYTE       *fn_response_data;
    UWORD        fn_response_capacity;
    UWORD        fn_response_length;

    /*
     * FN-space result code (see §2.1). Carries NIO/FujiBus protocol-level
     * errors. Set by the broker worker before ReplyMsg. Independent of
     * fn_io.io_Error; the two fields cover different error domains.
     */
    UBYTE        fn_nio_error;

    UBYTE        fn_pad[3];         /* alignment; must be zero */
};
```

`UWORD` (16-bit) is used for lengths because FujiBus frames are bounded by
`FN_MAX_PACKET_SIZE` (currently 512 bytes). If that bound is ever raised above
65535 the fields must become `ULONG`; that is a future ABI version bump tracked
through `fn_struct_size`.

### 2.1 Error domain

The struct carries **two independent error fields** with different domains.
Conflating them has caused real debugging confusion in this project and must not
happen again.

**`fn_io.io_Error` — native Exec/device errors only**

Set by the broker to reflect the outcome of the Exec dispatch itself:

| Value | Meaning |
|---|---|
| 0 | Dispatch succeeded; check `fn_nio_error` for NIO outcome |
| `IOERR_ABORTED` (2) | Request was aborted before or during processing |
| `IOERR_NOCMD` (3) | Unrecognised command (not `FUJINET_NIO_CMD_EXCHANGE`) |
| `IOERR_BADLENGTH` (5) | `fn_struct_size` does not match the broker's ABI version |

The broker does **not** copy `fn_nio_error` into `io_Error`. Callers must not
read `io_Error` to determine whether an NIO exchange succeeded or failed.

**`fn_nio_error` — FN-space protocol errors**

Carries the outcome of the NIO exchange itself, using codes from `fujinet-nio.h`.
Valid only when `io_Error == 0` (dispatch succeeded).

| Symbol | Value | Meaning in broker context |
|---|---|---|
| `FN_OK` | 0x00 | Exchange completed, response written to buffer |
| `FN_ERR_TRANSPORT` | 0x10 | Physical layer failure (backend error) |
| `FN_ERR_TIMEOUT` | 0x06 | No response received within the exchange timeout |
| `FN_ERR_IO` | 0x05 | Backend setup or IO error |
| `FN_ERR_INVALID` | 0x02 | `fn_struct_size` mismatch or reserved fields non-zero |

**TODO before Stage 1:** `FN_ERR_ABORTED` does not exist in `fujinet-nio.h`.
Add it with a value outside the current `0x00`–`0x12` range. Until then,
`AbortIO` on a queued request sets `io_Error = IOERR_ABORTED` and
`fn_nio_error = FN_ERR_TRANSPORT` as a placeholder.

The broker must not define new FN constants without coordinating with
`fujinet-nio.h` to prevent future collisions.

### 2.2 ABI forward compatibility

`fn_struct_size` is the version/size guard. The protocol is:
- Caller sets `fn_struct_size = sizeof(struct FujiNetNIORequest)` before
  `DoIO`. This encodes the ABI version the caller was compiled against.
- The broker checks this field in `BeginIO`. If it does not match the
  broker's compiled size, the broker sets `io_Error = IOERR_BADLENGTH` and
  `fn_nio_error = FN_ERR_INVALID` and replies immediately without queuing.
- When the struct grows (new fields at the end), callers compiled against the
  old header have a smaller `fn_struct_size`; the broker can detect this and
  either reject or apply defaults for the new fields. The exact policy is
  defined at the time of each extension.
- `fn_flags` is reserved for future per-request flags (e.g. priority hints,
  timeout overrides). Must be zero on submission; broker rejects non-zero with
  `IOERR_BADLENGTH`.

### 2.3 Other ABI invariants

- No serial-specific fields. Baud rate, parity, stop bits, SLIP markers, timer
  polling — all backend-internal.
- No service-specific fields. DiskService, FileService, and network protocol
  identifiers are carried inside `fn_request_data` as opaque bytes.
- A packet-native backend receives the same struct, extracts the payload, and
  transmits it natively without SLIP. The struct is identical across all
  backends.
- `IORequest` (not `IOStdReq`) is the base because the broker does not use
  `io_Length`/`io_Data`/`io_Actual`. Those standard fields conflict in naming
  with the explicit request/response fields and would add confusion.

---

## 3. `fn_transport_init / exchange / close` after the change

The Amiga platform transport shim (`src/platform/amiga/fn_transport.c`)
becomes a thin client of the broker. It no longer touches any physical device.

```
fn_transport_init()
    → allocate FujiNetNIORequest and a response buffer
    → OpenDevice(FUJINET_NIO_DEVICE_NAME, 0, &_broker_req.fn_io, 0)
    → _device_open = 1

fn_transport_exchange_buffers(request, req_len, response, resp_cap, resp_len)
    → populate _nio_req fields (fn_request_data, lengths, response pointer)
    → DoIO(&_nio_req.fn_io)           // blocks until broker worker replies
    → *resp_len = _nio_req.fn_response_length
    → return _nio_req.fn_nio_error

fn_transport_close()
    → CloseDevice(&_broker_req.fn_io)
    → free FujiNetNIORequest and response buffer
    → _device_open = 0
```

`FN_AMIGA_EXPLICIT_LIFECYCLE` remains meaningful: the disk device manages its
own open/close lifecycle on the broker; CLI tools use `atexit(fn_transport_close)`.

The change is transparent to all callers of `fn_transport_*`. `fn_init`,
`fn_raw_call`, `fnsvc_*`, and `fn_disk_*` are unaffected.

---

## 4. How `fujinet-disk.device` submits NIO calls through the broker

No structural change is needed. After Stage 3 of the migration (see §10),
`fn_transport_init` opens the broker instead of `serial.device`. The disk
device already calls `fn_init()` before each NIO operation; `fn_init` calls
`fn_transport_init`; `fn_transport_init` now opens the broker. The disk device
never learns that the broker exists.

The disk device's worker loop can then be simplified (Stage 4): the idle-close
cycle — `fn_transport_close` when the FIFO empties — is no longer needed.
The broker keeps the physical transport open regardless of FIFO state. The
worker becomes: dequeue → `fn_init` (no-op if already open) → exchange →
set `io_Error` → `ReplyMsg` → loop. The `ReplyMsg`-ordering race is
eliminated because the transport is never closed mid-batch.

---

## 5. Concurrency and lifetime rules

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
transport operation is serialised end-to-end, not merely round-robined between
callers.

### Multiple simultaneous callers

Each caller allocates its own `FujiNetNIORequest` and its own
request/response buffers (typically on its stack or in process memory).
Multiple tasks may call `DoIO` on the broker simultaneously. Exec's message
queue serialises them: each `IORequest` is appended to the FIFO inside
`BeginIO` under `Disable`. The broker worker dequeues and processes one at a
time over a single open physical transport handle. No caller requires knowledge
of the others, and no semaphore or explicit coordination is needed at the
caller level.

### IORequest buffer ownership

`fn_request_data` and `fn_response_data` are caller-owned. Ownership passes
to the broker at `DoIO`/`SendIO` and returns at `WaitIO`/reply. Rules:
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

`IOF_QUICK` is not supported for `FUJINET_NIO_CMD_EXCHANGE`. Every exchange
requires the worker. `BeginIO` clears `IOF_QUICK` before queuing.

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
the broker sets `fn_nio_error` to `FN_ERR_TRANSPORT` (TODO: FN_ERR_ABORTED per
§2.1), sets `io_Error` to the same, and calls `ReplyMsg` from `AbortIO`'s
context. The request does not enter the worker.

**In-progress state:** the worker has dequeued the request and is executing the
exchange. `AbortIO` sets the abort flag but cannot interrupt an in-progress
exchange safely (mid-SLIP-frame interruption is not reliable on all backends).
The worker completes the physical exchange, then on transition to completing
state checks the abort flag. If set, it overwrites the result with the abort
error code and calls `ReplyMsg`. The physical response data is discarded.

**Completing and replied states:** `AbortIO` after the worker has set the
completing state has no effect. `ReplyMsg` is called exactly once by the worker;
`AbortIO` never calls `ReplyMsg` if the worker has already taken responsibility
(flag-check protocol under `Disable` prevents double-reply).

The synchronization protocol between `AbortIO` and the worker is:
1. `AbortIO` and the worker both access the abort flag and queue manipulation
   under `Disable`/`Enable`.
2. After dequeue, the worker sets a "dispatched" flag under `Disable` before
   `Enable`. `AbortIO` that arrives after seeing "dispatched" knows the worker
   owns the request and will not call `ReplyMsg` itself.
3. This prevents the race: AbortIO removes from FIFO and calls ReplyMsg;
   worker simultaneously dequeues and calls ReplyMsg → double completion.

---

## 6. Physical backend lifetime

### Chosen policy: lazy-open on first exchange, close on expunge

The backend is opened the first time `FUJINET_NIO_CMD_EXCHANGE` is received.
After that it remains open for the broker's resident lifetime. It is closed
only when:
- `device_expunge` is called (broker about to be unloaded), or
- the backend reports an unrecoverable error (see §7).

`lib_OpenCnt` reaching zero does **not** trigger a backend close.

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

**Unresolved: mark as prerequisite for Stage 2 completion.**

The draft had two contradictory statements. The contradiction is resolved by
leaving the policy open, because the right choice depends on whether
`fn_session` / SLIP framing can recover reliably after a mid-exchange failure.

The candidate policy is:

```
fatal/unrecoverable backend error
  → close/reset backend (CloseDevice serial etc.)
  → fail the current request (fn_nio_error = FN_ERR_TRANSPORT)
  → on next exchange attempt, one controlled lazy-reopen attempt
  → if reopen fails, fail that request too and stay in failed state
  → repeat on each subsequent attempt (never permanently give up until expunge)
```

This is reasonable if `fn_stream_session_close` + `fn_stream_session_open`
correctly resets SLIP framing and any pending partial frame state. If partial
state is not cleanly reset, a reopen attempt could corrupt the next exchange.

**TODO (Stage 2 prerequisite):** audit `fn_stream_session_close` and
`fn_stream_session_open` to confirm whether they reset all framing state. If
yes, adopt the candidate policy. If not, document what additional reset is
required, or make permanent failure (until expunge/reload) the policy.

---

## 8. Broker residency and load ordering

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
AmigaOS (no error path, race with multiple initialisers, no unload owner).

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
`fn_transport_init` maps this to `FN_ERR_NOT_FOUND` and returns it to the
caller. The caller (application or disk device) sees the same error it would
have seen if serial.device were busy — a meaningful transport-unavailable
error, not a crash or silent failure.

### Test bootstrap

The Amiberry integration test harness must ensure `fujinet-nio.device` is
resident before any sequence step that triggers NIO. This is an environment
concern, not a test-logic concern; the test assertions and startup sequences
are unchanged (see §10 Stage 3).

---

## 9. Dependency graph and SLIP/session code placement

### Current source locations

`fn_slip.c` and `fn_session.c` live in
`repos/fujinet-nio-lib/src/common/` and are compiled into the amiga library
(`COMMON_SRCS_DEFAULT`). The Amiga platform transport (`fn_transport.c`) uses
`fn_stream_session_t` and the stream-session API directly.

The serial backend inside `fujinet-nio.device` also needs SLIP framing and the
stream session, which could create a dependency cycle. The actual dependency
chain was inspected:

**`fn_slip.c`**
- `#include "fn_protocol.h"` → `#include "fujinet-nio.h"` → `<stdint.h>`
- No reference to any library-level symbol. Clean.

**`fn_session.c`**
- `#include "fn_session.h"` → `<stdint.h>` only
- `#include "fujinet-nio.h"` → `<stdint.h>` only
- `#include "fn_protocol.h"` → as above
- `#include "fn_internal.h"` → declares `_fn_sessions[]`, `_fn_initialized`,
  `_fn_req_buf[]`, `_fn_resp_buf[]`, `fn_transport_ctx_t`, etc.

**`fn_internal.h` is the problem.** It includes declarations for library-level
globals that are defined in other library objects (`fn_state.c`, etc.). If the
broker's serial backend compiles `fn_session.c` as-is, those `extern`
declarations do not create linker errors by themselves — the linker only
complains when a definition is missing and the symbol is actually referenced.
Inspection of `fn_session.c` confirms that the session framing code
(`write_frame`, `read_frame`, `fn_stream_session_*`) does not reference any
symbol declared in `fn_internal.h`. The include appears to be a leftover from
an earlier refactor.

**Required fix before Stage 2:** remove the `#include "fn_internal.h"` line
from `fn_session.c`. This is a one-line change with no behavioural effect and
eliminates the dependency on library-level globals at the header level. After
this change the framing/session code has no dependency on any library service
or transport symbol.

### Source organisation after the fix

The broker's serial backend compiles `fn_slip.c` and `fn_session.c` directly
(referenced by path from the broker's build, not via the library's build
target). The framing code is pure computation with no library-level side
effects.

No source file movement is required. The build system for `fujinet-nio.device`
specifies exactly which source files it compiles. If sharing source files by
path between two build trees proves unwieldy, extracting a
`fujinet-nio-framing` static library is the appropriate solution — deferred
until the path-sharing approach proves impractical.

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

### Near-term (single backend, current phase)

One broker binary compiled with the serial backend. Installed as
`DEVS:fujinet-nio.device`. No runtime selection; no loadable modules.

### When a second backend is needed

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

Advantages: single broker binary; backend theoretically swappable without
replacing the broker binary.

Disadvantages: more complexity; requires a stable backend callback ABI; two
installed files per configuration.

**Recommendation:** implement Option A. It is simpler, correct, and matches
how most AmigaOS hardware drivers are distributed. Move to Option B only if
multiple backends need to coexist or be selected at runtime without a reboot.
The public broker ABI is identical under both options; callers do not change
if the strategy changes.

---

## 11. Internal physical-backend contract

The broker's internal backend interface is not part of the public ABI (callers
never see it), but its semantics must be fixed now so that both a stream/SLIP
backend (serial) and a packet-native backend (Zorro, floppy) can implement it
without requiring changes to the broker or to any caller.

### Semantic contract

A backend implements exactly three operations:

**`backend_open()`**
- Opens and initialises the physical hardware resource (e.g. `OpenDevice`,
  memory-mapped register setup).
- Performs any one-time configuration (baud rate, buffer allocation, DMA
  setup).
- Returns success or an FN-space error code.
- Called at most once during the broker's resident lifetime (lazy, on first
  exchange). Not called per-request.

**`backend_close()`**
- Releases the physical hardware resource.
- Resets all internal framing/session state so that a subsequent
  `backend_open()` starts clean.
- Called on expunge or after an unrecoverable error.

**`backend_exchange(request, request_len, response, response_capacity, response_len_out)`**
- Performs one complete, atomic NIO transaction:
  sends the entire `request` buffer to the remote device, then receives the
  complete response into `response`. Framing (SLIP encoding/decoding for
  stream backends; native packet format for packet backends) is handled
  entirely within this function.
- Sets `*response_len_out` on success.
- Returns an FN-space error code (`FN_OK`, `FN_ERR_TRANSPORT`,
  `FN_ERR_TIMEOUT`, `FN_ERR_IO`).
- **Must not return until the exchange is complete or has definitively failed.**
  The broker calls `ReplyMsg` only after this function returns.
- **Must be re-entrant across calls but not concurrent.** The broker worker
  guarantees it is never called from two threads simultaneously.

### Invariants the contract enforces across backends

- **Service-agnostic.** The exchange function receives and returns raw bytes.
  It does not parse FujiBus headers, service IDs, or disk geometry.
- **Transport-neutral.** A stream backend (serial) applies SLIP; a
  packet-native backend does not. The contract imposes no framing assumption.
- **No disk semantics.** No command codes, unit numbers, or catalog state
  appear in the backend interface.
- **Stateless between calls from the broker's perspective.** Internal state
  (partial frames, buffer offsets) is the backend's private concern.
- **Deterministic completion.** The backend must time out internally rather
  than blocking indefinitely, so the broker's FIFO always makes forward
  progress.

The concrete C function signatures will be defined at Stage 2. The above
semantic contract is fixed.
