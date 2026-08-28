---
title: 'Amiga RS-232 response failure diagnostics'
type: 'bugfix'
created: '2026-08-28'
status: 'in-review'
review_loop_iteration: 0
baseline_commit: '9dbcdd9d52a6bad17e320142c961702393c67b21'
context:
  - 'docs/agent-test-policy.md'
  - 'repos/fujinet-nio-driver/amiga/README.md'
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** On a real Amiga connected to the ESP32-S3 RS-232 FujiBus endpoint, valid FujiNet responses for `FHOST` and `FLS` are logged by the ESP32 but the Amiga application reports `FN_ERR_TRANSPORT` (16) or a timeout. The existing broker deliberately maps several receive-side failures to the same public error, so current evidence cannot distinguish serial.device I/O failure from malformed SLIP/session data.

**Approach:** Add narrowly scoped, request-local completion diagnostics to the Amiga NIO broker and expose them to callers for temporary hardware investigation. Preserve the normal exchange result and wire protocol; use the new detail only to report the underlying failed receive stage/cause after a `FN_ERR_TRANSPORT` result.

## Boundaries & Constraints

**Always:** Preserve `fujinet-nio.device` command behavior, response payloads, queue semantics, baud controls, and the existing `fn_pad[0]` completion-stage / `fn_pad[1]` broker-result diagnostics. Use existing request storage only; add no resident trace buffer, background logger, or print statements from the broker. The diagnostic must be valid for a caller-owned `FujiNetNIORequest` and reset for each exchange.

**Ask First:** Any attempt to alter serial timing, retry policy, SLIP framing, ESP32 UART configuration, or transport error mapping beyond reporting the underlying cause.

**Never:** Change FHOST/FLS or clock application behavior, mutate interactive Workbench media/startup, lower one physical UART endpoint without the other, or run broad Amiberry/firmware suites for this diagnostic-only change.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|---------------|---------------------------|----------------|
| Success | Backend exchange returns `FN_OK` | Existing stage/result remain; failure-detail field is clear | No user-visible change |
| Serial I/O failure | Receive channel reports an underlying serial error | Request completes with existing `FN_ERR_TRANSPORT` plus serial-I/O detail | Caller can distinguish it from decode failure |
| Malformed SLIP/session frame | Stream session returns malformed-frame/I/O result with no serial-device error | Request completes with existing `FN_ERR_TRANSPORT` plus session/decode detail | No response payload is published |
| Timeout | Stream session times out without a sticky channel error | Existing `FN_ERR_TIMEOUT` behavior remains | Diagnostic identifies timeout without relabelling it transport |
</frozen-after-approval>

## Code Map

- `repos/fujinet-nio-driver/amiga/nio.device/fujinet_nio_serial_backend.c` -- owns the RS-232 session, knows the raw session result and sticky `channel_error`, and is the only correct place to classify receive failure.
- `repos/fujinet-nio-driver/amiga/include/fujinet_nio_backend.h` -- backend/device boundary; extend only if a request-local diagnostic accessor is needed.
- `repos/fujinet-nio-driver/amiga/nio.device/fujinet_nio_device.c` -- copies backend exchange outcome into `FujiNetNIORequest`; `fn_pad[0]` and `[1]` already hold temporary request-local diagnostics. Use `[2]` for the detailed cause.
- `repos/fujinet-nio-driver/amiga/include/fujinet_nio_device.h` -- public request layout and command ABI; do not change layout.
- `repos/fujinet-nio-driver/amiga/tests/test_fujinet_nio_device.c` -- native harness for injected backend outcomes and request completion; extend it to assert detail propagation/reset.
- `repos/fujinet-nio-lib/src/platform/amiga/fn_transport.c` -- library transport currently returns only the public error and exposes stage/result; it may expose the third diagnostic byte without changing normal `fn_*` outcomes.

## Tasks & Acceptance

**Execution:**

- [x] `repos/fujinet-nio-driver/amiga/nio.device/fujinet_nio_serial_backend.c` and `amiga/include/fujinet_nio_backend.h` -- classify the most recent failed session exchange into a small documented diagnostic code, retaining no history beyond the active completion.
- [x] `repos/fujinet-nio-driver/amiga/nio.device/fujinet_nio_device.c` -- reset and return the diagnostic through existing `fn_pad[2]` for `EXCHANGE`; retain `[0]` and `[1]` meanings.
- [x] `repos/fujinet-nio-driver/amiga/tests/test_fujinet_nio_device.c` -- cover success clearing, transport failure detail, and timeout preservation using the native injected backend.
- [x] `repos/fujinet-nio-lib/src/platform/amiga/fn_transport.c` and public Amiga declaration if needed -- make the request-local detail observable to FHOST/FLS diagnostics without changing transport success/failure values.

**Acceptance Criteria:**

