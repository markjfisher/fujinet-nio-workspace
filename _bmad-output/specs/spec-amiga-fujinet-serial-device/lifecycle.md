# Lifecycle: ownership, RBF, pending READ

Owning repo: `repos/fujinet-nio-driver`. Diagrams, teardown order, edge-case matrix, and named native tests for `fujinet-serial.device`. Kernel constraints in `SPEC.md` cite this companion.

## misc.resource open/close

Exclusive open of `fujinet-serial.device` only protects this device from a second open. It does not stop another task from opening Kickstart `serial.device` and touching the same Paula UART.

On first open, in this order:

1. `AllocMiscResource(MR_SERIALPORT)`.
2. `AllocMiscResource(MR_SERIALBITS)`.
3. If either fails: free only resources this open acquired; fail `OpenDevice()` with no change to `SERPER`, serial interrupt enables, or `INTB_RBF`. Do not `RemDevice` another owner.
4. Only after both claims succeed: save the previous `INTB_RBF` handler and relevant RBF interrupt-enable state, then program `SERPER` / enable RBF / install the FujiNet handler with `SetIntVector()`.

On final close:

```text
stop accepting new ownership transitions
    ->
resolve/cancel retained READ exactly once (deferred path or AbortIO path, not the RBF handler)
    ->
mask RBF
    ->
handle/clear any required pending receive state safely
    (if INTEN is live: read SERDATR, retain byte/status, clear INTF_RBF once;
     repeat while INTF_RBF remains asserted)
    ->
if current INTB_RBF vector is still the FujiNet handler:
    restore the saved previous handler and relevant interrupt-enable state
else:
    do not overwrite the vector
    ->
FreeMiscResource(MR_SERIALBITS)
    ->
FreeMiscResource(MR_SERIALPORT)
    ->
finish CloseDevice
```

Do not expunge, rename, patch, or otherwise steal ownership from Kickstart `serial.device`. Do not restore a previous `SERPER` divisor: it cannot be read back.

While `fujinet-serial.device` owns Paula, stock serial access must not result in both drivers manipulating the UART concurrently. `misc.resource` ownership is the mechanism; do not share the UART.

`MR_SERIALPORT` is Paula (TXD/RXD). `MR_SERIALBITS` is CIA-B port A (RTS/CTS/DTR and the other modem lines). This cut claims both and programs Paula only. Do not write CIA-B PRA/DDRA handshake bits here. Seven-wire later is additive CIA + `SERF_7WIRE` at open + ESP CTS/RTS; it does not change the RBF handler. See `docs/amiga/rs232-paula-and-cia-handshake.md`.

## RBF interrupt-handler boundary

`INTB_RBF` is installed with `SetIntVector()`, so this is an exclusive Exec interrupt handler, not an interrupt-server chain entry.

For an Exec interrupt handler, `D0`, `D1`, `A0`, `A1`, `A5`, and `A6` are scratch; all other registers must be preserved.

This exclusive `SetIntVector()` handler uses Exec’s entry registers: `D1` = INTENA & INTREQ, `A0` = custom-chip base, `A1` = `is_Data`, `A6` = SysBase. Keep `A0` as the custom base and use `A5` as the RX/TX store pointer. `_LVOCause` is invoked with SysBase already in `A6`. Return with `RTS`, not `RTE`.

The handler must stay short. It must not `ReplyMsg()`, `CopyMem` into the caller’s IORequest, call Exec (except `_LVOCause`), or transition a pending READ out of `PENDING`.

Required servicing order:

```text
if Exec D1 does not show INTB_RBF:
    return without acknowledging

while INTF_RBF is asserted (entry from D1; later iterations from INTREQR):
    read SERDATR
        ->
    clear INTF_RBF once
        ->
    record OVRUN/status and the received byte into the private ring
        (set hardware_overrun_latched or software_ring_overflow_latched as required)
        ->
    if a pending READ can now be satisfied:
        Cause() a device-owned software interrupt via A6
        (do not complete the IORequest here)

return
```

One acknowledgement per byte. Never clear RBF before sampling `SERDATR`. Never test `SERDATR_RBF` after RBF was already established by Exec `D1` or `INTREQR`. Never use the rejected duplicate-`INTREQ`/NOP acknowledgement. Apply the same sample-then-ack order when rearming or tearing down a pending RBF condition.

