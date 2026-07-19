# MS-DOS QEMU NIO Curses Workflow

This is the fast feedback path for MS-DOS NIO application UI work.

The goal is to run MS-DOS in QEMU, view the DOS screen directly in the terminal
with QEMU's curses display, and connect the DOS `FUJINET.SYS` driver to POSIX
`fujinet-nio` without using an ESP32.

## Architecture

```text
config-nio.exe
  -> FUJINET.SYS
  -> DOS COM1
  -> QEMU serial chardev socket
  -> fujinet-nio fujibus-tcp-debug
  -> local fujinet-data/
```

`FUJINET.SYS` remains unchanged. It still uses the DOS serial port. QEMU is the
adapter: COM1 is connected to a TCP socket, and POSIX `fujinet-nio` listens on
that socket.

The PTY path used by Beebium remains useful prior art, but this MS-DOS path uses
the existing TCP serial backend because it already works with `run-qemu-nio`.

## One Command

From the workspace root:

```sh
./scripts/build.sh msdos-dev-curses
```

This target:

- ensures `fujinet-nio` `fujibus-tcp-debug` exists
- builds `fujinet-nio-msdos/build/dos/fujinet.sys`
- builds PDCurses for Open Watcom/MS-DOS
- builds `nio-apps` MS-DOS applications, including `config-nio`
- builds `repos/fujinet-qemu-msdos/build/msdos-nio-apps.qcow2`
- launches QEMU with `--display curses`

The QEMU run is intentionally not piped through `tee`, because QEMU's curses
display needs to own a real terminal. In curses display mode, `fujinet-nio`
logs are redirected by `run-qemu-nio` to:

```text
repos/fujinet-qemu-msdos/build/fujinet-nio.log
```

## Manual Sequence

The workspace target is just orchestration. The equivalent explicit steps are:

```sh
./scripts/build.sh fujinet-tcp
./scripts/build.sh msdos-driver
./scripts/build.sh apps-msdos
./scripts/build.sh qemu-image
./scripts/build.sh qemu-run -- --display curses
```

For active UI work, prefer the one-command `msdos-dev-curses` target. It uses
the debug TCP FujiNet build and avoids the release/test work in `fujinet-tcp`.

## Running config-nio

Once DOS boots:

```dos
CONFNIO
```

`config-nio` is the first exemplar for this path. It is injected into the QEMU
image from `repos/fujinet-qemu-msdos/manifests/apps.yaml`:

```yaml
- src: ${NIO_APPS_MSDOS_BIN}/config-nio.exe
  name: CONFNIO.EXE
```

Keep using that manifest for future MS-DOS application setup. It maps long host
build filenames to DOS 8.3 image names and is shared by the bootable QEMU image
and raw FAT app images.

## Useful Commands

Build the bootable QEMU image without launching:

```sh
./scripts/build.sh qemu-image
```

Launch an existing image in curses mode:

```sh
./scripts/build.sh qemu-run -- --display curses
```

Show the QEMU command without starting QEMU:

```sh
./scripts/build.sh qemu-run -- --display curses --dry-run
```

Build the raw FAT app image for TNFS:

```sh
./scripts/build.sh msdos-image
```

## Notes For Future App Work

- Put MS-DOS app entries in `repos/fujinet-qemu-msdos/manifests/apps.yaml`.
- Use 8.3 destination names in the manifest.
- Keep `FUJINET.SYS` transport assumptions simple: app -> driver -> COM1.
- Let `run-qemu-nio` own the host-side transport choice.
- For curses UI debugging, use QEMU curses display first, then test real DOS
  hardware after the screen is broadly correct.
