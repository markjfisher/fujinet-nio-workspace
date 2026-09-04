# Current-code comparison digest — round 1

Decision served: explain why short FujiNet disk/file/host commands can fail at 38,400 while the long-running network application is reliable, and identify experiments that discriminate the remaining causes.

Repository state inspected 2026-09-03. Claims below point to immutable repository commits where possible. The handoff is treated as an observation record, not as an authority for hardware behavior.

## Findings

### C1 — “disk side” and network traffic use the same physical backend

- **claim:** Amiga `fn_raw_call()` sends every host, file, appstore, and network service operation through `fn_transport_exchange()`. The Amiga transport submits `FUJINET_NIO_CMD_EXCHANGE` to the same resident `fujinet-nio.device`; the device serializes requests through one `backend_exchange()` function. A persistent TCP handle is an ESP-side network-session lifetime, not a persistent byte stream between the Amiga application and the ESP. Each `fn_write()` and `fn_read()` remains a separate FujiBus request/response transaction over the same serial backend used by FHOST/FLS/FIN.
- **sources:** https://github.com/markjfisher/fujinet-nio-lib/blob/a5406c8bc71484a68f1de4d6117b90345f216751/src/common/fn_raw.c ; https://github.com/markjfisher/fujinet-nio-lib/blob/a5406c8bc71484a68f1de4d6117b90345f216751/src/platform/amiga/fn_transport.c ; https://github.com/markjfisher/fujinet-nio-driver/blob/44bea7fd44434f75a8f2b2622fc075611d1f5e0a/amiga/nio.device/fujinet_nio_device.c
- **publisher:** current project repositories
- **pub_date:** commits current on 2026-09-03
- **accessed:** 2026-09-03
- **confidence:** high
- **class:** current implementation / architecture

### C2 — the transport already remains open across application closes

- **claim:** Closing an application's `fujinet-nio.device` request decrements `OpenCnt` but explicitly does not close the serial backend unless expunge is pending. Successful exchanges therefore retain the same open `serial.device` backend across ordinary short-lived CLI programs. A timeout closes the backend; an overrun-class `FN_ERR_TRANSPORT` takes the soft-recovery path and retains it when recognized.
- **source:** https://github.com/markjfisher/fujinet-nio-driver/blob/44bea7fd44434f75a8f2b2622fc075611d1f5e0a/amiga/nio.device/fujinet_nio_device.c
- **publisher:** current project repository
- **pub_date:** commit current on 2026-09-03
- **accessed:** 2026-09-03
- **confidence:** high
- **class:** current implementation / lifecycle

### C3 — the handoff's “Current code state” is stale in one material respect

- **claim:** Contrary to “No session_flush overrun drain,” current `session_flush()` still queries `io_Status` and performs a sacrificial one-byte `CMD_READ` when `IO_STATF_OVERRUN` is set. The current source also still contains comments assigning the UART and overrun to the CIA and asserting a TX→RX transition; primary Amiga documentation contradicts those comments.
- **source:** https://github.com/markjfisher/fujinet-nio-driver/blob/44bea7fd44434f75a8f2b2622fc075611d1f5e0a/amiga/nio.device/fujinet_nio_serial_backend.c
- **publisher:** current project repository
- **pub_date:** commit current on 2026-09-03
- **accessed:** 2026-09-03
- **confidence:** high
- **class:** current implementation / documentation defect

### C4 — the prior RTS/CTS test did not satisfy the Amiga API contract

- **claim:** The experiment added `SERF_7WIRE` only after `OpenDevice()`, immediately before `SDCMD_SETPARAMS`. Commodore documentation requires `SERF_7WIRE` to be set before `OpenDevice()`. Therefore that experiment cannot prove Amiga seven-wire handshaking was enabled; the corrected ESP pin routing by itself does not validate end-to-end RTS/CTS behavior.
- **sources:** https://github.com/markjfisher/fujinet-nio-driver/commit/241cb4f1bb47b3519f744ad4bc8d287e3837e092 ; https://wiki.amigaos.net/wiki/Serial_Device
- **publisher:** project repository; Commodore RKM material mirrored by AmigaOS Documentation Wiki
- **pub_date:** project commit 2026-08-28; wiki revision 2025-01-26
- **accessed:** 2026-09-03
- **confidence:** high
- **class:** integration validity

### C5 — the proving application is not an equivalent cold disk/file test

- **claim:** `fujinet-nio-exchange` calls `try_open_serial()` before opening the broker; that function opens and closes `serial.device`, so the diagnostic changes precisely the device lifecycle it is meant to observe. Its first FujiBus request is a small clock request. Its file-list request (“MARKER”) is executed only after multiple clock exchanges, a forced timeout/recovery cycle, and concurrent requests. Thus `PASS isolated-exchange` does not show that a cold first FLS/FHOST-like response is reliable.
- **source:** https://github.com/markjfisher/fujinet-nio-driver/blob/44bea7fd44434f75a8f2b2622fc075611d1f5e0a/amiga/tools/fujinet-nio-exchange.c
- **publisher:** current project repository
- **pub_date:** commit current on 2026-09-03
- **accessed:** 2026-09-03
- **confidence:** high
- **class:** verification gap

### C6 — response shape and service timing remain the strongest code-level difference

