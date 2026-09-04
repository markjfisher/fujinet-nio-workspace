# Flow control and request/response turnaround — round 1 digest

- Decision served: explain why RTS/CTS did not hold an immediate FujiNet response, and assess pre-posted receive, ping/pong, ACK-before-response, fixed delay, and explicit ready/full-duplex designs.
- Scope: ESP32-S3 / ESP-IDF UART semantics plus transferable serial request/response patterns. The reported failure and the observation that long-lived network traffic works are investigation premises, not evidence.
- Accessed: 2026-09-03.
- Evidence limit: six primary vendor/standards sources retrieved in this run; no project file or prior project conclusion was used as evidence.

## Decision answer

The strongest explanation is that RTS/CTS was expected to solve a condition it does not represent. In ESP-IDF, enabling **RTS** enables receiver-side flow control driven by the ESP32-S3 RX FIFO threshold; enabling **CTS** enables flow control for the ESP32-S3 transmitter. Therefore FujiNet's own RTS cannot gate FujiNet's response. FujiNet TX is gated only by its CTS input, which must be routed, wired to the peer's readiness output, and enabled. Even when all of that is correct, the peer will normally continue to permit transmission while its hardware receive FIFO has space. Nothing in the ESP-IDF model makes an application-level `read()` or a posted I/O request the condition for asserting readiness. [S1][S2][S3][S4]

This makes a **pre-posted asynchronous read or a continuously active receive path** the best first corrective experiment and the cleanest likely design: arm the receiver before the request is transmitted, or keep one receive task/ring buffer active for the entire opened transport and frame responses there. If receive service remains continuously active, setup is once per opened transport/session; if it is torn down around writes, it must be armed before every request. This is an inference from the documented independence of UART reception from the application read path, not a verified statement about Amiga `serial.device`. [S1]

If the host API cannot safely keep a receive pending while it writes, add an explicit **client READY/GO phase tied to the request ID**: FujiNet accepts/buffers the request but emits no result until the host has armed its receive and sends READY. That readiness exchange is per request if every request recreates the turnaround window. A one-time session ping can establish liveness or negotiate a protocol version, but cannot establish momentary readiness for later responses. A server-generated immediate ACK does not by itself fix the problem because that ACK is also an immediate inbound byte stream and can be lost by the same mechanism. [S5][S6]

A fixed response delay is useful as a diagnostic and perhaps as a bounded compatibility fallback, but is not a robust preservation mechanism: no retrieved standard establishes a universal safe delay, and scheduling latency is not a stable wire contract. The robust protocol form is one outstanding request (or explicit request IDs), persistent receive buffering, timeout/retry, duplicate suppression, and cached/replayable responses until acknowledged. Modbus serial provides the one-request-at-a-time state-machine precedent; CoAP provides a well-specified precedent for separate ACK/response, request/response identifiers, retransmission, and duplicate handling. [S5][S6]

## Relevance-filtered claims

### C1 — ESP32-S3 RTS and CTS control opposite directions

- claim: On ESP32-S3, `UART_HW_FLOWCTRL_RTS` enables receiver flow control (`rx_flow_en`) and applies `rx_thrs`; `UART_HW_FLOWCTRL_CTS` enables transmitter flow control (`tx_flow_en`). Consequently, an ESP32-S3 response is held by its **CTS input**, not by its own RTS output.
- source URL: https://raw.githubusercontent.com/espressif/esp-idf/v6.1/components/esp_hal_uart/esp32s3/include/hal/uart_ll.h
- publisher: Espressif Systems (ESP-IDF source, v6.1 tag)
- pub_date: undated source snapshot (retrieved from current v6.1 tag)
- accessed: 2026-09-03
- confidence: high
- class: version/compatibility; implementation semantics

### C2 — Automatic RTS represents RX FIFO capacity, not application readiness

