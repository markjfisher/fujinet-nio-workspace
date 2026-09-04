---
title: 'Retry idempotent Amiga DiskDevice sector exchanges after RS-232 recovery'
type: 'bugfix'
created: '2026-09-04'
status: 'draft'
review_loop_iteration: 0
context:
  - '{project-root}/docs/agent-test-policy.md'
  - '{project-root}/backlog/amiga-rs232-38400-reliability.md'
  - '{project-root}/repos/fujinet-nio-driver/docs/amiga/rs232-38400-pacing-evidence.md'
  - '{project-root}/repos/fujinet-nio-driver/docs/amiga/Serial-IO-Interface.md'
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** At 38,400 baud, a residual Paula receive overrun makes an otherwise recoverable DiskDevice sector exchange fail after the broker drains RX and closes `serial.device`. The failed packet is safely unpublished, but one missed byte can still fail an AmigaDOS read/write and leave the volume requiring human intervention.

**Approach:** At the Amiga NIO DiskDevice raw-exchange boundary, replay only complete, structurally valid encoded DiskService READ_SECTOR and WRITE_SECTOR packets after transport-level `FN_ERR_TRANSPORT` or `FN_ERR_TIMEOUT`. Retry the identical packet at most twice after the initial attempt; each replay naturally lazy-reopens the broker backend after its existing drain-and-close recovery.

## Boundaries & Constraints

**Always:** Require the complete encoded sector-request shape before classifying a packet as retryable: DiskService device; READ_SECTOR `0x03` at exactly 14 bytes or WRITE_SECTOR `0x04` at exactly 526 bytes; matching encoded total length; simple descriptor; valid checksum; Disk protocol version; valid DiskDevice slot; and an encoded capacity/body length of exactly 512 bytes. Reset `*response_length` and the per-attempt response length before every attempt. Retry only the two transport results, preserve the last result after exhaustion, and send byte-identical request data, especially the same slot/LBA/full 512-byte WRITE body. Only a final successful attempt may publish its response length; failed attempts must leave the outward response length at zero and must not leak response state forward. Preserve fail-closed behavior: an unsuccessful exchange publishes no response and can never advance `io_Actual` for that sector.

**Ask First:** Changing the two-retry limit; adding delay/backoff; changing broker drain/reopen, packet format, public APIs, or DiskDevice trace structures; broadening retry to any other command or error.

**Never:** Retry Mount, Info, Flush, Unmount, ClearChanged, Inspect, network/application calls, malformed packets, or any other non-idempotent FujiBus command. Do not add request IDs, READY/GO, seven-wire flow control, 57,600 baud, a custom `serial.device`, or reopen DiskDevice Phase 2 or broker Stage 3/4.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Recovered READ | Disk READ; first raw exchange returns transport/timeout, later attempt succeeds with a full sector | Identical request replayed; typed read returns 512 bytes; DiskDevice completes `io_Error=0`, full `io_Actual` | Broker recovery completes before replay |
| Recovered WRITE | Disk WRITE; first raw exchange returns transport/timeout, later attempt succeeds | Identical slot/LBA/body replayed; DiskDevice completes `io_Error=0`, full `io_Actual` | Same-sector ADF write is replay-safe |
| Persistent link fault | All three attempts return transport/timeout | Exactly three attempts; final error is preserved | Response length remains zero; no short success |
| Non-retryable result | READ/WRITE exchange returns any other error | One attempt, original result preserved | No replay |
| Excluded command | Any non-sector command returns transport/timeout | One attempt, original result preserved | No replay |
| Invalid/truncated packet | Header-valid but truncated WRITE, wrong exact length, malformed header/payload fields, or invalid checksum | One attempt only | Incomplete sector packet is not retryable |

</frozen-after-approval>

## Code Map

