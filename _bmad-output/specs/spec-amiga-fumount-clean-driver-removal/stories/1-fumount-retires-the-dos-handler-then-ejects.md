---
title: 'FUMOUNT retires the DOS handler then ejects'
type: 'feature'
created: '2026-09-03'
status: 'done'
baseline_commit: 'fdda78d547a674b395c66a249529e3397b47553b'
review_loop_iteration: 0
context:
  - '{project-root}/_bmad-output/specs/spec-amiga-fumount-clean-driver-removal/SPEC.md'
  - '{project-root}/docs/agent-test-policy.md'
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** Amiga `FUMOUNT` ejects media but keeps the `DNx:` filesystem handler via Inhibit-keep-handler, so `OpenCnt` never reaches zero and a later resident unload cannot proceed.

**Approach:** Make `FUMOUNT` Flush → `ACTION_DIE` → eject → `CloseDevice`. Prove handler absence with DOS-list `dol_Task` and disk status, never by poking `DNx:`. Prove busy DIE refusal in Amiberry. Update fmount assertions that assumed keep-handler-after-eject.

## Boundaries & Constraints

**Always:**
- Success path: live handler → `DeviceProc` → `ACTION_FLUSH`; FLUSH fail → stop (no DIE, no eject). Then `ACTION_DIE`; DIE fail → no eject. Then `TD_EJECT` → `CloseDevice`. Keep `DNx:` / `0`–`7` parse and `Ejected DNx:` on success.
- DIE success is `dol_Task` becoming null (poll like `fmount.c` `retire_handler`). Do not treat `DoPkt(ACTION_DIE)` return as retirement (`-1`/`IoErr=0` is proven).
- After success, do not `DeviceProc`/`Dir`/`Type` that `DNx:` to prove absence. Observe `doslistdiag`/`dol_Task`, `fujinet-mount --status` `absent=1`, and `fujinet-disk.device` `lib_OpenCnt` via Exec `FindName` (not `OpenDevice` on `DNx:`).
- Busy path may `Dir`/`Type` because the handler is still live.
- `nio-core-apps` uses DiskDevice SDK + `dos.library` only. `FUMOUNT` does not `RemDosEntry` / `REMOVE`.
- If the busy Amiberry case shows DIE succeeding anyway, HALT and report — do not paper over it as a DOS guarantee.

**Ask First:**
- Busy handler still accepts `ACTION_DIE` in Amiberry.
- Need for Inhibit, `Assign DISMOUNT`, or OS 3.2 `Dismount` as the unmount path.

**Never:**
- Disk-device Expunge / seglist unload (Story 2).
- `fujinet-unload-resident` (Story 3) or unload-reload Amiberry (Story 4).
- Portable `apps/fumount.c`, BBC/Atari `FUMOUNT`.
- Shipping Inhibit-keep-handler as `FUMOUNT`.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Idle live handler | Mounted ADF, handler `dol_Task != 0`, no locks | FLUSH, DIE until `dol_Task==0`, eject, CloseDevice; `Ejected DNx:`; `absent=1`; DOS node may remain | N/A |
| No live handler | `dol_Task` already null | Skip FLUSH/DIE; still eject + CloseDevice; `Ejected DNx:` | N/A |
| FLUSH fail | `DoPkt(ACTION_FLUSH)` false | No DIE, no eject | Existing flush error; non-zero rc |
| Handler busy | Cwd/lock/open/notify; handler refuses DIE (`dol_Task` stays set) | No eject; media still present; `Dir`/`Type` still works | Non-zero rc; busy report |
| Bad argv | Not `DNx:` / `0`–`7` | Usage | rc=10 |

</frozen-after-approval>

## Code Map

- `repos/nio-core-apps/apps/platform/amiga/fumount.c:43-191` -- Today: `has_active_handler` + `DeviceProc` + FLUSH + **Inhibit TRUE → TD_EJECT → Inhibit FALSE**. Replace Inhibit block with DIE + `dol_Task` poll; keep parse/OpenDevice/eject/CloseDevice/`Ejected`.
- `repos/nio-core-apps/apps/platform/amiga/fmount.c:76-90` -- Reuse DIE + Delay poll of `snapshot_node` / `dol_Task`; ignore `DoPkt` return.
- `repos/nio-core-apps/include/platform/amiga/fujinet_disk_iface.h` -- SDK shim only; no new driver command.
- `repos/fujinet-nio-driver/amiga/public/include/fujinet-amiga-disk/device.h` -- `FUJINET_DISK_DEVICE_NAME`; read-only.
- `repos/nio-apps/apps/test/doslistdiag.c:23-29` -- `DEVICE name=DN0 type=0 task=00000000` pattern for absence. Hardcoded DN0 find; post-`FUMOUNT DN0:` can use list output.
- `docs/amiga/disk-media-architecture.md:319-321` -- DIE return is not proof; `dn_Task==0` is.
- `integration-tests/amiberry/startup/diskdevice-fmount.sequence:47-69` -- `FUMOUNT` then status/`Type` only after **FMOUNT remount**; after final `fumount DN0:` do not Dir/Type that unit. Add `doslistdiag` + OpenCnt after last eject if proving CAP-1/3 there, or in the new CAP-8 sequence.
- `integration-tests/amiberry/test_diskdevice_fmount.py:55-69` -- Asserts `Ejected` + `absent=1`; rewrite any keep-handler assumption; remount+Type after `FUMOUNT` stays valid.
- `integration-tests/amiberry/tests.toml:261+` -- Copy a `[[test]]` + `startup/` + pytest module for CAP-8 (success + busy). `project = "apps"` already ships `doslistdiag`.
- `docs/amiga/disk-media-architecture.md:42-43` -- User sentence still says flush/eject; update to handler-die-then-eject.

