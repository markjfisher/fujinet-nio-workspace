---
title: 'Amiga RS-232 cold/warm + response-size diagnostic (research rank 1)'
type: 'feature'
created: '2026-09-04'
status: 'draft'
review_loop_iteration: 0
baseline_commit: '143dd7586eae2b9fcd96d27887cbd68cfb91a108'
context:
  - 'docs/agent-test-policy.md'
  - '_bmad-output/planning-artifacts/research/technical-amiga-rs-232-disk-operation-failures-abo-2026-09-03/research.md'
  - 'repos/fujinet-nio-driver/docs/amiga/Serial-IO-Interface.md'
  - 'repos/fujinet-nio-driver/docs/amiga/serial-interface-connector.md'
  - 'repos/fujinet-nio-driver/docs/amiga/cia-port-signal-assigments.md'
  - 'repos/fujinet-nio-driver/docs/amiga/cia-chip-register-map.md'
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** `fujinet-nio-exchange` primes `serial.device` with `try_open_serial()` then starts with a small clock GET, so hardware trials cannot separate cold vs warm backend from response size.

**Approach:** Selectable first FujiBus type (clock, host-get, file-list) and LIST `maxPayloadBytes`, explicit cold vs warm backend, no pre-trial serial probe, and one log line per trial. Keep no-arg prove mode without priming. No protocol or product-app change.

## Boundaries & Constraints

**Always:**
- Paula owns TXD/RXD with independent RX/TX; overrun means the prior RX character was not serviced before the next completed. CIA-B is handshake GPIO only; CIAB `sdr` unused; modem-control lines do not affect TXD/RXD.
- Cold = `SET_BAUD` (even same rate) then the selected EXCHANGE as the first FujiBus. Warm = no SET_BAUD; if backend closed, log `WARMUP` clock then measure the selected type. Baud this pass: 9600, 19200, 38400.
- `try_open_serial()` must not run before the first measured EXCHANGE (prove and matrix). Post-trial busy/free probes are OK.
- Each matrix trial logs `req_len`, `resp_len`, `elapsed_us` (timer around `DoIO` if cheap), `ttfb_us=-` unless a first-bit stamp already exists, `result`, `cause`, `native`, `status`, `backend=cold|warm`.
- No-arg prove script remains for Amiberry `nio-broker-isolated`. Update its ISOLATED assertion if the pre-open string disappears. Do not change FHOST/FLS product behavior.

**Ask First:** ESP UART timing, retry policy, SLIP/framing, new FujiBus commands (including echo), 57600, SERF_7WIRE, pre-posted CMD_READ, ping/pong, custom serial driver.

**Never:** Treat CIA TX→RX as a mechanism. Implement ranks 2–7. Change `fujinet-nio-lib`, firmware, FHOST/FLS apps, or broker ABI. Run the full Amiberry suite.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Clock cold | `--type clock --backend cold --baud 38400` | SET_BAUD then clock GET is first FujiBus; `backend=cold` + lengths | Log broker errors; no retry |
| List size | `--type file-list --backend cold --size 420` | LIST maxPayloadBytes=420 as first FujiBus | Reject size outside 8,16,32,64,128,256,420,512 |
| Host-get | `--type host-get --backend warm` | 0xF0 GET_CURRENT; `--size` forbidden | Reject `--size` on clock/host-get |
| Warm baud mismatch | `--backend warm` and `--baud` ≠ GET_BAUD | Fail before EXCHANGE | Baud change is cold |
| Warm, backend closed | `--backend warm` | `WARMUP` clock then measured type; trial `backend=warm` | WARMUP failure aborts |
| Bad flags | `--baud 57600` or unknown type | Usage error; no OpenDevice | RETURN_ERROR |
| Prove no-arg | `argc==1` | Existing prove flow; no serial OpenDevice before first EXCHANGE | Isolation uses FindName/FindTask only |

</frozen-after-approval>

## Code Map

