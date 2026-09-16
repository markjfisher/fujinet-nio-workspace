---
title: Restore deterministic Amiga suite serial transport
type: bugfix
created: 2026-09-16
status: done
baseline_commit: ddcdff329bbf41cbf7a7ccc96c5abf322fbf515a
review_loop_iteration: 0
context: []
---

<frozen-after-approval reason="User explicitly authorized continuation of interrupted repair and removal of speculative workarounds">

## Intent

**Problem:** The Amiga FFS mount test fails despite firmware mount success. Previous uncommitted changes mask the failure with reduced inspect requests, cached catalogue resolution, and changed persistence semantics. The full suite must run through the same public wrapper.

**Approach:** Capture the rejected frame and serial configuration, fix the demonstrated transport initialization regression, remove unsupported changes, and validate the original command flows and complete suite.

## Boundaries & Constraints

**Always:** Preserve strict packet validation, 512-byte inspect contract, catalogue freshness, mapping failure behavior and custom serial device pre-open configuration. Source workspace environment before tests. Record evidence distinguishing observations from hypotheses. Commit completed changes, never push.

**Ask First:** Broader product behavior changes beyond repairing these regressions.

**Never:** Introduce retries, mount recovery from inspect/Info, advisory packet lengths, reduced replies, skipped application steps, or silently ignored errors merely to pass tests. No hardware RS232 redesign.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected behavior | Error handling |
|---|---|---|---|
| Stock serial open | OpenDevice replaces requested parameters with defaults | Reapply baud, buffer, 8N1 and binary flags before SETPARAMS | Existing open/parameter errors retained |
| Custom serial open | Device needs baud at claim time | Requested settings available before open and at SETPARAMS | Existing cleanup retained |
| FFS mount | FHOST, FIN, 512-byte inspect and 19-byte mount reply | Successful mount and KNOWN.TXT directory entry | No recovery path |
| Mapping failure | Read-only mappings store | Existing failure semantics retained | Must not silently succeed |
| Wrapper selection | Exact relative pytest node or no node | One test or complete Amiberry suite | Pytest status propagated |

</frozen-after-approval>

## Code Map

- `repos/fujinet-nio-driver/amiga/nio.device/fujinet_nio_serial_backend.c:backend_open` initializes IOExtSer before OpenDevice but never restores parameters afterward. Commit `62168e9d509c20ca12a1060b74b89aceca22cdce` moved configuration before open on September 7.
- `test-evidence/amiberry-20260916-232137/amiga-fin-ffs-adf/session-raw.log`: debugger observes pre-open baud=19200/rbuf=2112/flags=90, pre-SETPARAMS baud=9600/rbuf=512/flags=00. Earlier run `amiberry-20260916-232035` captures mount raw bytes `c0 fc 01 00 04 01 00 01 03 00 00 01 04 00 02 e0 06 00 00 c0`: missing header byte 13. Completion response similarly loses byte 11. These are XOFF/XON.
- `repos/fujinet-nio-lib/src/common/fn_session.c`: exact decoded/header length check agrees with firmware; pending empty-frame skip is not this failure.
- `repos/fujinet-nio-lib/src/common/fn_disk.c`: pending 16-byte inspect replaces established 512-byte request.
- `repos/fujinet-nio-driver/amiga/disk.device/fujinet_disk_device.c`: pending cache and persistence changes need removal; HEAD is the established behavior.
- `repos/nio-core-apps/apps/platform/amiga/fmount.c`: pending diagnostic output can revert to HEAD.
- `integration-tests/amiberry/{conftest.py,startup/amiga-fin-ffs-adf.sequence,test_amiga_fin_ffs_adf.py}`: inherited skipped FHOST and boot-block modifications need removal; preserve safe skip of Dir when mount fails.
- `scripts/amiga-tests`: run pytest in suite directory; existing pytest testpaths already defaults to complete suite.

## Tasks & Acceptance

**Execution:**
- [x] Driver serial backend: use one small parameter-setting helper before OpenDevice and again immediately before SETPARAMS; document overwritten defaults. Preserve custom-device configuration and existing lifecycle.
- [x] Restore inherited product workarounds to HEAD in library's four modified files, disk resident source, and FMOUNT source. Their incoming patches are preserved under `/tmp/amiga-suite-inherited-changes/`. Do not revert any other files.
- [x] Workspace harness: restore FHOST and relative FIN, original assertion and original FFS fixture, retain Dir guard, simplify wrapper default collection. Remove temporary debugger hook from run.py.
- [x] Run focused FFS test, per-owner checks, complete requested suite, and correct further demonstrated failures without reducing assertions.
- [x] Record root cause and evidence in durable workspace docs; finish review and commit.

**Acceptance Criteria:**
- Given stock serial.device overwrites IOExtSer defaults, when backend opens it, then configured binary transport is applied and mount/inspect replies arrive intact.
- Given the user command with its exact node, when invoked, then the original FHOST/FIN/FMOUNT/Dir test passes without retry or recovery additions.
- Given no node, when invoked, then all collected tests complete and pass (any declared skips must be recorded).

## Implementation coordination

