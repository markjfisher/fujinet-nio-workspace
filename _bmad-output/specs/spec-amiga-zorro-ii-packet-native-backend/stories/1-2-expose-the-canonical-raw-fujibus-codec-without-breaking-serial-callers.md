---
title: '1-2 Expose the canonical raw FujiBus codec without breaking serial callers'
type: refactor
created: '2026-09-11'
status: done
review_loop_iteration: 0
baseline_commit: 6a08a5c9ae498eb4bfe992de5ebad6f783455ff7
owner_baseline_commit: 46324942a7eed01871b9c1ed21b62f14a90916a1
context:
  - '{project-root}/AGENTS.md'
  - '{project-root}/docs/agent-test-policy.md'
  - '{project-root}/repos/fujinet-nio/AGENTS.md'
---

<frozen-after-approval reason="approved Story 1.2; routine checkpoints disabled by execution-gates.md">

## Intent

**Problem:** The C++ FujiBus codec requires SLIP and copies native header layout, preventing an explicit portable raw-packet path.

**Approach:** Expose raw encoding/decoding while preserving serial entry points and established wire outcomes. Implements CAP-1 and approved Story 1.2 in the parent SPEC/epic companion. Prerequisite 1.1 is done, with independent literal fixtures committed at the owner baseline.

## Boundaries & Constraints

**Always:** Preserve six-byte header, little-endian fields, descriptors, checksum, payload and status semantics. Raw versus serial is selected explicitly, never sniffed from bytes. You own codec header/source, codec tests and protocol reference only. You are not alone in the codebase; preserve others' edits. Parent owns story records, review and commits.

**Ask First:** Any incompatible protocol validity rule or service/API scope expansion that cannot preserve compatibility.

**Never:** Change ITransport, framers, services, C/Python encoders, the library or driver. No hardware claims, runtime fallback, unrelated parser redesign, pushes or co-author trailers.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Literal vectors | Minimum, typed, binary and status fixtures | Exact raw bytes and decoded fields; serial bytes unchanged | None |
| Raw framing choice | Payload/header contains C0/DB or SLIP-wrapped input | Raw treats bytes literally; never automatically unwraps | Invalid raw length/checksum rejected |
| Raw structure | Empty/short header, checksum corruption, length mismatch, descriptor/parameter truncation | Reject without partial public result | Null factory result |
| Raw trailing data | Extra bytes outside length versus payload within length | Outside rejected; inside accepted with valid checksum | Null on mismatch |
| Descriptor compatibility | Reserved bits, zero-count and continued descriptors | Existing decoding semantics retained | Truncated continuation rejected |
| Serial compatibility | Prefix noise, consecutive/end delimiters, malformed escapes, trailing frame data | Existing serial outcomes retained and characterized | Existing null/result behavior |
| Size boundary | Raw total 65535 and 65536 bytes | Exact-limit succeeds; raw oversize returns empty; legacy serial outcome retained | Explicit documented raw failure |

</frozen-after-approval>

## Code Map

Paths are workspace-relative. Investigation used production code and exhaustive caller audit.

- `repos/fujinet-nio/include/fujinet/io/protocol/fuji_bus_packet.h`: add public `serializeRaw()` / `fromRaw()`; serial names stay compatible.
- `repos/fujinet-nio/src/lib/fuji_bus_packet.cpp`: parse (~136), serialize (~238), factory (~327). Extract common raw field parser/encoder; replace struct memcpy with explicit byte offsets and LE reads/writes. Keep SLIP helpers and serial validation behavior.
- `repos/fujinet-nio/tests/test_fujipacket.cpp`: append raw fixtures and all matrix edge tests.
- `repos/fujinet-nio/tests/fujibus_wire_fixtures.h`: unchanged independent expected bytes, all descriptor indices and folded checksums.
- `repos/fujinet-nio/src/lib/fujibus_transport.cpp`: only production codec caller (receive/send/receiveResponse); remains on serial wrappers until Story 1.3. Other callers are packet, transport mapping/framing and SlipFramer tests.
- `repos/fujinet-nio/docs/protocol_reference.md`: document explicit APIs, raw/trailing/size behavior and correct known worked-example discrepancies from Story 1.1 without inventing new wire rules.
- `repos/fujinet-nio-lib` and `repos/fujinet-nio/py`: read-only cross-check C/Python length/header/checksum encoding; record exact evidence paths in execution results.

