"""Bounded host-side trace of fujinet-disk.device BeginIO requests."""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

from . import device_debug, ipc
from .debug_snapshot import capture_breakpoint, parse_registers, read_io_request


def wait_for_device(socket_path: Path, timeout: float) -> tuple[int, device_debug.DeviceVectors, list[str]]:
    """Wait for the unchanged LoadModule command to register the device."""
    deadline = time.monotonic() + timeout
    last_error: Exception | None = None
    while time.monotonic() < deadline:
        try:
            return device_debug.resolve_device(socket_path)
        except LookupError as error:
            last_error = error
        time.sleep(0.05)
    raise TimeoutError(f"fujinet-disk.device was not registered: {last_error}")


def wait_for_begin_io(socket_path: Path, address: int, timeout: float) -> None:
    """Wait only for the resolved entry PC, not debugger status wording."""
    deadline = time.monotonic() + timeout
    last_pc: int | None = None
    while time.monotonic() < deadline:
        registers = parse_registers(ipc.request(socket_path, "GET_CPU_REGS"))
        last_pc = registers.get("PC")
        if last_pc == address:
            return
        time.sleep(0.05)
    raise TimeoutError(
        f"BeginIO breakpoint not observed at {address:#x}; last PC was {last_pc:#x}"
        if last_pc is not None else "BeginIO breakpoint not observed"
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--socket", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--limit", type=int, default=140)
    parser.add_argument("--total-timeout", type=float, default=45.0)
    parser.add_argument("--hit-timeout", type=float, default=5.0)
    parser.add_argument("--device-timeout", type=float, default=20.0)
    args = parser.parse_args(argv)

    socket_path = Path(args.socket)
    output = Path(args.output_dir)
    trace_path = output / "beginio-command-stream.log"
    timeout_path = output / "beginio-timeout.log"
    deadline = time.monotonic() + args.total_timeout
    hits = 0

    try:
        with trace_path.open("w", encoding="utf-8") as trace:
            # The runner paused Amiberry before opening the serial bridge.
            # Allow the unchanged startup through LoadModule at normal speed.
            # Slowing first made even its early third command miss the short
            # registration budget.
            ipc.request(socket_path, "DEBUG_CONTINUE")
            exec_base, vectors, names = wait_for_device(socket_path, args.device_timeout)
            # Freeze before resolving again and arming the sole breakpoint.
            ipc.request(socket_path, "DEBUG_ACTIVATE")
            exec_base, vectors, names = device_debug.resolve_device(socket_path)
            ipc.request(socket_path, "SET_BREAKPOINT", hex(vectors.begin_io))
            ipc.request(socket_path, "SET_CPU_SPEED", "10")
            trace.write(
                f"EXEC_BASE {exec_base:#x}\nDEVICE_BASE {vectors.base:#x}\n"
                f"BEGIN_IO {vectors.begin_io:#x}\nDEVICES {names}\n"
            )
            trace.flush()
            (output / "beginio-trace-armed").write_text("\n", encoding="ascii")
            ipc.request(socket_path, "DEBUG_CONTINUE")
            while hits < args.limit and time.monotonic() < deadline:
                try:
                    wait_for_begin_io(
                        socket_path,
                        vectors.begin_io,
                        timeout=min(args.hit_timeout, deadline - time.monotonic()),
                    )
                except TimeoutError:
                    capture_breakpoint(socket_path, timeout_path)
                    trace.write(f"TIMEOUT index={hits}\n")
                    break
                registers = capture_breakpoint(socket_path, output / f"beginio-{hits:04d}.log")
                request = read_io_request(socket_path, registers["A1"])
                offset = request["io_Offset"]
                fields = [
                    f"index={hits}", f"pc={registers['PC']:#x}",
                    f"a1={registers['A1']:#x}", f"unit={request['io_Unit']}",
                    f"command={request['io_Command']}", f"flags={request['io_Flags']:#x}",
                    f"error={request['io_Error']:#x}", f"actual={request['io_Actual']}",
                    f"length={request['io_Length']}", f"offset={offset}",
                ]
                if offset % 512 == 0:
                    fields.append(f"lba={offset // 512}")
                trace.write(" ".join(fields) + "\n")
                trace.flush()
                hits += 1
                ipc.request(socket_path, "DEBUG_CONTINUE")
            else:
                trace.write(f"LIMIT_OR_DEADLINE index={hits}\n")
    finally:
        try:
            ipc.request(socket_path, "SET_CPU_SPEED", "-1")
        except Exception:
            pass
        try:
            ipc.request(socket_path, "QUIT")
        except Exception:
            pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
