---
title: 'Close Story 1.5 retry-containment gaps for 1.6 acceptance'
type: bugfix
created: '2026-09-15'
status: done
baseline_commit: ff73b2a782d47ccfdd221ccdbc70ccbc14baa1a3
review_loop_iteration: 0
spec_checkpoint: false
done_checkpoint: false
context:
  - '{project-root}/AGENTS.md'
  - '{project-root}/docs/agent-test-policy.md'
---

<frozen-after-approval reason="user authorized scoped follow-up: Perform the fix; technical acceptance delegated">

## Intent

**Problem:** Story 1.6's audit found F1 (a misindexed retry script), F2 (no persistent remote ambiguity evidence through the broker), and F3 (no actual fn_raw_call coverage).

**Approach:** Correct F1 and implement a reusable, transport-independent native backend containment component plus deterministic integration tests through both unchanged real callers and the broker. Close the six-row fault matrix before reconsidering 1.6.

## Boundaries & Constraints

**Always:** Preserve raw FujiBus bytes, public broker ABI, error domains, caller buffers, serial deployment and both retry policies. Backend-side code under test owns containment; an independent bounded peer owns delivery, effects and late responses. Count attempts, transmissions, effects, replies and remotely in-flight work separately. Keep persistent uncertainty across backend close/open and local reset. At most one remote exchange.

**Ask First:** Only a demonstrated incompatibility requiring changed caller/service semantics or an unresolved scope tradeoff. Ordinary tests, backend implementation and necessary harness binding are already authorized.

**Never:** Make the peer double enforce safety for the backend; invent correlation fields, physical registers/link/reset protocol, serial fallback, runtime selection or hardware readiness. Do not silently redesign library parsers/retries.

## I/O & Edge-Case Matrix

Each fault row must run through both actual callers.

| Scenario | Input/state | Required outcome |
| --- | --- | --- |
| F1 regression | Second caller retries after first consumed script entries | Correct absolute indices; exact attempt counts, independent buffer preservation and diagnostics |
| Before send | Definite rejection/unavailable/open failure | Zero transmissions/effects for rejected attempt; bounded caller retries can safely recover |
| After delivery | Sent but completion unknown | Subsequent attempts cannot transmit until independently established quiescence |
| After effect | Lost/corrupt/oversize/truncated response | One effect; no ambiguous replay; zero reported failed length |
| Lifecycle | Close/open, local reset, failed quiescence, queued callers | Quarantine persists and blocks new sends; no stale attribution |
| Late reply | Old same-device/command response after local clear | Cannot complete a newer request; failed proof cannot clear quarantine |
| Recovery | Peer establishes no pending effect or old-response delivery | Explicit backend recovery permits a new exchange; successful local reset alone does not |
| Ownership | Queued/in-progress abort, delayed delivery, buffer sentinels | Queued abort sends nothing; active abort not rollback; one reply/request; max remote count one |

</frozen-after-approval>

## Code Map

- `repos/fujinet-nio-driver/amiga/tests/test_fujinet_nio_client_retry.c:330` -- F1 uses script slots 0/1 twice while transport_calls advances. Fix and strengthen assertions.
- `repos/fujinet-nio-driver/amiga/tests/test_fujinet_nio_device.c` -- real broker native hooks plus Exec stubs; reuse idioms without substituting fake broker results.
- `repos/fujinet-nio-driver/amiga/nio.device/fujinet_nio_device.c` -- existing backend callbacks, worker pump, abort/close. Preserve serial behavior; new component binds behind this seam.
- `repos/fujinet-nio-driver/amiga/channels/rs232/fujinet_nio_client.c` and `common/fujinet_disk_retry.c` -- actual disk chain and diagnostic observer, unchanged.
- `repos/fujinet-nio-lib/src/common/fn_raw.c`, actual Amiga transport and common codec/state sources -- link unchanged through broker; library changes require complete make check.
- Proposed `repos/fujinet-nio-driver/amiga/nio.device/fujinet_nio_packet_backend.c` and adjacent header -- reusable bounded whole-packet backend guard, opaque packet I/O callbacks, response validation and explicit quiescence-gated recovery. No physical adapter or deployed serial change.
- Proposed `repos/fujinet-nio-driver/amiga/tests/test_fujinet_nio_packet_backend.c`, focused peer/stub helpers and `amiga/tests/Makefile` -- register integration target and executable fault matrix.
- `repos/fujinet-nio-driver/amiga/README.md` -- document software component/test entry point and adapter obligations.

## Tasks & Acceptance

