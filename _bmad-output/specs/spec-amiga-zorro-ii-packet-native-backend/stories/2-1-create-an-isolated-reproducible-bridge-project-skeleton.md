---
title: '2.1: Create an isolated, reproducible bridge project skeleton'
type: feature
created: 2026-09-17
status: done
review_loop_iteration: 0
baseline_commit: ddc269c3e79db86b85cebfb174de7807de7bbda1
firmware_baseline_commit: 2365fbce15391ae445f38962909ab8c8f172d84e
implementation_commit: 6b654677281fdb551cd77e0de75e3a5fa67a0987
context:
  - '{project-root}/docs/agent-test-policy.md'
  - '{project-root}/_bmad-output/implementation-artifacts/epic-2-context.md'
---

<frozen-after-approval reason="user authorized Story 2.1 implementation; dispatch checkpoints are false">

## Intent

**Problem:** NIO lacks an independently buildable RP2350B bridge project with executable PIO behavioral coverage.

**Approach:** Implement the approved Story 2.1 contract: separate native epio tests and Pico SDK firmware builds using one apio C program/configuration source, reproducible pinned dependency setup and a synthetic capture smoke test.

## Boundaries & Constraints

**Always:** Test PIO behavior first with epio, record red/green, and author instructions only with apio C macros. Use independent expected FIFO words, IRQ and cycle assertions, active even in Release. Pin compatible dependencies and verify existing checkout revisions. Support validated PICO_SDK_PATH. Keep host/native and firmware builds independent, caches ignored and existing POSIX/ESP collection unchanged. Source workspace scripts/env.sh before tests. Own only the bridge tree, its architecture documentation link and this story's implementation record; others may be working, so preserve their edits.

**Ask First:** Changes to production Zorro mapping/ABI or scope; physical validation belongs to later stories.

**Never:** First-party .pio files, pioasm generation, duplicated emulator programs, prebuilt reference archives, required core2350-test checkout, service-stack linkage, physical readiness claims or pushes.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|---|---|---|---|
| Idle | Strobe high | No FIFO data/IRQ after bounded cycles | Test fails on activity |
| Capture | Strobe low with 0xA | WAIT, IN, PUSH, IRQ observable on successive cycles | Wrong cycle/data fails |
| Held low | Drained FIFO and cleared IRQ, strobe stays low | No repeated capture | Duplicate fails |
| Rearm | Release then assert with 0x5 | One new full word/IRQ | Stale data fails |
| Bootstrap | Empty/repeated dependency cache | Pinned source checkout; repeated setup unchanged | Reject wrong revision or dirty source with repair guidance |
| Bad setup | Missing/wrong SDK or dependency | Actionable configure/bootstrap failure | Never reuse silently |
| Isolation | Host without SDK/ARM; firmware without epio archive | Each builds independently | Wrong target/package rejected |
| PIO policy | Forbidden source/build rule introduced | Guard fails | Nonzero test exit |

</frozen-after-approval>

## Code Map

- `repos/fujinet-nio/bridges/rp2350-zorro/` — new standalone owner; root firmware build untouched.
- `repos/core2350-test/capture_program.c`, `tests/test_capture.c`, `tests/CMakeLists.txt` — read-only structural reference. Do not copy the root .pio generation or absolute caches.
- `repos/core2350-test/third_party/epio/Makefile` — host library sources/options, including `-fshort-enums`; `src/epio_apio.c` owns APIO_EMU_IMPL. Host consumers need matching options.
- `repos/core2350-test/third_party/epio/apio/include/apio.h` — APIO_WRAP_TOP precedes its endpoint instruction; assembler init/emission share one function.
- `repos/fujinet-nio/scripts/update_cmake_sources.py:24` — scans only root src for .cpp; run and verify unchanged generated lists.
- `/home/markf/dev/pico/pico-sdk` — existing clean 2.3.1 SDK, waveshare_core2350b sets PICO_RP2350A=0; reference only, default bootstrap must be independent.
- `repos/fujinet-nio/docs/architecture.md` — add bridge README link.

