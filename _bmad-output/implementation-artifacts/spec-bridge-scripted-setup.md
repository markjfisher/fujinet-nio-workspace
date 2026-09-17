---
title: Script-driven bridge dependency setup and repair
type: bugfix
created: 2026-09-17
status: done
review_loop_iteration: 1
baseline_commit: dd43b0b310a6a761e816af527afa2688268e85b8
context: [docs/agent-test-policy.md]
---

## Intent

User cannot run generator-check after accidentally formatting vendored dependencies.
Confirmed dirty apio, Pico SDK (including tinyusb), and picotool; epio is clean.
README duplicated bootstrap and exposed curl/extraction and CMake recipes. Replace
recipes with scripts: setup dependencies/toolchain, safely repair local caches,
and run native tests/builds. Preserve pinned sources and strict validation.
Implementation is authorized; no routine approval checkpoint. This is a tooling
fix, not completion of Story 2.2 or permission to drive hardware.

## Boundaries

Never silently reset dirty trees, touch external PICO_SDK_PATH, install system
packages, sudo, change firmware behavior, drive hardware, or update dependency
versions. Explicit --repair backs up invalid managed .deps trees before replacing
from verified pins; backups survive failure. Reuse local Git objects where
possible to avoid downloading a large SDK merely to undo formatting. Handle
registered tinyusb submodule as part of restoration. Reject symlink/external
repair targets. Missing caches may be downloaded by setup. Toolchain installation
is explicit, pinned/checksummed, Linux x86_64 only; honor user override and usable
existing compiler, never silently replace invalid explicit toolchain paths.
All commands work from arbitrary cwd, source workspace env when present, preserve
standalone bridge operation. Help must not download or mutate anything.

## Code Map and ownership

Worker owns code and code tests under bridge only: scripts/bootstrap.py,
scripts/create-deps.sh, scripts/setup.sh and supporting Python/module,
scripts/test.sh, optional scripts/build.sh, scripts/install-toolchain.*,
tests/test_tooling.py or focused setup tests registered in cmake/host.cmake,
tests/feasibility/experiment.py and its tests as needed. You are not alone: root
owns all README/docs, this spec and actual local dependency repair after tests;
do not revert others' edits or commit. No other agents edit implementation.

Existing bootstrap.setup(path,pin,check_only) validates Git revision/status and
SDK submodules; CMake and workspace tasks rely on existing host/firmware/stimulus
CLI arguments and --check. Preserve those. dependencies.json is source of pins.
CMakePresets host/host-release are Debug/Release; firmware RP2350B and
stimulus-rp2040 RAM RP2040. experiment.build runs host+stimulus bootstrap and
CMake loops then USB picotool and build provenance. Reuse common scripted setup
rather than independent divergent dependency logic; preserve build provenance,
logging and serial/acquisition workflows. Shell starter currently finds workspace
and sources env; model new entry points on that behavior.

## Interface and acceptance

- [x] scripts/create-deps.sh [--mode host|firmware|stimulus|all] [--check|--repair]:
  default all, only pinned source dependencies, no ARM toolchain required. Dirty
  normal call fails with exact repair command. --check is read-only. --repair
  preserves invalid managed trees in ignored .deps-backups and restores verified
  sources, keeps already-clean dependencies untouched. Report backup locations.
  External SDK override remains validation-only even in repair mode.
- [x] scripts/setup.sh [--host-only] [--repair] [--install-toolchain]: default all
  source dependencies plus validate compiler/tool requirements; host-only requires
  no SDK/ARM. install-toolchain explicitly downloads verified archive if no usable
  compiler. Put URL/hash/extraction logic in script, not README. Reuse current
  pinned Linux x86_64 14.2.Rel1 archive/hash from bridge README. Prefer existing
  workspace build/toolchains cache, standalone bridge build/toolchains fallback.
- [x] scripts/test.sh: single native Debug+Release configure/build/CTest command;
  fetch needed host deps idempotently; no hardware/system changes. Provide simple
  firmware build entry point if needed so README needs no CMake recipe.
- [x] Generator build calls shared source setup once; actionable repair diagnostics
  survive command-log wrapping. Match actual selected SDK in CMake cache by passing
  resolved path during configuration, avoid stale SDK selection after env change.
- [x] Offline tests cover repair idempotence/preserved dirty+untracked files,
  incorrect pins, restore failures, submodule repair, external/symlink refusal,
  --check vs --repair exclusion, toolchain checksum failure and cwd independence.
- [x] Root: concise bridge README command table, no copied build/download recipes;
  generator docs point to setup/repair commands. Ignore dependency backups and
  exclude vendor/build trees from recursive clang-format using supported mechanism.

