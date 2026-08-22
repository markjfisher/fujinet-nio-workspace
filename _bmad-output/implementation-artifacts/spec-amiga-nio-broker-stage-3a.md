---
title: 'Amiga NIO broker Stage 3A — lib transport cut-over'
type: 'feature'
created: '2026-08-22'
status: 'done'
review_loop_iteration: 0
baseline_commit: 'fa2d221d59c6b0ea77f5503291afabd305e68fcf'
context:
  - docs/amiga/nio-broker-architecture.md
  - docs/agent-test-policy.md
  - backlog/nio-broker.md
  - _bmad-output/implementation-artifacts/spec-amiga-nio-broker-stage-3.md
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** Amiga `fn_transport` still owns `serial.device`/`timer.device` with module-global `IOExtSer`, so it cannot be a broker client and remains a competing serial owner.

**Approach:** Rewrite the Amiga shim as architecture §3 broker client: each linked transport context owns its `FujiNetNIORequest`, reply port, and broker-open flag. Public `fn_transport_*` signatures remain unchanged. Do not start 3B until this spec’s Verification has run and passed. Parent Stage 3 stays open.

## Boundaries & Constraints

**Always:**
- `OpenDevice(FUJINET_NIO_DEVICE_NAME, FUJINET_NIO_DEVICE_UNIT, …)` only — not `serial.device` or `timer.device`.
- One in-flight exchange per context. Do not introduce a machine-global `IORequest` shared by independent tasks. CLI = process-local singleton (one context per process). `amiga-driver` BSS in `fujinet-disk.device` is a **second** context because it is a different linked image; the disk worker already serializes TD callers onto it.
- Keep public APIs: `fn_init` / `fn_transport_init` / `exchange` / `exchange_buffers` / `close` / `ready` signatures unchanged (`init`/`ready`/`exchange*` return `uint8_t`; only `fn_transport_close` is `void`). Architecture’s `fn_transport_init(ctx)` sketch is internal ownership, not a new public ctx argument.
- Kickstart 1.3-safe `CreatePort`/`DeletePort` (current shim comment ~L195–197), not V36-only `CreateMsgPort`.
- Before `OpenDevice`, initialize the per-context `FujiNetNIORequest`: zero the struct; `ln_Type = NT_MESSAGE`; `mn_ReplyPort` = the context port; `mn_Length = sizeof(struct FujiNetNIORequest)`.
- Before every `DoIO`, reset ABI/result fields so stale completion cannot leak: `io_Command = FUJINET_NIO_CMD_EXCHANGE`; `fn_struct_size`; `fn_flags`/`fn_pad` = 0; request/response pointers and lengths; `fn_response_length = 0`; `io_Error = 0`; `fn_nio_error = 0`. Then `DoIO`. If `io_Error != 0` then `*resp_len = 0` and return **mapped** FN failure — never a previous request’s `fn_nio_error`. If `io_Error == 0`, return `fn_nio_error` and `fn_response_length`.
- Map: init `OpenDevice` fail → `FN_ERR_NOT_FOUND`; `IOERR_ABORTED` → `FN_ERR_ABORTED`; `IOERR_NOCMD` / `IOERR_BADLENGTH` / `IOERR_BADADDRESS` → `FN_ERR_INVALID`; other non-zero `io_Error` → `FN_ERR_IO`. Never copy FN codes into `io_Error`.
- No private in-flight/pending flag and no concurrent close: `exchange_buffers` uses synchronous `DoIO`, so `fn_transport_close` runs only with **no request outstanding**. CloseDevice + delete port + `device_open = 0` on **this** context. Do **not** `AbortIO`/`WaitIO` an already completed request. Does not touch physical serial. Do not change the public API.
- `FN_AMIGA_EXPLICIT_LIFECYCLE`: no `atexit`; CLI `amiga` target keeps `atexit(fn_transport_close)`. Remove race-investigation `DBG_PRINTF`.
- Include `fujinet_nio_device.h` from `repos/fujinet-nio-driver/amiga/include` (add `-I` on `amiga` / `amiga-driver` only). Do not vendor a second ABI copy.
- Host tests covering the I/O matrix must be part of `make test` / `make check`. Compile-only is not 3A complete.

**Ask First:**
- Changing public `FujiNetNIORequest` or `fn_transport_*` signatures.
- Auto-loading the broker from the library (§8 forbids it).

