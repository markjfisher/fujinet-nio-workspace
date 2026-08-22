---
id: SPEC-amiga-nio-broker
companions:
  - requirements.md
  - stages.md
  - ../../../docs/amiga/nio-broker-architecture.md
sources:
  - ../../planning-artifacts/briefs/brief-fujinet-nio-workspace-2026-08-22/brief.md
  - ../../../backlog/nio-broker.md
---

> **Canonical contract.** This SPEC and the files in `companions:` are the complete, preservation-validated contract for what to build, test, and validate. Source documents listed in frontmatter are for traceability — consult them only if you need narrative rationale or prose color this contract intentionally omits.

# Amiga NIO broker

## Why

**Pain plus vision.** On Amiga, FLS and `fujinet-disk.device` each `OpenDevice("serial.device")`, so concurrent FujiNet NIO clients race the wire. Serial is only a proving-ground backend; leaking it into apps, DiskDevice, or the public client API would force a rewrite for Zorro or other packet-native links. FujiNet NIO (the product) requires replaceable physical transports, a single owner of the physical resource, serialized concurrent exchanges, and native vs NIO error domains. This spec is the Amiga implementation of those product rules: a backend-neutral broker so services and applications stay on `fujinet-nio-lib` while the selected backend owns the hardware.

## Capabilities

- **CAP-1**
  - **intent:** Implementers can compile Amiga clients and the broker against one published public IORequest ABI, including a first-class abort result in FN-space, and the broker serial backend can compile session/SLIP framing without depending on library globals.
  - **success:** `fujinet_nio_device.h` matches architecture §2; `FN_ERR_ABORTED` is `0x13` in `fujinet-nio.h` and does not collide with existing `FN_ERR_*`; `#include "fn_internal.h"` is gone from `fn_session.c`; Amiga GCC header is warning-clean; amiga and amiga-driver library builds pass; existing integration suite is unchanged.
- **CAP-2**
  - **intent:** Any number of Amiga tasks can submit NIO exchanges at the same time and each receive one complete request/response transaction, with no interleaving of send/receive phases between callers.
  - **success:** Concurrent submissions use distinct `FujiNetNIORequest`s; the broker FIFO worker processes one exchange end-to-end before starting the next; responses go to the correct caller in FIFO order (broker test: Concurrent-client FIFO ordering).
- **CAP-3**
  - **intent:** Callers can distinguish Exec/device dispatch failure from FujiNet/NIO exchange outcome.
  - **success:** Every BeginIO reject, abort, and completed exchange sets `io_Error` and `fn_nio_error` per architecture §2.1; malformed requests use a native request-validation `io_Error` (symbol from the build’s `exec/errors.h`) and `FN_ERR_INVALID`; `io_Error` never holds `FN_ERR_*`; failed paths set `fn_response_length` to 0; `IOF_QUICK` is cleared before any `ReplyMsg`; tests never hard-code guessed `IOERR_*` numerics (broker test: BeginIO ABI reject).
- **CAP-4**
  - **intent:** Callers can abort a queued or in-progress exchange and receive a single abort completion, without treating abort as a remote FujiBus rollback.
  - **success:** Queued abort: request never reaches the worker; in-progress abort: physical exchange finishes, response is discarded; both complete with `IOERR_ABORTED` + `FN_ERR_ABORTED` + `fn_response_length` 0; exactly one `ReplyMsg` (broker tests: AbortIO queued and in-progress).
- **CAP-5**
  - **intent:** The selected physical backend exclusively owns the FujiNet transport for the broker’s resident lifetime, stays open across client open/close, and can recover after a defined reset without permanently giving up until expunge.
  - **success:** First exchange lazy-opens the backend; later exchanges reuse it; `lib_OpenCnt` 0 does not close it; client `CloseDevice` is not `backend_close`; fatal error closes/resets, fails the current request with `FN_ERR_TRANSPORT`, next exchange may lazy-reopen; ordinary expunge is deferred/refused while opens, queued requests, or an in-progress exchange remain, and does not abort live requests (broker tests: lazy-open, resident-lifetime, error recovery, expunge while busy).
- **CAP-6**
  - **intent:** Applications and `fujinet-disk.device` keep using `fujinet-nio-lib` service APIs; only the Amiga transport shim names `fujinet-nio.device`.
  - **success:** After Stage 3, `fn_transport_init`/`exchange`/`close` operate on a per-context broker `FujiNetNIORequest`; no application or service source changes; `OpenDevice("serial.device")` exists only in the broker serial backend; disk device uses its own context, not a CLI/global singleton.
- **CAP-7**
  - **intent:** Broker behavior can be proven against a real serial backend without sharing the port with the pre-cut-over serial-direct shim.
  - **success:** Stage 2 suite (stages.md) passes in an isolated image that does not start FLS, `fujinet-disk.device`, or any tool whose `fn_transport` still opens `serial.device`; a standalone tool completes one known FujiBus exchange through the broker.
