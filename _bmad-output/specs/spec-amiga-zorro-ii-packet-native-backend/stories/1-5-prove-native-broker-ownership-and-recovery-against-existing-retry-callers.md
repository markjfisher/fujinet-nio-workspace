---
title: '1-5 Prove native broker ownership and recovery against existing retry callers'
type: feature
created: '2026-09-11'
status: done
review_loop_iteration: 0
baseline_commit: '1ad2fad87304b0d987009c8f7cfd3a8ce1718e24'
context:
  - '{project-root}/AGENTS.md'
  - '{project-root}/_bmad-output/specs/spec-amiga-zorro-ii-packet-native-backend/execution-gates.md'
  - '{project-root}/_bmad-output/planning-artifacts/epics.md'
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** Story 1.5 must prove that the native broker owns request/response handling even when calls fail or retry, and that existing retry-capable callers do not observe stale ownership or reused responses.

**Approach:** Bind existing native test hooks to the current broker contract, extend broker tests for queue/abort/recovery ownership evidence, and add focused retry-caller evidence so the same retry policies are exercised through real disk-client retry code paths.

## Boundaries & Constraints

**Always:**
- Preserve single remote in-flight exchange behavior in `amiga/nio.device`; retain local FIFO queueing only.
- Keep request ownership strict: each broker IORequest gets one completion, one `fn_response_length`, and one error/result tuple.
- Separate transport outcome (`native` status/detail) from final broker result so unknown completion does not become stale success.
- Preserve existing retry policies in `fn_disk_retry_exchange` and `fn_raw_call`; do not claim safety by silently removing or weakening retry semantics.
- Use `CloseDevice`/`OpenDevice` boundaries as lifecycle signals, not as remote rollback/reopen side effects.
- Test all retry-path evidence with script-based or instrumented doubles so stale or cross-request buffers would fail deterministically.

**Ask First:**
- Any required production retry-policy changes beyond instrumentation or existing contract evidence.
- Any ambiguity we choose to document as a scope-blocking incompatibility if unsafe behavior is found with untouched retry callers.

**Never:**
- Change existing retry logic in `fn_disk_retry_exchange`/`fn_raw_call` as a workaround.
- Treat `IOERR_ABORTED`/`FN_ERR_TIMEOUT`/`FN_ERR_TRANSPORT` as equivalent completion or auto-cleared as recovered without measured evidence.
- Introduce new transport/failover layers or correlation fields outside this story’s acceptance.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|---------------|---------------------------|----------------|
| Concurrent queue + abort | Three queued EXCHANGE requests with `in_progress` request and one mid-queue queued request aborted | Each remaining request receives exactly one completion with correct request-specific buffer ownership | Queued abort returns `FN_ERR_ABORTED` on that request only; other requests proceed after prior completion |
| In-progress close retry | In-progress request returns transport/timeout-like failure while backend is reopened on next exchange | Backend state stays recoverable; next request is executed only after reopen path and returns clean result | Backend-close state is observable in open count and exchange count; no request is silently completed as success |
| Local close during in-flight | Request remains in progress, `CloseDevice` called on another IORequest | In-progress request is not rollback-aborted by close; it is completed exactly once | Close may defer expunge but must not change in-flight request ownership |
| Abort + subsequent retry on same semantics | A request gets `AbortIO` during in-progress and is retried as a fresh call | Retry request is independent and not influenced by aborted caller state | Aborted request returns `IOERR_ABORTED` and zero-length response; retry request runs normally |
| Backend failure before send | Backend returns `FN_ERR_TRANSPORT` with detail marker, first call | Failure stays per-request and does not leak into unrelated queued calls | `fn_response_length` remains zero for failed call; broker moves to next request without aliasing payload |
| Retry policy replay boundary | Retriable disk sector request is retried by caller-facing retry wrapper, with multiple scripted transport attempts | Retry wrapper may transmit multiple identical packets, and diagnostics capture attempts and per-attempt causes/natives | Non-retryable commands never exceed one attempt; retry result never invents a reply payload |

</frozen-after-approval>

## Code Map

- `repos/fujinet-nio-driver/amiga/tests/test_fujinet_nio_device.c` -- extend native broker harness and add ownership/recovery tests for queued/in-progress abort, close boundary, and no stale reply cross-attribution.
- `repos/fujinet-nio-driver/amiga/tests/test_fujinet_nio_client_retry.c` -- add focused V-RETRY evidence for ambiguous/failure-before-success and diagnostics capture in existing retry caller path.
- `repos/fujinet-nio-driver/amiga/nio.device/fujinet_nio_device.c` -- read-only in execution unless a failing test proves queue/ownership mismatch.
- `repos/fujinet-nio-driver/amiga/channels/rs232/fujinet_nio_client.c` -- read-only reference for current `fn_disk_client_context_t` diagnostics hookup and retry attempt recording.
- `repos/fujinet-nio-driver/common/fujinet_disk_retry.c` -- read-only evidence source for retry attempt limits and transport-result handling.
- `repos/fujinet-nio-driver/amiga/include/fujinet_disk_driver.h` -- read-only for `fujinet_nio_disk_context_t` retry + exchange diagnostics fields.

