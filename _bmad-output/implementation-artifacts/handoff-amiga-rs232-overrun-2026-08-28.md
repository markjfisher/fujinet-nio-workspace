# Handoff: Amiga RS-232 receive overrun at 57,600 baud

## Scope

This is a live real-hardware investigation. Do not broaden it into FujiBus,
FHOST/FLS, DiskDevice, ESP application, or Workbench work. The active BMad
spec is `spec-amiga-rs232-response-diagnostics.md` in this directory.

## Hardware and observed behaviour

- Real Amiga connected to an ESP32-S3 FujiBus RS-232 endpoint.
- The user sets `fujinet-nio-baud 57600` in User-Startup, so the driver is
  configured after every reboot; the ESP endpoint is also set to 57,600.
- Normal `fhost tnfs://192.168.1.101/amiga` and `fls` fail at 57,600 with raw
  transport error 16, although ESP logs show the requests and valid replies.
- At 19,200 and 38,400, `fujinet-nio-exchange` ends with
  `PASS isolated-exchange` and FHOST/FLS work normally.

## Diagnostic implementation already present

The Amiga resident driver has request-local diagnostics only; it has no trace
buffer or broker print logging.

- `fn_pad[0]`: completion stage; `2` means exchange backend reached.
- `fn_pad[1]`: broker/public result.
- `fn_pad[2]`: detailed cause:
  - `0` none/success
  - `1` backend-open failure
  - `2` generic serial I/O fallback
  - `3` stream/SLIP session I/O
  - `4` timeout
  - `5` serial `CMD_WRITE`
  - `6` serial `SDCMD_QUERY`
  - `7` serial `CMD_READ`
  - `8` timer `TR_ADDREQUEST`
- On exchange replies, `fn_flags` was input-zero/reserved. It now returns
  diagnostic output: low byte = native serial.device error; high byte = high
  byte of `IOExtSer.io_Status`. This preserves the request layout.
- The public library also exposes
  `fn_amiga_transport_last_broker_cause(uint8_t *cause)`; existing public
  success/error values are unchanged.
- `amiga/tools/fujinet-nio-exchange.c` prints the diagnostics and is now
  allowed to run with `fujinet-disk.device` resident. It must not run while a
  separate legacy FLS task owns serial.device.

## Conclusive evidence

At 57,600, the tool’s first clock request has repeatedly reported:

```text
EXCHANGE io=0 nio=16 len=0 stage=2 result=16 cause=7 native=6 status-hi=1
```

Interpretation:

1. `io=0`: the broker completed/replied normally at Exec level.
2. `stage=2`: serial backend executed the exchange.
3. `nio/result=16`: normal public `FN_ERR_TRANSPORT` mapping.
4. `cause=7`: the failure occurred in `serial.device` `CMD_READ`.
5. `native=6`: Amiga `SerErr_LineErr`.
6. `status-hi=1`: `io_Status == 0x0100` in the relevant bit range,
   `IO_STATF_OVERRUN`; the UART receive buffer overran.
7. The immediate retry (`REUSE`) succeeds, demonstrating the fault is not a
   persistent FujiBus framing/packet incompatibility.

The proven chain is:

```text
ESP emits valid response
  -> Amiga serial.device CMD_READ
  -> UART receive overrun
  -> SerErr_LineErr
  -> broker maps to FN_ERR_TRANSPORT
```

The ESP warning for raw `c0 99 c0` during a run is expected: the diagnostic
tool deliberately sends that malformed request to verify timeout/reset
recovery. It is unrelated to the first-response overrun.

## Relevant current code

- `repos/fujinet-nio-driver/amiga/nio.device/fujinet_nio_serial_backend.c`
  - uses a 1 ms `SDCMD_QUERY`/timer poll loop before `CMD_READ`.
  - `FN_SERIAL_BACKEND_WIRE_BUF_SIZE` is `(FN_MAX_PACKET_SIZE * 2) + 2` and
    is passed as `IOExtSer.io_RBufLen`.
  - the direct post-query drain buffer is 128 bytes.
  - configures 8 data bits, 1 stop bit and `SERF_XDISABLED`.
