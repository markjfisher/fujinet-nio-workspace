---
title: 'Amiga FujiNet Paula serial device rewrite'
type: 'feature'
created: '2026-09-07'
status: 'draft'
review_loop_iteration: 0
context:
  - '{project-root}/_bmad-output/specs/spec-amiga-fujinet-serial-device/SPEC.md'
  - '{project-root}/_bmad-output/specs/spec-amiga-fujinet-serial-device/lifecycle.md'
  - '{project-root}/docs/amiga/rs232-paula-and-cia-handshake.md'
  - '{project-root}/docs/agent-test-policy.md'
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** The draft `fujinet-serial.device` completes an Amiberry exchange and printed success on PiStorm, but its guessed RBF interrupt teardown then rebooted the PiStorm machine. The broker needs an opt-in, FujiNet-owned Exec serial device that services Paula receive deadlines without disturbing Kickstart `serial.device`.

**Approach:** Rewrite Paula ownership and the `IOExtSer` command subset as an explicit acquire/open/request/flush/close lifecycle. Preserve runtime SET_SERIAL/GET_SERIAL selection, install surfaces, host UART math, and the existing focused Amiberry case; make `CMD_READ` wait when data is not yet available and support timer-driven `AbortIO`. Direct Paula UART control; do not replace Kickstart `serial.device`. PiStorm remains the sole hardware-stability acceptance gate.

## Boundaries & Constraints

**Always:** Use the print-validated in-tree Paula extracts as hardware truth; compile for 68000 with soft-float; keep `fujinet-serial.device` unit 0 exclusive; keep SET_SERIAL/GET_SERIAL ABI, `fujinet-nio-serial`, install lists, and default `serial.device` unit 0.

Acquire `MR_SERIALPORT` then `MR_SERIALBITS` through `misc.resource` before changing Paula serial registers, serial interrupt enables, or the RBF vector. Fail open cleanly if either is already owned; free only what this open acquired. Do not `RemDevice` another owner.

Treat `INTB_RBF` as an exclusive Exec interrupt handler installed with `SetIntVector()`. By project policy use only `D0-D1/A0-A1` as ISR scratch and preserve all other registers. Exec also permits `A5/A6` as handler scratch; this handler does not require them. This is the RBF interrupt-handler boundary, not an interrupt-server chain.

The RBF handler must not `ReplyMsg()`, copy into the caller IORequest, or transition a pending READ. If master `INTEN` is clear, return without acknowledging. Otherwise service each byte as: read `SERDATR`, retain byte/status into the private ring, clear `INTF_RBF` once; repeat while `INTF_RBF` remains asserted. If a pending READ can now be satisfied, `Cause()` a device-owned software interrupt to complete it. Never acknowledge first. Never use the rejected duplicate-`INTREQ`/NOP sequence. Do not hitch deferred work onto `INTB_PORTS`.

Pending READ completion (deferred path), `AbortIO`, `CMD_FLUSH`, and final close must use one atomic request-ownership transition and produce at most one reply. The RBF handler is not a completion owner.

Preserve the prior RBF vector and relevant interrupt-enable state. Restore that vector only if it is still the FujiNet handler. Release `MR_SERIALBITS` then `MR_SERIALPORT`. Do not claim to restore a previous `SERPER` divisor.

Keep distinct private latches `hardware_overrun_latched` and `software_ring_overflow_latched`; public status may collapse them. SETPARAMS accepted range is 300–230400; FujiNet hardware acceptance matrix is 9600 / 19200 / 38400 only. PiStorm is the sole hardware-stability gate.

**Ask First:** Any need to change broker public ABI, Stage 3/4 backend lifetime, ESP pacing, installation names, the default backend, or the 9600/19200/38400 acceptance matrix.

