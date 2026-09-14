---
title: '1-6 Accept the canonical software packet contract for bridge design'
type: 'feature'
created: '2026-09-14'
status: 'in-progress'
baseline_commit: '79f6f97f99378a7bf92383e0664e676ef15b91c6'
review_loop_iteration: 0
spec_checkpoint: false
done_checkpoint: false
contract_acceptance: held
context:
  - '{project-root}/AGENTS.md'
  - '{project-root}/docs/agent-test-policy.md'
  - '{project-root}/_bmad-output/specs/spec-amiga-zorro-ii-packet-native-backend/SPEC.md'
  - '{project-root}/_bmad-output/specs/spec-amiga-zorro-ii-packet-native-backend/execution-gates.md'
  - '{project-root}/_bmad-output/planning-artifacts/epics.md'
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** Bridge ABI decisions need an accepted contract for raw bytes, packet boundaries, ownership and failures. Stories 1.1–1.5 are recorded complete, but their evidence must substantiate the full approved contract before 1.6 can be accepted.

**Approach:** Audit prerequisite evidence, consolidate the software contract, and prepare a revision-addressable technical decision record. The user authorized agent technical acceptance on 2026-09-14; missing safety coverage produces a documented hold and a scoped follow-up, never inferred acceptance.

## Boundaries & Constraints

**Always:** Preserve existing FujiBus fields, lengths, checksums, status mapping, service payloads and serial behavior. Accept raw packets without SLIP delimiters; keep packet boundaries explicit and adapter capacity, caller buffer ownership, local reset, send/receive outcomes and unknown completion observable. Preserve one remotely in-flight exchange, existing broker/retry ownership and the distinction between local acceptance and remote effect. Record the exact evidence revisions and leave hardware decisions for Epic 2.

**Ask First:** A limitation, scope change or meaningful tradeoff that needs the user's judgment. Complete the evidence audit and concrete hold/follow-up record before escalation. Do not request routine approval of plans or test results.

**Never:** Define a Zorro address map, mailbox, queue depth, physical link, timing target or correlation field. Do not treat a mock or local reset as proof of remote quiescence, add fallback/failover or runtime backend selection, weaken retries, or accept the contract from codec tests alone.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|---------------|---------------------------|----------------|
| Complete evidence | Stories 1.1–1.5 have passing recorded V-CXX, V-BROKER and V-RETRY results | Acceptance record maps bytes, boundaries, ownership and failures to implementation/tests | Missing evidence withholds acceptance |
| Missing coverage or discrepancy | Required behavior lacks evidence or conflicts with the implementation | Record a hold; resolve the gap or obtain an explicit amendment of the governing scope before reconsidering acceptance | Merely documenting or deferring a discrepancy cannot waive a safety requirement |
| Ambiguous completion | Fault before send, after delivery, or after effect; then retry, close/open or late reply | Both actual retry paths have evidence of transmission/effect counts and no new remote exchange until proven safe quiescence | Local buffer isolation or reopen success alone is insufficient |
| Technical decision | Evidence prepared and reviewed | Agent records acceptance only when full coverage supports it; otherwise hold and identify the scope decision | Test passes and implementation status alone are insufficient |
| ABI handoff | Epic 2 reviews the accepted software record | Story 2.4 cites this record and revision as a prerequisite | Positive hardware feasibility alone cannot substitute |

</frozen-after-approval>

## Code Map

Paths below are workspace-relative; subordinate filenames in a grouped entry use the first file's owning repository.

- `repos/fujinet-nio/docs/native-packet-contract.md:9-185` -- existing canonical raw representation, explicit packet capability, bounded ownership, operation-specific outcomes, reset/uncertainty rules and downstream gates; update its acceptance reference only after review.
- `repos/fujinet-nio/include/fujinet/io/protocol/fuji_bus_packet.h:88-98` and `repos/fujinet-nio/src/lib/fujibus_transport.cpp:38-177` -- production raw codec entry points and FujiBus request/response mapping; serial wrappers and status parameter conventions are read-only evidence.
- `repos/fujinet-nio/include/fujinet/io/core/packet_io.h:8-51`, `include/fujinet/io/transport/native_framer.h:8-41`, and `src/lib/native_framer.cpp:32-119` -- bounded whole-packet capability, ownership and independent receive/send/reset state transitions.
- `repos/fujinet-nio/tests/fujibus_wire_fixtures.h:1-20`, `tests/test_native_framer.cpp`, and `tests/test_fujibus_transport_framing.cpp` -- independent literal wire vectors and production-code-driven framing/fault coverage; expected bytes are not generated by the codec under test.
- `repos/fujinet-nio-driver/amiga/nio.device/fujinet_nio_device.c:153-167,372-392`, `amiga/tests/test_fujinet_nio_device.c:840`, and `amiga/tests/test_fujinet_nio_client_retry.c:35` -- local ownership and scripted retry evidence; these inspected cases do not establish post-effect ambiguity containment or late-peer-response isolation.
- `repos/fujinet-nio-driver/common/fujinet_disk_retry.c` and `repos/fujinet-nio-lib/src/common/fn_raw.c` -- both actual retry implementations required by the epic; read unchanged and trace their fault evidence through the broker/backend boundary.
- `backlog/amiga-faster-backends.md:22-37` -- workspace gate and exit criteria; add the accepted software-contract reference without claiming hardware readiness.