- `amiga/tools/fujinet-nio-exchange.c` — **change.** `try_open_serial` L130–149 from `isolation_ok` L236 before first clock L279. Builders: clock L50–65; file-list L67–91 (max payload 256 at L87–88). Add host-get from `nio-core-apps/apps/fhost.c` L10–12, L64–79 (`0xF0`/`0x01`/1-byte version) — do not edit FHOST. Matrix response cap ≥ 512+header (prove buffer is 256 at L255).
- New host-safe `amiga/tools/fujinet_nio_exchange_opts.c` (+ `.h`) — parse `--type/--backend/--baud/--size/--uri/--trials`; baud and size allow-lists. No Amiga headers.
- LIST `--size` is existing maxPayloadBytes (`fnsvc.c` L55–56 production cap 420). Request 512 is allowed; log actual `fn_response_length`.
- Cold/warm **read-only** broker: `fujinet_nio_device.c` SET_BAUD closes L210–214; next EXCHANGE lazy-opens L141. Copy argv/SET_BAUD from `fujinet-nio-baud.c`.
- Request fields already exist (`fujinet_nio_device.h` L35–54) — do not extend ABI.
- Native: `test_fujinet_nio_device.c` `test_baud_controls` L255–292 (add follow-up EXCHANGE increments `backend_opens`). Keep `test_opencnt_zero_keeps_backend` L463–487.
- Host flags: new `amiga/tests/test_fujinet_nio_exchange_opts.c` + `amiga/tests/Makefile` (mirror `test_fujinet_nio_serial_channel.c`). Assert LIST builder writes selected max-payload LE.
- Prove string: `integration-tests/amiberry/test_nio_broker.py` L6. Sequence still no-arg. Do not run guest.
- `amiga/Makefile` L76–78 — link opts into `NIO_EXCHANGE`.
- Serial backend OpenDevice/SETPARAMS — **read-only.** Post-trial `try_open_serial` for RESIDENT may stay.

**Do not edit:** lib, firmware, FHOST/FLS, broker layout, serial timing.

## Tasks & Acceptance

**Execution:**
- [ ] `amiga/tools/fujinet_nio_exchange_opts.c` (+ header) — parse/validate flags
- [ ] `amiga/tools/fujinet-nio-exchange.c` — prove without pre-trial serial open; matrix mode; host-get; LIST `--size`; cold SET_BAUD; warm retain/WARMUP; per-trial log; larger LIST cap
- [ ] `amiga/tests/test_fujinet_nio_exchange_opts.c` + `amiga/tests/Makefile` — flags, size/baud rejection, LIST max-payload bytes
- [ ] `amiga/tests/test_fujinet_nio_device.c` — SET_BAUD then next EXCHANGE re-opens backend
- [ ] `amiga/Makefile` — link opts into the tool
- [ ] `integration-tests/amiberry/test_nio_broker.py` — ISOLATED assertion without priming probe

**Acceptance Criteria:**
- Given `--type file-list --backend cold --size 8`, when run, then the first FujiBus is LIST maxPayloadBytes=8 and the log has `backend=cold` plus req/resp lengths and result/cause/native/status.
- Given `--backend warm` with matching baud and an already-open backend, when run, then no SET_BAUD and the measured type is the selected one.
- Given no-arg prove, when isolation runs, then `serial.device` is not opened before the first EXCHANGE.
- Given `--baud 57600` or `--size` on clock, when parsed, then usage-error with no broker open.

## Spec Change Log

## Design Notes

Log FujiBus `fn_*_length`, not SLIP wire size. `--size` is LIST maxPayloadBytes; the ESP may return fewer bytes. Do not add an echo command. Do not resume `spec-amiga-rs232-response-diagnostics.md` (different in-review `fn_pad` work).

## Verification

**Commands:**
- `source "$NIO_WORKSPACE/scripts/env.sh" && make -C repos/fujinet-nio-driver/amiga tests` -- expected: native tests pass, including opts + SET_BAUD reopen
- `source "$NIO_WORKSPACE/scripts/env.sh" && make -C repos/fujinet-nio-driver/amiga native` -- expected: `fujinet-nio-exchange` links

**Manual checks (if no CLI):**
- Do not run `scripts/amiga-tests` or the `nio-broker-isolated` guest node.
