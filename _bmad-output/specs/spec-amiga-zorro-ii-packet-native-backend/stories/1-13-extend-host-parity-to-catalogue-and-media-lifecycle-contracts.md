---
title: '1-13 Extend host parity to catalogue and media lifecycle contracts'
type: feature
created: '2026-09-17'
status: done
baseline_commit: 28c7e33abc74016cc892e21b1f99a7426f01bf3e
owner_baseline_commit: 5ed96128972b9aafa44381319cd6f2c3b4028224
review_loop_iteration: 0
spec_checkpoint: false
done_checkpoint: false
context:
  - '{project-root}/docs/agent-test-policy.md'
  - '{project-root}/repos/fujinet-nio/AGENTS.md'
---

<frozen-after-approval reason="approved Story 1.13; routine checkpoints disabled by execution-gates.md">

## Intent

**Problem:** Existing catalogue and media lifecycle tests do not establish equivalent behavior through serial and native FujiBus framing.

**Approach:** Exercise real SlotCatalogService and DiskDevice through both production transports, using isolated disposable DD/HD ADF storage and independent protocol/state oracles.

## Boundaries & Constraints

**Always:** Check complete decoded replies (device, command, status, exact payload), independent backing bytes, persisted state and non-target slots. Catalogue indices and runtime slots are distinct. Reuse accepted 1.7/1.8 evidence and production seams. Own only new firmware test files and this record; you are not alone in the workspace, so accommodate other edits without reverting them.

**Ask First:** Production behavior changes, public ABI changes or unresolved contract contradictions.

**Never:** Reopen completed stories, change shared fake_fs or existing parity helpers, add formats, fabricate handler replies, claim hardware or Amiga FMOUNTRESTORE/trackdisk acceptance, push, or add co-author trailers.

## I/O & Edge-Case Matrix

| Input/state | Expected behavior |
|---|---|
| Catalogue Put/Get indices above 8; independent runtime slots 1 and 8 | Exact canonical URI/RO entries; selected media mounted independently with DD/HD authoritative geometry |
| DD-to-DD and DD-to-HD-to-DD replacement | Expected media/geometry and changed flag; other slot and all unmodified backing bytes remain intact |
| ClearChanged, write/flush, eject/remount | Per-slot changed/dirty/RO flags follow established service semantics; full written image matches seed plus intended sector; empty read is NotReady |
| Reconstruct services over retained persisted bytes | Catalogue index/URI/RO retained; firmware runtime recovery stages saved mappings, then Info activates correct media/mode; ejected mappings stay absent |
| Invalid/missing catalogue/media and RO write | Exact established service errors; protected media and non-target slot remain unchanged; record existing failed replacement semantics rather than assume rollback |

</frozen-after-approval>

## Code Map

Workspace-relative; production files are read-only evidence.

- `repos/fujinet-nio/tests/disk_serial_native_parity.h`: reuse channel doubles and exchange pattern via inclusion or test-local adaptation. Existing exchange hardcodes DiskDevice/0xFC; new fixture needs VirtualDevice and explicit endpoint (catalogue 0xF2). Preserve full-response oracles from corrected 1.8.
- `repos/fujinet-nio/tests/test_slot_catalog_service.cpp:85`: real SlotCatalogService with shared AppStore/StorageManager. Use independent MemoryFileSystem("host") per path. Put 0x02 payload `[1,index,RO?2:0,u16 uriLen,uri]`; Get 0x01 `[1,index]`; entry `[1,valid|RO,index,u16 uriLen,uri]`. Delete 0x03.
- `repos/fujinet-nio/tests/test_disk_device_protocol.cpp:827`: restart recovery; `src/lib/disk_device.cpp:260` loads `/fujinet-runtime-mounts.tsv`, stages pending mounts; framed Info activates. Reconstruct service objects, not just transport. Catalogue persistence uses recreated AppStore. This is firmware reset recovery, distinct from Amiga desired mappings and boot RestoreBoot.
- `repos/fujinet-nio/include/fujinet/io/devices/disk_commands.h` and `src/lib/disk_device.cpp`: Mount 01, Unmount 02, Read 03, Write 04, Info 05, ClearChanged 06, Flush 0E. Info flags inserted=1, RO=2, dirty=4, changed=8, geometry=16, error=32. Full Info is 13 bytes. Commands preserve wire slot 1–8.
- `repos/fujinet-nio/tests/fake_fs.h`: existing disposable bytes/flush observation, read-only. Standard media seed: .adf, 512-byte sectors, 1760 DD or 3520 HD, DOS0/1 boot prefix. No filesystem validity claim.
- New `repos/fujinet-nio/tests/disk_catalog_serial_native_parity.h` and `tests/test_disk_catalog_serial_native_parity.cpp`: test-local fixture and suite `disk_catalog_serial_native_parity`. `tests/CMakeLists.txt` discovers test_*.cpp automatically.

