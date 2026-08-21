# FujiNet NIO Broker Architecture

*Status: design for review — not yet implemented*

This document defines the target architecture for the Amiga NIO transport
layer. The immediate motivation is a proven race condition between `FLS` and
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
  │  public, platform-agnostic service API                  │
  └───────────────────────┬────────────────────────────────┘
                          │ Amiga platform transport layer
                          │ (fn_transport_init/exchange/close)
  ┌───────────────────────▼────────────────────────────────┐
  │  fujinet-nio.device                                     │
  │  generic NIO broker / sole transport arbitrator         │
  │  one FIFO worker, service-agnostic, backend-neutral     │
  └────────┬───────────────────────────────────────────────┘
           │ backend interface (internal, not public ABI)
     ┌─────┴──────┬─────────────────────┐
     ▼            ▼                     ▼
  serial        Zorro              future hardware
  backend       backend               backend
  (owns         (owns                 (owns its
  serial.device) Zorro card)          resource)

  ┌───────────────────────────────────────────────────────┐
  │  fujinet-disk.device                                   │
  │  Amiga TD_* disk semantics only                        │
  │  client of fujinet-nio-lib (same path as applications) │
  └───────────────────────────────────────────────────────┘
```

### Dependency rules

| Component | May depend on | Must not depend on |
|---|---|---|
| Physical backend | exec.library, its own hardware | fujinet-disk.device, fujinet-nio-lib, service code |
| fujinet-nio.device | exec, selected backend | fujinet-disk.device, any service or disk abstraction |
| fujinet-nio-lib Amiga transport layer | fujinet-nio.device (via OpenDevice) | specific backends, serial.device directly |
| fujinet-disk.device | fujinet-nio-lib, exec | fujinet-nio.device directly, physical backends |
| Applications | fujinet-nio-lib | fujinet-nio.device internals, physical backends |

No component above the broker ever names, opens, or knows about a specific
physical transport. No component in or below the broker understands disk
sectors, FujiBus service IDs, or catalog semantics.

---

## 2. The `fujinet-nio.device` public IORequest ABI

The broker exposes exactly one logical command. It is deliberately opaque: the
broker does not interpret the NIO payload.

```c
/* DEVS:fujinet-nio.device  — public header */

#define FUJINET_NIO_DEVICE_NAME   "fujinet-nio.device"
#define FUJINET_NIO_DEVICE_UNIT   0

/* Command code */
#define FUJINET_NIO_CMD_EXCHANGE  (CMD_NONSTD + 0)

/* Error codes returned in fn_io_Error (mirrors fn error space) */
#define FUJINET_NIO_OK            0x00
#define FUJINET_NIO_ERR_TRANSPORT 0x10   /* physical layer failure */
#define FUJINET_NIO_ERR_TIMEOUT   0x11
#define FUJINET_NIO_ERR_ABORTED   0x12   /* AbortIO called before dispatch */

struct FujiNetNIORequest {
    struct IORequest fn_io;         /* standard Exec IORequest header      */

    /* Request payload — caller-owned; valid until ReplyMsg */
    APTR  fn_request_data;
    ULONG fn_request_length;

    /* Response buffer — caller-allocated; valid until ReplyMsg */
    APTR  fn_response_data;
    ULONG fn_response_capacity;

    /* Filled in by the broker on successful return */
    ULONG fn_response_length;

    /* FN-space error code; also mirrored into fn_io.io_Error */
    UBYTE fn_error;

    UBYTE fn_pad[3];                /* reserved; must be zero              */
};
```

### ABI invariants

- **No serial-specific fields.** Baud rate, parity, stop bits, SLIP markers,
  and all framing details are backend-internal.
- **No service-specific fields.** DiskService, FileService, and network
  protocol IDs are carried inside `fn_request_data` as opaque bytes.
- **A packet-native backend** (Zorro) receives the same struct, extracts the
  payload, and sends it natively without SLIP. The struct is identical.
- The payload is the already-encoded FujiBus frame. Framing (SLIP or
  equivalent) is the backend's responsibility.

---

## 3. `fn_transport_init / exchange / close` after the change

The Amiga platform transport layer (`src/platform/amiga/fn_transport.c`)
becomes a thin client of the broker. It no longer touches any physical device.

```
fn_transport_init()
    → OpenDevice(FUJINET_NIO_DEVICE_NAME, 0, &_broker_req, 0)
    → allocate FujiNetNIORequest, response buffer
    → _device_open = 1

