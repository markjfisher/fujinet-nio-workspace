#!/usr/bin/env python3
"""Drive the linux Bouncy World client under a pty and capture output."""
import os
import pty
import select
import sys
import time

CLIENT = "/home/markf/dev/nio/fujinet-nio-workspace/repos/bounce-world-client-nio/build/bwcn.linux"
OUT = "/tmp/kilo/linux-client.log"

master, slave = pty.openpty()
env = dict(os.environ, FN_PORT="/tmp/fujinet-nio-pty", TERM="vt100")
pid = os.fork()
if pid == 0:
    os.setsid()
    os.dup2(slave, 0)
    os.dup2(slave, 1)
    os.dup2(slave, 2)
    os.close(master)
    os.close(slave)
    os.chdir(os.path.dirname(CLIENT))
    os.execve(CLIENT, [CLIENT], env)
os.close(slave)

log = open(OUT, "wb")
start = time.time()


def send(data: bytes) -> None:
    os.write(master, data)


def pump(duration: float) -> None:
    end = time.time() + duration
    while time.time() < end:
        r, _, _ = select.select([master], [], [], 0.2)
        if r:
            try:
                data = os.read(master, 4096)
            except OSError:
                return
            if not data:
                return
            log.write(data)
            log.flush()


# startup + get_info (fields prefilled from appstore)
pump(6)
send(b" ")          # leave get_info
pump(4)
send(b" ")          # leave shapes preview
pump(90)            # soak in the main loop

send(b"q")          # clean quit
pump(3)
try:
    os.kill(pid, 9)
except ProcessLookupError:
    pass
log.close()
print("done")
