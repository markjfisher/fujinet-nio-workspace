"""Capture final AmigaDOS sector buffers at fujinet_disk_write entry."""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

from . import device_debug, ipc
from .debug_snapshot import parse_registers, read_io_request


DEVICE_BEGIN_IO_LINK = 0x110E
WRITE_ENTRY_LINK = 0x05F6
TARGET_LBAS = {880, 881, 882, 883}


def read_bytes(socket_path: Path, address: int, length: int) -> bytes:
    values = bytearray()
    for offset in range(0, length, 4):
        word = int(ipc.request(socket_path, "READ_MEM", hex(address + offset), "4").split("\t", 1)[-1], 0)
        values.extend(word.to_bytes(4, "big"))
    return bytes(values[:length])


def wait_for_device(socket_path: Path, timeout: float):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            return device_debug.resolve_device(socket_path)
        except LookupError:
            time.sleep(0.05)
    raise TimeoutError("fujinet-disk.device was not registered")


def wait_for_pc(socket_path: Path, address: int, timeout: float) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if parse_registers(ipc.request(socket_path, "GET_CPU_REGS")).get("PC") == address:
            return
        time.sleep(0.03)
    raise TimeoutError(f"write breakpoint not observed at {address:#x}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--socket", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--total-timeout", type=float, default=75.0)
    args = parser.parse_args(argv)
    socket_path = Path(args.socket)
    output = Path(args.output_dir)
    log_path = output / "write-buffer-capture.log"
    deadline = time.monotonic() + args.total_timeout
    captures = 0
    try:
        ipc.request(socket_path, "DEBUG_CONTINUE")
        _, vectors, _ = wait_for_device(socket_path, 20.0)
        ipc.request(socket_path, "DEBUG_ACTIVATE")
        delta = vectors.begin_io - DEVICE_BEGIN_IO_LINK
        write_entry = delta + WRITE_ENTRY_LINK
        ipc.request(socket_path, "SET_BREAKPOINT", hex(write_entry))
        log_path.write_text(
            f"ARMED begin_io={vectors.begin_io:#x} write_entry={write_entry:#x} "
            f"deadline_seconds={args.total_timeout}\n", encoding="ascii"
        )
        ipc.request(socket_path, "DEBUG_CONTINUE")
        while time.monotonic() < deadline:
            try:
                wait_for_pc(socket_path, write_entry, min(5.0, deadline - time.monotonic()))
            except TimeoutError:
                break
            registers = parse_registers(ipc.request(socket_path, "GET_CPU_REGS"))
            request_address = device_debug.read_word(socket_path, registers["A5"] - 44, 4)
            request = read_io_request(socket_path, request_address)
            offset = request["io_Offset"]
            lba = offset // 512 if offset % 512 == 0 else -1
            if request["io_Command"] == 3 and request["io_Length"] == 512 and lba in TARGET_LBAS:
                buffer = read_bytes(socket_path, request["io_Data"], 512)
                (output / f"write-buffer-{captures:03d}-lba-{lba}.bin").write_bytes(buffer)
                with log_path.open("a", encoding="ascii") as log:
                    log.write(
                        f"index={captures} lba={lba} request={request_address:#x} "
                        f"data={request['io_Data']:#x} offset={offset} length=512\n"
                    )
                captures += 1
            ipc.request(socket_path, "DEBUG_CONTINUE")
        with log_path.open("a", encoding="ascii") as log:
            log.write(f"STOP captures={captures}\n")
    except Exception as error:
        with log_path.open("a", encoding="ascii") as log:
            log.write(f"ERROR {type(error).__name__}: {error}\n")
        raise
    finally:
        try:
            ipc.request(socket_path, "QUIT")
        except Exception:
            pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
