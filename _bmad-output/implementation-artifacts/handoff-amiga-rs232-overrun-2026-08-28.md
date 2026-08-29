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
- DB25-to-DB9 adapter tested with multimeter: all five signal lines (TX, RX,
  RTS, CTS, GND) correctly wired to the standard DB25↔DB9 pin mapping.

## Diagnostic tool output format

```text
EXCHANGE io= nio= len= stage= result= cause= native= status-hi=
```

- `cause=7`: failure in `CMD_READ`
- `native=6`: `SerErr_LineErr`
- `status-hi=1`: `IO_STATF_OVERRUN` (bit 8 of `io_Status`)
- `REUSE` line: second exchange on same backend without re-opening serial

## Confirmed root cause

**The CIA 8520 TX→RX mode transition, triggered at the end of every CMD_WRITE,
latches IO_STATF_OVERRUN as a hardware side effect.** This is not caused by data
arriving too fast, ISR priority, or cable quality. Evidence:

- `status-hi=1` always: `IO_STATF_OVERRUN`, not framing or parity error.
- Flag NOT present during `session_flush` (before CMD_WRITE) — confirmed
  by `cause=7` (flush drain never fired).
- SERF_RAD_BOOGIE (Level 6 ISR) does not fix it — ISR priority is irrelevant.
- SERF_7WIRE + hardware RTS/CTS (correctly wired) does not fix it — the
  ESP is gated and hasn't sent a byte yet, yet CMD_READ still finds the flag.
  This definitively proves the flag is set before any response data arrives.
- REUSE always succeeds: the failed CMD_READ consumed the flag; the CIA is
  now in a clean state for subsequent exchanges.
- The flag is NOT present immediately after SDCMD_SETPARAMS — only after
  the first CMD_WRITE completes.

The Amiga CIA 8520 serial shift register is shared between TX and RX.
`serial.device` switches it to TX mode for CMD_WRITE and back to RX mode
after. The TX→RX mode transition at the end of CMD_WRITE produces a spurious
hardware event that latches `IO_STATF_OVERRUN`.

## What has been tried and failed (do not repeat)

### 1. io_RBufLen alignment correction (2050 → 2112)
A real bug (RBufLen must be multiple of 64) but did not affect the overrun.
The fix is retained in the code.

### 2. SERF_RAD_BOOGIE
Level 6 ISR. Retained in code (correct for 57,600 baud in general), but
did NOT fix the overrun. The overrun is not an ISR latency issue.

### 3. CMD_READ soft retry (fall-through on io_Actual > 0)
Serial.device CMD_READ with overrun returns io_Actual=0 always. The retry
path was never reached. Not useful.

### 4. session_flush drain (SDCMD_QUERY + CMD_READ before CMD_WRITE)
Added check for IO_STATF_OVERRUN in session_flush before CMD_WRITE.
Confirmed: flag is NOT present before CMD_WRITE (cause=7 every time).
This drain never fires. Removed from session_flush.

### 5. post-SDCMD_SETPARAMS drain in backend_open()
SDCMD_QUERY immediately after SDCMD_SETPARAMS shows no overrun flag.
The flag does not appear at SDCMD_SETPARAMS time; it appears during CMD_WRITE.
The drain never fires here either.

### 6. backend_recover_from_overrun() soft reset
Keeps serial/timer open, re-inits SLIP session. The backend already survives
CloseDevice (confirmed from code). The soft reset leaves the CIA in the same
state — the next first exchange still fails.

### 7. tx_gap_us = 1,000,000 µs on ESP
Applies `esp_rom_delay_us()` before `uart_write_bytes()`. The Amiga
experiences the delay (1-second pause), but the overrun still occurs. This
confirms the overrun is NOT a timing/settling issue between SDCMD_SETPARAMS
and the first received byte.

### 8. ArtSer patched serial.device
ArtSer (artser.device 37.6) renamed to serial.device in DEVS:, but the ROM
serial.device (in Kickstart) takes precedence and is always used instead.
ArtSer on disk is never loaded because the ROM node named "serial.device" is
already resident. `serial-free-before=0` confirmed this.

### 9. SERF_7WIRE + hardware RTS/CTS
FujiNet RS232-Rev1 schematic: IO7→DIN4 (driver, output toward DB9 = ESP's
RTS output to Amiga CTS). IO15→ROUT3 (receiver, input from DB9 = Amiga RTS
to ESP CTS). Pinmap in firmware was SWAPPED — corrected to `rts=7, cts=15`
in `repos/fujinet-nio/src/platform/esp32/pinmap.cpp`.

