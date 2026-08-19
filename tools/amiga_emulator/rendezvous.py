"""Reusable host-side primitives for deterministic Amiberry diagnostics."""

from __future__ import annotations

import json
import shutil
import subprocess
import time
from pathlib import Path

from . import device_debug, ipc
from .debug_snapshot import read_memory


def _xdf_command() -> list[str]:
    if shutil.which("xdftool"):
        return ["xdftool"]
    if shutil.which("uvx"):
        return ["uvx", "--from", "amitools", "xdftool"]
    raise FileNotFoundError("xdftool or uvx is required for guest checkpoints")


def wait_for_hdf_checkpoint(image: Path, guest_path: str, timeout: float) -> None:
    """Wait for a local-DH0 marker without sending FujiNet traffic."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        result = subprocess.run(
            [*_xdf_command(), str(image), "read", guest_path, "/dev/null"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False,
        )
        if result.returncode == 0:
            return
        time.sleep(0.05)
    raise TimeoutError(f"guest checkpoint was not published: {guest_path}")


def log_event(transcript: Path, event: str, **fields: object) -> None:
    record = {"event": event, **fields}
    with transcript.open("a", encoding="utf-8") as out:
        out.write(json.dumps(record) + "\n")


def release_guest(socket_path: Path, transcript: Path) -> None:
    """Submit Return to the local AmigaDOS Ask gate through Amiberry IPC."""
    request(socket_path, transcript, "SEND_KEY", "68", "1")
    request(socket_path, transcript, "SEND_KEY", "68", "0")


def pause_guest(socket_path: Path, transcript: Path) -> str:
    return request(socket_path, transcript, "PAUSE")


def resume_guest(socket_path: Path, transcript: Path) -> str:
    return request(socket_path, transcript, "RESUME")


def request(socket_path: Path, transcript: Path, command: str, *args: str) -> str:
    response = ipc.request(socket_path, command, *args)
    with transcript.open("a", encoding="utf-8") as out:
        out.write(json.dumps({"command": command, "args": args,
                              "response": response}) + "\n")
    return response


def resolve_device(socket_path: Path, transcript: Path, name: str) -> device_debug.DeviceVectors:
    _, vectors, names = device_debug.resolve_device(socket_path, name)
    with transcript.open("a", encoding="utf-8") as out:
        out.write(json.dumps({"device": name, "devices": names,
                              "base": hex(vectors.base),
                              "begin_io": hex(vectors.begin_io)}) + "\n")
    return vectors


def arm_breakpoint(socket_path: Path, transcript: Path, address: int) -> None:
    request(socket_path, transcript, "SET_BREAKPOINT", hex(address))


def capture_raw(socket_path: Path, transcript: Path, address: int,
                size: int = 56) -> dict[str, object]:
    registers = request(socket_path, transcript, "GET_CPU_REGS")
    raw = bytes(read_memory(socket_path, address + offset, 1)
                for offset in range(size))
    record: dict[str, object] = {"address": hex(address), "size": size,
                                 "raw": raw.hex(), "registers": registers}
    with transcript.open("a", encoding="utf-8") as out:
        out.write(json.dumps(record) + "\n")
    return record
