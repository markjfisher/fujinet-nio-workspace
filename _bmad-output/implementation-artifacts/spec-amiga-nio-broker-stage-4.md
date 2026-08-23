---
title: 'Amiga NIO broker Stage 4 — remove disk-device idle-close'
type: 'feature'
created: '2026-08-22'
status: 'draft'
review_loop_iteration: 0
baseline_commit: '25bfaad048f992226a3ad30386295d1a470eb581'
context:
  - docs/amiga/nio-broker-architecture.md
  - docs/agent-test-policy.md
  - backlog/nio-broker.md
  - _bmad-output/specs/spec-amiga-nio-broker/stages.md
  - completed/amiga-nio-broker-stage-3.md
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** After Stage 3, `fujinet-disk.device` still `fn_transport_close`s its broker client whenever the worker FIFO empties, so idle DiskDevice drops the context and the next TD/`fn_init` must reopen. That idle-close was a serial-ownership workaround; it is now wrong.

**Approach:** Keep one Stage 4 checkpoint. Stop closing on FIFO-empty. Keep the broker client open across idle. Call `fn_transport_close` only from explicit disk teardown (`device_expunge` when the resident is idle). Do not unload the disk resident, change the broker, or start Stage 5.

## Boundaries & Constraints

**Always:**
- Production inner drain after a `Wait`: dequeue runnable → `device_process_request` (existing `ensure_client` → `nio_init` → `fn_init`) → continue; on empty queue set `io_processing = 0` and return to `Wait`. No `fn_transport_close` and no `client_initialized` wipe on that empty path.
- `fn_init` / `fn_transport_init` stay no-ops when the disk context is already open (`fn_init.c` already-initialized + `device_open` branch; `ensure_client` skip when `client_initialized`).
- `fn_transport_close` in `disk.device/` exists only on the expunge teardown path. Safe expunge: `lib_OpenCnt == 0`, IO queue empty, `io_processing == 0` → close transport and clear every unit’s `client_initialized`. Otherwise set `LIBF_DELEXP` and return 0 **without** closing.
- Disk expunge still does **not** `RemTask`, free the resident, or return a seglist. Unload stays deferred (today’s Stage-7 comment).
- Native tests must execute the **same** empty-FIFO drain as production (today `FUJINET_DISK_NATIVE_TEST` skips `device_worker_entry` and never hits idle-close). Count `fn_transport_close`.
- Follow `docs/agent-test-policy.md`. Check Stage 4 backlog boxes only after named Verification commands run.

**Ask First:**
- Closing transport on ordinary last `device_close` (`OpenCnt` → 0 without expunge).
- Implementing real disk `RemTask`/unload.
- Changing public `fn_*` / Trackdisk / FMOUNT / broker ABI.

**Never:**
- Edit `nio.device` serial ownership, broker FIFO, or backend lazy-open/OpenCnt policy.
- Change DiskDevice mount/geometry or public APIs.
- Close because the FIFO went idle.
- Start Stage 5. Create epics/`stories.yaml`. Default to `scripts/amiga-tests`. Touch `fujinet-nio-lib` unless a compile break appears (then HALT).

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| FIFO idle | Last runnable processed; queue empty | `io_processing = 0`; worker `Wait`s; **no** `fn_transport_close`; `client_initialized` unchanged | N/A |
| Work after idle | Broker context still open | `fn_init`/`ensure_client` no-op; exchange proceeds | Init fail only if broker actually gone |
| Safe expunge | OpenCnt 0, queue empty, not processing | `fn_transport_close`; clear `client_initialized`; return 0 (still loaded) | N/A |
| Busy expunge | OpenCnt > 0 or queued or `io_processing` | `LIBF_DELEXP`; **no** close | Worker/I/O continues |
| Last CloseDevice | OpenCnt → 0, no expunge | **No** transport close (resident still live) | N/A |

</frozen-after-approval>

## Code Map

