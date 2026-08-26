# `amiga_emulator`

Host-side utilities for running and diagnosing AmigaOS guest tests in
Amiberry. The module starts Amiberry and the FujiBus bridge, talks to
Amiberry's Unix IPC socket, resolves live Exec objects, and writes diagnostic
evidence into an individual test run directory.

The normal test path does not use a debugger controller. Controllers are
opt-in diagnostics: they can pause or slow the emulator and must not be used
as routine regression evidence.

## Keyboard control (`amiga_emulator.keyboard`)

Full raw-key model (AmigaOS Keymap Library USA0 mapping) plus typing helpers
over the IPC `SEND_KEY` command. Every character knows its own key and
modifier chord, so callers never hand-roll shift handling:

```python
from amiga_emulator.keyboard import Keyboard

kb = Keyboard()                        # finds the live IPC socket
kb.prekey_amiga("e")                   # Amiga+E -> Workbench Execute dialog
kb.type_text("newshell{return}")
kb.type_text("nio:bwcn.amiga{return}") # ':' gets its Shift automatically
kb.screenshot("/tmp/kilo/shot.png")
```

- Modifiers are held as chords (down, tap, up); releasing first yields the
  unmodified key — verified live: tap-method `;`, hold-method `:`.
- Special keys in text use `{name}` tokens: `{return}`, `{esc}`, `{space}`,
  `{f1}`... Names: see `BY_NAME` (`lshift`, `rshift`, `capslock`, `ctrl`,
  `lalt`, `ralt`, `lamiga`, `ramiga`, arrows, `help`, `backspace`,
  `delete`, ...).
- Modifier chords use `{mod+key}` tokens — modifiers held across the tap,
  any number of them, explicit even where a shortcut exists
  (`{ctrl+shift+a}`): `./scripts/amiberry-type '{ramiga+e}'` opens the
  Workbench Execute dialog. Modifier aliases: `shift`→lshift,
  `alt`→lalt, `amiga`→lamiga; the key part is any key name or single
  character (`{shift+;}`).
  Verified live: `{ramiga+e}` opens Execute, `{escape}` closes it.
- Workbench requesters close via their underscored button key, not
  Escape alone: `{escape}` only defocusses the input box. To open and
  cleanly close the Execute dialog:
  `./scripts/amiberry-type '{amiga+e}{delay:1.5}{escape}c'`
  (`c` invokes the underscored **C**ancel button).
- `{delay:seconds}` pauses before the next keystroke — use it after
  `{return}` while the guest is busy, or its early keystrokes are
  swallowed: `kb.type_text('dir NIO:{return}{delay:2.5}echo "done"{return}')`.
  Range (0, 60] seconds; verified live against a Workbench shell.
- `\` and `|` have no US-keyboard mapping and raise `UnknownKeyError`.
- **Two different delays matter.** The per-event `--delay`/`delay` paces
  individual keystrokes; it does not wait for window focus. Opening a
  requester (e.g. `{ramiga+e}`) is a focus change, and at low per-event
  delays its first keystroke gets swallowed. Keep `--delay` small for
  fast typing and pay only where focus changes (verified live:
  `--delay 0.01` loses the `H` below, `0.03` does not):

  ```sh
  # fast: small per-event delay, targeted pause after the chord
  ./scripts/amiberry-type --delay 0.01 '{ramiga+e}{delay:0.3}Hello{escape}{delay:1.0}c'
  # simple: one delay covers everything, but slower overall
  ./scripts/amiberry-type --delay 0.03 '{ramiga+e}Hello{escape}{delay:1.0}c'
  ```
- If keystrokes mysteriously vanish (letters invisible, shortcuts dead),
  a modifier is probably stuck from a dropped chord release:
  `kb.release_all()` sends key-up for every modifier as recovery.

Shell users can invoke the same typing through the wrapper script:

```sh
./scripts/amiberry-type 'dir NIO:{return}{delay:2.5}echo "Dir Completed!"{return}'
./scripts/amiberry-type --socket /run/user/1000/amiberry.sock --screenshot /tmp/shot.png 'hello'
```

## Prerequisites

Source the workspace environment before building Amiga code or invoking the
module directly:

```sh
source "$NIO_WORKSPACE/scripts/env.sh"
export PYTHONPATH="$NIO_WORKSPACE/tools"
```

Amiberry must be built with IPC socket support. A test run writes its exact
socket path to:

```text
test-evidence/amiberry-YYYYMMDD-HHMMSS/<case>/amiberry.sock.path
```

Use that path rather than guessing a shared `/tmp/amiberry.sock` endpoint.

## Normal Use

Run the focused writable DiskDevice baseline without debugger perturbation:

```sh
pytest integration-tests/amiberry/test_diskdevice_adf.py \
  -q --run-amiga -k test_standard_adf