## Tasks & Acceptance

**Entry audit:** Preserve recorded completion of 1.1–1.5; audit evidence against the approved epic rather than treating status as proof. Start with the five colocated `stories/1-1-*.md` through `stories/1-5-*.md` records, resolving each to its exact filename and accepted repository revision. The 2026-09-14 user instruction delegates technical acceptance; do not invent historical confirmation or treat that delegation as proof of coverage. If evidence is missing, finish the audit/hold record and pause dependent contract publication. Additional tests or implementation repairs belong to an explicitly scoped follow-up.

**Execution:**
- [x] This story -- audit each prerequisite and map every contract claim to named tests, exact commands/results and full owner revisions. For both retry paths require pre-send, post-delivery and post-effect fault evidence, actual transmission/effect counts, close/open and late-response isolation. Inventory any additional focused targets; a baseline suite pass cannot fill a missing scenario.
- [x] This story -- assemble the decision record: prerequisite links/approval provenance; workspace, firmware, driver and read-only library revisions; contract revision; claim-to-test matrix; limitations and unresolved findings; acceptance state; reviewer, date and explicit decision when supplied. Missing evidence means `held`, not `accepted`.
- [x] `repos/fujinet-nio/docs/native-packet-contract.md` -- consolidate verified bytes, capacities, ownership and outcomes; reconcile stale statements about 1.5 with the audit's actual findings. Prepare pending/held references before approval, without claiming recovery that tests do not establish.
- [x] This story -- obtain independent technical review, then record the completed contract/evidence verdict. No routine human plan or completion checkpoint is required. Hold acceptance for missing coverage and present the concrete follow-up for any needed scope decision.
- [x] `backlog/amiga-faster-backends.md` and the native contract -- publish consistent gate/evidence links after the decision, marking acceptance only after approval. Record full commit IDs obtained from Git; use the resulting workspace commit containing this decision as the immutable acceptance-record revision for consumers. Published as a hold; no acceptance revision exists.

**Acceptance Criteria:**
- Given passing evidence for Stories 1.1–1.5, when the contract is reviewed, then the acceptance record identifies canonical packet bytes, explicit boundaries, bounded ownership, capacities, send/receive/reset outcomes and unknown-completion behavior, with every claim mapped to code and tests.
- Given any unresolved safety or compatibility discrepancy, when acceptance is considered, then the record withholds acceptance and names the blocking evidence; no dependent ABI decision is released.
- Given complete evidence, when the agent accepts the independently reviewed contract, then the technical decision and reviewed revisions are recorded before any dependent gate is released.
- Given acceptance, when 1.6 is completed, then it provides an immutable, revision-addressable record for Story 2.4; execution of 2.4 is not a completion dependency. ABI approval still requires positive 2.2/2.3 evidence, and physical implementation still requires 1.14 and 2.4.

## Spec Change Log

- 2026-09-14: Readiness review found assumed retry coverage and implicit acceptance ordering. Added prerequisite evidence audit, both retry paths and fault/effect matrix, explicit completion approval, held-state handling and revision provenance. Preserve 1.5's historical completion; do not infer safety or approval from it. User authorized these story revisions and expressed uncertainty about 1.5 coverage.
- 2026-09-14: User explicitly delegated software technical acceptance and requested 1.6 execution. Removed routine human checkpoints for 1.5/1.6 in all active governing documents; retained coverage requirements and escalation for limitations, scope changes and meaningful tradeoffs.

## Design Notes

Raw length, SLIP-expanded length and physical capacity remain separate. Local adapter uncertainty latching is not proof of containment through actual Amiga retry callers. Software doubles can prove the required ownership/fault behavior; physical reset feasibility remains Epic 2 work. Changes to an accepted software contract require renewed acceptance and downstream ABI impact review; consumers must not silently substitute a newer revision.

## Verification

**Commands:**
- `source /home/markf/dev/nio/fujinet-nio-workspace/scripts/env.sh && cd /home/markf/dev/nio/fujinet-nio-workspace/repos/fujinet-nio && ./build.sh -cp fujibus-pty-debug && ctest --test-dir build/fujibus-pty-debug -R '^fujinet-nio-tests$' --output-on-failure` -- expected: independent wire, raw/SLIP, native boundary/fault and serial compatibility tests pass.
- `source /home/markf/dev/nio/fujinet-nio-workspace/scripts/env.sh && cd /home/markf/dev/nio/fujinet-nio-workspace/repos/fujinet-nio-driver/amiga/tests && make build/test_fujinet_nio_device && ./build/test_fujinet_nio_device` -- expected: broker ownership/recovery evidence passes.
- `source /home/markf/dev/nio/fujinet-nio-workspace/scripts/env.sh && cd /home/markf/dev/nio/fujinet-nio-workspace/repos/fujinet-nio-driver/amiga/tests && make build/test_fujinet_nio_client_retry && ./build/test_fujinet_nio_client_retry` -- expected: existing retry caller evidence passes with bounded, request-local attempts.