**Read-only:** `fujinet_disk_device.c` Expunge; `apps/fumount.c`; nio Expunge.

## Tasks & Acceptance

**Execution:**
- [x] `repos/nio-core-apps/apps/platform/amiga/fumount.c` -- Replace Inhibit-keep-handler with FLUSH → DIE (poll `dol_Task`) → eject → CloseDevice; FLUSH/DIE fail-safe as matrix -- product unmount.
- [x] `repos/nio-apps/apps/test/devopencnt.c` -- New diagnostic: Forbid/`FindName` `DeviceList` for `fujinet-disk.device`, print `lib_OpenCnt`, no `OpenDevice` -- CAP-3 observation without bumping OpenCnt. Wildcard `apps/test/*.c` picks it up.
- [x] `integration-tests/amiberry/startup/` + `tests.toml` + new pytest -- CAP-8: mount known ADF `DN0:`, `Dir` ok, `FUMOUNT`, `Ejected`, `absent=1`, `doslistdiag` `DN0` `task=00000000`, `devopencnt` 0; **no** DeviceProc/Dir/Type `DN0:` after success. Second path: `CD DN0:` (or equivalent lock) then `FUMOUNT` fails, `Dir`/`Type` still works.
- [x] `integration-tests/amiberry/startup/diskdevice-fmount.sequence` and `test_diskdevice_fmount.py` -- CAP-10: after `FUMOUNT`, do not poke `DNx:` to prove absence; remount via `FMOUNT` + `Type` still required. Touch restore sequences only if they poke `DNx:` to prove handler gone.
- [x] `docs/amiga/disk-media-architecture.md` -- `FUMOUNT` is unmount: handler dies, then eject.

**Acceptance Criteria:**
- Given an idle mounted `DNx:`, when `FUMOUNT DNx:` succeeds, then `dol_Task` is null, media `absent=1`, confirmation is `Ejected DNx:`, and with no other clients `lib_OpenCnt` is 0.
- Given a busy volume whose handler refuses DIE, when `FUMOUNT` runs, then it does not eject and a subsequent `Dir`/`Type` of that volume works.
- Given FLUSH failure, when `FUMOUNT` runs, then it does not DIE and does not eject.
- Given existing `diskdevice-fmount` remount-after-eject, when the suite runs, then `FMOUNT` + `Type` still pass and post-unmount absence checks do not `DeviceProc`/`Dir`/`Type` that unit.

## Spec Change Log

- 2026-09-03: CAP-8 sequence covers idle (no `Dir` before `FUMOUNT DN1:`), live handler teardown, bad argv, and Shell `CD DN0:` busy refusal. FLUSH-fail remains a code fail-safe (`DoPkt(ACTION_FLUSH)` false → no DIE/eject); no guest injection was available on a healthy FFS volume. A host boolean wrapper around `flush_ok != 0` was removed after review — it did not execute `fumount.c`.

## Design Notes

`ACTION_DIE` is the OS 1.3 terminate packet, used on purpose. Copy `retire_handler` polling, not Inhibit. Busy = Shell `CD DNx:` in the same CLI so the script holds a lock. `devopencnt` lives in nio-apps test apps, not the unload CLI.

## Verification

**Commands:**
- `source "$NIO_WORKSPACE/scripts/env.sh" && ./scripts/build.sh core-apps-amiga` -- `fumount` links; SDK present.
- `./scripts/build.sh apps-amiga` -- `devopencnt` (and `doslistdiag`) built.
- `source scripts/env.sh && uv run pytest --run-amiga --amiga-env wb32 --amiga-machine a1200-030 integration-tests/amiberry/test_diskdevice_fumount_handler.py` -- CAP-8 node (name the `::test_…` after adding it).
- `source scripts/env.sh && uv run pytest --run-amiga --amiga-env wb32 --amiga-machine a1200-030 integration-tests/amiberry/test_diskdevice_fmount.py::test_fmount_fumount_standard_adf` -- CAP-10 fmount node. Run restore node only if those sequences/assertions changed.

Do not run full `scripts/amiga-tests`. Do not change disk Expunge to make OpenCnt/unload pass.

## Suggested Review Order

**Handler teardown**

- FLUSH fail-safe then DIE; retirement is `dol_Task` poll, not `DoPkt`.
  [`fumount.c:140`](../../../../repos/nio-core-apps/apps/platform/amiga/fumount.c#L140)

- Poll plus a final DOS-list check so a late DIE is not reported busy.
  [`fumount.c:66`](../../../../repos/nio-core-apps/apps/platform/amiga/fumount.c#L66)

**OpenCnt observation**

- `FindName` on `DeviceList` under Forbid; never `OpenDevice`.
  [`devopencnt.c:15`](../../../../repos/nio-apps/apps/test/devopencnt.c#L15)

**Guest proof**

- Live `DN0:`: Dir, FUMOUNT, status/doslistdiag/opencnt; no post-success Dir/Type.
  [`diskdevice-fumount-handler.sequence:12`](../../../../integration-tests/amiberry/startup/diskdevice-fumount-handler.sequence#L12)

- Busy `CD DN0:` must not eject; Dir/Type still allowed.
  [`test_diskdevice_fumount_handler.py:43`](../../../../integration-tests/amiberry/test_diskdevice_fumount_handler.py#L43)

**Peripherals**

- Register the CAP-8 node.
  [`tests.toml:309`](../../../../integration-tests/amiberry/tests.toml#L309)

- User-facing FUMOUNT is die-then-eject.
  [`disk-media-architecture.md:42`](../../../../docs/amiga/disk-media-architecture.md#L42)