**Never:**
- Edit disk.device idle-close, Amiberry harness, or guest sequences (3B).
- Compile `fn_session`/`fn_slip` into the shim; keep SLIP in the broker backend.
- Load broker beside a leftover serial-direct shim in any test this spec runs.
- Check Stage 3 backlog boxes. Run Amiberry pytest as the 3A gate. Start Stage 4/5. Create epics/stories.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Happy exchange | Broker open; `DoIO` `io_Error` 0; `fn_nio_error` FN_OK; length N | Return FN_OK; `*resp_len` = N | N/A |
| Broker absent | `OpenDevice` fails | `fn_transport_init` → `FN_ERR_NOT_FOUND`; not ready | Not a crash; not serial busy |
| Stale FN on native fail | Prior `fn_nio_error` non-zero; this `DoIO` `io_Error` = `IOERR_ABORTED` | Return `FN_ERR_ABORTED`; `*resp_len` 0 | Do not return prior `fn_nio_error` |
| BeginIO reject class | `io_Error` = `IOERR_NOCMD` (or BADLENGTH/BADADDRESS) | Return `FN_ERR_INVALID`; `*resp_len` 0 | Native and FN domains stay separate |
| Init before OpenDevice | New context; port created | Request zeroed; `NT_MESSAGE`; reply port; `mn_Length = sizeof(FujiNetNIORequest)` | Fail init if port alloc fails |
| Exchange field reset | Prior `io_Error`/`fn_nio_error`/length leftover | Those fields cleared/set before this `DoIO` | Stale completion must not leak |
| Close context | Open broker; **no** in-flight `DoIO` | CloseDevice + delete port; `device_open` 0; no AbortIO | Serial ownership unchanged (not this TU) |
| Re-init | Already `device_open` | `FN_OK`; no second OpenDevice | N/A |

</frozen-after-approval>

## Code Map

- `docs/amiga/nio-broker-architecture.md` §3 L288–353 — client ownership, init/exchange/close; §2.1 abort/init mappings; §8 L631–636 `IOERR_OPENFAIL` → `FN_ERR_NOT_FOUND`.
- `repos/fujinet-nio-driver/amiga/include/fujinet_nio_device.h` — **read-only ABI**; `FUJINET_NIO_DEVICE_NAME` / `UNIT` / `CMD_EXCHANGE` / `REQUEST_SIZE`.
- `repos/fujinet-nio-lib/src/platform/amiga/fn_transport.c` — **rewrite**. Today: globals `_serial_req`/`_timer_req` L46–59; `OpenDevice("serial.device")` L211–223; `DBG_PRINTF` L24–30, L214–216; session/SLIP helpers; `exchange_buffers` L331–363. Replace with `struct fn_amiga_transport` (port, `FujiNetNIORequest`, `device_open`) as process-local static — **no** pending/in_flight member. Drop `devices/serial.h` / `timer.h`.
- `repos/fujinet-nio-lib/include/fn_platform.h` L37–74 — **read-only** public transport API.
- `repos/fujinet-nio-lib/include/fn_internal.h` L34–40, L58 + `src/common/fn_state.c` — FujiBus `_fn_transport_ctx` buffers; **do not** store the Exec `IORequest` there.
- `repos/fujinet-nio-lib/src/common/fn_init.c` L4–22 — keep calling `fn_transport_init()`; no API change.
- `repos/fujinet-nio-lib/makefiles/targets.mk` L112–119 — add driver-include `-I` for `amiga` and `amiga-driver` only (`../fujinet-nio-driver/amiga/include` from lib root).
- `repos/fujinet-nio-lib/Makefile` L139 — hook new host test into `test`.
- `repos/fujinet-nio-lib/tests/` — **create** host binary compiling `fn_transport.c` against Exec stubs that record `OpenDevice` name/unit and inject `io_Error`/`fn_nio_error`. Cover the I/O matrix. Do not open real serial.
- `repos/fujinet-nio-driver/amiga/tools/fujinet-nio-exchange.c` L90–125 — fill-request pattern to copy (command, size, flags/pad zero).
- `repos/fujinet-nio-lib/README.md` L162–163 + `docs/building.md` L148 — Amiga transport is `fujinet-nio.device`, not direct `serial.device`.
- `repos/fujinet-nio-driver/amiga/disk.device/` — **do not edit** in 3A.

## Tasks & Acceptance

**Execution:**
- [x] `repos/fujinet-nio-lib/makefiles/targets.mk` -- Amiga `-I` to `fujinet_nio_device.h` -- shim compiles against Stage 1 ABI
- [x] `repos/fujinet-nio-lib/src/platform/amiga/fn_transport.c` -- broker client per §3; drop serial/timer/DBG/session -- cut-over
- [x] Host tests + `Makefile` `test` hook -- I/O matrix; OpenDevice name is broker -- cheapest lib gate
- [x] `README.md` + `docs/building.md` -- stop saying lib uses `serial.device` directly -- Stage 3 README deliverable (lib)
- [x] Confirm `amiga` and `amiga-driver` still build inside `make check` -- both link images get the new shim