## Tasks & Acceptance

- [x] Add isolated real-service serial/native fixture with complete independent response and backing-state expectations.
- [x] Exercise every matrix row, including reconstruction, indices above 8, both capacities and non-target slot assertions.
- [x] Run focused gates, audit coverage and record evidence/review here.

Given equivalent isolated configurations, when catalogue selection and lifecycle operations run through both framers, then independent slots, persistence and change flags match established expectations without limiting catalogue indices to unit numbers.

Given invalid/missing or read-only media, when selected or written, then established errors and protection remain unchanged without new formats or Phase 2 implementation changes.

## Spec Change Log

## Design Notes

Both transports must independently satisfy literal protocol expectations; equality alone is insufficient. Runtime restoration and catalogue persistence are host evidence only. Actual Amiga command/resident integration stays in 1.14. Prerequisites 1.7/1.8 are accepted with corrective firmware revision `f9a430cebee652cf7308100b20a96f0ce2e0b016`; 1.12 continuity accepted at this record's baseline. No sprint-status file exists.

## Verification

Source workspace `scripts/env.sh` first. In `repos/fujinet-nio`:

- `./build.sh -cp fujibus-pty-debug` — existing host preset build and bundled tests.
- `./build/fujibus-pty-debug/tests/fujinet-nio-tests --test-suite=disk_catalog_serial_native_parity` — every new matrix row runs and passes.
- `./build/fujibus-pty-debug/tests/fujinet-nio-tests --test-suite='Disk serial*'` — accepted disk parity regression.
- `./build/fujibus-pty-debug/tests/fujinet-nio-tests --test-case='*Disk*,*SlotCatalog*,*boot_mount*'` — existing service/boot regression coverage.
- `git diff --check` in firmware and workspace; verify production and prior accepted tests unchanged. Workspace changes are the acceptance record and firmware pointer only, checked against executed test output and approved story.

### Implementation evidence (2026-09-17)

Added only `tests/disk_catalog_serial_native_parity.h` and
`tests/test_disk_catalog_serial_native_parity.cpp` in firmware. The fixture
reuses existing channel doubles without editing accepted parity helpers or
`fake_fs.h`, dispatches real services with explicit 0xF2/0xFC endpoints, and
checks every decoded response against independently constructed device,
command, status and exact payload expectations. Each scenario runs through
both production framers with separate disposable host filesystems.

Coverage audit:

- Catalogue selection/replacement case: canonical relative Put/Get at index 100 and absolute URI entries at
  indices 101 and 200; independent slots 1 and 8; DD-to-DD and DD-to-HD-to-DD;
  full Info geometry/flags, distinct sector contents and all backing files.
- Lifecycle/reconstruction case: ClearChanged, dirty write, measured flush,
  full image seed-plus-sector oracle, eject/NotReady/remount, reconstructed
  AppStore/SlotCatalogService/DiskDevice, pending runtime restoration followed
  by framed Info activation, retained RO/RW modes, and absent ejected mapping.
- Error case: malformed catalogue version/flags, absent and deleted entries,
  persisted deletion, catalogue URI whose media is missing, bad-size ADF,
  invalid runtime slot and RO write rejection. Slot 8 and protected backing
  bytes are checked throughout. Failed replacement preserves old media and
  runtime mapping, but flushes dirty data and changes lastError (FileNotFound
  4 or BadImage 8); these established effects are not assumed transactional.

Verification executed after sourcing `scripts/env.sh`:

- `./scripts/update_cmake_sources.py`: ran; its unrelated generated build-profile
  rewrites were discarded. Test discovery requires no CMake change.
