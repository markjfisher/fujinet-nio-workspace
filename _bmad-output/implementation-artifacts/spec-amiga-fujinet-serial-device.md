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

**Approach:** Rewrite Paula ownership and the `IOExtSer` command subset as an explicit acquire/open/request/flush/close lifecycle. Preserve runtime SET_SERIAL/GET_SERIAL selection, install surfaces, host UART math, and the existing focused Amiberry case; make `CMD_READ` wait when data is not yet available and support timer-driven `AbortIO`.

## Boundaries & Constraints

**Always:** Use the print-validated in-tree Paula extracts as hardware truth; compile for 68000 with soft-float; keep `fujinet-serial.device` unit 0 exclusive; keep SET_SERIAL/GET_SERIAL ABI, `fujinet-nio-serial`, install lists, and default `serial.device` unit 0. First open must claim `misc.resource` serial ownership (including `MR_SERIALPORT` and required serial-control resources) before changing Paula, and failure rolls back only acquisitions made by this device. `SetIntVector(INTB_RBF)` is an exclusive RBF interrupt-handler boundary: use D0-D1/A0-A1 as scratch and preserve every other register. Every serviced receive is `read SERDATR -> retain byte/status -> clear INTF_RBF once`; never acknowledge first. Preserve/restore the prior RBF vector and relevant interrupt-enable state, but never claim to restore write-only SERPER. Keep distinct private latches/counters for Paula hardware overrun and software-ring overflow; public status may collapse them. Keep PiStorm as the sole hardware-stability gate; acceptance at 9600/19200/38400 does not validate every accepted SETPARAMS rate.

**Ask First:** Any need to change broker public ABI, Stage 3/4 backend lifetime, ESP pacing, installation names, the default backend, or the 9600/19200/38400 acceptance matrix.

**Never:** Rename, expunge, patch, or replace Kickstart `serial.device`; use CIA serial-shift behavior; acknowledge twice, acknowledge before `SERDATR`, or retain the draft NOP rationale; claim Amiberry proves PiStorm stability; add 57600 or hardware flow control.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|---------------|----------------------------|----------------|
| Open/configure | Unit 0, exclusive; SETPARAMS 300–230400 8N1 | Claim misc serial resources before Paula/vector access; preserve RBF vector/enable state and program a divisor | Reject other units, second open, invalid baud/parity/word/stop; release partial claims only |
| Receive | READ with enough queued bytes or bytes arriving later | Copy requested bytes, complete it once; QUERY reports queued count/status | Retained READ is atomically owned by exactly one of RBF completion, AbortIO, FLUSH, or close; keep hardware and ring-overflow diagnostics distinct |
| Exchange lifecycle | WRITE after open/flush, then QUERY/READ, then FLUSH | Rearm RBF before first TX byte; during rearm sample pending `SERDATR` before clearing RBF | FLUSH aborts one retained READ with `IOERR_ABORTED`, clears RX, then quiesces RBF while retaining ownership |
| Close/expunge | Open device with armed or quiesced receive | Resolve/cancel retained READ before masking/removing RBF, restoring vector/enables, and releasing resources once | No pending IORequest survives final teardown; delayed expunge waits for final close |

</frozen-after-approval>

## Code Map

- `repos/fujinet-nio-driver/amiga/serial.device/fujinet_serial_device.c:34` -- replace draft Paula ownership, synchronous READ, flush, close, and AbortIO behavior; add misc.resource acquisition and atomic retained-READ ownership.
- `repos/fujinet-nio-driver/amiga/serial.device/fujinet_serial_rbf.S:1` -- replace rejected offset-driven double-ack ISR with the new exclusive RBF interrupt-handler boundary.
- `repos/fujinet-nio-driver/amiga/serial.device/fujinet_paula_uart.c:5` -- retain AHRM-derived SERPER/SERDAT/ring primitives; extend only pure, host-testable state logic.
- `repos/fujinet-nio-driver/amiga/tests/test_fujinet_paula_uart.c:12` -- existing SERPER, ring, and overrun regression coverage.
- `repos/fujinet-nio-driver/amiga/tests/Makefile:14` -- add focused device/lifecycle native coverage to `make tests`.
- `repos/fujinet-nio-driver/amiga/nio.device/fujinet_nio_serial_backend.c:89` -- read-only broker contract: SendIO READ plus timer AbortIO; QUERY/READ and post-exchange FLUSH.
- `integration-tests/amiberry/test_nio_paula_serial.py` -- existing focused load/select/clock/FileDevice marker acceptance case; retain size 256.
- `repos/fujinet-nio-driver/docs/amiga/Serial-IO-Interface.md` -- read-only hardware authority for independent TX/RX, SERPER, SERDATR, and RBF acknowledgement.