**Acceptance Criteria:**
- Given a stubbed `OpenDevice`, when `fn_transport_init` runs, then the name is `fujinet-nio.device` unit 0 and never `serial.device`, and the request was zeroed/`NT_MESSAGE`/reply-port/`mn_Length` initialized first.
- Given leftover completion fields, when `fn_transport_exchange_buffers` issues `DoIO`, then ABI/result fields were reset first; if `io_Error != 0`, the mapped FN code is used and `*resp_len` is 0.
- Given a successful `DoIO` has already returned, when `fn_transport_close` runs, then it CloseDevices without AbortIO/WaitIO on that completed request.
- Given 3A Verification passed, when Stage 3 status is considered, then Stage 3 is still incomplete.

## Spec Change Log

- 2026-08-22: Human edit — signatures wording; OpenDevice request init + per-DoIO reset; close is no-in-flight (no AbortIO of a completed request).

## Design Notes

Public signatures stay unchanged (`close` is the only `void`). Ownership is one `fn_amiga_transport` static **per linked image**. That is the architecture’s CLI process-local singleton plus the resident driver’s own copy — not one machine-global request. Do not add a shared `.library` Exec request.

Synchronous `DoIO` is the in-flight bound: close is not concurrent with exchange, so there is no pending flag and no AbortIO on a completed request. The architecture’s AbortIO-before-CloseDevice note applies only if a request were still outstanding, which this public API does not allow.

`CreatePort` remains the 1.3-safe port constructor; the §3 snippet’s `CreateMsgPort` is illustrative.

## Verification

3A is incomplete if these were not run. Do not use guest pytest as the 3A gate.

**Commands (after `source "$NIO_WORKSPACE/scripts/env.sh"`):**
- `cd "$NIO_WORKSPACE/repos/fujinet-nio-lib" && make check` -- expected: all configured targets (including `amiga` / `amiga-driver` via `all` + `check` rules) and host tests pass, **including the new Amiga transport host test**
- `cd "$NIO_WORKSPACE/repos/fujinet-nio-driver/amiga" && make tests` -- expected: existing native tests still pass against the rebuilt `amiga-driver` archive

**Manual checks (if no CLI):**
- `rg -n 'serial\\.device' repos/fujinet-nio-lib/src/platform/amiga/` -- expected: no production OpenDevice of serial in the rewritten shim

## Suggested Review Order

**Broker client ownership**

- Process-local context owns the request, reply port, and open flag.
  [`fn_transport.c:30`](../../repos/fujinet-nio-lib/src/platform/amiga/fn_transport.c#L30)

- Init opens `fujinet-nio.device` after 1.3-safe port and request header setup.
  [`fn_transport.c:81`](../../repos/fujinet-nio-lib/src/platform/amiga/fn_transport.c#L81)

**Exchange mapping**

- Reset ABI/result fields immediately before each blocking `DoIO`.
  [`fn_transport.c:60`](../../repos/fujinet-nio-lib/src/platform/amiga/fn_transport.c#L60)

- Native `io_Error` maps to FN codes; success returns `fn_nio_error` and length.
  [`fn_transport.c:126`](../../repos/fujinet-nio-lib/src/platform/amiga/fn_transport.c#L126)

- CloseDevice plus DeletePort only; no AbortIO on a completed request.
  [`fn_transport.c:149`](../../repos/fujinet-nio-lib/src/platform/amiga/fn_transport.c#L149)

**Build and docs**

- Amiga targets include the driver ABI header instead of a vendored copy.
  [`targets.mk:114`](../../repos/fujinet-nio-lib/makefiles/targets.mk#L114)

- `make check` builds `amiga-driver` and runs the new host test.
  [`Makefile:136`](../../repos/fujinet-nio-lib/Makefile#L136)

- Library docs name the broker, not direct `serial.device`.
  [`README.md:162`](../../repos/fujinet-nio-lib/README.md#L162)

**Host I/O matrix**

- Stubbed OpenDevice records broker name/unit and request initialization.
  [`amiga_transport_host_test.c:140`](../../repos/fujinet-nio-lib/tests/amiga_transport_host_test.c#L140)

- Stale `fn_nio_error` must not leak through a native `io_Error`.
  [`amiga_transport_host_test.c:206`](../../repos/fujinet-nio-lib/tests/amiga_transport_host_test.c#L206)

- Close after completed DoIO must not AbortIO or WaitIO.
  [`amiga_transport_host_test.c:289`](../../repos/fujinet-nio-lib/tests/amiga_transport_host_test.c#L289)
