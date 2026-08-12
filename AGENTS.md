# Workspace agent instructions

## Environment and toolchains

Before building or testing repositories in this workspace, source the shared
environment setup:

```sh
source "$NIO_WORKSPACE/scripts/env.sh"
```

The same setup exports `CC65_HOME` for Atari/BBC builds and adds the configured
Amiga cross-toolchain directory when available.

For Amiga builds, the compiler and NDK headers must also be readable by the
current user. A toolchain that is present but contains unreadable headers is an
environment failure, not a source-build pass.

## Library change check

For every change under `repos/fujinet-nio-lib`, run:

```sh
cd "$NIO_WORKSPACE/repos/fujinet-nio-lib"
make check
```

`make check` first builds every configured library target, then runs the fast
host-side wire tests and public archive-link test. A partial build is not an
all-target pass; if a toolchain is genuinely unavailable, record the exact
target and toolchain in the task review.

## Cross-repository work

Use `backlog/` for active workspace-level goals and move completed goal files
to `completed/`. Keep repository-specific implementation details in the
owning repository's documentation.

## Amiga DiskDevice Phase 2 handoff

Stage 8 and its hardening work are complete. Do not reopen the standard-ADF
implementation or replay its history unless a regression is found. Phase 2 is
the active goal:

- Standard `nio-core-apps` `FMOUNT`/`FUMOUNT` must replace the transitional
  `fujinet-mount` end-user workflow.
- Amiga units `DN0:`–`DN7:` must continue to map to catalogue slots 1–8.
- Remove the driver's fixed 880 KiB/1760-sector assumption and use successful
  NIO `Info` geometry independently for each unit.
- Define DD/HD ADF support separately from partitioned RDB/HDF media.
- Preserve Stage 8 writable, replacement, persistence, queue, notification,
  and timeout regressions for every supported geometry.

The Phase 2 acceptance criteria and unchecked work are authoritative in:

```text
backlog/amiga-diskdevice-phase-2.md
backlog/amiga-disk-media-architecture.md
```

For a scratch-session startup, read only these files first:

1. `AGENTS.md`
2. `backlog/amiga-diskdevice-phase-2.md`
3. `backlog/amiga-disk-media-architecture.md`
4. `repos/fujinet-nio-driver/amiga/README.md`
5. `repos/fujinet-nio-driver/amiga/WRITE_MEDIA_POLICY.md`

Then inspect the current commits and status in the workspace plus these
repositories:

```sh
git status --short
git log --oneline -10
git -C repos/fujinet-nio-driver log --oneline -5
git -C repos/fujinet-nio-lib log --oneline -5
```

Before implementation, identify the owning repository from the Phase 2 ticket:

- `repos/nio-core-apps`: standard `FMOUNT`/`FUMOUNT` command behavior.
- `repos/fujinet-nio-driver`: Amiga resident device, dynamic geometry,
  MountLists/device integration, and native tests.
- `repos/fujinet-nio-lib`: shared DiskDevice/session contracts and target
  transport only when a library change is required.
- Workspace `integration-tests/amiberry`: cross-repository acceptance tests.
- Workspace `backlog/`: goal status and acceptance evidence only.

Use the smallest context sufficient for the ticket. Quote the relevant Phase 2
checkbox and read only the owning implementation file, its focused tests, and
the associated architecture section. Do not load the completed Stage 8
backlog or full session history unless the ticket explicitly concerns a
regression or a contract established there.

Phase 2 validation remains environment-sensitive. Source the environment first;
when changing `repos/fujinet-nio-lib`, run the complete `make check`; for Amiga
changes, run the native driver tests/build and the focused Amiberry case before
the complete `scripts/build.sh amiga-tests` gate.