The implementation subagent owns only the serial backend fix and restoring the six inherited product files: lib src/common/fn_session.c, src/common/fn_disk.c, tests/session_wire_test.c, tests/disk_context_test.c; driver amiga/disk.device/fujinet_disk_device.c; apps apps/platform/amiga/fmount.c. It is not alone in the workspace and must preserve all other edits. Parent owns harness changes, diagnostics, guest runs, complete library check, documentation, and final commits. Subagent should run driver native tests and report; do not run simultaneous guest tests or commit partial work.

## Spec Change Log

- Full-suite run `amiberry-20260916-232356` exposed an outdated low-level DD
  remount sequence: FUMOUNT removes DN2's DOS node, but the diagnostic media
  remount does not recreate it. Its retained result files show both commands
  succeeded, followed by an insert-volume DN2 requester. Extend the harness
  task to recreate the static DN2 mount and assert its result before the
  existing persistence check. Keep the serial fix and persistence assertions.
- The same run exposed stale handler-test assertions expecting registered
  inactive DN0/DN1 nodes. September 3 app commit
  `158e48ff36751e0af875827ff3da381ce106ec2c` intentionally removes those entries
  for resident unload; the existing unload/reload test depends on that behavior.
  Assert their absence in a valid DOS listing and update the architecture's
  FUMOUNT description, retaining all busy-handler/media-preservation assertions.

## Verification

All commands begin with `source scripts/env.sh` from workspace root.

- `PATH="$CC65_HOME/bin:/opt/watcom/binl64:/opt/watcom/binl:$PATH" WATCOM=/opt/watcom make -C repos/fujinet-nio-lib check` — complete configured targets and wire checks.
- `make -C repos/fujinet-nio-driver/amiga/tests test` — driver contracts, including mapping failure.
- `make -C repos/nio-core-apps TARGET=amiga` — Amiga application build (guest fixture also builds these).
- `scripts/amiga-tests --amiga-env wb32 --amiga-machine a1200-030 test_amiga_fin_ffs_adf.py::test_fin_mounts_and_reads_ffs_adf` — focused regression.
- `scripts/amiga-tests --amiga-env wb32 --amiga-machine a1200-030` — user-requested complete suite.

## Verification results

- Original isolated FFS command: **1 passed in 11.97s**, evidence
  `test-evidence/amiberry-20260916-232333/amiga-fin-ffs-adf/`.
- Complete library check: **passed**, including every configured target and
  all host wire/archive tests. The initial invocation could not locate cl65;
  adding existing cc65 and Watcom installations to PATH resolved that setup
  issue without skipping targets or changing repository configuration.
- Driver native suite: **passed**. The serial backend itself is verified in
  the guest, not by these host contracts.
- Amiga core-apps build: **passed**. The library and core-apps repositories have
  no remaining source changes.
- Wrapper collection: exact relative node collects **1** test; no node collects
  **65** tests. `bash -n scripts/amiga-tests` passed.

## Review triage

Independent edge-case and verification reviews found no production-code defect.
Blind review identified improvements to branch on exact Shell success codes,
document pytest's relative-path base, identify the captured binary, and link
final acceptance evidence; these are incorporated. Existing FFS regression
covers both control-byte length values (0x11 for inspect, 0x13 for mount).
The captured baseline exercised the guarded mount-failure path without a
requester. A follow-up review added a guard before reading the recreated DN2
node if DOS mounting fails. No retry or packet-validation relaxation was added.

- Final complete command: **65 passed in 364.42s**, no skips or failures.
  Evidence: `test-evidence/amiberry-20260916-233252/`, including `pytest.log`,
  `library-check.log`, and `amiga-apps-build.log`.
- Final focused FFS and corrected DD remount checks: **2 passed in 25.82s**,
  evidence `test-evidence/amiberry-20260916-233208/`.
- Both previously stale lifecycle cases pass in the final complete run,
  including busy refusal, media persistence, and resident unload/reload.
- Captured failing HDF broker binary disassembly matches the retained
  diagnostic disassembly exactly. SHA-256 is recorded in the driver diagnosis.

## Suggested Review Order

- Apply binary serial settings at both device lifecycle boundaries.
  [fujinet_nio_serial_backend.c:563](../../../repos/fujinet-nio-driver/amiga/nio.device/fujinet_nio_serial_backend.c#L563)

- Inspect captured bytes, overwritten settings, source history, and binary identity.
  [serial-open-parameters-regression.md:1](../../../repos/fujinet-nio-driver/docs/amiga/serial-open-parameters-regression.md#L1)

- Recreate the DOS node after low-level media remount.
  [diskdevice-adf.sequence:34](../../../integration-tests/amiberry/startup/diskdevice-adf.sequence#L34)

- Verify successful unmount removes nodes while retaining busy-handler checks.
  [test_diskdevice_fumount_handler.py:33](../../../integration-tests/amiberry/test_diskdevice_fumount_handler.py#L33)

- Report mount failure without opening an insert-volume requester.
  [amiga-fin-ffs-adf.sequence:10](../../../integration-tests/amiberry/startup/amiga-fin-ffs-adf.sequence#L10)

- Select one relative node or use pytest’s complete-suite default.
  [amiga-tests:26](../../../scripts/amiga-tests#L26)

