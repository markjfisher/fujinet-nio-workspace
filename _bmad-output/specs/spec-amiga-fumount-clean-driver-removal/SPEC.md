---
id: SPEC-amiga-fumount-clean-driver-removal
companions:
  - brownfield.md
  - delivery.md
  - lifecycle.md
  - ../../../docs/amiga/disk-media-architecture.md
  - ../../../docs/agent-test-policy.md
  - ../../../docs/amiga/amiberry-testing.md
  - ../../../repos/fujinet-nio-driver/amiga/README.md
sources:
  - ../../../backlog/amiga-fumount-clean-driver-removal.md
---

> **Canonical contract.** This SPEC and the files in `companions:` are the complete, preservation-validated contract for what to build, test, and validate. Source documents listed in frontmatter are for traceability — consult them only if you need narrative rationale or prose color this contract intentionally omits.

# Amiga FUMOUNT and clean resident-driver unload

## Why

**Pain.** Reloading `fujinet-disk.device` and `fujinet-nio.device` after a rebuild currently requires rebooting the Amiga, because the disk device never actually Expunges and DOS handlers keep its units open. Developers cannot FTP a new binary and `fujinet-load-resident` it in place. The same gap blocks a clean user unmount: `FUMOUNT` today ejects media while leaving the filesystem handler alive, so `OpenCnt` never reaches zero.

## Capabilities

- **CAP-1**
  - **intent:** An operator can unmount `DN0:`–`DN7:` so that unit’s AmigaDOS filesystem handler terminates and the FujiNet media in that unit is ejected. That pair is the meaning of `FUMOUNT`.
  - **success:** After a successful `FUMOUNT DNx:` (existing `DNx:` / bare `0`–`7` syntax), the DOS-list entry’s `dol_Task` is null (e.g. `doslistdiag`); `fujinet-mount --status` reports `absent=1`; confirmation remains `Ejected DNx:`. Absence is **not** proven with `DeviceProc`, `Dir`, `Type`, or any other `DNx:` access (those can restart the handler). The command does not leave a live handler on ejected media.
- **CAP-2**
  - **intent:** An operator can attempt unmount while the volume is busy (cwd, open file, lock, notification) and the **filesystem handler** refuses `ACTION_DIE` rather than tearing itself out.
  - **success:** The bound `DNx:` handler rejects `ACTION_DIE` while unsafe; `FUMOUNT` reports busy, does not eject (`absent=0`), and a subsequent `Type`/`Dir` of that still-mounted volume works. Do not treat this refusal as a DOS/`DoPkt` guarantee independent of the handler. Amiberry sequence covers this.
- **CAP-3**
  - **intent:** After every FujiNet `DNx:` handler that was holding the disk device has been retired, nothing in the FujiNet stack keeps `fujinet-disk.device` open except a deliberate later `OpenDevice`.
  - **success:** With no remaining `DNx:` handlers and no other clients, `FUMOUNT` has `CloseDevice`’d its temporary open and `lib_OpenCnt` is 0, so a following `RemDevice` is allowed to complete rather than only set `LIBF_DELEXP`. Tests read `lib_OpenCnt` from the Exec device node (`FindName` on `DeviceList`), not by `OpenDevice`/`DeviceProc` on `DNx:`.
- **CAP-4**
  - **intent:** The system can remove `fujinet-disk.device` from memory at runtime when it is idle.
  - **success:** Idle `RemDevice("fujinet-disk.device")` results in a later `FindName` miss on the guest. Native tests prove busy deferral (`LIBF_DELEXP`, return 0) vs idle completion returning the stored `LoadSeg` segment list; they are not required to emulate Exec `DeviceList` removal.
- **CAP-5**
  - **intent:** After the disk device is gone, the system can remove `fujinet-nio.device` from memory at runtime when it is idle.
  - **success:** Idle `RemDevice("fujinet-nio.device")` results in a later `FindName` miss. Disk device must already be unloaded (it is a broker client). Existing nio Expunge behavior is kept, not redesigned.
