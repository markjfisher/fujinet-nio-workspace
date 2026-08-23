# AmigaOS testing with Amiberry

Use Amiberry with FujiNet through **two public paths**:

| Path | Command | Purpose |
| --- | --- | --- |
| Interactive | `amiga-workbench` | Persistent Workbench session; poke FujiNet commands by hand |
| Automated | `amiga-tests` | Disposable guest HDFs, assertions, and retained evidence |

Amiberry supplies the guest machine and emulated `serial.device`. A POSIX
FujiNet NIO instance is the device/network service. The guest HDF/VHD is local
emulator storage; mounting FujiNet disk media (`DNx:`) is a separate feature
covered by the automated suite.

Lower-level targets (`amiga-e2e`, `amiga-run`, `amiga-test-disk`,
`run-amiberry-nio`) still exist as implementation details. Prefer the two
paths above unless you are changing the harness itself.

## Quick start

### Prerequisites

Install `amiberry`, `socat`, `nc`, and the `m68k-amigaos` toolchain.

Configure licensed AmigaOS paths in `local/amiga.env` (copy from
`local/amiga.env.example`). Build an OS environment once:

```sh
scripts/amiga-env build wb32 --machine a1200-030
```

See [`docs/amiga/environment-setup.md`](environment-setup.md) for full environment and profile setup.

### Interactive Workbench (try FujiNet by hand)

Three image roles matter:

```text
BASE HDF        pristine/reproducible (from scripts/amiga-env)
TEST HDF        disposable copy of BASE; tests inject exact artifacts
RUN/WORKBENCH   persistent developer-owned machine (not modified by the launcher)
development share (e.g. NIO:)
                host directory mounted into the guest with current build artifacts
```

1. Start FujiNet NIO yourself on TCP port `65504` (your usual config is fine;
   the TCP channel must be enabled).
2. Point a workbench profile at a **persistent** VHD/HDF in
   `configs/amiga/workbenches.yaml` (the `harddrive` field).
3. Boot Amiberry:

```sh
./scripts/build.sh amiga-workbench --profile wb32-a1200 -- --external-nio
./scripts/build.sh amiga-workbench --profile wb31-a1200 -- --external-nio
```

Amiberry opens visibly. Open `System/Shell` and run commands such as
`fhost`, `fls`, `wifitest`, `fmount`.

Default WB3.x profiles attach a read-only development share `NIO:` that exposes
current driver and app binaries from `build/amiga-share` (refreshed with
symlinks at launch; the persistent Workbench image is never written). Use it
to install or run fresh builds explicitly:

```text
Copy NIO:fujinet-nio.device DEVS:
Copy NIO:fujinet-disk.device DEVS:
Copy NIO:fujinet-load-resident C:
NIO:FLS ...
```

Profiles declare an `environment` (e.g. `wb32`) and `machine` (e.g.
`a1200-030`). Kickstart and machine settings come from the built environment;
`harddrive` is your own image, separate from test base HDFs.

Other useful profile options:

```sh
./scripts/build.sh amiga-workbench --profile wb1.3 -- --external-nio
```

```sh
AMIGA_WORKBENCH_CONFIG_FILE="$HOME/path/to/workbenches.yaml" \
AMIGA_WORKBENCH_CONFIG=my-profile \
./scripts/build.sh amiga-workbench -- --external-nio
```

Amiberry runner options go after `--` (for example `--external-nio`). See
`./scripts/build.sh --explain amiga-workbench`.

#### Getting current build artifacts into Workbench

Interactive Workbench images are deliberately not rewritten on every launch.
Mount the workspace's Amiga build-output directory as a host-directory volume
in Amiberry (for example `NIO:`).

You can then either run CLI utilities directly from that volume during
development, or copy the versions you want into `C:` / `DEVS:`.

Automated tests are different: they copy a pristine base HDF and inject the
exact binaries required by each case, so every test starts from a controlled
image.

### Automated tests (prove behaviour)

Build Amiga artefacts and run the guest suite:

```sh
./scripts/build.sh amiga-tests --amiga-env wb32 --amiga-machine a1200-030
```

When binaries are already built:

```sh
scripts/amiga-tests --amiga-env wb32 --amiga-machine a1200-030
scripts/amiga-tests --amiga-env wb32 --amiga-machine a1200-030 -k wifi -v
scripts/amiga-tests --amiga-env wb31 --amiga-machine a1200-030 -k cli -v
```

Focused pytest (same harness):

```sh
source scripts/env.sh && \
  uv run pytest --run-amiga --amiga-env wb32 --amiga-machine a1200-030 -q --tb=no \
  integration-tests/amiberry/test_diskdevice_adf.py::test_hd_adf_mount_geometry_dir_and_type
```

Agents and BMAD Build: follow `docs/agent-test-policy.md` — prefer a targeted
`-k` / single node; do not default to the full suite.

Each run writes evidence under `test-evidence/amiberry-YYYYMMDD-HHMMSS/`.
Adding cases: `integration-tests/amiberry/README.md`, registry
`integration-tests/amiberry/tests.toml`, startups under
`integration-tests/amiberry/startup/`.

### Optional: ADF media for `fmount`

This does not start Amiberry. It builds floppy images for TNFS / DiskDevice
mount tests:

```sh
AMIGA_TEST_APP=sizetest \
  ./scripts/build.sh amiga-test-adf --label SIZETEST

AMIGA_TEST_APP=sizetest \
  ./scripts/build.sh amiga-test-adf --blank --label SIZETEST
```

Output: `build/images/amiga-sizetest.adf`. Blank images are non-bootable
media for `fmount`, not disks to boot directly.

### What these paths validate

Interactive workbench sessions exercise the live broker and CLI tools against
your NIO. Automated cases cover Wi-Fi config/scan, stateful CLI, and DiskDevice
mount behaviour. Guest Amiga code uses `fujinet-nio-lib`; the resident
`fujinet-nio.device` broker owns `serial.device`; POSIX `fujinet-nio` owns
device services.

---

## Reference: harness, profiles, and diagnostics

The sections below are for maintainers and agents extending the suite (IPC,
completion markers, debugger controllers). For day-to-day use, stay with the
quick start above.

### Workbench profiles

Named profiles live in `configs/amiga/workbenches.yaml`. Default:
`wb32-a1200`.

Each profile can specify `harddrive` or `disk`, `kickstart`, and an Amiberry
`settings` mapping such as `cpu_type`, `chipmem_size`, and `fastmem_size`.
These map to `-s` key/value pairs (UAE names).

Named **development shares** are defined at the top level and opted into per
profile. They become Amiberry `filesystem2=` host-directory mounts (same form
as a GUI-saved UAE file), not injections into the persistent HDF:

```yaml
shares:
  NIO:
    volume: NIO           # Amiga volume label → NIO:
    path: ${NIO_WORKSPACE}/build/amiga-share
    writable: false       # default → filesystem2=ro,…
    sync: true            # refresh host dir with build artifact symlinks at launch
    # device: DH1         # optional; auto DH1+ so DH0 stays free for the boot HDF
    # bootpri: 0          # optional Amiga boot priority

# Emitted as e.g.: -s filesystem2=ro,DH1:NIO:/…/build/amiga-share,0
# (GUI UAE files also write uaehfN=dir,…; the launcher uses filesystem2= only.)

profiles:
  wb32-a1200:
    environment: wb32
    machine: a1200-030
    harddrive: ${NIO_WORKSPACE}/images/amigaos3.2-run.vhd
    shares:
      - NIO
```

Profiles that declare `environment` + `machine` derive kickstart (and
optionally base HDF) from a built `scripts/amiga-env` manifest; `harddrive`
may point at a personal persistent VHD/HDF:

```yaml
  wb31-a1200:
    environment: wb31
    machine: a1200-030
    harddrive: ${NIO_WORKSPACE}/images/amigaos3.1-run.hdf
```

Profiles without `environment` (such as `wb1.3`) specify `disk`, `kickstart`,
and `settings` directly; set the matching variables in `local/amiga.env`. An
optional `uae_config` loads a UAE config before profile `-s` overrides.
Profiles that omit `shares` behave exactly as before.

