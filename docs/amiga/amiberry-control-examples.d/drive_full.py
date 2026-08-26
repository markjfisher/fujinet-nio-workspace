#!/usr/bin/env python3
"""Drive the Bouncy World Amiga client end-to-end via Amiberry IPC."""
from __future__ import annotations

import sys
import time

sys.path.insert(0, "/home/markf/dev/nio/fujinet-nio-workspace/tools")
from amiga_emulator import ipc  # noqa: E402

sock = "/run/user/1000/amiberry.sock"
K = {"a": 32, "b": 53, "c": 51, "e": 18, "g": 36, "h": 37, "i": 23, "k": 39,
     "l": 40, "m": 55, "n": 54, "o": 24, "s": 33, "w": 17, ".": 57, "9": 9,
     "1": 1, "6": 6, "8": 8, "0": 10, "3": 3, ";": 41, "2": 2}


def down(code):
    ipc.request(sock, "SEND_KEY", str(code), "1")
    time.sleep(0.15)


def up(code):
    ipc.request(sock, "SEND_KEY", str(code), "0")
    time.sleep(0.15)


def key(code):
    down(code)
    up(code)


def colon():
    down(96)
    key(41)
    up(96)


def text(t):
    for ch in t:
        colon() if ch == ":" else key(K[ch])


def shot(name, wait=1.5):
    time.sleep(wait)
    ipc.request(sock, "SCREENSHOT", f"/tmp/kilo/{name}")
    time.sleep(0.3)


def main() -> int:
    # wait for Workbench
    deadline = time.time() + 60
    while time.time() < deadline:
        try:
            ipc.request(sock, "GET_STATUS")
            break
        except Exception:
            time.sleep(2)
    time.sleep(5)

    # open Execute dialog (right-amiga + e) and start a shell
    down(103)
    key(18)
    up(103)
    shot("50-execute.png", 1.0)
    text("newshell")
    key(68)
    shot("51-shell.png", 2.0)
    time.sleep(1.0)

    # launch the client
    text("nio:bwcn.amiga")
    shot("52-typed.png", 0.8)
    key(68)
    shot("53-getinfo.png", 3)

    # fill fields
    key(K["s"])
    text("192.168.1.101:9003")
    key(68)
    key(K["n"])
    text("ami")
    key(68)
    shot("54-fields.png")

    # into the loop
    key(64)
    shot("55-preview.png", 2.5)
    key(64)
    time.sleep(5)
    shot("56-loop.png", 0)
    time.sleep(10)
    shot("57-loop-later.png", 0)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
