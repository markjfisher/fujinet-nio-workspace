# Digest: proven Amiga `serial.device` patterns for immediate request/response

Decision focus: which classic-Amiga serial I/O patterns bear on reliable request/write/immediate-response exchanges at 38400/57600 baud.

Access date for every source: **2026-09-03**. Old documentation is used where it defines the unchanged classic Amiga API or hardware. This digest is evidence-only; project files were not used as evidence.

## Decision-relevant synthesis

The safest documented architecture is two distinct `IOExtSer` request objects (read and write) derived from one successfully opened/configured request, with a read kept pending asynchronously when no bytes are buffered. `serial.device` does buffer input even with no pending read, so a synchronous write followed by a read does not inherently create a receive blind spot; however, `DoIO(CMD_WRITE)` can block indefinitely under handshaking, and distinct requests allow the response to be collected concurrently. For high-speed receive, the Commodore pattern is: `SDCMD_QUERY`; synchronously drain the reported count (bounded by the application buffer); if the count is zero, `SendIO()` a one-byte read; on its completion, repeat. Do not have more than one read request outstanding.

At the API boundary, request 38400 or 57600 through `io_Baud` and check `SDCMD_SETPARAMS` for failure. `SERPER` is the underlying Paula hardware divisor and matters only to direct-hardware code or to understanding rate quantization; an application using `serial.device` should not calculate or write `SERPER`. Flow control and buffer capacity are the practical reliability levers: request RTS/CTS by setting `SERF_7WIRE` **before `OpenDevice()`**, use a properly wired cable and matching peer configuration, enlarge `io_RBufLen`, and always retain/process `io_Actual` even when a read terminates early. A hardware overrun means a character has already been lost; no post-facto error handler can guarantee lossless recovery, so prevention and protocol-level retry/checking are required.

## Claims

### C1 — Correct construction and open sequencing

- **claim:** The request passed to `OpenDevice("serial.device", ...)` must be a zero-initialized, full-size `IOExtSer`, with a reply port. `SERF_SHARED` and `SERF_7WIRE` are open-time flags and must be set before `OpenDevice()` if wanted. `OpenDevice()` fills the serial-specific fields with current/default settings, which may then be adjusted with `SDCMD_SETPARAMS`.
- **source_url:** https://d0.se/autodocs/serial.device/OpenDevice and https://amigadev.elowar.com/read/ADCD_2.1/Includes_and_Autodocs_2._guide/node004B.html
- **publisher:** Commodore-Amiga / Amiga, Inc. SDK documentation and `devices/serial.h` (mirrored by d0.se and ADCD 2.1)
- **pub_date:** `serial.h` revision dated 1990-11-06; AutoDoc date not stated
- **accessed:** 2026-09-03
- **confidence:** high
- **class:** API compatibility / initialization

### C2 — Fields for ordinary 8N1 binary operation

- **claim:** For ordinary 8N1 binary operation, configure `io_Baud` to the desired numeric rate, `io_ReadLen = 8`, `io_WriteLen = 8`, `io_StopBits = 1`, parity off (`SERF_PARTY_ON` clear), and normally software flow control off (`SERF_XDISABLED` set) when the protocol treats all byte values as payload. `io_RBufLen` is a recommended device input-buffer size, not the length of an individual application read. `SDCMD_SETPARAMS` must be issued only while no serial I/O request is pending, and its error must be checked.
- **source_url:** https://wiki.amigaos.net/wiki/Serial_Device
- **publisher:** AmigaOS Documentation Wiki; material derived from *Amiga ROM Kernel Reference Manual: Devices*
- **pub_date:** page revision 2025-01-26 (classic API content originally published in the Commodore RKM)
- **accessed:** 2026-09-03
- **confidence:** high
- **class:** API compatibility / configuration

### C3 — 38400/57600 and `SERPER`

