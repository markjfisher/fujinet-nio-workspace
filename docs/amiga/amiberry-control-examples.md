# Amiberry control examples — driving the guest from the host

Working recipes for controlling an interactive Amiberry Workbench session
from this workspace: launching it, opening a guest shell ("Amiga+E"),
typing into it, running the Bouncy World client (`NIO:bwcn.amiga`), taking
screenshots, and running soaks. Captured because these live in throwaway
`/tmp` scripts that get lost between sessions.

Related reading:

- `[docs/amiga/amiberry-testing.md](amiberry-testing.md)` — the two public paths
(`amiga-workbench`, `amiga-tests`) and environment setup
- `[tools/amiga_emulator/README.md](../../tools/amiga_emulator/README.md)` — harness internals

> **Superseded by the library:** the ad-hoc key tables and chord helpers
> below are now captured as real code in
> `tools/amiga_emulator/keyboard.py` (full USA0 raw-key map, per-character
> modifier resolution, `{name}` tokens, `prekey_amiga()`, `type_text()`).
> Prefer that module for anything new; this document remains as background,
> launch recipes, and the historical record of the tap-vs-hold experiment.



## 1. Launching an interactive session with IPC

```sh
source "$NIO_WORKSPACE/scripts/env.sh"
./scripts/build.sh amiga-workbench --profile wb32-a1200 -- --external-nio --tcp
```

- Requires a FujiNet NIO instance reachable over TCP (port `65504`) for
`--external-nio`.
- The runner waits for Amiberry to log its **Unix IPC socket** and prints
it; typically `/run/user/1000/amiberry.sock`. It also writes the path to
the run dir as `amiberry.sock.path`.
- The development share `NIO:` exposes current build artifacts, including
`bwcn.amiga` (linked from `build/amiga-share`; refresh links there after
rebuilding the client).



## 2. IPC basics (`tools/amiga_emulator/ipc.py`)

```python
import sys
sys.path.insert(0, "/path/to/fujinet-nio-workspace/tools")
from amiga_emulator import ipc

sock = "/run/user/1000/amiberry.sock"
ipc.request(sock, "GET_STATUS")                       # liveness check
ipc.request(sock, "SEND_KEY", "68", "1")              # key down (rawkey 68 = Return)
ipc.request(sock, "SEND_KEY", "68", "0")              # key up
ipc.request(sock, "SCREENSHOT", "/tmp/kilo/shot.png") # grab the frame
```

There is also a CLI form: `python -m amiga_emulator.ipc [--socket PATH] COMMAND ...`
(useful one-liners: `GET_STATUS`). Debugger commands (`DEBUG_ACTIVATE`,
`PAUSE`, `GET_CPU_REGS`, memory reads) exist for crash hunts — see
`run.py` usage of them.

**Key timing matters:** ~30 ms between down/up pairs is usually fine;
150 ms is safer when the guest is busy or a window just opened. Always
sleep briefly before a screenshot (~1 s) so the guest catches up.

## 3. Rawkey codes used repeatedly

From the proven drive scripts (`/tmp/kilo/drive_bwcn.py`,
`drive_full.py`):


| Key        | Code |     | Key         | Code |
| ---------- | ---- | --- | ----------- | ---- |
| Return     | 68   |     | Space       | 64   |
| Left Shift | 96   |     | Right Amiga | 103  |
| `;`        | 41   |     | `.`         | 56   |


Letters (Amiga rawkey, decimal) — values marked ✓ appear verbatim in the
proven drive scripts; the rest follow the same keyboard layout:

```
q=16 w=17✓ e=18✓ r=19 t=20 y=21 u=22 i=23✓ o=24✓ p=25
a=32✓ s=33✓ d=34 f=35 g=36✓ h=37✓ j=38 k=39✓ l=40✓
z=49 x=50 c=51✓ v=52 b=53✓ n=54✓ m=55✓
digits: 1..9,0 = 1..9,10
```

### Modifier chords: hold, tap, release

Modifiers must be **held** across the tapped key — down, tap, up. The
guest's input.device derives the rawkey qualifier from the modifiers held
when the key-down event is processed, so a released modifier contributes
nothing.

```python
def send(code, state, delay=0.03):                     # low-level
    ipc.request(sock, "SEND_KEY", str(code), state); time.sleep(delay)

def key(code, delay=0.03):                             # plain tap
    send(code, "1", delay); send(code, "0", delay)

def chord(mods, code, delay=0.03):                     # hold mods, tap code
    for m in mods:
        send(m, "1", delay)
    key(code, delay)
    for m in reversed(mods):
        send(m, "0", delay)

def colon():   chord([96], 41)     # ':'  = Shift + ';'
def upper(ch): chord([96], RAWKEY[ch])                 # capital letters

def amiga_e(): chord([103], 18)    # Amiga+E -> Workbench Execute dialog
```

`drive_full.py` uses this correct pattern (its `down`/`up`/`colon`
helpers) — this is what drove the successful client sessions, colons
included. `drive_bwcn.py` once shipped a sloppy variant —
`key(96); key(41); key(96)` tapping shift *released* before `;` — which
has since been fixed to the chord pattern.

> **Verified live (Amiberry IPC, 2026-08-26):** in a focused shell,
> tap-method produced `;`, hold-method produced `:`. Amiberry has no
> qualifier quirk — modifiers must be held for the chord to register.
> The tap variant would therefore type `192.168.1.101;9003`.

