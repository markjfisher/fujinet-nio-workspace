---
title: 'Amiga FujiNet Paula serial device rewrite'
type: 'feature'
created: '2026-09-07'
status: 'draft'
review_loop_iteration: 0
context:
  - '{project-root}/_bmad-output/specs/spec-amiga-fujinet-serial-device/SPEC.md'
  - '{project-root}/_bmad-output/specs/spec-amiga-fujinet-serial-device/lifecycle.md'
  - '{project-root}/docs/agent-test-policy.md'
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** The draft `fujinet-serial.device` completes an Amiberry exchange and printed success on PiStorm, but its guessed RBF interrupt teardown then rebooted the PiStorm machine. The broker needs an opt-in, FujiNet-owned Exec serial device that services Paula receive deadlines without disturbing Kickstart `serial.device`.

**Approach:** Rewrite Paula ownership and the `IOExtSer` command subset as an explicit acquire/open/request/flush/close lifecycle. Preserve runtime SET_SERIAL/GET_SERIAL selection, install surfaces, host UART math, and the existing focused Amiberry case; make `CMD_READ` wait when data is not yet available and support timer-driven `AbortIO`. Direct Paula UART control; do not replace Kickstart `serial.device`. PiStorm remains the sole hardware-stability acceptance gate.

## Boundaries & Constraints

**Always:** Use the print-validated in-tree Paula extracts as hardware truth; compile for 68000 with soft-float; keep `fujinet-serial.device` unit 0 exclusive; keep SET_SERIAL/GET_SERIAL ABI, `fujinet-nio-serial`, install lists, and default `serial.device` unit 0.

Acquire the built-in serial hardware through `misc.resource` before changing Paula serial registers, serial interrupt enables, or the RBF vector. Fail open cleanly if the required serial resources are already owned.

Treat `INTB_RBF` as an exclusive Exec interrupt handler installed with `SetIntVector()`. By project policy use only `D0-D1/A0-A1` as ISR scratch and preserve all other registers. Exec also permits `A5/A6` as handler scratch; this handler does not require them. This is the RBF interrupt-handler boundary, not an interrupt-server chain.

Service each RBF exactly as: read `SERDATR`, retain byte/status, clear `INTF_RBF` once. Never acknowledge first. Never use the rejected duplicate-`INTREQ`/NOP sequence. Apply the same order to pending-RBF during rearm or teardown.

Pending READ completion, `AbortIO`, `CMD_FLUSH`, and final close must use one atomic request-ownership transition and produce at most one reply.

Preserve/restore the prior RBF vector and relevant interrupt-enable state exactly once. Do not claim to restore a previous `SERPER` divisor.

Keep distinct private latches `hardware_overrun_latched` and `software_ring_overflow_latched`; public status may collapse them. SETPARAMS accepted range is 300–230400; FujiNet hardware acceptance matrix is 9600 / 19200 / 38400 only. PiStorm is the sole hardware-stability gate.

**Ask First:** Any need to change broker public ABI, Stage 3/4 backend lifetime, ESP pacing, installation names, the default backend, or the 9600/19200/38400 acceptance matrix.