- [x] Correct F1 and prove intended retries and ownership assertions execute.
- [x] Implement backend-side containment outside peer, with bounded borrowed buffers, explicit transfer outcomes and persistent quarantine; validate raw response before exposing it to retrying callers.
- [x] Integrate both actual caller paths, actual Amiga transport, actual broker and new backend in focused native tests; cover every matrix row with independent counts.
- [x] Document scope, capacity and recovery obligations; record exact tests/results and any genuine residual limitation.

Given ambiguity after transmission, when unchanged callers retry or local lifecycle changes occur, then no new remote transmission/effect occurs until the backend obtains proof excluding prior pending work and stale delivery.

Given independent quiescence proof, when recovery is requested, then only the backend's explicit recovery transition clears uncertainty and later calls receive their own response.

Given the six fault rows and ownership scenarios, when the registered target runs, then both real caller paths traverse the real broker and backend, with at most one remotely in-flight exchange and exactly one completion per IORequest.

## Design Notes

Peer callbacks may describe completion, definite rejection or unknown completion; local acceptance is not remote completion. The software recovery callback contract must guarantee old work cannot still execute and old replies cannot arrive. Tests control peer state/proof independently, including failure and late replies; local clear/close cannot synthesize that guarantee. Physical realization stays deferred. Definite transport success with a valid response is distinct from unknown completion; do not promise removal of all existing application-level retry semantics.

Read-only caller audit: `fn_raw_call` can replay a successfully received valid
response when its payload exceeds the application's `reply_capacity`; the
transport/backend only receives `FN_MAX_PACKET_SIZE`, so cannot see that limit.
This is existing policy after known completion, not ambiguous transport completion.
Preserve and document it. Structural/checksum/device-command failures visible
before successful exposure must still quarantine. A valid U8 remote error/status
is not a transport failure and must pass through unchanged.

## Verification

Source `scripts/env.sh` from workspace before each command.

- Driver `amiga/tests`: `make build/test_fujinet_nio_packet_backend build/test_fujinet_nio_client_retry build/test_fujinet_nio_device && ./build/test_fujinet_nio_packet_backend && ./build/test_fujinet_nio_client_retry && ./build/test_fujinet_nio_device`.
- Cross-compile the new portable backend component with the configured Amiga compiler using documented target flags; record exact command before running. No guest test is required for an undeployed component/native harness; any serial/DiskDevice-visible change requires the policy's focused guest check.
- Workspace and each touched owner: `git diff --check`. Parent updates firmware contract using previously passed raw/framer tests, reruns V-CXX if required by changed contract claims, and reassesses 1.6.
- Firmware contract owner, from workspace: `source scripts/env.sh && cd repos/fujinet-nio && ./build.sh -cp fujibus-pty-debug && ctest --test-dir build/fujibus-pty-debug -R '^fujinet-nio-tests$' --output-on-failure`. Parent runs this baseline while driver implementation proceeds; new containment is verified by the driver integration target.

## Execution ownership

### Native link recipe from read-only investigation

Explicit sources: driver `common/fujinet_disk_retry.c`,
`amiga/channels/rs232/fujinet_nio_client.c`,
`amiga/nio.device/fujinet_nio_device.c`, `amiga/common/fujinet_io_queue.c`;
library `src/platform/amiga/fn_transport.c`, and common `fn_disk.c`,
`fn_raw.c`, `fn_init.c`, `fn_state.c`, `fn_packet_header.c`,
`fn_packet_parse_common.c`, `fn_packet_checksum.c`,
`fn_packet_checksum_packet.c`, `fn_checksum_fold.c`. No Linux archive
or wrapped transport. Use `FUJINET_NIO_NATIVE_TEST` and
`FN_AMIGA_EXPLICIT_LIFECYCLE`; unified test stubs must have compatible
Exec layouts across all translation units. Supply actual API shims:
OpenDevice to native open (pointer success maps to zero); CloseDevice to native
close; DoIO to BeginIO plus worker pumping until ReplyMsg for that request.
Supply allocation/ports/Disable/Enable/ReplyMsg. Existing driver stubs lack
CONST_STRPTR, ports/alib and some Exec declarations; do not simply combine
incompatible driver/library stub include trees. Initialize/close actual transport
around harness cases before resetting broker/global init state. Never WaitIO an
OpenDevice-only request.

