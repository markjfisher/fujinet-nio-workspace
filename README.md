# fujinet-nio-workspace

Workspace and build orchestration for the fujinet-nio development stack.

This repository owns no product source code. It pins the related repositories as
submodules and provides one place to set environment variables, build the stack,
create MS-DOS images, and record exactly which commits were used.

## Repository Layout

```text
fujinet-nio-workspace/
  repos/
    fujinet-nio/
    fujinet-nio-lib/
    nio-apps/
    fujinet-qemu-msdos/
    fujinet-msdos/
    fn-rom/
    bounce-world-client-nio/
  scripts/
    env.sh
    build.sh
    build-all.sh
    make-msdos-image.sh
    status-all.sh
    update-all.sh
  build/
    logs/
    images/
  local/
    config.env
```

`build/` and `local/config.env` are intentionally ignored.

## Clone

```sh
git clone --recurse-submodules <workspace-url>
cd fujinet-nio-workspace
```

For an existing clone:

```sh
scripts/update-all.sh
```

To move submodules to their configured remote branches:

```sh
scripts/update-all.sh --remote
git status
```

Review and commit the changed submodule pointers in this workspace repo when you
want to pin a new integrated stack.

## Environment

Every script sources:

```sh
scripts/env.sh
```

The defaults point at the submodules:

```sh
FUJINET_NIO=repos/fujinet-nio
FUJINET_NIO_LIB=repos/fujinet-nio-lib
NIO_APPS=repos/nio-apps
FUJINET_QEMU_MSDOS=repos/fujinet-qemu-msdos
FUJINET_MSDOS=repos/fujinet-msdos
FN_ROM=repos/fn-rom
BOUNCE_WORLD_CLIENT_NIO=repos/bounce-world-client-nio
```

Override any of them in `local/config.env`:

```sh
export FUJINET_NIO=/home/markf/dev/nio/repos/fujinet-nio
export FUJINET_NIO_LIB=/home/markf/dev/nio/repos/fujinet-nio-lib
export NIO_APPS=/home/markf/dev/nio/repos/nio-apps
export FUJINET_MSDOS=/home/markf/dev/msdos/fujinet-msdos
```

`env.sh` also sources `~/.local/bin/add_watcom.sh` when present, so Open Watcom
builds work from the workspace scripts.

## Build

Build the usual integrated stack:

```sh
scripts/build.sh all
```

Useful smaller targets:

```sh
scripts/build.sh fujinet-tcp
scripts/build.sh fujinet-pty
scripts/build.sh fujinet-rs232
scripts/build.sh lib
scripts/build.sh msdos-driver
scripts/build.sh apps-msdos
scripts/build.sh bounce-world
scripts/build.sh msdos-image
scripts/build.sh qemu-image
```

`scripts/build.sh all` builds:

- fujinet-nio TCP debug and release presets
- fujinet-nio PTY debug preset
- fujinet-nio RS-232 debug preset
- fujinet-nio-lib Linux and MS-DOS libraries
- fujinet-msdos `FUJINET.SYS` with `FUJINET_TRANSPORT=NIO`
- nio-apps MS-DOS tools
- bounce-world-client-nio
- raw FAT image from `nio-apps/msdos/bin`
- QEMU qcow image through `fujinet-qemu-msdos`

The QEMU image builder defaults to `repos/fujinet-qemu-msdos/msdos.qcow2`.
Set `BASE_IMAGE` only when you want to use a different base image:

```sh
BASE_IMAGE=/path/to/base-dos.qcow2 scripts/build.sh qemu-image
```

## QEMU

After building the TCP fujinet binary and a QEMU image:

```sh
scripts/build.sh qemu-run
```

Additional arguments are passed to `run-qemu-nio`:

```sh
scripts/build.sh qemu-run -- --hda repos/fujinet-qemu-msdos/build/msdos-nio-apps.qcow2
```

## Status And Manifest

Show workspace and submodule state:

```sh
scripts/status-all.sh
```

Each build writes:

```text
build/manifest.txt
```

The manifest records the workspace path, submodule commits, dirty markers, and
important output paths. It is meant to catch stale binaries and image mismatches.

## Notes

- Subprojects remain independently buildable. The workspace only supplies a
  common environment and build order.
- `nio-docs` currently has no remote configured in its source checkout, so its
  submodule URL is a local relative path. Update `.gitmodules` when it has a
  remote.
- If you are actively editing the original checkouts under `/home/markf/dev/nio/repos`,
  set those paths in `local/config.env` so the workspace builds your working
  trees rather than the pinned submodule clones.