## Tasks & Acceptance

**Execution:**
- [x] Codec header/source — expose raw API and explicit portable header encoding while retaining serial wrappers.
- [x] Codec tests — cover every matrix row with independent expectations; retain existing test outcomes.
- [x] Protocol reference — document raw contract, compatibility quirks and caller/C/Python audit evidence.
- [x] This story — record exact test results, review and acceptance evidence (parent).

**Acceptance Criteria:**
- Given literal vectors, when raw APIs run, then exactly FujiBus bytes are consumed/produced without SLIP and structural/trailing rules are explicit and tested.
- Given existing serial callers, when compatibility entry points run, then established wire bytes/outcomes remain unchanged and no caller must infer framing from bytes.

## Spec Change Log

## Design Notes

Raw length includes all six header bytes, descriptor continuation bytes, parameter bytes and payload. Use bounded arithmetic to reject raw oversize before building output. Preserve legacy oversized serial serialization separately if necessary; its wrapped uint16 length is not a valid raw packet contract. Existing descriptor reserved bits are ignored; do not tighten that rule. Serial wrapper skips prefix noise, requires final END, decodes the first frame and ignores malformed escape pairs: preserve those quirks with focused characterization. SLIP helper extraction belongs to Story 1.3.

## Verification

From workspace root: `source scripts/env.sh && cd repos/fujinet-nio && ./build.sh -cp fujibus-pty-debug && ctest --test-dir build/fujibus-pty-debug -R '^fujinet-nio-tests$' --output-on-failure`.

Expected: host build and registered suite pass, including unchanged serial fixtures and every new matrix case. No additional owner changes. Run `git diff --check` and `git -C repos/fujinet-nio diff --check`. Review literal expectations independently of codec output; read unchanged C/Python encoders for corroboration. Record exact commands and counts, never claim unexecuted tests.

## Execution results

Required V-CXX command passed on 2026-09-11: 317/317 host cases, 6150/6150 assertions, zero skipped; automatic build CTest also passed 23 Python tests. Explicit host CTest passed 1/1 suite. Logs: `/tmp/story-1-2-build.log`, `/tmp/story-1-2-ctest.log`. Both workspace and firmware `git diff --check` passed. Parent independently checked new literal checksum arithmetic and unchanged C/Python encoding evidence. Every matrix row is exercised by the nine added codec cases.

## Review outcome

All three review layers completed. Edge-case and verification-gap reviews found no issues. Blind review's actionable coverage improvement added a literal 0x0107-length success case and reran the required gate; parameter-only overflow and exact C evidence paths were already added in the final diff. Other suggestions were optional broader characterization or refactoring, with existing grouping/fixture coverage and no demonstrated defect. No blocking findings or deferred scope remain. Story 1.2 is accepted for releasing 1.3; this is not software-contract or hardware acceptance.

## Suggested Review Order

- Start with explicit raw and retained serial entry points.
  [fuji_bus_packet.h:103](../../../../repos/fujinet-nio/include/fujinet/io/protocol/fuji_bus_packet.h#L103)
- Inspect portable header handling and raw size bounds.
  [fuji_bus_packet.cpp:158](../../../../repos/fujinet-nio/src/lib/fuji_bus_packet.cpp#L158)
- Check independent raw fixture and boundary coverage.
  [test_fujipacket.cpp:390](../../../../repos/fujinet-nio/tests/test_fujipacket.cpp#L390)
- Read documented compatibility rules and encoder audit.
  [protocol_reference.md:438](../../../../repos/fujinet-nio/docs/protocol_reference.md#L438)

Accepted firmware commit: `abed047e42bed48e54821368035a00df887d1105`.
