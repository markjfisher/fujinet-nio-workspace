# Amiga built-in serial hardware and `serial.device` digest — round 1

Decision served: determine whether the handoff hypothesis — “CIA 8520 TX→RX mode transition after `CMD_WRITE` latches `IO_STATF_OVERRUN`” — is technically valid, and establish what the built-in UART and classic `serial.device` do at 38,400 and 57,600 baud.

Scope: classic built-in Amiga serial port, Paula/CIA hardware, and Commodore `serial.device` documentation/source. Accessed 2026-09-03. The GitHub source tree is an archival mirror rather than an authenticated Commodore publication; conclusions that depend on it are marked accordingly.

**Working source of truth (print-validated in-tree extracts, not the AHRM PDF):**
- Paula UART: `repos/fujinet-nio-driver/docs/amiga/Serial-IO-Interface.md`
- CIA-B handshake pins: `repos/fujinet-nio-driver/docs/amiga/cia-port-signal-assigments.md`
- CIA address maps / unused CIAB `sdr`: `repos/fujinet-nio-driver/docs/amiga/cia-chip-register-map.md`
- Connector spec / software modem control: `repos/fujinet-nio-driver/docs/amiga/serial-interface-connector.md`

## Verdict

The proposed CIA TX→RX transition mechanism is contradicted by the retrieved evidence. The built-in serial data path is Paula's UART, with distinct receive and transmit shift/buffer paths designed for full-duplex operation. CIA-B provides software-controlled modem/handshake GPIO; its own serial-data register is documented as unused. Neither the Hardware Reference Manual nor the examined classic `serial.device` source contains a transmit/receive mode transition in `CMD_WRITE`.

`IO_STATF_OVERRUN` instead denotes a receive-side hardware overrun: a second complete character reached Paula before software cleared the prior receive-buffer-full condition. A completed write can correlate with the observation only indirectly — for example, the peer replies immediately while Amiga interrupt latency or other load delays receive service. That is a timing/service hypothesis, not a CIA mode-switch hypothesis.

At 38,400 and 57,600, the archived V42 driver accepts both rates, computes one shared Paula `SERPER` value for read and write, and programs no separate TX/RX baud generators. Replaying the source algorithm gives the following nominal wire rates:

| Requested | NTSC `SERPER` | NTSC actual | Error | PAL `SERPER` | PAL actual | Error |
|---:|---:|---:|---:|---:|---:|---:|
| 38,400 | 93 | 38,080.266 | -0.833% | 92 | 38,138.656 | -0.681% |
| 57,600 | 62 | 56,818.175 | -1.357% | 61 | 57,207.984 | -0.681% |

These figures are derived from the archived driver's integer algorithm and the official NTSC/PAL Paula clock formula; they are not a published Commodore baud table. The source performs truncating integer divisions with historical “magic” constants, not nearest-divider rounding, and even comments that the NTSC constant is wrong but retained for compatibility.

## Evidence claims

### Claim 1 — Paula, not a CIA, implements the built-in UART

- **claim:** The Paula custom chip contains the built-in UART and its `SERDAT`, `SERDATR`, and `SERPER` registers. The manual's decisive wording is: “The Paula custom chip contains a Universal Asynchronous Receiver/Transmitter, or UART.”
- **source:** `repos/fujinet-nio-driver/docs/amiga/Serial-IO-Interface.md`
- **publisher:** Commodore-Amiga / Addison-Wesley, *Amiga Hardware Reference Manual*, Third Edition (Ch. 8 Serial I/O extract)
- **pub_date:** 1991-08
- **accessed:** 2026-09-03
- **confidence:** high
- **class:** primary-hardware-manual

### Claim 2 — CIA-B handles modem-control GPIO, not TXD/RXD serialization

