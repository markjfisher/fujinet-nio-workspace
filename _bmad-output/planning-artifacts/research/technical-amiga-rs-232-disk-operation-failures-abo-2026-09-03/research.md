---
title: 'Technical research: Amiga RS-232 disk-operation failures above 9600 baud'
type: 'technical'
topic: 'Amiga RS-232 disk-operation failures above 9600 baud'
decision: 'Select the fastest, lowest-risk experiments and fixes that make disk-oriented FujiNet NIO request/response operations reliable above 9600 baud while preserving reliable long-lived network traffic.'
source: 'native web research plus current repository inspection'
status: complete
preset: 'standard'
validation: 'normal'
created: '2026-09-03'
updated: '2026-09-04'
claims_verified: 10
claims_unverified: 1
---

# Technical research: Amiga RS-232 disk-operation failures above 9600 baud

**Decision this research serves:** Select the fastest, lowest-risk experiments and fixes that make disk-oriented FujiNet NIO request/response operations reliable above 9600 baud while preserving reliable long-lived network traffic.

This report **supersedes** the 2026-08-28 RS-232 overrun handoff (CIA 8520 TX→RX as confirmed cause). That document is archived and must not drive work: [`_bmad-output/archive/handoff-amiga-rs232-overrun-2026-08-28.md`](../../../archive/handoff-amiga-rs232-overrun-2026-08-28.md).

## Executive summary

The fastest route to reliable 38,400 operation is a controlled response-size and pacing matrix, followed by the least costly fix that the matrix validates. The leading hypothesis is receive-burst pressure: the existing one-second `tx_gap_us` test delayed only the start of the response and did not pace its bytes. [9] If modest inter-byte or inter-chunk pacing prevents the fault, retain 38,400 baud for Amiga-to-ESP requests and apply the fastest response-pacing profile that remains reliable.

Do not build the fix around a CIA TX→RX transition. Paula has independent full-duplex transmit and receive paths; `IO_STATF_OVERRUN`/`SerErr_LineErr` means the prior received character was not serviced before the next one completed. `CMD_READ` reports that latched fault but did not necessarily cause it. [1][2][4][14][15] Nor is there a separate disk transport: the inspected FHOST, FLS, FIN, appstore, and network call sites all reach the same resident serial backend. [6][7][13] Response length, burst shape, service timing, system load, and cold/warm state are the remaining differentiators. FLS permits a 420-byte payload. [13]

Repeat RTS/CTS only after setting `SERF_7WIRE` before `OpenDevice()`; the previous test set it too late to validate Amiga seven-wire mode. [3][5] Test a separate pre-posted read as a scheduling experiment, not as a way to switch Paula into receive mode. A ping is justified only if failures prove cold-only: use it once per physical backend open/reconfiguration. If warm requests fail, per-request ping adds another vulnerable response. Possible robust designs include READY/GO or request IDs with replay and duplicate suppression; RFC 7252 supplies precedent for the latter pattern. [11]

## Established hardware constraints

**AHRM source of truth (in-tree, print-validated).** Do not fetch the Hardware Reference Manual PDF. Use these extracts:

- Paula UART: [`Serial-IO-Interface.md`](../../../../../repos/fujinet-nio-driver/docs/amiga/Serial-IO-Interface.md) [1]
- CIA-B handshake pins: [`cia-port-signal-assigments.md`](../../../../../repos/fujinet-nio-driver/docs/amiga/cia-port-signal-assigments.md) [14]
- CIA address maps / unused CIAB `sdr`: [`cia-chip-register-map.md`](../../../../../repos/fujinet-nio-driver/docs/amiga/cia-chip-register-map.md) [14]
- DB25 spec, software modem control, 19.2 kHz connector rating: [`serial-interface-connector.md`](../../../../../repos/fujinet-nio-driver/docs/amiga/serial-interface-connector.md) [15]

Do not re-derive Paula behaviour from the archived overrun handoff or from CIA 8520 serial-shift folklore.

The Paula UART extract states: Paula contains the UART; receive and transmit use separate shift/buffer paths; `TBE` is for full-duplex and `TSRE` for half-duplex; `SERPER` sets the interval for both receive sampling and transmit bit times; overrun is set if another character completes before software picks up `SERDATR` and clears `INTF_RBF`, with a service window of one character time (8–10 bit times).

