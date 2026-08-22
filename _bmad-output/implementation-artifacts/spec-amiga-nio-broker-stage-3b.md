---
title: 'Amiga NIO broker Stage 3B — bootstrap and guest race proof'
type: 'feature'
created: '2026-08-22'
status: 'draft'
review_loop_iteration: 0
context:
  - docs/amiga/nio-broker-architecture.md
  - docs/agent-test-policy.md
  - docs/amiga/amiberry-testing.md
  - backlog/nio-broker.md
  - _bmad-output/implementation-artifacts/spec-amiga-nio-broker-stage-3.md
  - _bmad-output/implementation-artifacts/spec-amiga-nio-broker-stage-3a.md
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** After 3A, guests still copy/load `fujinet-nio.device` only on the isolated image, so DiskDevice/FLS can initialize NIO without the broker and the original serial-ownership race is unproven gone.

**Approach:** Environment-only bootstrap: install and `LoadResident` `fujinet-nio.device` **before** any app or `fujinet-disk.device` NIO init. Keep isolated broker exclusive of the old shim and of disk.device. Rebuild disk.device against the cut-over lib with **no** DiskDevice semantics redesign. Prove the original race with broker-backed inspect-catalog (disk NIO then immediate FLS). Do not start until 3A Verification has run and passed. Parent Stage 3 completes only with 3A **and** this spec accepted.

## Boundaries & Constraints

**Always:**
- Load order: `fujinet-nio.device` resident → optional `fujinet-disk.device` → any `fn_transport_init` (§8). Library must not auto-load the broker.
- Isolated `nio_broker` images stay exclusive of `driver` / FLS / serial-direct clients (`conftest.py` reject both flags).
- Normal Amiga NIO cases (driver **and** CLI-only) must copy `fujinet-nio.device` onto the HDF and prepend `fujinet-load-resident DEVS:fujinet-nio.device fujinet-nio.device` **ahead of** sequence steps. Do not rewrite DiskDevice/FLS assertions or startup operations except that prepend/install. Isolated sequences already load nio — do **not** double-prepend there.
- `fujinet-disk.device` keeps calling `fn_init` / `fn_transport_exchange_buffers` / idle-close at `fujinet_disk_device.c:745`. Idle-close now closes the **broker** context, not serial; **leave it** (Stage 4). No Trackdisk/FMOUNT redesign.
- Old serial-direct shim and broker must never coexist as competing serial owners in any Amiberry case this spec runs.
- Run named Verification commands, including a source search. Check Stage 3 backlog boxes only after 3A and 3B both passed.

**Ask First:**
- Changing public `FujiNetNIORequest` or DiskDevice mount/geometry semantics.
- Removing idle-close (Stage 4).

**Never:**
- Edit `fn_transport.c` except if 3A left a compile break blocking this spec (then stop and report).
- Fold DiskDevice/FLS into `nio-broker-isolated`.
- Default to `scripts/amiga-tests` (~full suite) as the 3B gate.
- Start Stage 4/5. Create epics/stories. Treat 3B as a second Stage 3 checkpoint.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Isolated still isolated | `nio-broker-isolated` | Same 2B assertions; disk.device and FLS absent | Fail if `driver` also set |
| Bootstrap driver case | `driver: true` HDF | `Devs/fujinet-nio.device` present; LoadResident nio **before** disk/app NIO | Missing broker → init `FN_ERR_NOT_FOUND`, not serial contention |
| Original race | DiskDevice NIO completes; shell immediately `FLS`; both via broker | inspect-catalog assertions pass; no `serial.device` OpenDevice contention | Repeat must not flake on OpenDevice busy |
| Idle-close remains | Disk worker FIFO empty | Still `fn_transport_close` on disk context | Serial stays with broker backend |
| Source invariant | Production Amiga NIO tree | Classified search: broker serial backend is the sole production FujiNet NIO `serial.device` owner | `fn_transport.c` has no serial/timer ownership; disk/apps have none; `try_open_serial` is test-only |

</frozen-after-approval>

## Code Map

- 3A rewritten `fn_transport.c` — **consume** via `TARGET=amiga-driver` / `amiga` rebuilds; do not reopen the shim design.
- `repos/fujinet-nio-driver/amiga/disk.device/fujinet_disk_device.c` L118/135/154 `fn_init`; L745 idle-close — **no Stage 3 semantics change**; rebuild only.
- `repos/fujinet-nio-driver/amiga/channels/rs232/fujinet_nio_client.c` — still `fn_init` / `fn_transport_exchange_buffers`; **read-only**.
- `repos/fujinet-nio-driver/Makefile` L15–16 + `amiga/Makefile` `all`/`native` — `make amiga` already builds `fujinet-nio.device`; CLI-only Amiberry cases must **build and copy** it too (today only `nio_broker` copies `--nio-device`).
- `scripts/build-amiga-test-disk` L102–142 — `--nio-device` copies to `Devs/`; `--load-driver` prepends **disk** only. Add nio LoadResident prepend (or equivalent) so nio is first.
- `integration-tests/amiberry/conftest.py` L754–861 — `nio_broker` vs `driver` exclusive; driver branch `make amiga` + `--disk-device` without `--nio-device`. Extend: non-isolated NIO cases get `--nio-device` + nio prepend; keep isolated without disk.
- `integration-tests/amiberry/startup/*.sequence` — **leave operations**; inspect-catalog already does disk NIO then `FLS` L55–56.
- `integration-tests/amiberry/test_diskdevice_adf.py` L103–122 — `test_catalog_inspection_preserves_live_dd_handler` / case `diskdevice-inspect-catalog`.
- `integration-tests/amiberry/test_nio_broker.py` — **keep** isolated assertions.
- `repos/fujinet-nio-driver/amiga/nio.device/fujinet_nio_serial_backend.c` L25, L241 — **only** production `OpenDevice("serial.device")` for FujiNet NIO.
- `repos/fujinet-nio-driver/amiga/tools/fujinet-nio-exchange.c` L127–145 `try_open_serial` — **test probe** (serial exclusivity on isolated image), not production path.
- `repos/nio-core-apps/README.md` L36–37 + `repos/nio-apps/README.md` L54–57 + `docs/amiga/amiberry-testing.md` L794–797 — stop saying apps/lib open `serial.device` directly / atexit-releases serial.
- `backlog/nio-broker.md` Stage 3 — boxes after 3A+3B commands ran.

