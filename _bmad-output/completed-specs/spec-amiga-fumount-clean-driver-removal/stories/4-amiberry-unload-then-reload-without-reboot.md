---
title: 'Amiberry unload then reload without reboot'
type: 'feature'
created: '2026-09-03'
status: 'done'
baseline_commit: '6761b2e58ea6e8fd0854cf00e9f8c5a8f4be55d2'
review_loop_iteration: 0
context:
  - '{project-root}/_bmad-output/completed-specs/spec-amiga-fumount-clean-driver-removal/SPEC.md'
  - '{project-root}/docs/agent-test-policy.md'
  - '{project-root}/_bmad-output/completed-specs/spec-amiga-fumount-clean-driver-removal/stories/1-fumount-retires-the-dos-handler-then-ejects.md'
  - '{project-root}/_bmad-output/completed-specs/spec-amiga-fumount-clean-driver-removal/stories/2-disk-device-expunge-actually-unloads.md'
  - '{project-root}/_bmad-output/completed-specs/spec-amiga-fumount-clean-driver-removal/stories/3-add-fujinet-unload-resident.md'
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** Stories 1–3 shipped FUMOUNT handler teardown, disk Expunge unload, and the unload CLI tool, but the full unload→reload→remount path is not proven on the guest. Developers cannot verify that reloading updated binaries works without rebooting.

**Approach:** Add Amiberry sequence + pytest node (CAP-5, CAP-7, CAP-9). Sequence: mount ADF on DN0:, Dir to prove, FUMOUNT DN0:, unload disk device, unload nio device, reload nio (nio before disk per constraint), reload disk, remount same ADF, Dir/Type to prove I/O works. Assert unloader CLI output (`Unloaded:` strings), loader success (`Resident loaded:` strings), and post-reload file content. One pytest node on wb32/a1200-030. Register in tests.toml.

## Boundaries & Constraints

**Always:**
- FUMOUNT all used DNx: units before unloading disk device.
- Unload disk device before nio device (disk is a broker client).
- Load nio device before disk device (broker must exist first).
- After FUMOUNT, do not DeviceProc/Dir/Type DNx: to prove handler absence — those can restart it. `Unloaded: <name>` output is sufficient (Story 3 CLI does fresh FindName post-RemDevice).
- One uninterrupted .sequence execution proves same Amiga session (no reboot between unload and reload).
- Sequence uses `FailAt 21`, so commands can return non-zero without terminating. Pytest must assert `RC=0` for every lifecycle-critical step: initial FMOUNT, initial Dir/Type, FUMOUNT, unload disk, unload nio, reload nio, reload disk, post-reload FMOUNT, post-reload Dir, post-reload Type.
- Assert both expected stdout strings AND `RC=0` for unload/load operations. Do not rely solely on `Unloaded:` or `Resident loaded:` strings.
- Use existing test ADF with known content (e.g., catalogue slot 11 from fumount-handler sequence).
- Default guest: wb32 / a1200-030. Do not run full scripts/amiga-tests.
- Install on test HDF: fujinet-unload-resident beside fujinet-load-resident (Story 3 wiring is already done).

**Ask First:**
- Changing FUMOUNT, disk/nio Expunge, or the unloader tool.

**Never:**
- Testing unload while handlers are still live (FUMOUNT must succeed first).
- DeviceProc/Dir/Type DNx: after FUMOUNT to "prove absence" (that restarts the handler).
- Reordering unload (nio before disk) or load (disk before nio).
- Running full Amiberry suite as the gate.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Clean unload/reload | FUMOUNT DN0:, unload disk, unload nio, reload nio, reload disk, FMOUNT DN0: | Dir/Type post-reload shows known ADF content | Sequence records each command's RC; pytest fails if any expected-success step returns non-zero |
| Initial mount/Dir | FMOUNT slot DN0: RO, Dir DN0:, Type DN0:KNOWN.TXT | Known file visible, `RC=0` for all | Pytest asserts `FMOUNT RC=0`, `DIR RC=0`, `TYPE RC=0` |
| FUMOUNT success | FUMOUNT DN0: after successful Dir | stdout: `Ejected DN0:`, `RC=0` | Pytest asserts `FUMOUNT RC=0` |
| Unload disk success | fujinet-unload-resident fujinet-disk.device | stdout: `Unloaded: fujinet-disk.device`, `UNLOAD RC=0` | Pytest asserts both string and RC=0 |
| Unload nio success | fujinet-unload-resident fujinet-nio.device | stdout: `Unloaded: fujinet-nio.device`, `UNLOAD RC=0` | Pytest asserts both string and RC=0 |
| Reload nio success | fujinet-load-resident DEVS:fujinet-nio.device fujinet-nio.device | stdout: `Resident loaded: fujinet-nio.device`, `LOAD RC=0` | Pytest asserts both string and RC=0 |
| Reload disk success | fujinet-load-resident DEVS:fujinet-disk.device fujinet-disk.device | stdout: `Resident loaded: fujinet-disk.device`, `LOAD RC=0` | Pytest asserts both string and RC=0 |
| Post-reload mount/I/O | FMOUNT slot DN0: RO, Dir DN0:, Type DN0:KNOWN.TXT | Same known file visible, `RC=0` for all | Pytest asserts `FMOUNT RC=0`, `DIR RC=0`, `TYPE RC=0` |

