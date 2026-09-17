---
title: '1-12 Add safe ordinary disk operations to the exchange tool'
type: feature
created: '2026-09-17'
status: done
baseline_commit: 1d3ecffb50bdbd1b5957bdbd9ce2b54708b73606
owner_baseline_commit: c7f1fbd382724b34b5f83ec8f99baf8df4ea1fcb
firmware_baseline_commit: f9a430cebee652cf7308100b20a96f0ce2e0b016
review_loop_iteration: 0
spec_checkpoint: false
done_checkpoint: false
context:
  - '{project-root}/docs/agent-test-policy.md'
  - '{project-root}/docs/amiga/cli-stack-and-iorequest.md'
  - '{project-root}/_bmad-output/implementation-artifacts/epic-1-context.md'
---

<frozen-after-approval reason="approved Story 1.12; routine checkpoints disabled by execution-gates.md">

## Intent

**Problem:** Disk diagnostics require serial provocation and can write existing mounted media. Native parity needs ordinary resident disk operations on deliberately supplied disposable fixtures.

**Approach:** Separate ordinary warm disk read/write from explicit legacy provocation. Require disposable fixture URI/declaration and write intent; use resident mount and trackdisk operations, flush and full read-back verification.

## Boundaries & Constraints

**Always:** Preserve slot 1–8 to resident unit 0–7 mapping, serial provocation and 1.11 behavior. Ordinary operations use no baud/pacing/serial controls. Refuse locally or remotely occupied target slots before mount. Use isolated diagnostic sessions; never claim atomic exclusion of competing clients. Retain Exec, FN/transport and service error distinctions. Leave the fixture mounted and report this explicitly, including after post-mount failure: automatic TD_EJECT would alter saved mappings. No write restoration can substitute for explicit disposable-media authorization.

**Ask First:** Public ABI, retry semantics, production service/driver redesign, hardware changes.

**Never:** Write without explicit intent; replace existing media; raw-unmount behind resident state; modify persisted mappings; fabricate replies; test harness under production src; expand media formats.

## I/O & Edge-Case Matrix

| Input/state | Behavior |
|---|---|
| Authorized ordinary read/write, unused slot | Resident I/O; write flushes then compares every byte; nondefault slot works |
| Missing fixture/declaration/write intent, invalid slot/LBA or conflicting options | Usage failure before I/O/write |
| Local or remote occupied slot, INFO failure | Refuse mount/write; original media unchanged |
| Missing fixture or geometry-out-of-range LBA | Clear failure, zero writes |
| Transfer failure or read-back mismatch | Nonzero result; preserve separate errors, no tool replay |
| Legacy serial provocation; native clock/list | Existing supported behavior preserved |

</frozen-after-approval>

## Code Map

Paths workspace-relative. Own files below, accommodate other edits without reverting them. Keep public ABI, broker, library and resident implementation read-only.

