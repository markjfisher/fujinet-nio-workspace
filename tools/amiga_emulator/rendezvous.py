"""Reusable host-side primitives for deterministic Amiberry diagnostics."""

from __future__ import annotations

import json
import time
from pathlib import Path

from . import device_debug, ipc
from .debug_snapshot import read_memory


def checkpoint_path(run_dir: Path, namespace: str, key: str) -> Path:
    return (run_dir / "fujinet-data" / "FujiNet" / "app-store" / "v1" /
            namespace / f"{key}.bin")


def wait_for_checkpoint(run_dir: Path, namespace: str, key: str,
                        timeout: float) -> Path:
    path = checkpoint_path(run_dir, namespace, key)
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if path.is_file():
            return path
        time.sleep(0.05)
    raise TimeoutError(f"checkpoint was not published: {namespace}/{key}")


def release_guest(run_dir: Path, namespace: str, key: str,
                  value: bytes = b"go") -> Path:
    path = checkpoint_path(run_dir, namespace, key)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(value)
    return path


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