**Manual checks:**
- Resolve all evidence paths/anchors and full revisions; verify each covers the claimed scenario. Compare all required retry/fault rows to executed evidence, not only suite names. Review documented parser/encoder discrepancies against the existing protocol audit; record their disposition without silently expanding into library changes.
- Check the decision, native contract and backlog agree on pending/held/accepted status and limits. Run workspace `git diff --check` and firmware `git diff --check` if its documentation changes. Library reads alone do not require `make check`; separately authorized library edits do.

The commands above are planned baseline verification, not results. Record any extra prerequisite targets before running them. Validate local references, checkpoint consistency and whitespace; no product behavior changes.

## Execution ownership

The implementation agent owns this story's audit/results and the native contract and backlog documentation. The parent owns the already-edited governing SPEC, epics, execution gates, stories.yaml and cached epic context, final independent review and commits. Preserve those edits; do not commit or push. For a coverage hold, document the exact missing scenarios and owning files here, leave acceptance ungranted and notify the parent; do not expand into production fixes or new retry tests. A completed hold record is not completion of the acceptance story.

## Technical decision record — 2026-09-14

**Decision: held.** Codex implementation agent completed the prerequisite audit
and withholds technical acceptance. Passing baseline tests establish the local
software claims below, but do not establish the approved retry/remote-ownership
contract. Independent review confirms the held verdict. No dependent ABI gate is
released; story status remains `in-progress`. This is not story completion.

**Approval provenance:** the 2026-09-14 delegation in this story, the SPEC,
execution gates and adopted epic authorizes agent technical acceptance only on
sufficient evidence. The exact user instruction was “do that, and build story 1.6 too.”
This records acceptance-owner amendment provenance only, not acceptance of the
software contract or proof of requirement coverage. It does not retroactively
certify Story 1.5. Historical
completion and review claims are preserved verbatim in Stories 1.1–1.5.
**Independent reviews (2026-09-14, supplied by parent):** edge-case review `[]`;
verification-gap review: none. Blind review requested the documentation patches
recorded below and retained the outstanding pre-existing F1–F3 findings. The
parent additionally verified F1 against source. This implementing agent applied
the patches; the independent technical review task is complete. Final parent
publication and provenance are recorded below.

### Revision provenance

All identifiers below were obtained from Git, not expanded by inference.

| Evidence owner | Audited revision / state |
| --- | --- |
| Workspace HEAD and preserved story baseline | `79f6f97f99378a7bf92383e0664e676ef15b91c6` |
| Firmware code, tests and pre-audit contract | `fd965f5ec8609bacead86b94a23f73093da98de2` |
| Driver code/tests | `342c5700d843901c6120a17b2620602995e6fd00` |
| Library, read-only | `dac8bf66c4ec44841790e08021c1654379c21255` |
| Pre-audit firmware contract Git blob | `0670f22d46422c1cf32abc91c14a641b6a7bad9e` |

The three repositories were clean before this audit. Workspace governing edits
to SPEC, execution gates, epics, stories.yaml, cached epic context and this
story already existed; they are not represented as committed at workspace HEAD.
Only this story's execution fields/results, the firmware contract and faster
backends backlog were edited here. Product code/tests and the library are unchanged.

The revised contract and this hold record carry the reviewed held verdict;
parent publication details are recorded below. **Accepted contract revision: none. Immutable acceptance
record revision: none.** On eventual acceptance, use the full firmware commit
containing the reviewed contract and the full resulting workspace commit
containing the decision. Do not use the baseline commit, a branch name, a blob
identifier or a guessed future self-reference as an acceptance-record revision.

### Prerequisite audit

V-CXX, V-BROKER and V-RETRY refer to the exact commands in Verification above;
current execution results are below. Historical counts are recorded evidence,
not claims that those older checkouts were rerun here.

| Prerequisite record | Audited owner/gitlink revision and workspace completion-record revision (not acceptance provenance) | Recorded verification, acceptance provenance and current disposition |
| --- | --- | --- |
| [1.1 independent fixtures](1-1-establish-independent-fujibus-wire-format-regression-fixtures.md) | Firmware `46324942a7eed01871b9c1ed21b62f14a90916a1`; workspace `6a08a5c9ae498eb4bfe992de5ebad6f783455ff7` | V-CXX: 308 cases / 5,975 assertions; initial sandbox socket failures followed by successful explicit CTest. Fixture arithmetic independently reviewed by its parent. Current V-CXX retains and passes the fixture cases. |
| [1.2 raw codec](1-2-expose-the-canonical-raw-fujibus-codec-without-breaking-serial-callers.md) | Firmware `abed047e42bed48e54821368035a00df887d1105`; workspace `4c879d10a4d9b9045dce66b101eebf61b3148454` | V-CXX: 317 cases / 6,150 assertions, 23 Python tests, explicit CTest 1/1; recorded three-layer review. Raw validity/size and serial compatibility cases still pass. |
| [1.3 raw framer composition](1-3-make-framer-composition-use-raw-fujibus-packets-consistently.md) | Firmware `ee17409ef2fd4d78b25fc8835deeb0177788f0f0`; workspace `88f4686c83eafe0eef86561899d6b741165fd0b6` | V-CXX: 324 cases / 6,352 assertions, 23 Python tests, explicit CTest 1/1; recorded review fixes and acceptance. Raw/SLIP and SIO composition remain covered. |
| [1.4 bounded adapter](1-4-provide-a-bounded-native-packet-adapter-and-deterministic-io-double.md) | Firmware `fd965f5ec8609bacead86b94a23f73093da98de2`; workspace `e62c31152574635183b2b3420b94886d22933c83` | Final V-CXX: 344 cases / 6,856 assertions, 23 Python tests, explicit CTest 1/1; 25 native cases and recorded review. Local bounded ownership and uncertainty latching pass; no Amiga retry or remote recovery proof. Its old human-checkpoint wording is superseded by the 2026-09-14 governing amendment. |
| [1.5 broker/retry evidence](1-5-prove-native-broker-ownership-and-recovery-against-existing-retry-callers.md) | Driver `342c5700d843901c6120a17b2620602995e6fd00`; workspace `93bc94508a7e9327f965148791e4a893665cd61c` | Recorded V-BROKER/V-RETRY pass and “No verification gaps found.” Current passes corroborate only local ownership and scripted attempts. Full epic ambiguity/fault matrix is missing; historical done status does not satisfy this gate. |

