# Brownfield: draft to rewrite, not to extend

This companion is evidence. The next implementation session starts from SPEC.md and `lifecycle.md`, not from “make the current ISR slightly safer.”

## Why a FujiNet device exists

Stock `serial.device` at 19200/38400 misses Paula RBF. Research: `_bmad-output/planning-artifacts/research/technical-amiga-rs-232-disk-operation-failures-abo-2026-09-03/research.md`. Network soaks can pass while FLS/FHOST/FIN fail because reply burst shape differs, not because there is a second UART.

Runtime driver selection was added so the broker can `OpenDevice("fujinet-serial.device")` without a rebuild. That ABI is in use and tested. Keep it.

Third-party serial replacements were considered and dropped. They are out of scope and must not appear in docs or code comments.

## Draft files (present in tree)

| Path | Role |
| --- | --- |
| `amiga/include/fujinet_paula_uart.h` + `serial.device/fujinet_paula_uart.c` | SERPER, SERDAT 8N1 (`0x0100 \| byte`), ring |
| `amiga/include/fujinet_serial_device.h` | `"fujinet-serial.device"`, unit 0 |
| `amiga/serial.device/fujinet_serial_device.c` | Exec device |
| `amiga/serial.device/fujinet_serial_rbf.S` | Exclusive RBF handler (sample, retain, ack once, `Cause` via A0) |
| `amiga/serial.device/fujinet_serial_lifecycle.c` | Host-testable ownership/READ/RBF model |
| `amiga/tools/fujinet-nio-serial.c` | GET/SET_SERIAL CLI |
| `integration-tests/amiberry/startup/nio-paula-serial.sequence` | Load serial device, load nio, clock, file-list marker |
| `integration-tests/amiberry/test_nio_paula_serial.py` | Asserts load RC=0 and `result=0` |

Host SERPER/ring tests passed and are worth keeping if the math still matches AHRM. The draft did not claim Paula through `misc.resource`; the rewrite must.

## What the draft tried

1. **C RBF server + `AddIntServer(INTB_RBF)`.** Kickstart stayed on the chain. Amiberry log: our `period=183` (19200 PAL) then ROM `period=372` (9600) at Kickstart PC. Guru `8000 000B` (Line F) while ISR used globals / C helpers without saving D2–D7/A2–A6.
2. **`SetIntVector(INTB_RBF)`**, TBE polled not interrupted, ISR inlined C with `movem` around a body that still had a gcc A2/D2 prologue. Amiberry clock then worked.
3. **Assembler ISR**, always ack `INTF_RBF`, only scratch D0/D1/A0/A1. Still PiStorm reboot after print.
4. **Double `INTREQ` write + `NOP` before `RTS`, plus `CMD_FLUSH` to mask RBF and restore Kickstart’s vector before the CLI prints.** Operator: still crashed. Treat as rejected, not as a missing NOP.

The draft also treated the RBF path as an interrupt-server boundary. The rewrite treats `INTB_RBF` as an exclusive Exec interrupt handler (`SetIntVector`). Exec supplies `D1`/`A0`/`A1`/`A6`; the handler keeps `A0` as the custom-chip base and uses `A5` as the RX/TX pointer.

## Evidence split

**Amiberry `nio-paula-serial` (wb32 / a1200-030):** clock `dev=0x45 cmd=0x01` status 0; file-list of `host:/amiga-e2e-complete/nio-paula-serial` status 0 when `--size 256`; SERPER held at 19200 after Kickstart’s initial 9600. Guest round-trip through the draft driver works here. Amiberry does not prove PiStorm stability.

**PiStorm hardware:** FujiNet traffic seen; one printed trial line with `status=0`; then power LED flashes and the PiStorm cold-reboot screen. The exchange completed; teardown or a still-live RBF path killed the emulator. Amiberry does not reproduce this. PiStorm is the sole hardware-stability gate.

**Do not run** `C:fujinet-nio-exchange` with no arguments on PiStorm. That isolation program has completed PASS and then rebooted the same way.

## Broker lifetime

Stage 4: success does not idle-close the serial backend. After a one-shot clock the backend (and therefore Paula ownership) can remain until the next SET_SERIAL/SET_BAUD, error close, or expunge. SET_SERIAL already closes the backend so the next EXCHANGE opens the newly named device.

Chosen receive policy: `CMD_FLUSH` keeps RBF armed and clears the software queue. WRITE drains leftover `SERDATR` and discards the queue before TX. FLUSH-quiesce was the first PiStorm cut; first 38400 request after idle timed out with no RX (`cause=4`) with and without 16/2000 pacing. Always-armed did not fix a clean-reboot first open at 38400: the device programmed 19200 on claim then `SETPARAMS` 38400. Open now takes `io_Baud` from `OpenDevice`; the broker fills it before `OpenDevice`. See `lifecycle.md`.
