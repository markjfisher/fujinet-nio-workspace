---
status: archived
archived: '2026-09-04'
original_date: '2026-08-28'
original_path: '_bmad-output/implementation-artifacts/handoff-amiga-rs232-overrun-2026-08-28.md'
superseded_by: '_bmad-output/planning-artifacts/research/technical-amiga-rs-232-disk-operation-failures-abo-2026-09-03/research.md'
do_not_use_as: guidance
---

# ARCHIVED — historical snapshot only

**Do not use this document for future work.** It is not a live handoff,
not a current root-cause statement, and not an experiment plan.

This file is the 2026-08-28 understanding of Amiga RS-232 receive overruns,
kept so the **flaws in that understanding remain visible**. Research dated
2026-09-03/04 superseded it:

- [`research.md`](../planning-artifacts/research/technical-amiga-rs-232-disk-operation-failures-abo-2026-09-03/research.md)

The body below is the original text, annotated. Status labels:

| Label | Meaning |
| --- | --- |
| **DISPROVEN** | Central mechanism is false; do not reuse. |
| **SUPERSEDED** | Later research replaced the recommendation. |
| **INCONCLUSIVE** | Experiment did not test what it claimed. |
| **MISINTERPRETED** | Observation can stand; the inference does not. |
| **STALE** | Snapshot of code or scope at the time, not current. |
| **OBSERVATIONAL** | Recorded symptoms; not a causal claim. |
| **SEPARATE** | Side issue; not the UART mechanism. |

## Verdict map (read this, not the original conclusions)

| Original section | Status | Why |
| --- | --- | --- |
| Scope | **STALE** / **SUPERSEDED** | Narrowing away from FHOST/FLS/DiskDevice hid that those calls share one serial backend; response profile is the remaining differentiator. |
| Hardware and observed behaviour | **OBSERVATIONAL** | Symptom log from 2026-08-28. Later work still treats 57,600 as hostile and 38,400 as intermittent for some request/response shapes. |
| Diagnostic tool output format | **OBSERVATIONAL** | Decoder for the diagnostic bytes remains historically useful. |
| Confirmed root cause | **DISPROVEN** | Built-in RS-232 data path is Paula, not CIA 8520. Paula TX and RX are independent; there is no TX→RX mode switch. `IO_STATF_OVERRUN` / `SerErr_LineErr` means the prior received character was not serviced before the next one completed. `CMD_READ` reports a latched fault; it did not necessarily cause it. `serial.device` buffers after `OpenDevice()` whether or not a read is pending. |
| Tried #1 `io_RBufLen` 2050→2112 | Still a real API fix; **not the overrun cause**. Further enlarging the software buffer will not fix `SerErr_LineErr`. |
| Tried #2 `SERF_RAD_BOOGIE` | Did not create a FIFO or change direction. High-speed overruns remain possible under load. |
| Tried #3–6, #8, #10, #11 | Historical experiments. Do not repeat as CIA-transition countermeasures. |
| Tried #7 `tx_gap_us` | **MISINTERPRETED** | A one-second start delay does not pace the response burst, so failure does not disprove receive-burst / RBF-service starvation. |
| Tried #9 SERF_7WIRE + RTS/CTS | **INCONCLUSIVE** | `SERF_7WIRE` was set after `OpenDevice()`. Commodore requires it at open time. The test did not validate Amiga seven-wire mode. |
| Current code state | **STALE** | 2026-08-28 driver/ESP snapshot. Not a living contract. Source comments that still mention a CIA UART or TX→RX switch are themselves incorrect. |
| What still needs solving | **DISPROVEN** mechanism, **SUPERSEDED** plan | Do not post a pending `CMD_READ` to “keep Paula in RX mode”. A pre-posted one-byte read remains a ranked *scheduling* experiment only. Current ranked work is the research hardware matrix (cold/warm + response size, then pacing, then correctly configured seven-wire). |
| C0 C0 empty-frame | **SEPARATE** | ESP `_rxBuffer` leftover from the SLIP_END warm-up experiment; not evidence for CIA TX→RX. |
| Relevant files | Pointers only | Inspect current trees; do not trust CIA comments in those files. |

**Current investigation contract:** the research executive summary and ranked
options in `research.md`. Not this file.

---

# Original handoff (2026-08-28) — annotated

The following is the original text. Annotations in blockquotes are from
2026-09-04 research. Treat original unquoted claims as **then-current
beliefs**, including the ones later shown to be wrong.

## Scope

> **STALE / SUPERSEDED.** The diagnostic spec
> `_bmad-output/implementation-artifacts/spec-amiga-rs232-response-diagnostics.md`
> recorded a real instrumentation task. The instruction “do not broaden into
> FHOST/FLS/DiskDevice” is obsolete as a causal boundary: those applications
> use the same resident serial backend. Differences that remain are response
> length, burst shape, service timing, system load, and cold/warm state.