Never copy the tap pattern. If punctuation or chords ever seem to drop,
lengthen the delays and verify typed text in a screenshot before
trusting it.

## 4. The canonical client-launch sequence

This is the exact flow used to get from bare Workbench to the Bouncy
World loop:

```python
# wait for Workbench to settle after boot
deadline = time.time() + 60
while time.time() < deadline:
    try:
        ipc.request(sock, "GET_STATUS"); break
    except Exception:
        time.sleep(2)
time.sleep(5)

# open the Execute dialog: right-Amiga + E  ("Amiga+E")
amiga_e()
time.sleep(1.0)

# start a fresh shell from the Execute dialog
text("newshell"); key(68); time.sleep(2.0)

# launch the client from NIO: share
text("nio:bwcn.amiga"); key(68); time.sleep(3.0)

# fill the connect screen: s = edit server URL, n = edit name
key(K["s"]); text("192.168.1.101:9003"); key(68)
key(K["n"]); text("ami");                key(68)

# space through shapes preview into the main loop
key(64)   # preview
key(64)   # main loop begins
```

(`text()` here uses `chord([96], 41)` for `:` and plain taps for
unshifted characters — see the chord helper above.)

Full runnable versions are preserved in `docs/amiga/amiberry-control-examples.d/` (`drive_bwcn.py`, `drive_full.py`, `pty_drive.py`; stage flags:
`all | menu | url | name | run`). Both drive scripts now use the chord
pattern; copy whichever fits.

### Gotchas learned the hard way

- **Amiga+E only opens the Execute dialog when Workbench has focus.**
With a shell/console window focused it does nothing — this caused
"misaligned starting" once (typed text landing in the wrong place).
If a stale shell exists, close it or click Workbench first before
sending the combo.
- Always send **down then up** as separate `SEND_KEY`s; a stuck modifier
  (e.g. Amiga held) changes what every later keystroke does.
- Type slowly into freshly opened windows; give each Return a beat before
  typing the next command.
- **Workbench requesters close via their underscored button key.**
  `{escape}` only defocusses an input box. To open and cleanly close the
  Execute dialog: `{amiga+e}{delay:1.5}{escape}c` — the final `c`
  invokes the underscored **C**ancel button.
- **Per-event delay ≠ focus delay.** `--delay` paces keystrokes but does
  not wait for a new window; at `--delay 0.01` the first character after
  `{ramiga+e}` is swallowed. Keep the global delay small and insert
  `{delay:0.3}` after focus-changing chords:
  `'{ramiga+e}{delay:0.3}Hello{escape}{delay:1.0}c'`.
- If letters start vanishing (invisible input, dead shortcuts), a
  modifier is stuck from a dropped release — `Keyboard.release_all()`
  in the library sends key-up for every modifier as recovery.
- The library module `tools/amiga_emulator/keyboard.py` accepts explicit
  multi-modifier chords (`{ctrl+shift+a}`, `{lshift+alt+amiga+x}`) even
  where a shortcut exists.



## 5. Soak / evidence pattern

Soaks ran as tracked background sessions that boot, drive, screenshot
periodically, then tear down:

```
background_process start:
  bash -c '... launch amiberry ... python drive_bwcn.py --socket ... ;
           sleep 240 ; SCREENSHOT final.png'
then read /tmp/kilo/*.png at intervals to inspect frames
```

Conventions used throughout the debugging sessions: screenshots named
`NN-description.png` under `/tmp/kilo/` (e.g. `01-execute.png`,
`07-loop.png`), read with the image-capable Read tool.

## 6. Host-side reference client under a pty

For diffing Amiga behaviour against a controllable target, the linux
client runs under a Python pty with scripted keystrokes and full output
capture (`FN_PORT=/tmp/fujinet-nio-pty ./build/bwcn.linux`; server URL
and name prefilled via appstore settings, space/space into the loop,
`q` to quit). Script pattern: `/tmp/kilo/pty_drive.py` —

```python
master, slave = pty.openpty()
env = dict(os.environ, FN_PORT="/tmp/fujinet-nio-pty", TERM="vt100")
pid = os.fork()
if pid == 0:
    os.setsid(); os.dup2(slave, 0); os.dup2(slave, 1); os.dup2(slave, 2)
    os.execve(CLIENT, [CLIENT], env)
# parent: select() on master, os.write(master, b" ") to send keys,
# capture everything to a log for analysis
```

The FujiNet instance itself runs at
`repos/fujinet-nio/build/fujibus-pty-debug/run-fujinet-nio`
(config: `fujinet-data/fujinet.yaml`, PTY path `/tmp/fujinet-nio-pty`).
Script preserved at `docs/amiberry-control-examples.d/pty_drive.py`.

## 7. Quick checklist: fresh demo/debug run end-to-end

1. Start FujiNet NIO (TCP channel enabled).
2. `./scripts/build.sh amiga-workbench --profile wb32-a1200 -- --external-nio --tcp`
3. Note the printed IPC socket path.
4. Wait for Workbench (`GET_STATUS` loop + sleep).
5. Amiga+E → `newshell` ⏎ → `nio:bwcn.amiga` ⏎.
6. `s` → server URL ⏎, `n` → name ⏎, space ⏎ space.
7. Screenshot periodically; `q` quits cleanly back through the shell.