**Never:** Rename, expunge, patch, or replace Kickstart `serial.device`; use CIA serial-shift behavior; acknowledge twice, acknowledge before `SERDATR`, or retain the draft NOP rationale; claim Amiberry proves PiStorm stability; add 57600 or hardware flow control; restore write-only `SERPER`; treat exclusive open of this device as a substitute for `misc.resource`.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|---------------|----------------------------|----------------|
| Open/configure | Unit 0, exclusive; SETPARAMS 300–230400 8N1 | Claim misc serial resources before Paula/vector access; preserve RBF vector/enable state and program a divisor | Reject other units, second open of this device, invalid baud/parity/word/stop; release partial claims only |
| Paula ownership conflict | Stock `serial.device` already owns serial hardware | `fujinet-serial.device` open fails without touching Paula/RBF/`SERPER`/INTENA | Clean open failure; no partial ownership |
| Stock access while FujiNet owns Paula | `fujinet-serial.device` holds `misc.resource` | Stock serial must not manipulate the UART concurrently | Ownership remains exclusive |
| Receive | READ with enough queued bytes or bytes arriving later | Copy requested bytes, complete it once; QUERY reports queued count/status | Retained READ is atomically owned by exactly one of RBF completion, AbortIO, FLUSH, or close |
| READ vs AbortIO race | Final requested byte arrives while `AbortIO()` runs | Exactly one completion owner and one reply | No duplicate reply, stale pointer, or lost ownership |
| FLUSH with pending READ | READ retained by device | Cancel READ once, clear queue, quiesce RBF, retain Paula ownership | READ completes `IOERR_ABORTED` |
| Exchange lifecycle | WRITE after open/flush, then QUERY/READ, then FLUSH | Rearm RBF before first TX byte; during rearm sample pending `SERDATR` before clearing RBF | Always-armed receive is documented PiStorm fallback only |
| Rearm with pending RBF | RBF condition exists while receive is quiesced | Capture `SERDATR` byte/status before clearing RBF | No lost leading byte |
| Final close with pending READ | Last opener closes while READ is retained | Resolve request before vector/resource teardown | No ISR access after teardown |
| Close/expunge | Open device with armed or quiesced receive | Mask RBF after request resolution; restore vector/enables; release `misc.resource` once | Delayed expunge waits for final close |
| Ring vs hardware overrun | Paula overrun or private ring full | Public overrun latched; private cause retained separately | Diagnostic state remains distinguishable |

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
- [ ] `amiga/serial.device/fujinet_paula_uart.c` and `amiga/tests/` -- preserve valid math/ring behavior and add the named lifecycle cases in `lifecycle.md`: misc.resource ownership conflict; partial-open rollback; single acquisition / single release; RBF handler register contract; read-SERDATR-before-ack ordering; single acknowledgement; FLUSH -> WRITE rearm ordering; rearm with already-pending RBF; blocking READ satisfied later; AbortIO before data; AbortIO vs final-byte race; FLUSH with pending READ; final close with pending READ; hardware overrun latch; software ring overflow latch; one-time teardown / delayed expunge.
- [ ] `_bmad-output/specs/spec-amiga-fujinet-serial-device/` and `repos/fujinet-nio-driver/docs/amiga/rs232-cold-warm-hardware-test.md` -- record the chosen READ/RBF lifecycle, its always-armed alternative, and PiStorm-only CAP-5 gate without changing commands.
- [ ] Preserve existing SET_SERIAL, install-list, `--devs-file`, share, ADF/FTP, and `nio-paula-serial` wiring; modify only if verification exposes a regression.

**Acceptance Criteria:**
- Given a clean wb32 A1200-030 test image, when the focused Paula case loads and selects `fujinet-serial.device`, then clock and size-256 FileDevice marker complete with result 0 while default cases remain on `serial.device`.
- Given the operator's isolated PiStorm, when the 19200 cold one-shot runs, then it prints result/status 0 and returns to Shell without a power-LED flash or reboot screen.

## Spec Change Log

- 2026-09-07: Folded long pre-implementation review into SPEC.md, new `lifecycle.md`, companions, and this artifact (misc.resource, exclusive Exec RBF handler ABI, SERPER-not-restored, pending-READ ownership, named native tests).

## Design Notes

Paula ownership lasts from successful `misc.resource` acquisition through final close. `CMD_FLUSH` atomically aborts a retained READ with `IOERR_ABORTED`, clears RX, and masks/quiesces RBF without returning the vector; the next WRITE, READ, or QUERY rearms it, with RBF armed before the first new TX byte. Rearming samples a pending receive before clearing RBF, so no leading byte is discarded. This minimizes idle interrupt exposure while retaining warm broker ownership. Continuous RBF arming remains a documented PiStorm fallback if rearm latency or a lost leading byte is demonstrated.

`CMD_READ` follows stock waiting semantics because the broker already supplies timer AbortIO and immediate zero-byte completion creates a race after QUERY.

```text
NEW
  |
  v
PENDING
  | \
  |  \ AbortIO / FLUSH / Close
  |   \
  v    v
COMPLETING / ABORTING
       |
       v
     REPLIED
```

Exactly one path may leave `PENDING`; exactly one `ReplyMsg()` may occur. Protect the transition with `Disable()`/`Enable()` or equivalent.

Final teardown:

```text
stop accepting new ownership transitions
    ->
resolve/cancel retained READ exactly once
    ->
mask RBF
    ->
handle/clear any required pending receive state safely
    ->
restore previous RBF vector / interrupt-enable state
    ->
release misc.resource ownership
    ->
finish CloseDevice
```

No ISR-visible pointer to an IORequest or device-private state may remain after vector removal.

## Verification

**Commands:**
- `source "$NIO_WORKSPACE/scripts/env.sh" && make -C repos/fujinet-nio-driver/amiga tests` -- all host tests, including SERPER/ring and named lifecycle cases, pass.
- `source "$NIO_WORKSPACE/scripts/env.sh" && make -C repos/fujinet-nio-driver/amiga native` -- builds the device and retained broker/tools with the Amiga toolchain.
- `source "$NIO_WORKSPACE/scripts/env.sh" && uv run pytest --run-amiga --amiga-env wb32 --amiga-machine a1200-030 integration-tests/amiberry/test_nio_paula_serial.py::test_paula_serial_clock` -- only the requested Amiberry node passes.

**Manual checks:**
- Operator runs `clock --type clock --backend cold --baud 19200 --serial-device fujinet-serial.device --trials 1` on PiStorm; result/status is 0 and Shell remains usable.
