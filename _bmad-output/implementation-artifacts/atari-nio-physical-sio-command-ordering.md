---
title: 'Atari physical SIO command ordering'
type: 'bugfix'
created: '2026-10-25'
status: 'in-progress'
baseline_commit: '0a9a1db9fdf80c24bf8de65deb1038b2eb60dca3'
review_loop_iteration: 0
context: ['docs/agent-test-policy.md', '_bmad-output/implementation-artifacts/atari-nio-physical-sio-epic-3-readiness.md']
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

Correct physical ESP32 SIO COMMAND/UART association and unowned-device silence using the existing ingress and router.

## Boundaries & Constraints

**Always:** Bounded, level-aware handling of assertion, five-byte command frame and release; correctly handle buffered bytes, rapid edges, partial frames, subsequent write data and repeated commands. ISR must not block. No response for IDs outside $31–$38 and $7F; preserve owned-ID errors and production DiskService and $7F service semantics. Host tests must exercise the actual capture/ordering assumptions and fail safely on overflow or ambiguous ordering. Build official original-ESP32 16 MB profile and run focused regressions. Record limits and physical evidence separately.

**Never:** Speculative reply delays, PROC signaling, physical RESET detection, new hardware features, a new SIO HAL, DiskService rewrite, or native wire protocol change.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|---|---|---|---|
| Complete command | assertion, five bytes, release | Dispatch exactly once after release | No premature response |
| Partial or overflow | interrupted frame, queue overflow or unresolvable order | no fabricated command; subsequent valid transaction recovers | fail closed |
| Write data | owned write command, release, data/checksum | data goes to pending write phase | abort safely on new assertion |
| Other device | valid or malformed command for unowned device | no output | preserve subsequent transactions |
| Owned error | unsupported command for owned ID | established NAK/error | no cross-device response |
| Repeated commands | multiple edges and frames pending | correct order or explicitly detected ambiguous capture | no misclassification |

</frozen-after-approval>

## Code Map

- `repos/fujinet-nio/src/platform/esp32/atari_sio_ingress.cpp` -- physical GPIO, UART and ingress integration.
- `repos/fujinet-nio/include/fujinet/io/atari_sio_transaction_boundary.h` -- current lossy edge flag.
- `repos/fujinet-nio/src/lib/atari_sio_ingress_router.cpp` -- disk/NIO dispatch and data phases; unowned addresses currently NAK.
- `repos/fujinet-nio/src/platform/esp32/uart_channel.cpp` -- independently buffered ESP-IDF UART; edge level queues alone do not order buffered bytes.
- `repos/fujinet-nio/tests/` -- existing router, frontend and transaction boundary tests.
- `_bmad-output/implementation-artifacts/atari-nio-physical-sio-epic-3-readiness.md` -- update with results and residual physical uncertainty.

## Tasks & Acceptance

**Execution:**
- [ ] Implement bounded physical capture/transaction handling and isolate unowned IDs in the existing router.
- [ ] Add host-executable behavioral tests including capture integration, overflow and independently buffered bytes; run focused regressions and official ESP32 profile build.
- [ ] Update Epic 3 evidence with exact checks and remaining hardware validation.

**Acceptance Criteria:**
- Given ordered physical events, when complete or interrupted transactions occur, then no response precedes release or arises from unowned traffic, and subsequent writes and commands remain correctly classified.
- Given event queue saturation or genuinely ambiguous ordering, when ingress resumes, then it fails closed and recovers on a fresh transaction without inventing bytes or commands.

## Verification

Source the workspace environment before builds. Run the focused Atari host tests, `ctest` for the relevant POSIX build, and `cd repos/fujinet-nio && ./build.sh -b` for the configured official 16 MB Atari profile. Record exact commands and outcomes here.

**Partial verification (2026-10-25):** After `source scripts/env.sh`,
`cd repos/fujinet-nio && ./build.sh -cp fujibus-pty-debug` passed;
`build/fujibus-pty-debug/tests/fujinet-nio-tests --test-case='Atari SIO*'`
passed 9 cases / 146 assertions; `ctest --test-dir build/fujibus-pty-debug
--output-on-failure` passed 3/3; `./build.sh -b` passed for the configured
original-ESP32 16 MB Atari profile. Router-only tests cover valid and malformed
unowned frames, owned NAK, and subsequent owned command. Physical capture,
independent UART buffering, unowned write-data spoofing, and recovery are not
yet fixed or tested; the acceptance criteria remain open.

**Legacy-based implementation (2026-10-25):** Firmware commit
`25d8d87e4f1f363957861a9e943a5d402255e383` adds release-gated capture,
bounded recovery, progress-based write timeout and focused state-machine
coverage. After `source scripts/env.sh`, in `repos/fujinet-nio`,
`./build.sh -cp fujibus-pty-debug` passed; the focused
`build/fujibus-pty-debug/tests/fujinet-nio-tests --test-case='Atari SIO*'`
passed 17 cases / 175 assertions; `ctest --test-dir build/fujibus-pty-debug
--output-on-failure` passed 3/3; `./build.sh -b` passed for the configured
classic ESP32 16 MB Atari profile. The acceptance criterion concerning *all*
ambiguous ordering remains unproven: neither GPIO coalescing nor the UART's
delayed hardware bytes are fully observable. The readiness record describes
the assumptions and the physical measurement required.

## Spec Change Log

## Current implementation direction

The user requires the existing working Atari SIO implementation in
`/home/markf/dev/atari/fujinet-firmware` as the primary reference. Study its
`lib/bus/sio/sio.cpp`, `sio.h`, `lib/hardware/ESP32UARTChannel.cpp` and
initialization paths before designing the fix. Legacy polls active-low COMMAND,
reads five bytes using a timeout, waits for release, then routes; it handles
write data inside the selected transaction and discards idle stray input.
Adapt this proven sequence where practical; do not introduce a competing
event-queue architecture without demonstrating why it is needed. Bound any
recovery and explicitly document timing assumptions and physical limitations.
Do not change reply timing, PROC, reset or service protocols. Own the firmware
ingress and its focused host tests; update this spec and the Atari readiness
record with verification and legacy comparisons. Other work may occur in the
workspace: do not revert others' changes; accommodate them.