- **CAP-8**
  - **intent:** The environment that owns startup can make the broker available before any NIO client initializes transport; a missing broker is a mapped error, not a crash or silent auto-load.
  - **success:** `fn_transport_init` does not load the device; missing `OpenDevice` maps to `FN_ERR_NOT_FOUND`; Amiberry bootstrap (and documented Startup-Sequence / user load) loads `fujinet-nio.device` before any FujiNet tool; Stage 3 integration assertions and sequences are unchanged.
- **CAP-9**
  - **intent:** A resident disk-device worker can leave its broker transport open across idle FIFO gaps and close it only on explicit teardown.
  - **success:** Worker no longer calls `fn_transport_close` when the FIFO empties; close only in `device_expunge` (or equivalent); integration tests pass and do not depend on idle-close.
- **CAP-10**
  - **intent:** A later packet-native backend can replace serial without changing applications, DiskDevice, public client APIs, NIO payloads, or the public broker ABI.
  - **success:** New backend is a new broker binary installed as `DEVS:fujinet-nio.device`; no changes to `fujinet-disk.device`, `fujinet-nio-lib`, or apps; Stage 3 integration suite passes with the same assertions (environment/backend selection only).

## Constraints

- Public broker ABI is architecture §2 (`IORequest` base, one command `FUJINET_NIO_CMD_EXCHANGE`, opaque payload, no serial/service/hardware fields). Do not redesign it.
- Length fields are `UWORD` (ABI capacity 65535). Oversize is vs platform `FN_MAX_PACKET_SIZE`, currently 1024 on Amiga. The ABI does not hard-code 1024.
- v1 `fn_struct_size` must equal `sizeof(struct FujiNetNIORequest)`. After growth: too-small prefix reject; known older size accept with documented tail defaults; caller size larger than the driver knows reject. Old→newer may work; new→older rejects. Do not implement the table until the struct grows.
- Malformed broker `IORequest`: `io_Error` = appropriate native Exec/device request-validation error; `fn_nio_error` = `FN_ERR_INVALID`. Choose the symbol by inspecting the Amiga GCC `exec/errors.h` used in the build. Never bake guessed numeric `IOERR_*` values into tests.
- Unit is validated at `OpenDevice`, not in `BeginIO`.
- `IOF_QUICK` is unsupported for exchange; never inline-complete an exchange.
- Broker never interprets FujiBus services; backends never implement disk/TD_* semantics.
- Internal backend is architecture §11: `backend_open` / `backend_close` / `backend_exchange` with the v1 signatures there. Stage 2 may add a private context pointer without changing semantics.
- `backend_exchange` must finish in bounded time and return `FN_ERR_TIMEOUT` when the selected backend’s response deadline is exceeded. Baud, serial/timer units, poll interval, and timeout values are serial-backend private named constants/config, not broker ABI.
- Framing (`fn_slip`, `fn_session`) compiles into the serial backend by path; no library-symbol cycle; only runtime `OpenDevice` string from lib to broker.
- Stage order is a gate: Stage 1 before Stage 2; do not install Stage 2 broker beside pre-Stage-3 shim on a shared serial port.
- New FN constants are added only in `fujinet-nio.h`, not invented in the broker.
- Exec error symbols come from `exec/errors.h`; do not hard-code numeric `IOERR_*` values in architecture or tests.
- Near-term: one serial-backed broker binary as `DEVS:fujinet-nio.device` (Option A). Loadable-backend Option B is out of this spec.
- While the broker is resident, the physical transport is unavailable to other software (e.g. a terminal on `serial.device`). Unload the broker to release it. That exclusive hold is intended, not a defect.
- Invalid unit is an `OpenDevice` failure (native device error + `FN_ERR_NOT_FOUND` or documented equivalent), not a BeginIO check.
- Ordinary expunge does not abort or destroy live requests. Refuse/defer while `OpenCnt != 0`, queue nonempty, or an exchange is in progress; then stop worker, close backend if open, release resources.

## Non-goals

- Redesigning the broker architecture or public ABI.
- Blanket classic FujiNet wire/API compatibility.
- Implementing Zorro/floppy/packet-native hardware in this cut-over (CAP-10 is the ABI/parity contract only).
- HDF/RDB media work.
- Auto-loading `fujinet-nio.device` from `fujinet-nio-lib`.
- Dual `OpenDevice("serial.device")` (old shim + broker) as a supported configuration.
- Priority queuing inside the broker.
- Treating abort as remote transaction rollback.
- Implicit abort/drain of live requests because expunge was requested.
- Forcing BBC-style ROM apps or other platforms into this Amiga device shape.
- Making serial a permanent product identity or putting baud/SLIP/timer on the public ABI.
- Naming serial baud/unit/timer/timeout values in this broker spec.
- Multi-adapter backend instances before a single adapter exists.

## Success signal

Stages 1–4 complete with their testable invariants (stages.md): the ABI exists; isolated broker tests pass on serial; Amiberry integration (including `diskdevice-inspect-catalog`) passes after cut-over with unchanged assertions; no `serial.device` open outside the serial backend; disk idle-close is gone. A future backend can be a new binary against the same public ABI and the same higher-level suite.

## Assumptions

- Option A (separate broker binaries, identical public ABI) is the second-backend strategy unless a later decision requires coexistence without reboot.
