---
title: 'Amiga RS-232 cold/warm + response-size diagnostic (research rank 1)'
type: 'feature'
created: '2026-09-04'
status: 'done'
review_loop_iteration: 0
baseline_commit: '143dd7586eae2b9fcd96d27887cbd68cfb91a108'
context:
  - 'docs/agent-test-policy.md'
  - '_bmad-output/planning-artifacts/research/technical-amiga-rs-232-disk-operation-failures-abo-2026-09-03/research.md'
  - 'repos/fujinet-nio-driver/docs/amiga/' # Serial-IO-Interface, serial-interface-connector, cia-port-signal-assigments, cia-chip-register-map
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** `fujinet-nio-exchange` primes `serial.device` via `try_open_serial()` then starts with a small clock GET, so trials cannot separate cold/warm backend from response size.

**Approach:** Selectable measured FujiBus type (clock, host-get, file-list) and LIST `maxPayloadBytes`; explicit cold vs warm sequences; no pre-trial serial probe; one log line per measured trial. Keep no-arg prove mode without priming. No protocol or product-app change.

## Boundaries & Constraints

**Always:**
- Paula owns TXD/RXD (independent RX/TX). Overrun = prior RX character not serviced before the next completed. CIA-B is handshake GPIO only; CIAB `sdr` unused; modem-control lines do not affect TXD/RXD.
- Cold: `SET_BAUD` (even same rate) then selected EXCHANGE as first FujiBus. Warm: GET_BAUD must match `--baud` (or omit `--baud`), then **always** one unmeasured `WARMUP` clock, then selected EXCHANGE. Do not detect whether the backend is already open. Baud: 9600, 19200, 38400.
- `try_open_serial()` must not run before the first measured EXCHANGE. Post-trial busy/free probes are OK.
- `--size` is LIST `maxPayloadBytes`, not guaranteed `resp_len`. File-list requires `--uri` large enough to fill the cap. Hardware conclusions use logged `resp_len`.
- Trial log: `req_len`, `resp_len`, `elapsed_us` or `-`, `ttfb_us=-` unless a first-bit stamp already exists, `result`, `cause`, `native`, `status`, `backend=cold|warm`. `elapsed_us` optional: one process-start `timer.device`/EClock around measured `DoIO(EXCHANGE)` only. If that fails or would touch serial or extra serial I/O, print `-`. No per-byte or CMD_QUERY/CMD_READ timing.
- No-arg prove remains for Amiberry `nio-broker-isolated`; update ISOLATED if the pre-open string goes. Do not change FHOST/FLS product behavior.
- Comment-only CIA-UART/TX→RX cleanup in the serial backend/header is in scope.

**Ask First:** ESP UART timing, retry/SLIP/framing, new FujiBus commands (including echo), 57600, SERF_7WIRE, pre-posted CMD_READ, ping/pong, custom serial driver.

**Never:** CIA TX→RX as a mechanism. Ranks 2–7. Change lib, firmware, FHOST/FLS, or broker ABI. Full Amiberry suite. Infer warm/cold from OpenCnt or a serial probe.

## I/O & Edge-Case Matrix

- Clock cold (`--type clock --backend cold --baud 38400`): SET_BAUD then clock GET first; `backend=cold`. Log errors; no retry.
- List size (`--type file-list --backend cold --size 420 --uri …`): LIST maxPayloadBytes=420 first; log actual `resp_len`. Size must be 8,16,32,64,128,256,420,512; `--uri` required.
- Host-get warm (`--type host-get --backend warm`): baud match, `WARMUP`, then 0xF0 GET_CURRENT. `--size` forbidden.
- Warm baud mismatch: fail before WARMUP (baud change is cold).
- Warm always (baud matches): always `WARMUP` then measured type; `backend=warm`. WARMUP fail aborts.
- `--baud 57600` or unknown type: usage error, no OpenDevice.
- Prove `argc==1`: existing prove; no serial open before first EXCHANGE. Isolation: FindName/FindTask only.
- timer.device unavailable: `elapsed_us=-`. Do not open serial to time.

</frozen-after-approval>

## Code Map

Driver paths under `repos/fujinet-nio-driver/`.

- `amiga/tools/fujinet-nio-exchange.c` — relocate `try_open_serial` L130 out of `isolation_ok` L236 (before clock L279). Clock L50–65; file-list L67–91 (max 256). Host-get from `repos/nio-core-apps/apps/fhost.c` L64–79 (`0xF0`/`0x01`); do not edit FHOST. Matrix cap ≥ 512+header. No MARKER URI as matrix default.
- `amiga/tools/fujinet_nio_exchange_opts.c` (+ `.h`) — new, host-safe. Flags `--type/--backend/--baud/--size/--uri/--trials`. Plan cold=`SET_BAUD`+measure, warm=`WARMUP`+measure; file-list needs uri.
- Read-only broker: `amiga/nio.device/fujinet_nio_device.c` SET_BAUD close L210–214, EXCHANGE open L141; ABI `amiga/include/fujinet_nio_device.h` L35–54; CLI pattern `amiga/tools/fujinet-nio-baud.c`.
- `amiga/tests/test_fujinet_nio_device.c` L255 baud test: next EXCHANGE increments `backend_opens`; keep L463. New `amiga/tests/test_fujinet_nio_exchange_opts.c` + `amiga/tests/Makefile` (like `test_fujinet_nio_serial_channel.c`).
- `amiga/Makefile` L76–78 link opts. `integration-tests/amiberry/test_nio_broker.py` L6 ISOLATED; do not run guest.
- Comment-only Paula RBF wording: `amiga/nio.device/fujinet_nio_serial_backend.c` L219–224, L349–372, L421–424; `amiga/include/fujinet_nio_backend.h` L25–26. Post-trial RESIDENT probe may stay.