- claim: ESP32-S3 low-level code defines the RX flow signal as becoming active when RX FIFO occupancy exceeds the configured threshold. A second vendor's official UART description independently describes the common crossed-wire model: each endpoint outputs RTS to report ability to accept bytes and reads CTS for permission to send. Neither source defines readiness as “an application read is pending.”
- source URL: https://raw.githubusercontent.com/espressif/esp-idf/v6.1/components/esp_hal_uart/esp32s3/include/hal/uart_ll.h ; https://www.ti.com/lit/an/swra779/swra779.pdf
- publisher: Espressif Systems; Texas Instruments
- pub_date: ESP-IDF v6.1 snapshot, exact date not shown; TI SWRA779, 2023-09
- accessed: 2026-09-03
- confidence: high
- class: flow-control semantics; independently corroborated

### C3 — Posting an ESP-IDF read is not what enables hardware reception

- claim: ESP-IDF documents reception as hardware FSM -> RX FIFO -> application read, and the installed driver allocates an RX ring buffer. `uart_read_bytes()` retrieves bytes after reception. Thus, on the ESP32-S3 side, calling or blocking in `uart_read_bytes()` is not a prerequisite for the UART hardware to accept incoming bytes, and it is not documented as a flow-control line transition.
- source URL: https://docs.espressif.com/projects/esp-idf/en/stable/esp32s3/api-reference/peripherals/uart.html
- publisher: Espressif Systems
- pub_date: ESP-IDF Programming Guide v6.1, exact page date not shown
- accessed: 2026-09-03
- confidence: high for ESP-IDF; unverified for Amiga `serial.device`
- class: version/compatibility; receive-path semantics

### C4 — Flow control must be explicitly enabled and physically routed

- claim: ESP-IDF's UART HAL initialization disables hardware flow control. The public API separately requires UART signal pin assignment; the driver uses direct IOMUX routing when a GPIO matches the native signal and otherwise uses the GPIO Matrix. ESP32-S3 reset-field descriptions show `tx_flow_en=0`, `rx_flow_en=0`, `cts_inv=0`, and `rts_inv=0`. Therefore wiring alone is insufficient, and actual first-transaction CTS/RTS levels must not be inferred without checking configuration and the signal at the relevant electrical point.
- source URL: https://github.com/espressif/esp-idf/blob/master/components/esp_hal_uart/uart_hal.c ; https://docs.espressif.com/projects/esp-idf/en/stable/esp32s3/api-reference/peripherals/uart.html ; https://raw.githubusercontent.com/espressif/esp-idf/v6.1/components/soc/esp32s3/register/soc/uart_struct.h
- publisher: Espressif Systems
- pub_date: current source/docs snapshots; exact dates not shown
- accessed: 2026-09-03
- confidence: high for configuration defaults/routing; medium for any conclusion about observed electrical level because external inversion/level shifting was not inspected
- class: version/compatibility; hardware integration

### C5 — Correctly crossed RTS/CTS protects buffers at byte boundaries

- claim: Official UART guidance describes RTS from the receiving UART connected to CTS of the transmitting UART. CTS deassertion can stop subsequent bytes, while a byte already in progress may complete; receiver headroom must account for that. This is buffer-overrun control, not a message-level request/response rendezvous.
- source URL: https://www.ti.com/lit/an/swra779/swra779.pdf ; https://onlinedocs.microchip.com/oxy/GUID-E774EBA8-C789-4B05-BFF5-B18812D2D7DC-en-US-17/GUID-73E2D7CF-1873-4234-99CA-7882E14EE8AA.html
- publisher: Texas Instruments; Microchip Technology
- pub_date: TI SWRA779, 2023-09; Microchip online manual, exact date not shown
- accessed: 2026-09-03
- confidence: high as a general UART flow-control principle; ESP32-S3's exact stop latency was not measured
- class: protocol/hardware pattern

### C6 — Serialized request/response needs an explicit pending state and timeout

- claim: The Modbus serial state machine allows a master to send a request only from Idle, moves it to Waiting for Reply with a response timeout, and does not allow a second request concurrently. It also permits retry after timeout/frame error. This is an authoritative precedent for one outstanding serial transaction and explicit timeout/retry rather than relying on incidental timing.
- source URL: https://www.modbus.org/file/secure/modbusoverserial.pdf
- publisher: Modbus Organization
- pub_date: 2006-12-20 (Specification and Implementation Guide V1.02)
- accessed: 2026-09-03
- confidence: high for the cited pattern; adaptation to this protocol is a design inference
- class: protocol pattern

