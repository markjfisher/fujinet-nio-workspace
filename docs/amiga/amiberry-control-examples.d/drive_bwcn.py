#!/usr/bin/env python3
"""Drive the Bouncy World Amiga client through Amiberry IPC.

Modifiers are held as chords (down, tap, up) — see
docs/amiga/amiberry-control-examples.md for why the older tap-tap-tap
variant in this file's history was verified broken (it typed ';').
"""
from __future__ import annotations

import argparse
import time
from pathlib import Path

import sys
sys.path.insert(0, "/home/markf/dev/nio/fujinet-nio-workspace/tools")
from amiga_emulator import ipc  # noqa: E402

# Amiga rawkey codes (decimal)
RAMIGA = 103
LSHIFT = 96
RETURN = 68
SPACE = 64

# letters
K = {"a": 32, "b": 53, "c": 51, "e": 18, "g": 36, "h": 37, "i": 23,
     "k": 39, "l": 40, "m": 55, "n": 54, "o": 24, "s": 33, "w": 17,
     ".": 56, "9": 9, "1": 1, "6": 6, "8": 8, "0": 10, "3": 3, ";": 41,
     "2": 2, "4": 4, "5": 5, "7": 7}


def send(sock, code: int, state: str, delay: float = 0.03) -> None:
    ipc.request(sock, "SEND_KEY", str(code), state)
    time.sleep(delay)


def key(sock, code: int, delay: float = 0.03) -> None:
    send(sock, code, "1", delay)
    send(sock, code, "0", delay)


def chord(sock, mods, code: int, delay: float = 0.03) -> None:
    """Hold every modifier in mods while tapping code."""
    for m in mods:
        send(sock, m, "1", delay)
    key(sock, code, delay)
    for m in reversed(mods):
        send(sock, m, "0", delay)


def type_text(sock, text: str) -> None:
    for ch in text:
        if ch == ":":
            chord(sock, [LSHIFT], K[";"])
        elif ch.isupper():
            chord(sock, [LSHIFT], K[ch.lower()])
        else:
            key(sock, K[ch.lower()])


def amiga_e(sock) -> None:
    """Right-Amiga + E opens the Workbench Execute dialog."""
    chord(sock, [RAMIGA], K["e"])


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--socket", required=True)
    p.add_argument("--shots", default="/tmp/kilo")
    p.add_argument("--stage", default="all",
                   choices=["all", "menu", "url", "name", "run"])
    args = p.parse_args()

    sock = Path(args.socket)
    shots = Path(args.shots)
    shots.mkdir(parents=True, exist_ok=True)

    def shot(name: str) -> None:
        time.sleep(1.0)
        ipc.request(sock, "SCREENSHOT", str(shots / name))
        time.sleep(0.5)

    if args.stage == "all":
        amiga_e(sock)
        shot("01-execute.png")

    if args.stage in ("all", "menu"):
        type_text(sock, "newshell")
        key(sock, RETURN)
        shot("02-shell.png")

    if args.stage in ("all", "url"):
        type_text(sock, "nio:bwcn.amiga")
        key(sock, RETURN)
        shot("03-getinfo.png")

    if args.stage in ("all", "url", "name"):
        key(sock, K["s"])           # edit server URL
        type_text(sock, "192.168.1.101:9003")
        key(sock, RETURN)
        shot("04-url.png")
        key(sock, K["n"])           # edit name
        type_text(sock, "ami")
        key(sock, RETURN)
        shot("05-name.png")

    if args.stage in ("all", "run"):
        key(sock, SPACE)            # proceed to shapes preview
        shot("06-preview.png")
        key(sock, SPACE)            # proceed to main loop
        time.sleep(5)
        shot("07-loop.png")
        time.sleep(5)
        shot("08-loop-later.png")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
