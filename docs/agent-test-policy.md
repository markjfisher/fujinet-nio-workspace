# FujiNet NIO — agent and BMAD verification policy

This is the **product-wide** rule for agents and BMAD Build: every change must have
an appropriate test **written or selected** and **run to pass**, at the cheapest
level that can fail for that change. It applies to the whole FujiNet NIO workspace
and every repo under `repos/`, not only the current Amiga broker stages.

Source the workspace environment before builds or tests:

```sh
source "$NIO_WORKSPACE/scripts/env.sh"
```

Per-repo `AGENTS.md` / README remains the command authority if this table drifts.
Amiga guest procedure: `docs/amiga/amiberry-testing.md`.

## Rules

1. **Identify every owner you touched.** A workspace spec that edits lib + driver +
   firmware needs a check in **each** owner, not one Amiga pytest “for the whole stack.”
2. **Cheapest sufficient gate.** Do not run the most expensive suite by default
   (full Amiberry, all ESP32 boards, every fn-rom machine/interface, `scripts/build.sh all`).
3. **Write a test if nothing covers the behavior.** Smallest native/unit/wire/pytest
   case. Compile-only is not behavioral coverage (a header-only Stage 1 compile check
   is allowed **for that kind of change only**).
4. **Record the exact command** in the BMAD spec Verification section, then execute it.
   Incomplete if the command was not run, or if an I/O-matrix row has no covering test
   that ran and passed.
5. **Environment blockers.** If a required toolchain, licensed Amiga media, or hardware
   is missing, stop and report it. Do not skip coverage silently or substitute a huge
   unrelated suite.

## Per-owner usual gates

Match the **channel and platform** of the change. Examples: PTY vs TCP vs RS232 vs
ESP32 in `fujinet-nio`; Amiga vs MS-DOS in the driver; BBC vs Atari in apps.

| Owner | Usual (do this) | Deeper (when the change needs it) | Do not default to |
| --- | --- | --- | --- |
| `repos/fujinet-nio` | POSIX: `./build.sh -cp fujibus-pty-debug` then `ctest --test-dir build/fujibus-pty-debug`. If the change is the TCP channel, use `fujibus-tcp-debug` (and its `ctest`) instead of PTY. After adding/removing sources: `./scripts/update_cmake_sources.py`. | ESP32 platform/board code: `./build.sh -b` for the configured board. Python host tools: `./scripts/run-python-tests`. | Every board type; hardware YAML E2E; all POSIX presets |
| `repos/fujinet-nio-lib` | Complete `make check` (all configured targets + host wire tests). Shared C: at least one cc65 target and one non-cc65 target are already inside `check` when those toolchains exist. | Extra platform `make TARGET=…` only if `check` skipped that toolchain and you must record why. | Skipping `make check` after lib edits |
| `repos/fujinet-nio-driver` | Native tests/build for the **OS you changed** (Amiga device vs MS-DOS `FUJINET.SYS`). Follow that tree’s README / test entry point. | Guest Amiberry **one node** if DiskDevice or serial-visible behavior changed. | Full Amiberry suite |
| `repos/nio-core-apps` | Build/test the **platform whose sources changed** (`make TARGET=<platform>` or the documented equivalent). | Boot-disk/manifest path only if those files changed. | Every platform in one loop unless the change is shared C used everywhere |
| `repos/nio-config` | Same: the config target/platform you changed. | — | `all-targets` when Atari (or another target) is known excluded |
| `repos/nio-apps` | The example/diagnostic you changed, on that platform. | — | All examples on all machines |
| `repos/fn-rom` | `./run_unit_tests.sh` or the focused YAML under `unit-tests/tests/` that covers the command/FS path. | `./run_tests.sh` if unit tests are not enough. Beebium only when the ticket is E2E. | Every `BUILD_MACHINE` × `BUILD_INTERFACE` |
| Workspace `integration-tests/amiberry` | One pytest node (see Amiga section). | `-k` subset. | Full `scripts/amiga-tests` (~6 min) |
| Workspace `tools/build`, `tools/amiga_emulator` | That package’s pytest (e.g. `tools/amiga_emulator/tests`). | — | Amiberry guest suite for a Python-only harness change, unless the harness itself is under test |

Workspace platform workflows (`scripts/build.sh linux`, `amiga`, `bbc`, …) are for
human/CI composition, not the default inner agent loop.

## Amiga guest (when guest behavior changed)

Full suite — **not** the default:

```sh
scripts/amiga-tests --amiga-env wb32 --amiga-machine a1200-030
```

Normal agent gate — exact node (example):

```sh
source scripts/env.sh && \
  uv run pytest --run-amiga --amiga-env wb32 --amiga-machine a1200-030 \
  integration-tests/amiberry/test_diskdevice_adf.py::test_hd_adf_mount_geometry_dir_and_type
```

Default guest unless the ticket says otherwise: `wb32` + `a1200-030`.

## BMAD Build

The spec Verification list is the contract. Each touched owner from the table
must appear with a command that was run. Implementation is incomplete until
those pass or an environment blocker is reported.
