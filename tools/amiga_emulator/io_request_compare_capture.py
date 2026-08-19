"""Capture two complete block-device requests from one AmigaDOS handler."""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

from . import device_debug, ipc
from .debug_snapshot import EXEC_THIS_TASK, parse_registers, read_memory, resolve_dos_device_task


IOEXTTD_SIZE = 56
REPLY_MSG_LVO = 378


def exec_vector(socket_path: Path, exec_base: int, lvo: int) -> int:
    vector = exec_base - lvo
    if read_memory(socket_path, vector, 2) == 0x4EF9:
        return read_memory(socket_path, vector + 2, 4)
    return vector


def raw_request(socket_path: Path, address: int) -> bytes:
    return bytes(read_memory(socket_path, address + offset, 1)
                 for offset in range(IOEXTTD_SIZE))


def be(raw: bytes, offset: int, width: int) -> int:
    return int.from_bytes(raw[offset:offset + width], "big")


def record(log, event: str, sequence: int, handler: int, request: int,
           raw: bytes) -> None:
    log.write(
        f"event={event} sequence={sequence} handler={handler:#x} request={request:#x} "
        f"node_type={raw[8]:#x} node_succ={be(raw, 0, 4):#x} "
        f"node_pred={be(raw, 4, 4):#x} reply_port={be(raw, 14, 4):#x} "
        f"message_length={be(raw, 18, 2)} device={be(raw, 20, 4):#x} "
        f"unit={be(raw, 24, 4):#x} command={be(raw, 28, 2):#x} "
        f"flags={raw[30]:#x} error={raw[31]:#x} actual={be(raw, 32, 4)} "
        f"length={be(raw, 36, 4)} data={be(raw, 40, 4):#x} "
        f"offset={be(raw, 44, 4):#x} iotd_count={be(raw, 48, 4):#x} "
        f"iotd_seclabel={be(raw, 52, 4):#x}\n"
    )
    log.write(f"raw={raw.hex()}\n")
    log.flush()


def wait_for_pc(socket_path: Path, addresses: set[int], deadline: float) -> int:
    while time.monotonic() < deadline:
        registers = parse_registers(ipc.request(socket_path, "GET_CPU_REGS"))
        if registers.get("PC") in addresses:
            return registers["PC"]
        time.sleep(0.03)
    raise TimeoutError("request comparison breakpoint was not observed")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--socket", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--device", required=True)
    parser.add_argument("--dos-device", required=True)
    parser.add_argument("--total-timeout", type=float, default=90.0)
    args = parser.parse_args(argv)
    socket_path = Path(args.socket)
    output = Path(args.output_dir)
    deadline = time.monotonic() + args.total_timeout
    log_path = output / "io-request-compare.log"
    selected: list[int] = []
    awaiting: dict[int, int] = {}
    try:
        ipc.request(socket_path, "DEBUG_CONTINUE")
        log_path.write_text("starting\n", encoding="ascii")
        while True:
            try:
                exec_base, vectors, _ = device_debug.resolve_device(socket_path, args.device)
                break
            except (LookupError, ValueError, OSError, RuntimeError):
                if time.monotonic() >= deadline:
                    raise TimeoutError("target device or DOS handler was not available")
                time.sleep(0.05)
        reply_msg = exec_vector(socket_path, exec_base, REPLY_MSG_LVO)
        with log_path.open("w", encoding="ascii") as log:
            log.write(f"device={args.device} dos_device={args.dos_device} "
                      f"begin_io={vectors.begin_io:#x} reply_msg={reply_msg:#x} "
                      f"size={IOEXTTD_SIZE}\n")
            ipc.request(socket_path, "DEBUG_ACTIVATE")
            ipc.request(socket_path, "SET_BREAKPOINT", hex(vectors.begin_io))
            ipc.request(socket_path, "SET_BREAKPOINT", hex(reply_msg), "1")
            ipc.request(socket_path, "DEBUG_CONTINUE")
            while len(selected) < 2 and time.monotonic() < deadline:
                pc = wait_for_pc(socket_path, {vectors.begin_io, reply_msg}, deadline)
                registers = parse_registers(ipc.request(socket_path, "GET_CPU_REGS"))
                if pc == vectors.begin_io:
                    this_task = read_memory(socket_path, exec_base + EXEC_THIS_TASK, 4)
                    request = registers["A1"]
                    raw = raw_request(socket_path, request)
                    # Capture non-quick handler-issued data requests only.
                    try:
                        handler = resolve_dos_device_task(socket_path, args.dos_device) - 0x5C
                    except LookupError:
                        handler = 0
                    if (this_task == handler and
                            be(raw, 28, 2) in {2, 3, 0x8002, 0x8003} and
                            (raw[30] & 1) == 0):
                        sequence = len(selected)
                        selected.append(request)
                        awaiting[request] = sequence
                        record(log, "entry", sequence, this_task, request, raw)
                else:
                    request = registers["A1"]
                    if request in awaiting:
                        record(log, "pre_reply", awaiting.pop(request), 0, request,
                               raw_request(socket_path, request))
                ipc.request(socket_path, "DEBUG_CONTINUE")
    except Exception as error:
        log_path.write_text(f"ERROR {type(error).__name__}: {error}\n", encoding="ascii")
        raise
    finally:
        try:
            ipc.request(socket_path, "QUIT")
        except Exception:
            pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
