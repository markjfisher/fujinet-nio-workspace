---
title: 'Amiga NIO broker Stage 4 — remove disk-device idle-close'
type: 'feature'
created: '2026-08-22'
status: 'done'
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

**Approach:** Keep one Stage 4 checkpoint. Stop closing on ordinary FIFO-empty. Keep the broker client open across idle. Treat `LIBF_DELEXP` as a pending explicit teardown: `device_expunge` either completes safe teardown immediately or only sets the flag; last `CloseDevice` (OpenCnt → 0) or later worker-idle must complete that pending teardown **exactly once**. Do not unload the disk resident, change the broker, or start Stage 5.

## Boundaries & Constraints

**Always:**
- Drain after `Wait`: dequeue → `device_process_request` (existing `ensure_client` → `fn_init`) → continue; empty ⇒ `io_processing = 0`. Ordinary idle (no `LIBF_DELEXP`) must not close or wipe `client_initialized`.
- `LIBF_DELEXP` = pending explicit teardown. Safe iff OpenCnt == 0, queue empty, `io_processing == 0`. Complete **once** via one helper: `discard_change_requests`, `fn_transport_close`, clear all `client_initialized`, clear `LIBF_DELEXP`. Return 0; no `RemTask`/unload. `fn_transport_close` in `disk.device/` only from that helper.
- Not-safe `device_expunge`: set `LIBF_DELEXP` only — no close, no discard. Completers: last `device_close` (OpenCnt → 0) and worker transition to idle. `device_open` already clears the flag (cancel); keep that.
- `fn_init` stays a no-op when the disk broker context is already open.
- Native tests must run the **same** drain as production, count `fn_transport_close`, and cover I/O-matrix lifecycle rows 1–5 (ordinary idle, safe idle expunge, OpenCnt-deferred last close, in-progress then idle, no double-close).
- Follow `docs/agent-test-policy.md`. Check Stage 4 boxes only after named Verification runs.

**Ask First:**
- Completing teardown on last `CloseDevice` when `LIBF_DELEXP` is **not** set.
- Implementing real disk `RemTask`/unload.
- Changing public `fn_*` / Trackdisk / FMOUNT / broker ABI.

**Never:**
- Edit `nio.device` serial ownership, broker FIFO, or backend lazy-open/OpenCnt policy.
- Change DiskDevice mount/geometry or public APIs.
- Close because the FIFO went idle unless `LIBF_DELEXP` is already pending and OpenCnt == 0.
- Discard live change-int registrations on a deferred/busy expunge.
- Start Stage 5. Create epics/`stories.yaml`. Default to `scripts/amiga-tests`. Touch `fujinet-nio-lib` unless a compile break appears (then HALT).

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Ordinary FIFO idle | Queue empty; `LIBF_DELEXP` clear | `io_processing = 0`; **no** close; `client_initialized` unchanged | N/A |
| Work after ordinary idle | Broker still open | `fn_init`/`ensure_client` no-op; exchange proceeds | Init fail only if broker actually gone |
| Safe expunge, already idle | OpenCnt 0, queue empty, not processing | Complete teardown once; still loaded | N/A |
| Expunge while OpenCnt > 0 | Then last CloseDevice, otherwise idle | Expunge sets flag only; last close completes once | Live change-ints kept until complete |
| Expunge while I/O in progress | OpenCnt 0; `io_processing` or queue busy | Flag only; **no** close; worker idle then completes once | No discard until complete |
| Last CloseDevice, no DELEXP | OpenCnt → 0 | **No** close | N/A |
| OpenDevice after deferred expunge | `device_open` | Clears `LIBF_DELEXP`; later ordinary idle does not close | Pending teardown cancelled |
| Repeated complete attempts | Same pending request; last-close and/or idle | Close **once**; flag cleared | `fn_transport_close` not invoked twice for that request |

</frozen-after-approval>

## Code Map

- `repos/fujinet-nio-driver/amiga/disk.device/fujinet_disk_device.c:724–763` — **change.** Shared drain (nio `worker_pump` analog). **Delete** L742–757 idle-close. Empty arm: `io_processing = 0`, then try complete.
- Same file `:868–872` — native BeginIO dequeues one request today; point at shared drain.
- Same file `:281–288` — expunge always discards then sets `LIBF_DELEXP`. Try complete if safe; else flag only. Discard only in the helper (`:348–360` is all-units destructive). `:260–263` already drops ints for **that** closer.
- Same file `:256–278` — after OpenCnt--, try complete if `LIBF_DELEXP` (nio `:278–284`, but no `RemTask`). `:249–252` open clears the flag; **keep**. `:948–983` add native Open/Close/Expunge hooks.
- `amiga/nio.device/fujinet_nio_device.c:251–285` — **read-only** last-close delayed expunge; nio pump does **not** complete on idle — disk must.
- `amiga/tests/test_fujinet_disk_resident.c:52–53` — count `fn_transport_close`; matrix cases 1–5.
- `fujinet_disk_driver.c:31–52`, `fujinet_nio_client.c:20–23`, `fn_init.c:9–10`, `fn_transport.c:81–86,153–161` — **read-only**.
- Docs after Verification: architecture §4 L365–366, `backlog/nio-broker.md`, `stages.md`. Guest unchanged: inspect-catalog + `test_hd_adf_mount_geometry_dir_and_type`.

