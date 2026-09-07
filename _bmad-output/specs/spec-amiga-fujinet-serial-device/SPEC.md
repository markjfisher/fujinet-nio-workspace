---
id: SPEC-amiga-fujinet-serial-device
companions:
  - conventions.md
  - brownfield.md
  - failure-modes.md
  - ../../../repos/fujinet-nio-driver/docs/amiga/Serial-IO-Interface.md
  - ../../../repos/fujinet-nio-driver/docs/amiga/serial-interface-connector.md
  - ../../../repos/fujinet-nio-driver/docs/amiga/cia-port-signal-assigments.md
  - ../../../repos/fujinet-nio-driver/docs/amiga/cia-chip-register-map.md
  - ../../../repos/fujinet-nio-driver/docs/amiga/rs232-cold-warm-hardware-test.md
  - ../../planning-artifacts/research/technical-amiga-rs-232-disk-operation-failures-abo-2026-09-03/research.md
  - ../../../docs/agent-test-policy.md
sources: []
---

> **Canonical contract.** This SPEC and the files in `companions:` are the complete, preservation-validated contract for what to build, test, and validate. Source documents listed in frontmatter are for traceability — consult them only if you need narrative rationale or prose color this contract intentionally omits.

# Amiga FujiNet Paula serial device

## Why

**Pain.** FujiNet NIO on Amiga still talks to the ESP over RS-232. Above 9600 baud, stock `serial.device` misses Paula receive-buffer-full deadlines: disk and file replies overrun even with ESP 16-byte / 2000 µs chunk pacing. TCP and Amiberry’s stock serial path are not Paula, so they do not prove the hardware. Third-party serial replacements are out. FujiNet needs its own Exec serial device that owns Paula, selectable at runtime through the existing SET_SERIAL path, so 19200/38400 request/response can work on real machines (including PiStorm) without renaming Kickstart `serial.device`.

The in-tree draft proved a clock round-trip on Amiberry and printed `status=0` on PiStorm, then the machine rebooted. This spec is the contract for a **clean rewrite** of that device. Do not cargo-cult the draft ISR.

## Capabilities

- **CAP-1**
  - **intent:** An operator can choose which Exec serial device the resident broker next opens, by name and unit, without rebuilding the broker.
  - **success:** `C:fujinet-nio-serial` with no args prints the current name and unit; with a name (optional unit) SET_SERIAL persists until unload or reboot; `fujinet-nio-exchange --serial-device NAME` selects for that run only; omitting it uses the last SET_SERIAL value; default remains `serial.device` unit 0. Host tests in `test_fujinet_nio_device.c` and `test_fujinet_nio_exchange_opts.c` pass.
- **CAP-2**
  - **intent:** An operator can load a FujiNet-owned Exec device named `fujinet-serial.device` that presents an `IOExtSer` subset sufficient for the broker serial backend.
  - **success:** `make native` in `repos/fujinet-nio-driver/amiga` produces `build/amiga/fujinet-serial.device`; `fujinet-load-resident DEVS:fujinet-serial.device fujinet-serial.device` returns 0; exclusive open of unit 0; 8N1 only; baud 300–230400 accepted by SETPARAMS; unsupported parity/word/stop rejected. Stock `serial.device` is not renamed or replaced on disk.
- **CAP-3**
  - **intent:** The broker can complete FujiBus request/response through that device at 9600, 19200, and 38400.
  - **success:** Cold clock via `fujinet-nio-exchange --type clock --backend cold --baud <rate> --serial-device fujinet-serial.device --trials 1` returns `result=0` at each of 9600, 19200, and 38400 on Amiberry; the same command is the hardware matrix entry in `rs232-cold-warm-hardware-test.md`. 57600 is not in this spec.
- **CAP-4**
  - **intent:** The workspace Amiberry harness can prove load, select, one clock, and a successful FileDevice list marker through `fujinet-serial.device`.
  - **success:** `uv run pytest --run-amiga --amiga-env wb32 --amiga-machine a1200-030 integration-tests/amiberry/test_nio_paula_serial.py::test_paula_serial_clock` passes. File-list `maxPayloadBytes` is large enough for FileDevice (not 8; 256 is the known-good size). Default suite cases remain on `serial.device`.
- **CAP-5**
  - **intent:** On the operator’s PiStorm Amiga, a successful cold clock through `fujinet-serial.device` leaves the machine usable.
  - **success:** The one-shot in CAP-3 at 19200 prints one trial line containing `status=0` (or `result=0`) **and** returns to the Shell prompt with no power-LED flash and no PiStorm cold-reboot screen. Printing the line then dying is failure.
