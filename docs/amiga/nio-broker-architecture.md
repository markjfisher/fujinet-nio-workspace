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
  │  public, platform-agnostic service API                  │
  └───────────────────────┬────────────────────────────────┘
                          │ Amiga platform transport shim
                          │ (fn_transport_init/exchange/close)
  ┌───────────────────────▼────────────────────────────────┐
  │  fujinet-nio.device                                     │
  │  generic NIO broker / sole transport arbitrator         │
  │  one FIFO worker, service-agnostic, backend-neutral     │
  └────────┬───────────────────────────────────────────────┘
           │ internal backend interface (not public ABI)
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

struct FujiNetNIORequest {
    /*
     * Standard Exec IORequest header. io_Command must be
     * FUJINET_NIO_CMD_EXCHANGE. The broker worker never supports IOF_QUICK
     * for this command; BeginIO clears it before queuing.
     */
    struct IORequest fn_io;

    /*
     * NIO request frame — a complete, already-encoded FujiBus frame ready to
     * be handed to the physical transport. The broker does not construct,
     * inspect, or modify the frame. For stream backends this is the
     * pre-SLIP-encoded payload; the backend applies SLIP framing. For
     * packet-native backends this is the FujiBus payload delivered directly.
     *
     * Caller owns this buffer. It must remain valid and unmodified from
     * the time DoIO/SendIO is called until the IORequest is replied.
     */
    const UBYTE *fn_request_data;
    UWORD        fn_request_length;  /* frames are bounded by FN_MAX_PACKET_SIZE */

    /*
     * Response buffer, caller-allocated. On a successful exchange the broker
     * writes the decoded response payload here. The caller must supply
     * fn_response_capacity >= the maximum expected response size.
     *
     * Caller owns this buffer. The same lifetime rule as fn_request_data
     * applies.
     */
    UBYTE       *fn_response_data;
    UWORD        fn_response_capacity;
    UWORD        fn_response_length; /* set by broker; valid only when fn_nio_error == 0 */

    /*
     * FN-space result code (see §2.1). Populated by the broker worker before
     * ReplyMsg. fn_io.io_Error is set to the same value for compatibility with
     * callers that only check io_Error.
     */
    UBYTE        fn_nio_error;

    UBYTE        fn_reserved[3];    /* must be zero on submission */
};
```

`UWORD` (16-bit) is used for lengths because FujiBus frames are bounded by
`FN_MAX_PACKET_SIZE` (currently 512 bytes). If that bound is ever raised above
65535 the field must become `ULONG`; that is a future ABI version bump.

### 2.1 Error domain

The `fn_nio_error` field carries **FN-space error codes from `fujinet-nio.h`**,
not native Exec `io_Error` values. This is a deliberate split: the broker's
`io_Error` carries the same FN value (for callers that only check `io_Error`),
but there is no conflation with Exec error codes such as `IOERR_OPENFAIL = 1`
or `IOERR_ABORTED = 2`.

Relevant existing FN codes (from `fujinet-nio.h`):

| Symbol | Value | Meaning in broker context |
|---|---|---|
| `FN_OK` | 0x00 | Exchange completed successfully |
| `FN_ERR_TRANSPORT` | 0x10 | Physical layer failure (backend error) |
| `FN_ERR_TIMEOUT` | 0x06 | Exchange timed out waiting for response |
| `FN_ERR_IO` | 0x05 | Backend setup/IO error (not a framing error) |

The broker must not define new constants in the `0x01`–`0x12` range without
auditing `fujinet-nio.h`. A future broker-specific extension range should be
coordinated with that header to prevent collision. `FN_ERR_ABORTED` does not
currently exist in the FN error space; **TODO before Stage 2**: either add it
to `fujinet-nio.h` with a value outside the current range, or document which
existing code a caller should expect when `AbortIO` fires.

The `fn_reserved` bytes must be zeroed on submission. A future minor version
may place a flags or version field there; the broker rejects non-zero values
with `FN_ERR_INVALID` to avoid silent misinterpretation.

### 2.2 ABI invariants

- No serial-specific fields. Baud rate, parity, stop bits, SLIP markers, timer
  polling — all backend-internal.
- No service-specific fields. DiskService, FileService, and network protocol
  identifiers are carried inside `fn_request_data` as opaque bytes.
- A packet-native backend receives the same struct, extracts the payload, and
  transmits it natively without SLIP. The struct is identical across all
  backends.
- `IORequest` (not `IOStdReq`) is the base because the broker does not use
  `io_Length`/`io_Data`/`io_Actual` — those names conflict with the explicit
  request/response fields and would add confusion. The broker's fields are
  explicit members of `FujiNetNIORequest`.

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
(`COMMON_SRCS_DEFAULT`). The current Amiga platform transport
(`fn_transport.c`) uses `fn_stream_session_t` and the session API directly.

The serial backend inside `fujinet-nio.device` also needs SLIP framing and the
stream session. This creates a potential dependency cycle:

```
fujinet-nio.device
    → needs fn_slip.c, fn_session.c        ← framing/session code
    → those files include fn_protocol.h, fujinet-nio.h    ← error codes, basic types
    → those headers do NOT pull in fn_init, fn_raw, fn_packet, or service code
