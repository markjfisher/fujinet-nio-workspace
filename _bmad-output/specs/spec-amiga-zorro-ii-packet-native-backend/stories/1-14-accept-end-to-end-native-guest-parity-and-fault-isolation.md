---
title: '1-14 Accept end-to-end native guest parity and fault isolation'
type: feature
created: '2026-09-17'
status: done
execution_gate: satisfied
contract_acceptance: accepted
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

Workspace-relative. Implementer owns this story's driver, firmware-test and workspace harness changes; you are not alone in the codebase, do not revert others' edits. Leave library/public ABI, production serial and service handlers unchanged.

- `repos/fujinet-nio-driver/amiga/nio.device/fujinet_nio_directory_backend.{c,h}`: replace false `directory_quiesce` proof and unconditional reopen recovery; retain actual packet guard. Add test-only sideband controls and durable ambiguity latch; adapt `amiga/tests/test_fujinet_nio_directory_backend.c` and its Makefile coverage.
- `repos/fujinet-nio/tests/directory_packet_io.{h,cpp}`, `native_test_runner.cpp`: implement host barrier between synchronous `core.tick()` calls. Inject delayed/lost actual service replies at packet delivery, not fake handlers. `src/lib/io_service.cpp::serviceOnce` is read-only drain evidence. Extend `test_native_test_endpoint.cpp` for subprocess freshness/restart/barrier faults.
- Runner registers only File/Clock/Disk; add real Host/application-state registrations following read-only `src/app/main_posix.cpp:231` for catalogue/mappings. Update `native_test_records.h` only as needed for matching tests.
- Driver `amiga/tools/fujinet-nio-native-test-probe.c`, new focused fault probe beside it, `amiga/Makefile`: real guest asynchronous EXCHANGE callers, distinct buffers and completion accounting; actual retry callers where needed. Existing `amiga/tests/test_fujinet_nio_packet_backend.c` supplies accepted actual-caller coverage to extend with directory adapter regression where appropriate.
- `integration-tests/amiberry/conftest.py::run_amiga_case`: accept explicit install selection, separate evidence directories, reuse app/MountList/media setup. Native host root is `native-test-records/host-fs`; do not delete prepared fixtures. Preserve native_disk_fixture semantics. Handle second boot completion and mapping extraction for selected backend.
- Existing `test_diskdevice_fmount.py`, `test_diskdevice_adf.py`, `test_diskdevice_fmount_restore.py`: parameterize focused nodes listed below, preserving assertions and startup semantics. `test_nio_native_test.py` has accepted tool/list/clock/disk oracles; extend serial/native comparison and real guest faults. `tests.toml`, `startup/`, `test_harness_completion.py`: register and verify narrowly scoped startup/completion handling.
- Owner docs `repos/fujinet-nio/docs/native-packet-contract.md` and driver `amiga/README.md`: record test-only recovery procedure/limits. Historical diagnostic: `../evidence/1-14/initial-hold.md`; preserve original defect evidence without claiming it passes against repaired code.

## Tasks & Acceptance

- [x] Audit prerequisites and reproduce/review directory safety defect; user approved repair.
- [x] Implement peer barrier, freshness, durable quarantine and explicit recovery; test stale/missing ACK, interruption/restart, delayed work and no retry replay.
- [x] Register real catalogue/mapping services; parameterize existing guest assertions and test harness edge cases.
- [x] Run guest tool/media parity plus queued/lost/delayed fault recovery with independent backing bytes and transmission/effect counts.
- [x] Run all targeted gates, review, record exact revisions/component limits and commit locally; never push.

Given separate serial/native installations, when acceptance operations run, then identical service/media assertions pass without native serial setup. Given ambiguous completion and queued/retrying callers, when close/open or delayed replies occur, then no unsafe resend/stale completion occurs; explicit independently proven recovery permits fresh work.

## Spec Change Log

- 2026-09-17: User explicitly approved the test-only peer-acknowledged recovery mechanism after the recorded hold. Continue the complete 1.14 objective without routine checkpoints.

## Design Notes