For 1.1 and 1.5, which lack an explicit accepted-owner line, the completion
commit's gitlink resolves the owner revision above (`git ls-tree`); owner commit
subjects/diffs also identify their fixture/test changes. This is revision
provenance, not additional historical human approval.
Acceptance provenance is the linked story's recorded review/decision, subject
to this audit's coverage limits; an owner gitlink identifies code, not approval.

### Claim-to-test matrix

Paths in this table are relative to their named repository. Every named C++
case is registered in the executed V-CXX suite; the broker/retry C functions
are called by their executed test mains. Names identify the actual assertions,
not merely a passing suite. “Local” deliberately limits the established claim.

| Claim / implementation | Named test evidence | Result / limit |
| --- | --- | --- |
| Firmware `src/lib/fuji_bus_packet.cpp::parseRaw/encodeRaw`; six-byte header, LE length and U8/U16/U32 descriptors, folded checksum, literal payload | `tests/test_fujipacket.cpp`: `literal FujiBus minimum header serialization and parsing`, `literal FujiBus descriptors cover every count and width index`, `literal FujiBus binary payload escaping and carry checksum`, `raw APIs consume and produce independent literal vectors`, `raw header encodes and parses an asymmetric little-endian length`; independent `tests/fujibus_wire_fixtures.h` | V-CXX pass; five valid and five malformed literal raw/SLIP pairs. Typed checksum sum 0x792 folds to 0x99; binary 0x2AB folds to 0xAD. |
| Explicit raw input, short/checksum/length/descriptor/parameter rejection, trailing bytes, compatibility quirks | Same file: `raw framing is explicit even when header bytes are SLIP specials`, `raw rejects short checksum and structural failures without a packet`, `raw distinguishes trailing bytes outside length from payload inside it`, `raw and serial preserve reserved and zero-count descriptor semantics`, `serial parser retains first-frame and malformed-escape compatibility` | V-CXX pass. No SLIP sniffing; no tightening of inherited serial parser quirks. |
| Raw length 6–65535, oversize failure including descriptors and parameters | Same file: `raw size boundary includes the header parameters and extra descriptors`, `raw rejects parameter-only overflow before building output` | V-CXX pass. Legacy serial encoder's wrapped oversize length is characterized, not a valid native packet. |
| Firmware `src/lib/fujibus_transport.cpp`; unchanged request fields and status U8 param0, raw IFramer boundary | `tests/test_fujibus_transport_framing.cpp`: `literal FujiBus request maps parameters and binary payload`, `literal FujiBus response send and receive preserve status and payload`, `raw and serial framers map independent request fixtures identically`, `raw and serial framers preserve literal response status and bytes` | V-CXX pass. Response IDs remain synthetic, without on-wire correlation. No real-service parity claimed. |
| Serial escaping/extraction and SIO envelope compatibility | `tests/test_slip_framer.cpp`: `literal binary frame survives every split and repeated polls`, `noise is discarded and literal binary frames retain ordering`, `framer and serial wrapper share escaping and malformed-escape compatibility`, `escape-only malformed frame is consumed without empty delivery`; `tests/test_atari_sio_fujibus_framer.cpp`: `AtariSioFujiBusFramer preserves literal SLIP through raw transport composition` | V-CXX pass, including fragmentation inside escapes and independent envelope checksums. |
| Firmware `IPacketIO`, `NativeFramer::poll/nextPacket`; whole records, one slot, bounded work, partial and size failures | `tests/test_native_framer.cpp`: `queued packets preserve boundaries and receive-slot backpressure bounds work`, `delayed packets need explicit bounded delivery steps`, `partial records complete once or truncate without leaking prefixes`, `empty exact-capacity and metadata-only oversized records have explicit outcomes`, `effective raw capacity is capped at 65535 for both directions`, `double bounds both record count and bytes including partial and scheduled data`, `invalid successful receive lengths never expose buffer contents` | V-CXX pass; adapter count/byte limits are local test choices, not bridge queue depth. Empty opaque records rejected; nonempty opaque records still need codec validation. |
| Caller buffer lifetime, stable capability, exclusive framer, fail-closed bootstrap | Same file: `accepted send and extracted receive buffers have independent ownership`, `adapter identity change cannot expose the old receive slot or reset another adapter`, `unsupported and zero-capacity channels fail closed without byte I/O`, `native bootstrap requires usable packet capability and serial bootstrap remains available`; four noncopy/nonmove static assertions | V-CXX pass. Exclusive active-framer use is an interface precondition, not a tested multi-framer synchronization guarantee. |
| Single-attempt send, separate outcomes, backpressure/definite rejection and serialization errors | Same file: `transmit queue enforces record and byte backpressure without partial acceptance or replay`, `unavailable peer and definite send failure are separate from receive outcomes`, `real FujiBus transport preserves literal packets and exposes native send failure`, `real transport serialization rejection cannot leave native send success stale`, `real transport rejects responses above smaller adapter capacity without sending or replay`, `serial transport drops oversized serialization and later sends valid response bytes`, `double validates send fault injection and latches reset-required state` | V-CXX pass. `Ok` means local acceptance only; statuses are last-operation results, not readiness or remote effects. |
| Local reset clears local data; reset-required/failure and uncertainty latch independently | Same file: `local reset discards ready queued partial scheduled and transmitted data`, `reset failure locks I/O and drops the ready slot until successful reset`, `failed reset can retain bounded local state but none is accessible before successful reset`, `framer latches adapter reset-required outcomes independently of adapter behavior`, `unknown completion blocks send and stale receive across successful local resets`, `unknown completion reported by reset remains latched after a later successful reset`, `locally accepted ambiguous send cannot be accepted again after reset or retry` | V-CXX pass. Last case counts one local acceptance across three blocked retries; it does not count remote service effects or invoke an Amiga retry caller. |
| Driver `amiga/nio.device/fujinet_nio_device.c::process_exchange/worker_pump/device_close`; local FIFO, abort, response capacity, error domains | `amiga/tests/test_fujinet_nio_device.c`: `test_fifo_order`, `test_abort_queued`, `test_abort_queued_middle_request_preserves_ownership`, `test_abort_in_progress`, `test_abort_in_progress_fatal_closes`, `test_close_in_progress_does_not_abort`, `test_backend_oversize_response_is_fn_err_io`, `test_fatal_backend`, `test_timeout_resets_backend` | V-BROKER pass. Queued abort invokes backend zero times; in-progress abort invokes it once and replies once with zero reported length. Error-domain and local callback counts do not prove remotely in-flight counts. |
| Driver close/open and request-local buffers after a scripted timeout | Same file: `test_transport_timeout_recover_and_retry_request`, `test_close_does_not_abort_in_progress_then_next_request`, `test_opencnt_zero_keeps_backend` | V-BROKER pass. Two backend calls and successful lazy-open are asserted, with no modeled peer effect, pending remote exchange or late reply. **Insufficient for remote containment.** |
| Actual driver `common/fujinet_disk_retry.c::fujinet_disk_retry_exchange`; bounded unchanged retry policy and response lengths | `amiga/tests/test_fujinet_nio_client_retry.c`: `test_recovered_read`, `test_recovered_write`, `test_context_diagnostics_records_retry_attempts`, `test_persistent_fault`, `test_non_retryable_result`, `test_excluded_commands`, `test_malformed_sector_packets`, `test_remote_timeout_is_not_retried`, `test_null_response_length_is_rejected` | V-RETRY pass. Read recovers in 2 scripted calls, write in 3, persistent failure stops at 3; nonretryable cases stop at 1. Remote timeout status is distinguished from transport timeout. **No broker/backend traversal or effect oracle.** |
| Both actual callers enforce remote ambiguity containment across lifecycle and late response | Required `fujinet_disk_retry_exchange` and library `src/common/fn_raw.c::fn_raw_call` through actual broker/backend boundary | **Missing; held.** No executed target provides this integration matrix. |