`CMD_WRITE` must rearm RBF and enable CPU interrupts before the first `SERDAT` load or TBE enable. Do not FLUSH, clear-without-read, reset the RX ring, or rearm RBF after TX begins. TBE level 1 may be preempted by RBF level 5; keep RBF enabled for the whole request. After the extra TBE that follows the final `SERDAT` load (`OFF_TX_REM == 0`), disable TBE in `INTENA` (SET/CLR=0). `OFF_TX_DONE` means the final byte left `SERDAT` into the transmit shift register, not that `TSRE` is set.

The drain loop exists so a burst already pending in Paula is taken before the handler returns. Returning while `INTF_RBF` is still asserted livelocks interrupt level 5.

Deferred completion uses a software interrupt the device owns. Do not attach that work to `INTB_PORTS` (CIA/keyboard/timer traffic). The software-interrupt routine (or a task path started from that `Cause`) is the RBF-side completion owner: it copies from the private ring into the IORequest, performs the one-owner `PENDING` → `COMPLETING` → `REPLIED` transition, and `ReplyMsg()`s.

## Exchange receive arming

Selected lifecycle (PiStorm fallback taken 2026-09-07):

```text
exchange completes
    -> FLUSH
    -> pending READ aborted, software queue cleared
    -> RBF stays armed

next exchange
    -> WRITE drains leftover SERDATR, discards the software queue, rearms
       RBF if needed, enables interrupts, then TX via TBE
    -> FujiNet response arrives into the still-armed receiver
    -> FujiNet response arrives into the still-armed receiver
```

FLUSH-quiesce plus rearm-before-TX lost the first 38400 request after idle
(cold `cause=4` 13.7 s timeout, warm WARMUP `nio=6`, FLS single-shot fail)
with and without ESP 16/2000 pacing. Later trials in the same command
succeeded after timeout closed and reopened the backend. Always-armed
receive is now the production path. Close still masks RBF.

Always-armed did not fix the same first-request timeout after a clean
reboot. Open had been programming `DEVICE_BAUD_DEFAULT` 19200, then
`SETPARAMS` jumped to 38400. 19200 first-open worked because that jump
never happened. Open now programs `io_Baud` from the `OpenDevice` request
(broker fills it before `OpenDevice`). `SETPARAMS` waits for TX idle
(`TSRE`, RBF masked), writes `SERPER` once, discards RX garbage, and
re-arms before return. The broker still issues `SETPARAMS` after open.

If WRITE finds an RBF condition already pending: sample `SERDATR` and
retain, then discard the software queue so idle/late bytes are not parsed
as the next frame. Do not mask RBF around that drain or around the
following TX. Transmit is a TBE interrupt that writes `SERDAT` without
reading `SERDATR`. Polling `SERDATR` TBE under `Disable()` lost the
opening SLIP END (`0xC0`) of the first 38400 response.

## Pending CMD_READ ownership

`CMD_READ` waits until the requested byte count is available (stock-like). Immediate 0-byte completion is rejected.

```text
NEW
  |
  v
PENDING
  | \
  |  \ AbortIO / FLUSH / Close
  |   \
  v    v
COMPLETING / ABORTING     <-- deferred software interrupt is the RBF-side owner
       |                    (not the RBF handler itself)
       v
     REPLIED
```

Exactly one path may transition a pending READ out of `PENDING` and exactly one `ReplyMsg()` may occur. Protect the transition with `Disable()`/`Enable()` or equivalent so the deferred completion path and task-level `AbortIO()` cannot both complete the same request.

`CMD_FLUSH` with a pending READ: same single-owner cancellation path as `AbortIO`, complete with `IOERR_ABORTED`, then clear the software receive queue. RBF stays armed. Must not leave a retained IORequest pointer referring to discarded queue state. Paula/`misc.resource` ownership is retained.

Final close must resolve any retained READ through that same path before vector removal or resource release. No ISR-visible pointer to an IORequest or device-private state may remain after vector removal.

Timer-driven `AbortIO` remains the broker’s timeout mechanism.

## Overrun causes

Private:

```text
hardware_overrun_latched     <- Paula SERDATR overrun status
software_ring_overflow_latched <- private receive ring had no free slot
```

Public QUERY/status may collapse both into the existing overrun indication. Host/native tests should be able to distinguish the private causes.

## Baud ranges

```text
SETPARAMS accepted range:        300 .. 230400
FujiNet hardware acceptance:     9600 / 19200 / 38400
```

Do not extend the hardware matrix without asking. Use the AHRM-extract SERPER formula, not a substitute divisor table.

