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

## Amiga DiskDevice status and future media work

Stage 8, its hardening work, and DiskDevice Phase 2 are complete. Do not reopen
their implementation or replay their history unless a regression is found.
The completed acceptance record is
`completed/amiga-diskdevice-phase-2.md`; the durable user and architecture
contract is `docs/amiga/disk-media-architecture.md`.

Current production support is standard DD and high-density-floppy ADF media.
The standard `FMOUNT`/`FUMOUNT`/`FMOUNTRESTORE` workflow owns normal mounting,
eject, replacement, and persisted restoration. Amiga units `DN0:`–`DN7:` map
independently to the resident driver's eight DiskDevice slots; catalogue media
selection is not restricted to catalogue entries 1–8.

Future whole-volume HDF and partitioned RDB work is tracked in
`backlog/amiga-hdf-rdb-support.md`. Do not treat it as unfinished Phase 2 or
broaden media support without satisfying that task's staged validation.

For an HDF/RDB scratch session, read only these files first:

1. `AGENTS.md`
2. `backlog/amiga-hdf-rdb-support.md`
3. `docs/amiga/disk-media-architecture.md`
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

Before implementation, identify the owning repository from the active ticket:

- `repos/nio-core-apps`: standard `FMOUNT`/`FUMOUNT` command behavior.
- `repos/fujinet-nio-driver`: Amiga resident device, dynamic geometry,
  MountLists/device integration, and native tests.
- `repos/fujinet-nio-lib`: shared DiskDevice/session contracts and target
  transport only when a library change is required.
- Workspace `integration-tests/amiberry`: cross-repository acceptance tests.
- Workspace `backlog/`: active goal scope, dependencies, checkboxes, and exit
  criteria only.
- Workspace `docs/amiga/`: durable user and architecture documentation.
- Workspace `completed/`: closed acceptance records and historical evidence.

Use the smallest context sufficient for the ticket. Quote the relevant active
checkbox and read only the owning implementation file, its focused tests, and
the associated architecture section. Do not load completed Stage 8/Phase 2
history unless the ticket explicitly concerns a regression or an established
contract.

Amiga validation remains environment-sensitive. Source the environment first;
when changing `repos/fujinet-nio-lib`, run the complete `make check`; for Amiga
changes, run the native driver tests/build and focused Amiberry cases before a
complete `scripts/build.sh amiga-tests` gate when the active acceptance task
requires it.