- **CAP-6**
  - **intent:** An operator can request unload of one named Exec device and learn whether it actually left the device list.
  - **success:** `fujinet-unload-resident <device-name>` (built next to `fujinet-load-resident`) prints unloaded vs still-resident (open/busy); it never inspects the pointer passed to `RemDevice` afterward.
- **CAP-7**
  - **intent:** After a successful unload of disk then nio, an operator can load replacement binaries with the existing resident loader and use disks again without rebooting.
  - **success:** `fujinet-load-resident` of nio then disk succeeds; a subsequent `FMOUNT` + `Dir`/`Type` on a supported ADF works in the same Amiga session.
- **CAP-8**
  - **intent:** Handler-teardown `FUMOUNT` is proven in the Amiberry suite independently of driver unload.
  - **success:** A new `integration-tests/amiberry/startup/*.sequence` plus pytest module (registered in `tests.toml`) asserts success teardown and busy-refuse; it is runnable as a single pytest node. Success-path handler absence uses DOS-list/`dol_Task` (and media status), never `DeviceProc`/`Dir`/`Type` on that `DNx:`.
- **CAP-9**
  - **intent:** Full disk-then-nio unload and reload is proven in the Amiberry suite.
  - **success:** A new sequence+pytest node: `FUMOUNT` all used units, unload disk, unload nio, reload nio, reload disk, remount and read; asserts FindName/status text from the unload CLI and post-reload I/O. Run as one pytest node, not the full suite, for the story gate.
- **CAP-10**
  - **intent:** Existing catalogue mount, remount, and restore flows still work when `FUMOUNT` now kills the handler.
  - **success:** `diskdevice-fmount` and `diskdevice-fmount-restore` still pass. Assertions that assumed a live handler after eject are rewritten to match DIE-then-eject (DOS-list `dol_Task` null, media absent, remount via `FMOUNT` still works). Post-`FUMOUNT` checks in those cases must not poke `DNx:` to prove the handler is gone.

## Constraints

- Ship FUMOUNT handler teardown (CAP-1, CAP-2, CAP-8) and keep those tests green before changing disk-device Expunge to return a seglist (CAP-4).
- Runtime reload order is: retire handlers / eject units → `RemDevice` disk → `RemDevice` nio → `fujinet-load-resident` nio → `fujinet-load-resident` disk.
- Do not unload `fujinet-disk.device` while any unit still has an active DOS handler.
- `FUMOUNT` success path is classic packets: `DeviceProc` / `DoPkt` `ACTION_FLUSH`, then `ACTION_DIE`, then eject. `ACTION_DIE` is used **because** it is the OS 1.3-compatible handler-terminate packet; later documentation that deprecates it, and OS 3.2 `Dismount`, are not the implementation. The path is not Inhibit-keep-handler or `Assign DISMOUNT`.
- `ACTION_FLUSH` failure is fail-safe: do not send `ACTION_DIE` and do not eject. This epic does not treat “FLUSH unsupported” as success.
- If `ACTION_DIE` fails, do not `TD_EJECT` / `FUJINET_DISK_CMD_EJECT` that unit. The **filesystem handler** bound to `DNx:` must reject `ACTION_DIE` while it still has locks, file handles, a busy cwd, or notifications. That is a handler contract to prove in tests, not a DOS-library guarantee.
- After a successful unmount, do not call `DeviceProc` or access `DNx:` to prove the handler is gone (`Dir`/`Type`/`DeviceProc` may restart it). Observe `dol_Task` on the DOS list and media via `fujinet-disk.device` status.
- `FUMOUNT`’s temporary `OpenDevice` for eject must be `CloseDevice`’d. With no other clients, `fujinet-disk.device` `lib_OpenCnt` is 0.
- `FUMOUNT` does not take `REMOVE` and does not `RemDosEntry`. The DOS node may remain after DIE.
- Ordinary Expunge does not abort in-flight I/O. Refuse or delay while `OpenCnt != 0`, the I/O queue is nonempty, or a request is processing (`LIBF_DELEXP` until last close/idle).
- Disk-device unload Expunge must mirror nio teardown: worker stop and stack/signal free, `fn_transport_close()`, discard change requests, `Remove` device node, free NegSize+PosSize base, return `segment_list` stored at `InitResident`.
- Unload status after `RemDevice` is a new `FindName` on `DeviceList` under `Forbid`/`Permit`.
- `fujinet-mount` stays diagnostic. User-facing unmount remains `FUMOUNT` in `repos/nio-core-apps/apps/platform/amiga/fumount.c` (`DNx:` / `0`–`7`).
- `nio-core-apps` talks to the disk device only through the published SDK: `make sdk` / `amiga-driver-sdk` produces `build/amiga/include/fujinet-amiga-disk/*.h` and `libfujinet-amiga-disk.a`. Do not include driver-private headers or compile driver `.c` into core-apps. `FUMOUNT` DIE-then-eject uses `dos.library` packets plus existing `OpenDevice` / `TD_EJECT`; no new SDK command is required for that path.
- Unload CLI is `fujinet-unload-resident` in the driver tools tree beside `fujinet-load-resident`, one device name per run.
- Tests: native/host tests in `repos/fujinet-nio-driver` for Expunge deferral/seglist; Amiga `nio-core-apps` build for `FUMOUNT`; new Amiberry cases as CAP-8/CAP-9 (`DeviceList` disappearance is the guest node). Default guest `wb32` + `a1200-030`. Do not default to the full Amiberry suite.
- Out of this spec: HDF/RDB, Phase 2 media expansion, broker ABI redesign, auto-load of devices from `fujinet-nio-lib`.