This is a live real-hardware investigation. Do not broaden it into FujiBus,
FHOST/FLS, DiskDevice, ESP application, or Workbench work. The active BMad
spec is `spec-amiga-rs232-response-diagnostics.md` in this directory.

## Hardware and observed behaviour

> **OBSERVATIONAL.** Keep as a 2026-08-28 symptom log. Do not infer a
> CIA-shared shift register from it.

- Real Amiga connected to an ESP32-S3 FujiBus RS-232 endpoint.
- The user sets `fujinet-nio-baud 57600` in User-Startup, so the driver is
  configured after every reboot; the ESP endpoint is also set to 57,600.
- Normal `fhost tnfs://192.168.1.101/amiga` and `fls` fail at 57,600 with raw
  transport error 16, although ESP logs show the requests and valid replies.
- At 19,200 and 38,400, `fujinet-nio-exchange` ends with
  `PASS isolated-exchange` and FHOST/FLS work normally.
- DB25-to-DB9 adapter tested with multimeter: all five signal lines (TX, RX,
  RTS, CTS, GND) correctly wired to the standard DB25↔DB9 pin mapping.

> Later research: `fujinet-nio-exchange` is not a faithful cold FHOST/FLS
> stand-in (pre-open of `serial.device`, small clock request first). A later
> network soak can pass at 38,400 while FLS/FHOST/FIN still fail; that does
> not prove all response profiles are safe.

## Diagnostic tool output format

> **OBSERVATIONAL.** Encoding of the diagnostic fields, not a mechanism.

```text
EXCHANGE io= nio= len= stage= result= cause= native= status-hi=
```

- `cause=7`: failure in `CMD_READ`
- `native=6`: `SerErr_LineErr`
- `status-hi=1`: `IO_STATF_OVERRUN` (bit 8 of `io_Status`)
- `REUSE` line: second exchange on same backend without re-opening serial

> Research: `SerErr_LineErr` + overrun is Paula RBF service failure, distinct
> from `SerErr_BufOverflow`. Seeing the flag at `CMD_READ` after a completed
> write does not mean the write caused it.

## Confirmed root cause

> **DISPROVEN.** There is no documented CIA 8520 TX→RX transition on the
> built-in RS-232 data path. Paula has separate TX and RX shift/buffer paths
> for full duplex. CIA-B owns handshake GPIO; its serial shift register is
> unused for this UART. `serial.device` receives continuously after open.
> Do not design fixes around a mode switch that does not exist.

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

> The RTS/CTS bullet is also **INCONCLUSIVE** (seven-wire not enabled at
> `OpenDevice()`). “ESP hasn't sent a byte yet” was not established by a
> valid CTS-gating test. REUSE succeeding is compatible with a consumed
> latched overrun mark, not with a CIA mode reset.

## What has been tried and failed (do not repeat)

> **SUPERSEDED as a “do not repeat” list.** Several items remain useful
> history. Item 7’s inference and item 9’s “failed seven-wire” conclusion
> must not block the research matrix. Do not repeat CIA-transition hacks
> (bare SLIP_END warm-up, treating overrun as a mode-switch glitch).

### 1. io_RBufLen alignment correction (2050 → 2112)

> Real NDK constraint; retained. Not the cause of `SerErr_LineErr`.

A real bug (RBufLen must be multiple of 64) but did not affect the overrun.
The fix is retained in the code.

### 2. SERF_RAD_BOOGIE

> Fast path under 8N1 / no XON/XOFF. Does not change `SERPER`, add a FIFO,
> or switch direction. Overruns under load remain possible.

Level 6 ISR. Retained in code (correct for 57,600 baud in general), but
did NOT fix the overrun. The overrun is not an ISR latency issue.

### 3. CMD_READ soft retry (fall-through on io_Actual > 0)

Serial.device CMD_READ with overrun returns io_Actual=0 always. The retry
path was never reached. Not useful.

### 4. session_flush drain (SDCMD_QUERY + CMD_READ before CMD_WRITE)

Added check for IO_STATF_OVERRUN in session_flush before CMD_WRITE.
Confirmed: flag is NOT present before CMD_WRITE (cause=7 every time).
This drain never fires. Removed from session_flush.

> **STALE vs later trees:** a later source digest noted `session_flush()`
> still querying overrun in some revisions. Check current code; do not
> assume this paragraph is the live implementation.

### 5. post-SDCMD_SETPARAMS drain in backend_open()

SDCMD_QUERY immediately after SDCMD_SETPARAMS shows no overrun flag.
The flag does not appear at SDCMD_SETPARAMS time; it appears during CMD_WRITE.
The drain never fires here either.

### 6. backend_recover_from_overrun() soft reset

Keeps serial/timer open, re-inits SLIP session. The backend already survives
CloseDevice (confirmed from code). The soft reset leaves the CIA in the same
state — the next first exchange still fails.