**Do not edit:** lib, firmware, FHOST/FLS, broker layout, serial timing. Do not resume `spec-amiga-rs232-response-diagnostics.md`. Lengths are FujiBus `fn_*_length`, not SLIP.

## Tasks & Acceptance

**Execution:**
- [x] `amiga/tools/fujinet_nio_exchange_opts.c` (+ header) — parse/validate; cold vs always-WARMUP plan
- [x] `amiga/tools/fujinet-nio-exchange.c` — prove without pre-trial serial open; matrix; host-get; LIST `--size`/`--uri`; cold SET_BAUD; warm WARMUP then measure; trial log; `elapsed_us` or `-`
- [x] `amiga/tests/test_fujinet_nio_exchange_opts.c` + Makefile — flags, size/baud/uri, LIST bytes, warm WARMUP
- [x] `amiga/tests/test_fujinet_nio_device.c` — SET_BAUD then EXCHANGE re-opens backend
- [x] `amiga/Makefile` — link opts
- [x] `integration-tests/amiberry/test_nio_broker.py` — ISOLATED without priming probe
- [x] `fujinet_nio_serial_backend.c` + `fujinet_nio_backend.h` — comment-only CIA/TX→RX cleanup

**Acceptance Criteria:**
- Given `--type file-list --backend cold --size 8 --uri …`, when run, then first FujiBus is LIST maxPayloadBytes=8 and the log has `backend=cold`, `req_len`, actual `resp_len`, `elapsed_us` or `-`, result/cause/native/status.
- Given `--backend warm` with matching baud, when run, then one `WARMUP` clock always precedes the measured type and no SET_BAUD runs.
- Given no-arg prove, when isolation runs, then `serial.device` is not opened before the first EXCHANGE.
- Given `--baud 57600`, `--size` on clock, or file-list without `--uri`, when parsed, then usage-error with no broker open.

## Spec Change Log

## Verification

**Commands:**
- `source "$NIO_WORKSPACE/scripts/env.sh" && make -C repos/fujinet-nio-driver/amiga tests` -- native tests pass (opts + SET_BAUD reopen)
- `source "$NIO_WORKSPACE/scripts/env.sh" && make -C repos/fujinet-nio-driver/amiga native` -- `fujinet-nio-exchange` links

**Manual checks (if no CLI):** Do not run `scripts/amiga-tests` or `nio-broker-isolated`. CIA cleanup is comments only.

## Suggested Review Order

**Entry and matrix dispatch**

- Flag mode is `argc >= 2`; no-arg prove is unchanged.
  [`fujinet-nio-exchange.c:577`](../../repos/fujinet-nio-driver/amiga/tools/fujinet-nio-exchange.c#L577)

- Parse fails before `OpenDevice` for 57600, unknown type, and missing `--uri`.
  [`fujinet_nio_exchange_opts.c:55`](../../repos/fujinet-nio-driver/amiga/tools/fujinet_nio_exchange_opts.c#L55)

**Cold vs warm plan**

- Cold is always `SET_BAUD` then MEASURE; warm always includes unmeasured `WARMUP`.
  [`fujinet_nio_exchange_opts.c:120`](../../repos/fujinet-nio-driver/amiga/tools/fujinet_nio_exchange_opts.c#L120)

- The Amiga tool executes that plan; baud mismatch aborts before `WARMUP`.
  [`fujinet-nio-exchange.c:486`](../../repos/fujinet-nio-driver/amiga/tools/fujinet-nio-exchange.c#L486)

**Measured packets**

- Host-get is `0xF0` / `0x01` with version 1, copied from FHOST without editing it.
  [`fujinet_nio_exchange_opts.c:206`](../../repos/fujinet-nio-driver/amiga/tools/fujinet_nio_exchange_opts.c#L206)

- LIST `maxPayloadBytes` comes from `--size`; matrix cap is 1024.
  [`fujinet_nio_exchange_opts.c:222`](../../repos/fujinet-nio-driver/amiga/tools/fujinet_nio_exchange_opts.c#L222)

**Prove isolation**

- Isolation is FindName/FindTask only; `try_open_serial` is post-trial.
  [`fujinet-nio-exchange.c:238`](../../repos/fujinet-nio-driver/amiga/tools/fujinet-nio-exchange.c#L238)

**Trial log**

- One line per MEASURE: `req_len`, `resp_len`, `elapsed_us` or `-`, `ttfb_us=-`.
  [`fujinet_nio_exchange_opts.c:172`](../../repos/fujinet-nio-driver/amiga/tools/fujinet_nio_exchange_opts.c#L172)

**Comment-only Paula RBF**

- Overrun wording is Paula RBF, not CIA UART or TX→RX.
  [`fujinet_nio_serial_backend.c:219`](../../repos/fujinet-nio-driver/amiga/nio.device/fujinet_nio_serial_backend.c#L219)

**Tests**

- Native opts tests cover flags, LIST bytes, warm WARMUP, and usage errors.
  [`test_fujinet_nio_exchange_opts.c:18`](../../repos/fujinet-nio-driver/amiga/tests/test_fujinet_nio_exchange_opts.c#L18)

- SET_BAUD then EXCHANGE re-opens the backend.
  [`test_fujinet_nio_device.c:298`](../../repos/fujinet-nio-driver/amiga/tests/test_fujinet_nio_device.c#L298)

- ISOLATED no longer expects a pre-trial serial probe string.
  [`test_nio_broker.py:7`](../../integration-tests/amiberry/test_nio_broker.py#L7)

