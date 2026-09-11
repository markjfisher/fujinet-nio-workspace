---
title: '1-3 Make framer composition use raw FujiBus packets consistently'
type: refactor
created: '2026-09-11'
status: done
review_loop_iteration: 0
baseline_commit: 144af26593a4c17f6ec0b4e7a92420bb5e114795
owner_baseline_commit: abed047e42bed48e54821368035a00df887d1105
context:
  - '{project-root}/AGENTS.md'
  - '{project-root}/docs/agent-test-policy.md'
  - '{project-root}/repos/fujinet-nio/AGENTS.md'
---

<frozen-after-approval reason="approved Story 1.3; routine checkpoints disabled by execution-gates.md">

## Intent

**Problem:** FujiBusTransport still passes SLIP frames across a nominal raw framer boundary, preventing genuine native composition.

**Approach:** Use the accepted raw codec in the transport, and let SlipFramer own escaping and delimiters through shared helpers reused by legacy codec wrappers. Implements CAP-1/CAP-2 and approved Story 1.3. Story 1.2 is accepted at the owner baseline with 317 passing cases.

## Boundaries & Constraints

**Always:** Preserve valid serial wire bytes, request/response mapping and construction-time selection. Every IFramer consumes/produces raw opaque packet bytes. You are not alone: implementation worker owns all listed firmware files except `tests/test_atari_sio_fujibus_framer.cpp`, which the parent owns in parallel. Preserve others' changes. Parent owns story records, review and commits; coordinate final build after parent test is ready.

**Ask First:** Incompatible wire or service semantics beyond the approved framing separation.

**Never:** Change ITransport/service handlers, hardware profiles or physical ABI. Do not implement native packet boundaries yet or endorse the native stub's merge behavior. No library/driver edits, pushes or co-author trailers.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Raw versus SLIP request | Same independent literal request in raw test framer or serial channel | Same decoded params/payload; only serial adds SLIP | Existing decode failure |
| Response/status | Literal success and error packets | Framer sees raw fixture; serial channel sees exact SLIP fixture | Preserve status mapping |
| Fragmented serial | Every split including between escape bytes, repeated polls | No early delivery; complete raw packet once | Wait for delimiter |
| Serial separators | Prefix noise, consecutive ENDs, two frames | Preserve extraction ordering and discard behavior | No empty frame delivery |
| SLIP compatibility | Legacy wrapper and framer with same raw bytes | Shared escaping and existing malformed-escape behavior | Existing compatibility outcomes |
| Atari SIO composition | SIO W/R wrapping literal serial request/response | Actual transport semantics and exact SIO payload/padding/checksum preserved | Existing SIO validation |

</frozen-after-approval>

## Code Map

Paths are workspace-relative; investigator audited every IFramer implementation and codec caller.

- `repos/fujinet-nio/src/lib/fujibus_transport.cpp`: receive/receiveResponse call `fromRaw`; send uses `serializeRaw`. Mapping and public interface unchanged.
- `repos/fujinet-nio/src/lib/slip_framer.cpp`: retain delimiter scan and buffering; decode extracted frame to raw; encode outgoing raw packet once.
- `repos/fujinet-nio/include/fujinet/io/transport/{iframer,slip_framer}.h`: state raw boundary, remove inclusive-delimiter/verbatim claims.
- `repos/fujinet-nio/src/lib/fuji_bus_packet.cpp` and codec header: relocate existing private SLIP helpers to a shared pure helper (suggest `include/fujinet/io/protocol/slip_codec.h`), preserving exact algorithms and serial-wrapper validation. Avoid duplicate encoders.
- `repos/fujinet-nio/tests/test_slip_framer.cpp`: adapt expected output to raw, preserve extraction coverage; add literal binary split coverage.
- `repos/fujinet-nio/tests/test_fujibus_transport_framing.cpp`: SpyFramer sees raw, wire sees SLIP. Add raw test framer request/response parity against independent fixtures. Audit raw StubFramer in `test_iframer.cpp`; serial mapping tests remain unchanged.
- `repos/fujinet-nio/tests/test_atari_sio_fujibus_framer.cpp`: parent adds Channel test adapter composing actual SIO wrapper, SlipFramer and FujiBusTransport.
- `repos/fujinet-nio/src/lib/transport/atari_sio_fujibus_framer.cpp`: read-only; not an IFramer. ESP32 SIO profile selects FujiBusSlip and carries its serial bytes unchanged. Existing POSIX build includes this adapter and tests.
- `repos/fujinet-nio/src/lib/bootstrap.cpp`, native framer and Zorro profile: read-only composition audit; native stub replacement is 1.4.
- `repos/fujinet-nio/docs/protocol_reference.md`: update current C++ caller audit to raw transport/shared SLIP framing.

