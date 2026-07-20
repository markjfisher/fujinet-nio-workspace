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
- builds and installs the `nio-apps` boot disks into `fujinet-nio/distfiles`
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
./scripts/build.sh qemu-msdos-image
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
image under `C:\FNAPPS` from `manifests/disks/qemu-msdos-apps.yaml`:

```yaml
- src: ${NIO_APPS_MSDOS_BIN}/config-nio.exe
  name: CONFNIO.EXE
```

The generated `AUTOEXEC.BAT` adds `C:\FNAPPS` to `PATH`, so `CONFNIO` and the
`F*` tools can be run from any DOS directory. The POSIX `fujinet-nio` instance
also receives the current MS-DOS boot/config disk at:

```text
host:/boot/msdos/autorun.img
```

That boot disk is copied from:

```text
repos/fujinet-nio/distfiles/boot/msdos/autorun.img
```

That path is supplied by the workspace `scripts/build.sh qemu-run` wrapper. The
underlying `repos/fujinet-qemu-msdos/run-qemu-nio` script remains standalone and
only accepts an optional `--nio-boot-disk` path.

No empty writable `FNDOS` disk is mounted by default. For a test that needs one,
pass it explicitly:

```sh
./scripts/build.sh qemu-run -- --display curses \
  --nio-scratch-disk repos/fujinet-qemu-msdos/fujinet-data/dos/fn-dos.img
```

That scratch disk uses config `slot: 2` by default. FujiNet YAML mount slots are
user-facing 1-8; runtime slot 0 is the first internal slot and is reserved by
the boot/config disk in this workflow.

## Useful Commands

Build the bootable QEMU image without launching:

```sh
./scripts/build.sh qemu-msdos-image
```

Launch an existing image in curses mode:

```sh
./scripts/build.sh qemu-run -- --display curses
```

Drive the running QEMU instance from another terminal through its monitor
socket:

```sh
./scripts/build.sh qemu-monitor type CONFNIO ret
./scripts/build.sh qemu-monitor sendkey q
./scripts/build.sh qemu-monitor sendkey left ret
```

Prefer this for repeatable TUI testing. It sends QEMU `sendkey` commands through
the monitor socket, so it does not depend on typing into the curses display
terminal. The default monitor socket is:

```text
repos/fujinet-qemu-msdos/build/qemu-nio-monitor.sock
```

`qemu-run` enables that socket by default. Override it with
`--monitor path/to/socket` or disable it with `--no-monitor`.

Show the QEMU command without starting QEMU:

```sh
./scripts/build.sh qemu-run -- --display curses --dry-run
```

Build the raw FAT app image for TNFS:

```sh
./scripts/build.sh msdos-apps-image
```

## Notes For Future App Work

- Put workspace QEMU app entries in `manifests/disks/qemu-msdos-apps.yaml`.
- Use 8.3 destination names in the manifest.
- The QEMU image builder puts those apps in `C:\FNAPPS`, not `C:\`.
- Keep `FUJINET.SYS` transport assumptions simple: app -> driver -> COM1.
- Let `run-qemu-nio` own the host-side transport choice.
- Keep workspace-specific default boot disk paths in `scripts/build.sh`, not in
  `repos/fujinet-qemu-msdos`.
- For curses UI debugging, use QEMU curses display first, then test real DOS
  hardware after the screen is broadly correct.