</frozen-after-approval>

## Code Map

- `integration-tests/amiberry/startup/diskdevice-fumount-handler.sequence` -- **copy pattern** (FMOUNT, Dir, FUMOUNT, assert via result files). New sibling `diskdevice-unload-reload.sequence`.
- `integration-tests/amiberry/test_diskdevice_fumount_handler.py` -- **copy pattern** (run_amiga_case, assert result file content). New sibling `test_diskdevice_unload_reload.py`.
- `integration-tests/amiberry/tests.toml:40-` -- existing `[[test]]` entries with driver=true, timeout, startup, completion_mode, results. Add `diskdevice-unload-reload` entry.
- `integration-tests/amiberry/conftest.py:777-889` -- already passes resident_unloader (Story 3). No changes needed unless test registration pattern differs.
- Story 1 sequence pattern: `C:FMOUNT <slot> DN0: RO >DH0:result`, `C:Dir DN0: >DH0:result`, `C:FUMOUNT DN0: >DH0:result`, `C:Echo "RC=$RC"`.
- Story 3 unloader: `C:fujinet-unload-resident <device-name> >DH0:result`, `C:Echo "UNLOAD RC=$RC"`.
- Loader (existing): `C:fujinet-load-resident DEVS:<device> <device> >DH0:result`, `C:Echo "LOAD RC=$RC"`.

**Read-only:** `fumount.c`, disk/nio Expunge code, unloader C code, existing Amiberry sequences for Dir/Type/FMOUNT patterns.

## Tasks & Acceptance

**Execution:**
- [x] `integration-tests/amiberry/startup/diskdevice-unload-reload.sequence` -- full unload/reload/remount CLI script; captures RC for every lifecycle step -- CAP-9.
- [x] `integration-tests/amiberry/test_diskdevice_unload_reload.py` -- pytest node asserts RC=0 for all lifecycle steps + expected stdout strings + post-reload I/O content.
- [x] `integration-tests/amiberry/tests.toml` -- register [[test]] for diskdevice-unload-reload.

**Acceptance Criteria:**
- Given a mounted DN0: with known ADF content, when the sequence FUMOUNTs, unloads disk, unloads nio, reloads nio, reloads disk, and remounts, then Dir/Type show the original known file content and all lifecycle-critical steps return RC=0.
- Given the unload commands, when they succeed, then stdout contains `Unloaded: fujinet-disk.device` and `Unloaded: fujinet-nio.device`, and pytest asserts `UNLOAD RC=0` for both.
- Given the reload commands, when they succeed, then stdout contains `Resident loaded: fujinet-nio.device` and `Resident loaded: fujinet-disk.device`, and pytest asserts `LOAD RC=0` for both.
- Given all lifecycle steps (initial FMOUNT/Dir/Type, FUMOUNT, unload disk, unload nio, reload nio, reload disk, post-reload FMOUNT/Dir/Type), when pytest runs, then it asserts RC=0 for each.
- Given the test registered in tests.toml, when pytest runs the node on wb32/a1200-030, then it passes.

## Spec Change Log

## Design Notes

The sequence mirrors the delivery.md Story 4 example, with RC capture for every step:

```text
C:FMOUNT <slot> DN0: RO >DH0:initial-fmount.result
C:Echo "FMOUNT RC=$RC" >>DH0:initial-fmount.result
C:Dir DN0: >DH0:initial-dir.result
C:Echo "DIR RC=$RC" >>DH0:initial-dir.result
C:Type DN0:KNOWN.TXT >DH0:initial-type.result
C:Echo "TYPE RC=$RC" >>DH0:initial-type.result
C:FUMOUNT DN0: >DH0:fumount.result
C:Echo "FUMOUNT RC=$RC" >>DH0:fumount.result
C:fujinet-unload-resident fujinet-disk.device >DH0:unload-disk.result
C:Echo "UNLOAD DISK RC=$RC" >>DH0:unload-disk.result
C:fujinet-unload-resident fujinet-nio.device >DH0:unload-nio.result
C:Echo "UNLOAD NIO RC=$RC" >>DH0:unload-nio.result
C:fujinet-load-resident DEVS:fujinet-nio.device fujinet-nio.device >DH0:reload-nio.result
C:Echo "LOAD NIO RC=$RC" >>DH0:reload-nio.result
C:fujinet-load-resident DEVS:fujinet-disk.device fujinet-disk.device >DH0:reload-disk.result
C:Echo "LOAD DISK RC=$RC" >>DH0:reload-disk.result
C:FMOUNT <slot> DN0: RO >DH0:post-fmount.result
C:Echo "FMOUNT RC=$RC" >>DH0:post-fmount.result
C:Dir DN0: >DH0:post-dir.result
C:Echo "DIR RC=$RC" >>DH0:post-dir.result
C:Type DN0:KNOWN.TXT >DH0:post-type.result
C:Echo "TYPE RC=$RC" >>DH0:post-type.result
```

Story 1 CAP-8 sequence uses catalogue slot 11 with KNOWN.TXT. Reuse that slot for continuity.

Because `FailAt 21` allows commands to fail without terminating the sequence, the pytest must assert `RC=0` in every result file for lifecycle-critical steps. This preserves diagnostics when a command fails while ensuring the test fails if any expected-success step returns non-zero.

## Verification

**Commands:**
- `source "$NIO_WORKSPACE/scripts/env.sh" && uv run pytest --run-amiga --amiga-env wb32 --amiga-machine a1200-030 integration-tests/amiberry/test_diskdevice_unload_reload.py::test_unload_reload_without_reboot` -- one pytest node, not full suite.

Do not run `scripts/amiga-tests` (full suite) as the gate. The gate is the single pytest node above.

## Suggested Review Order

**Amiberry sequence: unload/reload lifecycle**

- Full unload→reload→remount CLI script with RC capture for every step
  [`diskdevice-unload-reload.sequence:3`](../../../../integration-tests/amiberry/startup/diskdevice-unload-reload.sequence#L3)

- FUMOUNT DN0: after proving initial I/O works
  [`diskdevice-unload-reload.sequence:12`](../../../../integration-tests/amiberry/startup/diskdevice-unload-reload.sequence#L12)

- Unload disk then nio (disk is broker client, must unload first)
  [`diskdevice-unload-reload.sequence:15`](../../../../integration-tests/amiberry/startup/diskdevice-unload-reload.sequence#L15)

- Reload nio then disk (broker must exist before disk)
  [`diskdevice-unload-reload.sequence:20`](../../../../integration-tests/amiberry/startup/diskdevice-unload-reload.sequence#L20)

- Post-reload FMOUNT and I/O to prove same-session success
  [`diskdevice-unload-reload.sequence:25`](../../../../integration-tests/amiberry/startup/diskdevice-unload-reload.sequence#L25)

**Pytest node: comprehensive RC and content assertions**

- Test function with run_amiga_case fixture
  [`test_diskdevice_unload_reload.py:1`](../../../../integration-tests/amiberry/test_diskdevice_unload_reload.py#L1)

- Initial mount/Dir/Type assertions: RC=0 + known content
  [`test_diskdevice_unload_reload.py:4`](../../../../integration-tests/amiberry/test_diskdevice_unload_reload.py#L4)

- FUMOUNT assertion: RC=0 + Ejected message
  [`test_diskdevice_unload_reload.py:12`](../../../../integration-tests/amiberry/test_diskdevice_unload_reload.py#L12)

- Unload assertions: RC=0 + Unloaded strings for both devices
  [`test_diskdevice_unload_reload.py:16`](../../../../integration-tests/amiberry/test_diskdevice_unload_reload.py#L16)

- Reload assertions: RC=0 + Resident loaded strings for both devices
  [`test_diskdevice_unload_reload.py:24`](../../../../integration-tests/amiberry/test_diskdevice_unload_reload.py#L24)

- Post-reload I/O assertions: RC=0 + content matches original
  [`test_diskdevice_unload_reload.py:32`](../../../../integration-tests/amiberry/test_diskdevice_unload_reload.py#L32)

**Test registration**

- tests.toml [[test]] entry with timeout, results list
  [`tests.toml:342`](../../../../integration-tests/amiberry/tests.toml#L342)
