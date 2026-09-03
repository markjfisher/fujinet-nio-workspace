# Delivery — one epic, four stories

This spec is **one epic**: clean runtime unmount of FujiNet `DNx:` volumes and unload/reload of the two resident devices without reboot.

Stories run in list order. Story 1 must be done (including CAP-8 Amiberry) before Story 2 changes disk Expunge.

| Story | Title | Capabilities | Owners |
| --- | --- | --- | --- |
| 1 | FUMOUNT retires the DOS handler then ejects | CAP-1, CAP-2, CAP-8, CAP-10 (fumount assertions) | `nio-core-apps` `apps/platform/amiga/fumount.c` via DiskDevice SDK; workspace Amiberry |
| 2 | Disk device Expunge actually unloads | CAP-3, CAP-4 | `fujinet-nio-driver` `fujinet_disk_device.c` + native tests (deferral/seglist) |
| 3 | `fujinet-unload-resident` | CAP-6 | driver `amiga/tools/`, beside `fujinet-load-resident.c` |
| 4 | Amiberry unload then reload | CAP-5, CAP-7, CAP-9, CAP-10 remainder | workspace Amiberry (`DeviceList` gone + reload) |

## Story 1 — FUMOUNT handler teardown

Replace Amiga `FUMOUNT` with: `DeviceProc` (live handler only) → `ACTION_FLUSH` → on FLUSH fail stop (no DIE, no eject) → `ACTION_DIE` → on DIE fail stop (no eject) → `TD_EJECT` → `CloseDevice`. This is the only `FUMOUNT` success path. `ACTION_DIE` is the OS 1.3 packet, used deliberately despite later deprecation. Do not keep Inhibit-keep-handler. Do not add `REMOVE` / `RemDosEntry`.

The filesystem handler must reject `ACTION_DIE` while busy; if the busy Amiberry case shows DIE succeeding anyway, stop and report — do not paper over it as a DOS guarantee.

Amiberry (CAP-8): new `startup/` sequence + `tests.toml` `[[test]]` + pytest. Minimum:

- Mount known ADF on `DN0:`, `Dir` succeeds, `FUMOUNT` succeeds, status `absent=1`, `doslistdiag` (or DOS-list `dol_Task`) shows no handler task, `Ejected DN0:`, and disk.device `lib_OpenCnt` is 0 via Exec `FindName` (not `OpenDevice` on `DNx:`). Do **not** `DeviceProc`/`Dir`/`Type` `DN0:` after success to prove absence.
- Mount, hold the volume busy so the **handler** refuses DIE, `FUMOUNT` fails, `Dir`/`Type` still works (handler still live — access is allowed on this path).

CAP-10: update `diskdevice-fmount` / restore sequences and pytest if they assumed a live handler after eject; remount after `FUMOUNT` must still work (`FMOUNT` + `Type`). Post-unmount absence checks must use DOS-list/`dol_Task`, not `DeviceProc`.

## Story 2 — Disk Expunge unload

Change `complete_pending_expunge` / `device_expunge` so idle teardown matches nio: worker stop, `fn_transport_close`, discard change requests, `Remove`, free base, return `segment_list`. Keep deferral when open/queued/processing.

Native tests: expunge while `OpenCnt!=0` returns 0 and sets `LIBF_DELEXP`; after last close, delayed expunge completes and returns the stored seglist. Native builds may skip real `Remove`/`FreeMem` the same way nio native tests do. Guest CAP-9 proves the name is gone from `DeviceList`.

## Story 3 — Unload CLI

`fujinet-unload-resident <device-name>` beside the loader. Core: Forbid, FindName DeviceList, RemDevice if found, Permit; Forbid, FindName again, Permit; print unloaded vs still resident. Install on the test HDF like the loader.

## Story 4 — Sequence: unload and reload

New sequence, typical guest steps (adjust paths to how tests.toml installs C:/DEVS:):

```text
FMOUNT … DN0:
Dir DN0:
FUMOUNT DN0:
; repeat for any other mounted DNx:
fujinet-unload-resident fujinet-disk.device
fujinet-unload-resident fujinet-nio.device
fujinet-load-resident DEVS:fujinet-nio.device fujinet-nio.device
fujinet-load-resident DEVS:fujinet-disk.device fujinet-disk.device
FMOUNT … DN0:
Dir DN0:
```

Assert unload CLI text, load success, and a known file on the remounted ADF. Unload disk before nio; load nio before disk.

## Verification commands (record and run per story)

Per `docs/agent-test-policy.md`:

- Story 1: Amiga `nio-core-apps` build for the Amiga target; pytest node for the new FUMOUNT sequence (`wb32` / `a1200-030`).
- Story 2: `repos/fujinet-nio-driver` native/host tests for disk Expunge.
- Story 3: driver `make native` produces the unload tool; smoke in Story 4.
- Story 4: one new pytest node, not full `scripts/amiga-tests`.
- After stories that change FUMOUNT semantics: existing `test_diskdevice_fmount.py` / restore nodes if assertions still apply.

## Docs to update when behavior ships

- `docs/amiga/disk-media-architecture.md` (`FUMOUNT` is unmount: handler dies, then eject; not inhibit-and-keep-handler).
- `repos/fujinet-nio-driver/amiga/README.md` unload/reload recipe.
- `docs/amiga/amiberry-testing.md` if bootstrap/copy lists gain the unload tool.
