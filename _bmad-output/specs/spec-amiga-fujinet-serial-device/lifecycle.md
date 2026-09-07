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

By project policy the FujiNet handler may use only `D0-D1/A0-A1` as scratch and must preserve all other registers. Exec also permits `A5/A6` as handler scratch, but this handler does not require them. Return with `RTS`, not `RTE`.

The handler must stay short. It must not `ReplyMsg()`, `CopyMem` into the caller’s IORequest, call Exec (except what an interrupt handler is already in), or transition a pending READ out of `PENDING`.

Required servicing order:

```text
if master INTEN is clear:
    return without acknowledging

while INTF_RBF is asserted:
    read SERDATR
        ->
    record OVRUN/status and the received byte into the private ring
        (set hardware_overrun_latched or software_ring_overflow_latched as required)
        ->
    clear INTF_RBF once
        ->
    if a pending READ can now be satisfied:
        Cause() a device-owned software interrupt
        (do not complete the IORequest here)

return
```

One acknowledgement per byte. Never clear RBF before sampling `SERDATR`. Never use the rejected duplicate-`INTREQ`/NOP acknowledgement. Apply the same sample-then-ack order when rearming or tearing down a pending RBF condition.

The drain loop exists so a burst already pending in Paula is taken before the handler returns. Returning while `INTF_RBF` is still asserted livelocks interrupt level 5.

Deferred completion uses a software interrupt the device owns. Do not attach that work to `INTB_PORTS` (CIA/keyboard/timer traffic). The software-interrupt routine (or a task path started from that `Cause`) is the RBF-side completion owner: it copies from the private ring into the IORequest, performs the one-owner `PENDING` → `COMPLETING` → `REPLIED` transition, and `ReplyMsg()`s.

## Exchange receive arming

Selected lifecycle:

```text
exchange completes
    -> FLUSH
    -> RBF quiesced

next exchange
    -> WRITE/READ/QUERY rearms RBF
    -> request is transmitted
    -> FujiNet response arrives
```

Rearm RBF before the first byte of the new request is written to `SERDAT`. Because FujiNet is request/response, that should avoid a legitimate receive window while RBF is masked.

If rearm finds an RBF condition already pending: sample `SERDATR` and retain byte/status before clearing the pending interrupt; repeat while `INTF_RBF` remains asserted.

Always-armed receive is the documented PiStorm fallback if testing shows lost leading response bytes or unacceptable rearm latency. Do not switch to it without that evidence.

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

`CMD_FLUSH` with a pending READ: same single-owner cancellation path as `AbortIO`, complete with `IOERR_ABORTED`, then clear the software receive queue and quiesce RBF. Must not leave a retained IORequest pointer referring to discarded queue state. Paula/`misc.resource` ownership is retained.

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
| FLUSH with pending READ | READ retained by device | Cancel READ once, clear queue, quiesce RBF, retain Paula ownership | READ completes `IOERR_ABORTED` |
| Rearm with pending RBF | RBF condition exists while receive is quiesced | Capture `SERDATR` byte/status before clearing RBF; drain while still asserted | No lost leading byte |
| FLUSH then WRITE | Quiesced after FLUSH, new request starts | RBF armed before the first byte is written to `SERDAT` | No TX while receive is still masked |
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
FLUSH -> WRITE rearm ordering
rearm with already-pending RBF
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
not a caller of C. Always-armed receive remains the documented PiStorm
fallback only and is not the implemented default.