- `repos/fujinet-nio-driver/amiga/tools/fujinet_nio_exchange_opts.{h,c}`: native validator:49, disk parse:164, plan:194 currently enforce provocation. Add `--fixture-uri URI --disposable-fixture`, plus `--write-intent` for ordinary writes. Require warm lifecycle, explicit slot/LBA; reject serial options and combinations with provocation. Bound LBA before 512 multiplication. Keep old valid serial numeric syntax.
- `repos/fujinet-nio-driver/amiga/tools/fujinet-nio-exchange.c`: run_disk_provocation:731 stays separate; dispatch:922 chooses ordinary versus provocation. Ordinary path opens installed broker/device, reads remote INFO using existing fn_disk context codec/callback and local TD_CHANGESTATE, fails closed, mounts URI with existing MOUNT/MOUNT_WRITABLE, checks TD_GETGEOMETRY and bounds, captures change count, uses ETD_READ/WRITE then CMD_UPDATE/read-back. Use trial-distinct deterministic 512-byte patterns; BSS/allocated buffers. Snapshot io_Error/io_Actual before trace queries, clear trace per operation. Mount/geometry lack exchange trace: do not invent details. No WaitIO on unsubmitted requests.
- Read-only `amiga/disk.device/fujinet_disk_device.c`: URI mount:478, I/O:561, local-only state:658, persistent mapping side effects on eject:674, geometry:699, trace:785. Existing `fn_disk_info_context` lives in library `src/common/fn_disk.c:255`; no library changes needed.
- Driver `amiga/tests/test_fujinet_nio_exchange_opts.c`, `amiga/tests/Makefile`, `amiga/Makefile`, `amiga/README.md`: parser/plan and ordinary workflow tests, linking, usage. A small production ordinary-workflow helper under `amiga/tools/` may isolate actual decision/I/O sequence for host tests; test doubles remain under tests.
- `repos/fujinet-nio/tests/native_test_records.h:165` AND `tests/native_test_runner.cpp:169`: register real DiskDevice in both helper and actual process. `tests/test_native_test_endpoint.cpp`: subprocess disk request coverage with independent backing bytes. No catalogue/appstore extension needed.
- Workspace `integration-tests/amiberry/conftest.py`: native broker branch currently forbids driver=true. Add narrow native disk fixture opt-in installing disk.device via --devs-file, without static DOS MountLists. Fresh per-case host-fs under native-test-records; reuse create_standard_adf:503, retain original snapshots outside host-fs.
- Workspace `integration-tests/amiberry/tests.toml`, new `startup/nio-native-disk.sequence`, `test_nio_native_test.py`: real guest tool on separate read/write fixtures. Invalid CLI before resident loading, occupied-slot protection, missing fixture and bounds, slot8 write trials. Independently check complete backing image against seeded bytes plus expected target sector; unchanged read/control image and surrounding bytes. Count actual host write requests; no hidden replay. Preserve 1.11 case.

## Tasks & Acceptance

- [x] Implement validated ordinary operation planning and resident workflow.
- [x] Test matrix including zero-write guards and mismatch/failure handling using actual workflow logic.
- [x] Register/test real host DiskDevice and add disposable native guest acceptance.
- [x] Document flags, isolated-session constraint, retained mounted fixture and separate provocation; run gates and review.

Given explicit disposable fixtures, when ordinary disk diagnostics run, then resident/native service I/O succeeds without serial setup and writes match independent expected bytes. Given invalid authorization or unsafe state, when diagnostics run, then no write occurs. Existing provocation remains explicitly selected and compatible.

## Spec Change Log

## Verification

Source `scripts/env.sh` before each build/test. Required commands:

- `make -C repos/fujinet-nio-driver/amiga/tests test` (includes retry containment and new workflow tests).
- `make -C repos/fujinet-nio-driver/amiga ../build/amiga/fujinet-nio-exchange ../build/amiga/fujinet-disk.device`.
- In `repos/fujinet-nio`: `./build.sh -cp fujibus-pty-debug`, then `ctest --test-dir build/fujibus-pty-debug --output-on-failure`.
- `scripts/amiga-tests --amiga-env wb32 --amiga-machine a1200-030 test_nio_native_test.py::test_native_exchange_tool_disk test_nio_native_test.py::test_native_exchange_tool_read_only test_nio_paula_serial.py`.

Record exact results and evidence paths. Each matrix row needs executed coverage; guest proves actual tool/resident path, host tests exercise failure decisions. No full Amiberry suite or physical hardware claim.


### Implementation verification — 2026-09-17

All commands below sourced `scripts/env.sh` first. Parent workflow review and
commits remain pending; no library/public ABI/resident/broker source changed.