## Tasks & Acceptance

**Execution:**
- [ ] `scripts/build-amiga-test-disk` + `integration-tests/amiberry/conftest.py` -- copy nio.device and LoadResident it first on all non-isolated NIO cases -- §8 bootstrap
- [ ] Rebuild `fujinet-disk.device` against cut-over `amiga-driver` -- disk uses broker via lib; no idle-close edit
- [ ] Isolated pytest still passes; inspect-catalog pytest run **twice** -- original race gone; no shim+broker coexistence
- [ ] App/core-apps READMEs + `amiberry-testing.md` serial sentences -- Stage 3 README remainder
- [ ] Classified source search (serial/timer symbols **and** `OpenDevice` sites) -- Stage 3 invariant; literal `OpenDevice("serial.device")` regex is not enough
- [ ] `backlog/nio-broker.md` -- Stage 3 boxes only after 3A and 3B Verification ran

**Acceptance Criteria:**
- Given 3A is `done`, when 3B builds a `driver: true` image, then `fujinet-nio.device` is resident before disk or CLI NIO.
- Given disk/device NIO then immediate FLS both through the broker, when `test_catalog_inspection_preserves_live_dd_handler` runs twice, then both runs pass without serial OpenDevice contention.
- Given classified hits for `serial.device` / `timer.device` symbols and every `OpenDevice` site, when reviewed, then production `fn_transport.c` has no serial/timer ownership, disk.device/apps have no physical serial ownership, the broker serial backend is the sole production FujiNet NIO `serial.device` owner, and `fujinet-nio-exchange` `try_open_serial` is test-only.

## Spec Change Log

- 2026-08-22: Human edit — source-search verification must find symbol-based `OpenDevice` sites, not only a literal `OpenDevice(.*serial.device` regex.

## Design Notes

Idle-close can remain: after cut-over it drops the disk image’s **broker** OpenCnt; the backend keeps `serial.device`. That is why Stage 3 can prove the race gone without Stage 4.

Do not change inspect-catalog assertions; FLS is already the last NIO step.

## Verification

3B is incomplete if these were not run. Compile-only is not sufficient. Do not substitute `scripts/amiga-tests`.

**Commands (after `source "$NIO_WORKSPACE/scripts/env.sh"`):**
- `cd "$NIO_WORKSPACE/repos/fujinet-nio-lib" && make check` -- expected: still passes after any 3B-driven lib rebuild
- `cd "$NIO_WORKSPACE/repos/fujinet-nio-driver/amiga" && make tests && make native` -- expected: natives pass; `fujinet-nio.device` and `fujinet-disk.device` both produced
- `uv run pytest --run-amiga --amiga-env wb32 --amiga-machine a1200-030 integration-tests/amiberry/test_nio_broker.py::test_isolated_exchange` -- expected: isolated PASS; no disk.device/FLS
- `uv run pytest --run-amiga --amiga-env wb32 --amiga-machine a1200-030 integration-tests/amiberry/test_diskdevice_adf.py::test_catalog_inspection_preserves_live_dd_handler` -- expected: PASS (run 1)
- Repeat the previous inspect-catalog pytest command -- expected: PASS (run 2); no serial OpenDevice contention
- From `$NIO_WORKSPACE`, run **both** searches and **classify every hit** (do not stop at a literal `OpenDevice("serial.device")` regex; backend/shim pass a name variable):
  1. `rg -n -g '!**/.*' 'serial\\.device|timer\\.device|TIMERNAME|serial_device_name' repos/fujinet-nio-lib repos/fujinet-nio-driver/amiga repos/nio-core-apps repos/nio-apps`
  2. `rg -n -g '!**/.*' 'OpenDevice\\s*\\(' repos/fujinet-nio-lib/src/platform/amiga repos/fujinet-nio-driver/amiga repos/nio-core-apps repos/nio-apps`
  -- expected classification:
  - production `fn_transport.c`: **no** `serial.device` / `timer.device` / `TIMERNAME` ownership and no `OpenDevice` of those devices
  - `disk.device` and `nio-core-apps` / `nio-apps`: **no** physical serial ownership
  - sole production FujiNet NIO `serial.device` owner: `fujinet_nio_serial_backend.c` (`serial_device_name` + `OpenDevice`)
  - `fujinet-nio-exchange.c` `try_open_serial`: **test-only** probe, not production
  - comments/READMEs that only describe the cut-over are not ownership

**Manual checks (if no CLI):**
- Confirm non-isolated guest Startup-Sequence lists nio `LoadResident` before disk `LoadResident` or FLS/`fn_transport_init`