### C7 — ACK-before-response requires correlation and duplicate handling

- claim: CoAP specifies that a request may receive an empty ACK followed later by a separate response; the ACK promises later action. It correlates acknowledgements with Message IDs, responses with client-generated tokens echoed by the server, retransmits on timeout, and requires duplicate detection/replay behavior. This supports an ACK/separate-response design only when identifiers and retry semantics accompany it.
- source URL: https://www.rfc-editor.org/info/rfc7252/
- publisher: IETF / RFC Editor
- pub_date: 2014-06 (RFC 7252)
- accessed: 2026-09-03
- confidence: high as a protocol-design precedent; it does not prove suitability on this serial link
- class: protocol pattern; reliability

### C8 — Why RTS/CTS plausibly failed to gate the immediate response

- claim: **Inference:** if FujiNet RTS was observed or configured but FujiNet CTS TX gating was absent/miswired, FujiNet transmission would not be held. If CTS gating was correctly enabled, the peer's automatic RTS would still normally permit the response while its RX FIFO had space, regardless of whether application code had posted the next read. Either case explains why hardware flow control need not close an application-level write-to-read turnaround window.
- source URL: https://raw.githubusercontent.com/espressif/esp-idf/v6.1/components/esp_hal_uart/esp32s3/include/hal/uart_ll.h ; https://www.ti.com/lit/an/swra779/swra779.pdf ; https://docs.espressif.com/projects/esp-idf/en/stable/esp32s3/api-reference/peripherals/uart.html
- publisher: Espressif Systems; Texas Instruments
- pub_date: ESP-IDF v6.1 snapshot, exact date not shown; TI SWRA779, 2023-09
- accessed: 2026-09-03
- confidence: medium until CTS/RTS and RX data are captured together on the actual hardware
- class: decision inference

## Remedy assessment

| Remedy | When it establishes readiness | Does it preserve response bytes? | Verdict |
|---|---|---|---|
| Pre-post asynchronous read | Before each request, unless a persistent receive stays queued for the session | Yes if the host driver writes incoming bytes into the pending request/buffer; host-specific behavior still needs verification | Best first experiment and likely minimal fix |
| Continuous full-duplex receive task/ring | Once per opened transport/session; receive remains active across writes | Yes, provided framing and overflow handling are correct | Most robust architecture; pair with one outstanding request or IDs |
| One-time ping/pong | Establishes only session liveness/capability | No: pong is itself an immediate response and says nothing about later per-request readiness | Useful negotiation/health check, not the turnaround fix |
| Ping/pong before every operation | Attempts per-request synchronization | Not by itself: pong can hit the same unarmed window | Inferior to an explicit client READY sent after receive is armed |
| Immediate server ACK, then result | Establishes request receipt, not client receive readiness | Not by itself: ACK can be the byte stream that is lost | Useful only after receive readiness is solved and with IDs/retry/dedup |
| Client READY/GO after request | Per request; server waits until READY tied to that request | Yes if the host arms receive before sending READY and FujiNet buffers the result | Robust fallback when continuous concurrent receive is impossible |
| Fixed response delay | Assumes readiness after elapsed time | Usually but not provably; timing can vary with load/driver/platform | Good diagnostic; compatibility fallback only, with measured margin and timeout |

## Idempotent handshake contract

An idempotent exchange should establish exactly one of two scopes:

1. **Session scope:** protocol version/capabilities and liveness for a newly opened transport. Repeating the same HELLO/session token returns the same negotiated result without creating another logical session. This happens once per open/reopen, but does not claim that the receiver is ready for every future response.
2. **Request scope:** a request ID identifies one logical operation; client READY names that request after receive is armed; duplicate REQUEST or READY is re-ACKed or replays the cached final response without executing side effects twice. The responder retains the request/result until final client ACK or a defined expiry. This must happen per request when each write recreates the failure window. [S6]

For an initial implementation, allow only one outstanding request per session, monotonically advance a small request ID, retain the last completed ID and response for duplicate replay, and make HELLO/READY/ACK side-effect-free. This recommendation is an adaptation of C6/C7, not a requirement of either source.