| Gate | Result | Evidence |
| --- | --- | --- |
| `make -C repos/fujinet-nio-driver/amiga/tests test` | PASS, including production ordinary-workflow tests and existing retry containment | `/tmp/story112-driver-tests.log` |
| `make -C repos/fujinet-nio-driver/amiga ../build/amiga/fujinet-nio-exchange ../build/amiga/fujinet-disk.device` | PASS | `/tmp/story112-driver-build.log` |
| `cd repos/fujinet-nio && ./build.sh -cp fujibus-pty-debug` | PASS | `/tmp/story112-firmware-build.log` |
| `cd repos/fujinet-nio && ctest --test-dir build/fujibus-pty-debug --output-on-failure` | PASS, 3/3 | `/tmp/story112-firmware-ctest.log` |
| `scripts/amiga-tests --amiga-env wb32 --amiga-machine a1200-030 test_nio_native_test.py::test_native_exchange_tool_disk test_nio_native_test.py::test_native_exchange_tool_read_only test_nio_paula_serial.py` | PASS, 3/3, 16.86 s | `/tmp/story112-guest-tests.log`; `test-evidence/amiberry-20260917-115310/` |
| `scripts/amiga-tests --amiga-env wb32 --amiga-machine a1200-030 test_nio_native_test.py::test_native_exchange_tool_disk` | PASS, 1/1, 8.88 s, after adding exact write/flush/read request ordering assertion | `/tmp/story112-guest-disk-final.log`; `test-evidence/amiberry-20260917-115413/nio-native-disk/` |

Executed matrix evidence:

- Authorized read uses slot 1, two trials; write uses slot 8, three trials. Entire
  independent original read/control ADF images remain identical. Entire write ADF
  equals its independent seeded original with only LBA 17 changed to trial 3's
  expected 512 bytes. Real host log has exactly three WRITE requests and final
  operation sequence `[WRITE, FLUSH, READ]` repeated three times.
- Eight invalid CLI cases execute before either resident loads and return usage
  status 10: missing URI, declaration or intent, bad slot, missing/overflow LBA,
  serial options and provocation conflict. Native parser/plan tests additionally
  cover read/write-intent conflict, cold, omitted slot, empty URI and list flags.
- Guest local occupancy refuses before remote INFO; resident unload/reload leaves
  the host mounted, proving the remote-only occupancy refusal independently.
  Neither refusal performs a mount/write. Actual workflow tests inject local and
  remote INFO failures and assert zero mount/write effects.
- Guest nonexistent fixture fails at mount; out-of-geometry LBA fails after mount
  with zero writes and explicit retained-mount reporting. Workflow tests cover
  every operation failure, short read/write, final-byte mismatch and immediate
  stop without replay. Post-mount failures retain fixture status.
- Existing parser provocation tests, native clock/list guest and Paula serial
  guest pass. No hardware claim. The runtime service mount inventory is expected;
  no catalogue/persisted drive mapping operations or raw unmount requests occur.

The first guest iteration failed only an overstrict fixture-directory assertion
that omitted the real service's `fujinet-runtime-mounts.tsv`. This was corrected;
all operation results and image comparisons had already passed. Later complete
focused gates above passed. No remaining environment blockers.

### Review patch verification — 2026-09-17

Addressed the parent's focused review bundle without changing frozen intent:

1. Numeric parsing rejects a minus after leading whitespace before calling
   `strtoul`, preventing unsigned wraparound on both host and Amiga. Explicit plus
   and whitespace-positive legacy serial syntax remain accepted. Host tests derive
   negative values from `ULONG_MAX`; guest executes `--slot -4294967295` and
   `--lba -4294967279` before either resident loads, expecting usage status 10.
2. Workflow records a mount attempt separately from confirmed success. Failed mount
   reports `FIXTURE STATE UNKNOWN` / may remain mounted, never retries or unmounts.
   A test simulates a peer accepting the mount before returning a failed completion
   and verifies exactly one mount, zero writes and no follow-up operation.
3. Each completed full-sector read emits its one-based trial and FNV-1a 32-bit
   checksum. Guest independently computes the expected checksum from the original
   seeded sector and matches both delivered read trials. Write/flush/read logs also
   identify their trial.
4. Moved the existing ordinary resident adapter into the internal tool module
   `fujinet_nio_exchange_disk_adapter.{c,h}`. Its host harness links that actual
   production adapter, workflow and library INFO codec, replacing only Exec `DoIO`
   under `amiga/tests/`. Executed cases preserve distinct nonzero Exec/FN/result/
   cause/native/status fields, service rejection, malformed INFO slot, malformed
   geometry, failed trace-clear, failed trace-query with both successful and failed
   data commands, and zero subsequent writes. Trace errors print their own results
   separately from saved data-operation results.