### Required retry/fault evidence audit

“Missing” means the required assertion was not exercised, not an observed
hardware failure. Callback invocation counts cannot be relabeled transmissions.
The broker double echoes even one-byte requests and always opens successfully;
it is not a packet-I/O peer with persistent uncertain state.

| Required scenario | Disk retry path | `fn_raw_call` path |
| --- | --- | --- |
| Pre-send failure; zero transmissions/effects on rejected attempt; safe subsequent attempt | Scripted transport failure exists, but delivery stage, actual zero transmissions/effects and broker traversal are missing | No actual caller fault test identified |
| Delivery occurred; response unavailable; retry held until safe quiescence | Missing delivery/in-flight oracle and containment assertion | Missing |
| Effect occurred; response lost/corrupt; no duplicate effect or new remote exchange while uncertain | `test_recovered_write` permits 3 identical scripted calls without effect count; missing post-effect evidence | Missing; production code may replay a non-timeout failure once |
| Close/open, local reset, queued callers and caller retries while completion remains unknown | Broker reopens on timeout, tested separately; no persistent peer uncertainty or both-caller integration | Missing |
| Late old reply after local clear/reopen cannot complete a later same-device/command request | No late peer reply is scheduled; different response buffers alone are insufficient | Missing; device/command match is not a correlation identifier |
| Proven safe quiescence permits recovery; unavailable/failed quiescence keeps remote transmissions blocked | No such backend proof or recovery schedule | Missing |

