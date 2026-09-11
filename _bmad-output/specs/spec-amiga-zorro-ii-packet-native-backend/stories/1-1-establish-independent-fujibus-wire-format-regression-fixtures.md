---
title: '1-1 Establish independent FujiBus wire-format regression fixtures'
type: chore
created: '2026-09-11'
status: done
review_loop_iteration: 0
baseline_commit: 44ef9ab42899688442655fa34034ff59f6bf0a5e
owner_baseline_commit: 3755a407ddb58e06bba55b9b65346e7ea0c03d45
context:
  - '{project-root}/AGENTS.md'
  - '{project-root}/docs/agent-test-policy.md'
  - '{project-root}/repos/fujinet-nio/AGENTS.md'
---

<frozen-after-approval reason="approved Story 1.1; routine checkpoints disabled by execution-gates.md">

## Intent

**Problem:** Existing codec tests mostly round-trip production-generated packets, so shared serializer/parser errors could survive raw-codec separation.

**Approach:** Add independently specified literal raw/SLIP fixtures and characterization tests for production serialization, parsing and transport status mapping. This implements Story 1.1 and CAP-1 from the parent SPEC and approved epic companion. No prerequisites or physical hardware are required.

## Boundaries & Constraints

**Always:** Preserve current serial wire behavior. Expected packet bytes and decoded fields must be literal, independently reviewed expectations grounded in documented field rules and explicit checksum arithmetic. Keep existing serial tests unchanged. Report documentation discrepancies explicitly. Own only firmware test files plus workspace story/context records; you are not alone in the workspace, preserve others' changes.

**Ask First:** Production behavior changes, new wire rules, or an acceptance failure requiring scope expansion.

**Never:** Implement the raw API, change production code/library/service semantics, infer hardware readiness, or bless permissive malformed SLIP/trailing-data behavior as a new protocol contract. Commit completed story changes locally with an informative message and no co-author trailers. Never push.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Minimum packet | Literal six-byte raw header and SLIP pair, no params/payload | Exact serialization and independent decoded fields | None |
| Typed parameters | U8/U16/U32, descriptor continuation and indices across both descriptor tables | Exact lengths, little-endian values and preserved widths | None |
| Binary payload | Literal packet containing 00/C0/DB/FF | Exact escaped serial bytes and original decoded payload | None |
| Response mapping | Literal success and nonzero error responses | Production send bytes and receiveResponse status/payload match expectations | Existing status mapping |
| Corrupt checksum | Change checksum only in a valid literal frame | Parsing fails | Null result |
| Invalid structure | Literal too-small/too-large/swapped lengths and truncated descriptor/parameter with valid checksum | Parsing fails independently of checksum | Null result |

</frozen-after-approval>

## Code Map

All code paths below are workspace-relative.

- `repos/fujinet-nio/tests/test_fujipacket.cpp`: existing roundtrips and malformed framing tests; append literal codec assertions.
- `repos/fujinet-nio/tests/test_fujibus_transport_framing.cpp`: reusable LoopbackChannel, SpyFramer and feed helper; append independent request/response mapping cases.
- `repos/fujinet-nio/tests/fujibus_wire_fixtures.h`: new test-only shared literal fixtures, comments explaining layout/checksums; no production-generated oracle.
- `repos/fujinet-nio/src/lib/fuji_bus_packet.cpp`: read-only parse (~136), serialize (~238), fromSerialized (~327). Public API currently requires SLIP; raw literals can be checked against their literal SLIP partners with a minimal test-only escape mapper.
- `repos/fujinet-nio/include/fujinet/io/protocol/fuji_bus_packet.h`: typed constructor/addParamU8/U16/U32, setData, paramCount/param/tryParamU8. Re-serialization of literal parsed packets verifies descriptor widths.
- `repos/fujinet-nio/src/lib/fujibus_transport.cpp` and `include/fujinet/io/core/io_message.h`: read-only response U8 status param0 mapping and status enum.
- `repos/fujinet-nio/docs/protocol_reference.md`: read-only field/checksum reference, sections 4–8. Section 11 worked examples contain arithmetic/length discrepancies; see Design Notes.
- `repos/fujinet-nio/tests/CMakeLists.txt`: existing automatic test source discovery; no production source list updates needed.

## Tasks & Acceptance

**Execution:**
- [x] `repos/fujinet-nio/tests/fujibus_wire_fixtures.h` — add reviewed literal pairs and malformed inputs with annotated checksum arithmetic.
- [x] `repos/fujinet-nio/tests/test_fujipacket.cpp` — test each codec matrix row using independent bytes and field expectations; retain all existing cases.
- [x] `repos/fujinet-nio/tests/test_fujibus_transport_framing.cpp` — verify literal receive and success/error response mapping through real transport/framer.
- [x] This story — record exact verification results, matrix coverage, independent fixture review and documentation discrepancies.

**Acceptance Criteria:**
- Given independently reviewed fixtures, when production serialization and parsing run, then bytes and decoded fields match literal expectations that are not generated by the production codec.
- Given checksum corruption and inconsistent packet lengths, when parsed, then rejection occurs and the existing serial framing tests still pass unchanged.
- Given documentation/implementation differences, when completing this story, then report them explicitly without changing wire rules.