## Tasks & Acceptance

**Execution:**
- [x] `bridges/rp2350-zorro/dependencies.json`, `scripts/bootstrap.py`, `.gitignore` — pin epio v0.2.1 (bf49b19a534befb69bd518ee463365a1a5d73a65), apio v0.3.0 (1023d866849694417ced497e17e98a2cd2bd026e), SDK 2.3.1 (079c6f39023649b154152db30f1d781e884879bc); bootstrap host/firmware separately, SDK required submodules, stale/dirty validation.
- [x] `CMakeLists.txt`, `CMakePresets.json`, `cmake/` — separate host and firmware presets/directories, shared apio source, native epio source build with consistent ABI flags; firmware SDK import before project/init, waveshare_core2350b/rp2350-arm-s, ELF/UF2. Pin any necessary fetched SDK host tool too.
- [x] `src/capture_program.{c,h}`, `src/main.c`, `tests/` — failing smoke tests first, implement capture/rearm behavior, host-only APIO_EMULATION; synthetic input-only GPIOs, no hardware interrupt handler needed. Keep stdio from conflicting with fixture GPIOs.
- [x] `scripts/check_pio_policy.py`, focused tooling tests — cover guard detection, bootstrap idempotence/stale/dirty errors and invalid setup.
- [x] `README.md`, firmware architecture link — exact setup/build/test commands, pins/compiler, dependency refresh, scope and emulator limitations.

**Acceptance Criteria:**
- Given native prerequisites only, when host bootstrap/build/CTest run, then all behavior/tooling tests pass from source without SDK/ARM/reference checkout.
- Given installed SDK/cross-compiler, when firmware builds, then RP2350B ELF/UF2 include shared apio code and no host emulator.
- Given both configurations, when isolation and policy checks run, then root POSIX/ESP source generation is unchanged and forbidden first-party PIO text workflows fail.

## Spec Change Log

## Design Notes

Use epio only in host tests, apio in both builds. SDK 2.3.1 board support is verified; physical operation is not. Parent installs official Arm GNU 14.2.rel1 under workspace `build/toolchains/arm-gnu-toolchain-14.2.rel1-x86_64-arm-none-eabi`; use its bin directory through PICO_TOOLCHAIN_PATH. Bootstrap source dependencies locally; avoid copying reference caches. Preserve normal input synchronization in firmware and document epio's missing input synchronizer delay.

## Verification

After `source "$NIO_WORKSPACE/scripts/env.sh"`, from bridge directory:

- `python3 scripts/bootstrap.py --mode host` twice; tooling tests exercise mismatches.
- `cmake --preset host && cmake --build --preset host && ctest --preset host` — red first, green after implementation; repeat with Release assertions active.
- `python3 scripts/bootstrap.py --mode firmware` then `cmake --preset firmware && cmake --build --preset firmware` — fresh build and nonempty ELF/UF2; set PICO_TOOLCHAIN_PATH as above.
- `python3 scripts/check_pio_policy.py` — no first-party PIO text workflow.
- From firmware repo: `./scripts/update_cmake_sources.py` and `git diff --exit-code -- CMakeLists_posix.cmake src/CMakeLists.txt` — unchanged collection.
- Workspace and firmware: `git diff --check` — clean. Record exact additional negative/isolation commands and outputs below.

### Implementation record (2026-09-17)

Implemented the standalone bridge tree, pinned source bootstrap and configure-time
validation, independent native/firmware presets, shared apio capture configuration,
input-only polling firmware, always-active behavioral checks, offline tooling tests,
PIO policy guard, README and firmware architecture link. No service-stack linkage,
production mapping, ABI or physical-readiness claim was added.