## Tasks & Acceptance

**Execution:**
- [ ] `amiga/serial.device/fujinet_serial_device.c`, `fujinet_serial_rbf.S`, and related private headers -- replace ownership and request lifecycle. Claim misc serial resources before all Paula/vector changes; use one read-retain-ack RBF sequence; atomically arbitrate pending READ completion/abort/flush/close; restore only vector and relevant interrupt-enable state; remove duplicate acknowledgement/NOP and hard-coded draft coupling.
- [ ] `amiga/serial.device/fujinet_paula_uart.c` and `amiga/tests/` -- preserve valid math/ring behavior and add tests for resource contention and partial-claim rollback; arm-before-write, pending rearm ingest, blocking READ, AbortIO, final-byte/AbortIO race, FLUSH/close cancellation, distinct overrun latches, and one-time vector/resource teardown.
- [ ] `_bmad-output/specs/spec-amiga-fujinet-serial-device/` and `repos/fujinet-nio-driver/docs/amiga/rs232-cold-warm-hardware-test.md` -- record the chosen READ/RBF lifecycle, its always-armed alternative, and PiStorm-only CAP-5 gate without changing commands.
- [ ] Preserve existing SET_SERIAL, install-list, `--devs-file`, share, ADF/FTP, and `nio-paula-serial` wiring; modify only if verification exposes a regression.

**Acceptance Criteria:**
- Given a clean wb32 A1200-030 test image, when the focused Paula case loads and selects `fujinet-serial.device`, then clock and size-256 FileDevice marker complete with result 0 while default cases remain on `serial.device`.
- Given the operator's isolated PiStorm, when the 19200 cold one-shot runs, then it prints result/status 0 and returns to Shell without a power-LED flash or reboot screen.

## Spec Change Log

## Design Notes

Paula ownership lasts from successful misc-resource acquisition through final close. `CMD_FLUSH` atomically aborts a retained READ, clears RX, and masks/quiesces RBF without returning the vector; the next WRITE, READ, or QUERY rearms it, with RBF armed before the first new TX byte. Rearming samples a pending receive before clearing RBF, so no leading byte is discarded. This minimizes idle interrupt exposure while retaining warm broker ownership. Continuous RBF arming remains a documented PiStorm fallback if rearm latency or a lost leading byte is demonstrated.

`CMD_READ` follows stock waiting semantics because the broker already supplies timer AbortIO and immediate zero-byte completion creates a race after QUERY. Its retained request has one ownership transition, protected by `Disable()/Enable()` or equivalent: RBF completion, AbortIO, FLUSH, and final close compete to remove it, and only the winner replies. Final teardown first resolves/cancels that request, then masks RBF, restores the saved vector/enables, and releases each acquired resource once.

## Verification

**Commands:**
- `source "$NIO_WORKSPACE/scripts/env.sh" && make -C repos/fujinet-nio-driver/amiga tests` -- all host tests, including SERPER/ring and new lifecycle cases, pass.
- `source "$NIO_WORKSPACE/scripts/env.sh" && make -C repos/fujinet-nio-driver/amiga native` -- builds the device and retained broker/tools with the Amiga toolchain.
- `source "$NIO_WORKSPACE/scripts/env.sh" && uv run pytest --run-amiga --amiga-env wb32 --amiga-machine a1200-030 integration-tests/amiberry/test_nio_paula_serial.py::test_paula_serial_clock` -- only the requested Amiberry node passes.

**Manual checks:**
- Operator runs `clock --type clock --backend cold --baud 19200 --serial-device fujinet-serial.device --trials 1` on PiStorm; result/status is 0 and Shell remains usable.
