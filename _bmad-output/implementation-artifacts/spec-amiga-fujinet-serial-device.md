---
title: 'Amiga FujiNet Paula serial device rewrite'
type: 'feature'
created: '2026-09-07'
status: 'draft'
review_loop_iteration: 0
context:
  - '{project-root}/_bmad-output/specs/spec-amiga-fujinet-serial-device/SPEC.md'
  - '{project-root}/docs/agent-test-policy.md'
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** The draft `fujinet-serial.device` completes an Amiberry exchange and printed success on PiStorm, but its guessed RBF interrupt teardown then rebooted the PiStorm machine. The broker needs an opt-in, FujiNet-owned Exec serial device that services Paula receive deadlines without disturbing Kickstart `serial.device`.

**Approach:** Rewrite Paula interrupt ownership and the `IOExtSer` command subset as an explicit open/request/flush/close lifecycle. Preserve runtime SET_SERIAL/GET_SERIAL selection, install surfaces, host UART math, and the existing focused Amiberry case; make `CMD_READ` wait when data is not yet available and support timer-driven `AbortIO`.

## Boundaries & Constraints

**Always:** Use the print-validated in-tree Paula extracts as hardware truth; compile for 68000 with soft-float; keep `fujinet-serial.device` unit 0 exclusive; keep SET_SERIAL/GET_SERIAL ABI, `fujinet-nio-serial`, install lists, and default `serial.device` unit 0; acknowledge RBF once after reading `SERDATR`; preserve only D0-D1/A0-A1 across the Exec interrupt-server boundary; keep PiStorm as the sole hardware gate.

**Ask First:** Any need to change broker public ABI, Stage 3/4 backend lifetime, ESP pacing, installation names, the default backend, or the 9600/19200/38400 acceptance matrix.

**Never:** Rename or replace Kickstart `serial.device`; use CIA serial-shift behavior; restore the draft double-INTREQ/NOP rationale; claim Amiberry proves PiStorm stability; add 57600 or hardware flow control.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|---------------|----------------------------|----------------|
| Open/configure | Unit 0, exclusive; SETPARAMS 300–230400 8N1 | Claim Paula, preserve prior state, program one SERPER divisor | Reject other units, second open, invalid baud/parity/word/stop |
| Receive | READ with enough queued bytes or bytes arriving later | Copy requested bytes, complete once; QUERY reports queued count/status | Pending READ is abortable; latch hardware/software overrun |
| Exchange lifecycle | WRITE after open/flush, then QUERY/READ, then FLUSH | Rearm RBF before request; FLUSH clears queue and quiesces RBF while retaining ownership | No stale interrupt or duplicate reply/ack |
| Close/expunge | Open device with armed or quiesced receive | Mask RBF, clear pending request, restore vector/state once, return safely | Delayed expunge waits for final close |

</frozen-after-approval>

## Code Map

- `repos/fujinet-nio-driver/amiga/serial.device/fujinet_serial_device.c:34` -- replace draft Paula ownership, synchronous READ, flush, close, and AbortIO behavior.
- `repos/fujinet-nio-driver/amiga/serial.device/fujinet_serial_rbf.S:1` -- replace rejected offset-driven double-ack ISR with the new Exec interrupt-server boundary.
- `repos/fujinet-nio-driver/amiga/serial.device/fujinet_paula_uart.c:5` -- retain AHRM-derived SERPER/SERDAT/ring primitives; extend only pure, host-testable state logic.
- `repos/fujinet-nio-driver/amiga/tests/test_fujinet_paula_uart.c:12` -- existing SERPER, ring, and overrun regression coverage.
- `repos/fujinet-nio-driver/amiga/tests/Makefile:14` -- add focused device/lifecycle native coverage to `make tests`.
- `repos/fujinet-nio-driver/amiga/nio.device/fujinet_nio_serial_backend.c:89` -- read-only broker contract: SendIO READ plus timer AbortIO; QUERY/READ and post-exchange FLUSH.
- `integration-tests/amiberry/test_nio_paula_serial.py` -- existing focused load/select/clock/FileDevice marker acceptance case; retain size 256.
- `repos/fujinet-nio-driver/docs/amiga/Serial-IO-Interface.md` -- read-only hardware authority for independent TX/RX, SERPER, SERDATR, and RBF acknowledgement.

## Tasks & Acceptance

**Execution:**
- [ ] `amiga/serial.device/fujinet_serial_device.c`, `fujinet_serial_rbf.S`, and related private headers -- replace interrupt ownership and request lifecycle; remove rejected double acknowledgements and hard-coded draft coupling.
- [ ] `amiga/serial.device/fujinet_paula_uart.c` and `amiga/tests/` -- preserve valid math/ring behavior and add tests for arm/quiesce transitions, blocking READ completion, abort, overrun, flush, and one-time teardown.
- [ ] `_bmad-output/specs/spec-amiga-fujinet-serial-device/` and `repos/fujinet-nio-driver/docs/amiga/rs232-cold-warm-hardware-test.md` -- record the chosen READ/RBF lifecycle, its always-armed alternative, and PiStorm-only CAP-5 gate without changing commands.
- [ ] Preserve existing SET_SERIAL, install-list, `--devs-file`, share, ADF/FTP, and `nio-paula-serial` wiring; modify only if verification exposes a regression.

**Acceptance Criteria:**
- Given a clean wb32 A1200-030 test image, when the focused Paula case loads and selects `fujinet-serial.device`, then clock and size-256 FileDevice marker complete with result 0 while default cases remain on `serial.device`.
- Given the operator's isolated PiStorm, when the 19200 cold one-shot runs, then it prints result/status 0 and returns to Shell without a power-LED flash or reboot screen.

## Spec Change Log

## Design Notes

Paula ownership lasts from exclusive open through close. `CMD_FLUSH` masks/quiesces RBF but does not return the vector; the next WRITE/READ/QUERY rearms it. This minimizes idle interrupt exposure while retaining warm broker ownership. The alternative is continuous RBF arming for stock-like unsolicited buffering; retain it as a documented fallback if PiStorm testing shows rearm latency or lost leading bytes. `CMD_READ` follows stock waiting semantics because the broker already supplies timer AbortIO and immediate zero-byte completion creates a race after QUERY.

## Verification

**Commands:**
- `source "$NIO_WORKSPACE/scripts/env.sh" && make -C repos/fujinet-nio-driver/amiga tests` -- all host tests, including SERPER/ring and new lifecycle cases, pass.
- `source "$NIO_WORKSPACE/scripts/env.sh" && make -C repos/fujinet-nio-driver/amiga native` -- builds the device and retained broker/tools with the Amiga toolchain.
- `source "$NIO_WORKSPACE/scripts/env.sh" && uv run pytest --run-amiga --amiga-env wb32 --amiga-machine a1200-030 integration-tests/amiberry/test_nio_paula_serial.py::test_paula_serial_clock` -- only the requested Amiberry node passes.

**Manual checks:**
- Operator runs `clock --type clock --backend cold --baud 19200 --serial-device fujinet-serial.device --trials 1` on PiStorm; result/status is 0 and Shell remains usable.