- **claim:** CIA-B port A maps DTR and RTS as outputs and CD, CTS, and DSR as inputs. The same CIA map calls CIA-B's serial data register “unused.” Separately, the serial connector section states that modem-control signals are software-controlled, asynchronous to TXD/RXD, and have no hardware effect on TXD/RXD. Thus CIA-B participates in handshake/status policy, not Paula's bit serialization.
- **source:** `repos/fujinet-nio-driver/docs/amiga/cia-port-signal-assigments.md`, `repos/fujinet-nio-driver/docs/amiga/cia-chip-register-map.md`, `repos/fujinet-nio-driver/docs/amiga/serial-interface-connector.md`
- **publisher:** Commodore-Amiga / Addison-Wesley, *Amiga Hardware Reference Manual*, Third Edition (App. E Parts 1–2 and 4; App. F maps)
- **pub_date:** 1991-08
- **accessed:** 2026-09-03
- **confidence:** high
- **class:** primary-hardware-manual

### Claim 3 — transmit does not disable receive; the hardware is intended for full duplex

- **claim:** Receive data moves through its own serial-to-parallel shift register into `SERDATR`, immediately freeing the receive shifter for the next character. Transmit data independently moves from `SERDAT` into an output shift register. The `TBE` status is explicitly described as normally used for full-duplex operation. `SERPER` supplies the interval both between receive samples and between transmitted bits. No receive-disable or TX/RX selector is documented.
- **source:** `repos/fujinet-nio-driver/docs/amiga/Serial-IO-Interface.md`
- **publisher:** Commodore-Amiga / Addison-Wesley, *Amiga Hardware Reference Manual*, Third Edition (Ch. 8 Serial I/O extract)
- **pub_date:** 1991-08
- **accessed:** 2026-09-03
- **confidence:** high
- **class:** primary-hardware-manual

### Claim 4 — Paula overrun is receive-buffer starvation and is cleared through `INTREQ.RBF`

- **claim:** Paula sets `SERDATR.OVRUN` if another complete character arrives before the processor picks up the previous character and clears the receive-buffer-full interrupt. The manual gives a service window of one character time (8–10 bit times). It specifies that resetting `INTREQ` bit 11 (`INTF_RBF`) resets the overrun condition; reading `SERDATR` alone is not documented as the clear action.
- **source:** `repos/fujinet-nio-driver/docs/amiga/Serial-IO-Interface.md`
- **publisher:** Commodore-Amiga / Addison-Wesley, *Amiga Hardware Reference Manual*, Third Edition (Ch. 8 Serial I/O extract)
- **pub_date:** 1991-08
- **accessed:** 2026-09-03
- **confidence:** high
- **class:** primary-hardware-manual

### Claim 5 — `IO_STATF_OVERRUN` is the driver's hardware-overrun status, distinct from its software buffer overflow

- **claim:** The official V37.4 header defines `IO_STATF_OVERRUN` as bit 8 (`1<<8`) of `IOExtSer.io_Status` and labels it the read/RBF overrun. The RKM status table calls bit 8 “Read overrun.” The RKM error table separately maps `SerErr_LineErr` to hardware data overrun and `SerErr_BufOverflow` to read-buffer overflow, so these are not interchangeable failure modes.
- **source URL:** https://amigadev.elowar.com/read/ADCD_2.1/Includes_and_Autodocs_2._guide/node004B.html
- **publisher:** Amiga, Inc. / Commodore SDK include `devices/serial.h`, Release 2.04 V37.4
- **pub_date:** 1990-11-06
- **accessed:** 2026-09-03
- **confidence:** high
- **class:** primary-sdk-header

### Claim 6 — classic `serial.device` software-latches Paula's overrun for later query/error delivery

- **claim:** In the archived V42 receive interrupt handler, the driver reads `SERDATR`; if its sign/overrun bit is set, it clears `INTREQ.RBF`, sets its internal `IOSTB_OVERRUN`, and marks the affected receive-buffer position. `SDCMD_QUERY` copies that internal status into `io_Status`. When a read reaches the marked position, the driver returns `SerErr_LineErr` and clears the internal overrun flag. This explains how `IO_STATF_OVERRUN` can remain observable after the instantaneous Paula condition has been acknowledged, without invoking any TX→RX transition.
- **source URL:** https://github.com/Arquivotheca/amiga-os-src/blob/b78c1ada537615c6eda889ad97b4ccd51ff4a178b/os-source/v42/src/workbench/devs/serial/read.asm
- **publisher:** Commodore-Amiga source (RCS metadata), preserved by Arquivotheca archival mirror
- **pub_date:** 1993-10-01
- **accessed:** 2026-09-03
- **confidence:** medium (source content is internally consistent and carries Commodore copyright/RCS history, but repository provenance is unofficial)
- **class:** archival-driver-source