Driver auto-loading uses the redistributable loader from
`fujinet-nio-driver`. The loader is validated on Workbench 3.1; full `DNx:`
filesystem access is not yet validated there (`TD_REMOVE` vs Workbench 3.2
`TD_ADDCHANGEINT`).

The runner defaults SDL3 to `SDL_VIDEO_DRIVER=kmsdrm,wayland,x11`, respecting
either SDL video-driver variable if already set (`SDL_VIDEODRIVER` remains the
compatibility spelling).

### Integration suite

The suite under `integration-tests/amiberry/` starts a fresh POSIX FujiNet NIO
and Amiberry for each case, copies the pre-built base HDF, injects the test
payload, extracts guest result files, and asserts their contents.

Early cases cover Wi-Fi SET/GET/status/scan via `fujinet-nio-lib` and stateful
CLI behaviour across processes (`FHOST`, `FLS`, `FAPP`).

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

The integration suite owns its emulated machine configuration in the
top-level `[amiberry]` table of `integration-tests/amiberry/tests.toml`.
`args` contains native Amiberry command-line arguments, while `settings`
contains ordered UAE `key=value` overrides. The checked-in test machine uses
maximum emulation speed and a 68030 with a 68882 FPU. These values are applied
only by the pytest harness; interactive `amiga-workbench` profiles and their
UAE configuration files are unaffected. For example:

```toml
[amiberry]
args = ["-w", "-1"]
settings = [
  "cpu_type=68020/68881",
  "cpu_model=68030",
  "fpu_model=68882",
  "cpu_compatible=true",
]
```

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

#### Disk-media acceptance evidence

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

### Amiberry IPC

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

#### Debugger IPC

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
continue. If the startup loader registers the resident later, allow the guest to run
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
startup loader command to register `fujinet-disk.device`, then pauses,
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
then issue its first `DEBUG_CONTINUE`. For a device loaded during startup, add
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
armed; slowing boot can prevent the guest reaching the resident loader or the test
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


### Internal / legacy run targets

These remain available but are not the recommended friend-facing interface:

| Target | Role |
| --- | --- |
| `amiga-e2e` | Build a disposable test HDF and boot one app (historical one-shot smoke) |
| `amiga-run` | Forward an already-configured disk to `run-amiberry-nio` |
| `amiga-test-disk` | Build-only HDF helper used by e2e and tests |
| `scripts/run-amiberry-nio` | Shared Amiberry + serial-bridge runner |

Hard-drive boots need `AMIBERRY_KICKSTART`. `AMIBERRY_FAST_FILE_SYSTEM` is
resolved automatically from a built `amiga-env` manifest, `AMIGA_ENV_ID`, or
`AMIGA_WB32_EXPANDED` when unset. Runner options for the shared script are
documented by `scripts/run-amiberry-nio --help` / `./scripts/build.sh --explain amiga-workbench`.

The default TCP serial path uses `serial_direct=true` and a `socat` bridge to
the `fujibus-tcp-debug` NIO profile. Without `serial_direct`, Amiberry can drop
bytes from binary FujiBus frames. Experimental `--pty` mode exists but current
Amiberry builds do not treat `/dev/pts/*` as a serial device.

### Architecture notes (what the guest validates)

`wifitest` exercises `fn_init()` and the Wi-Fi status/configuration/scan wire
operations. `fhost` exercises the host-device protocol. The generated NIO
configuration uses the simulated Wi-Fi backend, so the Wi-Fi test can verify
decoded status, configuration, and scan records without requiring host Wi-Fi.

CLI Amiga tools still register `fn_transport_close` at process exit so each
process closes its broker context. Physical `serial.device` stays with the
resident `fujinet-nio.device` broker, which must be LoadResident before any
`fn_transport_init`. If the broker is absent, init returns `FN_ERR_NOT_FOUND`
instead of contending for serial.

This keeps the architecture split clean: Amiga code uses the platform
transport in `fujinet-nio-lib`, Amiberry supplies the guest serial device, and
POSIX `fujinet-nio` owns the device services. Future FujiNet disk-image support
can be added independently; it is not required to boot or test these apps.