### No TX→RX transition

There is no documented hardware transition from transmit mode to receive mode:

- Paula has separate TX and RX shift/buffer paths intended for full-duplex use. `TBE`/`SERDAT` service does not disable `RBF`/`SERDATR`. [1]
- CIA-B handles RTS, CTS, DTR, DSR, and CD policy; CIAB `sdr` is unused and RS-232 data is Paula. Modem-control lines are software-driven and have no hardware effect on TXD/RXD. [14][15]
- `serial.device` buffers received characters continuously after `OpenDevice()`, whether or not `CMD_READ` is pending. [3]
- A Paula overrun occurs when the RBF handler does not clear the prior received character before the next one completes. At the stock driver's programmed rates, the RBF handler has about 262 µs per character at requested 38,400 and 175 µs at requested 57,600 on PAL. [1][4]
- The driver latches the hardware overrun and reports it when a read reaches the marked receive-buffer position. Thus, a diagnostic can report the fault at `CMD_READ` after a completed write without implying that the write caused it. [4]

The existing source comments that mention a CIA UART, CIA ISR, and TX→RX switch are incorrect and should be removed before further experiments; they are currently steering diagnosis toward a nonexistent state transition. [6]

### SERPER and baud correctness

Applications using `serial.device` should not calculate or write `SERPER`. They request the real rate in `IOExtSer.io_Baud`, issue `SDCMD_SETPARAMS`, and check its error. `SERPER` is the Paula hardware divisor programmed by the device. [2][3]

The archived V42 driver accepts both requested rates. Replaying its integer divisor algorithm gives approximately:

| Requested baud | PAL programmed rate | Error | Character time, 8N1 |
| ---: | ---: | ---: | ---: |
| 38,400 | 38,139 | −0.68% | 262 µs |
| 57,600 | 57,208 | −0.68% | 175 µs |

The public documentation does not specify a permitted percentage error. The identical derived PAL error at both requested rates means that the divisor calculation alone does not explain why 38,400 fails intermittently while 9,600 works. However, at 57,600 the interrupt handler has only two-thirds of the service time available at 38,400. Because the divisor calculations rely on an unofficial archival source mirror, they are medium confidence. The public API conclusion—use `io_Baud`, not direct `SERPER`—is high confidence. [1][4]

`SERF_RAD_BOOGIE` removes some serial-driver checks and overhead under 8-bit, no-parity, no-XON/XOFF operation. It does not alter `SERPER`, create a FIFO, or change transmit/receive direction, and the manual warns that high-speed overruns remain possible under system load. [2]

## Why network can work while FLS/FHOST/FIN fail

The network soak test disproves a generic 38,400 electrical or framing failure, but it does not prove all response profiles are safe:

1. The inspected service and application calls share the same physical serial exchange path. There is no separate “disk UART” to fix. [6][7][13]
2. The service replies differ. FLS can request 420 bytes of payload. [13] Network write acknowledgements and many polling replies appear smaller from their structures, but the exact wire sizes in the reported trials were not logged. The proposed correlation between larger continuous bursts and missed RBF deadlines remains unverified.
3. ESP service time differs. A TCP operation may naturally insert network/task scheduling gaps before a short FujiBus response, whereas host/file/disk metadata can be returned immediately from local state.
4. The successful proving tool is not equivalent to a cold FLS/FHOST run. Before its first broker exchange it opens and closes `serial.device` in `try_open_serial()`. Its first request is a small clock request, and its file-list marker occurs only after several clock requests, a deliberate timeout/recovery cycle, and concurrent exchanges. [8]
5. The resident broker does not normally close its serial backend merely because a CLI process exits. Cold/warm state therefore must be measured explicitly rather than inferred from application lifetime. [6]

## RTS/CTS: why the attempt was inconclusive

The previous test corrected the ESP pin mapping but set `SERF_7WIRE` only during the post-open `SDCMD_SETPARAMS` call. Commodore's device contract requires `SERF_7WIRE` when calling `OpenDevice()`. [3][5] Therefore, the test does not establish that Amiga hardware handshaking was active.

A valid retest must:

1. Put `SERF_7WIRE` in `io_SerFlags` before `OpenDevice("serial.device", ...)`.
2. Retain `SERF_7WIRE | SERF_XDISABLED | SERF_RAD_BOOGIE` in the later parameters.
3. Enable `UART_HW_FLOWCTRL_CTS_RTS` on the ESP and confirm the selected UART and routed GPIOs in logs.
4. Capture Amiga TXD/RXD/RTS/CTS and ESP-side GPIO levels with a logic analyzer, accounting for inversion in the RS-232 transceiver.
5. Confirm that Amiga RTS reaches the ESP CTS input. ESP CTS—not ESP RTS—is what gates an ESP response. ESP automatic RTS follows its receive-FIFO threshold; the archived classic Amiga driver similarly manages RTS from receive-buffer thresholds, not from the presence of a user `CMD_READ`. [4][10]

Correct seven-wire flow control protects finite buffers and is worth retaining if verified, but it may deassert too late to prevent Paula's one-character hardware overrun. A passing result would be useful; a failing result would not revive the TX→RX hypothesis.

## Ping/pong and pending-read answers

### Pending `CMD_READ` before `CMD_WRITE`

This is a valid experiment but not for the reason stated in the handoff. It will not keep Paula “in receive mode”; Paula is already receiving, and `serial.device` is already buffering. [1][3] To run the experiment correctly, use two `IOExtSer` requests: queue an asynchronous one-byte read on one request, then perform the write on the other. Separate requests are the documented way to overlap serial reads and writes; avoid multiple simultaneous read requests. [3][12]

If pre-posting alone fixes the issue, it reveals a driver scheduling/delivery effect worth exploiting. If it does not, that is expected for a true Paula RBF interrupt-service overrun, because the same receive ISR still has the same per-character deadline.

### Initial idempotent ping/pong

It is worthwhile only as a tightly scoped diagnostic or compatibility warm-up:

- **Cold-only failure confirmed:** after each physical backend open or baud reconfiguration, send an idempotent HELLO/PING. Tolerate and retry an initial failed response, and start normal requests only after a valid PONG. Run this warm-up once per backend open or reopen.
- **Warm failures observed:** do not ping before every request. The PONG is itself an immediate response and can overrun. It adds latency without establishing readiness.
- **Arbitrary automatic request retry:** unsafe for non-idempotent commands unless duplicate execution is prevented. Request IDs plus duplicate suppression or cached-response replay are one possible design. [11]

## Ranked investigation and fix options

| Rank | Option | What it tests/fixes | Cost and risk | Recommendation |
| ---: | --- | --- | --- | --- |
| 1 | Faithful cold/warm + response-size diagnostic | Separates first-exchange state from burst length and service timing | Small diagnostic changes; no protocol change | Do first |
| 2 | ESP response pacing by byte or chunk | Directly reduces Paula RBF deadline pressure while retaining 38,400 request speed | Small configurable firmware change; throughput trade-off | Test at 38,400; adopt only the fastest reliable profile |
| 3 | Correct seven-wire setup and four-channel capture | Validates end-to-end CTS gating and repairs the invalid prior test | Small Amiga/ESP change; requires analyzer | Run alongside rank 2 |
| 4 | Separate asynchronous read and synchronous write requests | Tests whether a pending read changes driver scheduling/delivery | Moderate Amiga lifetime/abort complexity | Diagnostic branch, not assumed fix |
| 5 | Cold-start PING warm-up | Hides a fault limited to first response after backend initialization | Small but masks root cause; only safe if PING is idempotent | Conditional workaround only |
| 6 | READY/GO or replay-safe request IDs | Prevents response before explicit readiness and permits safe retry | Cross-repository protocol/compatibility change | Use only if pacing/flow control cannot meet throughput |
| 7 | Alternate/custom serial driver or direct Paula polling | Avoids stock interrupt-service limits | Highest complexity and compatibility risk | Last resort for 57,600+ |

### Minimum real-hardware matrix

Make the first exchange type and response size deterministic and selectable: use clock, host-get, file-list, or a synthetic response of 8, 16, 32, 64, 128, 256, 420, or 512 bytes. Remove or relocate the pre-test `try_open_serial()` call so that it cannot prime the device. For each run, record the request and response wire lengths, time to first response bit, the `result`, `cause`, `native`, and `status` values, backend state, and system load.

