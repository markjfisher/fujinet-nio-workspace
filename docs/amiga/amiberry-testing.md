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

For a single interactive playground image containing every Amiga application
from `nio-apps`, every Amiga utility from `nio-core-apps`, and the resident
FujiNet disk driver, use:

```sh
./scripts/build.sh amiga-workbench --all-apps --with-driver -- --external-nio
```

The image includes `DEVS:fujinet-disk.device` and `C:fujinet-mount`, but no
static `DN0`-`DN7` MountLists. `fmount` inspects the selected media and creates
the DOS node dynamically. The generated HDF is the local interactive image at
`build/images/amiga-workbench.hdf`; it is not a TNFS-mounted media image. With
`--with-driver`, its startup sequence also runs
`C:LoadModule DEVS:fujinet-disk.device` before Workbench loads, so the driver
is ready after a warm start without opening a shell manually.

Additional Amiga archives can be unpacked into the HDF while it is being
assembled. For example, to stage the Picasso96 installer and its files:

```sh
./scripts/build.sh amiga-workbench \
  --profile wb3.2 \
  --all-apps \
  --with-driver \
  --install-archive \
  /home/markf/dev/amiga/AmigaForever/af11/Archives/Picasso96/Picasso96.lha \
  -- \
  --external-nio
```

The archive is extracted under the HDF root, preserving its
`Picasso96Install/` tree. The Amiga-side `InstallPicasso96` program is not
run automatically; launch it from Workbench or a Shell when you want to
perform its interactive installation. Multiple `--install-archive` options
are supported. The same list can be stored in a profile as an
`install_archives` YAML list (`install_archive` is also accepted for
compatibility). The `all_apps` and `with_driver` flags can be stored in the
profile as well, so the complete environment can be recreated without
command-line switches. For example:

```yaml
profiles:
  wb32-setup:
    build_test_disk: true
    disk: ${NIO_WORKSPACE}/build/images/amiga-wb32-base.hdf
    kickstart: ${AMIBERRY_ASSET_ROOT}/ROM/kickCDTVa1000a500a2000a600.rom
    all_apps: true
    with_driver: true
    install_archives:
      - /path/to/Picasso96.lha
    settings:
      cpu_type: 68040
      z3_autoconfig: true

  wb32-run:
    build_test_disk: false
    disk: ${NIO_WORKSPACE}/build/images/amiga-wb32-run.hdf
    kickstart: ${AMIBERRY_ASSET_ROOT}/ROM/kickCDTVa1000a500a2000a600.rom
    settings:
      cpu_type: 68040
      z3_autoconfig: true
```

Build the setup image with `--profile wb32-setup`, copy it to the run image
when you want a disposable working copy, then launch the copy with
`--profile wb32-run`.

## Building ADF media for TNFS

`amiga-test-adf` preserves the licensed Workbench filesystem by default. Give
each image a unique volume label when creating media for `fmount`:

```sh
AMIGA_TEST_APP=sizetest \
  ./scripts/build.sh amiga-test-adf --label SIZETEST
```

For a formatted, non-bootable ADF containing only the selected application
under `C:`, use `--blank`:

```sh
AMIGA_TEST_APP=sizetest \
  ./scripts/build.sh amiga-test-adf --blank --label SIZETEST
```

The output is `build/images/amiga-sizetest.adf`. Blank images contain no
Workbench files or startup sequence; they are intended as media for
`fmount`, not as disks to boot directly.

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
`fastmem_size`. These values are directly mapped to `-s` key/value pairs
and match the names found in typical UAE config files.

For a generated profile (`build_test_disk: true`), `disk` is
the output HDF path; if omitted, the default is
`build/images/amiga-workbench.hdf`. For a direct profile
(`build_test_disk: false`), `disk` is an existing image to reuse. An optional
`uae_config` entry loads an existing Amiberry configuration before applying
the profile settings.

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