## Instrumentation needed to decide among causes

- Capture FujiNet TX, RX, CTS input, and RTS output from before the request write through the first response bytes. Capture on the MCU logic side and note whether an RS-232 transceiver inverts the observable connector level.
- Log the configured UART number, `uart_get_hw_flow_ctrl()` result, routed RTS/CTS GPIOs, inversion mask, CTS level before `uart_write_bytes()`, and RX FIFO/ring overflow events.
- On the host, compare three otherwise identical operations: synchronous write then read; read queued before write; continuous read task. If only the latter two work, that isolates the application/driver turnaround path better than adding a delay.
- Sweep a response delay only after the zero-delay/pre-post comparison. Treat the minimum passing delay as diagnostic data, not a protocol constant.

## Contradictions and cautions

- RTS/CTS names retain DTE/DCE history, and official vendor documents describe both classical DTE/DCE roles and the modern crossed ready-to-receive convention. The actionable truth for ESP32-S3 is the implemented direction: RTS is an output driven by RX flow state; CTS is an input that gates TX. Verify the peer's actual direction instead of relying on the names.
- Active-low logic is common in the cited UART guidance, while ESP32-S3 exposes independent CTS/RTS inversion controls and an external RS-232 level shifter can change observable voltage polarity. No universal “high means ready” or “low means ready” claim is made for the assembled link.
- A response delay and a protocol turnaround delay are not equivalent. The Modbus guide specifies response timeouts and a broadcast turnaround delay, but the retrieved material does not specify a universal minimum delay before a unicast responder may answer.
- CoAP is not proposed as the on-wire protocol. It is cited only as a standards-track example proving that ACK and separate response require identifiers, timers, and duplicate state to be reliable.

## Leads and negative searches

- Lead: verify the exact Amiga `serial.device` semantics for simultaneous CMD_READ/CMD_WRITE, receive buffering when no read I/O request is pending, and how seven-wire mode drives RTS. This was outside the source budget and remains the most important host-side evidence gap.
- Lead: identify the exact ESP-IDF version used by the target firmware, then inspect its tagged `uart_ll.h`, `uart_hal.c`, and SoC register definitions. The v6.1 findings are current, but compatibility claims require checking the deployed tag.
- Lead: inspect the board schematic/level shifter and confirm the physical cross-connection FujiNet RTS -> host CTS and host RTS -> FujiNet CTS.
- Negative search: no official Espressif source retrieved tied RTS assertion to whether application code is currently blocked in `uart_read_bytes()`; the retrieved source ties it to RX FIFO occupancy.
- Negative search: no authoritative source retrieved supports a fixed post-request delay as a generally safe way to prevent lost serial response bytes.
- Negative search: the retrieved material does not establish actual CTS/RTS initial voltage levels on this board after pin routing and external RS-232 conversion; those require schematic inspection and measurement.

## Sources

- **S1** Espressif Systems, *ESP-IDF Programming Guide v6.1 — ESP32-S3 UART*: https://docs.espressif.com/projects/esp-idf/en/stable/esp32s3/api-reference/peripherals/uart.html
- **S2** Espressif Systems, *ESP-IDF v6.1 ESP32-S3 UART low-level implementation (`uart_ll.h`)*: https://raw.githubusercontent.com/espressif/esp-idf/v6.1/components/esp_hal_uart/esp32s3/include/hal/uart_ll.h
- **S3** Espressif Systems, *ESP32-S3 UART register definitions (`uart_struct.h`, v6.1)*: https://raw.githubusercontent.com/espressif/esp-idf/v6.1/components/soc/esp32s3/register/soc/uart_struct.h
- **S4** Texas Instruments, *SimpleLink CC33xx Host Interfaces*, SWRA779, September 2023: https://www.ti.com/lit/an/swra779/swra779.pdf
- **S5** Modbus Organization, *MODBUS over Serial Line Specification and Implementation Guide V1.02*, 20 December 2006: https://www.modbus.org/file/secure/modbusoverserial.pdf
- **S6** IETF / RFC Editor, *RFC 7252: The Constrained Application Protocol (CoAP)*, June 2014: https://www.rfc-editor.org/info/rfc7252/