Host owns one exclusive directory, fresh boot nonce and rotating barrier challenge. Guest requests current challenge; host processes between synchronous ticks, drains old work/held delivery and packet files, rotates challenge before ACK. Guest accepts only its current ACK. Interrupted/restarted participants must fail closed on stale controls. No FujiBus transaction field.

Barrier alone must NOT auto-recover unknown writes: broker retries close/reopen after transport error. Persist an ambiguity marker before send, clearing only after validated completion or proven pre-send rejection. Retain it across close/open and guest reload. Unknown completion requires explicit test-operator authorization bound to the fresh challenge, consumed once after prior callers have finished; then peer barrier clears quarantine. Initial healthy startup also needs the barrier. No higher-layer retry changes. Failures publishing/clearing safety state fail closed. Explain operator procedure and enforce isolated callers during recovery.

## Verification

Source `scripts/env.sh` first. Required owner gates (record actual results):

- `make -C repos/fujinet-nio-driver/amiga/tests test`
- `make -C repos/fujinet-nio-driver/amiga native` (includes changed/new guest probes and native-test device; verify readable toolchain headers and map omits serial/session/SLIP).
- `cd repos/fujinet-nio && ./build.sh -cp fujibus-pty-debug && ctest --test-dir build/fujibus-pty-debug --output-on-failure`
- `uv run --project integration-tests/amiberry pytest integration-tests/amiberry/test_harness_completion.py`
- `scripts/amiga-tests --amiga-env wb32 --amiga-machine a1200-030 test_nio_native_test.py test_nio_paula_serial.py` (include newly registered fault nodes and both selected tool installations).
- `scripts/amiga-tests --amiga-env wb32 --amiga-machine a1200-030 test_diskdevice_fmount.py::test_fmount_fumount_standard_adf test_diskdevice_fmount.py::test_hd_stage8_replacement_and_writable_durability test_diskdevice_adf.py::test_standard_adf_mount_info_read_dir_and_type test_diskdevice_adf.py::test_catalog_inspection_preserves_live_dd_handler test_diskdevice_fmount_restore.py::test_fmount_fumount_persisted_dd_hd_restore test_diskdevice_fmount_restore.py::test_invalid_persisted_mapping_fails_without_creating_node` (each selected node runs separate serial/native installs).
- `git diff --check` in every touched owner. Add exact new focused test commands here before running them. No library edits planned; any actual library edit mandates complete `make check`.

No sprint-status file exists. Historical baseline is preserved; approved-repair start workspace revision is `7f1a2dce4385114527956f1a2d72612989eee53c`. Actual guest/media results and independent workflow review are required before marking done.


### Focused repair verification commands

After sourcing `scripts/env.sh`:
- `repos/fujinet-nio/build/fujibus-pty-debug/tests/fujinet-nio-tests --test-suite=native_test_endpoint`
- `scripts/amiga-tests --amiga-env wb32 --amiga-machine a1200-030 test_nio_native_test.py::test_native_fault_isolation`
- `scripts/amiga-tests --amiga-env wb32 --amiga-machine a1200-030 test_diskdevice_fmount.py::test_fmount_fumount_standard_adf`


## Review record — 2026-09-17

Independent blind, edge-case and verification-gap reviews completed against the
complete workspace/driver/firmware diff. Deduplicated actionable findings were
implementation patches within the approved recovery contract:

| Finding | Severity / route | Resolution |
| --- | --- | --- |
| Control publication could block on a FIFO or follow a symlink | high / patch | Nonblocking, no-follow open and regular-file check before truncation; regression tests |
| Startup retained old fault/release controls | medium / patch | Retire both after acquiring exclusive ownership; restart test |
| Unused release could affect a later held response | medium / patch | Consume unused release; barriers retire controls; focused host tests |
| Permission deposited during healthy traffic survived into a future failure | high / patch | Retire permission before healthy sends; timeout/reopen regression |
| Duplicate subprocess helper could erase live readiness | medium / patch | Lock before clearing identity; duplicate uses normal helper and preserves identity |
| Known completion with failed marker cleanup lacked coverage | high / patch | Independent peer injects unremovable marker temporary; current success/exact bytes retained, future sends/reopen blocked |
| Tool parity did not decode directory entry fields | medium / patch | Independent filename/type/count/size checks for both installations |
| Held real reply was drained but not released into a quarantined guest | high / patch | Guest observes actual late reply before retry; retry still fails with zero response and no extra service write |
| Second-boot monitor lacked focused regression tests | medium / patch | Shared monitor tested for old marker offset, split input, peer exit and guest reset precedence |
| Historical reproducer silently compiled against repaired sources | low / patch | Explicit clean-baseline check; preserved original defect evidence |