To inspect guest result files after a focused pytest run, select the newest
evidence directory and its case HDF, then use `xdftool type`:

```sh
RUN=$(/bin/ls -dt test-evidence/amiberry-* | head -1)
HDF=$(find "$RUN" -type f -name '*diskdevice-fmount-restore*.hdf' | head -1)
uvx --from amitools xdftool "$HDF" type restore-startup.result
```

Replace the HDF glob and result filename with the focused case and checkpoint
you need. The same files are normally extracted and asserted by pytest; direct
HDF inspection is useful for reviewing retained evidence or diagnosing the
last checkpoint reached by an interrupted run. The case directory also
contains `amiberry.log`, `fujinet-nio.log`, the framebuffer screenshot, and
the generated HDF.

### Disk-media acceptance evidence

The current Amiga production support boundary is standard DD and
high-density-floppy ADF media. The focused cases supporting that statement are:

| Case | Evidence |
| --- | --- |
| `diskdevice-fmount` | Standard-command DD access, replacement, failed-replacement preservation, writable copy, eject/remount durability, and mapping state |
| `diskdevice-hd-stage8` | Standard-command high-density-floppy replacement and writable eject/remount durability |
| `diskdevice-hd-adf` | 512 x 3520 geometry plus the resident concurrent-access and change-notification boundary |
| `diskdevice-dynamic-fmount-dd` / `diskdevice-dynamic-fmount-hd` | Initial DD/high-density-floppy mount with no static MountList |
| `diskdevice-fmount-restore` | Fresh-process restoration of simultaneous DD and high-density-floppy mappings, followed by standard eject and mapping removal |
| `diskdevice-fmount-restore-invalid` | Invalid persisted catalogue entry fails without creating a DOS node |

Run only the relevant case while investigating a support claim, for example:

```sh
pytest integration-tests/amiberry/test_diskdevice_fmount.py \
  -k 'hd_stage8' -vv --run-amiga
pytest integration-tests/amiberry/test_diskdevice_fmount_restore.py \
  -vv --run-amiga
```

These cases do not establish support for whole-partition HDF or whole-disk RDB
images. The test HDF containing AmigaOS and retained result files is the
emulator's local boot/storage medium, not media mounted through `DNx:`.

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

### Debugger IPC

You must be running at least amiberry 8.3.0 for the debugger fixes that correct breakpoint and stepping issues
that were in previous releases.

The existing `scripts/amiberry-ipc` helper passes debugger commands directly
to Amiberry:

```sh
./scripts/amiberry-ipc DEBUG_ACTIVATE
./scripts/amiberry-ipc DEBUG_STATUS
./scripts/amiberry-ipc GET_CPU_REGS
./scripts/amiberry-ipc SET_BREAKPOINT 0xADDRESS
./scripts/amiberry-ipc DISASSEMBLE 0xADDRESS 16
./scripts/amiberry-ipc READ_MEM 0xADDRESS 4
./scripts/amiberry-ipc DEBUG_CONTINUE
```

Breakpoint hits leave the emulator paused. Capture registers, disassembly,
and request memory with the same helper before issuing `DEBUG_CONTINUE`.
`READ_MEM` accepts widths 1, 2, or 4 bytes.

PAUSE/RESUME is emulator pause control.

DEBUG_CONTINUE is debugger-stop control and should be used once Amiberry
reports the debugger as internally stopped (stopped=1), e.g. after a
breakpoint.

Do not substitute DEBUG_CONTINUE for RESUME after a generic IPC PAUSE.

### Debugging Playbook

This is a host-side manual for diagnosing an Amiga guest failure. Preserve a
normal, controller-free reproduction first. Debugger controllers pause or slow
the guest and can change timing; diagnostic success is not a regression pass.

#### Capture Passive Timeout Evidence

Before adding a breakpoint, collect the failure boundary:

```sh
./scripts/amiberry-ipc GET_STATUS
./scripts/amiberry-ipc GET_CPU_REGS
./scripts/amiberry-ipc DISASSEMBLE 0x00f80000 16
./scripts/amiberry-ipc SCREENSHOT test-evidence/manual-screen.png
```

Replace the disassembly address with `PC` from `GET_CPU_REGS`. Retain status,
registers, disassembly around `PC`, a small longword window from `A7`, and the
framebuffer. This distinguishes a requester, a paused debugger, a handler
wait, a ROM idle loop, and resident-device code before making a theory.

#### Derive Guest Layouts From the NDK

Never decode guest memory with host ABI layouts or guessed offsets. Generate
them against the installed m68k NDK:

```sh
source "$NIO_WORKSPACE/scripts/env.sh"
printf '%s\n' \
  '#include <stddef.h>' \
  '#include <exec/tasks.h>' \
  '#include <dos/dosextens.h>' \
  'int task_state = offsetof(struct Task, tc_State);' \
  'int process_port = offsetof(struct Process, pr_MsgPort);' \
  | m68k-amigaos-gcc -x c -S -o /tmp/amiga-ndk-offsets.s -
```

Read the generated `.long` initializers. Repeat for `MsgPort`, `Message`,
`DosPacket`, `CommandLineInterface`, and `DeviceNode`. A BPTR is an Amiga
word pointer: dereference it at `BPTR << 2`.

For a standard `IORequest` at `A1` in `BeginIO`, use these m68k offsets:

```text
io_Unit    +24 long       io_Command +28 word
io_Flags   +30 byte       io_Error   +31 byte
io_Actual  +32 long       io_Length  +36 long
io_Data    +40 long       io_Offset  +44 long
```

The `io_Offset` offset is `+44`. Reading `+40` decodes the data pointer as a
plausible but false disk offset and LBA.

#### Resolve Relocatable Resident Vectors

Do not use a map address directly as a breakpoint. Resident code is relocated
when loaded. Obtain link-time offsets from:

```text
repos/fujinet-nio-driver/build/amiga/fujinet-disk.device.map
```

Then resolve the loaded device from Exec. `tools/amiga_emulator/device_debug.py`
reads ExecBase from address `4`, walks `ExecBase.DeviceList`, matches
`fujinet-disk.device`, and decodes standard library vectors:

```text
Open=-6 Close=-12 Expunge=-18 BeginIO=-30 AbortIO=-36
```

Validate that `BeginIO`, `Close`, and `AbortIO` yield the same relocation delta
before deriving an internal breakpoint. Fail closed if the deltas differ.

Example:

```python
from pathlib import Path
from amiga_emulator import device_debug

offsets = {"begin_io": 0x110e, "close": 0x10c0, "abort_io": 0x10f0}
vectors = device_debug.write_resolution_log(
    Path("/run/user/1000/amiberry.sock"),
    Path("test-evidence/device-resolution.log"), offsets,
)
print(hex(vectors.begin_io))
```

#### Capture a Bounded BeginIO Stream

At `device_begin_io()`, `A1` is the live `IORequest *` and `A6` is the device
base. Set one breakpoint, record request fields, then continue immediately:

```sh
./scripts/amiberry-ipc DEBUG_ACTIVATE
./scripts/amiberry-ipc SET_BREAKPOINT 0xRUNTIME_BEGINIO
./scripts/amiberry-ipc DEBUG_CONTINUE
# after the hit:
./scripts/amiberry-ipc GET_CPU_REGS
./scripts/amiberry-ipc READ_MEM 0xREQUEST_PLUS_28 2
./scripts/amiberry-ipc READ_MEM 0xREQUEST_PLUS_44 4
./scripts/amiberry-ipc DEBUG_CONTINUE
```

For aligned 512-byte operations, calculate `LBA = io_Offset / 512`. Persist a
short record containing PC, request pointer, command, flags, error, actual,
length, offset, and LBA. Do not single-step ordinary execution.
`tools/amiga_emulator/debug_snapshot.py` supplies reusable request readers;
`tools/amiga_emulator/beginio_trace.py` is a bounded controller example.