```

Run the standard-tool mount/eject case:

```sh
pytest integration-tests/amiberry/test_diskdevice_fmount.py -q --run-amiga
```

The test harness imports `run.py`, which:

1. starts POSIX `fujinet-nio` and Amiberry;
2. waits for the Amiberry IPC socket reported by that exact process;
3. writes `amiberry.sock.path` in the evidence directory;
4. opens the TCP-to-TCP `socat` serial bridge; and
5. retains logs, screenshots, HDF images, and result files in the evidence
   directory.

## Module Map

| File | Purpose |
| --- | --- |
| `run.py` | Amiberry/NIO/serial bridge runner used by integration tests. |
| `disk.py` | Reusable HDF assembly, archive extraction, and Amiga tree installation helpers. |
| `ipc.py` | Small client for the Amiberry Unix IPC text protocol. |
| `device_debug.py` | Resolves a loaded Exec device and its live vectors. |
| `debug_snapshot.py` | Decodes registers, IORequests, timeout snapshots, Exec/DOS objects. |
| `beginio_trace.py` | Bounded Copy/write/flush completion trace for `fujinet-disk.device`. |
| `read_path_capture.py` | Bounded `CMD_READ` entry/completion trace for target LBAs. |
| `write_buffer_capture.py` | Captures live write buffers at `fujinet_disk_write()` entry. |
| `task_snapshot.py` | Captures current/ready/wait Exec task and process state. |
| `dn2_handler_trace.py` | Tracks DN2 processes and DOS DeviceNode handler selection. |
| `disk_read_compare.py` | Compares full NIO read responses with backing ADF sectors. |
| `disk_write_compare.py` | Compares logged NIO write payloads with backing ADF sectors. |

## IPC Client

Invoke the IPC client directly with an explicit socket:

```sh
python -m amiga_emulator.ipc \
  --socket "$(<test-evidence/amiberry-YYYYMMDD-HHMMSS/diskdevice-adf/amiberry.sock.path)" \
  GET_CPU_REGS
```

Useful commands:

```sh
python -m amiga_emulator.ipc --socket "$SOCKET" GET_STATUS
python -m amiga_emulator.ipc --socket "$SOCKET" GET_CPU_REGS
python -m amiga_emulator.ipc --socket "$SOCKET" DISASSEMBLE 0xc3111e 8
python -m amiga_emulator.ipc --socket "$SOCKET" READ_MEM 0x00c00000 4
python -m amiga_emulator.ipc --socket "$SOCKET" SCREENSHOT /tmp/amiberry.png
```

Debugger commands pause normal guest execution:

```sh
python -m amiga_emulator.ipc --socket "$SOCKET" DEBUG_ACTIVATE
python -m amiga_emulator.ipc --socket "$SOCKET" SET_BREAKPOINT 0xc3111e
python -m amiga_emulator.ipc --socket "$SOCKET" DEBUG_CONTINUE
```

Always issue `DEBUG_CONTINUE` after a manual breakpoint hit, or `QUIT` when
ending the diagnostic run.

## Resolve A Live Resident Device

`device_debug.py` does not rely on a fixed resident base. It reads the ExecBase
pointer from address `4`, walks `ExecBase.DeviceList`, finds
`fujinet-disk.device`, and decodes its public library vectors.

```python
from pathlib import Path
from amiga_emulator import device_debug

socket = Path("/run/user/1000/amiberry.sock")
exec_base, vectors, names = device_debug.resolve_device(socket)
print(hex(exec_base), hex(vectors.begin_io), names)
```

For internal symbols, use the driver map and prove relocation with all three
known vectors:

```python
from pathlib import Path
from amiga_emulator import device_debug

link_offsets = {
    "begin_io": 0x110e,
    "close": 0x10c0,
    "abort_io": 0x10f0,
}
device_debug.write_resolution_log(
    Path("/run/user/1000/amiberry.sock"),
    Path("/tmp/device-resolution.log"),
    link_offsets,
)
```

Do not set a breakpoint at a link-time map address. Resident code is relocated.

## Decode an IORequest

At `device_begin_io()`, `A1` is the request pointer. Use
`debug_snapshot.read_io_request()` after stopping at the live `BeginIO` vector:

```python
from pathlib import Path
from amiga_emulator import debug_snapshot, ipc

