# Brownfield — FUMOUNT and resident Expunge

## User-facing commands today

`docs/amiga/disk-media-architecture.md` and `repos/fujinet-nio-driver/amiga/README.md`: `FMOUNT` / `FUMOUNT` / `FMOUNTRESTORE` are the product commands. `fujinet-mount` is diagnostic only.

Amiga `FMOUNT` / `FUMOUNT` live in `repos/nio-core-apps/apps/platform/amiga/`. They do **not** compile driver sources. They consume the driver’s **SDK release**:

- Workspace `core-apps-amiga` runs `make all sdk` in `fujinet-nio-driver/amiga` first (`amiga-driver-sdk`).
- Compile: `-I../fujinet-nio-driver/build/amiga/include`
- Link: `-lfujinet-amiga-disk`
- Thin shim: `include/platform/amiga/fujinet_disk_iface.h` → `<fujinet-amiga-disk/device.h>`

`FMOUNT` uses SDK support (`classify` / DosEnvec). `FUMOUNT` currently needs only `FUJINET_DISK_DEVICE_NAME` and `OpenDevice`/`TD_EJECT`. Handler DIE is `dos.library`, not a new driver command.

Amiga `FUMOUNT` already parses `DNx:` / `dnx:` / `0`–`7`.

Current success path when a handler is live (**to be replaced**; it is not the product unmount):

1. `OpenDevice("fujinet-disk.device", unit)`
2. `ACTION_FLUSH`
3. `Inhibit(DNx:, TRUE)`
4. `TD_EJECT`
5. `Inhibit(DNx:, FALSE)` so the handler can see no-media
6. `CloseDevice`

That ejects media (`absent=1`) but **keeps the filesystem handler**. `FUMOUNT` must become Flush → `ACTION_DIE` → eject; Inhibit-keep-handler is not a retained default.

`FMOUNT` (`apps/platform/amiga/fmount.c`) already calls `ACTION_DIE` in `retire_handler()` when geometry/DosType is incompatible. Compatible live replacement uses Inhibit, not DIE. Remount after `FUMOUNT` must work with a dead handler and a possibly still-registered DOS node (null task).

## Devices today

Loader: `repos/fujinet-nio-driver/amiga/tools/fujinet-load-resident.c` — `LoadSeg` + `InitResident` with the real seglist.

`fujinet-nio.device` (`amiga/nio.device/fujinet_nio_device.c`): stores `segment_list`; `device_expunge` defers if open/queued/in-progress (`LIBF_DELEXP`); otherwise stops worker, `close_backend`, `Remove`, frees base, **returns seglist**. Close with `OpenCnt==0` and `LIBF_DELEXP` completes delayed expunge.

`fujinet-disk.device` (`amiga/disk.device/fujinet_disk_device.c`): stores `segment_list` but `device_expunge` comments “No unload”, sets `LIBF_DELEXP`, and `complete_pending_expunge` only discards change requests, `fn_transport_close()`, clears `client_initialized`, **returns 0**. No `RemTask`/stack free, no `Remove`, no `FreeMem` of the base. Native hooks: `fujinet_disk_native_test_expunge`.

Disk device is a broker client (`fn_transport_init` / close on teardown). Unload disk before nio.

## Tests today

Amiberry: `integration-tests/amiberry/startup/*.sequence`, `tests.toml`, pytest modules. `diskdevice-fmount.sequence` already runs `FUMOUNT` and asserts `Ejected DNx:` plus status `absent=1`. New behavior needs **new** sequences/nodes, not only those assertions.

Driver host: `make tests` / native disk tests from `amiga/README.md`. Broker Expunge-while-busy is already a Stage 2/4 concern; do not regress it.

## Load-bearing Q&A from the backlog (absorbed)

- `RemDevice` → Expunge; disk-loaded code unloads via returned seglist.
- FlushDevice pattern: `Forbid`, `FindName` `DeviceList`, `RemDevice`, `Permit`.
- Report unload via a **second** `FindName`.
- `ACTION_DIE` may fail if the **filesystem handler** still has locks/handles/notifications; then do not eject. That refusal is the handler’s job, not a DOS-library guarantee.
- `ACTION_FLUSH` failure stops `FUMOUNT` (no DIE, no eject).
- `ACTION_DIE` is the classic/OS 1.3 terminate packet; use it on purpose, not OS 3.2 `Dismount`.
- After successful handler retirement and TD_EJECT, FUMOUNT removes the DNx DosList device entry with RemDosEntry while holding LDF_WRITE | LDF_DEVICES. FUMOUNT does not call FreeDosEntry on MountList-created entries. If LockDosList fails, FindDosEntry misses, or the entry is not successfully removed, FUMOUNT returns failure because the DNx DOS registration has not been fully retired. Proving the handler is gone must use DOS-list `dol_Task`, not `DeviceProc`/`Dir` on `DNx:` (that can restart the handler).
- Do not use `Assign DISMOUNT` (name only, no resource free).