#### Find Call Return and Completion Sites

Use disassembly to break after a helper returns, not only at helper entry:

```sh
source "$NIO_WORKSPACE/scripts/env.sh"
m68k-amigaos-objdump -d \
  repos/fujinet-nio-driver/build/amiga/fujinet-disk.device
```

Find the linked `jsr`/`bsr`, use the instruction immediately following it as
the return breakpoint, and add the verified relocation delta to both addresses.
At helper entry record input fields; at return record `D0 & 0xff`,
`io_Actual`, and `io_Error`; at the common completion point record final
request fields immediately before `ReplyMsg` or the quick-return path.

`IOF_QUICK` requests complete synchronously from `BeginIO`; absence of
`ReplyMsg` is expected. A successful quick command keeps `IOF_QUICK`, has
`io_Error == 0`, and is followed by normal guest progress.

#### Bounded Controllers

A controller is a host Python diagnostic program, not guest/resident code and
not Sidecar, serial-bridge, or protocol validation:

```text
runner starts Amiberry -> obtains exact IPC socket
  -> optional controller resolves live state and arms breakpoints
  -> serial bridge releases unchanged guest startup
  -> controller records bounded evidence and cleans up
```

Controllers prevent the race where a separate terminal notices the socket only
after guest startup has passed the target. A startup-sensitive controller may
pause Amiberry before the serial bridge is opened, arm a breakpoint, then
continue. If `LoadModule` registers the resident later, allow the guest to run
only until the device appears in the live DeviceList, pause, resolve, arm, and
continue.

##### Checked-In Runner Hook

The checked-in implementation is in `tools/amiga_emulator/run.py`. Its order
is important: the socket is written first; an opt-in controller activates the
debugger and starts; only then does `start_amiberry()` reach the TCP `socat`
bridge code that lets the guest startup sequence run.

The relevant code is deliberately ordinary Python, not hidden runner magic:

```python
# tools/amiga_emulator/run.py, inside start_amiberry()
self.ipc_socket = logged_socket
(self.run_dir / "amiberry.sock.path").write_text(
    str(self.ipc_socket) + "\n", encoding="utf-8"
)

if os.environ.get("AMIGA_E2E_BEGINIO_TRACE") == "1":
    # The guest cannot run through the serial startup path while paused.
    ipc.request(self.ipc_socket, "DEBUG_ACTIVATE")
    self.debugger_controller = self.start_process(
        [sys.executable, "-m", "amiga_emulator.beginio_trace",
         "--socket", str(self.ipc_socket),
         "--output-dir", str(self.run_dir)],
        self.run_dir / "beginio-controller.log", cwd=ROOT,
    )

# This is later in the same method. Opening socat releases guest serial I/O.
self.bridge = self.start_process(
    ["socat", "-d", "-d",
     f"TCP:{self.host}:{self.amiga_port}",
     f"TCP:{self.nio_host}:{self.nio_port}"],
    self.bridge_log,
)
```

The matching checked-in controller is:

```text
tools/amiga_emulator/beginio_trace.py
```

It begins by releasing the initial pause just long enough for the unchanged
startup `LoadModule` command to register `fujinet-disk.device`, then pauses,
resolves the live vector, installs the breakpoint, and resumes:

```python
# tools/amiga_emulator/beginio_trace.py
ipc.request(socket_path, "DEBUG_CONTINUE")
exec_base, vectors, names = wait_for_device(socket_path, args.device_timeout)
ipc.request(socket_path, "DEBUG_ACTIVATE")
exec_base, vectors, names = device_debug.resolve_device(socket_path)
ipc.request(socket_path, "SET_BREAKPOINT", hex(vectors.begin_io))
ipc.request(socket_path, "DEBUG_CONTINUE")
```

Run that checked-in path, rather than copying a controller into a shell, with:

```sh
AMIGA_E2E_DEBUGGER=1 AMIGA_E2E_BEGINIO_TRACE=1 \
  pytest integration-tests/amiberry/test_diskdevice_adf.py \
  -q --run-amiga -k test_standard_adf
```

Artifacts are written in that run's evidence directory:

```text
beginio-controller.log
beginio-command-stream.log
beginio-timeout.log
device-resolution.log
beginio-0000.log
```

The current checked-in runner also has named hooks for task snapshots, write
buffer capture, read-path capture, and DN2 handler tracing. They follow the
same socket/output-dir contract and must remain opt-in.

Controller rules:

- Accept explicit `--socket` and `--output-dir` arguments.
- Use a fixed total deadline and short per-hit timeout.
- Start with the minimum breakpoints needed for one claim.
- Write evidence before every `DEBUG_CONTINUE`.
- On timeout capture registers, PC disassembly, and stack evidence.
- Restore CPU speed with `SET_CPU_SPEED -1` if changed.
- Clean up in `finally`; never leave a visible paused emulator.
- Never change guest binaries, resident code, guest memory, or startup merely
  to make tracing easier.

##### Complete Controller Example: Bounded BeginIO Capture

The following is a complete, typable host-side controller. Save it outside the
repository, for example as `/tmp/capture_beginio.py`. It resolves the live
`fujinet-disk.device` through Exec, installs one breakpoint on its actual
`BeginIO` vector, records every hit for up to 30 seconds, and always releases
the emulator. It does not require a link map because it breaks on the live
public vector.

```python
#!/usr/bin/env python3
from __future__ import annotations

import argparse
import time
from pathlib import Path

from amiga_emulator import device_debug, ipc
from amiga_emulator.debug_snapshot import parse_registers, read_io_request


def wait_for_pc(socket_path: Path, address: int, timeout: float) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        registers = parse_registers(ipc.request(socket_path, "GET_CPU_REGS"))
        if registers["PC"] == address:
            return
        time.sleep(0.05)
    raise TimeoutError(f"breakpoint {address:#x} was not observed")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--socket", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--seconds", type=float, default=30.0)
    args = parser.parse_args()

    socket_path = Path(args.socket)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    log_path = output_dir / "manual-beginio.log"
    deadline = time.monotonic() + args.seconds

    try:
        # This returns the live, relocated public device vectors.
        _, vectors, _ = device_debug.resolve_device(socket_path)
        ipc.request(socket_path, "DEBUG_ACTIVATE")
        ipc.request(socket_path, "SET_BREAKPOINT", hex(vectors.begin_io))
        ipc.request(socket_path, "DEBUG_CONTINUE")

        with log_path.open("w", encoding="ascii") as log:
            log.write(f"BEGIN_IO {vectors.begin_io:#x}\n")
            index = 0
            while time.monotonic() < deadline:
                try:
                    wait_for_pc(socket_path, vectors.begin_io, 2.0)
                except TimeoutError:
                    continue

                registers = parse_registers(
                    ipc.request(socket_path, "GET_CPU_REGS")
                )
                request = read_io_request(socket_path, registers["A1"])
                offset = request["io_Offset"]
                lba = offset // 512 if offset % 512 == 0 else -1
                log.write(
                    f"index={index} pc={registers['PC']:#x} "
                    f"request={registers['A1']:#x} "
                    f"command={request['io_Command']} "
                    f"flags={request['io_Flags']:#x} "
                    f"error={request['io_Error']:#x} "
                    f"actual={request['io_Actual']} "
                    f"length={request['io_Length']} "
                    f"offset={offset} lba={lba}\n"
                )
                log.flush()
                index += 1
                ipc.request(socket_path, "DEBUG_CONTINUE")
    finally:
        # Never leave a manually launched controller holding the emulator.
        try:
            ipc.request(socket_path, "QUIT")
        except Exception:
            pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

Run it against the socket path created by the exact test run:

```sh
PYTHONPATH="$NIO_WORKSPACE/tools" \
  python /tmp/capture_beginio.py \
  --socket "$(<test-evidence/amiberry-YYYYMMDD-HHMMSS/diskdevice-adf/amiberry.sock.path)" \
  --output-dir test-evidence/manual-beginio \
  --seconds 30
