# Failure modes the rewrite must not repeat

## Missed RBF (product failure)

At 38400 PAL the service window is about 262 µs per 8N1 character; at 19200 about 521 µs. If software does not read `SERDATR` and clear `INTF_RBF` in `INTREQ` before the next character completes, `OVRUN` is set and the byte is gone. Framing checksums can retry; lossless recovery after overrun is not a serial-device job.

AHRM Table 8-9: after reading `SERDATR`, reset `INTF_RBF` in `INTREQ` once. Returning from an RBF handler while `INTREQ` is still asserted livelocks interrupt level 5. Never acknowledge before sampling `SERDATR`. Never use the rejected duplicate-`INTREQ`/NOP sequence.

Private diagnostics must keep `hardware_overrun_latched` (Paula was not serviced in time) distinct from `software_ring_overflow_latched` (the software queue was not drained in time). Public status may collapse both.

## Kickstart still owns SERPER / Paula

Sharing the RBF interrupt chain with Kickstart let ROM reprogram `SERPER` to 9600 after FujiNet set 19200. Exclusive Paula ownership via `SetIntVector(INTB_RBF)` plus `misc.resource` is required while the device is open. Exclusive does not mean a raw exception `RTE` handler.

Exclusive `OpenDevice` of `fujinet-serial.device` is not enough: another task can still open Kickstart `serial.device` and touch the same UART. Claim `misc.resource` first. If stock `serial.device` already owns the hardware, FujiNet open must fail with no Paula/RBF/`SERPER`/INTENA change.

Do not restore a previous `SERPER` divisor on close: it is write-only.

## Immediate 0-byte READ vs stock serial.device

Stock `CMD_READ` waits for data. A driver that completes READ immediately with `io_Actual=0` will strand the broker’s `SendIO`+timer path if QUERY ever over-reports, and will not match AutoDocs. The rewrite uses pending stock-like `CMD_READ`. Immediate 0-byte completion is rejected.

A pending READ, `AbortIO`, `CMD_FLUSH`, and final close must not both complete the same request. Dual `ReplyMsg` or a stale retained pointer after FLUSH/close is a crash class.

## FileDevice list as harness marker

`maxPayloadBytes == 0` or below 18 (non-formatted) is `InvalidRequest` (wire status 2). The Amiberry scanner only accepts a later send with `status=0` containing the marker URI. A too-small list looks like a hung guest.

## PiStorm death after success

Observed: trial line with `status=0`, then power-LED flash and PiStorm screen. That is a hard emulator reset, not a waiting Guru. Causes to investigate in the rewrite (not prescriptions): interrupt still pending after the CLI runs; supervisor-stack blow-up from re-entered level 5; `SetIntVector` fighting Emu68; CloseDevice/timer/clib2 after print; tearing down Paula while a READ is still retained. Printing then dying is CAP-5 fail even when FujiBus succeeded.

Final close must resolve retained requests before vector removal. No ISR-visible pointer may remain after teardown.

## Isolation

A second NIO client (`FLS`, DiskDevice, another Shell) opening the broker changes cold/warm and can steal or share the serial backend. Hardware matrix requires isolation as in `rs232-cold-warm-hardware-test.md`.