**Never:** Rename, expunge, patch, or replace Kickstart `serial.device`; `RemDevice` another serial owner to steal the port; use CIA serial-shift behavior; program CIA-B handshake bits in this cut; `ReplyMsg` or mutate an IORequest from the RBF handler; hitch deferred completion onto `INTB_PORTS`; acknowledge twice, acknowledge before `SERDATR`, or retain the draft NOP rationale; claim Amiberry proves PiStorm stability; add 57600 or hardware flow control; restore write-only `SERPER`; overwrite `INTB_RBF` on close if the vector is no longer ours; treat exclusive open of this device as a substitute for `misc.resource`.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|---------------|----------------------------|----------------|
| Open/configure | Unit 0, exclusive; SETPARAMS 300–230400 8N1 | Claim `MR_SERIALPORT` then `MR_SERIALBITS` before Paula/vector access; preserve RBF vector/enable state and program a divisor | Reject other units, second open of this device, invalid baud/parity/word/stop; release partial claims only (`BITS` then `PORT`) |
| Paula ownership conflict | Stock `serial.device` already owns serial hardware | `fujinet-serial.device` open fails without touching Paula/RBF/`SERPER`/INTENA | Clean open failure; no partial ownership; no `RemDevice` of the owner |
| Receive | READ with enough queued bytes or bytes arriving later | Copy requested bytes on the deferred path, complete it once; QUERY reports queued count/status | Retained READ is atomically owned by exactly one of deferred completion, AbortIO, FLUSH, or close; RBF handler is not a completion owner |
| READ vs AbortIO race | Final requested byte arrives while `AbortIO()` runs | Deferred completion path and `AbortIO` compete; exactly one owner and one reply | No duplicate reply, stale pointer, or lost ownership |
| Burst already pending in Paula | Handler entered with more than one RBF byte ready | Drain: sample/retain/ack-once per byte until `INTF_RBF` is clear | Returning with RBF still asserted is a livelock |
| RBF handler vs ReplyMsg | Byte(s) satisfy a pending READ | Handler only rings + `Cause()`s; software interrupt copies and replies | No `ReplyMsg` or IORequest mutation on the RBF handler path |
| Close/expunge | Open device with armed or quiesced receive | Mask RBF after request resolution; restore vector/enables only if still ours; release `MR_SERIALBITS` then `MR_SERIALPORT` | Delayed expunge waits for final close; do not overwrite a stolen vector |
| Stock access while FujiNet owns Paula | `fujinet-serial.device` holds `misc.resource` | Stock serial must not manipulate the UART concurrently | Ownership remains exclusive |
| Receive | READ with enough queued bytes or bytes arriving later | Copy requested bytes on the deferred path, complete it once; QUERY reports queued count/status | Retained READ is atomically owned by exactly one of deferred completion, AbortIO, FLUSH, or close; RBF handler is not a completion owner |
| READ vs AbortIO race | Final requested byte arrives while `AbortIO()` runs | Deferred completion path and `AbortIO` compete; exactly one owner and one reply | No duplicate reply, stale pointer, or lost ownership |
| Burst already pending in Paula | Handler entered with more than one RBF byte ready | Drain: sample/retain/ack-once per byte until `INTF_RBF` is clear | Returning with RBF still asserted is a livelock |
| RBF handler vs ReplyMsg | Byte(s) satisfy a pending READ | Handler only rings + `Cause()`s; software interrupt copies and replies | No `ReplyMsg` or IORequest mutation on the RBF handler path |
| FLUSH with pending READ | READ retained by device | Cancel READ once, clear queue, quiesce RBF, retain Paula ownership | READ completes `IOERR_ABORTED` |
| Exchange lifecycle | WRITE after open/flush, then QUERY/READ, then FLUSH | Rearm RBF before first TX byte; during rearm sample pending `SERDATR` before clearing RBF | Always-armed receive is documented PiStorm fallback only |
| Rearm with pending RBF | RBF condition exists while receive is quiesced | Capture `SERDATR` byte/status before clearing RBF; drain while still asserted | No lost leading byte |
| Final close with pending READ | Last opener closes while READ is retained | Resolve request before vector/resource teardown | No ISR access after teardown |
| Close/expunge | Open device with armed or quiesced receive | Mask RBF after request resolution; restore vector/enables only if still ours; release `MR_SERIALBITS` then `MR_SERIALPORT` | Delayed expunge waits for final close; do not overwrite a stolen vector |
| Ring vs hardware overrun | Paula overrun or private ring full | Public overrun latched; private cause retained separately | Diagnostic state remains distinguishable |

</frozen-after-approval>

## Code Map

Draft (rewrite, do not patch in place): `claim_paula` at `fujinet_serial_device.c:178` mutates Paula with no `misc.resource`; `cmd_read` at `:221` completes immediately including 0 bytes; `device_abort_io` at `:446` is a no-op; `cmd_flush` at `:311` calls `rbf_disable` and uninstalls the vector; `release_paula` at `:158` writes SERPER=9600 and restores the vector unconditionally; delayed expunge at `:384` is the keepable skeleton. ISR `fujinet_serial_rbf.S:18` samples then double-acks, one byte per entry, NOP+RTS, no INTEN check, no drain, no `Cause()`. Offsets `fujinet_serial_rbf_off.h:9` (`2146`–`2156`) die with that ISR.

Reuse: `fujinet_paula_uart.c:5` SERPER/SERDAT/ring (host tests `test_fujinet_paula_uart.c:22` expect NTSC 9600=371, PAL 19200=183, PAL 38400=91). Split `rx.overrun` into `hardware_overrun_latched` / `software_ring_overflow_latched`. Add host-testable lifecycle C (`serial.device/fujinet_serial_lifecycle.c` + `amiga/tests/test_fujinet_serial_lifecycle.c` wired from `amiga/tests/Makefile:14`) for the named cases in `lifecycle.md`. Keep `fujinet_serial_device.h` name/unit 0 and the Exec Resident/open/close/expunge vector table shape.