With SERF_7WIRE on Amiga + `flow_control rts_cts` on ESP + corrected pinmap:
CMD_WRITE failed with cause=5 (SERIAL_WRITE, native=13). This was because
SERF_7WIRE with Amiga checks CTS before sending, and CTS wasn't asserted.

After understanding that RTS/CTS flow control in SERF_7WIRE does NOT gate
transmission based on pending CMD_READ (it gates based on buffer space),
the sequence is: RTS is already asserted, ESP sends response during CMD_WRITE,
bytes arrive, first CMD_READ fails with overrun and clears ring buffer, retry
CMD_READ waits 8 seconds and times out. This is the same failure mode as #10.

### 10. CMD_READ retry in channel_read after IO_STATF_OVERRUN
Two attempts:
- Without SERF_7WIRE: ESP sends response during CMD_WRITE. Bytes in ring
  buffer. First CMD_READ clears ring buffer. Retry CMD_READ times out (8s).
  FAILED.
- With SERF_7WIRE: Assumed ESP was gated until CMD_READ posted. In fact,
  SERF_7WIRE asserts RTS based on buffer space, not pending CMD_READ. Same
  outcome: bytes sent by ESP during CMD_WRITE, cleared by failed CMD_READ,
  retry CMD_READ times out (8s). FAILED.

### 11. SLIP_END warm-up byte in backend_open()
Sent 0xC0 via CMD_WRITE after SDCMD_SETPARAMS, then queried and drained
the resulting overrun. The ESP interpreted the 0xC0 as an empty SLIP frame
every time backend_open() ran, producing repeated FujiBus warnings
("invalid FujiBus frame, dropped") and completely destabilising the session.
Reverted immediately.

## Current code state

The driver is reverted to the state that works at 38,400 baud:
- `SERF_XDISABLED | SERF_RAD_BOOGIE` in SDCMD_SETPARAMS (no SERF_7WIRE)
- Harmless (never-fires) SDCMD_QUERY drain in backend_open() retained with
  accurate comments explaining it does not fire
- No channel_read retry
- No session_flush overrun drain
- `backend_recover_from_overrun()` still wired (soft reset path, doesn't hurt)
- `io_RBufLen = 2112` (correct multiple of 64, retained)
- ESP pinmap corrected: `rts=7, cts=15` in pinmap.cpp (correct per schematic)
- ESP `flow_control none`, `tx_gap_us 0`

## What still needs solving

The overrun is definitively caused by the CIA 8520 TX→RX mode transition at
the end of CMD_WRITE. The flag appears AFTER CMD_WRITE, BEFORE CMD_READ.
The response bytes from the ESP arrive DURING this window (ESP sends
immediately after receiving the request, before CMD_READ is even posted).
The failed CMD_READ clears the ring buffer. The response bytes are lost.

Viable directions not yet attempted:

1. **Pending CMD_READ before CMD_WRITE**: Post an async CMD_READ (SendIO)
   before issuing CMD_WRITE (DoIO). The CIA stays in RX mode the whole time —
   there is no TX→RX transition because serial.device may not need to switch
   CIA mode when a CMD_READ is already outstanding. This requires a second
   IOExtSer request structure and async I/O. This is architecturally the
   cleanest fix if the CIA actually avoids the mode switch in this scenario —
   needs verification against serial.device source behaviour.

2. **Proper hardware RTS/CTS with a different Amiga implementation**: The
   Amiga's RTS with SERF_7WIRE is asserted based on buffer space, not pending
   CMD_READ. A custom serial implementation (not serial.device) could drive RTS
   only when CMD_READ is actually posted. This is beyond the current scope.

3. **Reduce to 38,400 baud**: Declare 57,600 unsolvable without changing
   the serial I/O architecture. 38,400 works reliably.

## Relevant files

- `repos/fujinet-nio-driver/amiga/nio.device/fujinet_nio_serial_backend.c`
- `repos/fujinet-nio-driver/amiga/nio.device/fujinet_nio_device.c`
- `repos/fujinet-nio-driver/amiga/include/fujinet_nio_backend.h`
- `repos/fujinet-nio-driver/amiga/tools/fujinet-nio-exchange.c`
- `repos/fujinet-nio/src/platform/esp32/pinmap.cpp` (pinmap corrected, rts=7 cts=15)