fn_transport_exchange_buffers(request, req_len, response, resp_cap, resp_len)
    → populate _nio_req.fn_request_data / length / response fields
    → DoIO(&_nio_req)           // blocks until broker worker completes exchange
    → copy fn_response_length, return fn_error

fn_transport_close()
    → CloseDevice(&_broker_req)
    → free FujiNetNIORequest, response buffer
    → _device_open = 0
```

`FN_AMIGA_EXPLICIT_LIFECYCLE` remains meaningful: the disk device manages its
own `OpenDevice`/`CloseDevice` lifecycle on the broker; CLI tools use
`atexit(fn_transport_close)` as before.

The change is opaque to all callers of fn_transport_*. `fn_init`, `fn_raw_call`,
`fnsvc_*`, and `fn_disk_*` are entirely unaffected.

---

## 4. How `fujinet-disk.device` submits NIO calls through the broker

No structural change is needed on the disk device side. After Stage 3 of the
migration (see §10), `fn_transport_init` opens the broker instead of
serial.device. The disk device already calls `fn_init()` before each NIO
operation; `fn_init` calls `fn_transport_init`; `fn_transport_init` now opens
the broker. The disk device never learns that the broker exists.

The `FN_AMIGA_EXPLICIT_LIFECYCLE` path controls when the disk device opens and
closes the broker:

- **Open:** on the first NIO call from the worker (via `fn_init`), the
  broker's `OpenDevice` increments `lib_OpenCnt`. The broker's backend opens
  the physical transport lazily on first `FUJINET_NIO_CMD_EXCHANGE`.
- **Close:** when the disk device calls `fn_transport_close` (at
  `device_expunge` time, or when the worker decides to release), `CloseDevice`
  decrements `lib_OpenCnt`. The broker does not close the backend at this point
  (see §6).

As a consequence, the disk device's worker can drop the idle-close cycle
entirely. The worker need not call `fn_transport_close` when the FIFO empties
— transport lifetime is no longer coupled to request batches. The worker
becomes simpler: dequeue, call fn_init (no-op if open), exchange, ReplyMsg,
loop. There is no ReplyMsg ordering problem to solve.

---

## 5. Concurrency and lifetime rules

### Multiple simultaneous callers

Each caller allocates its own `FujiNetNIORequest` and its own response buffer
on its own stack or in its own memory. Multiple tasks may call `DoIO` on the
broker concurrently. Exec's message queue is the serialization mechanism: each
`IORequest` is appended to the FIFO in `BeginIO` order (under `Disable`). The
broker worker dequeues and processes one at a time. No caller requires any
knowledge of the others.

### IORequest buffer ownership

Buffers (`fn_request_data`, `fn_response_data`) are caller-owned. Ownership
passes to the broker at `SendIO`/`DoIO` and returns at `WaitIO`/reply. The
caller must not read, write, or free these buffers until the IORequest has been
replied. For synchronous callers (`DoIO`), this is automatic — `DoIO` returns
after the reply. Async callers (`SendIO`) must wait on the reply port before
touching the buffers.

The broker worker never copies or retains request or response data beyond the
duration of a single exchange. It holds a pointer, writes the response in
place, sets `fn_response_length`, sets `fn_error`, then calls `ReplyMsg`.

### Worker FIFO ordering

FIFO within a single unit (unit 0). Requests are appended by `BeginIO` under
`Disable` to prevent concurrent modification. The worker processes one request
from head-to-tail. There is no priority queueing within the broker; callers
that need priority must implement it at a higher layer.

### ReplyMsg semantics

The broker calls `ReplyMsg` after the exchange is complete and the response
buffer has been filled. The physical transport is still open when `ReplyMsg` is
called, and remains open afterward. There is no race window because the backend
is never closed in the request-completion path.

### Abort behaviour

`AbortIO` sets an abort flag on the request. If the request is still in the
FIFO (not yet dispatched), the worker sets `fn_error = FUJINET_NIO_ERR_ABORTED`
and `ReplyMsg` without performing the exchange. If the request is already being
processed (exchange in progress), the broker completes the current exchange
(mid-frame abort is not reliably safe on all backends), sets
`FUJINET_NIO_ERR_ABORTED`, and replies. The in-progress exchange result is
discarded. This follows the convention used by other Amiga streaming devices.

### Quick requests

`IOF_QUICK` is never set for `FUJINET_NIO_CMD_EXCHANGE`. All exchanges require
the worker task. `BeginIO` clears `IOF_QUICK` before queuing. This is the same
policy used by `fujinet-disk.device` today.

---

## 6. Physical backend lifetime

The backend lifetime is deliberately decoupled from `lib_OpenCnt`.

**Chosen policy: lazy-open on first exchange, close on expunge or unrecoverable error.**

The sequence is:

1. Broker is loaded (`InitResident` / `LoadSeg`). Backend is not yet opened.
2. First `FUJINET_NIO_CMD_EXCHANGE` arrives. Broker opens the backend (e.g.,
   calls `OpenDevice("serial.device")`). This is the one and only open. On
   success, `_backend_open = 1`.
3. All subsequent exchanges use the already-open backend. No open/close per
   request or per batch.
4. `lib_OpenCnt` goes to zero (all clients called `CloseDevice(broker)`).
   Backend remains open. `_backend_open` is unchanged.
5. A new client calls `OpenDevice(broker)`. `lib_OpenCnt` goes back up. The
   backend is already open; the first exchange proceeds immediately.
6. `device_expunge` is called (broker is about to be unloaded). Broker closes
   backend (`CloseDevice("serial.device")` etc.), frees backend resources.
   Unloads.

**Why not close at lib_OpenCnt == 0?**

If the backend is closed when the last client disconnects, and a new client
opens the broker before the backend close completes, or immediately after, the
race is simply moved up one level: two concurrent `OpenDevice(broker)` calls
can race on the backend open. Serial.device's exclusivity constraint applies at
the broker level too unless the backend is opened exactly once and kept open.

**Why not close on a timer?**

A timer-based close reintroduces a window — however small — between the close
and the next open. A sufficiently busy or unlucky system can hit it.

**Trade-off: the physical transport is held for the broker's resident lifetime.**

For serial.device this means: as long as `fujinet-nio.device` is loaded, the
serial port is in use. Applications that need the serial port for another
purpose (terminal emulators, etc.) will find it busy. This is the expected and
correct behaviour: loading the NIO broker is the user's declaration that the
serial port belongs to FujiNet. The user unloads the broker (or reboots) to
release it.

For Zorro hardware there is no shared-resource conflict; the Zorro backend owns
a card that nothing else needs. The lifetime policy is the same but the
practical impact is lower.

**Unrecoverable errors.** If the backend reports a fatal error (hardware not
responding, device removed), the broker sets `_backend_open = 0`, attempts
`CloseDevice` on the backend, and returns `FUJINET_NIO_ERR_TRANSPORT` on all
subsequent exchanges until expunge/reload.

---

## 7. Backend-neutral broker ABI

The broker ABI is defined solely by `struct FujiNetNIORequest` (§2) and the
`FUJINET_NIO_CMD_EXCHANGE` command code. The following details must remain
internal to the backend implementation:

| Detail | Stays inside |
|---|---|
| `OpenDevice("serial.device")` | serial backend |
| Baud rate / `io_Baud` | serial backend |
| SLIP framing, END/ESC bytes | serial backend |
| SDCMD_QUERY / CMD_READ / CMD_WRITE | serial backend |
| Timer-based polling | serial backend |
| `FN_TRANSPORT_WIRE_BUF_SIZE` | backend (wire buffer) |
| Zorro DMA descriptors | Zorro backend |
| Packet framing for packet-native hardware | packet backend |

A packet-native backend receives the encoded FujiBus payload in
`fn_request_data` and transmits it directly in one or more hardware packets.
It does not need to SLIP-encode or maintain a stream byte channel. The broker
struct and command code are identical regardless.

The session layer (`fn_stream_session_*`) is also a backend-internal detail: it
encapsulates SLIP framing for stream transports. A packet backend does not use
`fn_stream_session_*` at all; it operates directly on the FujiBus payload.

---

## 8. Backend implementation and selection strategies

**Near-term (one backend):** a single broker binary with the serial backend
compiled in. No runtime selection or loadable modules. The binary is installed
as `DEVS:fujinet-nio.device`.

**When a second backend is needed:**

*Option A — multiple broker binaries, same external ABI.*

Different binaries are compiled: `fujinet-nio-serial.device`,
`fujinet-nio-zorro.device`. The installer or the user places the correct one in
`DEVS:` as `fujinet-nio.device`. All callers use `OpenDevice("fujinet-nio.device")`;
the ABI is identical. Different binaries can be packaged together in an LHA
archive with a simple installer script.

Advantages: each binary is self-contained; no dynamic loading; straightforward
to build and test each variant independently.

Disadvantages: hot-swapping backends requires a reboot or explicit unload/load.

*Option B — one broker binary with a loadable backend module.*

The broker opens a backend library (e.g., `LIBS:fujinet-serial-backend.library`)
selected by a preference file or environment variable. The backend library
exports a fixed callback table (`init`, `open_physical`, `exchange`, `close_physical`).

Advantages: single broker binary; backend can in principle be swapped without
reloading the broker (though the physical transport would need a reset).

Disadvantages: more complexity; requires a stable backend callback ABI;
two installed files per configuration; the preference file must be managed.

**Recommendation:** implement Option A first. The binary-per-backend model is
simple, correct, and matches how most AmigaOS hardware drivers are distributed.
Move to Option B only if multiple backends need to be selectable at runtime
(e.g., detecting hardware automatically). The public broker ABI is identical
under both options, so callers do not change when switching strategies.

---

## 9. Dependency and circular-linking risks

```
fujinet-nio-backend-serial
    deps: exec.library, serial.device, timer.device
    no deps on: any FujiNet component

