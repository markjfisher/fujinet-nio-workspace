---
title: 'Add fujinet-unload-resident'
type: 'feature'
created: '2026-09-03'
status: 'done'
baseline_commit: '723b7249297d20e867abbd643616989636da5bf1'
review_loop_iteration: 0
context:
  - '{project-root}/_bmad-output/specs/spec-amiga-fumount-clean-driver-removal/SPEC.md'
  - '{project-root}/docs/agent-test-policy.md'
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** Operators can `RemDevice` only by hand; there is no CLI that requests unload and reports whether the Exec device actually left the list. Disk Expunge already returns a seglist (Story 2); this story is the operator tool that triggers it.

**Approach:** Add `fujinet-unload-resident <device-name>` beside the loader. One name per run. Two separate critical sections per RKM: first `Forbid` covers `FindName` + `RemDevice` (if found) + discard old pointer, `Permit`; second `Forbid` / fresh `FindName` / `Permit` reports unloaded vs still-resident. Wire `make native` and HDF/`NIO:` install like the loader. Document disk first: `fujinet-unload-resident fujinet-disk.device`.

## Boundaries & Constraints

**Always:**
- Exactly one argv: Exec device name (e.g. `fujinet-disk.device`). Usage on wrong argc → `RETURN_ERROR`.
- Two separate critical sections:
  ```
  Forbid
    FindName DeviceList
    if found: RemDevice(node)
    never touch old Device* again
  Permit

  Forbid
    fresh FindName DeviceList
  Permit
  ```
- If first `FindName` misses: print `Not resident: <name>`, `RETURN_FAIL`; do not call `RemDevice`.
- If found: `RemDevice` that node inside first `Forbid`. Second lookup: miss → `Unloaded: <name>`, `RETURN_OK`. Hit → `Still resident: <name>`, `RETURN_FAIL`.
- "Still resident" means unload deferred (open, queued/in-progress I/O, or drained-worker / LIBF_DELEXP from Story 2). A second call after idle may succeed.
- Install on `C:` whenever the loader is installed (HDF write + `NIO:` share). Copy docs next to the loader.

**Ask First:**
- Changing disk/nio Expunge, FUMOUNT, or adding a CAP-9 Amiberry unload/reload pytest node.

**Never:**
- Story 4 sequence (unload nio, reload, remount). Generic name is allowed; do not add dual-device CLI or reorder recipes here.
- Editing `fujinet_disk_device.c` / nio Expunge. Dereferencing after `RemDevice`. Auto-expunge without `RemDevice`.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Idle disk unload | `fujinet-disk.device` idle, OpenCnt 0 | `Unloaded: fujinet-disk.device`; later FindName miss | N/A |
| Still open/busy | Device in list, RemDevice defers | `Still resident: <name>`; name still on DeviceList | RETURN_FAIL |
| Already gone | Name not on DeviceList | `Not resident: <name>`; no RemDevice | RETURN_FAIL |
| Usage | argc ≠ 2 | stderr Usage: `fujinet-unload-resident DEVICE-NAME` | RETURN_ERROR |

</frozen-after-approval>

## Code Map

- `repos/fujinet-nio-driver/amiga/tools/fujinet-load-resident.c` -- **copy style** (clib2, `RETURN_*`, DeviceList `FindName`). New sibling `fujinet-unload-resident.c`; do not change loader behavior.
- `repos/fujinet-nio-driver/amiga/Makefile:10-39,91-93` -- `RESIDENT_LOADER` pattern: add `RESIDENT_UNLOADER`, `native` dep, `mcrt=clib2` `-lamiga` rule.
- `scripts/build-amiga-test-disk:41-48,117-120` -- `--resident-loader` → `C/fujinet-load-resident`. Add `--resident-unloader` → `C/fujinet-unload-resident` the same way.
- `integration-tests/amiberry/conftest.py:778-889` -- pass unloader whenever `resident_loader` is passed.
- `tools/build/nio_build/tasks.py:341-350` -- same flag on `amiga-test-disk`.
- `tools/build/nio_build/amiga_config.py:243-249` -- add `fujinet-unload-resident` to `NIO:` share (FTP/copy path).
- `tools/build/tests/test_amiga_test_disk.py:27-106` -- expect `--resident-unloader` next to loader.
- `repos/fujinet-nio-driver/amiga/README.md:51-65,135-137` -- replace “does not ship an unload CLI”; example disk unload. Document `Still resident` → repeat after idle (Story 2 drained-worker / LIBF_DELEXP case). Keep Expunge contract from Story 2.
- `docs/amiga/amiberry-testing.md:66-68,107-109` -- `Copy NIO:fujinet-unload-resident` to `C:` beside the loader.