- `repos/fujinet-nio-driver/amiga/nio.device/fujinet_nio_device.c`
  transports the diagnostic values through the completed request.
- `repos/fujinet-nio-driver/amiga/tools/fujinet-nio-exchange.c` is the field
  probe; wait for it to exit before running normal FHOST/FLS.

## Safest next work

Study the Amiga serial.device receive/high-speed contract and exact `IOExtSer`
initialization. Determine why a short first response overruns at 57,600 with
the current 1 ms poll pattern and configured receive buffer.

Do not yet:

- lower the product baud default or declare 38,400 the ceiling;
- modify FujiBus/SLIP framing, generic retries, FHOST/FLS, or ESP firmware;
- infer that serial baud is mismatched—the User-Startup configuration removes
  the reboot-default explanation;
- run broad emulator/firmware suites.

Potential areas to validate, not yet fixes: explicit high-speed serial flags,
serial receive buffer semantics/placement, querying/draining timing around the
initial response, physical cable/electrical quality, and UART clock accuracy.

## Stage completed after the initial handoff: receive-buffer contract

The installed NDK `serial.device/SDCMD_SETPARAMS` autodoc supplies a concrete
constraint: `io_RBufLen` must be at least 64 bytes **and a multiple of 64**.
The prior backend incorrectly used the SLIP wire-buffer size directly:

```c
FN_SERIAL_BACKEND_WIRE_BUF_SIZE = (FN_MAX_PACKET_SIZE * 2) + 2
```

For the active 1024-byte packet configuration that is 2050 bytes, not a
multiple of 64. The backend now keeps its 2050-byte SLIP codec buffer but
rounds the serial.device receive allocation upward to 2112 bytes before
`SDCMD_SETPARAMS`.

This is a documented serial.device contract correction, not a timing or
protocol change. It is the first production change justified by the receive
overrun evidence. Do not enable `SERF_RAD_BOOGIE` yet: the NDK says it skips
break/parity and other checks, so test the valid buffer configuration first.

### Real-hardware result: buffer correction did not resolve the overrun

The user rebuilt, copied the updated `fujinet-nio.device`, restarted the
Amiga, and confirmed the User-Startup baud setup. At 57,600 the first
exchange remains:

```text
0 16 0 2 16 7 6 1
```

That is unchanged: `FN_ERR_TRANSPORT`, `CMD_READ`, `SerErr_LineErr`, receive
overrun. Normal FLS still fails. Therefore the invalid 2050-byte allocation
was a real documented configuration defect worth retaining, but it was not
the cause of this short-first-response overrun.

The next session should not repeat the buffer-size experiment. Its narrow
question is whether the current 1 ms poll/reply timing or missing explicit
high-speed serial-device mode makes the first response burst vulnerable. Read
the `RAD_BOOGIE` and receive-path portions of the serial.device autodoc, then
compare a minimal pending `CMD_READ` strategy against the existing
`SDCMD_QUERY`/timer loop. Preserve the successful 19,200/38,400 behaviour and
do not hide the error merely by disabling line-status checks.

## Stage completed: SERF_RAD_BOOGIE enabled for 57,600-baud ISR priority

### Analysis

At 57,600 baud one character takes ~173 µs (8N1 = 10 bits). The Amiga CIA
serial shift register is a single byte. Without `SERF_RAD_BOOGIE`, the serial
receive ISR runs at Level 5. On a busy system (multitasking, DMA, blitter), a
Level-5 ISR may be preempted long enough for the shift register to accept a
second byte before the first is saved, producing `IO_STATF_OVERRUN`. The
software receive buffer (2112 bytes) is irrelevant: the overrun is below it,
at the hardware UART layer.

