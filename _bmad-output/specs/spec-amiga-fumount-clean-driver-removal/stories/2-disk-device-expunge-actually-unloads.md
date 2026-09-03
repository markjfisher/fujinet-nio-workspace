---
title: 'Disk device Expunge actually unloads'
type: 'feature'
created: '2026-09-03'
status: 'draft'
review_loop_iteration: 0
context:
  - '{project-root}/_bmad-output/specs/spec-amiga-fumount-clean-driver-removal/SPEC.md'
  - '{project-root}/docs/agent-test-policy.md'
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** Idle `fujinet-disk.device` Expunge sets `LIBF_DELEXP` and closes transport but returns 0, never `Remove`s the node or the `InitResident` seglist, so `RemDevice` cannot unload the binary.

**Approach:** Mirror `fujinet-nio.device` idle Expunge: defer while open or busy; when safe, stop the worker, close transport, discard change registrations, `Remove`/free the base (guest only), and return the stored `LoadSeg` list.

## Boundaries & Constraints

**Always:**
- Defer (`LIBF_DELEXP`, return 0) while `OpenCnt != 0`, the I/O queue is nonempty, or `io_processing != 0`. Do not abort in-flight I/O.
- Idle complete: `discard_change_requests`, `fn_transport_close()`, clear per-unit `client_initialized`, return `base->segment_list`.
- Guest (`#ifndef FUJINET_DISK_NATIVE_TEST`): stop worker (`RemTask` + stack/`FreeSignal`) only from a task that is not that worker; `Forbid`/`Remove`/`FreeMem` NegSize+PosSize like nio. Native tests skip `Remove`/`FreeMem`/`RemTask`.
- If `complete_pending_expunge` runs on the disk worker, do resource teardown only (no self-`RemTask`/`FreeMem` of that stack). Leave `Remove` + returning the BPTR to Exec for Expunge/`CloseDevice` on another task. `fn_transport_close` must stay safe if already closed.
- `OpenDevice` still clears `LIBF_DELEXP`. Ordinary idle without `LIBF_DELEXP` must not close transport.
- Native `device_init` for tests stores a non-zero sentinel seglist (nio uses `(BPTR)1`).

**Ask First:**
- Completing `Remove`/`FreeMem` of the resident base from the disk worker task.
- Adding Amiberry CAP-9, `fujinet-unload-resident`, or FUMOUNT changes in this story.

**Never:**
- Unload while a live `DNx:` handler still holds the device (Story 1 owns handler DIE).
- Unload CLI (Story 3), guest unload/reload sequence (Story 4), nio Expunge redesign, auto-expunge on last close without `RemDevice`/`LIBF_DELEXP`.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Idle Expunge | OpenCnt 0, empty queue, not processing, sentinel seglist | Returns stored BPTR; transport closed once; DELEXP clear | N/A |
| OpenCnt busy | OpenCnt ≥ 1 | Return 0; DELEXP set; no transport close | Deferred |
| Queue / in-progress | Queued or `io_processing` | Return 0; DELEXP set; no close until idle | Deferred |
| Delayed complete | DELEXP set, then last close or worker drain to idle | Close/teardown once; last close returns stored BPTR when it completes unload | N/A |
| Repeat after complete | Idle drain/expunge again | No second `fn_transport_close` | N/A |
| Open cancels | Expunge while open, then another Open | DELEXP cleared; later idle without DELEXP does not close | N/A |

</frozen-after-approval>

## Code Map

- `repos/fujinet-nio-driver/amiga/disk.device/fujinet_disk_device.c:292-299` -- `device_expunge` comment “No unload”; sets DELEXP and calls complete.
- `repos/fujinet-nio-driver/amiga/disk.device/fujinet_disk_device.c:372-391` -- `complete_pending_expunge` busy-gates then discard/close/`client_initialized`, **returns 0**. Replace with nio-like return of `segment_list` + guest worker stop/`Remove`/`FreeMem`.
- `repos/fujinet-nio-driver/amiga/disk.device/fujinet_disk_device.c:258-289` -- `device_close` delayed path already returns complete’s BPTR (today always 0).
- `repos/fujinet-nio-driver/amiga/disk.device/fujinet_disk_device.c:754-768` -- `worker_drain` voids complete at idle (`OpenCnt` may already be 0).
- `repos/fujinet-nio-driver/amiga/disk.device/fujinet_disk_device.c:215-231` -- guest worker `AllocSignal`/`AllocMem`/`AddTask`; pair teardown in expunge.
- `repos/fujinet-nio-driver/amiga/disk.device/fujinet_disk_device.c:977-981` -- native reset `device_init(..., 0, ...)`; change sentinel like nio.
- `repos/fujinet-nio-driver/amiga/nio.device/fujinet_nio_device.c:374-411` -- **copy this structure** (`#ifndef FUJINET_NIO_NATIVE_TEST` → disk’s native macro).
- `repos/fujinet-nio-driver/amiga/nio.device/fujinet_nio_device.c:568` -- native init `(BPTR)1`.
- `repos/fujinet-nio-driver/amiga/tests/test_fujinet_disk_resident.c:263-375` -- asserts idle/last-close return **0**; flip to sentinel BPTR like `test_fujinet_nio_device.c:614-686`. Keep deferral and “close once” checks.
- `repos/fujinet-nio-driver/amiga/Makefile` -- `make tests` / `make native`.

**Read-only:** `fumount.c`; nio Expunge behavior (mirror only); Amiberry sequences; `fujinet-load-resident.c`.

## Tasks & Acceptance

**Execution:**
- [ ] `repos/fujinet-nio-driver/amiga/disk.device/fujinet_disk_device.c` -- Idle Expunge returns `segment_list` and guest-unloads; defer when open/busy; no self-free on the worker -- CAP-4.
- [ ] `repos/fujinet-nio-driver/amiga/tests/test_fujinet_disk_resident.c` -- Native matrix: busy 0+DELEXP; idle/delayed complete returns sentinel; close-once; open cancels DELEXP.
- [ ] `repos/fujinet-nio-driver/amiga/README.md` -- Idle Expunge returns the `InitResident` seglist (no unload CLI).

**Acceptance Criteria:**
- Given OpenCnt 0 and an idle queue, when Expunge runs, then the stored seglist is returned and transport has closed once.
- Given OpenCnt, queued I/O, or in-progress work, when Expunge runs, then it returns 0, sets `LIBF_DELEXP`, and does not abort that work.
- Given deferred Expunge, when the last close (or worker idle) makes the device safe, then teardown runs once and a completing close returns the stored seglist.
- Given native tests, when they run, then they do not require real Exec `DeviceList` removal (guest CAP-9 is Story 4).

## Spec Change Log

## Design Notes

Nio never completes Expunge from its worker; disk `worker_drain` does, because OpenCnt can already be 0 with queued I/O. Resource teardown may run there; Exec `UnLoadSeg` needs the BPTR from `RemDevice`/`CloseDevice` on another task. Do not copy nio’s `Remove`/`FreeMem` onto the worker stack.

## Verification

**Commands:**
- `source "$NIO_WORKSPACE/scripts/env.sh" && make -C "$NIO_WORKSPACE/repos/fujinet-nio-driver/amiga" tests` -- host native suite including `test_fujinet_disk_resident`.
- `source "$NIO_WORKSPACE/scripts/env.sh" && make -C "$NIO_WORKSPACE/repos/fujinet-nio-driver/amiga" native` -- compiles guest `RemTask`/`Remove`/`FreeMem` path.

Do not run full `scripts/amiga-tests` or add a CAP-9 pytest node in this story.