**Read-only:** `fujinet_disk_device.c`, `fumount.c`, Amiberry `startup/*.sequence`, nio Expunge.

## Tasks & Acceptance

**Execution:**
- [x] `repos/fujinet-nio-driver/amiga/tools/fujinet-unload-resident.c` -- CLI per I/O matrix; two-phase Forbid/Permit per Boundaries -- CAP-6.
- [x] `repos/fujinet-nio-driver/amiga/Makefile` -- `make native` builds `build/amiga/fujinet-unload-resident`.
- [x] `scripts/build-amiga-test-disk`, `conftest.py`, `tasks.py`, `amiga_config.py`, `test_amiga_test_disk.py` -- HDF/`NIO:` install like the loader.
- [x] `amiga/README.md` + `docs/amiga/amiberry-testing.md` -- disk unload recipe; pinned stdout strings; `Still resident` → retry after idle (Story 2 deferred case).

**Acceptance Criteria:**
- Given idle `fujinet-disk.device`, when the CLI is run with that name, then stdout is `Unloaded: fujinet-disk.device` and a later `FindName` misses.
- Given the device remains in the list after `RemDevice`, when the CLI finishes, then stdout is `Still resident: <name>` and the process does not read the old pointer.
- Given `make native`, when it succeeds, then `build/amiga/fujinet-unload-resident` exists; HDF/`NIO:` paths install it to `C:` with the loader.

## Spec Change Log

## Verification

**Commands:**
- `source "$NIO_WORKSPACE/scripts/env.sh" && make -C "$NIO_WORKSPACE/repos/fujinet-nio-driver/amiga" native` -- produces `build/amiga/fujinet-unload-resident`.
- `source "$NIO_WORKSPACE/scripts/env.sh" && uv run pytest tools/build/tests/test_amiga_test_disk.py` -- `--resident-unloader` wiring.

Do not run full `scripts/amiga-tests` or add a CAP-9 pytest node (Story 4). Guest smoke of the CLI is Story 4.

## Suggested Review Order

**Core unloader implementation**

- Two-phase Forbid/Permit critical sections; RemDevice between, fresh FindName after
  [`fujinet-unload-resident.c:24`](../../../../repos/fujinet-nio-driver/amiga/tools/fujinet-unload-resident.c#L24)

- First check: device absent, print "Not resident", return FAIL
  [`fujinet-unload-resident.c:31`](../../../../repos/fujinet-nio-driver/amiga/tools/fujinet-unload-resident.c#L31)

- Second check: still present after RemDevice, print "Still resident", return FAIL
  [`fujinet-unload-resident.c:41`](../../../../repos/fujinet-nio-driver/amiga/tools/fujinet-unload-resident.c#L41)

**Build and installation wiring**

- Makefile adds RESIDENT_UNLOADER variable and native target dependency
  [`Makefile:11`](../../../../repos/fujinet-nio-driver/amiga/Makefile#L11)

- Build rule mirrors loader: clib2, -lamiga
  [`Makefile:96`](../../../../repos/fujinet-nio-driver/amiga/Makefile#L96)

- HDF installer accepts --resident-unloader and writes to C:/
  [`build-amiga-test-disk:42`](../../../../scripts/build-amiga-test-disk#L42)

- conftest passes unloader whenever loader is passed
  [`conftest.py:780`](../../../../integration-tests/amiberry/conftest.py#L780)

- NIO: share includes unloader for Copy operations
  [`amiga_config.py:247`](../../../../tools/build/nio_build/amiga_config.py#L247)

**Documentation**

- README replaces "does not ship an unload CLI" with usage and output strings
  [`README.md:64`](../../../../repos/fujinet-nio-driver/amiga/README.md#L64)

- Documents Still resident → retry after idle (Story 2 drained-worker case)
  [`README.md:83`](../../../../repos/fujinet-nio-driver/amiga/README.md#L83)

- Amiberry testing guide adds Copy NIO:fujinet-unload-resident C:
  [`amiberry-testing.md:69`](../../../../docs/amiga/amiberry-testing.md#L69)

**Test infrastructure**

- Python test expects --resident-unloader flag in disk build commands
  [`test_amiga_test_disk.py:84`](../../../../tools/build/tests/test_amiga_test_disk.py#L84)

- Test validates unloader path passed correctly
  [`test_amiga_test_disk.py:110`](../../../../tools/build/tests/test_amiga_test_disk.py#L110)
