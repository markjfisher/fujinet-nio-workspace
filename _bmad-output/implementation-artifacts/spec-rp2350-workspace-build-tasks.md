---
title: 'Discoverable RP2350B workspace build tasks'
type: feature
created: 2026-09-17
status: done
route: one-shot
verification:
  - 'After source scripts/env.sh: PYTHONPATH=tools/build:tools python3 -m unittest discover -s tools/build/tests -v — 18 passed'
  - 'scripts/build.sh rp2350 — Debug/Release CTest 3/3 each, firmware ELF/UF2 build passed'
  - 'scripts/build.sh --explain rp2350-firmware — setup and artifact help displayed'
  - 'git diff --check — passed'
review: '10 findings patched: compiler/cache checks, exported override and prerequisite help, SDK pin help, stronger compiler fixtures, workflow success/failure and exact listing coverage. None deferred or rejected.'
---

# Discoverable RP2350B workspace build tasks

## Intent

**Problem:** The independent bridge presets are not discoverable through workspace build commands.

**Approach:** Add public `rp2350`, `rp2350-pio-tests` and `rp2350-firmware` tasks, delegating bootstrap and CMake/CTest to the bridge. Show prerequisites, overrides and artifact paths through `--explain`. Respect explicit/cached toolchains and the installed workspace-local compiler. Existing aggregate workflows remain unchanged.

## Suggested Review Order

- Follow the native tests and firmware orchestration, including compiler selection.
  [tasks.py:106](../../tools/build/nio_build/tasks.py#L106)

- Verify discoverability, environment handling and failure propagation.
  [test_rp2350_tasks.py:13](../../tools/build/tests/test_rp2350_tasks.py#L13)