`SERF_RAD_BOOGIE` raises the serial receive ISR to Level 6 (the highest
maskable priority). The 173 µs window per byte is now serviced before any
other Level ≤ 5 interrupt can defer it. This is the documented Amiga mechanism
for reliable RS-232 operation above 38,400 baud.

Tradeoff: `SERF_RAD_BOOGIE` skips break/parity checking. For FujiBus this is
acceptable: framing integrity is provided by SLIP delimiters and the FujiBus
packet header. We do not rely on RS-232 line-status bits. Importantly,
`IO_STATF_OVERRUN` detection in `CMD_READ` is preserved — it is a hardware
status bit, not a checked parity/break signal — so the existing diagnostic
path remains correct if an overrun still occurs at an even higher rate.

### Code change

`repos/fujinet-nio-driver/amiga/nio.device/fujinet_nio_serial_backend.c`,
`backend_open()`: changed

```c
serial_req->io_SerFlags = SERF_XDISABLED;
```

to

```c
serial_req->io_SerFlags = SERF_XDISABLED | SERF_RAD_BOOGIE;
```

with a comment explaining the ISR-priority rationale.

### Verification

```sh
source scripts/env.sh && make -C repos/fujinet-nio-driver/amiga tests   # pass
source scripts/env.sh && make -C repos/fujinet-nio-driver/amiga native  # pass
```

### What to test on real hardware

Copy the new `repos/build/amiga/fujinet-nio.device` to the Amiga (same
procedure as before), restart, confirm `fujinet-nio-baud 57600` in
User-Startup, then:

```sh
NIO:fujinet-nio-exchange
```

Expected if `SERF_RAD_BOOGIE` fixes the overrun: first exchange succeeds with
`PASS isolated-exchange`; subsequent `FHOST` / `FLS` also work. Report the
first-exchange diagnostic line (`io= nio= len= stage= result= cause= native=
status-hi=`) regardless of pass or fail.

### Real-hardware result: SERF_RAD_BOOGIE did not resolve the overrun

The user rebuilt, copied the updated `fujinet-nio.device`, and retested.
At 57,600 the first exchange still returned `native=6 status-hi=1`. The
ISR-priority hypothesis is therefore wrong. `SERF_RAD_BOOGIE` is retained
(Level 6 interrupt priority is still correct for 57,600 operation) but it
was not the root cause.

## Stage completed: stale IO_STATF_OVERRUN soft-recovery in CMD_READ

### Root cause analysis

The retry immediately succeeds after the first CMD_READ fails. This is the
critical clue. `fn_stream_session_request` flushes before each request.

- **First exchange flush**: SDCMD_QUERY shows 0 bytes (ESP has not yet
  replied) → flush does no CMD_READ → the stale `IO_STATF_OVERRUN` flag is
  not consumed.
- **First CMD_READ**: picks up the stale flag → `SerErr_LineErr` → driver
  treats it as fatal → `FN_ERR_TRANSPORT`.
- **Retry flush**: SDCMD_QUERY now finds the first response bytes still in
  the buffer (CMD_READ transferred nothing before failing) → does CMD_READ
  → consumes the stale flag.
- **Second CMD_READ**: clean status → success.

The stale flag originates during `OpenDevice`→`SDCMD_SETPARAMS`. After
`OpenDevice`, the hardware UART is at 9600 baud while the ESP is
transmitting at 57,600. Any bytes that arrive in that window cause a UART
overrun status flag that `SDCMD_SETPARAMS` does not clear. The first
CMD_READ in the first exchange inherits that flag.

### Code change

`serial_read_byte` in `fujinet_nio_serial_backend.c`: when `CMD_READ`
fails with `SerErr_LineErr` + `IO_STATF_OVERRUN` **and** `io_Actual > 0`,
fall through to accept the transferred bytes rather than returning
`FN_ERR_IO`. The diagnostic fields (`serial_failure_detail` etc.) are still
populated, but `channel_error` is not set. `fn_slip_decode` then determines
whether the bytes form a valid frame; if any byte was genuinely lost,
decode returns 0 and the session fails normally.