Given dirty managed deps, repair preserves originals and normal validation passes.
Given failed restoration, preserved original remains available and no invalid tree
is accepted. Given fresh/clean setup, reruns converge without duplicate downloads.
Given commands from outside bridge, paths resolve correctly. Given external SDK,
no repair mutation occurs. Given generator build, same host tests, RAM image and
USB loader remain available, with no live board operation in this task.

## Verification

After source scripts/env.sh: focused offline Python tooling/setup tests (registered
CTest); scripts/test.sh (Debug/Release); scripts/setup.sh --repair on actual dirty
caches; generator-check/run.sh build; scripts/build.sh firmware if new wrapper.
Check shell syntax/help from /tmp, inspect backup dirty data, all selected pins
clean, local README links, git diff --check for both owners. Workspace docs only:
no unrelated platform tests. Retain exact outcomes below; commit without pushing.


## Review and observed recovery

Actual failure reproduced: apio dirty (6 files), Pico SDK dirty (732 paths,
including TinyUSB), picotool dirty (31), epio clean. Repair preserved all three
originals under `.deps-backups/`; normal pinned checks pass. The first SDK repair
exposed a registered submodule name/path mismatch (`tinyusb` vs `lib/tinyusb`):
fixed from verified `.gitmodules` lookup and added an offline fixture reproducing
that layout. An explicitly escalated network retry restored the SDK in this run;
subsequent `setup.sh --repair` is idempotent and downloads nothing.

Review patches cover relative SDK resolution, compiler command arguments and
minimum CMake version, required Arm companion tools, stale compiler caches,
read-only help, optional installer capability tests, borrowed Git object stores,
and public setup/first-install orchestration coverage. Backup resume options and
arbitrary future nested-submodule topologies are not introduced; current pins
and their required submodule are the contract. No hardware behavior changed.


## Final verification

After `source scripts/env.sh`, all passed:

- `repos/fujinet-nio/bridges/rp2350-zorro/scripts/setup.sh --repair`: recovered
  three modified trees, retaining backups; repeated after recovery without changes.
- `repos/fujinet-nio/bridges/rp2350-zorro/scripts/create-deps.sh --check`:
  all four pinned dependencies and TinyUSB clean.
- `repos/fujinet-nio/bridges/rp2350-zorro/scripts/test.sh`: Debug and Release
  7/7 each, including 15 setup cases, 4 tooling cases and 31 runner cases in both
  normal and optimized Python. Extraction tests ran here (no capability skips).
- `repos/fujinet-nio/bridges/rp2350-zorro/scripts/build.sh firmware`: RP2350B
  ELF/UF2 built successfully through public wrapper.
- `repos/fujinet-nio/bridges/rp2350-zorro/tests/feasibility/generator-check/run.sh build`:
  host gates, RAM firmware, USB picotool and build identity record passed.
- Public shell `--help` from `/tmp`, shell syntax, README local-link resolution,
  clang-format dry-run exclusion against actual apio/SDK/picotool files passed.
  Fixture tests verify help/dry-run do not create bytecode or other files.
- Source collector exercised with output paths redirected to a temporary directory:
  bridge scripts remain excluded; pre-existing product generated-list drift untouched.
- `git diff --check` and `git -C repos/fujinet-nio diff --check`: passed.

Final review confirmed public repair/install orchestration coverage and all four
edge-case findings resolved. Existing compiler was reused; downloading the actual
Arm archive was not needed. Installer download/checksum/extraction paths use
controlled archive fixtures. No USB load, generator burst or physical capture
was performed. No story feasibility result is added by this tooling change.

Retained original dependency trees (ignored, not committed) under the bridge:

- `.deps-backups/apio-74341a05d5fc4c01aaff1b1ddf8d8638`: 6 changed paths.
- `.deps-backups/pico-sdk-05af4292fed14556988bc49722c2ec35`: 732 changed paths.
- `.deps-backups/picotool-2223f2e0dac74cbcb5dcf69f84e89afc`: 31 changed paths.

## Suggested Review Order

- Start with the public setup, recovery and test commands.
  [README.md:1](../../repos/fujinet-nio/bridges/rp2350-zorro/README.md#L1)

- Inspect backup preservation, pinned restoration and submodule handling.
  [bootstrap.py:1](../../repos/fujinet-nio/bridges/rp2350-zorro/scripts/bootstrap.py#L1)

- Inspect shared prerequisites, compiler selection and scripted builds.
  [bridge_setup.py:1](../../repos/fujinet-nio/bridges/rp2350-zorro/scripts/bridge_setup.py#L1)

- Verify recovery failures, independent objects and public command behavior.
  [test_setup.py:1](../../repos/fujinet-nio/bridges/rp2350-zorro/tests/test_setup.py#L1)
