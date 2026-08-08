# AmigaOS testing with Amiberry

The workspace can build a licensed AmigaOS 3.2 test HDF, boot it in Amiberry,
and connect its emulated `serial.device` to a POSIX FujiNet NIO instance.
The HDF is local Amiberry storage; FujiNet NIO remains the network/device
service and does not need Amiga disk support for this workflow.

## Prerequisites

Install `amiberry`, `socat`, `nc`, and the `m68k-amigaos` toolchain. Set the
Amiga asset root if it is not the default:

```sh
export AMIBERRY_ASSET_ROOT="$HOME/dev/amiga/amigaOS3.2"
```

The root must contain `ROM/kickCDTVa1000a500a2000a600.rom`,
`ADF/Workbench3.2.adf`, and `L/FastFileSystem`. These are user-supplied
licensed assets and are not stored in the workspace.

## Build and run

Build the Amiga example applications and a bootable HDF containing
`wifitest`:

```sh
./scripts/build.sh amiga-e2e --timeout 15
```

The runner defaults to Amiberry's TCP serial endpoint with
`serial_direct=true`, connected through a small `socat` bridge to the
`fujibus-tcp-debug` NIO profile. This direct setting is important: without it,
Amiberry's emulated serial reader drops bytes from binary FujiBus frames.
Logs are written under `build/amiga-e2e/`.

The runner also has an experimental `--pty` mode, using the topology employed
by FS-UAE and Jeff Piepmeier's Amiga harness: PTY → socat → PTY →
`fujibus-rs232-debug`. The current Amiberry build does not recognize
`/dev/pts/*` as a serial device, so use the default TCP mode with Amiberry.

To run a core utility instead:

```sh
AMIGA_TEST_PROJECT=core AMIGA_TEST_APP=fhost \
  ./scripts/build.sh amiga-e2e --timeout 15
```

The generated HDF is under `build/images/`. The builder imports
`Devs/serial.device` from the licensed Workbench ADF and installs the app in
the `C:` path. The startup command can be overridden with
`AMIGA_TEST_COMMAND` when an app needs arguments.

## Interactive session with your own NIO

First start FujiNet NIO yourself and leave it listening on TCP port `65504`.
Use the same NIO configuration you normally use; the important part is that
its TCP channel is enabled on that port.

In another terminal, build an interactive HDF. This preserves the normal
Workbench startup sequence instead of running one app and exiting:

```sh
AMIGA_TEST_INTERACTIVE=1 ./scripts/build.sh amiga-test-disk
```

The simplest way to build an interactive Workbench disk and connect it to the
already-running NIO is:

```sh
./scripts/build.sh amiga-workbench -- --external-nio
```

This builds the selected app into the HDF but preserves the normal Workbench
startup sequence. Amiberry opens visibly; open `System/Shell` and run the app.
The test-image builder removes Workbench's optional `WBStartup/Welcome`
program, so the first-run "Welcome to the Amiga Preinstallation Environment"
requester does not interrupt automated or interactive tests.

Alternatively, build and run in two steps:

```sh
AMIGA_TEST_INTERACTIVE=1 ./scripts/build.sh amiga-test-disk
./scripts/run-amiberry-nio \
  --external-nio \
  --disk build/images/amiga-wifitest.hdf
```

This command remains running. Amiberry should show the Workbench display;
open `System/Shell` (or the Shell icon) and type commands such as:

```text
 wifitest
 fhost
 fls
```

The selected example app and all built Amiga `nio-core-apps` utilities are
installed in `C:`. This gives the interactive test disk the standard FujiNet
commands, including `fmount`, `fboot`, `fhost`, `fapp`, `fin`, `fls`, `fout`,
and `fdrive`. The selected app still controls the startup command for
non-interactive e2e images. To make a core utility the e2e command, use
`AMIGA_TEST_PROJECT=core AMIGA_TEST_APP=fhost`.

On a native Wayland desktop such as Hyprland, install `wtype` for keyboard
injection and use `hyprctl` to focus Amiberry first. `grim` can capture the
whole desktop for test evidence:

```sh
AMIBERRY_WINDOW=$(hyprctl clients -j | jq -r '.[] | select(.class == "amiberry") | .address' | head -1)
hyprctl dispatch focuswindow "address:$AMIBERRY_WINDOW"
wtype 'wifitest'
grim build/amiga-e2e/screen.png
```

`xdotool` is only useful if Amiberry is running through XWayland; the normal
SDL3 build is a native Wayland client.

If your NIO listens on another host or port, add `--nio-port PORT` and set
`FUJINET_HOST=HOST` as appropriate. The Amiberry-side TCP listener defaults
to `127.0.0.1:23462`; it is bridged locally to NIO and normally needs no
change. Use `--tcp` explicitly to select this mode; it is also the default.

## What this validates

`wifitest` exercises `fn_init()` and the Wi-Fi status/configuration/scan wire
operations. `fhost` exercises the host-device protocol. The generated NIO
configuration uses the simulated Wi-Fi backend, so the Wi-Fi test can verify
decoded status, configuration, and scan records without requiring host Wi-Fi.

The Amiga transport registers cleanup for `serial.device` at process exit.
This matters because Amiga applications are normally short-lived CLI commands;
without releasing the device, a second invocation could fail at `fn_init()`
with `device not found` before producing any FujiBus traffic.

This keeps the architecture split clean: Amiga code uses the platform
transport in `fujinet-nio-lib`, Amiberry supplies the guest serial device, and
POSIX `fujinet-nio` owns the device services. Future FujiNet disk-image support
can be added independently; it is not required to boot or test these apps.
