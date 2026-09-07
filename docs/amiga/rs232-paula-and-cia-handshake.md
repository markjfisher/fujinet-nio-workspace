# Amiga RS-232: Paula UART and CIA-B handshake

Hardware register truth remains the print-validated extracts under
`repos/fujinet-nio-driver/docs/amiga/` (`Serial-IO-Interface.md`,
`serial-interface-connector.md`, `cia-port-signal-assigments.md`,
`cia-chip-register-map.md`). This file is the process map: which chip does
data, which chip does RTS/CTS, and what that means for `fujinet-serial.device`.

Do not diagnose from CIA 8520 serial-shift folklore. CIA-B does **not** shift
FujiNet payload bits. Paula does.

## Two chips, one connector

The 25-pin RS-232 connector carries both the UART data pair and the modem
control lines. They are not the same hardware.

| Function | Chip / resource | What it is |
| --- | --- | --- |
| Baud, TX byte, RX byte, RBF, TBE, overrun | Paula (`SERPER`, `SERDAT`, `SERDATR`, `INTF_RBF` / `INTF_TBE`) | The UART. Claimed as `misc.resource` **`MR_SERIALPORT`**. |
| DTR, RTS, CD, CTS, DSR | CIA-B port A (`ciab` PRA/DDRA) | Handshake and modem status only. Claimed as `misc.resource` **`MR_SERIALBITS`**. |

CIA-B port A (active-low names in the extract):

| Bit | Line |
| --- | --- |
| PA7 | `DTR*` |
| PA6 | `RTS*` |
| PA5 | carrier detect |
| PA4 | `CTS*` |
| PA3 | `DSR*` |

Connector pins 2/3 are TXD/RXD (Paula). Pins 4/5 are RTS/CTS (CIA-B). The
FujiNet RS-232 path has those control pins wired; wiring is not the same as
software seven-wire mode being on.

## What `SERF_7WIRE` actually does

`SERF_7WIRE` is the Exec serial-device request for CTS/RTS hardware
handshake. Commodore requires it in `io_SerFlags` **before** `OpenDevice()`.
Setting it only in a later `SDCMD_SETPARAMS` does not enable Amiga seven-wire
mode.

When seven-wire is really on:

- **Amiga RTS** (CIA-B PA6) is an output driven from **receive-buffer space**,
  not from “a `CMD_READ` is posted”.
- **Amiga CTS** (CIA-B PA4) is an input that may **gate Amiga transmit**
  (do not write `SERDAT` while the peer is not ready).
- On the ESP32-S3, **TX is gated by ESP CTS**, not by ESP RTS. ESP RTS
  reports ESP RX FIFO capacity. FujiNet’s reply is held only if Amiga RTS
  actually reaches ESP CTS and ESP `flow_control` includes CTS.

Correct seven-wire can protect software FIFOs and the ESP TX queue. It does
**not** extend Paula’s one-character RBF service window (about 262 µs per
8N1 character at 38400 PAL). A late RTS still loses the byte already in
`SERDATR` if RBF was not acked in time.

## This cut of `fujinet-serial.device`

Claim `MR_SERIALPORT` then `MR_SERIALBITS` so another driver cannot own the
control lines while FujiNet owns the UART. **Do not program CIA-B handshake
bits in this cut.** Leave RTS/CTS/DTR as found aside from the resource claim.
Do not treat `SERF_7WIRE` as the 38400 reliability fix. The broker still opens
with `SERF_XDISABLED | SERF_RAD_BOOGIE` only.

That keeps a later seven-wire add additive: CIA-B DDRA/PRA save/program/restore,
ring-threshold RTS, CTS gate before `SERDAT`, honour `SERF_7WIRE` at open and
in `SETPARAMS`, matching ESP `flow_control rts_cts`, analyzer capture of
TXD/RXD/RTS/CTS. It must not change the Paula RBF order (read `SERDATR`,
retain, ack once, drain while asserted, no `ReplyMsg` in the handler).

## Prior RTS/CTS attempt

The 2026-08-28 archived overrun handoff tried `SERF_7WIRE` **after**
`OpenDevice()`. That test is **inconclusive**. It does not prove seven-wire
works, and it does not prove it fails. Do not treat that archive as current
procedure.

A valid later test:

1. Put `SERF_7WIRE` in `io_SerFlags` before `OpenDevice()`.
2. Keep it in `SDCMD_SETPARAMS` with `SERF_XDISABLED`.
3. Enable matching ESP CTS/RTS flow control.
4. Capture TXD/RXD/RTS/CTS with a logic analyzer (transceiver inversion
   included).

Tracked as research rank 3, optional, in
`backlog/amiga-rs232-38400-reliability.md`. Procedure detail:
`_bmad-output/planning-artifacts/research/technical-amiga-rs-232-disk-operation-failures-abo-2026-09-03/research.md`.