Dependency revisions: epio `bf49b19a534befb69bd518ee463365a1a5d73a65` (v0.2.1),
apio `1023d866849694417ced497e17e98a2cd2bd026e` (v0.3.0), SDK
`079c6f39023649b154152db30f1d781e884879bc` (2.3.1), required TinyUSB gitlink
`86ad6e56c1700e85f1c5678607a762cfe3aa2f47`, and picotool
`2041936441b48a3cc53ae3da9e805229fe8f4e18` (2.3.1). Picotool is an imported
CMake target built from the validated checkout via ExternalProject; this avoids
SDK implicit fetching or selection of an ambient host installation. Native GCC
16.2.1; Arm GNU 14.2.Rel1 GCC 14.2.1 20241119, archive SHA256
`62a63b981fe391a9cbad7ef51b17e49aeaa3e7b0d029b36ca1e9c3b2a9b78823`.

Executed commands below from the bridge directory after explicitly exporting
`NIO_WORKSPACE=/home/markf/dev/nio/fujinet-nio-workspace` and sourcing
`"$NIO_WORKSPACE/scripts/env.sh"` (the variable was initially absent).

- Red: `cmake --build --preset host && ctest --preset host -R '^capture$'`
  with PUSH intentionally absent failed at the independent cycle-3 FIFO-depth
  assertion, exit 8. An earlier empty implementation also failed epio setup.
- Green: after adding `APIO_PUSH_BLOCK`, `PICO_SDK_PATH=/nonexistent-sdk cmake
  --preset host && cmake --build --preset host && ctest --preset host`: 3/3 pass.
  The same configure/build/CTest sequence with `host-release`: 3/3 pass. Native
  PATH did not include the downloaded ARM compiler. FIFO full words, exact
  WAIT/IN/PUSH/IRQ cycles, changed data after IN, 32 held-low cycles and rearm
  with different data are checked using literal independent oracles.
- `python3 scripts/bootstrap.py --mode host` twice: exact pins validated,
  unchanged. `python3 scripts/bootstrap.py --mode firmware`: fresh independent
  SDK/picotool clones and required SDK submodule initialization succeeded.
- `ctest --preset host` and `ctest --preset host-release` after adding all tooling
  cases: 3/3 each. Offline Git fixtures cover first setup, repeat, stale SHA,
  tracked dirt, untracked dirt, missing dependency, non-repository path and
  missing submodule; configure subprocesses reject invalid mode and missing SDK.
  Guard fixtures reject .pio files, CMake generation rules and Makefile assembler
  commands with nonzero exits, while allowing third-party dependency contents.
- `PICO_SDK_PATH=/home/markf/dev/pico/pico-sdk python3 scripts/bootstrap.py --mode
  firmware --check`: the supported external SDK override validated successfully.
- `cmake --preset firmware -B build/wrong-board -DPICO_BOARD=pico2`: nonzero,
  actionable waveshare_core2350b / rp2350-arm-s requirement before SDK import.
- `python3 scripts/check_pio_policy.py`: passed. SDK/vendor text programs are
  excluded; first-party build rules and sources are checked.
- `cmake --preset firmware -B build/firmware-clean && cmake --build
  build/firmware-clean`: fresh build passed with local `PICO_TOOLCHAIN_PATH`.
  ELF 345380 bytes, UF2 12288 bytes; graph contains neither APIO_EMULATION,
  epio sources nor libepio.a. Board is waveshare_core2350b, platform rp2350-arm-s,
  package PICO_RP2350A=0. No host emulator is linked.

Source-collection verification found pre-existing drift: running
`./scripts/update_cmake_sources.py` then `git diff --exit-code --
CMakeLists_posix.cmake src/CMakeLists.txt` changes build-profile selection in
both lists, already at firmware baseline `2365fbce15391ae445f38962909ab8c8f172d84e`. No bridge or SDK sources
appear. Restored only these generated files (initial repository status was clean).
To distinguish bridge isolation from that unrelated generator issue, extracted
`git archive 2365fbce15391ae445f38962909ab8c8f172d84e` into two temporary trees,
added the first-party bridge tree to one, ran the generator in each and asserted
byte-for-byte equality of both output files. SHA256 results:

| File | Baseline and bridge-added generated output | Preserved checked-in file |
| --- | --- | --- |
| CMakeLists_posix.cmake | `0395d367732ac73f7012c2960690ab091d7643468e91a395fb8f912cd17f834d` | `e03f6ece337ed97a07d9e490908ac5adc97fb2845ec706f68115673ef6421157` |
| src/CMakeLists.txt | `b920c7f50a0ad09987c2752666231c8dd6d865eaa9fce9479d205d8da0e4bf1a` | `978fb270c496d0aaf0e982fa38e58e904c815f72ace49ad909a8a11812ddcd5a` |

The literal clean-regeneration gate has this baseline limitation; bridge isolation
passes the direct baseline/current comparison. Generator repair is outside Story
2.1 ownership. Physical timing/electrical/synchronizer and bridge-link validation
remain intentionally deferred to later stories.

- Final firmware isolation: moved the previous preset build to
  `build/firmware-first`, temporarily moved `.deps/epio` to
  `.deps/epio-isolation-away` (restored with shell EXIT trap), then ran
  `cmake --preset firmware && cmake --build --preset firmware`: fresh preset
  ELF/UF2 build passed with emulator dependency absent.
- Final preset artifacts: ELF 345372 bytes, UF2 12288 bytes (ELF debug paths
  account for the size difference from the alternate fresh build directory).
  Firmware graph exclusion checks pass. Final dependency check and both CTest
  presets pass; `git diff --check` passes in firmware and workspace, and
  `git diff --exit-code -- CMakeLists_posix.cmake src/CMakeLists.txt` confirms
  the checked-in lists remain unchanged after preservation.

### Review hardening verification (2026-09-17)

Added dependency-manifest configure tracking and an always-run prerequisite
validation target for native epio/capture and firmware capture/picotool consumers.
Both configure paths also run the PIO guard. Guard traversal now prunes only the
actual root `.deps`, `build`, and `.git`; nested first-party directories named
`build` remain checked. Root Python build scripts are checked; test Python fixtures
and the policy implementation itself are excluded from text-rule matching.
Both CTest presets set `execution.noTestsAction` to `error`.

Expanded tooling fixtures disable Git commit/tag signing locally. A real registered
local submodule is rejected uninitialized, accepted initialized at its gitlink,
rejected at another commit, and rejected with dirty content. Isolated CLI fixtures
prove host mode ignores an invalid SDK environment, firmware rejects a missing
SDK and stale SDK revision, and firmware accepts the valid pinned SDK override.
Wrong board and wrong platform configure subprocesses fail before SDK loading,
so these negatives remain independent of an installed SDK or ARM toolchain.
The behavioral test now checks synthetic GPIO1–5 input-only configuration and no
PIO block output control, plus the strobe pull-up and data pull-down/default-low
states before external drive. No PIO behavior or FIFO-capacity scope was added.

Incremental red/green verification used the already-configured `host` and
`firmware` preset directories, after sourcing the shared workspace environment.
For each preset, ran `cmake --build --preset <preset>` after each mutation below,
restoring the exact original bytes in a Python `finally` clause:

1. Append `/* validation fixture */` to `.deps/apio/include/apio.h`:
   build exit 1, dirty dependency rejected before bridge compilation/link.
2. Set `dependencies.json` apio revision to forty zeroes:
   build exit 1, automatic CMake reconfiguration rejects the stale pin.
3. Create `src/build/review-forbidden.pio` with `.program forbidden`:
   build exit 1, first-party policy rejects the nested build-directory source.
4. Restore all originals/remove the fixture and rerun the same build command:
   both native and firmware builds pass.