- **claim:** FLS explicitly permits a 420-byte service payload, whereas network writes generally receive short acknowledgement/status responses and the Bounce World polling request/response size depends on the small per-frame state packet. Every operation uses the same serial exchange sequence, so current code provides no disk-specific receive path that could explain the failures. The observed ordering of failure rates (FLS highest, FHOST intermediate, FIN lowest) is consistent with response-size/burst-exposure or service-timing differences, but the exact wire lengths for the user's trials were not recorded, so this remains a hypothesis.
- **sources:** https://github.com/markjfisher/nio-core-apps/blob/542af6cc28f737ba1819a6e3b5a98fab474ecbc6/src/common/fnsvc.c ; https://github.com/markjfisher/fujinet-nio-lib/blob/a5406c8bc71484a68f1de4d6117b90345f216751/src/common/fn_rw.c ; https://github.com/markjfisher/bounce-world-client-nio/blob/c1b56800d83e5b1b33bce47dad88d8c6be5913e9/src/common/connection.c
- **publisher:** current project repositories
- **pub_date:** commits current on 2026-09-03
- **accessed:** 2026-09-03
- **confidence:** medium
- **class:** causal inference / response profile

### C7 — a pre-response delay does not test receive burst capacity

- **claim:** ESP `tx_gap_us` is applied once immediately before `uart_write_bytes(buffer, len)`. It delays the beginning of the entire response but does not add inter-byte or inter-chunk spacing. Its failure at one second therefore argues against a simple “Amiga needs time after sending” explanation, but it does not test the documented Paula failure mechanism: servicing every received character within one character time during the subsequent burst.
- **source:** https://github.com/markjfisher/fujinet-nio/blob/32f54d15f25c37bafddcf5fd3f2c22d02e8a2a82/src/platform/esp32/uart_channel.cpp
- **publisher:** current project repository
- **pub_date:** commit current on 2026-09-03
- **accessed:** 2026-09-03
- **confidence:** high
- **class:** experiment interpretation

### C8 — posting a read first does not keep the Amiga UART “in RX mode”

- **claim:** Current code uses one `IOExtSer` for synchronous write, query, and read. A separate asynchronous read request would be required for overlap and is a valid controlled experiment. However, official documentation says `serial.device` buffers incoming characters after open even without a read pending, and Paula's transmit and receive paths are independent. Consequently a pre-posted read cannot fix a nonexistent TX→RX mode transition. It might still change driver scheduling/delivery latency; that narrower claim requires real-hardware testing.
- **sources:** https://wiki.amigaos.net/wiki/Serial_Device ; https://www.ikod.se/wp-content/uploads/2020/08/Amiga_Hardware_Reference_Manual_3rd_Edition.pdf ; https://github.com/markjfisher/fujinet-nio-driver/blob/44bea7fd44434f75a8f2b2622fc075611d1f5e0a/amiga/nio.device/fujinet_nio_serial_backend.c
- **publisher:** Commodore manuals / current project repository
- **pub_date:** manuals 1991; commit current on 2026-09-03
- **accessed:** 2026-09-03
- **confidence:** high for hardware/API behavior; medium for possible scheduling benefit
- **class:** architecture assessment

### C9 — a one-time ping can only be a sacrificial warm-up, not readiness handshaking

- **claim:** If and only if failures are confined to the first response after a backend open/reconfiguration, an idempotent cold-start ping can deliberately absorb that failure and be retried before real work. It would be required once per physical backend open/reopen, not once per application or request. If failures continue on a warm backend, a ping before each request adds another vulnerable response and provides no protection. A true per-request workaround would need a host READY/GO phase or replay-safe request IDs; arbitrary FIN/FHOST operations cannot safely be blindly retried because some mutate state.
- **sources:** current lifecycle in `fujinet_nio_device.c`; https://www.rfc-editor.org/info/rfc7252/ (separate responses, identifiers, retransmission and duplicate handling as protocol precedent)
- **publisher:** current project repository; IETF
- **pub_date:** current commit 2026-09-03; RFC 7252 June 2014
- **accessed:** 2026-09-03
- **confidence:** high as protocol/lifecycle reasoning; cold-only premise remains unverified
- **class:** workaround assessment

## Highest-value experiment sequence

1. Make the diagnostic faithful: remove the pre-test `try_open_serial()` open/close side effect; allow the first request to be clock, host-get, file-list with controlled payload/response sizes, or a synthetic N-byte echo; print request and response wire lengths and whether the backend was newly opened/recovered.
2. Run warm/cold matrices at 9,600, 19,200, 38,400, and 57,600. Explicitly expunge/reload or baud-reconfigure only for the cold case. Run at least 100 exchanges per cell and record overrun index, response size, and task/system load.
3. Add configurable **inter-byte or inter-chunk** response pacing on ESP. Sweep spacing while retaining 38,400 physical baud. This directly tests receive-service starvation; the existing one-time `tx_gap_us` does not.
4. Validate seven-wire correctly: set `SERF_7WIRE` before `OpenDevice()` and retain it in set-parameters; enable ESP CTS/RTS; capture TXD/RXD/RTS/CTS on a logic analyzer. Treat line names as directions at each UART, not merely connector labels.
5. Only then compare the present query-poll read with a separate, pre-posted one-byte async read plus a separate write request. If pacing changes the failure threshold but pre-posting does not, receive ISR service time—not application read timing—is isolated.

## Stop condition

Coverage reached for round 1: current code, official API behavior, and hardware behavior together invalidate the handoff's named mechanism and expose two invalid/mismatched experiments. The remaining unknowns (cold versus warm scope, response-length curve, inter-byte pacing threshold, and actual RTS/CTS levels) require real-hardware measurements rather than another web round.
