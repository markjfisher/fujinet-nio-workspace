# Lifecycle: ownership, RBF, pending READ

Owning repo: `repos/fujinet-nio-driver`. Diagrams, teardown order, edge-case matrix, and named native tests for `fujinet-serial.device`. Kernel constraints in `SPEC.md` cite this companion.

## misc.resource open/close

Exclusive open of `fujinet-serial.device` only protects this device from a second open. It does not stop another task from opening Kickstart `serial.device` and touching the same Paula UART.

On first open:

1. Claim the Amiga serial hardware through `misc.resource` (`MR_SERIALPORT` and the required serial-control resource(s)).
2. If already owned, fail `OpenDevice()` with no change to `SERPER`, serial interrupt enables, or `INTB_RBF`.
3. Only after a successful claim: save the previous `INTB_RBF` handler and relevant RBF interrupt-enable state, then program `SERPER` / enable RBF / install the FujiNet handler with `SetIntVector()`.

On final close:

```text
stop accepting new ownership transitions
    ->
resolve/cancel retained READ exactly once
    ->
mask RBF
    ->
handle/clear any required pending receive state safely
    (read SERDATR, retain byte/status, then clear INTF_RBF once)
    ->
restore previous RBF vector / interrupt-enable state
    ->
release misc.resource ownership exactly once
    ->
finish CloseDevice
```

Do not expunge, rename, patch, or otherwise steal ownership from Kickstart `serial.device`. Do not restore a previous `SERPER` divisor: it cannot be read back.

While `fujinet-serial.device` owns Paula, stock serial access must not result in both drivers manipulating the UART concurrently. `misc.resource` ownership is the mechanism; do not share the UART.

## RBF interrupt-handler boundary

`INTB_RBF` is installed with `SetIntVector()`, so this is an exclusive Exec interrupt handler, not an interrupt-server chain entry.

For an Exec interrupt handler, `D0`, `D1`, `A0`, `A1`, `A5`, and `A6` are scratch; all other registers must be preserved.

By project policy the FujiNet handler may use only `D0-D1/A0-A1` as scratch and must preserve all other registers. Exec also permits `A5/A6` as handler scratch, but this handler does not require them. Return with `RTS`, not `RTE`.

Every serviced RBF event:

```text
read SERDATR
    ->
record received byte and status
    ->
clear INTF_RBF once
```

Never clear RBF before sampling `SERDATR`. Never use the rejected duplicate-`INTREQ`/NOP acknowledgement. Apply the same order when rearming or tearing down a pending RBF condition.

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

If rearm finds an RBF condition already pending: sample `SERDATR` and retain byte/status before clearing the pending interrupt.

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
COMPLETING / ABORTING
       |
       v
     REPLIED
```

Exactly one path may transition a pending READ out of `PENDING` and exactly one `ReplyMsg()` may occur. Protect the transition with `Disable()`/`Enable()` or equivalent so the ISR and task-level `AbortIO()` cannot both complete the same request.

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

Do not extend the hardware matrix without asking.

## Edge-case matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
| --- | --- | --- | --- |
| Paula ownership conflict | Stock `serial.device` already owns serial hardware | `fujinet-serial.device` open fails without touching Paula/RBF/`SERPER`/INTENA | Clean open failure; no partial ownership |
| Stock access while FujiNet owns Paula | `fujinet-serial.device` holds `misc.resource` | Stock serial must not manipulate the UART concurrently | Ownership remains exclusive; no dual-driver UART access |
| READ vs AbortIO race | Final requested byte arrives while `AbortIO()` runs | Exactly one completion owner and one reply | No duplicate reply, stale pointer, or lost ownership |
| FLUSH with pending READ | READ retained by device | Cancel READ once, clear queue, quiesce RBF, retain Paula ownership | READ completes `IOERR_ABORTED` |
| Rearm with pending RBF | RBF condition exists while receive is quiesced | Capture `SERDATR` byte/status before clearing RBF | No lost leading byte |
| FLUSH then WRITE | Quiesced after FLUSH, new request starts | RBF armed before the first byte is written to `SERDAT` | No TX while receive is still masked |
| Final close with pending READ | Last opener closes while READ is retained | Resolve request before vector/resource teardown | No ISR access after teardown |
| Ring vs hardware overrun | Paula overrun or private ring full | Public overrun latched; private cause retained separately | Diagnostic state remains distinguishable |
| Partial-open rollback | Claim or vector install fails after a partial acquisition | Release only resources this open acquired | Paula/RBF/INTENA left as found |
| Second open of this device | Unit 0 already exclusive-open | Reject the second open | First opener unchanged |

## Named native tests

Focused host/native coverage must include:

```text
misc.resource ownership conflict
partial-open rollback
single acquisition / single release
RBF handler register contract
read-SERDATR-before-ack ordering
single acknowledgement
FLUSH -> WRITE rearm ordering
rearm with already-pending RBF
blocking READ satisfied later
AbortIO before data
AbortIO vs final-byte race
FLUSH with pending READ
final close with pending READ
hardware overrun latch
software ring overflow latch
one-time teardown / delayed expunge
```