### Claim 7 — `CMD_WRITE` uses Paula's TBE/SERDAT path and does not reconfigure the receiver

- **claim:** The archived V42 write handler services the transmit-buffer-empty (`TBE`) interrupt, clears `INTREQ.TBE`, formats the next output character, and writes `SERDAT`. CIA-B is consulted only for CTS/DSR when seven-wire handshaking is enabled. It does not disable RBF, change receive mode, or perform a post-write switch to receive. Driver initialization installs independent RBF and TBE interrupt vectors.
- **source URL:** https://github.com/Arquivotheca/amiga-os-src/blob/b78c1ada537615c6eda889ad97b4ccd51ff4a178b/os-source/v42/src/workbench/devs/serial/write.asm
- **publisher:** Commodore-Amiga source (RCS metadata), preserved by Arquivotheca archival mirror
- **pub_date:** 1991-01-12
- **accessed:** 2026-09-03
- **confidence:** medium (unofficial archival provenance)
- **class:** archival-driver-source

### Claim 8 — one `SERPER` controls both directions

- **claim:** Hardware defines `SERPER = (3,579,545 / baud) - 1` on NTSC and `(3,546,895 / baud) - 1` on PAL; `N+1` color clocks separate both receive samples and transmitted bits. The RKM likewise defines `io_Baud` as the baud for reads and writes. There is no independent TX and RX baud setting in the built-in UART API.
- **source:** `repos/fujinet-nio-driver/docs/amiga/Serial-IO-Interface.md`
- **publisher:** Commodore-Amiga / Addison-Wesley, *Amiga Hardware Reference Manual*, Third Edition (Ch. 8 Serial I/O extract)
- **pub_date:** 1991-08
- **accessed:** 2026-09-03
- **confidence:** high
- **class:** primary-hardware-manual

### Claim 9 — the classic V42 driver accepts 38,400 and 57,600 and uses truncating “magic constant” arithmetic

- **claim:** The archived source accepts requested rates from 112 through 292,000. `sCalcBaud` multiplies the requested baud by 7, selects `BaudMagic=25,000,000` for nominal NTSC or `PALBaudMagic=24,772,416` at 50 Hz, then uses integer `DIVU` and right shifts before writing the resulting word to `SERPER`. Requests over 65,535 in the intermediate path are scaled down by 32 before division and the quotient is shifted down by 32 afterward. It does not test an explicit percentage tolerance or choose the mathematically nearest divider. Out-of-range values follow `ParamErr` and return `SerErr_InvParam`; the source defines `SerErr_BaudMismatch` but the examined built-in set-parameters path does not emit it.
- **source URL:** https://github.com/Arquivotheca/amiga-os-src/blob/b78c1ada537615c6eda889ad97b4ccd51ff4a178b/os-source/v42/src/workbench/devs/serial/setparams.asm
- **publisher:** Commodore-Amiga source (RCS metadata), preserved by Arquivotheca archival mirror
- **pub_date:** 1991-01-12
- **accessed:** 2026-09-03
- **confidence:** medium (algorithm is explicit, but repository provenance is unofficial)
- **class:** archival-driver-source

### Claim 10 — official public documentation does not define a baud-error tolerance

- **claim:** The official RKM says the driver rejects a rate when hardware cannot support it; the Release 2 autodoc states the concrete accepted interval 112–292,000. Neither retrieved official document specifies an allowed percentage mismatch or a nearest-rounding rule. Therefore the actual-rate error figures above are source-derived calculations, not evidence of a formally guaranteed tolerance.
- **source URL:** https://amigadev.elowar.com/read/ADCD_2.1/Includes_and_Autodocs_2._guide/node05AB.html
- **publisher:** Commodore-Amiga Includes and Autodocs 2.0, `serial.device/SDCMD_SETPARAMS`
- **pub_date:** c. 1990
- **accessed:** 2026-09-03
- **confidence:** high for absence in the retrieved API contract; medium for any broader claim about all OS revisions
- **class:** primary-os-autodoc