```

The cycle does **not** exist provided the serial backend links only the framing
object files and does not link the full fujinet-nio-lib library. Specifically:

- **Safe to link into the backend**: `fn_slip.o`, `fn_session.o`,
  `fn_protocol.h` constants.
- **Must not link into the backend**: `fn_raw.o`, `fn_init.o`, `fn_packet*.o`,
  `fn_session.o` if it pulls in service state — confirm at Stage 2.
- **The transport shim** (`fn_transport.c`) links against the full
  fujinet-nio-lib, which is correct — it is part of that library.

### Required source organisation

The broker's serial backend should be built as a separate compilation unit
that compiles `fn_slip.c` and `fn_session.c` directly (or a copy/symlink
under the broker's source tree) without inheriting the full library build.
The framing code is pure computation with no library-level side effects.

**No source movement is required for Stage 1 or Stage 2.** The build system
for `fujinet-nio.device` should specify exactly which source files it compiles.
If it becomes unwieldy to share source files between the library and the broker
build, extracting a `fujinet-nio-framing` static library is the appropriate
solution — but this is deferred until the duplicate-source approach proves
impractical.

### No-cycle guarantee (after migration)

```
fn_slip.c, fn_session.c          (framing/session, no service deps)
  ↑ compiled into both:
fujinet-nio-lib (serial backend role)
fujinet-nio.device serial backend (directly)

fujinet-nio-lib transport shim   (fn_transport.c)
  → OpenDevice("fujinet-nio.device")   [Exec call, not a code dep]

fujinet-disk.device
  → fujinet-nio-lib              [link dep]
  [no dep on fujinet-nio.device source]