Implementer owns driver sources/tests/docs and this follow-up's results; parent owns all 1.6/governing/backlog/firmware documentation, independent reviews and commits. Preserve others' edits; no staging, commits or pushes by implementer. Read the six-row audit and scoped follow-up in `stories/1-6-accept-the-canonical-software-packet-contract-for-bridge-design.md` as required supporting context; the user's 2026-09-15 fix authorization supersedes its prior prohibition on implementing the follow-up. No routine human checkpoint. Do not modify existing library sources unless a demonstrated necessity is reported first.

## Implementer verification record (2026-09-15)

Selected before execution, workspace-root commands (Amiga flags from
`repos/fujinet-nio-driver/amiga/Makefile`):

```sh
source scripts/env.sh && cd repos/fujinet-nio-driver/amiga/tests && make build/test_fujinet_nio_packet_backend build/test_fujinet_nio_client_retry build/test_fujinet_nio_device && ./build/test_fujinet_nio_packet_backend && ./build/test_fujinet_nio_client_retry && ./build/test_fujinet_nio_device
source scripts/env.sh && m68k-amigaos-gcc -std=c99 -Wall -Wextra -Werror -O2 -mcpu=68000 -msoft-float -Irepos/fujinet-nio-lib/include -c repos/fujinet-nio-driver/amiga/nio.device/fujinet_nio_packet_backend.c -o /tmp/fujinet_nio_packet_backend.o
source scripts/env.sh && cd repos/fujinet-nio-driver/amiga/tests && make -B build/test_fujinet_nio_device build/test_fujinet_disk_resident && ./build/test_fujinet_nio_device && ./build/test_fujinet_disk_resident
source scripts/env.sh && git diff --check && git -C repos/fujinet-nio-driver diff --check
```

The forced broker/resident rebuild checks the two consumers of the extended
unified native Exec stubs. No deployed broker or serial implementation changes.
The initial integration compile exposed the old test-only `fn_platform.h`
shadowing the real library declarations; the target now includes actual
library headers before Exec stubs and defines the existing `__AMIGA__` guard.
No library edits were required.

Parent requested the full cheap Amiga native gate because Exec stub layouts
and declarations are shared. Selected before execution:

```sh
source scripts/env.sh && cd repos/fujinet-nio-driver/amiga/tests && make test
```

Parent separately reports 2026-09-15 V-CXX passed: 344 cases / 6,856 assertions,
2/2 build CTests including Python, and explicit 1/1 CTest. This is parent-provided
evidence, not a C++ run by this implementer.

### Results and coverage

All implementer gates passed on 2026-09-15 (exit 0): focused packet/retry/broker
executables; portable backend cross-compile with the exact 68000 command above;
forced broker/resident rebuild and executions; and full `amiga/tests make test`
(**11 executable targets**, including the newly registered packet target).
Final `make test` includes the reset-from-healthy correction, independent caller
buffers, missing-status structural fault, and completed-response policy cases.
The shared-stub consumers now declare header dependencies so later stub edits
also rebuild the resident and broker tests.

The integration target links the explicit unchanged sources listed above,
including actual `fn_raw.c`, `fn_transport.c`, `fujinet_nio_client.c`, common disk
retry, and broker worker. One compatible driver Exec stub tree is used for all
translation units. OpenDevice maps native pointer success to zero; DoIO submits
BeginIO and pumps the worker until exactly one ReplyMsg for its request/port.
There is no wrapped transport or substituted broker result. F1's older target
still uses its existing scripted transport and Linux archive; the new target
supplies the missing real-chain evidence separately.

| Spec row | Executed coverage |
| --- | --- |
| F1 regression | `test_retry_outputs_are_request_local_per_call`: script slots 0/1 then 2/3, exactly four transport calls/two attempts per caller, request replay bytes, diagnostics, reset inbound lengths, independent first-buffer preservation and guard bytes |
| Before send | `test_before_send` for disk read, raw, disk write: definite rejection then recovery; failed open then recovery; persistently unavailable peer then recovery; zero sends/effects for rejected attempts |
| After delivery | `test_fault_and_recovery(..., DELIVERY)` for all three paths: one send, zero initial effects, one independently pending exchange; caller retries reach backend but never peer |
| After effect | `test_fault_and_recovery` for LOST, CORRUPT, OVERSIZE, TRUNCATED, WRONG_DEVICE, WRONG_COMMAND, BAD_DESCRIPTOR, BAD_LENGTH, SHORT_HEADER, MISSING_STATUS; one effect, zero failed lengths, unchanged caller buffers |
| Lifecycle | Every fault sequence: broker close/lazy-open, actual transport close/open, failed/successful local reset, failed recovery, blocked later callers; `test_reset_from_healthy` verifies both reset success and failure newly quarantine a healthy endpoint |
| Late reply | DELIVERY/LOST sequences plus `test_independent_buffers`: peer completes after local reset, retains old same-device/command reply, refuses proof while stale delivery remains possible, later request cannot consume it |
| Recovery | Independently controlled peer completion/delivery barrier; proof availability alone leaves guard blocked; only explicit successful recovery allows own subsequent response; missing proof callback covered by `test_guard_capacity_and_proof` |
| Ownership | `test_aborts`, `test_queued_behind_unknown`, `test_independent_buffers`: queued/active aborts, completed versus pending abort outcomes, queued actual caller behind unresolved broker request, immutable requests, independent app buffers/sentinels, exactly one ReplyMsg per submitted IORequest, max pending one |