The production disk chain is
`amiga/channels/rs232/fujinet_nio_client.c::nio_exchange` → actual
`fujinet_disk_retry_exchange` → `fn_transport_exchange_buffers` → broker.
V-RETRY instead supplies `context_exchange/scripted_transport`; its Makefile
links the common retry implementation and Linux library but not the Amiga client,
Amiga transport or broker. It also passes no attempt observer, so it does not
test `nio_record_attempt`'s broker/native diagnostic collection.

The library chain is actual `fn_raw_call` → `fn_transport_exchange` → Amiga
`fn_transport_exchange_buffers` → broker. `fn_raw_call` attempts a replay for
failed validation or non-timeout transport failure, up to two total attempts;
`FN_ERR_TIMEOUT` exits without replay. This is source evidence, not executed
fault/effect evidence. It must remain unchanged in the proposed follow-up unless
a separate scope decision authorizes otherwise.

**Test discrepancy F1:** in `test_retry_outputs_are_request_local_per_call`, the
first call consumes script indices 0 and 1. The second call writes indices 0/1
again without resetting `transport_calls`; it consumes index 2, initialized to
`FN_OK`, so its intended timeout/retry does not execute. There is no assertion
on the second call's attempts or independent preservation of the first buffer.
The pass proves different final output bytes only. Do not rely on this test as
second-call replay or late-peer-response coverage.

**Coverage finding F2:** the broker closes on `FN_ERR_TRANSPORT`/`FN_ERR_TIMEOUT`
and lazy-opens on the next request. Its callback double has no persistent
uncertainty, remote effect counter, or old-response delivery. A future native
backend must contain this lifecycle; the audit does not demonstrate that such
containment is impossible, nor that it currently exists.

**Coverage finding F3:** no actual `fn_raw_call` retry test was found in the
driver native tests, library test sources/scripts/targets or workspace
integration-test references audited. Literal-symbol inventory found test stubs
in `legacy_appkey_wire_test.c`, `wifi_wire_test.c`, `mount_resolve_wire_test.c`,
`disk_context_test.c`, `disk_wire_test.c` and `library_link_test.c`; the public
archive-link test defines its own `fn_raw_call`. Linking the archive does not
establish execution of the actual raw retry implementation.

### Compatibility findings and focused-target inventory

