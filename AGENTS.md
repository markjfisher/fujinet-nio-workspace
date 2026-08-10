# Workspace agent instructions

## Environment and toolchains

Before building or testing repositories in this workspace, source the shared
environment setup:

```sh
source "$NIO_WORKSPACE/scripts/env.sh"
```

When `~/.local/bin/add_watcom.sh` exists, `scripts/env.sh` sources it for the
current shell. This is required for the MS-DOS Open Watcom targets; do not
assume `wcc` is on the global PATH.

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