Recovery is scoped to the explicitly isolated test session. The fault probe joins
both queued requests and waits for the actual resident retry loop to finish
before it publishes permission. The adapter cannot establish that an arbitrary
operator has stopped unrelated external callers; the owner procedure states
that precondition. Host restart freshness/persistent-marker behavior is tested
with the real runner; fresh adapter executable reload and interrupted recovery
are separately tested with an independent synthetic peer. No combined live
Amiga/host-crash recovery claim is made. These boundaries do not weaken the
required guest delayed/lost-reply and actual retry-containment checks.


## Component and acceptance evidence

Prerequisites: accepted 1.6 portable packet contract and the 1.10–1.13 guest/tool/
host-parity acceptance records. Investigation of completed work was limited to
the independently reproduced directory-adapter stale-response defect. The
portable guard acceptance remains unchanged; the incompatible test adapter is
repaired under the user's explicit approval.

Real guest components are the cross-compiled exchange tool, broker, public
`fn_raw_call` caller, resident DiskDevice and its unchanged three-attempt retry
loop, normal FMOUNT/FUMOUNT/FMountRestore commands, MountLists and Amiga OS
handlers. Host parity uses real File, Clock, Disk, Host, AppStore and SlotCatalog
services with disposable, independently initialized ADF files. The fault shim
holds/drops the response **after** the real service executes. Whole-image byte
comparisons, decoded response payloads and host request logs are independent
oracles, not serial/native result equality alone.

The connection is the test-only directory transport through Amiberry's host
filesystem. Amiberry emulates Amiga CPU/OS/hardware. Host adapter unit tests use
Exec stubs and an independently scheduled synthetic packet peer; runner tests
use the real core in an independent subprocess. No RP2350B, physical Zorro bus,
ESP32-S3 link, electrical behavior, hardware ABI, hardware recovery, performance
or host power-loss persistence is validated here. Library/public ABI, production
serial transport, service handlers and higher-layer retry policies are unchanged.

The two queued callers each complete once with distinct unchanged buffers and
zero response lengths under ambiguity. Actual `fn_raw_call` retries transmit no
additional write. The resident loop makes all three attempts, returns error 20
and actual length zero, while the core receives exactly one write. Independent
backing bytes show that this timed-out write did execute. Following joined
callers, consumed operator permission and fresh peer proof, read/flush expose
that exact result; a fresh same-command write to a different LBA receives its
own acknowledgment and changes only its expected sector. The hold case also
publishes the actual old response into the guest mailbox before the blocked
retry; the later fresh call cannot consume it. The resident hold case separately
exercises draining an undelivered held response.


### Final verification results

Commands are listed in Verification above; all builds/tests source the shared
environment. Final logs are retained locally in `test-evidence/story114-final/`.

| Gate | Result |
| --- | --- |
| Driver Amiga native test suite | PASS, including persistent ambiguity, late same-command reply, interrupted recovery, premature permission and cleanup-failure regressions |
| Driver Amiga cross-build | PASS; toolchain headers readable; actual guest probes/device built |
| Firmware `fujibus-pty-debug` build and CTest | PASS: 383 C++ cases, 12,946 assertions; 3/3 CTest targets including clock isolation and Python tools |
| Harness completion pytest | PASS: 25 tests |
| Actual guest tools/faults plus Paula serial reference | PASS: 8 cases, 87.43 seconds |
| Selected actual guest media/lifecycle cases | PASS: 12 serial/native cases, 164.13 seconds |
| Whitespace checks in workspace, driver and firmware | PASS |
| Historical diagnostic shell syntax | PASS; diagnostic is explicitly baseline-only |