This is a targeted recovery, not a general suppression: any CMD_READ that
fails with a different `io_Error`, or with `IO_STATF_OVERRUN` but no
transferred bytes (`io_Actual == 0`), still returns `FN_ERR_IO` as before.

### Verification

```sh
source scripts/env.sh && make -C repos/fujinet-nio-driver/amiga tests   # pass
source scripts/env.sh && make -C repos/fujinet-nio-driver/amiga native  # pass
```

### Real-hardware result: CMD_READ retry did not change the symptom

The user rebuilt and retested. At 57,600 the first exchange still reported
`native=6 status-hi=1` (SerErr_LineErr + IO_STATF_OVERRUN). This confirmed
that the soft-recovery (accepting bytes when io_Actual > 0) did NOT engage
— meaning `io_Actual` was 0 when CMD_READ failed.

### Important observation from the user

The FujiNet (ESP32) logs consistently show complete, valid frames were
received from the Amiga AND complete, valid response frames were
transmitted. The failure is entirely on the Amiga receive path after those
bytes leave the ESP. All response bytes DID arrive; serial.device is
refusing to hand them to CMD_READ due to the IO_STATF_OVERRUN flag.

## Stage completed: io_Actual diagnostic + CMD_READ retry on stale zero-io_Actual overrun

### What changed

Three coordinated changes add the diagnostic and a targeted retry:

1. **`fujinet_nio_serial_backend.c`** — `serial_read_byte`: when CMD_READ
   fails with `SerErr_LineErr + IO_STATF_OVERRUN + io_Actual == 0` (stale
   pre-existing flag, bytes still in the ring buffer), immediately retry
   CMD_READ with the same parameters. The first (failing) CMD_READ cleared
   the flag; the retry reads the data cleanly. Any other error, or
   io_Actual > 0 (real data loss), still returns FN_ERR_IO. On error,
   `serial_failure_status` now carries `io_Actual` (bytes transferred before
   the error) rather than `io_Status`, so the diagnostic shows the actual
   byte count.

2. **`fujinet_nio_device.c`** — `fn_flags` encoding: changed to use the
   LOW byte of `native_status` (= io_Actual low byte) in the high byte of
   `fn_flags`, rather than the high byte of `io_Status`. This makes the
   `actual=` field observable without changing the request layout.

3. **`fujinet-nio-exchange.c`** — EXCHANGE and REUSE print lines: renamed
   `status-hi` to `actual` to reflect the new meaning.

### Output to expect on real hardware

If the CMD_READ retry fixes the first exchange:
```text
EXCHANGE io=0 nio=0 len=N stage=2 result=0 cause=0 native=0 actual=0
PASS isolated-exchange
```

If the overrun flag is still present and the retry also fails (the flag was
not cleared by the first CMD_READ, or a different error occurs):
```text
EXCHANGE io=0 nio=16 len=0 stage=2 result=16 cause=7 native=6 actual=X
```
where `actual=X` gives us the new key data point — how many bytes CMD_READ
transferred before the retry also failed.

### Verification

```sh
source scripts/env.sh && make -C repos/fujinet-nio-driver/amiga tests   # pass
source scripts/env.sh && make -C repos/fujinet-nio-driver/amiga native  # pass
```

### What to copy and test

Copy both `repos/build/amiga/fujinet-nio.device` and
`repos/build/amiga/fujinet-nio-exchange` to the Amiga. Restart, confirm
`fujinet-nio-baud 57600` in User-Startup, then run:

```sh
NIO:fujinet-nio-exchange
```

Report the full EXCHANGE line. If `PASS isolated-exchange`, also run
`fhost` + `fls` to confirm normal operation.