fujinet-nio.device  (broker)
    deps: exec.library, selected backend (compiled-in or loaded)
    no deps on: fujinet-disk.device, fujinet-nio-lib service layer

fujinet-nio-lib Amiga transport layer  (fn_transport.c)
    deps: exec.library (via OpenDevice/DoIO/CloseDevice on the broker)
    no deps on: serial.device, timer.device, or backend internals

fujinet-disk.device
    deps: exec.library, fujinet-nio-lib
    no deps on: fujinet-nio.device directly, any backend

Applications (FLS, fujinet-mount, diskinspect)
    deps: fujinet-nio-lib
    no deps on: fujinet-nio.device ABI directly, any backend
```

No cycles exist. The key guards:

- The broker must not call into service code. If it discovers it needs
  service-level logic, that logic belongs elsewhere.
- `fujinet-disk.device` must not `OpenDevice("fujinet-nio.device")` directly.
  It goes through `fn_transport_init` in the library, which does the open.
  This keeps the disk device decoupled from the broker name and ABI.
- Application code must never call `OpenDevice("fujinet-nio.device")` or
  `OpenDevice("serial.device")` directly. All NIO goes through `fn_init` /
  the library transport layer. Only the transport layer names the broker.

---

## 10. Staged migration plan

Each stage has a testable invariant. Stages may proceed in parallel where
dependencies allow.

### Stage 1 — Define the broker ABI (no code change)

Deliverables:
- `repos/fujinet-nio-driver/amiga/include/fujinet_nio_device.h` with
  `struct FujiNetNIORequest`, command codes, and error codes.
- `docs/amiga/nio-broker-architecture.md` (this document).

Testable invariant: the header compiles cleanly against the Amiga GCC toolchain
with no warnings.

### Stage 2 — Implement `fujinet-nio.device` (serial backend only)

Deliverables:
- New `repos/fujinet-nio-driver/amiga/nio.device/` directory.
- Broker device driver: `device_init`, `device_open`, `device_close`,
  `device_expunge`, `device_begin_io`, `device_abort_io`, FIFO worker.
- Serial backend module: refactored from `fn_transport.c`; owns serial.device
  for the broker's resident lifetime.
- Build system wires up `fujinet-nio.device` binary.

Testable invariant: a standalone test tool opens the broker, submits a
`FUJINET_NIO_CMD_EXCHANGE` with a known FujiBus frame, receives the correct
response, closes the broker. This can be validated in the Amiberry test rig
using FLS rewritten to use the broker directly (temporary test harness).

### Stage 3 — Re-route `fn_transport.c` through the broker

Deliverables:
- `fn_transport.c` (Amiga) rewritten: `fn_transport_init` opens the broker,
  `fn_transport_exchange_buffers` submits `FUJINET_NIO_CMD_EXCHANGE`,
  `fn_transport_close` closes the broker.
- No application or service code changes.

Testable invariant: **all existing Amiga integration tests pass unchanged**.
The test suite does not know about the broker; this is a pure transport
re-plumbing. In particular, `diskdevice-inspect-catalog` should now pass
reliably because the broker serializes FLS and the disk device.

At this stage `OpenDevice("serial.device")` no longer appears anywhere except
inside the broker's serial backend.

### Stage 4 — Simplify `fujinet-disk.device` worker

Deliverables:
- Remove the idle-close cycle from `device_worker_entry`. The worker loop
  becomes: dequeue → fn_init (no-op if broker already open) → exchange →
  set io_Error → ReplyMsg → continue.
- Remove `fn_transport_close` from all worker paths.
- The disk device calls `fn_transport_close` only in `device_expunge` (or
  `device_close` when `lib_OpenCnt` reaches zero, whichever is appropriate).

Testable invariant: `diskdevice-inspect-catalog` continues to pass; the
worker code is visibly simpler; no test requires the old idle-close behaviour.

Remove the debug instrumentation added to `fn_transport.c` in this stage.

### Stage 5 — Validate backend neutrality with a stub backend

Deliverables:
- A loopback/stub broker variant that responds to NIO exchanges from a static
  response table. No serial.device involved.
- The full integration suite runs against the stub broker.

Testable invariant: all tests that do not require a real NIO device (unit-level,
catalog, mount/unmount metadata) pass against the stub. This proves that no
service, disk device, or application code has any latent dependency on
serial.device, Amiberry's PTY, or any specific backend.

### Stage 6 — Future backend (Zorro or other)

Deliverables:
- A new backend module implementing the backend interface.
- A new broker binary (`fujinet-nio-zorro.device` installed as
  `fujinet-nio.device` on the target system).
- No changes to fujinet-disk.device, fujinet-nio-lib, or applications.

Testable invariant: the full integration suite (from Stage 5) passes against
the new backend. Backend parity with the serial baseline is a requirement
before a new backend is considered production-ready.

---

## 11. Integration suite portability across backends

The integration suite (`integration-tests/amiberry/`) must remain unchanged
across backends. The only backend-specific configuration lives in the
environment layer (`local/amiga.env` or equivalent pytest fixtures). The
startup sequences (`.sequence` files), test assertions (`.py` files), and
expected result patterns are identical for all backends.

When a new backend is introduced:

1. Provide an environment configuration that selects the new broker binary.
2. Run the full suite. Failures indicate backend-specific regressions.
3. The serial baseline suite is the reference; a new backend must achieve
   parity before merging.

Test isolation between backends is achieved by selecting different Amiberry
configurations (different HDF sets, different ROM paths) via the existing
`configs/amiga/` YAML infrastructure. No test file needs a backend-specific
branch.

---

## Open questions for review

1. **broker device name**: `fujinet-nio.device` or a shorter name? AmigaOS
   device names are global strings; collision risk is low but worth confirming.

2. **Unit numbering**: unit 0 is the natural default. Are multiple units needed
   for multi-adapter configurations (e.g., two FujiNet devices in one Amiga)?
   Unit > 0 could select a second physical adapter. Not required for current
   hardware; design should not preclude it.

3. **`fn_transport_close` from the disk device**: at `device_expunge` the
   broker's lib_OpenCnt may or may not have been decremented already by the
   disk device's explicit lifecycle. The interaction with Exec's expunge
   sequencing should be reviewed when Stage 4 is implemented.

4. **Error recovery**: if the broker's backend fails mid-session (cable
   removed, emulator restart), the broker should return
   `FUJINET_NIO_ERR_TRANSPORT` and attempt a backend re-open on the next
   request. Define a re-open retry limit or let it remain failed until the
   broker is reloaded. This policy should be specified before Stage 2 is
   complete.