### Claim 11 — `SERF_RAD_BOOGIE` reduces driver work; it does not alter SERPER or hardware direction

- **claim:** The official autodoc says `SERF_RAD_BOOGIE` skips parity, XON/XOFF, non-8-bit-length, and break checks and also sets `SERF_XDISABLED`. The RKM warns that receive overruns can still occur on a busy multitasking/display-intensive system. The archived receive ISR confirms a fast branch after reading `SERDATR` and clearing `RBF`; set-parameters still calls the same `sCalcBaud` regardless of this flag. It is therefore a receive-processing fast path, not a baud multiplier, FIFO enable, or TX→RX switch.
- **source URL:** https://amigadev.elowar.com/read/ADCD_2.1/Includes_and_Autodocs_2._guide/node05AB.html
- **publisher:** Commodore-Amiga Includes and Autodocs 2.0, `serial.device/SDCMD_SETPARAMS`
- **pub_date:** c. 1990
- **accessed:** 2026-09-03
- **confidence:** high
- **class:** primary-os-autodoc

### Claim 12 — high baud is divider-supported but receive reliability is service-time limited

- **claim:** The RKM says the built-in driver accepts approximately 110 to 1 megabaud at the API/hardware level but warns that software overhead limits reliable reception above 19,200; output is not software-dependent. The Release 2 autodoc narrows its contract to 112–292,000 and warns asynchronous I/O above 32 KB/s is ambitious. The Hardware Reference Manual estimates roughly 150–250 kbit/s with a reasonable cable only when the receiver uses a tight polling loop instead of interrupts. Consequently 38,400 and especially 57,600 are valid programmed rates, but neither rate guarantees lossless interrupt-driven receive under system load.
- **source URL:** https://www.ikod.se/wp-content/uploads/2020/08/Amiga_ROM_Kernal_Reference_Manual_Devices_Third.pdf
- **publisher:** Commodore-Amiga / Addison-Wesley, *Amiga ROM Kernel Reference Manual: Devices*, Third Edition
- **pub_date:** 1991
- **accessed:** 2026-09-03
- **confidence:** high
- **class:** primary-os-manual

## Contradictions and reconciliation

1. **Hardware capability versus connector specification.** The UART extract calls Paula programmable from 110 to over 1,000,000 bit/s and estimates 150–250 kbit/s as possible with tight polling. The connector extract lists 19.2 kHz as the serial connector's maximum operating frequency and 31.25 kHz with a MIDI adapter. These are different layers: divider capability, practical CPU service capability, and conservative external-interface specification. They must not be collapsed into one “maximum baud” claim.

2. **RKM range versus Release 2 autodoc range.** The RKM prose says the built-in driver accepts 110 to about 1 megabaud (possibly rounding 110 to 112), while the Release 2 autodoc and V42 source enforce 112–292,000. For the decision at hand, both 38,400 and 57,600 lie inside every cited software range, so the discrepancy does not affect their validity.

3. **Manual ideal formula versus shipping driver arithmetic.** Applying the manual formula with mathematically nearest rounding does not reproduce the archived V42 driver's values. The driver uses compatibility-preserved constants and truncating arithmetic; its source explicitly notes an NTSC constant defect. Debugging or emulation should reproduce the driver algorithm when comparing actual classic-driver behavior, and use the HRM equation to convert the programmed divider to actual baud.

4. **Hardware overrun versus driver buffer overflow.** Paula's one-character holding behavior causes hardware overrun when RBF is not serviced in time. `serial.device` also has a larger software read buffer that can overflow separately. `IO_STATF_OVERRUN` and `SerErr_LineErr` point to the former; `SerErr_BufOverflow` points to the latter.

## Decision implications / next tests