- `./build.sh -cp fujibus-pty-debug`: passed against unchanged production build
  files; 379 doctest cases / 12871 assertions and all three bundled CTest gates
  passed (including 23 Python tests).
- `./build/fujibus-pty-debug/tests/fujinet-nio-tests --test-suite=disk_catalog_serial_native_parity`:
  4 cases / 5027 assertions passed, executing both serial and native paths.
- `./build/fujibus-pty-debug/tests/fujinet-nio-tests --test-suite='Disk serial*'`:
  7 cases / 569 assertions passed.
- `./build/fujibus-pty-debug/tests/fujinet-nio-tests --test-case='*Disk*,*SlotCatalog*,*boot_mount*'`:
  44 cases / 953 assertions passed.
- `git diff --check` in firmware and workspace: passed. Production files,
  shared doubles and prior accepted tests are unchanged.

This is host protocol/backing-state and firmware reset-recovery evidence only;
it does not establish Amiga FMOUNTRESTORE, trackdisk or hardware acceptance.

### Review coverage fixes (2026-09-17)

Strengthened the same test-local suite after review, without production edits:

- Slot 8 starts with changed cleared in lifecycle/replacement scenarios, so
  operations on slot 1 cannot silently clear or set its changed flag. The HD
  replacement checks this immediately before reconstructing services.
- Persisted runtime mappings are checked at the DD-to-DD and DD-to-HD steps;
  reconstruction at the intermediate HD/RO step verifies lazy activation and
  media/mode. HD reads cover LBA 2000 and final LBA 3519.
- A fourth case makes both independent slots writable and dirty, verifies
  slot 8 remains dirty/changed across slot 1 flush/replacement/eject, and
  measures successful dirty replacement/eject outgoing-image flushes while
  comparing every backing image to independent expected bytes.
- Reconstructed RW media accepts another framed write, checked against the
  complete expected image. Catalogue overwrite changes both URI and RO policy
  across reconstruction. Deleting a mounted catalogue entry leaves its runtime
  media and persisted URI intact, including after firmware reconstruction.
- Every exchange polls again after its expected response and rejects extra
  decoded or queued outbound responses. The relative-URI evidence wording is
  corrected to identify index 100 specifically.

All four listed build/test gates and both diff checks were rerun after the
final review fixes; the counts above describe this final tree.

## Acceptance record — 2026-09-17

Three independent workflow review layers completed. Accepted coverage findings
were medium/low patch items; the fixes above and final source inspection close
them. Every matrix row has executed serial/native coverage. No unresolved
acceptance, prerequisite or environment blocker remains for Story 1.13.

Firmware revision: `298e201fbb1f6b744ec607f8a17ee8adbaa2b11a`. Production sources and prior accepted tests are unchanged.
This accepts Story 1.13 host parity only; Story 1.14 retains its separate guest
and resident-driver acceptance gate.

## Suggested Review Order

- Follow the real-service transport path and complete decoded-response checks.
  [disk_catalog_serial_native_parity.h:21](../../../../repos/fujinet-nio/tests/disk_catalog_serial_native_parity.h#L21)

- Check independent catalogue selection, replacement mappings, change flags and HD addressing.
  [test_disk_catalog_serial_native_parity.cpp:30](../../../../repos/fujinet-nio/tests/test_disk_catalog_serial_native_parity.cpp#L30)

- Check reconstructed services, pending activation and restored write protection.
  [test_disk_catalog_serial_native_parity.cpp:69](../../../../repos/fujinet-nio/tests/test_disk_catalog_serial_native_parity.cpp#L69)

- Check established error responses and failed-replacement effects.
  [test_disk_catalog_serial_native_parity.cpp:141](../../../../repos/fujinet-nio/tests/test_disk_catalog_serial_native_parity.cpp#L141)

- Check dirty-slot independence and catalogue edits preserving mounted media.
  [test_disk_catalog_serial_native_parity.cpp:193](../../../../repos/fujinet-nio/tests/test_disk_catalog_serial_native_parity.cpp#L193)

- Inspect disposable media seeds and independent full-image expectations.
  [disk_catalog_serial_native_parity.h:102](../../../../repos/fujinet-nio/tests/disk_catalog_serial_native_parity.h#L102)
