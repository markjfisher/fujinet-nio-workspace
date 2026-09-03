---
title: 'Disk device Expunge actually unloads'
type: 'feature'
created: '2026-09-03'
status: 'done'
baseline_commit: '0b30f64ec86a46a30ba7f560aa7cf76b65eec88f'
review_loop_iteration: 0
context:
  - '{project-root}/_bmad-output/completed-specs/spec-amiga-fumount-clean-driver-removal/SPEC.md'
  - '{project-root}/docs/agent-test-policy.md'
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** Idle `fujinet-disk.device` Expunge sets `LIBF_DELEXP` and closes transport but returns 0, never `Remove`s the node or the `InitResident` seglist, so `RemDevice` cannot unload the binary.

**Approach:** Mirror `fujinet-nio.device` idle Expunge on a non-worker task: defer while open or busy; when safe, stop the worker, close transport, discard change registrations, `Remove`/free the base (guest only), and return the stored `LoadSeg` list. **The worker may make the device expungeable, but it must not expunge itself.**

## Boundaries & Constraints

**Always:**
- Defer (`LIBF_DELEXP`, return 0) while `OpenCnt != 0`, the I/O queue is nonempty, or `io_processing != 0`. Do not abort in-flight I/O.
- Full teardown only from Expunge or last `CloseDevice` on a task that is not the disk worker: `discard_change_requests`, `fn_transport_close()`, clear per-unit `client_initialized`, return `base->segment_list`. Guest (`#ifndef FUJINET_DISK_NATIVE_TEST`): `RemTask` + stack/`FreeSignal`, then `Forbid`/`Remove`/`FreeMem` NegSize+PosSize like nio. Native tests skip `Remove`/`FreeMem`/`RemTask`.
- If Expunge is deferred because `OpenCnt != 0`, the final `CloseDevice()` may complete teardown and return the stored seglist (queue and `io_processing` must already be idle).
- If Expunge is deferred because queued/in-progress I/O remains while `OpenCnt == 0`, the worker only drains that I/O and **leaves `LIBF_DELEXP` set**. It must not perform partial or final teardown (`fn_transport_close`, discard change ints, `Remove`, `FreeMem`, worker stack/signal teardown, etc.). A later explicit `RemDevice()` / Expunge from another task does the full teardown and returns `base->segment_list` to Exec.
- Reason: if the worker completed Expunge, the BPTR would have nowhere useful to go (`RemDevice` already returned; there may be no later `CloseDevice`). Partial teardown is also unsafe: a later `OpenDevice()` clears `LIBF_DELEXP` and could revive a half-torn-down device.
- `OpenDevice` still clears `LIBF_DELEXP`. Ordinary idle without `LIBF_DELEXP` must not close transport.
- Native `device_init` for tests stores a non-zero sentinel seglist (nio uses `(BPTR)1`).

**Ask First:**
- Adding Amiberry CAP-9, `fujinet-unload-resident`, or FUMOUNT changes in this story.

**Never:**
- Worker self-expunge or any worker-side teardown (partial or complete).
- Unload while a live `DNx:` handler still holds the device (Story 1 owns handler DIE).
- Unload CLI (Story 3), guest unload/reload sequence (Story 4), nio Expunge redesign, auto-expunge on last close without `RemDevice`/`LIBF_DELEXP`.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Idle Expunge | OpenCnt 0, empty queue, not processing, sentinel seglist | Returns stored BPTR; transport closed once; DELEXP clear | N/A |
| OpenCnt busy | OpenCnt ≥ 1 | Return 0; DELEXP set; no teardown | Deferred |
| Last CloseDevice idle | DELEXP set; last close drops OpenCnt to 0 with empty queue / not processing | Close completes teardown; returns stored BPTR | N/A |
| Worker drain, already closed | DELEXP set; OpenCnt 0; queued/in-progress then worker drain to idle | Drain I/O only; **leave LIBF_DELEXP**; no teardown | N/A |
| Next RemDevice after drain | OpenCnt 0, idle, LIBF_DELEXP still set | Full teardown; returns stored BPTR | N/A |
| Repeat after complete | Idle drain/expunge again | No second `fn_transport_close` | N/A |
| Open cancels | Expunge while open, then another Open | DELEXP cleared; later idle without DELEXP does not close | N/A |

</frozen-after-approval>

## Code Map

- `repos/fujinet-nio-driver/amiga/disk.device/fujinet_disk_device.c:292-299` -- `device_expunge` comment “No unload”; sets DELEXP and calls complete.
- `repos/fujinet-nio-driver/amiga/disk.device/fujinet_disk_device.c:372-391` -- `complete_pending_expunge` busy-gates then discard/close/`client_initialized`, **returns 0**. Replace with nio-like return of `segment_list` + guest worker stop/`Remove`/`FreeMem`. Must not be invoked for teardown from the worker.
- `repos/fujinet-nio-driver/amiga/disk.device/fujinet_disk_device.c:258-289` -- `device_close` delayed path already returns complete’s BPTR (today always 0). Keep this as the OpenCnt-deferred complete path.
- `repos/fujinet-nio-driver/amiga/disk.device/fujinet_disk_device.c:754-768` -- `worker_drain` currently `(void)complete_pending_expunge` at idle. Stop calling teardown from the worker; drain I/O only and leave `LIBF_DELEXP`.
- `repos/fujinet-nio-driver/amiga/disk.device/fujinet_disk_device.c:215-231` -- guest worker `AllocSignal`/`AllocMem`/`AddTask`; pair teardown in Expunge/`CloseDevice` on a non-worker task.
- `repos/fujinet-nio-driver/amiga/disk.device/fujinet_disk_device.c:977-981` -- native reset `device_init(..., 0, ...)`; change sentinel like nio.
- `repos/fujinet-nio-driver/amiga/nio.device/fujinet_nio_device.c:374-411` -- **copy this structure** (`#ifndef FUJINET_NIO_NATIVE_TEST` → disk’s native macro). Nio does not expunge from its worker.
- `repos/fujinet-nio-driver/amiga/nio.device/fujinet_nio_device.c:568` -- native init `(BPTR)1`.
- `repos/fujinet-nio-driver/amiga/tests/test_fujinet_disk_resident.c:263-375` -- idle/last-close currently expect return **0**; last-close-complete → sentinel BPTR. In-progress/queued cases must **not** expect transport close on drain; assert DELEXP remains, then a follow-up native expunge returns the sentinel. Open-cancels stays.
- `repos/fujinet-nio-driver/amiga/Makefile` -- `make tests` / `make native`.