5. Added second/third-trial failure containment and completed-count assertions,
   non-512-byte geometry rejection, 511/512-byte URI parser boundaries, and full
   literal 11-byte read metadata assertions in both helper and subprocess endpoint
   tests.

All commands sourced `scripts/env.sh` first:

| Gate | Result | Evidence |
| --- | --- | --- |
| `make -C repos/fujinet-nio-driver/amiga/tests test` | PASS, including actual adapter harness and all existing tests | `test-evidence/amiberry-20260917-115951/verification/story112-review-driver-tests.log` |
| `make -C repos/fujinet-nio-driver/amiga ../build/amiga/fujinet-nio-exchange ../build/amiga/fujinet-disk.device` | PASS | `test-evidence/amiberry-20260917-115951/verification/story112-review-driver-build.log` |
| `cd repos/fujinet-nio && ./build.sh -cp fujibus-pty-debug` | PASS | `test-evidence/amiberry-20260917-115951/verification/story112-review-firmware-build.log` |
| `cd repos/fujinet-nio && ctest --test-dir build/fujibus-pty-debug --output-on-failure` | PASS, 3/3 | `test-evidence/amiberry-20260917-115951/verification/story112-review-firmware-ctest.log` |
| `scripts/amiga-tests --amiga-env wb32 --amiga-machine a1200-030 test_nio_native_test.py::test_native_exchange_tool_disk test_nio_native_test.py::test_native_exchange_tool_read_only test_nio_paula_serial.py` | PASS, 3/3, 19.50 s | `test-evidence/amiberry-20260917-115951/verification/story112-review-guest-tests.log`; `test-evidence/amiberry-20260917-115951/` |

Independent rechecks confirmed the unsigned-wrap, uncertain-mount and actual-adapter error coverage findings resolved. No remaining review blocker. Ordinary serial disk and HD guest variants were not run; acceptance exercises native DD media, with existing serial compatibility and resident geometry contracts preserved.

## Acceptance revisions

- Driver: `1c37a6abe08556b57888bef8dcde4efd8ba6d564`.
- Firmware endpoint tests: `5ed96128972b9aafa44381319cd6f2c3b4028224`.

## Suggested Review Order

- Start with authorization, occupancy guards and fail-stop operation ordering.
  [fujinet_nio_exchange_disk.c:12](../../../../repos/fujinet-nio-driver/amiga/tools/fujinet_nio_exchange_disk.c#L12)

- Check explicit fixture flags and bounded numeric arguments.
  [fujinet_nio_exchange_opts.c:57](../../../../repos/fujinet-nio-driver/amiga/tools/fujinet_nio_exchange_opts.c#L57)

- Follow resident operations, preserved errors and read checksums.
  [fujinet_nio_exchange_disk_adapter.c:34](../../../../repos/fujinet-nio-driver/amiga/tools/fujinet_nio_exchange_disk_adapter.c#L34)

- Inspect tool setup and retained or uncertain mount reporting.
  [fujinet-nio-exchange.c:742](../../../../repos/fujinet-nio-driver/amiga/tools/fujinet-nio-exchange.c#L742)

- Read usage constraints and separate legacy provocation.
  [README.md:170](../../../../repos/fujinet-nio-driver/amiga/README.md#L170)

- Check failure decisions and no-replay assertions.
  [test_fujinet_nio_exchange_disk.c:44](../../../../repos/fujinet-nio-driver/amiga/tests/test_fujinet_nio_exchange_disk.c#L44)

- Check actual adapter error preservation across Exec and trace completions.
  [test_fujinet_nio_exchange_disk_adapter.c:120](../../../../repos/fujinet-nio-driver/amiga/tests/test_fujinet_nio_exchange_disk_adapter.c#L120)

- Inspect isolated guest fixtures and full backing-byte acceptance.
  [test_nio_native_test.py:96](../../../../integration-tests/amiberry/test_nio_native_test.py#L96)

- Inspect real endpoint service registration.
  [native_test_runner.cpp:171](../../../../repos/fujinet-nio/tests/native_test_runner.cpp#L171)