**Do not edit:** `fujinet_nio_device.c`, `fn_transport.c`, mount/geometry in `fujinet_disk_driver.c`.

## Tasks & Acceptance

**Execution:**
- [x] `fujinet_disk_device.c` -- shared drain; worker `Wait` + drain; native BeginIO uses drain
- [x] `fujinet_disk_device.c` -- remove ordinary FIFO-empty close/reset
- [x] `fujinet_disk_device.c` -- pending-`LIBF_DELEXP` helper; expunge / last-close / worker-idle complete once; discard only on complete; no unload
- [x] `test_fujinet_disk_resident.c` -- close counter; five lifecycle cases below
- [x] `nio-broker-architecture.md`, `backlog/nio-broker.md`, `stages.md` -- Stage 4 after commands pass

**Acceptance Criteria:**
- Given native resident tests, when the I/O-matrix lifecycle rows run, then close counts match (0 on ordinary idle; exactly one per pending expunge).
- Given Stage 3B inspect-catalog after this change, when disk NIO then immediate FLS runs, then it still passes.

## Spec Change Log

- 2026-08-23: Human edit — delayed `LIBF_DELEXP` completion on last CloseDevice **and** worker idle; discard change-ints only on safe complete. Avoids a deferred expunge that never runs again.

## Design Notes

One complete helper (name free). Clear `LIBF_DELEXP` in the same call that closes so last-close and idle cannot both fire. Nio last-close re-enters expunge; Exec may never call disk `device_expunge` again, so worker idle must complete a pending flag.

## Verification

Source workspace env first (`source "$NIO_WORKSPACE/scripts/env.sh"`). Lib `make check` is **not** required unless lib is edited.

**Commands:**
- `rg -n 'fn_transport_close' repos/fujinet-nio-driver/amiga/disk.device` -- expected: only the pending-expunge complete helper (not ordinary drain empty-arm)
- `make -C repos/fujinet-nio-driver/amiga tests` -- expected: all native binaries pass, including the five resident lifecycle cases
- `uv run pytest --run-amiga --amiga-env wb32 --amiga-machine a1200-030 integration-tests/amiberry/test_diskdevice_adf.py::test_hd_adf_mount_geometry_dir_and_type` -- expected: PASS (DiskDevice after inter-command idle)
- `uv run pytest --run-amiga --amiga-env wb32 --amiga-machine a1200-030 integration-tests/amiberry/test_diskdevice_adf.py::test_catalog_inspection_preserves_live_dd_handler` -- expected: PASS (run 1, Stage 3 race)
- Repeat the previous inspect-catalog pytest -- expected: PASS (run 2)

Do not run `scripts/amiga-tests`.

## Suggested Review Order

**Idle drain**

- Shared drain: empty sets `io_processing = 0`, then try pending teardown; no idle-close.
  [`fujinet_disk_device.c:755`](../../repos/fujinet-nio-driver/amiga/disk.device/fujinet_disk_device.c#L755)

- Native BeginIO uses that same drain so lifecycle tests see the idle arm.
  [`fujinet_disk_device.c:897`](../../repos/fujinet-nio-driver/amiga/disk.device/fujinet_disk_device.c#L897)

**Pending expunge**

- One helper: claim `LIBF_DELEXP` once, discard ints, `fn_transport_close`, clear init flags.
  [`fujinet_disk_device.c:373`](../../repos/fujinet-nio-driver/amiga/disk.device/fujinet_disk_device.c#L373)

- Unsafe expunge only sets the flag; last close completes if OpenCnt hits 0 and idle is safe.
  [`fujinet_disk_device.c:293`](../../repos/fujinet-nio-driver/amiga/disk.device/fujinet_disk_device.c#L293)

- Open still cancels a deferred expunge.
  [`fujinet_disk_device.c:255`](../../repos/fujinet-nio-driver/amiga/disk.device/fujinet_disk_device.c#L255)

**Tests and contract**

- Close counter plus ordinary-idle and in-progress-then-idle rows.
  [`test_fujinet_disk_resident.c:65`](../../repos/fujinet-nio-driver/amiga/tests/test_fujinet_disk_resident.c#L65)

- Last close while queued must not close; worker idle finishes once.
  [`test_fujinet_disk_resident.c:349`](../../repos/fujinet-nio-driver/amiga/tests/test_fujinet_disk_resident.c#L349)

- Architecture §4 now states idle-open and `LIBF_DELEXP` teardown.
  [`nio-broker-architecture.md:365`](../../docs/amiga/nio-broker-architecture.md#L365)