All six negative probes asserted that output contained neither `Building C object`
nor `Linking`; logs were saved under `/tmp/bridge-{host,firmware}-{dirty-header,
manifest-pin,forbidden-policy}.log`. Initial and restored firmware builds use the
same pinned toolchain and existing outputs. `cmake --preset host && cmake --build
--preset host && ctest --preset host` and the corresponding `host-release` commands
pass 3/3 tests each with the expanded checks. `cmake --preset firmware && cmake
--build --preset firmware` passes. Firmware and workspace `git diff --check` pass.
README now documents explicit cache reset for a cached SDK override and uses the
full firmware baseline revision.

Post-probe rebuild/CTest passes again for host and host-release (3/3 each).
`ctest --preset host -R '^no_such_test$'` and the corresponding host-release
command both exit 8, verifying the no-tests error contract. Final standalone
policy check, firmware dependency validation, whitespace checks and preserved
root source-list diff checks all pass.


### Technical acceptance and review — 2026-09-17

Story 2.1 is accepted for build/test infrastructure only. All matrix rows have
passing executable coverage: capture test covers idle/capture/hold/rearm and
input configuration, four tooling tests cover bootstrap, overrides, submodules,
negative configuration and policy rules, and recorded independent firmware/host
builds cover isolation. Debug and Release each pass all three CTest registrations.
Incremental-build mutations verify enforcement after initial configuration.

Three independent review layers ran. Medium patch findings addressed manifest
revalidation, incremental dirty-source rejection, firmware policy enforcement,
policy traversal/entry-point gaps, fixture Git signing independence, SDK cache
instructions, real submodule coverage, GPIO/pull coverage and CLI/platform
negatives. The empty-test gate was also corrected. No intent change or production
PIO behavior was required. A follow-up reviewer ran all four tooling tests and
confirmed closure. FIFO-full protocol behavior remains future feasibility work;
the current smoke contract tests one capture at a time. The pre-existing generator
drift is recorded in the workspace deferred-work ledger, with isolation proven by
identical baseline/current output rather than claiming clean regeneration.

Parent artifact audit used Python struct checks for ELF32 little-endian ARM
(e_machine=40) and every UF2 block's opening/closing magic, then the installed
`arm-none-eabi-nm build/firmware/bridge_capture.elf` to confirm
`capture_program_init` is linked and no `epio_` symbols exist: PASS.
No physical operation, bus timing or Epic 2 feasibility gate is accepted here.

## Suggested Review Order

**Build boundary**

- Separate native tests from SDK firmware and enforce the RP2350B target.
  [CMakeLists.txt:1](../../../../repos/fujinet-nio/bridges/rp2350-zorro/CMakeLists.txt#L1)

**Reproducible inputs**

- Reject stale or dirty dependencies without discarding local work.
  [bootstrap.py:16](../../../../repos/fujinet-nio/bridges/rp2350-zorro/scripts/bootstrap.py#L16)

- Keep validation active on incremental builds.
  [validation.cmake:1](../../../../repos/fujinet-nio/bridges/rp2350-zorro/cmake/validation.cmake#L1)

**Shared PIO behavior**

- Use one apio program for hardware and emulation.
  [capture_program.c:4](../../../../repos/fujinet-nio/bridges/rp2350-zorro/src/capture_program.c#L4)

- Check independent data, cycles, input configuration and rearming.
  [test_capture.c:1](../../../../repos/fujinet-nio/bridges/rp2350-zorro/tests/test_capture.c#L1)

**Setup and regression checks**

- Follow reproducible setup commands and evidence limits.
  [README.md:13](../../../../repos/fujinet-nio/bridges/rp2350-zorro/README.md#L13)

- Exercise setup failures and forbidden PIO workflows offline.
  [test_tooling.py:1](../../../../repos/fujinet-nio/bridges/rp2350-zorro/tests/test_tooling.py#L1)