For each matrix cell, run enough trials to convert the anecdotal rates into a failure-rate curve; 100 trials per cell is a useful target.

| Variable | Values |
| --- | --- |
| Baud | 9,600; 19,200; 38,400; later 57,600 |
| Backend state | explicit cold open/reconfigure; warm retained backend |
| Response size | 8–512 bytes as above |
| Start delay | 0; 1 ms; 10 ms; existing long-delay control |
| Inter-byte delay | 0; 125; 250; 500; 750 µs |
| Chunk pacing | 8, 16, 32-byte chunks with 0.5–2 ms gaps |
| Flow | none; correctly configured seven-wire |
| Receive strategy | current query/drain; one pre-posted async read |

At 38,400 baud, a 750 µs inter-byte delay plus the normal character time approximately matches the spacing of one character at 9,600 baud. If this setting is reliable, reduce the delay until you find the fastest reliable value. If short bursts are safe, chunk pacing may preserve considerably more throughput.

## Contrary evidence and limits

- The handoff reports an overrun even with a one-second pre-response gap. That contradicts a pure turnaround-settling problem but not burst-service starvation, because the implemented gap occurs once before the same unpaced burst. [9]
- A true hardware overrun is not caused by the configured 2,112-byte software receive buffer filling; the official API distinguishes `SerErr_LineErr` from `SerErr_BufOverflow`. Increasing `io_RBufLen` further is unlikely to solve this particular status, although a large buffer remains appropriate. [2][3][6]
- Because Bounce World runs for hours at 38,400, any explanation must account for why it remains reliable. The response-profile hypothesis remains medium confidence until actual wire lengths, timing, and overrun rates are captured.
- The exact V42 divisor implementation comes from an unofficial source archive. The hardware ownership, overrun definition, public baud API, and seven-wire open-time requirement do not depend on that archive. [1][2][3][4][14][15]

## Hardware-matrix decision gates

- **Response profile:** capture the exact serialized response lengths and time to first byte for successful Bounce World/appstore calls and failing FLS/FHOST/FIN calls.
- **Warm state:** determine whether the failure occurs on a warm backend with no preceding timeout, baud change, unload, or recovery.
- **Pacing:** identify the minimum inter-byte or inter-chunk pacing that makes 38,400 reliable under worst-case Workbench load.
- **Flow control:** verify whether Amiga RTS reaches ESP CTS and gates bytes on this board and cable when `SERF_7WIRE` is configured before `OpenDevice()`.
- **Pending read:** determine whether a pre-posted one-byte read changes the failure rate while response size and pacing remain constant.

## Source appendix

