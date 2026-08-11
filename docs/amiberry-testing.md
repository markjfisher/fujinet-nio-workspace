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

Named Amiberry environments are defined in
`configs/amiga/workbenches.yaml`. The default profile is `wb3.2`; select an
older or custom environment with `AMIGA_WORKBENCH_CONFIG`. Direct-image
profiles skip test-disk construction and are useful for trying older ROMs and
operating systems:

```sh
AMIGA_WORKBENCH_CONFIG=wb1.3 \
./scripts/build.sh amiga-workbench -- --external-nio
```

For interactive use, the profile can be selected directly on the build
target; the environment variable remains useful for scripts and defaults:

```sh
./scripts/build.sh amiga-workbench --profile wb1.3 -- --external-nio
```

To use another profile file:

```sh
AMIGA_WORKBENCH_CONFIG_FILE="$HOME/path/to/workbenches.yaml" \
AMIGA_WORKBENCH_CONFIG=my-profile \
./scripts/build.sh amiga-workbench -- --external-nio
```

Each profile can specify `disk`, `kickstart`, `build_test_disk`, and an
Amiberry `settings` mapping such as `cpu_type`, `chipmem_size`, and
`fastmem_size`. An optional `uae_config` entry loads an existing Amiberry
configuration before applying the profile settings.

The runner defaults SDL3 to `SDL_VIDEO_DRIVER=kmsdrm,wayland,x11`, while
respecting either SDL video-driver variable if already set. SDL3 documents
`SDL_VIDEO_DRIVER` as the canonical spelling; `SDL_VIDEODRIVER` is retained as
the compatibility spelling.

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

## Automated Amiberry integration tests

The workspace has a reusable guest integration suite under
`integration-tests/amiberry/`. It starts a fresh POSIX FujiNet-NIO and
Amiberry for each case, builds a test HDF with a generated Startup-Sequence,
extracts guest result files, and asserts their contents:

```sh
./scripts/build.sh amiga-tests
```

Run a focused case or see verbose output with:

```sh
./scripts/run-amiga-e2e-tests -k wifi -v
./scripts/run-amiga-e2e-tests -k cli -v
```

The first tests cover Wi-Fi SET/GET/status/scan using the public
`fujinet-nio-lib` API and stateful CLI behavior across separate processes:
`FHOST` set/get, `FLS` with an argument, and `FAPP` PUT/GET/LIST/DEL. This
exercises the application argument paths and persistence mechanism rather
than only launching an executable.

Every run creates a timestamped evidence tree at
`test-evidence/amiberry-YYYYMMDD-HHMMSS/`. Each case leaves a guest-only IPC
screenshot at `<run>/<case>/amiberry-screen.png`, alongside its HDF and
component logs. Set `AMIGA_E2E_EVIDENCE_ROOT` to choose an explicit directory.
These ignored artifacts are retained for manual review and cleanup. Protocol
cases run in the Amiga boot CLI and do not load
Workbench: their result files are displayed with `Type`, then the CLI
framebuffer is captured through IPC. Amiberry is launched visibly (with
`-G`, which skips its configuration GUI but does not hide the emulated
display), at maximum emulation speed (`-w -1`). The screenshot does not
capture the host desktop. Adjust the short capture delay with
`AMIGA_E2E_SCREENSHOT_DELAY` when a test's guest display changes later in
boot.

For cases whose mounted handlers continue producing protocol traffic, set a
unique `completion_log` marker in `integration-tests/amiberry/tests.toml` and
emit its successful NIO operation only after the guest has displayed all
results. This triggers immediate capture and IPC shutdown; the configured
timeout remains a safety bound rather than the normal completion mechanism.
The harness clears stale IPC/evidence files before launch and fails if the
new screenshot is not retained.

See `integration-tests/amiberry/README.md` for the four-step process for
adding another test. The test registry is
`integration-tests/amiberry/tests.toml`, and guest startup sequences live in
`integration-tests/amiberry/startup/`.

Amiberry builds with IPC socket support expose a Unix socket in
`$XDG_RUNTIME_DIR/amiberry.sock` (or `/tmp/amiberry.sock`). The workspace has
a small client for the text protocol. It discovers the active instance and
can capture only the Amiberry framebuffer, avoiding desktop-wide screenshots:

```sh
./scripts/amiberry-ipc GET_STATUS
./scripts/amiberry-ipc SCREENSHOT build/amiga-e2e/amiberry-screen.png
./scripts/amiberry-ipc SEND_KEY 65 1   # press key code 65
./scripts/amiberry-ipc SEND_KEY 65 0   # release it
```

`run-amiberry-nio` prints the socket path and writes it to
`build/amiga-e2e/amiberry.sock.path` when it detects one. The protocol also
provides commands such as `READ_MEM`, `GET_CPU_REGS`, and `GET_CONFIG` for
future diagnostics. See the [Amiberry IPC socket documentation](https://github.com/BlitterStudio/amiberry/wiki/IPC-Socket-support)
for command and key-code details.

On a native Wayland desktop such as Hyprland, `wtype` and `grim` remain useful
fallbacks when IPC is unavailable. `grim` captures the whole desktop for test
evidence:

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