All fault/ownership families run for both real caller implementations, with
separate disk read and write runs (33 fault-and-recovery sequences). The peer
counts transfers, transmissions, effects, remote responses, late deliveries,
current/max pending work independently from caller attempts, backend entries,
and local replies. It never checks quarantine or refuses a send because old
work is pending; an unsafe backend would increase the remote pending count or
receive the old response. Its proof callback only observes independent state;
it does not clear pending work or old replies. Backend buffer-capacity and
missing-callback checks supplement, rather than replace, this integration.

### Final scope and limits for parent review

- Driver changes: F1 repair; portable `fujinet_nio_packet_backend.[ch]`;
  integration target and native Exec shims; README capacity, ownership and
  recovery obligations. No deployed broker/serial source or library source edits.
- Backend initializes quarantined and preserves uncertainty across lifecycle.
  Every local reset attempt quarantines even a healthy endpoint. The active
  guard rejects callback reentry; all calls still require serialized ownership.
  Adapter callbacks borrow buffers only until return and must obey bounds.
- `test_known_completion_policy` characterizes the unchanged actual raw caller:
  valid matching 11-byte reply with application capacity 10 causes exactly two
  attempts/transmissions/effects/replies, max pending one, no quarantine and no
  output copy. A literal canonical response fixture is checked independently.
  Valid U8 timeout/error/unknown statuses pass unchanged in one exchange.
  Completed active-abort replay is also characterized. This is not a promise
  to prevent every raw replay or duplicate application effect. Service/parser
  and application buffer policies remain unchanged.
- Physical adapter, physical quiescence mechanism and deployment are deferred.
  Callback proof obligations require independent adapter validation before use;
  tests establish the software boundary only. No guest gate was required, no
  hardware claim is made, and no toolchain/environment blocker occurred.
- Driver baseline: `342c5700d843901c6120a17b2620602995e6fd00`.
  Read-only library: `dac8bf66c4ec44841790e08021c1654379c21255` (clean).
  These are source baselines, not commits containing this uncommitted fix.
- Independent review, governing/firmware/backlog updates, Story 1.6 acceptance
  reassessment and commits remain parent-owned. This follow-up is in review;
  it does not mark 1.6 accepted. No staging, commits or pushes by implementer.

Workspace and driver `git diff --check` passed (exit 0). Implementation is
ready for parent independent review; no implementation tasks remain unchecked.

### Implementer independent-review patch verification (2026-09-15)

Applied the parent's single review-fix batch. Public backend operations handle
NULL; exchange zeros a supplied length before returning INVALID; close is a
no-op. Initialization copies callback configuration before clearing the backend,
including when the supplied callback table is `&backend.io`. Reset/recovery
open-or-closed lifecycle obligations are explicit in the header. Structural
acceptance and caller policies are unchanged.

Coverage added: all descriptor width codes 0–7, with and without a valid
continuation, through actual disk read/write and raw callers; truncated U16/U32
responses quarantining after one send/effect; nonzero-width descriptor chains at
the direct boundary; proof availability with independently pending work and no
late reply yet; startup open without recovery; exact lifecycle open/close counts
and opened state; full queued-response sentinel; IORequest identity completion
oracle and two queued requests sharing a port; NULL/alias initialization,
minimum/exact/maximum capacities and oversized requests; lifecycle callback
reentry while open and closed. Packet target prerequisites now include the
actual driver/common/public/library header directories and Exec/alib/DOS stubs.

The focused three executable command recorded above passed after this patch.
Remaining required reruns use these same previously recorded commands:

```sh
source scripts/env.sh && cd repos/fujinet-nio-driver/amiga/tests && make test
source scripts/env.sh && m68k-amigaos-gcc -std=c99 -Wall -Wextra -Werror -O2 -mcpu=68000 -msoft-float -Irepos/fujinet-nio-lib/include -c repos/fujinet-nio-driver/amiga/nio.device/fujinet_nio_packet_backend.c -o /tmp/fujinet_nio_packet_backend.o
source scripts/env.sh && git diff --check && git -C repos/fujinet-nio-driver diff --check
```

Review-patch results: focused packet/retry/broker executables passed; full native
`make test` passed all 11 executable targets; portable 68000 cross-compile
passed; workspace and driver whitespace checks passed (all exit 0). The added
48 valid-descriptor caller cases and six truncated-width fault sequences ran,
as did identity/shared-port, lifecycle reentry, startup, pending-proof and
capacity/NULL/alias boundary cases. No frozen contract, caller/library policy,
deployed serial code, or parent-owned acceptance/provenance documents changed.
No staging or commits. Review fixes are ready for parent verification.

## Final parent review and acceptance — 2026-09-15

The preceding implementer handoff describes the state before publication.
Parent review and all required patch verification are now complete. Driver
commit `e6f9686797f6bae256342d362795c4b3fc5b3da1` contains the reviewed fix;
firmware commit `cf2ab541c95d8769e67cb41541ca627db455e541` contains the reviewed
contract. Story 1.6 is accepted in its
[current decision record](stories/1-6-accept-the-canonical-software-packet-contract-for-bridge-design.md#technical-acceptance-record--2026-09-15),
which also pins the unchanged library and historical prerequisite evidence.
The resulting workspace commit is the immutable acceptance record. No push.

The blind, edge-case and verification-gap reviewers examined the complete
tracked/untracked diff. Accepted patch findings: alias-safe initialization and
NULL handling (medium); missing wider-field rejection regression cases (high);
startup/pending-proof/lifecycle assertions, per-request/shared-port completion,
whole-buffer sentinels, header dependencies, capacity boundaries and lifecycle
callback reentry (medium). All were fixed without changing the captured intent.
The independent contract review's ownership/status wording corrections were
also applied. No unresolved intent gap or deferred safety issue remains.

The parent reviewed the final source and verification results: the focused
three executables, all 11 native executables and 68000 cross-compile pass after
patches. Firmware gate: 344 cases / 6,856 assertions and 23 Python tests pass.
No library source or deployed serial change occurred. The six core fault rows
are before-send, after-delivery, after-effect, lifecycle, late-reply and recovery;
F1 and ownership are supplemental rows in this document's eight-row matrix.
There are now 39 fault/recovery sequences plus 48 valid-descriptor cases.

Final document validation is `source scripts/env.sh && python
/tmp/story-1-6-final-doc-check.py`, checking links/anchors, 25 dispatch entries,
checkpoint preservation, authorized frozen intent, acceptance/gate consistency
and exact owner revisions, followed by workspace/touched-owner whitespace
checks. No sprint-status file exists, so sprint synchronization is skipped.

Final document checks passed (exit 0): 30 local links/anchors, all 25 dispatch
entries, checkpoint/gate consistency, preserved authorized frozen intent,
accepted state and exact owner revisions. Workspace and touched-owner whitespace
checks passed. The checker is a temporary audit aid; committed code/tests and
the commands, revisions and decisions above are the durable evidence.

## Suggested Review Order

- Understand persistent quarantine and the adapter proof obligation.
  [fujinet_nio_packet_backend.h:1](../../../repos/fujinet-nio-driver/amiga/nio.device/fujinet_nio_packet_backend.h#L1)

- Follow validation and the transitions that permit another transmission.
  [fujinet_nio_packet_backend.c:1](../../../repos/fujinet-nio-driver/amiga/nio.device/fujinet_nio_packet_backend.c#L1)

- Read the accepted contract and its software scope.
  [native-packet-contract.md:188](../../../repos/fujinet-nio/docs/native-packet-contract.md#L188)

- Inspect real caller fault/effect and request completion evidence.
  [test_fujinet_nio_packet_backend.c:401](../../../repos/fujinet-nio-driver/amiga/tests/test_fujinet_nio_packet_backend.c#L401)

- Check the corrected second-call regression and independent buffers.
  [test_fujinet_nio_client_retry.c:330](../../../repos/fujinet-nio-driver/amiga/tests/test_fujinet_nio_client_retry.c#L330)

- Inspect the registered integration target and actual production sources.
  [Makefile:122](../../../repos/fujinet-nio-driver/amiga/tests/Makefile#L122)
