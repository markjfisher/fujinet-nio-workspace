---
title: 'Make Amiga FIN a Slot Catalog client'
type: 'bugfix'
created: '2026-08-29'
status: 'done'
review_loop_iteration: 0
baseline_commit: '30bb7f42fe72b682b0b7b342a926c64a7be7431a'
context:
  - 'docs/agent-test-policy.md'
  - 'docs/amiga/disk-media-architecture.md'
  - 'repos/fujinet-nio/docs/slot_state.md'
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** On Amiga, `FIN 0 filename.adf` writes the private AppStore record
directly. It retains the bare filename even when `FHOST` has selected a TNFS
directory. `FMOUNT` later obtains that Slot Catalog entry, but candidate
inspection cannot use an unqualified target, so the user sees `Unsupported
candidate media`. The full-URI form also currently reports persistence failure
on real hardware.

**Approach:** Make FIN use the typed Slot Catalog service so the service
resolves a relative filename against current HostService state and persists its
canonical URI. Preserve the existing FIN/FOUT command syntax and leave
FMOUNT/DiskDevice responsible only for selecting an already-canonical catalog
entry and mounting it to a DNx: unit.

## Boundaries & Constraints

**Always:** Write a focused test before production behavior; cover the real
Amiga command chain `FHOST` → `FIN` → `FMOUNT` → `Dir DN0:`. The test must
cover both a relative filename and a full TNFS URI, and must verify the stored
Slot Catalog entry is canonical. Keep the existing typed Slot Catalog, Host
Service, AppStore, DiskDevice, broker, and wire contracts unchanged. Keep the
work compatible with future transports: FIN remains an ordinary
`fujinet-nio-lib` application and does not access `serial.device` or the
broker directly.

**Ask First:** Any need to migrate, reinterpret, or delete existing
`config-nio/slot-NNN` records; any change to FIN/FOUT syntax or to the
read-only default semantics.

**Never:** Teach FMOUNT or fujinet-disk.device to resolve bare host paths;
reintroduce a separate Amiga mapping mechanism; fold in the independent
`CMD_UPDATE` / `Assign DN2: DISMOUNT` requester regression; run the full
Amiberry suite.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|---|---|---|---|
| Relative FIN | Current host is `host:/`, `FIN 0 standard.adf` | Slot 0 contains canonical `host:/standard.adf`; `FMOUNT 0 DN0: RO` and `Dir DN0:` succeed | No private AppStore encoding in FIN |
| Full FIN | `FIN 0 host:/standard.adf` | Same valid canonical entry and mount flow | Return a clear FIN failure only if typed Put rejects it |
| Invalid target | Current host unavailable or target cannot resolve | Existing valid slot remains unchanged | FIN reports failure and exits non-zero |
| Clear | `FOUT 0` | Slot 0 is removed through the typed catalog | Existing command output/exit contract preserved |

</frozen-after-approval>

## Code Map

- `repos/nio-core-apps/apps/fin.c` — CLI entry point; currently delegates to
  `fnsvc_set_mount()` then re-reads the record for its status line.
- `repos/nio-core-apps/apps/fout.c` — same legacy helper for clearing a slot;
  keep FIN/FOUT aligned if the helper becomes Slot Catalog based.
- `repos/nio-core-apps/src/common/fnsvc.c` — `fnsvc_get_mount()` and
  `fnsvc_set_mount()` directly encode/read private `config-nio/slot-NNN`
  records. Replace this private client behavior with typed catalog calls or
  introduce narrowly named catalog helpers here.
- `repos/fujinet-nio-lib/include/fujinet-nio.h` and
  `src/common/fn_slot_catalog_{get,put,delete}.c` — existing public typed API;
  reuse without protocol changes.
- `repos/fujinet-nio/src/lib/slot_catalog_service.cpp` — service already
  resolves `Put` targets through `HostState::resolve_target()` and persists
  canonical URIs; read-only evidence, not a change target.
- `repos/fujinet-nio/docs/slot_state.md` — canonical contract: clients must
  use Slot Catalog Put and must not depend on its AppStore schema.
- `integration-tests/amiberry/conftest.py` — creates deterministic ADFs and
  catalog data. It currently pre-seeds records directly for test isolation.
- `integration-tests/amiberry/tests.toml`, a new focused startup sequence, and
  a new focused pytest module — add one `wb32/a1200-030` guest case using the
  real Amiga FIN and FMOUNT binaries.

## Tasks & Acceptance

**Execution:**

- [x] `integration-tests/amiberry/tests.toml`, new startup sequence, and new
  pytest module — add the initially failing real command-chain test for
  relative and full URI FIN input, catalog canonicalization, FMOUNT, and a
  normal `Dir DN0:`.
- [x] `repos/nio-core-apps/src/common/fnsvc.c`, `apps/fin.c`, and `apps/fout.c`
  — replace private slot-record writes/reads with the public Slot Catalog API,
  preserving the CLI surface and propagating typed failures.
- [x] Focused tests — make the new guest case pass and run the minimum build
  checks for the application and service owners touched.
- [x] `completed/amiga-fin-slot-catalog.md` — maintain the user-facing backlog
  record; do not mix in the independent writable-media regression.

**Acceptance Criteria:**

- Given `FHOST host:/`, when FIN receives `standard.adf`, then the catalog
  stores `host:/standard.adf` and `FMOUNT 0 DN0: RO` makes `KNOWN.TXT`
  visible through `Dir DN0:`.
- Given the full URI, when FIN stores it, then the same mount and directory
  access succeeds.
- Given a failed relative resolution, when FIN exits, then the prior valid
  catalog entry remains usable.
- Given `FOUT 0`, when it completes, then typed catalog Get reports slot 0
  absent.

## Spec Change Log

## Design Notes

The backing AppStore schema happens to be shared today, but that is private to
SlotCatalog. Direct AppStore writes bypass `Put` and therefore bypass current
host/path resolution. The correction is client-layer only: use the existing
typed API at the established layer boundary rather than broadening FMOUNT.

## Verification

**Commands:**

- `source scripts/env.sh && make -C repos/nio-core-apps TARGET=amiga` —
  expected: FIN/FOUT and Amiga command binaries compile.
- `source scripts/env.sh && ./build.sh -cp fujibus-pty-debug && ctest --test-dir build/fujibus-pty-debug --output-on-failure` from `repos/fujinet-nio` — expected: existing Slot Catalog service behavior remains green.
- `source scripts/env.sh && uv run pytest --run-amiga --amiga-env wb32 --amiga-machine a1200-030 integration-tests/amiberry/test_amiga_fin_slot_catalog.py::test_fin_uses_slot_catalog_for_relative_and_full_targets` — passed: relative and full FIN flows mount and list deterministic ADFs; FOUT removes its Slot Catalog entry.