- **claim:** `serial.device` accepts the desired real baud rate in `io_Baud` and rejects a request the underlying hardware cannot support; the documented interface range is 110–292000 baud. Thus 38400/57600 should be requested as numeric `io_Baud` values and accepted only if `SDCMD_SETPARAMS` succeeds. `SERPER` is the Paula hardware period register used by direct-hardware code; its divisor is derived from the PAL/NTSC color clock. The OS device API exposes `io_Baud`, not a caller-supplied `SERPER` value.
- **source_url:** https://wiki.amigaos.net/wiki/Serial_Device and `repos/fujinet-nio-driver/docs/amiga/Serial-IO-Interface.md`
- **publisher:** AmigaOS Documentation Wiki / Commodore-Amiga, *Amiga Hardware Reference Manual* (Ch. 8 extract)
- **pub_date:** RKM page revision 2025-01-26; hardware manual 1991-08
- **accessed:** 2026-09-03
- **confidence:** high for API boundary and hardware role; medium for successful operation on every specific machine/driver because acceptance is explicitly hardware-dependent
- **class:** version/compatibility

### C4 — Synchronous write then read versus pre-posted read

- **claim:** The device buffers all received characters after open even when no read is pending, so an immediate response arriving during a synchronous write is not automatically lost merely because the application has not yet posted `CMD_READ`. Nevertheless, `DoIO(CMD_WRITE)` waits for completion and may never return when handshaking stalls. A distinct asynchronous read request removes that blocking dependency and enables the documented simultaneous read/write operation.
- **source_url:** https://wiki.amigaos.net/wiki/Serial_Device
- **publisher:** AmigaOS Documentation Wiki; material derived from *Amiga ROM Kernel Reference Manual: Devices*
- **pub_date:** page revision 2025-01-26
- **accessed:** 2026-09-03
- **confidence:** high
- **class:** architecture pattern / reliability

### C5 — Documented high-speed receive loop

- **claim:** The documented throughput-oriented receive loop is: run `SDCMD_QUERY`; if bytes are available, `DoIO(CMD_READ)` exactly that count or the application-buffer maximum (which is guaranteed not to wait); if none are available, `SendIO(CMD_READ)` for one byte and wait for its completion, then query again. Larger transfers reduce per-request overhead. This is stronger evidence than simply issuing a large blocking read after each write.
- **source_url:** https://wiki.amigaos.net/wiki/Serial_Device and https://d0.se/autodocs/serial.device/CMD_READ
- **publisher:** AmigaOS Documentation Wiki / Commodore-Amiga serial.device AutoDocs (d0.se mirror)
- **pub_date:** wiki page revision 2025-01-26; AutoDoc date not stated
- **accessed:** 2026-09-03
- **confidence:** high
- **class:** architecture pattern / performance

### C6 — Outstanding request constraints

- **claim:** True overlapping input and output requires separate `IOExtSer` objects because an I/O request cannot be repurposed while outstanding. The RKM demonstrates duplicating the opened read request into a separate write request and says this permits simultaneous reading and writing. It also warns that multiple outstanding read requests will probably fail (AutoDoc). Two separate tasks require separate message ports; for a single task, a mature open-source AmigaOS implementation (Basilisk II) creates distinct read and write requests on the same reply port and a separate control request/port.
- **source_url:** https://wiki.amigaos.net/wiki/Serial_Device, https://d0.se/autodocs/serial.device/CMD_READ, and https://github.com/cebix/macemu/blob/master/BasiliskII/src/AmigaOS/serial_amiga.cpp
- **publisher:** AmigaOS Documentation Wiki / Commodore-Amiga AutoDocs / Christian Bauer and macemu contributors
- **pub_date:** wiki revision 2025-01-26; AutoDoc date not stated; Basilisk II AmigaOS implementation dates to approximately 2002 in the retrieved repository history
- **accessed:** 2026-09-03
- **confidence:** high for distinct requests, read/write overlap, and separate ports across tasks; medium-high for one-port/single-task pattern because it is implementation evidence rather than an explicit RKM prescription
- **class:** architecture pattern / concurrency

### C7 — RTS/CTS semantics

- **claim:** `SERF_7WIRE` selects the serial device's RS-232 CTS/RTS hardware-handshake mode and must be set at open time; the peer must use the same method and the cable must carry the control lines. This is not an in-band protocol feature. The retrieved official status table exposes CTS, RTS, DSR, CD, and DTR states, but the retrieved documentation only explicitly characterizes `SERF_7WIRE` as CTS/RTS protocol; no stronger claim about exactly which additional modem-control lines gate each operation is made here.
- **source_url:** https://d0.se/autodocs/serial.device/OpenDevice, https://wiki.amigaos.net/wiki/Serial_Device, and https://wiki.amigaos.net/wiki/AmigaOS_Manual:_Workbench_Preferences
- **publisher:** Commodore-Amiga AutoDocs (d0.se mirror) / AmigaOS Documentation Wiki
- **pub_date:** AutoDoc date not stated; Serial Device revision 2025-01-26; Workbench manual page date not stated
- **accessed:** 2026-09-03
- **confidence:** high
- **class:** API compatibility / electrical integration