- `repos/fujinet-nio-driver/amiga/channels/rs232/fujinet_nio_client.c:4` -- raw `nio_exchange()` sees transport errors before DiskService response-status parsing; this is the narrow safe retry boundary.
- `repos/fujinet-nio-driver/amiga/nio.device/fujinet_nio_device.c:129` -- read-only invariant: broker drains and closes on transport/timeout; the following EXCHANGE lazy-reopens.
- `repos/fujinet-nio-driver/amiga/common/fujinet_disk_driver.c:206` -- read-only invariant: per-sector READ/WRITE advance `actual` only after complete success; READ rejects non-512-byte responses.
- `repos/fujinet-nio-driver/amiga/tests/test_fujinet_nio_client_link.c:1` -- current adapter link smoke test; retain it and add a focused transport-stub retry harness.
- `repos/fujinet-nio-driver/amiga/tests/Makefile:1` -- register and run the focused native retry test.
- `repos/fujinet-nio-driver/amiga/channels/rs232/README.md:1` -- document why retry is limited to raw DiskService sector exchanges.
- `repos/fujinet-nio-driver/docs/amiga/Serial-IO-Interface.md:1` -- in-tree AHRM 3rd Edition reference: Paula owns UART and overrun means the prior received character was not serviced in time.

## Tasks & Acceptance

**Execution:**
- [ ] `amiga/channels/rs232/fujinet_nio_client.c` -- add private packet classification and a three-total-attempt raw exchange loop for DiskService READ_SECTOR/WRITE_SECTOR only.
- [ ] `amiga/tests/test_fujinet_nio_client_retry.c`, `amiga/tests/Makefile` -- add deterministic scripted transport tests for recovery, exhaustion, byte-identical replay, response-length isolation, excluded commands, malformed/truncated sector packets, and non-retryable errors.
- [ ] `amiga/channels/rs232/README.md`, `backlog/amiga-rs232-38400-reliability.md` -- record the narrow policy and check off implementation only after automated verification; leave physical hardware proof open until observed.

**Acceptance Criteria:**
- Given the broker has returned a transport/timeout fault and completed drain-and-close, when a DiskDevice sector READ or same-sector WRITE is retried successfully, then the request completes with `io_Error=0` and full `io_Actual`.
- Given all bounded attempts fail, when DiskDevice completes the request, then it reports a persistent error and never a short successful READ.
- Given any non-sector FujiBus command, when transport/timeout occurs, then it is not replayed.
- Given real Amiga hardware at 38,400 baud, when an induced or observed `cause=7` occurs during CMD_READ/CMD_WRITE, then evidence shows either full successful completion after retry or bounded persistent failure; this manual criterion remains open until hardware results are supplied.

## Spec Change Log

## Design Notes

Retrying inside `nio_read_sector()`/`nio_write()` would conflate a transport timeout with a valid DiskService response whose remote status is `FN_ERR_TIMEOUT`. The raw `nio_exchange()` callback sees only broker/transport results, so classification there keeps remote application errors single-attempt. Two retries after the first request cap the normal 5-second timeout path at three attempts without changing broker recovery.

WRITE_SECTOR is retry-safe here specifically because every replay is byte-identical for the same slot, LBA, and complete 512-byte sector body. This covers the case where the ESP committed the sector but the Amiga lost the response; it does not generalize idempotency to any other FujiBus command. Each attempt uses freshly cleared response-length state, and the adapter publishes a response length only from the attempt that returns `FN_OK`.

## Verification

**Commands:**
- `source scripts/env.sh && make -C repos/fujinet-nio-driver/amiga/tests build/test_fujinet_nio_client_retry && repos/fujinet-nio-driver/amiga/tests/build/test_fujinet_nio_client_retry` -- focused retry matrix passes.
- `source scripts/env.sh && make -C repos/fujinet-nio-driver/amiga tests` -- all Amiga driver native contracts pass.
- `source scripts/env.sh && make -C repos/fujinet-nio-driver/amiga native` -- Amiga binaries compile with the configured toolchain.
- `source scripts/env.sh && uv run pytest --run-amiga --amiga-env wb32 --amiga-machine a1200-030 integration-tests/amiberry/test_diskdevice_adf.py::test_standard_adf_mount_info_read_dir_and_type` -- one guest node confirms normal multi-sector READ and writable ADF behavior.

**Manual checks (hardware):**
- At 38,400 baud with 16-byte/2,000-us ESP pacing, capture a `cause=7` during CMD_READ and CMD_WRITE and record full success after retry or bounded final error, never success with short `io_Actual`.