Read-only: broker `fujinet_nio_serial_backend.c:89` SendIO READ + 5s timer AbortIO, post-exchange FLUSH at `:577`; SET_SERIAL ABI in `fujinet_nio_serial_config.h`; install lists; Amiberry `test_nio_paula_serial.py` size 256. Hardware truth: `docs/amiga/Serial-IO-Interface.md` Table 8-9 (sample then ack once). Handshake: `docs/amiga/rs232-paula-and-cia-handshake.md` (claim `MR_SERIALBITS`, do not drive CIA-B). Record lifecycle in `docs/amiga/rs232-cold-warm-hardware-test.md` without changing matrix commands.

## Tasks & Acceptance

**Execution:**
- [ ] `amiga/serial.device/fujinet_serial_device.c`, `fujinet_serial_rbf.S`, `fujinet_serial_lifecycle.c`, and related private headers -- replace ownership and request lifecycle. Claim `MR_SERIALPORT` then `MR_SERIALBITS` before Paula/vector changes; RBF handler only rings and `Cause()`s (drain while asserted, one ack per byte); complete pending READ on a device-owned software interrupt; atomically arbitrate deferred completion/abort/flush/close; restore the vector only if it is still ours; release BITS then PORT; drop duplicate ack/NOP and `fujinet_serial_rbf_off.h`.
- [ ] `amiga/serial.device/fujinet_paula_uart.c` and `amiga/tests/` -- keep SERPER/ring math; split overrun latches; add named lifecycle cases from `lifecycle.md` to `make tests`.
- [ ] `_bmad-output/specs/spec-amiga-fujinet-serial-device/` and `repos/fujinet-nio-driver/docs/amiga/rs232-cold-warm-hardware-test.md` -- record chosen READ/RBF lifecycle, always-armed fallback, and PiStorm-only CAP-5 without changing commands.
- [ ] Preserve SET_SERIAL, install-list, `--devs-file`, share, ADF/FTP, and `nio-paula-serial` wiring; touch only if verification exposes a regression.

**Acceptance Criteria:**
- Given a clean wb32 A1200-030 test image, when the focused Paula case loads and selects `fujinet-serial.device`, then clock and size-256 FileDevice marker complete with result 0 while default cases remain on `serial.device`.
- Given the operator's isolated PiStorm, when the 19200 cold one-shot runs, then it prints result/status 0 and returns to Shell without a power-LED flash or reboot screen.

## Spec Change Log

- 2026-09-07: Folded long pre-implementation review into SPEC.md, new `lifecycle.md`, companions, and this artifact (misc.resource, exclusive Exec RBF handler ABI, SERPER-not-restored, pending-READ ownership, named native tests).
- 2026-09-07: Recorded Paula-vs-CIA-B handshake map (`docs/amiga/rs232-paula-and-cia-handshake.md`); this cut claims `MR_SERIALBITS` but does not drive RTS/CTS.

## Design Notes

Host tests drive a pure-C lifecycle model (claim order, READ ownership, sample-then-ack drain, FLUSH rearm). The assembler ISR is a twin of that drain plus a `Cause()` tail, not a caller of C. `_LVOCause` needs `A6=SysBase`; Exec already lists `A6` as interrupt-handler scratch. Use `A6` only for that call. The sample/retain/ack loop stays `D0-D1/A0-A1`. Do not write SERPER on close.

Paula ownership lasts from successful `misc.resource` acquisition through final close. `CMD_FLUSH` aborts a retained READ with `IOERR_ABORTED`, clears RX, and masks RBF without returning the vector. The next WRITE, READ, or QUERY rearms it before the first new `SERDAT` byte, sampling a pending RBF first. Always-armed receive is the documented PiStorm fallback only.

```text
NEW -> PENDING -> COMPLETING|ABORTING -> REPLIED
```

Exactly one path leaves `PENDING`; exactly one `ReplyMsg()`. `Disable()`/`Enable()` around the transition. Final close: stop new transitions, resolve retained READ, mask RBF, drain pending receive, restore vector only if still ours, free BITS then PORT.

## Verification

**Commands:**
- `source "$NIO_WORKSPACE/scripts/env.sh" && make -C repos/fujinet-nio-driver/amiga tests` -- SERPER/ring plus named lifecycle cases pass.
- `source "$NIO_WORKSPACE/scripts/env.sh" && make -C repos/fujinet-nio-driver/amiga native` -- device and retained broker/tools build.
- `source "$NIO_WORKSPACE/scripts/env.sh" && uv run pytest --run-amiga --amiga-env wb32 --amiga-machine a1200-030 integration-tests/amiberry/test_nio_paula_serial.py::test_paula_serial_clock` -- only this Amiberry node.

**Manual checks:**
- Operator runs `fujinet-nio-exchange --type clock --backend cold --baud 19200 --serial-device fujinet-serial.device --trials 1` on PiStorm; result/status is 0 and Shell remains usable.