### C8 — Buffer size, application-buffer alignment, and lifetime

- **claim:** `io_RBufLen` is a requested device receive-buffer size; the driver may be unable to resize it, and a failed replacement allocation leaves the old buffer active. Official user documentation recommends a larger input buffer at high baud rates or under multitasking load and lists preference choices from 512 to 65536 bytes. The retrieved RKM examples use ordinary `char[]` application buffers and state no special alignment constraint. Therefore there is evidence for sizing and lifetime discipline, but no evidence that a `CMD_READ` buffer needs chip RAM, DMA alignment, or a power-of-two size.
- **source_url:** https://wiki.amigaos.net/wiki/Serial_Device and https://wiki.amigaos.net/wiki/AmigaOS_Manual:_Workbench_Preferences
- **publisher:** AmigaOS Documentation Wiki / AmigaOS Workbench manual
- **pub_date:** Serial Device revision 2025-01-26; Workbench manual page date not stated
- **accessed:** 2026-09-03
- **confidence:** high for `io_RBufLen` semantics and larger-buffer recommendation; medium for absence of alignment requirements (documentation silence plus unaligned `char[]` examples, not an explicit guarantee)
- **class:** implementation constraint / buffering

### C9 — Overrun and loss handling

- **claim:** The API distinguishes hardware data overrun (`SerErr_LineErr`) from device read-buffer overflow (`SerErr_BufOverflow`); `SDCMD_QUERY` also reports a read-overrun status bit. Reads can complete partially and `io_Actual` is authoritative, including when terminated early by an error. Robust code must preserve/process those `io_Actual` bytes before retrying. However, a Paula hardware overrun means the receive register was not serviced before the next character completed, so at least one byte is already unrecoverable; lossless recovery then requires a higher-level framed protocol with checksum/sequence/retry, not merely another `CMD_READ`.
- **source_url:** https://wiki.amigaos.net/wiki/Serial_Device and `repos/fujinet-nio-driver/docs/amiga/Serial-IO-Interface.md`
- **publisher:** AmigaOS Documentation Wiki / Commodore-Amiga, *Amiga Hardware Reference Manual* (Ch. 8 extract)
- **pub_date:** wiki revision 2025-01-26; hardware manual 1991-08
- **accessed:** 2026-09-03
- **confidence:** high for error/status meanings, partial completion, and irrecoverability after hardware overrun; medium for the higher-level retry recommendation because it is a direct engineering implication rather than an Amiga API mandate
- **class:** failure mode / recovery

### C10 — High-speed mode is conditional, not a cure-all

- **claim:** `SERF_RAD_BOOGIE` skips some internal checks to increase throughput, but is documented only for parity off, XON/XOFF off, 8-bit characters, and no break testing. The manual warns that multitasking load can still make the driver unable to keep up at high rates. It is therefore a conditional optimization, not evidence that 57600 will be reliable under every workload.
- **source_url:** https://wiki.amigaos.net/wiki/Serial_Device
- **publisher:** AmigaOS Documentation Wiki; material derived from *Amiga ROM Kernel Reference Manual: Devices*
- **pub_date:** page revision 2025-01-26
- **accessed:** 2026-09-03
- **confidence:** high
- **class:** performance / failure risk

## Open-source implementation pattern

The retrieved Basilisk II AmigaOS backend is the strongest credible source example located in-budget. It creates three full-size requests: read and write on one I/O reply port, control on a separate port; opens with the read request; copies the initialized/opened request into the other two; then restores the appropriate reply-port pointers. It sets parameters through the control request. This corroborates the RKM's distinct-request pattern while showing that separate message ports are not necessary merely because read and write overlap inside one task. It does **not** establish the best buffer size for 38400/57600, and its shown default `io_RBufLen = 64` should not be generalized as a high-speed recommendation.