socket = Path("/run/user/1000/amiberry.sock")
registers = debug_snapshot.parse_registers(ipc.request(socket, "GET_CPU_REGS"))
request = debug_snapshot.read_io_request(socket, registers["A1"])
print(request)
print("LBA", request["io_Offset"] // 512)
```

The m68k `IORequest` fields used by the module are:

```text
io_Unit    +24   io_Command +28   io_Flags +30   io_Error +31
io_Actual  +32   io_Length  +36   io_Data  +40    io_Offset +44
```

`io_Offset` is `+44`, not `+40`.

## Controllers

Controllers are checked-in Python programs that write diagnostics into the
current run directory. They are enabled only by explicit environment flags in
`run.py`. The runner writes `amiberry.sock.path`, optionally pauses Amiberry
with `DEBUG_ACTIVATE`, starts the selected controller, then opens the serial
bridge. This avoids missing startup-sensitive breakpoints.

### BeginIO/Copy Completion Trace

```sh
AMIGA_E2E_DEBUGGER=1 AMIGA_E2E_BEGINIO_TRACE=1 \
  pytest integration-tests/amiberry/test_diskdevice_adf.py \
  -q --run-amiga -k test_standard_adf
```

`beginio_trace.py` waits for `LoadModule` to register the device, resolves the
live vector, traces the Copy write sequence, and can follow write/flush/reply
boundaries. Typical artifacts are:

```text
beginio-controller.log
beginio-command-stream.log
beginio-timeout.log
device-resolution.log
```

### Task/Process Timeout Snapshot

```sh
AMIGA_E2E_DEBUGGER=1 AMIGA_E2E_TASK_SNAPSHOT=1 \
  pytest integration-tests/amiberry/test_diskdevice_adf.py \
  -q --run-amiga -k test_standard_adf
```

This writes `task-timeout-snapshot.log`, including current/ready/wait tasks,
process ports, CLI fields, and selected DOS message queues. Guest layouts are
explicit m68k NDK offsets; do not use host ABI layouts to interpret this file.

### Read and Write Capture

```sh
AMIGA_E2E_DEBUGGER=1 AMIGA_E2E_READ_PATH_CAPTURE=1 \
  pytest integration-tests/amiberry/test_diskdevice_adf.py \
  -q --run-amiga -k test_standard_adf

AMIGA_E2E_DEBUGGER=1 AMIGA_E2E_WRITE_BUFFER_CAPTURE=1 \
  pytest integration-tests/amiberry/test_diskdevice_adf.py \
  -q --run-amiga -k test_standard_adf
```

`read_path_capture.py` records `CMD_READ` entry/completion for LBAs 880-883.
`write_buffer_capture.py` reads the exact 512-byte guest buffer at write-helper
entry for those LBAs. These are diagnostic runs; rerun normally before accepting
a production conclusion.

### DN2 Handler Identity

```sh
AMIGA_E2E_DEBUGGER=1 AMIGA_E2E_DN2_HANDLER_TRACE=1 \
  pytest integration-tests/amiberry/test_diskdevice_adf.py \
  -q --run-amiga -k test_standard_adf
```

`dn2_handler_trace.py` records live DN2 processes and their embedded ports. It
also resolves the DOS `DN2:` DeviceNode through `dos.library` so the active
handler is identified by `dn_Task`, not by an ambiguous process name.

## Compare NIO Traffic With Backing Media

For a full read-response comparison, rebuild the POSIX debug service with the
diagnostic full-payload log switch enabled:

```sh
source "$NIO_WORKSPACE/scripts/env.sh"
cmake --build --preset fujibus-tcp-debug-build \
  --directory repos/fujinet-nio

FUJINET_FULL_PACKET_LOG=1 \
  pytest integration-tests/amiberry/test_diskdevice_adf.py \
  -q --run-amiga -k test_standard_adf
```

Then compare the run's NIO log with its ADF:

```sh
python -m amiga_emulator.disk_read_compare \
  --log test-evidence/amiberry-YYYYMMDD-HHMMSS/diskdevice-adf/fujinet-nio.log \
  --adf test-evidence/amiberry-YYYYMMDD-HHMMSS/diskdevice-adf/fujinet-data/writable.adf
```

Use `disk_write_compare` similarly for write payloads. Historical normal NIO
logs retain only a sector prefix for writes; do not claim full 512-byte equality
from a truncated log.

## Inspect and Modify ADF/HDF Images

The harness uses `xdftool` from `amitools` through `uvx`:

```sh
# List an ADF/HDF filesystem
uvx --from amitools xdftool writable.adf list

# Read a guest file from an image
uvx --from amitools xdftool writable.adf read PERSIST.TXT /tmp/PERSIST.TXT

# Write a host file into an image
uvx --from amitools xdftool writable.adf write /tmp/PERSIST.TXT PERSIST.TXT

# Create and format an OFS image
uvx --from amitools xdftool new output.adf format OFS
```

## Safety Rules

- Use the normal controller-free test as the pass/fail baseline.
- Preserve the full evidence directory before changing a hypothesis.
- Use NDK-derived offsets and live vector resolution; never guess addresses.
- Keep controller timeouts bounded and always restore altered CPU speed.
- On a timeout, record registers, disassembly, stack, and screenshot before
  quitting.
- Do not modify resident code, guest startup, or guest memory solely to make a
  diagnostic easier.
