---
title: '1-14 Accept end-to-end native guest parity and fault isolation'
type: feature
created: '2026-09-17'
status: draft
execution_gate: hold
baseline_commit: fe58a9117b79f501ab77aed8039e586a257e4143
owner_baseline_commit: 1c37a6abe08556b57888bef8dcde4efd8ba6d564
firmware_baseline_commit: 298e201fbb1f6b744ec607f8a17ee8adbaa2b11a
review_loop_iteration: 0
spec_checkpoint: false
done_checkpoint: false
context:
  - '{project-root}/docs/agent-test-policy.md'
  - '{project-root}/docs/amiga/amiberry-testing.md'
---

<frozen-after-approval reason="approved Story 1.14; routine checkpoints disabled, safety gates retained">

## Intent

**Problem:** Host parity and individual native guest operations do not establish complete guest/resident media parity and fault isolation.

**Approach:** Run the actual exchange tool and resident device against real core services in independently installed serial-reference and native-test environments. Retain existing semantic/media assertions and demonstrate induced failure followed by safe recovery.

## Boundaries & Constraints

**Always:** Preserve public ABI, service semantics, existing retries, independent slots, DD/HD ADF support and disposable-write protections. Read prerequisite acceptance records; investigate completed implementation only for a demonstrated regression. Name real, mocked and hardware-unvalidated components. Owner changes require demonstrated integration defects.

**Ask First:** An incompatible adapter recovery contract, higher-layer retry changes, or unresolved safety tradeoff. Execution gates require stopping on unsafe findings.

**Never:** Substitute canned responses for service parity; claim hardware readiness; infer quiescence from timeout, reopen or empty local files; introduce request correlation fields; use serial controls or fallback on native execution; push.

## I/O & Edge-Case Matrix

| Input/state | Required result |
|---|---|
| Separate serial/native installs; file/clock/disk tool operations | Same independent service assertions; native uses no serial transport/controls |
| DD/HD, independent drives, catalogue, replacement/eject/remount/restoration | Existing semantic/media assertions retained, independent backing effects |
| Delayed/lost response and queued callers | No stale attribution, unsafe replay or concurrent remote exchanges |
| Recovery after ambiguity | Independent quiescence evidence before new work; explicit component/evidence limits |

</frozen-after-approval>

## Code Map

- `integration-tests/amiberry/conftest.py:825`: parameterize `run_amiga_case` installation without changing assertions; separate evidence directories. Native broker selection exists at 858. Current broker-only path excludes ordinary app directories/MountLists (950/984); lifecycle cases need those artifacts. Mapping extraction (1464) assumes serial storage.
- `integration-tests/amiberry/test_diskdevice_fmount.py`: reuse `test_fmount_fumount_standard_adf` and `test_hd_stage8_replacement_and_writable_durability` for replacement/durability.
- `integration-tests/amiberry/test_diskdevice_adf.py`: reuse `test_standard_adf_mount_info_read_dir_and_type` and `test_catalog_inspection_preserves_live_dd_handler` for independent drives/catalogue. Restoration needs its existing focused node as well before final acceptance.
- `integration-tests/amiberry/test_nio_native_test.py`: accepted actual-tool read-only and disposable-disk cases; preserve complete backing-byte expectations.
- `repos/fujinet-nio/tests/native_test_runner.cpp:169`: currently registers File/Clock/Disk only. Catalogue/mappings need real application-state services and dependencies; reference `src/app/main_posix.cpp:231`. No production service redesign is planned.
- `repos/fujinet-nio-driver/amiga/nio.device/fujinet_nio_directory_backend.c:585`: false quiescence proof; `backend_open:645` calls recovery on every open.
- `repos/fujinet-nio-driver/amiga/nio.device/fujinet_nio_packet_backend.c`: accepted guard correctly delegates proof; it cannot distinguish a late same-device/command response after the adapter falsely reports quiescence.

## Tasks & Acceptance