Source metadata:

- **source_url:** https://github.com/cebix/macemu/blob/master/BasiliskII/src/AmigaOS/serial_amiga.cpp
- **publisher:** Christian Bauer / macemu contributors
- **pub_date:** approximately 2002 for the retrieved AmigaOS file lineage; current master retrieved
- **accessed:** 2026-09-03
- **confidence:** medium-high
- **class:** implementation evidence

## Contradictions and cautions

1. **The starting tutorial is not reliable enough to copy verbatim.** Its example sets `SERF_SHARED` only *after* `OpenDevice()`, contradicting the official requirement that the shared flag be set before open. The same ordering would be wrong for `SERF_7WIRE`. It also describes the UART as CIA-B shift-register/custom-chip-DMA based, whereas the hardware manual identifies Paula serial registers and interrupt-driven servicing. Treat its `SERPER` table as direct-hardware background, not application setup for `serial.device`.
   - source_url: https://github.com/alfishe/amiga-bootcamp/blob/main/10_devices/serial.md
   - publisher: alfishe / amiga-bootcamp
   - pub_date: not stated in retrieved page
   - accessed: 2026-09-03
   - confidence: high (contradiction directly visible against primary documentation)
   - class: source-quality contradiction

2. **Preferences UI versus device API:** the retrieved Workbench Preferences page lists selectable rates only through 31250, while the device documentation gives a much broader programmable range and says unsupported rates are rejected. This is a UI/default-list difference, not evidence that `io_Baud = 38400` or `57600` is forbidden. Per-machine/driver acceptance must still be checked.
   - source_url: https://wiki.amigaos.net/wiki/AmigaOS_Manual:_Workbench_Preferences and https://wiki.amigaos.net/wiki/Serial_Device
   - publisher: AmigaOS Documentation Wiki
   - pub_date: Serial Device revision 2025-01-26; Workbench manual page date not stated
   - accessed: 2026-09-03
   - confidence: high
   - class: compatibility contradiction resolved

## Leads and searches with no sufficient result

- Searches for public NComm and Amiga C-Kermit implementation source did not locate a directly inspectable Amiga backend within the call budget. Kermit documentation confirms `serial.device/0` as the Amiga line name, but not the internal request pattern, so it is not used for a claim.
- No credible retrieved example demonstrated recovery from an actual hardware overrun **without** data loss. This is expected from the hardware definition of overrun; prevention plus protocol-level retry is the defensible route.
- No primary source retrieved in-budget gave a special alignment requirement for application read/write buffers. Do not infer one from generic DMA concerns; the documented API examples use ordinary byte arrays.
- The exact stock-driver baud divisor choice/rounding at 38400 and 57600 was not verified from device source. The API contract is to pass `io_Baud` and check `SDCMD_SETPARAMS`, not to duplicate the driver's divisor calculation.

## Sources used (8 maximum)

1. AmigaOS Documentation Wiki, “Serial Device”: https://wiki.amigaos.net/wiki/Serial_Device
2. Commodore-Amiga serial.device AutoDoc, `OpenDevice` mirror: https://d0.se/autodocs/serial.device/OpenDevice
3. Commodore-Amiga serial.device AutoDoc, `CMD_READ` mirror: https://d0.se/autodocs/serial.device/CMD_READ
4. Amiga/Commodore `devices/serial.h`, ADCD 2.1 mirror: https://amigadev.elowar.com/read/ADCD_2.1/Includes_and_Autodocs_2._guide/node004B.html
5. AHRM 3rd ed. Paula UART extract: `repos/fujinet-nio-driver/docs/amiga/Serial-IO-Interface.md`
6. AmigaOS Documentation Wiki, “Workbench Preferences — Serial Editor”: https://wiki.amigaos.net/wiki/AmigaOS_Manual:_Workbench_Preferences
7. Christian Bauer / macemu, Basilisk II AmigaOS serial backend: https://github.com/cebix/macemu/blob/master/BasiliskII/src/AmigaOS/serial_amiga.cpp
8. alfishe, amiga-bootcamp `serial.md` (starting lead, used mainly for contradiction checking): https://github.com/alfishe/amiga-bootcamp/blob/main/10_devices/serial.md