The existing firmware [protocol audit](../../../../repos/fujinet-nio/docs/protocol_reference.md#caller-and-cross-language-audit)
corroborates common encoding, not identical parser acceptance across languages.
Story 1.1's worked-example arithmetic/status discrepancies were corrected in
1.2. Reserved descriptor bits/zero-count continuations, malformed serial escape
handling and oversized legacy serialization are explicit compatibility behavior
with executed C++ characterization. They are not new valid native encodings or
permission to reinterpret service payloads.

**Informational F4 — incidental pre-existing parser difference:** the read-only library
`src/common/fn_packet_parse_common.c::fn_parse_response_header` validates length
and checksum, but follows continuation bytes and interprets the final
descriptor; it does not decode every descriptor as C++ `parseRaw` does. With
descriptor zero it defaults status to `FN_OK`, whereas C++ `receiveResponse`
defaults missing/non-U8 status to `InternalError`. Canonical responses with one
U8 status parameter are supported. No conflict with the approved requirements
has been demonstrated by these permissive malformed-input differences. Universal
cross-language validity equivalence is not a requirement or an additional gate.
Include affected response fixtures where they exercise actual `fn_raw_call`
retry fault behavior; otherwise F4 is informational and requires no source
changes. It is not a reason to repair the library parser within this story.

Additional existing focused target inventory (inspected, **not executed**):
library `make test-amiga-transport` compiles actual Amiga `fn_transport.c` with
stubbed `DoIO` and `fn_state.c`; it tests client ABI/lifecycle, not actual broker
or raw retries. Library `make test-library-link`, `make test-disk-context` and
`make test-session` cover archive/API/context or serial-session seams, not the
missing both-caller native fault matrix. Driver `amiga/tests/Makefile` has
separate queue, Exec-boundary, resident, serial and lifecycle targets; none
combines either actual retry caller with a persistent packet peer. No extra
target was run as a substitute for missing scenarios. Library `make check` is
not required by read-only inspection or V-RETRY linking the unchanged Linux
archive; no all-target library pass is claimed.

### Scoped follow-up for parent/user decision

Proposed follow-up **“Prove both retry callers against persistent native peer
uncertainty”** is required before reconsidering 1.6. It is documented here for
scope approval, not implemented or silently added to another story.

1. Driver owner: correct F1 in `amiga/tests/test_fujinet_nio_client_retry.c`,
   asserting each call's absolute script indices, attempt counts, sentinel bytes,
   independent first-buffer preservation and diagnostics. This repair alone
   does not close the safety hold.
2. Driver owner: add a focused sibling native integration target in
   `amiga/tests/Makefile` and a test-only bounded packet peer. Exercise the
   actual `common/fujinet_disk_retry.c`, Amiga client/transport seam and
   `amiga/nio.device/fujinet_nio_device.c`. Link actual library `src/common/fn_raw.c`
   unchanged for a second path through the same broker boundary. Keep peer
   in-flight state, effects and delayed replies independent of local close/open.
   Containment must reside in backend-side code under test, outside the peer
   double. The independently controlled peer supplies faults and observations;
   it must not enforce the transmission/replay exclusion asserted by the test.
3. For **each** path, execute all six rows above with controlled fault steps.
   Count caller attempts, backend entries, actual transmissions, remote effects,
   current/max remotely in-flight exchanges and replies separately. Prove zero
   extra transmissions/effects during unresolved ambiguity, exactly one local
   completion per request, zero reported failed lengths, no late response
   misattribution, and explicit safe-quiescence versus failed-quiescence outcomes.
   Include same-device/command subsequent requests, locally queued callers,
   queued/in-progress abort, unavailable peer, failed open, corruption,
   oversize/truncation and reset failure. Do not infer success from identical
   final disk bytes or from clearing the double's local scheduled events.
   At the software boundary, quiescence proof means the prior request can no
   longer execute or deliver an old response. Independently controlled peer
   state or an observable completion barrier must establish that condition for
   the backend; local reset, reopen or elapsed time alone does not establish it.
   This defines a software evidence obligation, not a physical reset protocol.
4. Include independent canonical/malformed response fixtures where they affect
   actual `fn_raw_call` retry fault evidence. F4 otherwise remains informational:
   no universal parser-equivalence gate or source repair is added without a
   demonstrated conflict with approved requirements. Keep canonical bytes/status
   mapping intact. Any required library or retry-policy repair is a separate
   scope decision; actual library edits require complete `make check`.
5. Record exact new target commands before executing; rerun V-CXX/V-BROKER/
   V-RETRY as relevant, record full owner revisions, and return for independent
   1.6 review. If unchanged higher layers cannot be safely contained behind
   the backend, retain the hold and ask for the specific scope amendment.

No proposed test peer establishes physical reset feasibility. Epic 2 still owns
the physical reset/quiescence evidence. The follow-up introduces no hardware
addresses, queue-depth commitment, link protocol, timing target, correlation
field, automatic retry/fallback or runtime backend selection.

### Executed verification

On 2026-09-14, from workspace root, sourced the shared environment and ran:

```sh
source /home/markf/dev/nio/fujinet-nio-workspace/scripts/env.sh && cd /home/markf/dev/nio/fujinet-nio-workspace/repos/fujinet-nio && ./build.sh -cp fujibus-pty-debug > /tmp/story-1-6-build.log 2>&1 && ctest --test-dir build/fujibus-pty-debug -R '^fujinet-nio-tests$' --output-on-failure > /tmp/story-1-6-ctest.log 2>&1
source /home/markf/dev/nio/fujinet-nio-workspace/scripts/env.sh && cd /home/markf/dev/nio/fujinet-nio-workspace/repos/fujinet-nio-driver/amiga/tests && make build/test_fujinet_nio_device && ./build/test_fujinet_nio_device && make build/test_fujinet_nio_client_retry && ./build/test_fujinet_nio_client_retry
```

- V-CXX: exit 0, **344/344 cases, 6,856/6,856 assertions, zero skipped**.
  Build's automatic CTest passed 2/2 registered suites, including **23 Python
  tests**. Required explicit host CTest passed **1/1**, 0.20 seconds.
- V-BROKER: target up to date, executable exit 0; its 26 test functions are
  invoked by `main`. The executable prints no success count.
- V-RETRY: rebuilt with `-Wall -Wextra -Werror -pedantic`, exit 0 and
  `fujinet_nio_client retry tests passed`; 10 test functions invoked by `main`.
  Its prerequisite `make ... linux` found the unchanged library up to date.
- No guest, hardware, all-target library or new retry/fault tests were run.
  No environment blocker occurred. Passing baseline output is not missing
  scenario evidence.

Document validation commands selected for this documentation-only change:
`git diff --check`, `git -C repos/fujinet-nio diff --check`, plus a focused
Python check of local Markdown links/anchors, full Git revisions, held state,
unchanged frozen intent/prerequisites and consistent downstream gates. Final
document-check results are recorded below after execution.

Document checks passed: `source scripts/env.sh && python
/tmp/story-1-6-doc-check.py` verified 10 local links/anchors, 13 full Git object
identifiers, 46 named C++ cases, 26 broker and 10 retry calls in their test mains,
held/checkpoint/gate consistency, unchanged authorized amended frozen intent and
prerequisite records, and clean driver/library trees. The frozen-intent comparison
was against the authorized 2026-09-14 amended intent available in the index,
not the original intent at `baseline_commit`. That original baseline predates
the acceptance-owner amendment. The checker is a temporary audit aid;
the committed tests and the revision/command/results tables above are the
durable evidence. Workspace and firmware `git diff --check` passed; staged
workspace changes are checked separately with `git diff --cached --check`.

**Implementation handoff (before parent publication):** first four execution
tasks, including independent technical review, were complete. Final immutable
publication was parent-owned and is recorded below.
The backlog and native contract link the reviewed held evidence consistently.
No staging, commit, push, production fix or new retry test was performed by this
implementation agent. F1–F3 remain outstanding in the scoped follow-up; F4 is
informational unless it affects required retry fault evidence. Acceptance stays
held and the story remains incomplete.

### Independent-review patches and focused rebuild

Applied the parent-supplied blind-review patches: distinguish owner revisions
from approval provenance; identify the authorized amended frozen-intent baseline
and exact acceptance-owner instruction; keep F4 informational; require backend
containment outside the independently controlled peer with observable software
quiescence proof; link the driver follow-up in the backlog; and publish the
reviewed held verdict with inline limits in the firmware document. Edge-case
review returned `[]`, verification-gap review found none, and the parent
separately confirmed F1 in source. F1–F3 remain unresolved; no gate was released.

Additional focused verification command selected before execution to establish
broker binary/source provenance (no broader code retesting requested):

```sh
source /home/markf/dev/nio/fujinet-nio-workspace/scripts/env.sh && cd /home/markf/dev/nio/fujinet-nio-workspace/repos/fujinet-nio-driver/amiga/tests && make -B build/test_fujinet_nio_device && ./build/test_fujinet_nio_device
```

Result: **passed, exit 0** on 2026-09-14. `make -B` invoked `cc` with
`-std=c99 -Wall -Wextra -Werror -pedantic -Wno-unused-function
-DFUJINET_NIO_NATIVE_TEST`, rebuilding the executable from
`test_fujinet_nio_device.c`, `../nio.device/fujinet_nio_device.c` and
`../common/fujinet_io_queue.c` at audited driver revision
`342c5700d843901c6120a17b2620602995e6fd00`. The rebuilt executable ran all 26
test functions in `main` and exited successfully without success output.
Driver/library source trees remained clean. This replaces reliance on the
earlier up-to-date broker binary; it does not fill F1–F3 coverage gaps.

Post-patch document checks passed: `source scripts/env.sh && python
/tmp/story-1-6-doc-check.py` checked 11 local links/anchors, 13 Git objects,
46 named C++ cases, test-main registrations, four completed tasks with final
publication unchecked, held/in-review state, unchanged prerequisites and the
authorized amended frozen intent captured before these review patches in
`/tmp/story-1-6-authorized-intent.txt`. This again checks preservation of the
2026-09-14 amendment, not identity with the original baseline intent.
Workspace unstaged/staged and firmware whitespace checks passed with
`git diff --check`, `git diff --cached --check` and
`git -C repos/fujinet-nio diff --check`. No broad code retesting was performed.

### Final parent disposition and publication

The parent independently verified F1's script-index defect and the actual
`fn_raw_call` retry loop, inspected the contract diff and passing CTest output,
and reviewed all three independent review results. Technical verdict: **held**.
All documentation/audit execution tasks are complete, but the required both-caller
ambiguity evidence and software acceptance criteria remain unsatisfied.
Story 1.6 must not be marked done or used to release dependent work.

Review patches restored 3.6's unchanged pre-implementation human checkpoint,
made current 1-5/1-6 dependency holds explicit, distinguished audited revisions
from approval provenance, and made F4 informational rather than a new parser
equivalence requirement. The follow-up must test backend enforcement independently
of peer behavior. Grouped claim/test rows remain appropriate for this audit;
unsupported obligations are individually listed in the six-row fault matrix.
No runtime dispatcher or parser redesign was introduced by a documentation gate change.

Published firmware contract commit:
`059cf18cf6ee39f3a65cc7a4e01ee77815507057`.
The workspace commit containing this final disposition pins that firmware
gitlink and is the immutable **hold** record; it is not an acceptance revision.
For eventual acceptance, commit the reviewed firmware contract first, record
its full ID and decision in the workspace, then supply that workspace commit's
full ID to consumers. No document needs to contain its own future commit hash.

Workspace validation included an inline Node check of all 25 dispatch entries,
software checkpoint flags, preserved 2-4/3-6 flags, amendment propagation,
local evidence links and held state. Workspace unstaged/staged and firmware
whitespace checks passed. No product source changed; no hardware work occurred.

## Suggested Review Order

- Read the held verdict and distinguish passing baseline tests from missing safety evidence.
  [1-6-accept-the-canonical-software-packet-contract-for-bridge-design.md:102](1-6-accept-the-canonical-software-packet-contract-for-bridge-design.md#L102)

- Check technical acceptance ownership and direct dependency holds.
  [execution-gates.md:18](../execution-gates.md#L18)

- Read the published software guarantees and recovery limits.
  [native-packet-contract.md:1](../../../../repos/fujinet-nio/docs/native-packet-contract.md#L1)

- Inspect the existing misindexed script behind finding F1.
  [test_fujinet_nio_client_retry.c:330](../../../../repos/fujinet-nio-driver/amiga/tests/test_fujinet_nio_client_retry.c#L330)