Final tool/fault evidence: `test-evidence/amiberry-20260917-134016/`.
Committed compact fault evidence: [held-response guest output](../evidence/1-14/guest-hold.txt),
[dropped-response guest output](../evidence/1-14/guest-drop.txt), and
[host request sequence and whole-image SHA-256 effects](../evidence/1-14/fault-effects.json).
An earlier complete media pass is in `test-evidence/amiberry-20260917-132817/`;
the final rerun covers review patches and the second-boot monitor tests.

During development, an incorrect source-env path and an overlapping firmware
rebuild failed; both were corrected and sequential final commands above passed.
The initial guest probe also required `fn_init()` after explicitly closing its
library transport; the corrected probe is the one exercised in final evidence.
No unavailable toolchain or skipped required verification remains.

Unchanged dependencies: library `dac8bf66c4ec44841790e08021c1654379c21255`,
core apps `cdb026d28f53254459824591ec6439db108804e6`. No library edit was made;
complete library `make check` was therefore not required.


## Technical acceptance — 2026-09-17

**ACCEPTED: Story 1.14 software guest parity and fault isolation.** All required
I/O-matrix rows have passing actual guest or focused failure evidence, including
real retry callers and independent transmission/backing effects. The approved
test-only peer acknowledgment repair closes the initial adapter safety hold.
No higher-layer retry change, public protocol change or unresolved safety
tradeoff remains within the isolated-session contract.

Final media evidence is `test-evidence/amiberry-20260917-134154/`. Its 12 cases
retain the existing standard DD/HD read/geometry/content, independent-drive,
catalogue preservation, replacement/eject/remount, writable durability,
persisted restoration and invalid-mapping assertions for both installations.
Native map/guest tests confirm no serial/session/SLIP linkage; the separate
Paula serial case remains passing.

Accepted owner revisions:
- Driver: `99ff749083c10711c53c4c87ac1550be5e39cb3e`.
- Firmware/test peer: `2365fbce15391ae445f38962909ab8c8f172d84e`.
- Workspace implementation/acceptance: the local commit containing this record,
  based on `7f1a2dce4385114527956f1a2d72612989eee53c` (original story baseline and
  unchanged dependency revisions are above). All commits remain local.

This satisfies the **1.14** prerequisite only. Hardware stories still require
approved 2.4, positive physical feasibility evidence, suitable hardware and their
own execution gates. The active multi-epic spec remains in `specs/` because its
physical work is not complete. No sprint-status file exists to synchronize.

## Suggested Review Order

**Recovery ownership**

- Require consumed operator permission and fresh peer proof before clearing ambiguity.
  [fujinet_nio_directory_backend.c:638](../../../../repos/fujinet-nio-driver/amiga/nio.device/fujinet_nio_directory_backend.c#L638)

- Drain real service delivery between synchronous ticks, then rotate the challenge before acknowledgment.
  [directory_packet_io.cpp:152](../../../../repos/fujinet-nio/tests/directory_packet_io.cpp#L152)

**Guest acceptance**

- Join queued callers, observe late replies, and exercise actual raw and resident retries.
  [fujinet-nio-native-fault-probe.c:106](../../../../repos/fujinet-nio-driver/amiga/tools/fujinet-nio-native-fault-probe.c#L106)

- Select isolated installations while preserving media fixtures and existing acceptance assertions.
  [conftest.py:838](../../../../integration-tests/amiberry/conftest.py#L838)

- Verify independent backing bytes, exact service transmissions and fresh response ownership.
  [test_nio_native_test.py:159](../../../../integration-tests/amiberry/test_nio_native_test.py#L159)

**Supporting checks**

- Preserve known success when marker cleanup fails, while quarantining future calls.
  [test_fujinet_nio_directory_backend.c:595](../../../../repos/fujinet-nio-driver/amiga/tests/test_fujinet_nio_directory_backend.c#L595)

- Check subprocess freshness, held-reply drainage, exclusive ownership and restart persistence.
  [test_native_test_endpoint.cpp:636](../../../../repos/fujinet-nio/tests/test_native_test_endpoint.cpp#L636)

- Reject stale completion and preserve split-input state on the second boot.
  [test_harness_completion.py:293](../../../../integration-tests/amiberry/test_harness_completion.py#L293)

- Document explicit recovery procedure and software-only evidence limits.
  [README.md:257](../../../../repos/fujinet-nio-driver/amiga/README.md#L257)