- Given a successful exchange, when the caller inspects the diagnostics, then existing stage/result values remain correct and detailed cause is zero.
- Given a serial/session failure mapped to `FN_ERR_TRANSPORT`, when the exchange completes, then the caller can identify the underlying class without inspecting resident logs.
- Given a timeout, when the exchange completes, then it remains `FN_ERR_TIMEOUT`, response length remains zero, and it is not falsely presented as a serial I/O error.
- Given existing native device tests, when the diagnostic is added, then queue, reply, baud-control, and error completion tests remain green.

## Spec Change Log

- 2026-08-28 — Real-hardware evidence narrowed the original ambiguous
  `FN_ERR_TRANSPORT` failure to an Amiga `serial.device` receive overrun at
  57,600 baud. The diagnostic implementation was extended, without changing
  exchange behaviour, to identify the failed serial operation, its native
  error, and the meaningful high byte of `io_Status`.
- 2026-08-28 — Corrected the backend's non-compliant serial.device receive
  buffer allocation: the 2050-byte SLIP wire buffer is not a 64-byte multiple,
  so `io_RBufLen` is now rounded upward to 2112 as required by the NDK.
  Real-hardware retest retained the same `CMD_READ` receive overrun at 57,600,
  so this correction is preserved but is not the root-cause fix.

## Design Notes

`fn_pad` is caller-supplied, request-local storage already used by the broker for temporary diagnostics. Using byte 2 keeps resident base layout and the public request structure unchanged. The diagnostic taxonomy must be intentionally small and stable enough for a temporary CLI/debug print: none, serial-I/O, session/decode, timeout, and backend/open failure as applicable.

### Real-hardware findings, 2026-08-28

- The ESP32-S3 FujiBus endpoint logs valid FHOST, FLS, and clock requests and
  valid responses while the Amiga application reports raw error 16
  (`FN_ERR_TRANSPORT`). This established that an ESP application response is
  not sufficient evidence that the Amiga serial receive path accepted it.
- `fujinet-nio-exchange` is a self-contained direct-broker diagnostic. It
  must be run alone, wait for completion, and does not invoke FLS. It now
  permits `fujinet-disk.device` to be resident so it can be used from the
  normal interactive Workbench environment.
- The first direct clock exchange at 57,600 baud repeatedly produced:
  `io=0 nio=16 len=0 stage=2 result=16 cause=7 native=6 status-hi=1`.
  The immediate retry succeeds, as do later exchanges.
- `stage=2` means the exchange reached the broker backend. `cause=7` is the
  serial `CMD_READ` site. Native serial error 6 is `SerErr_LineErr`.
  `status-hi=1` represents serial `io_Status` bit 8 (`0x0100`), the UART
  receive-overrun flag.
- Therefore the proven first failing boundary is: valid ESP response ->
  Amiga `serial.device` `CMD_READ` -> receive overrun -> `SerErr_LineErr` ->
  existing public `FN_ERR_TRANSPORT`. It is not currently a FujiBus packet,
  SLIP/session-decoding, FHOST, FLS, or DiskDevice failure.
- The user configures `fujinet-nio-baud 57600` in User-Startup, so the
  failure is not explained by the resident driver's 19,200 default being
  restored after reboot.
- At 19,200 and 38,400 baud the same diagnostic ends `PASS isolated-exchange`
  and normal FHOST/FLS work correctly. 57,600 is the observed failure point.
- The intentionally malformed timeout probe produces the ESP log frame
  `c0 99 c0`; that warning is expected test traffic, not the fault.

### Next investigation boundary

Do not change FujiBus protocol, FHOST/FLS, baud defaults, retry policy, or
ESP firmware solely from the current evidence. Investigate the Amiga receive
path at 57,600: serial.device high-speed/buffering contract, current
`IOExtSer` setup, and whether the 1 ms `SDCMD_QUERY`/timer polling strategy
allows an initial response burst to overrun. Current backend configuration is
8 data bits, 1 stop bit, XON/XOFF disabled, serial receive buffer length
`(FN_MAX_PACKET_SIZE * 2) + 2`, and a 128-byte user-side drain buffer.

## Verification

**Commands:**

- `source "$NIO_WORKSPACE/scripts/env.sh" && make -C repos/fujinet-nio-driver/amiga tests` -- expected: native Amiga driver harnesses pass.
- `source "$NIO_WORKSPACE/scripts/env.sh" && make -C repos/fujinet-nio-driver/amiga native` -- expected: resident device and diagnostic tools build with readable Amiga toolchain/NDK headers.

**Manual checks:**

- On the real 57,600-baud Amiga/ESP32 link, run `FHOST` then `FLS`; expected: their failure output includes the detailed broker cause, while ESP32 request/response logging remains unchanged.
- On the real link, run `NIO:fujinet-nio-exchange` by itself and wait for it
  to exit. Record `cause`, `native`, and `status-hi` from the first EXCHANGE.