```

No code dependency cycle exists. The only reference from the library to the
broker is a runtime `OpenDevice` string — exactly the same way the library
currently references `"serial.device"`.

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

## 11. Staged migration plan

Each stage ends with a testable invariant. Stages that share no dependency may
proceed in parallel.

### Stage 0 — Prerequisite: `fujinet-nio.device` broker load in test bootstrap

Before any code change, update the Amiberry test harness to load
`fujinet-nio.device` in the startup sequence and in the integration-test
bootstrap. This establishes the load-ordering contract independently of the
implementation work.

**Testable invariant:** the bootstrap completes without error even before
`fujinet-nio.device` exists (by stub/placeholder). All existing tests continue
to pass because no code path yet uses the broker.

### Stage 1 — Define public ABI

Deliverables:
- `repos/fujinet-nio-driver/amiga/include/fujinet_nio_device.h` with
  `struct FujiNetNIORequest`, `FUJINET_NIO_CMD_EXCHANGE`, and error codes
  (coordinated with `fujinet-nio.h`).
- Resolve the `FN_ERR_ABORTED` constant (§2.1 TODO).
- This document finalised after peer review.

**Testable invariant:** the header compiles cleanly against the Amiga GCC
toolchain with no warnings.

### Stage 2 — Implement `fujinet-nio.device` (serial backend)

Deliverables:
- New `repos/fujinet-nio-driver/amiga/nio.device/` directory.
- Broker device: `device_init`, `device_open`, `device_close`,
  `device_expunge`, `device_begin_io`, `device_abort_io`, FIFO worker,
  request state machine (§5.1).
- Serial backend: serial.device + timer.device ownership, SLIP framing via
  `fn_session`/`fn_slip`, lazy-open on first exchange.
- Error recovery policy resolved per §7 TODO.
- Build system produces `fujinet-nio.device` binary.
- A dedicated broker test program (not a stub, see §12) validates FIFO,
  concurrency, buffer ownership, abort, and error propagation.

**Testable invariant:** a standalone test tool opens the broker, submits a
`FUJINET_NIO_CMD_EXCHANGE` with a known FujiBus frame, receives the correct
response, closes. The broker test suite passes (see §12).

### Stage 3 — Re-route `fn_transport.c` through the broker

Deliverables:
- `fn_transport.c` (Amiga) rewritten: `fn_transport_init` opens the broker,
  `fn_transport_exchange_buffers` submits `FUJINET_NIO_CMD_EXCHANGE`,
  `fn_transport_close` closes the broker.
- No application or service code changes.
- Remove debug instrumentation (`DBG_PRINTF` blocks) added in the race
  investigation.

**Testable invariant:** the Amiberry integration suite passes with the same
test assertions and startup-sequence operations as before Stage 3. The
bootstrap environment may have changed (broker now loaded at startup); test
logic is unchanged. `diskdevice-inspect-catalog` must pass reliably. No
`OpenDevice("serial.device")` call exists anywhere outside the broker's serial
backend.

### Stage 4 — Simplify `fujinet-disk.device` worker

Deliverables:
- Remove the idle-close cycle from `device_worker_entry` (the
  `fn_transport_close` + `client_initialized` reset when the FIFO empties).
- The disk device calls `fn_transport_close` only in `device_expunge` (or
  equivalent explicit-lifecycle teardown).
- Worker inner loop is now: dequeue → `fn_init` (no-op) → exchange →
  `io_Error` → `ReplyMsg` → continue.

**Testable invariant:** all integration tests pass; the worker code is visibly
simpler; no test depends on the old idle-close behaviour.

### Stage 5 — Future backend (Zorro or other)

Deliverables:
- New backend module implementing the internal backend interface.
- New broker binary compiled with the new backend; installed as
  `fujinet-nio.device` for users with that hardware.
- No changes to `fujinet-disk.device`, `fujinet-nio-lib`, or applications.

**Testable invariant:** the full integration suite from Stage 3 passes against
the new backend without modification to test logic or assertions. Backend
parity with the serial baseline is required before a new backend is
production-ready.

---

## 12. Broker test suite (replaces Stage 5 stub-backend)

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

---

## Open questions

1. **Broker device name:** `fujinet-nio.device` — confirm no collision with
   existing AmigaOS or third-party device names.

2. **Unit numbering:** unit 0 is assumed. If two FujiNet adapters in one Amiga
   are ever required, unit > 0 could select the second. Not required for current
   hardware; the ABI must not preclude it.

3. **`FN_ERR_ABORTED` constant:** add to `fujinet-nio.h` with a value outside
   the current `0x00`–`0x12` range before Stage 1 completion.

4. **Error recovery policy (§7):** unresolved; prerequisite for Stage 2.

5. **`fn_transport_close` from disk device at expunge:** the interaction between
   `device_expunge` and the broker's `lib_OpenCnt` needs review during Stage 4.
   Specifically: if the disk device's `fn_transport_close` → `CloseDevice(broker)`
   runs after `device_expunge` has already been called on the disk device, ensure
   no double-close or use-after-free.