## Spec Change Log

- 2026-09-11: User authorized committing Story 1.1 and instructed that completed stories be committed without co-author trailers and never pushed. Updated the execution constraint accordingly; implementation scope and acceptance remain unchanged.

## Design Notes

No public raw entry point exists yet; these tests characterize serial compatibility and preserve independent raw partners for Story 1.2. Fixtures must cover checksum carry folding, not just a low-byte sum. Malformed structure vectors need valid literal checksums so checksum rejection cannot mask absent structure validation.

Protocol reference section 11: request checksum 73 should be 03; the response declares length 0C for 11 raw bytes, and checksum 71 should be F3 with that declared length (F2 if length is corrected to 0B). Its echo-parameter example differs from production transport's U8 status param0 convention, omitted in section 10. Record these as discrepancies; do not use the worked examples as golden vectors. Ignored malformed SLIP escapes and post-frame trailing bytes are deferred parser questions, not new acceptance rules.

## Verification

Source the shared environment before building/testing. Exact firmware-owner gate from workspace root:

`source scripts/env.sh && cd repos/fujinet-nio && ./build.sh -cp fujibus-pty-debug && ctest --test-dir build/fujibus-pty-debug -R '^fujinet-nio-tests$' --output-on-failure`

Expected: build succeeds and the registered host test suite passes, including unchanged serial tests and every new matrix case. Use focused doctest filters if needed during development. Workspace records: `git diff --check`; firmware: `git -C repos/fujinet-nio diff --check`. Independently audit literal field offsets, lengths, checksum arithmetic and SLIP pairs during review. No library/driver/guest changes, hence no additional owner gates.


### Story 1.1 execution results — 2026-09-11

- Added ten independent literal raw/SLIP pairs: minimum, all typed descriptor
  indices, binary payload, success response, error response, and five invalid
  structures. Each checksum is annotated with arithmetic; no production codec
  generates expected bytes. Typed descriptors cover every index 0–7 across the
  fixtures, including continuation, all parameter widths and little-endian values.
- Appended six codec tests and two transport tests. Matrix coverage: minimum
  serialization/parse; typed serialization/parse and preserved widths; binary
  escaping/payload and checksum carry; checksum-only corruption; checksum-valid
  small/large/swapped lengths and descriptor/parameter truncation; literal request
  mapping and literal success/IOError response send/receive mapping through the
  real SlipFramer (SpyFramer delegates to it). All existing cases are unchanged.
- Independent parent-agent fixture audit passed for all ten pairs: header offsets,
  lengths, whole-buffer sums with repeated end-around carry, literal SLIP
  substitutions, typed descriptor counts/offsets and little-endian parameter values
  were checked separately from production code. Typed checksum is 0x792 folded
  to 0x99; binary payload checksum is 0x2AB folded to 0xAD.
- Ran `source scripts/env.sh && cd repos/fujinet-nio && ./build.sh -cp
  fujibus-pty-debug && ctest --test-dir build/fujibus-pty-debug -R
  '^fujinet-nio-tests$' --output-on-failure`. Clean compilation succeeded.
  `build.sh` itself automatically ran CTest: all new tests passed, but nine existing
  modem/TCP/socket cases were blocked by sandbox socket permissions (299/308 host
  cases passed; its 23 Python tests also passed). The chained explicit CTest was
  consequently not reached on that first invocation.
- Reran `source scripts/env.sh && cd repos/fujinet-nio && ctest --test-dir
  build/fujibus-pty-debug -R '^fujinet-nio-tests$' --output-on-failure` with approved
  escalation for local sockets: **passed, 1/1 registered host suite, 0.20 seconds**.
- Documentation discrepancies confirmed, without changing wire rules: protocol
  reference §11 request checksum 0x73 should be 0x03 (sum 0x3FF); its response
  declares 0x0C for 11 raw bytes and checksum 0x71 should be 0xF3 for that declared
  length (sum 0x3F0), or 0xF2 with corrected length 0x0B (sum 0x3EF). Its echo-param
  response also differs from production U8 status-param0 mapping, omitted in §10.
- No production, library, driver or guest changes; no raw API or malformed
  SLIP/trailing-data acceptance rules introduced. No remote operations.
- `git diff --check` and `git -C repos/fujinet-nio diff --check`: passed.

## Review outcome

All three review layers completed. No blocking defect or verification gap remained after scope triage. The host log confirms 308/308 cases and 5,975/5,975 assertions passed, with zero skipped. All matrix rows are covered by executed tests. Production files and pre-existing tests remain unchanged. User authorized local commits after review; the firmware changes and workspace completion record are committed separately, without pushing.

## Suggested Review Order

- Start with independent field layouts, literal bytes and annotated checksum arithmetic.
  [fujibus_wire_fixtures.h:3](../../../../repos/fujinet-nio/tests/fujibus_wire_fixtures.h#L3)

- Check fixture pairing, typed serialization, decoded fields and structural rejection.
  [test_fujipacket.cpp:302](../../../../repos/fujinet-nio/tests/test_fujipacket.cpp#L302)

- Follow literal requests and status responses through production transport and framing.
  [test_fujibus_transport_framing.cpp:228](../../../../repos/fujinet-nio/tests/test_fujibus_transport_framing.cpp#L228)