```

For a startup race, do not launch this after the normal guest sequence is
already running. Have the runner pause Amiberry after writing
`amiberry.sock.path` and before opening the serial bridge; start the controller,
then issue its first `DEBUG_CONTINUE`. For a device loaded by `LoadModule`, add
a short polling loop around `device_debug.resolve_device()` before arming the
breakpoint. This is the practical reason controller integration exists.

The existing named controller pattern is intentionally restrictive. A future
safe extension is an allowlisted controller registry with a structured
per-run JSON configuration, for example `AMIGA_E2E_CONTROLLER=beginio-trace`.
Do not add arbitrary shell-command execution through an environment variable.

Controllers do not validate an emulator Sidecar, the serial bridge, or the
NIO protocol. Normal end-to-end tests validate those systems. Controllers
validate a specific live-memory or register claim at a controlled point.

#### CPU Speed, Tasks, DOS, and Media Correlation

Use `GET_CPU_SPEED` and `SET_CPU_SPEED 10` only after a target breakpoint is
armed; slowing boot can prevent the guest reaching `LoadModule` or the test
phase before the controller deadline. Always restore with `SET_CPU_SPEED -1`.

If requests continue but a CLI checkpoint is absent, inspect Exec state using
NDK-derived offsets: `ThisTask`, `TaskReady`, `TaskWait`, task state/signals,
`Process.pr_MsgPort`, `pr_CLI`, `MsgPort` signal fields and queue, and attached
`DosPacket` fields. Two filesystem processes can share a name after remount;
resolve DOS `DeviceNode.dn_Task` through `dos.library` and match it to each
process's embedded message port. Do not infer active handler identity from a
task name alone.

For a disk claim, correlate every layer:

```text
BeginIO request -> LBA -> NIO request -> NIO response -> completion -> ADF
```

Use full packet logging only in a diagnostic trace run when comparing sectors.
Do not claim 512-byte equality from a payload log that truncates the final
bytes. Retain source revisions, environment flags, breakpoint addresses,
relocation evidence, full/truncated observation scope, and cleanup result.
After diagnosis, rerun the original foreground test with no controller,
debugger flag, packet trace, or timeout override.

The Amiga driver link writes a symbol map beside the resident binary:

```text
repos/fujinet-nio-driver/build/amiga/fujinet-disk.device.map
```

Use the map or `m68k-amigaos-nm -n` to obtain link-time symbol offsets. The
resident binary is relocatable, so establish the loaded relocation base from
a known resident entry point or breakpoint/disassembly address before adding
that base to symbol offsets. Do not add resident data or diagnostic commands
to expose the base.

The host-side resolver in `tools/amiga_emulator/device_debug.py` performs this
bootstrap without a guessed breakpoint: it reads the ExecBase pointer at
address 4, walks `ExecBase.DeviceList`, follows each node name, and reads the
six standard device vectors from the matched library base. Its offsets come
from the NDK headers: `LIB_OPEN=-6`, `LIB_CLOSE=-12`, `LIB_EXPUNGE=-18`, the
reserved vector at `-24`, `BeginIO` at `-30`, and `AbortIO` at `-36`. It
validates the relocation delta using `BeginIO`, `Close`, and `AbortIO` before
internal breakpoints are calculated.

At `device_begin_io()`, the live request is in `A1` and the resident base is
in `A6`. Use `READ_MEM` against `A1` to inspect the standard request fields:
command, flags, error, actual, length, offset, and unit. On a timeout, capture
`GET_CPU_REGS`, `DISASSEMBLE` around `PC`, and a small `READ_MEM` window around
`A7` before issuing the normal `QUIT`.

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