> “Leaves the CIA in the same state” is **DISPROVEN** framing. Soft reset
> not fixing first-exchange failure remains a historical observation.

### 7. tx_gap_us = 1,000,000 µs on ESP

> **MISINTERPRETED.** `tx_gap_us` delays the start of the UART write, then
> the same unpaced burst follows. That contradicts a pure turnaround-settling
> problem. It does **not** test inter-byte or inter-chunk pacing.

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

> **INCONCLUSIVE as a seven-wire verdict.** Pinmap correction (`rts=7`,
> `cts=15`) can stand as wiring work. The Amiga flag was applied in
> post-open `SDCMD_SETPARAMS`, which does not enable seven-wire per the
> device contract. A valid retest must set `SERF_7WIRE` before
> `OpenDevice()`, keep it in later parameters, enable ESP CTS/RTS, and
> capture TXD/RXD/RTS/CTS. ESP TX is gated by **ESP CTS**, not ESP RTS.
> Even a correct test may deassert too late to prevent Paula’s
> one-character hardware overrun. Failure would not revive TX→RX.

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

> Buffer-threshold RTS (not pending-read RTS) matches later ESP and classic
> Amiga driver behaviour. The “bytes arrive during CMD_WRITE because of a
> mode switch” story does not.

### 11. SLIP_END warm-up byte in backend_open()

Sent 0xC0 via CMD_WRITE after SDCMD_SETPARAMS, then queried and drained
the resulting overrun. The ESP interpreted the 0xC0 as an empty SLIP frame
every time backend_open() ran, producing repeated FujiBus warnings
("invalid FujiBus frame, dropped") and completely destabilising the session.
Reverted immediately.

> Historical: do not send a bare `0xC0` as CIA warm-up. Empty-frame discard
> on the ESP is a separate framing hardening (see last original section).

## Current code state

> **STALE.** Do not treat this list as the 2026-09 driver/firmware contract.

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

> **SUPERSEDED.** Do not implement from this section.
>
> 1. Pending `CMD_READ` before `CMD_WRITE` is a valid *scheduling* experiment
>    with two `IOExtSer` requests (async one-byte read, then write). It will
>    not keep Paula “in receive mode”; Paula is already receiving.
> 2. Custom serial / RTS-on-pending-read is research rank 7 (last resort),
>    not a next step.
> 3. Declaring 57,600 unsolvable and 38,400 “reliable” is not the current
>    decision. Rank 1 is a cold/warm × response-size matrix; rank 2 is ESP
>    byte/chunk pacing at 38,400; rank 3 is correctly configured seven-wire.

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

## C0 C0 empty-frame issue — root cause and fix

> **SEPARATE.** Incident from experiment #11. Not evidence for CIA TX→RX.
> Whether the ESP discard-empty-frames change is still present is a current-
> tree question, not a reason to reopen this handoff.

After the SLIP_END warm-up experiment (attempt #11) was reverted, the user
continued seeing persistent `C0 C0` (empty SLIP frames) in ESP logs on every
FLS/exchange call. The Amiga driver source was clean. The cause was a stale
corrupted state in the ESP's `FujiBusTransport::_rxBuffer`.

**What happened:**

During the warm-up experiment, the Amiga sent a bare `0xC0` byte before the
full SLIP frame. The ESP received `[C0_warmup][C0_start][data][C0_end]`.
`extractSlipFrame` extracted `[C0_warmup, C0_start]` as a valid-but-empty
frame ("invalid FujiBus frame, dropped") and left `[data][C0_end]` in
`_rxBuffer`. Every subsequent Amiga request starts with a leading `0xC0`
(normal SLIP frame start), which combines with the stale trailing `C0` in
`_rxBuffer` to produce another empty frame. The buffer never self-heals.
`_rxBuffer` is never cleared between client connections (it is a persistent
`std::vector` in `FujiBusTransport`).

**Immediate fix for user:** power-cycle the ESP to clear `_rxBuffer`.

**Code fix:** `fujibus_transport.cpp` `receive()` and `receiveResponse()` now
loop and silently discard empty SLIP frames (`C0 C0`, frame.size() == 2)
instead of returning false after the first empty frame. Consecutive SLIP_END
bytes are valid inter-packet separators per RFC 1055 and must not corrupt
subsequent framing. Fix committed in `repos/fujinet-nio`.

## Relevant files

> Paths of interest at the time. Read current sources. Ignore CIA / TX→RX
> comments if they remain.

- `repos/fujinet-nio-driver/amiga/nio.device/fujinet_nio_serial_backend.c`
- `repos/fujinet-nio-driver/amiga/nio.device/fujinet_nio_device.c`
- `repos/fujinet-nio-driver/amiga/include/fujinet_nio_backend.h`
- `repos/fujinet-nio-driver/amiga/tools/fujinet-nio-exchange.c`
- `repos/fujinet-nio/src/platform/esp32/pinmap.cpp` (pinmap corrected, rts=7 cts=15)