- `repos/fujinet-nio-driver/amiga/disk.device/fujinet_disk_device.c:724–763` — **change.** `device_worker_entry`: `Wait` then drain. **Delete** L742–750 (`fn_transport_close` + `client_initialized` loop) and the post-close second dequeue (L751–757). Empty path: `io_processing = 0`; `Enable`; break/return.
- Same file `:868–872` — native BeginIO currently dequeues **one** request and never runs idle-close. Point it at the shared drain so tests hit FIFO-empty.
- Same file `:281–288` — `device_expunge` stub (`LIBF_DELEXP`, return 0, no `RemTask`). **Add** idle transport teardown only; keep non-unload.
- Same file `:256–278` — `device_close`: OpenCnt--; **do not** add close (Last CloseDevice row).
- Same file `:948–983` — native hooks; add expunge + `client_initialized` inspect if tests cannot reach the statics.
- `amiga/common/fujinet_disk_driver.c:31–52` — `ensure_client` skip; **read-only** unless tests need a getter.
- `amiga/channels/rs232/fujinet_nio_client.c:20–23` — `nio_init` → `fn_init`; **read-only**.
- `repos/fujinet-nio-lib/src/common/fn_init.c:9–10` + `src/platform/amiga/fn_transport.c:81–86,153–161` — already-open no-op / close implementation; **read-only**.
- `amiga/nio.device/fujinet_nio_device.c:168–188,251–325` — broker idle does **not** close backend; **read-only** pattern for disk drain vs expunge.
- `amiga/tests/test_fujinet_disk_resident.c:52–53` — stub `fn_transport_close` is a no-op; **count calls**. Extend for idle vs expunge matrix.
- `amiga/tests/Makefile` — `make tests` / `RESIDENT_TEST` already builds this TU with `-DFUJINET_DISK_NATIVE_TEST`.
- `docs/amiga/nio-broker-architecture.md` §4 L365–366 — Stage 4 still “backlog”; update when done.
- `backlog/nio-broker.md` Stage 4 + `_bmad-output/specs/spec-amiga-nio-broker/stages.md` Stage 4 — checkboxes after Verification.
- Guest: `integration-tests/amiberry/test_diskdevice_adf.py:103–122` + `startup/diskdevice-inspect-catalog.sequence` — Stage 3 disk→immediate-FLS; `test_hd_adf_mount_geometry_dir_and_type` — disk I/O across command gaps. Do not rewrite assertions.

**Do not edit:** `fujinet_nio_device.c`, `fn_transport.c`, mount/geometry in `fujinet_disk_driver.c`.

## Tasks & Acceptance

**Execution:**
- [ ] `fujinet_disk_device.c` -- extract shared drain (nio `worker_pump` analog); worker `Wait` + drain; native BeginIO uses drain -- idle-close must be testable
- [ ] `fujinet_disk_device.c` -- remove FIFO-empty close/reset; empty ⇒ `io_processing = 0` only
- [ ] `fujinet_disk_device.c` -- `device_expunge` idle teardown (`fn_transport_close` + clear `client_initialized`); busy ⇒ DELEXP, no close; still no unload
- [ ] `test_fujinet_disk_resident.c` -- count `fn_transport_close`; cover I/O matrix (idle drain, safe expunge, busy expunge)
- [ ] `nio-broker-architecture.md`, `backlog/nio-broker.md`, `stages.md` -- Stage 4 contract/checkboxes after commands pass

**Acceptance Criteria:**
- Given the worker just finished the last queued TD request, when the FIFO is empty, then it does not call `fn_transport_close` and leaves `client_initialized` set.
- Given that idle state, when another TD/NIO path runs, then `fn_init` does not reopen an already-open context and DiskDevice I/O still succeeds.
- Given OpenCnt 0 and an idle queue, when `device_expunge` runs, then `fn_transport_close` runs once and units are marked uninitialized.
- Given OpenCnt > 0 or queued/in-progress work, when `device_expunge` runs, then transport stays open.
- Given Stage 3B inspect-catalog, when it is run after this change, then disk NIO then immediate FLS still passes (no serial-ownership race regression).

## Spec Change Log

## Verification

Source workspace env first (`source "$NIO_WORKSPACE/scripts/env.sh"`). Lib `make check` is **not** required unless lib is edited.

**Commands:**
- `rg -n 'fn_transport_close' repos/fujinet-nio-driver/amiga/disk.device` -- expected: only the expunge teardown path (not `device_worker_entry` / drain empty-arm)
- `make -C repos/fujinet-nio-driver/amiga tests` -- expected: all native binaries pass, including new resident idle/expunge cases
- `uv run pytest --run-amiga --amiga-env wb32 --amiga-machine a1200-030 integration-tests/amiberry/test_diskdevice_adf.py::test_hd_adf_mount_geometry_dir_and_type` -- expected: PASS (DiskDevice after inter-command idle)
- `uv run pytest --run-amiga --amiga-env wb32 --amiga-machine a1200-030 integration-tests/amiberry/test_diskdevice_adf.py::test_catalog_inspection_preserves_live_dd_handler` -- expected: PASS (run 1, Stage 3 race)
- Repeat the previous inspect-catalog pytest -- expected: PASS (run 2)

Do not run `scripts/amiga-tests`.