## Tasks & Acceptance

**Execution:**
- [x] `repos/fujinet-nio-driver/amiga/tests/test_fujinet_nio_client_retry.c` -- add regression tests that prove retries on transport-like failures are attempt-bounded, response buffers remain request-local, and diagnostics record each attempt.
- [x] `repos/fujinet-nio-driver/amiga/tests/test_fujinet_nio_device.c` -- add broker ownership/recovery tests for abort ordering, in-flight close/reopen paths, queue continuity, and one-reply-per-request behavior under mixed failures.
 - [x] `repos/fujinet-nio-driver/amiga/tests/Makefile` -- add any new test target or fixture file if introduced; keep existing test set unchanged otherwise.

**Acceptance Criteria:**
- Given multiple queued EXCHANGE requests with one abort and one close/open boundary interleaving, when the broker drains requests, then each request gets one completion, the right caller buffer is populated, and failed/aborted requests keep `fn_response_length == 0`.
- Given retriable disk sector transport errors in `fn_disk_retry_exchange`, when `fujinet_nio_client` replay logic runs, then each attempt is captured in diagnostics and late/failed attempt response data is never promoted to success on earlier attempts.
- Given an in-progress failure path and caller-triggered close/open retry, when the next exchange runs, then backend reopen/close transitions are explicit and there is no stale-response ownership carryover between request objects.

## Design Notes

Use broker-level tests as the ownership oracle: the same device harness already permits queued abort, delayed abort/close callbacks, and explicit in-progress vs queued state checks. Extend that harness with the minimum additional knobs needed to encode scripted multi-state backend outcomes and observe exchange counts per scenario, then keep production logic unchanged unless a test exposes an ownership/regression gap.

Retry evidence should come from the existing caller-facing retry path, because that is the actual production contract that cannot be refactored away. The goal is not to prove no retries exist; it is to prove retries remain request-local and cannot produce cross-request misattribution.

## Verification

**Commands:**
- `cd /home/markf/dev/nio/fujinet-nio-workspace/repos/fujinet-nio-driver/amiga/tests && make build/test_fujinet_nio_device` -- expected: compile succeeds with new assertions.
- `cd /home/markf/dev/nio/fujinet-nio-workspace/repos/fujinet-nio-driver/amiga/tests && ./build/test_fujinet_nio_device` -- expected: all broker ownership/recovery checks pass.
- `cd /home/markf/dev/nio/fujinet-nio-workspace/repos/fujinet-nio-driver/amiga/tests && make build/test_fujinet_nio_client_retry` -- expected: retry path compile succeeds with new cases.
- `cd /home/markf/dev/nio/fujinet-nio-workspace/repos/fujinet-nio-driver/amiga/tests && ./build/test_fujinet_nio_client_retry` -- expected: retry evidence includes attempt counts, response-length clearing, and bounded attempts.

Execution results:
- `source /home/markf/dev/nio/fujinet-nio-workspace/scripts/env.sh && make build/test_fujinet_nio_device && ./build/test_fujinet_nio_device` passed.
- `source /home/markf/dev/nio/fujinet-nio-workspace/scripts/env.sh && make build/test_fujinet_nio_client_retry && ./build/test_fujinet_nio_client_retry` passed.

## Review outcome and final verification

### Verification-gap review

No verification gaps found.

## Suggested Review Order

- Confirm request-local retry diagnostics and attempt recording before retry policy branching.
  [test_context_diagnostics_records_retry_attempts:275](../../../../repos/fujinet-nio-driver/amiga/tests/test_fujinet_nio_client_retry.c#L275)

- Confirm request-local replay buffers remain isolated across multiple caller invocations.
  [test_retry_outputs_are_request_local_per_call:330](../../../../repos/fujinet-nio-driver/amiga/tests/test_fujinet_nio_client_retry.c#L330)

- Confirm broker abort semantics preserve queued request ownership and prevent stale completion.
  [test_abort_queued_middle_request_preserves_ownership:587](../../../../repos/fujinet-nio-driver/amiga/tests/test_fujinet_nio_device.c#L587)

- Confirm timeout recovery leaves failed request state closed while retries reopen cleanly.
  [test_transport_timeout_recover_and_retry_request:840](../../../../repos/fujinet-nio-driver/amiga/tests/test_fujinet_nio_device.c#L840)

- Confirm in-progress close does not abort active request and does not leak buffers to next queue entry.
  [test_close_does_not_abort_in_progress_then_next_request:925](../../../../repos/fujinet-nio-driver/amiga/tests/test_fujinet_nio_device.c#L925)

- Sweep the updated test mains to verify all new assertions are executed.
  [test_fujinet_nio_client_retry.c:595](../../../../repos/fujinet-nio-driver/amiga/tests/test_fujinet_nio_client_retry.c#L595)
  [test_fujinet_nio_device.c:1011](../../../../repos/fujinet-nio-driver/amiga/tests/test_fujinet_nio_device.c#L1011)