- [x] Read approved story/gates and prerequisite acceptance records; inspect integration seams.
- [x] Reproduce and independently review suspected directory-adapter safety regression.
- [ ] Resolve recovery contract gate before implementation planning is ready.
- [ ] Complete exact focused verification plan, implement parameterized guest parity and real service registration, and test each touched owner.
- [ ] Exercise actual guest faults/queued callers and safe recovery; record technical acceptance and commit implementation locally.

Given separate serial/native deployments, when acceptance operations run, then identical semantic/media assertions pass without native serial use. Given delayed/lost replies and queued callers, when failure/recovery runs, then no stale reply completes a later request and ambiguous operations are not unsafely replayed.

## Spec Change Log

## Design Notes

Prerequisites remain recorded done: 1.6 accepts the portable guard with an independently valid adapter proof; 1.10 accepts basic directory guest operation; 1.11/1.12 accept individual tool operations; 1.13 accepts host catalogue/lifecycle parity. This newly demonstrated adapter regression is the exception permitting focused investigation of completed work. It does not invalidate the portable guard acceptance or establish guest/physical acceptance.

## Verification and execution hold — 2026-09-17

**Decision: HOLD. Story 1.14 is incomplete.** Planning stopped at the explicit unsafe-finding gate, before bmad-build implementation/review steps. No routine approval checkpoint is being introduced.

Executed workspace diagnostic (sources `scripts/env.sh`, compiles actual owner sources unchanged):

```sh
bash _bmad-output/specs/spec-amiga-zorro-ii-packet-native-backend/evidence/1-14/reproduce.sh
```

Observed:

```text
first_result=16 first_length=0
reopen_result=0 second_result=0 second_length=8 stale_tag=a1 peer_exit=0
```

**Exit 0 means the defect was reproduced, not that safety passed.** The independently scheduled child consumes request A and holds a synthetic canonical response outside mailbox files. A times out with FN_ERR_TRANSPORT. Close/open removes files and falsely releases quarantine. After B is submitted, the child atomically publishes A's retained response; B returns FN_OK with A's tag. There is no timing-only release: a pipe releases the peer after reopen, and it waits for B's request file before publication. Production transfer timeout is reduced to 100 ms for the host diagnostic.

Real: directory adapter, packet guard, packet checksums. Linked broker code supplies existing harness symbols but this probe calls the backend directly; it does **not** establish broker/queued-caller, actual retry-caller, Amiga guest or real-service results. Mocked: Exec environment and synthetic independently scheduled peer/response. No media is written, no real services or hardware are involved. An independent reviewer confirmed the proof violates the adapter callback contract and approved stale-response requirement.

The initial temporary probe ran after an environment-source error (`NIO_WORKSPACE` unset). The retained script explicitly exports the workspace root and successfully sources the environment before compiling/running; the output above is from that corrected execution.

`bash -n` on the retained script and workspace `git diff --check` are the other targeted checks. No owning repository files changed; no library change or `make check` requirement. Guest acceptance is intentionally unrun while the safety gate is open.

### Required recovery decision

Recommended next scope: repair the test-only guest/host adapter with independently acknowledged quiescence, then resume this story. Keep public FujiBus, retry callers and production serial behavior unchanged. A recovery acknowledgment must prove the old host work/delivery is drained; local file deletion is insufficient. The design must handle stale acknowledgments and interrupted recovery without clearing quarantine. This is a test-facility recovery contract, not a bridge ABI or per-request correlation field.

Alternative: keep the failed session permanently quarantined and require a coordinated host/guest restart into a fresh isolated directory. That is simpler but changes the recovery workflow and must be explicitly accepted before being used to satisfy the story.

Gate authority: [execution-gates.md](../../execution-gates.md) says “missing prerequisites or unsafe findings always stop work”; [SPEC.md](../../SPEC.md) says “an incompatible later adapter still requires scope review.” These are the reason for the decision request. No dependent physical implementation is released.