- **CAP-6**
  - **intent:** Host-side tests can fail SERPER math, ring/overrun ingest, and SET_SERIAL name rules without booting AmigaOS.
  - **success:** `source "$NIO_WORKSPACE/scripts/env.sh" && make -C repos/fujinet-nio-driver/amiga tests` includes `test_fujinet_paula_uart` and the SET_SERIAL/opts cases and passes. These tests do not claim interrupt or PiStorm coverage.

## Constraints

- Hardware truth is the print-validated AHRM extracts listed in `companions:`. Do not fetch the AHRM PDF. Do not diagnose from CIA 8520 serial-shift folklore or the archived 2026-08-28 overrun handoff.
- Paula receive and transmit are independent full-duplex paths. `IO_STATF_OVERRUN` / `SerErr_LineErr` means the prior received character was not picked up before the next completed.
- Applications that use `serial.device` request baud in `io_Baud` and SETPARAMS. A FujiNet Paula device may program `SERPER` itself; Kickstart must not rewrite `SERPER` while that device owns Paula.
- Exec interrupt servers scratch `D0–D1/A0–A1` only and return with `RTS`. `SetIntVector` still uses that convention, not a raw 68k `RTE` handler.
- Do not rename, patch, or ship a replacement for Kickstart `serial.device`. Do not integrate or document third-party serial drivers.
- Default broker backend stays `serial.device` unit 0. `fujinet-serial.device` is opt-in via SET_SERIAL or `--serial-device`.
- SET_SERIAL / GET_SERIAL ABI stays: `FUJINET_NIO_CMD_SET_SERIAL` = `CMD_NONSTD+3`, GET = `+4`; payload little-endian unit then a NUL-terminated Exec name; names 1..30 printable, no `:/\` or space. Header: `fujinet_nio_serial_config.h`. CLI: `fujinet-nio-serial`.
- Device name is `fujinet-serial.device` (not `fujinet-nio-serial.device`). Unit 0 only, exclusive open.
- Compile Amiga code `-mcpu=68000 -msoft-float`. PiStorm/Emu68 is still a 68040-class **runtime**; CAP-5 is that runtime, not Amiberry.
- Do not treat double `INTREQ` writes or a `NOP` before `RTS` as the accepted interrupt design. That change was tried on the draft ISR and did not stop the PiStorm reboot.
- The in-tree Paula device, RBF assembler, and post-exchange `CMD_FLUSH` mask are a **failed hardware draft**. Keep SET_SERIAL, install lists, and Amiberry case wiring unless this spec changes; replace interrupt ownership and receive servicing from this contract, not by patching that ISR in place.
- Verification follows `docs/agent-test-policy.md`: driver native tests plus the one Amiberry node in CAP-4. Do not default to the full Amiberry suite. CAP-5 is operator hardware.

## Non-goals

- Third-party or shareware serial.device replacements, by any name.
- 57600 baud until 38400 is stable on hardware.
- Switching the default Amiberry suite off `serial.device`.
- RTS/CTS (`SERF_7WIRE`) as the 38400 fix in this cut.
- Redesigning the broker public EXCHANGE ABI or Stage 3/4 idle-close policy except as needed to open/close `fujinet-serial.device` correctly.
- Packet-native (Zorro/floppy) backends.
- Making Amiberry Paula emulation a substitute for CAP-5.

## Success signal

An operator loads `fujinet-serial.device`, selects it with `fujinet-nio-serial`, runs a cold clock at 19200, sees `result=0`, and still has a Shell. Amiberry `nio-paula-serial` stays green. Stock `serial.device` remains the default for everyone else.

## Assumptions

- SET_SERIAL, `fujinet-nio-serial`, release/FTP/share install of `fujinet-serial.device`, and the Amiberry `fujinet_serial` flag are keepers from the draft.
- A rewrite may throw away the current RBF server and interrupt install path.
- ESP pacing 16/2000 remains the product default; this spec does not require turning pacing off to pass CAP-5.

## Open Questions

- Is PiStorm the only hardware gate, or must a real 68000 also return to Shell before 38400 is called done?
- Must `CMD_READ` wait for bytes like stock `serial.device`, or is QUERY-then-immediate-READ the broker contract?
- After a completed exchange, should Paula RBF stay armed for warm reuse or be released until the next open/write?