## Non-goals

- Forcing handler death or `RemDevice` under open locks, file handles, Shell cd, Workbench drawers, or other clients.
- Using `Assign DISMOUNT` or OS 3.2 `Dismount` as the `FUMOUNT` implementation.
- `FUMOUNT DNx: REMOVE`, `RemDosEntry`, or any other “purge DOS registration” behavior on the unmount command. A later debug/admin tool may do that as a separate command.
- Shipping “eject media, leave handler alive” as `FUMOUNT` (or as a default alternate unmount).
- Changing BBC/Atari `FUMOUNT` or the portable `apps/fumount.c` drive-letter path except where a shared header is unavoidably required.
- Redesigning `fujinet-nio.device` Expunge (already returns a seglist); only call it after disk is gone.
- Auto-expunge on last `CloseDevice` without `RemDevice`/`LIBF_DELEXP`.
- Making `fujinet-mount` the supported user unmount command.

## Success signal

On a running Amiga (Amiberry `wb32` / `a1200-030`), `FUMOUNT` can **terminate** every `DNx:` handler that was using FujiNet disks; `fujinet-unload-resident` then removes `fujinet-disk.device` and `fujinet-nio.device` from the device list; `fujinet-load-resident` brings both back; `FMOUNT` + `Dir` works — without a reboot. Busy `FUMOUNT` fails safe. Existing fmount/restore Amiberry cases still pass.

## Assumptions

- `FMOUNT` / `FUMOUNT` stay in `repos/nio-core-apps/apps/platform/amiga/`. Expunge and `fujinet-unload-resident` live in `repos/fujinet-nio-driver`. Workspace Amiberry tests cover the cross-repo path.
- After successful `ACTION_DIE` the `DNx:` DOS list entry may remain with a null task; later `FMOUNT` or volume access may restart the handler. That is why absence tests must not poke `DNx:`.
- `ACTION_DIE` remains the unmount packet for classic/OS 1.3 compatibility; this epic’s automated proof is the existing WB 3.x Amiberry guest, not a new 1.3 filesystem certification.
- Native `FUJINET_DISK_NATIVE_TEST` Expunge coverage is flags/seglist only; disappearance from Exec `DeviceList` is proven on the guest (CAP-9).