## Tasks & Acceptance

**Execution:**
- [x] Transport and framing headers/source — enforce raw boundary and share SLIP algorithms with serial wrappers.
- [x] Framer and transport tests — retain mapping coverage and test independent raw/SLIP fixtures plus fragmentation.
- [x] SIO composition regression — parent protects channel envelope compatibility.
- [x] Protocol reference — update actual caller/composition contract.
- [x] This story — record verification, full implementer/caller audit and review.

**Acceptance Criteria:**
- Given the same request/response, when passed through raw or SLIP framers, then semantics agree and exact fixture bytes show wrapping only on serial.
- Given fragmented input and consecutive delimiters, when polled, then extraction behavior is preserved and every IFramer has the same raw boundary without service edits.

## Spec Change Log

## Design Notes

Only SlipFramer and NativeFramer implement IFramer in production; AtariSioFujiBusFramer operates beneath Channel and must keep carrying SLIP bytes. Legacy serial codec API validation remains separate from pure shared SLIP helpers. Native stub boundary safety remains explicitly unresolved until 1.4. No new source is required if helpers are inline; regenerate source lists if adding production sources. Existing serial mapping tests should retain their wire expectations.

## Verification

From workspace root: `source scripts/env.sh && cd repos/fujinet-nio && ./build.sh -cp fujibus-pty-debug && ctest --test-dir build/fujibus-pty-debug -R '^fujinet-nio-tests$' --output-on-failure`.

The host gate includes SIO adapter and the new composition regression; no ESP32 production files change. Run `./scripts/update_cmake_sources.py` inside firmware if adding/removing production sources. Run both workspace and firmware `git diff --check`. Record all matrix rows and actual results; no library or guest changes need extra owner gates.

## Execution results

Required V-CXX command passed: 324/324 C++ cases, 6352/6352 assertions, zero skipped; build also passed 23 Python tests. Explicit host CTest passed 1/1. Logs: `/tmp/story-1-3-build.log` and `/tmp/story-1-3-tests.log`. Both diff checks passed. All matrix rows ran: raw typed/binary request parity, success/error response fixtures, every binary frame split, separators/noise/order, shared malformed escapes, and production SIO composition with independent literal envelope checksums. No production source file added (shared helper is inline).

Full audit: production IFramer implementations are SlipFramer and NativeFramer. Test StubFramer (`test_iframer.cpp`) already handles opaque raw bytes; SpyFramer and new RawFixtureFramer honor raw boundaries. FujiBusTransport is the only production codec caller and now uses raw APIs. AtariSioFujiBusFramer is a lower channel envelope carrying SLIP; its implementation/profile are unchanged and composition has host coverage. Bootstrap retains construction-time selection. Native stub boundary defects remain for 1.4, not validated by these tests.

## Review outcome

All three review layers completed. Fixed the overlapping blind/edge finding: escape-only malformed frames decode empty and are now consumed without a ready packet; a following valid frame survives. Added opaque non-FujiBus receive coverage and guarded legacy factory results in tests. Exact verification gate reran successfully. Remaining blind suggestions were optional performance/refactoring or broader coverage, not demonstrated defects. No blocking findings remain.

The transport now drops serialization exceeding 65535 raw bytes instead of emitting the legacy codec's invalid wrapped-length serial output. Valid serial wire behavior is unchanged; the legacy codec entry point retains its documented compatibility behavior. Story 1.3 is accepted for releasing 1.4, with native boundary safety still pending that story.

## Suggested Review Order

- Follow the transport's raw codec boundary.
  [fujibus_transport.cpp:46](../../../../repos/fujinet-nio/src/lib/fujibus_transport.cpp#L46)
- Inspect shared SLIP helpers and frame extraction.
  [slip_codec.h:29](../../../../repos/fujinet-nio/include/fujinet/io/protocol/slip_codec.h#L29)
  [slip_framer.cpp:63](../../../../repos/fujinet-nio/src/lib/slip_framer.cpp#L63)
- Review literal parity and serial fragmentation coverage.
  [test_fujibus_transport_framing.cpp:285](../../../../repos/fujinet-nio/tests/test_fujibus_transport_framing.cpp#L285)
  [test_slip_framer.cpp:196](../../../../repos/fujinet-nio/tests/test_slip_framer.cpp#L196)
- Verify the unchanged SIO wire envelope through actual transport composition.
  [test_atari_sio_fujibus_framer.cpp:65](../../../../repos/fujinet-nio/tests/test_atari_sio_fujibus_framer.cpp#L65)

Accepted firmware commit: `ee17409ef2fd4d78b25fc8835deeb0177788f0f0`.