**Read-only:** `fumount.c`; nio Expunge behavior (mirror only); Amiberry sequences; `fujinet-load-resident.c`.

## Tasks & Acceptance

**Execution:**
- [x] `repos/fujinet-nio-driver/amiga/disk.device/fujinet_disk_device.c` -- Idle Expunge/`CloseDevice` on a non-worker task returns `segment_list` and guest-unloads; worker drain never tears down -- CAP-4.
- [x] `repos/fujinet-nio-driver/amiga/tests/test_fujinet_disk_resident.c` -- Native matrix: busy 0+DELEXP; last close returns sentinel; worker-idle leaves DELEXP and a later expunge returns sentinel; open cancels DELEXP.
- [x] `repos/fujinet-nio-driver/amiga/README.md` -- Idle Expunge returns the `InitResident` seglist (no unload CLI).

**Acceptance Criteria:**
- Given OpenCnt 0 and an idle queue, when Expunge runs on a non-worker task, then the stored seglist is returned and transport has closed once.
- Given OpenCnt, queued I/O, or in-progress work, when Expunge runs, then it returns 0, sets `LIBF_DELEXP`, and does not abort that work.
- Given deferred Expunge because OpenCnt was non-zero, when the last `CloseDevice` makes the device idle, then teardown runs once and that close returns the stored seglist.
- Given deferred Expunge because I/O was busy with OpenCnt already 0, when the worker drains to idle, then `LIBF_DELEXP` stays set, no teardown runs, and the next Expunge/`RemDevice` from another task completes and returns the stored seglist.
- Given native tests, when they run, then they do not require real Exec `DeviceList` removal (guest CAP-9 is Story 4).

## Spec Change Log

## Design Notes

The worker may empty the queue so the device is *expungeable*; it must not expunge. Today `worker_drain` calls `complete_pending_expunge` and native tests expect transport close there — both must change. Last `CloseDevice` is the only delayed path that can return a BPTR to Exec besides a later `RemDevice`.

## Verification

**Commands:**
- `source "$NIO_WORKSPACE/scripts/env.sh" && make -C "$NIO_WORKSPACE/repos/fujinet-nio-driver/amiga" tests` -- host native suite including `test_fujinet_disk_resident`.
- `source "$NIO_WORKSPACE/scripts/env.sh" && make -C "$NIO_WORKSPACE/repos/fujinet-nio-driver/amiga" native` -- compiles guest `RemTask`/`Remove`/`FreeMem` path.

Do not run full `scripts/amiga-tests` or add a CAP-9 pytest node in this story.

## Suggested Review Order

**Core teardown contract**

- Idle Expunge now returns stored seglist; worker never tears down.
  [`fujinet_disk_device.c:377`](../../../../repos/fujinet-nio-driver/amiga/disk.device/fujinet_disk_device.c#L377)

- Guest path stops worker, closes transport once, then Remove/FreeMem.
  [`fujinet_disk_device.c:406`](../../../../repos/fujinet-nio-driver/amiga/disk.device/fujinet_disk_device.c#L406)

- Worker drain only finishes I/O; no teardown call.
  [`fujinet_disk_device.c:792`](../../../../repos/fujinet-nio-driver/amiga/disk.device/fujinet_disk_device.c#L792)

**Init and sentinel**

- Native init stores sentinel `(BPTR)1` not 0.
  [`fujinet_disk_device.c:1001`](../../../../repos/fujinet-nio-driver/amiga/disk.device/fujinet_disk_device.c#L1001)

- Initialize worker_signal and transport_closed.
  [`fujinet_disk_device.c:208`](../../../../repos/fujinet-nio-driver/amiga/disk.device/fujinet_disk_device.c#L208)

**Native test matrix**

- Idle expunge → sentinel; last close → sentinel.
  [`test_fujinet_disk_resident.c:271`](../../../../repos/fujinet-nio-driver/amiga/tests/test_fujinet_disk_resident.c#L271)

- Worker drain leaves DELEXP; follow-up expunge returns sentinel.
  [`test_fujinet_disk_resident.c:347`](../../../../repos/fujinet-nio-driver/amiga/tests/test_fujinet_disk_resident.c#L347)

**Documentation**

- README notes idle Expunge returns seglist; no unload CLI.
  [`README.md:61`](../../../../repos/fujinet-nio-driver/amiga/README.md#L61)