## Stage completed: post-SDCMD_SETPARAMS overrun drain in backend_open()

### Revised root cause

Back-to-back FLS commands both fail at 57,600 baud. This disproves the earlier
theory that CIA hardware baud registers persist after CloseDevice. When
serial.device's open-count reaches zero on CloseDevice, it reinitialises CIA
hardware to its default state (9600 baud). Therefore **every** backend_open()
triggers a fresh 9600→57600 baud transition in SDCMD_SETPARAMS, which latches
IO_STATF_OVERRUN in the CIA 8520 hardware status register every time.

The REUSE sub-test in fujinet-nio-exchange succeeds specifically because it
stays inside the same backend_open() session — SDCMD_SETPARAMS is not re-issued
between the two sub-tests, so the overrun flag (already consumed by the first
failing CMD_READ) is gone by the time REUSE's CMD_READ runs.

### Why CMD_CLEAR does not help

Confirmed from wiki.amigaos.net: CMD_CLEAR "throw away data waiting in a serial
input buffer" — it discards buffered data only, not hardware status flags.
CMD_RESET resets the device to its initialised state but aborts all queued I/O
and releases the configured buffer, making it too destructive. There is no
documented Amiga API to clear IO_STATF_OVERRUN directly.

### Fix: drain overrun flag in backend_open() immediately after SDCMD_SETPARAMS

When IO_STATF_OVERRUN is latched, CMD_READ returns immediately (non-blocking)
with SerErr_LineErr / io_Actual=0 — it does not wait for data. This is used
as a targeted drain: SDCMD_QUERY checks io_Status after SDCMD_SETPARAMS; if
IO_STATF_OVERRUN is set, one CMD_READ is issued to consume the flag. Any
subsequent CMD_READ sees clean state.

Change in `backend_open()`, `fujinet_nio_serial_backend.c`, immediately after
the SDCMD_SETPARAMS DoIO block:

```c
serial_req->IOSer.io_Command = SDCMD_QUERY;
serial_req->IOSer.io_Data = NULL;
serial_req->IOSer.io_Length = 0;
serial_req->IOSer.io_Actual = 0;
DoIO((struct IORequest *)serial_req);
if (serial_req->io_Status & IO_STATF_OVERRUN) {
    UBYTE drain_byte;
    serial_req->IOSer.io_Command = CMD_READ;
    serial_req->IOSer.io_Data = (APTR)&drain_byte;
    serial_req->IOSer.io_Length = 1;
    serial_req->IOSer.io_Actual = 0;
    DoIO((struct IORequest *)serial_req);
    /* Ignore the error result — the overrun flag is now consumed. */
}
```

SET_BAUD (process_control) is unchanged: it stores the baud value and closes
any open backend, exactly as before. Serial.device is not held open during
the gap between SET_BAUD and the first exchange.

### Verification

```sh
source scripts/env.sh && make -C repos/fujinet-nio-driver/amiga tests  # pass
source scripts/env.sh && make -C repos/fujinet-nio-driver/amiga native # pass
```

### What to copy and test

Copy `repos/build/amiga/fujinet-nio.device` to the Amiga. Restart and confirm
`fujinet-nio-baud 57600` in User-Startup, then run:

```sh
NIO:fujinet-nio-exchange
```

Expected: EXCHANGE succeeds (`PASS isolated-exchange`). Then run back-to-back:

```sh
fls
fls
```

Both should succeed. Report the EXCHANGE diagnostic line regardless of outcome.
If EXCHANGE passes, report whether both FLS invocations also pass.

## Verification completed

After each diagnostic change:

```sh
source scripts/env.sh && make -C repos/fujinet-nio-driver/amiga tests
source scripts/env.sh && make -C repos/fujinet-nio-driver/amiga native
```

Both pass. Earlier, after the public library diagnostic accessor was added:

```sh
cd repos/fujinet-nio-lib && source ../../scripts/env.sh && make check
```

also passed.