## Edge-case matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
| --- | --- | --- | --- |
| Paula ownership conflict | Stock `serial.device` already owns serial hardware | `fujinet-serial.device` open fails without touching Paula/RBF/`SERPER`/INTENA | Clean open failure; no partial ownership; no `RemDevice` of the owner |
| Stock access while FujiNet owns Paula | `fujinet-serial.device` holds `misc.resource` | Stock serial must not manipulate the UART concurrently | Ownership remains exclusive; no dual-driver UART access |
| BITS claim fails after PORT | `MR_SERIALPORT` acquired, `MR_SERIALBITS` busy | Free `MR_SERIALPORT` only; fail open | No Paula/RBF mutation |
| READ vs AbortIO race | Final requested byte arrives while `AbortIO()` runs | Deferred completion path and `AbortIO` compete; exactly one owner and one reply | No duplicate reply, stale pointer, or lost ownership |
| FLUSH with pending READ | READ retained by device | Cancel READ once, clear queue, keep RBF armed, retain Paula ownership | READ completes `IOERR_ABORTED` |
| WRITE after FLUSH | Idle or late bytes may sit in SERDATR | Drain then discard the software queue; RBF stays armed; TX via TBE interrupt | First 38400 request after idle is not masked; opening response `C0` is not dropped |
| Open at 38400 | `OpenDevice` `io_Baud` is 38400 | Claim programs 38400 once; no 19200 detour | Default 19200 only if request baud is out of range |
| SETPARAMS rate change | TX may still be shifting; RX may hold divisor-change garbage | Wait `TSRE` with RBF masked, apply `SERPER`, discard RX, re-arm | First TX after settle is at the requested rate |
| Burst already pending in Paula | Handler entered with more than one RBF byte ready | Drain: sample/retain/ack-once per byte until `INTF_RBF` is clear | Returning with RBF still asserted is a livelock |
| RBF handler vs ReplyMsg | Byte(s) satisfy a pending READ | Handler only rings + `Cause()`s; software interrupt copies and replies | No `ReplyMsg` or IORequest mutation on the RBF handler path |
| Final close with pending READ | Last opener closes while READ is retained | Resolve request before vector/resource teardown | No ISR access after teardown |
| Vector no longer ours | Close finds `INTB_RBF` is not the FujiNet handler | Do not overwrite the vector; still mask RBF and free `misc.resource` | No stolen-vector restore |
| Ring vs hardware overrun | Paula overrun or private ring full | Public overrun latched; private cause retained separately | Diagnostic state remains distinguishable |
| Partial-open rollback | Claim or vector install fails after a partial acquisition | Release only resources this open acquired (`BITS` then `PORT` if both were taken) | Paula/RBF/INTENA left as found |
| Second open of this device | Unit 0 already exclusive-open | Reject the second open | First opener unchanged |

## Named native tests

Focused host/native coverage must include:

```text
misc.resource ownership conflict
MR_SERIALPORT then MR_SERIALBITS claim order
partial-open rollback (BITS fail frees PORT only)
single acquisition / single release (BITS then PORT)
RBF handler register contract
read-SERDATR-before-ack ordering
single acknowledgement per byte
drain while INTF_RBF still asserted
handler does not ReplyMsg or mutate IORequest
Cause-deferred READ completion
FLUSH keeps RBF armed
WRITE drains leftover RBF then discards idle queue
WRITE TX uses TBE interrupt (RBF stays live; no SERDATR TBE poll)
WRITE Enable then TBE (RBF armed before first SERDAT)
RBF uses Exec D1/A0/A6; A5 store pointer; sample-then-ack; no SERDATR_RBF test
open programs requested baud (no 19200 then 38400 detour)
SETPARAMS waits TX idle, applies SERPER, discards RX garbage
blocking READ satisfied later
AbortIO before data
AbortIO vs final-byte race (deferred path vs AbortIO)
FLUSH with pending READ
final close with pending READ
restore vector only if still ours
hardware overrun latch
software ring overflow latch
one-time teardown / delayed expunge
```

Host coverage lives in `amiga/tests/test_fujinet_serial_lifecycle.c` driving
`serial.device/fujinet_serial_lifecycle.c`. The assembler RBF handler in
`fujinet_serial_rbf.S` is a twin of that drain plus a `Cause()` tail; it is
not a caller of C. Always-armed receive is the production path; close still
masks RBF. Open programs the `OpenDevice` `io_Baud` (default 19200 only when
the request baud is out of range).