| Ref | Claim/finding supported | Publisher/source | Publication date | Accessed | Confidence |
| --- | --- | --- | --- | --- | --- |
| [1] | Paula UART ownership, independent TX/RX, RBF overrun and `SERPER` formula | [`repos/fujinet-nio-driver/docs/amiga/Serial-IO-Interface.md`](../../../../../repos/fujinet-nio-driver/docs/amiga/Serial-IO-Interface.md) (AHRM 3rd ed. Ch. 8 Serial I/O; print-validated) | 1991-08 | 2026-09-04 | High |
| [2] | `serial.device` baud/high-speed/error contract | [Commodore-Amiga, ROM Kernel Reference Manual: Devices](https://www.ikod.se/wp-content/uploads/2020/08/Amiga_ROM_Kernal_Reference_Manual_Devices_Third.pdf) | 1991 | 2026-09-03 | High |
| [3] | Continuous input buffering, seven-wire open-time requirement, separate requests | [AmigaOS Documentation Wiki, Serial Device (RKM-derived)](https://wiki.amigaos.net/wiki/Serial_Device) | revision 2025-01-26 | 2026-09-03 | High |
| [4] | Classic driver overrun latch/delivery and baud algorithm | [Commodore V42 serial.device archival source mirror](https://github.com/Arquivotheca/amiga-os-src/tree/b78c1ada537615c6eda889ad97b4ccd51ff4a178b/os-source/v42/src/workbench/devs/serial) | 1991–1993 | 2026-09-03 | Medium |
| [5] | Prior `SERF_7WIRE` placement after `OpenDevice()` | [fujinet-nio-driver commit 241cb4f1](https://github.com/markjfisher/fujinet-nio-driver/commit/241cb4f1bb47b3519f744ad4bc8d287e3837e092) | 2026-08-28 | 2026-09-03 | High |
| [6] | Current serial backend, lifecycle, recovery, and stale comments | [fujinet-nio-driver at 44bea7fd](https://github.com/markjfisher/fujinet-nio-driver/tree/44bea7fd44434f75a8f2b2622fc075611d1f5e0a/amiga) | 2026-09 | 2026-09-03 | High |
| [7] | Shared Amiga transport and per-call FujiBus exchange | [fujinet-nio-lib at a5406c8b](https://github.com/markjfisher/fujinet-nio-lib/tree/a5406c8bc71484a68f1de4d6117b90345f216751/src) | 2026-09 | 2026-09-03 | High |
| [8] | Proving tool's pre-open and warmed file-list ordering | [fujinet-nio-exchange.c at 44bea7fd](https://github.com/markjfisher/fujinet-nio-driver/blob/44bea7fd44434f75a8f2b2622fc075611d1f5e0a/amiga/tools/fujinet-nio-exchange.c) | 2026-09 | 2026-09-03 | High |
| [9] | `tx_gap_us` is one pre-write delay, not burst pacing | [fujinet-nio uart_channel.cpp at 32f54d15](https://github.com/markjfisher/fujinet-nio/blob/32f54d15f25c37bafddcf5fd3f2c22d02e8a2a82/src/platform/esp32/uart_channel.cpp) | 2026-09 | 2026-09-03 | High |
| [10] | ESP32-S3 CTS/RTS direction and FIFO-threshold behavior | [Espressif ESP-IDF UART documentation](https://docs.espressif.com/projects/esp-idf/en/stable/esp32s3/api-reference/peripherals/uart.html) | current v6.1 docs | 2026-09-03 | High |
| [11] | Separate response, identifiers, retransmission, duplicate handling precedent | [IETF RFC 7252](https://www.rfc-editor.org/info/rfc7252/) | 2014-06 | 2026-09-03 | High as protocol precedent |
| [12] | `CMD_READ` query/post pattern and warning against multiple outstanding reads | [Commodore serial.device CMD_READ AutoDoc mirror](https://d0.se/autodocs/serial.device/CMD_READ) | c. 1990 | 2026-09-03 | High |
| [13] | Inspected FHOST/FLS/FIN application call sites and FLS's 420-byte service-payload limit | [nio-core-apps at 542af6cc](https://github.com/markjfisher/nio-core-apps/tree/542af6cc28f737ba1819a6e3b5a98fab474ecbc6) | 2026-09 | 2026-09-03 | High |
| [14] | CIA-B DTR/RTS/CD/CTS/DSR GPIO; CIAB `sdr` unused; RS-232 UART is Paula | [`cia-port-signal-assigments.md`](../../../../../repos/fujinet-nio-driver/docs/amiga/cia-port-signal-assigments.md) (AHRM App. E Part 4) and [`cia-chip-register-map.md`](../../../../../repos/fujinet-nio-driver/docs/amiga/cia-chip-register-map.md) (AHRM App. F maps + SDR assignment note); print-validated | 1991-08 | 2026-09-04 | High |
| [15] | Serial connector pinout; modem control software-only and asynchronous to TXD/RXD; 19.2 kHz connector rating | [`serial-interface-connector.md`](../../../../../repos/fujinet-nio-driver/docs/amiga/serial-interface-connector.md) (AHRM App. E serial spec); print-validated | 1991-08 | 2026-09-04 | High |

## Staleness map

Computed from the claims ledger on 2026-09-04:

| Claim class | Re-check |
| --- | --- |
| Current code, ESP-IDF compatibility, and experimental cause | **2026-10-01**, after code/toolchain changes, or when the hardware matrix lands |
| Protocol architecture | 2028-09 |
| Classic `serial.device` API | 2035-01 |
| Paula hardware | Only for nonstandard hardware/device implementations |
