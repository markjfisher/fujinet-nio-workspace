"""Correlate target DiskDevice reads with BeginIO completion state."""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

from . import device_debug, ipc
from .debug_snapshot import parse_registers, read_io_request


DEVICE_BEGIN_IO_LINK = 0x150A
COMPLETION_LINK = 0x17A0
def wait_for_device(socket_path: Path, timeout: float):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            return device_debug.resolve_device(socket_path)
        except (LookupError, ValueError, OSError, RuntimeError):
            time.sleep(0.05)
    raise TimeoutError("fujinet-disk.device was not registered")


def wait_for_pc(socket_path: Path, addresses: set[int], timeout: float) -> int:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        pc = parse_registers(ipc.request(socket_path, "GET_CPU_REGS")).get("PC")
        if pc in addresses:
            return pc
        time.sleep(0.03)
    raise TimeoutError("target read breakpoint not observed")


def request_at_completion(socket_path: Path, registers: dict[str, int]) -> int:
    del socket_path
    # The current build retains the active IORequest directly in A5 through
    # the common completion block.
    return registers["A5"]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--socket", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--total-timeout", type=float, default=75.0)
    args = parser.parse_args(argv)
    socket_path = Path(args.socket)
    output = Path(args.output_dir)
    log_path = output / "read-path-capture.log"
    deadline = time.monotonic() + args.total_timeout
    targets: dict[int, int] = {}
    try:
        ipc.request(socket_path, "DEBUG_CONTINUE")
        _, vectors, _ = wait_for_device(socket_path, 20.0)
        ipc.request(socket_path, "DEBUG_ACTIVATE")
        delta = vectors.begin_io - DEVICE_BEGIN_IO_LINK
        completion = delta + COMPLETION_LINK
        if device_debug.read_word(socket_path, completion, 2) != 0x082D:
            raise RuntimeError(f"completion opcode mismatch at {completion:#x}")
        ipc.request(socket_path, "SET_BREAKPOINT", hex(vectors.begin_io))
        ipc.request(socket_path, "SET_BREAKPOINT", hex(completion), "1")
        log_path.write_text(
            f"BEGIN_IO {vectors.begin_io:#x}\nCOMPLETION {completion:#x}\n", encoding="ascii"
        )
        ipc.request(socket_path, "DEBUG_CONTINUE")
        while time.monotonic() < deadline:
            try:
                pc = wait_for_pc(socket_path, {vectors.begin_io, completion}, min(5.0, deadline - time.monotonic()))
            except TimeoutError:
                break
            registers = parse_registers(ipc.request(socket_path, "GET_CPU_REGS"))
            if pc == vectors.begin_io:
                request_address = registers["A1"]
            else:
                request_address = request_at_completion(socket_path, registers)
            request = read_io_request(socket_path, request_address)
            lba = request["io_Offset"] // 512 if request["io_Offset"] % 512 == 0 else -1
            event = "begin" if pc == vectors.begin_io else "completion"
            with log_path.open("a", encoding="ascii") as log:
                log.write(
                    f"event={event} request={request_address:#x} "
                    f"command={request['io_Command']} lba={lba} "
                    f"length={request['io_Length']} actual={request['io_Actual']} "
                    f"error={request['io_Error']:#x} flags={request['io_Flags']:#x}\n"
                )
            ipc.request(socket_path, "DEBUG_CONTINUE")
    finally:
        try:
            ipc.request(socket_path, "QUIT")
        except Exception:
            pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