- Reject the specific “CIA TX→RX mode transition” explanation unless new evidence identifies nonstandard hardware or code that explicitly repurposes a CIA timer/shift register.
- Treat an overrun observed immediately after `CMD_WRITE` as evidence that a receive character arrived before the RBF handler completed, potentially because the peer responds with little or no turnaround delay.
- Instrument or emulate Paula `SERDATR`, `INTREQ.RBF`, RBF interrupt entry/exit, and the driver's software overrun latch. Also record peer first-response-bit time relative to the last transmitted stop bit. CIA modem-control transitions are secondary unless seven-wire handshaking is enabled.
- Compare 38,400 versus 57,600 using the actual programmed dividers above. With 8N1 framing, one full character is about 263 µs at the NTSC driver's 38,080 baud and about 176 µs at its 56,818 baud; this is the approximate maximum RBF service window described by the HRM.
- Test `SERF_RAD_BOOGIE` as a reduction in receive ISR/software work, not as a fix for a direction-transition bug. If it changes the failure rate, that supports service-latency/overhead as the mechanism.

## Leads worth chasing

- Obtain an independently authenticated Commodore V37/V40/V42 `serial.device` binary and compare a focused disassembly of set-parameters, RBF, and TBE handlers with the archival source. This would raise the source-dependent claims from medium to high confidence.
- Check the exact Amiga model's RS-232 transceiver and motherboard schematic if the failure is model-specific; Paula/CIA ownership is stable, but electrical margin at 57,600 may vary.
- If the failing stack uses seven-wire mode, trace CIA-B CTS/RTS and the driver's timer-based CTS retry separately. That path can delay transmit service but still does not switch Paula between TX and RX.

## Searches that found nothing

- Broad searches of official Hardware Reference Manual, RKM Devices, Release 2 headers, and `serial.device` autodocs found no CIA-based TX/RX mode switch, no receiver-disable action attached to `CMD_WRITE`, and no claim that transmit completion itself sets receive overrun.
- No authenticated official public `serial.device` implementation or official disassembly was found in the allotted search. The only directly inspectable classic implementation located was the Arquivotheca archival source mirror, so implementation-specific claims retain medium confidence.
- No official percentage tolerance or rounding guarantee for arbitrary `io_Baud` values was found. The documented contract gives accepted ranges and warnings; actual rounding behavior was recovered only from the archival source.

## Source list

1. In-tree AHRM 3rd ed. extracts (print-validated): `repos/fujinet-nio-driver/docs/amiga/Serial-IO-Interface.md`, `serial-interface-connector.md`, `cia-port-signal-assigments.md`, `cia-chip-register-map.md`
2. Commodore-Amiga / Addison-Wesley, *Amiga ROM Kernel Reference Manual: Devices*, Third Edition, 1991: https://www.ikod.se/wp-content/uploads/2020/08/Amiga_ROM_Kernal_Reference_Manual_Devices_Third.pdf
3. Commodore-Amiga SDK, `devices/serial.h`, Release 2.04 V37.4, 1990-11-06: https://amigadev.elowar.com/read/ADCD_2.1/Includes_and_Autodocs_2._guide/node004B.html
4. Commodore-Amiga Includes and Autodocs 2.0, `serial.device` autodoc: https://amigadev.elowar.com/read/ADCD_2.1/Includes_and_Autodocs_2._guide/node05AB.html
5. Commodore-Amiga V42 `serial.device` source, unofficial Arquivotheca archival mirror, `setparams.asm`: https://github.com/Arquivotheca/amiga-os-src/blob/b78c1ada537615c6eda889ad97b4ccd51ff4a178b/os-source/v42/src/workbench/devs/serial/setparams.asm
6. Same archive, `read.asm`: https://github.com/Arquivotheca/amiga-os-src/blob/b78c1ada537615c6eda889ad97b4ccd51ff4a178b/os-source/v42/src/workbench/devs/serial/read.asm
7. Same archive, `write.asm`: https://github.com/Arquivotheca/amiga-os-src/blob/b78c1ada537615c6eda889ad97b4ccd51ff4a178b/os-source/v42/src/workbench/devs/serial/write.asm

