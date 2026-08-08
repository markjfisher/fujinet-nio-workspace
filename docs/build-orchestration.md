# Build Orchestration Direction

The workspace build interface grew from a set of convenient shell helpers
into a large public API. The old `scripts/build.sh` was over 1200 lines and exposed
many low-level implementation steps as top-level targets. That makes simple
questions hard to answer:

- Which target builds everything needed for BBC work?
- Is `config-bbc` the app, a disk, or the firmware boot disk?
- Should a disk recipe live in the workspace, `nio-core-apps`, `nio-config`, or
  `fn-rom`?
- Which compatibility aliases are still active?

The direction from here should be fewer workflow targets at the workspace
level, with detailed build knowledge pushed back into the repos that own the
artifacts.

## Public Surface

The Python build front end now prefers platform workflows over exact artifact
names:

```sh
./scripts/build.sh bbc
./scripts/build.sh master
./scripts/build.sh msdos
./scripts/build.sh atari
./scripts/build.sh linux
./scripts/build.sh amiga
./scripts/build.sh all
```

Each workflow builds everything normally required for that platform. For
example, `bbc` builds the BBC cc65 prerequisites, BBC `fujinet-nio-lib`, the
BBC test apps, the BBC `nio-config` binary, the standalone BBC config disk, and
the BBC `FN-BOOT.ssd`, then installs that boot disk into `fujinet-nio`
distfiles. Use `bbc-pty` when the next step is to start the PTY FujiNet runner.
The `amiga` workflow builds `fujinet-nio-lib`, `nio-apps` test/example
applications, and `nio-core-apps` utilities. It remains a platform workflow so
additional Amiga components can be added without changing the public build
interface.

Artifact-specific names such as `confnio-bbc-disk`, `config-bbc`,
`bbc-boot-disk`, and `cc65-bbc` remain available as artifact/debug tasks, but
are no longer the recommended user-facing entry points.

## Target Layers

Workspace targets should be split into three layers:

| Layer | Examples | Intended audience |
|---|---|---|
| workflow | `bbc`, `master`, `msdos`, `atari`, `linux`, `amiga`, `all` | normal daily use |
| artifact | `bbc-boot-disk`, `confnio-bbc-disk`, `qemu-msdos-image` | debugging a specific output |
| repo task | repo-local `make` invocations wrapped by Python methods | build tool internals and CI |

The workflow layer should be small enough to remember. The artifact and repo
layers can be discoverable through `--list` or `--explain`, but should not
dominate the default help output.

## Ownership Rules

Keep the current ownership rule:

- a repo-local artifact is built by the repo that owns its files
- a cross-repo artifact is orchestrated by the workspace
- `fujinet-nio` consumes finished boot/config images from `distfiles`
- emulator runners are workspace workflows, not app-repo responsibilities

Applied to current repositories:

- `nio-config` owns building `CONFNIO` and `KEYCODE`
- `fn-rom` owns BBC/Master transient ROM utilities and `FN-BOOT*.ssd`
- `nio-core-apps` owns core utility boot disks for platforms where those
  utilities are ordinary programs
- `nio-apps` owns test/example app builds only
- the workspace owns installing composed boot disks into `fujinet-nio`
  distfiles and starting emulator/device-side runners

## Python Build Front End

A Python front end now owns the build behavior:

```text
tools/build/
  pyproject.toml
  nio_build/
    cli.py
    context.py
    tasks.py
    workflows.py
    repos.py
    manifest.py
    runner.py
    tasks.py
```

The shell entry point is a thin wrapper:

```sh
#!/usr/bin/env bash
set -euo pipefail
exec python3 -m nio_build.cli "$@"
```

The Python tool provides:

- declarative task metadata: name, description, dependencies, outputs
- `--list` for the small public workflow set by default
- `--list --all` for every artifact/repo task
- `--explain <target>` to show what will run and why
- one manifest writer shared by every task
- structured logging without every task reimplementing `tee`

## Migration Plan

1. Done: add workflow aliases:
   `bbc`, `master`, `msdos`, `atari`, `linux`, `amiga`.
2. Done: hide compatibility aliases from help and document them only as temporary
   migration names.
3. Done: introduce the Python front end with parity for the workflow targets
   and current artifact targets.
4. Later: add a true `--dry-run` command planner instead of the current
   command-executing runner.
5. Later: port artifact targets only when they are still useful after the workflow
   layer exists.
6. Done: replace `scripts/build.sh` with the thin Python wrapper.

The important change is not Python by itself. The important change is reducing
the workspace public API to "build the right thing for this platform" and
making exact artifact targets secondary.
