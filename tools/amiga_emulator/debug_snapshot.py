"""Host-side Amiberry debugger snapshot helpers."""

from __future__ import annotations

from pathlib import Path
import re

from . import ipc


IOREQUEST_FIELDS = {
    "io_Unit": (24, 4),
    "io_Command": (28, 2),
    "io_Flags": (30, 1),
    "io_Error": (31, 1),
    "io_Actual": (32, 4),
    "io_Length": (36, 4),
    "io_Offset": (44, 4),
}


def read_memory(socket_path: Path, address: int, width: int) -> int:
    response = ipc.request(socket_path, "READ_MEM", hex(address), str(width))
    return int(response.split("\t", 1)[-1].strip(), 0)


def read_io_request(socket_path: Path, request_address: int) -> dict[str, int]:
    return {
        name: read_memory(socket_path, request_address + offset, width)
        for name, (offset, width) in IOREQUEST_FIELDS.items()
    }


def wait_for_breakpoint(socket_path: Path, timeout: float = 60.0) -> str:
    """Require running-then-paused, avoiding the controller's initial pause."""
    import time

    deadline = time.monotonic() + timeout
    observed_running = False
    last_status = ""
    while time.monotonic() < deadline:
        last_status = ipc.request(socket_path, "DEBUG_STATUS")
        paused = "Paused=true" in last_status
        if not paused:
            observed_running = True
        elif observed_running:
            return last_status
        time.sleep(0.1)
    raise TimeoutError(f"breakpoint stop not observed; last status: {last_status}")


def parse_registers(response: str) -> dict[str, int]:
    values: dict[str, int] = {}
    for field in response.split("\t"):
        if "=" not in field:
            continue
        name, value = field.split("=", 1)
        values[name.upper()] = int(value, 16)
    return values


def next_instruction_address(disassembly: str) -> tuple[int, int]:
    """Return the first instruction address and decoded byte length."""
    for line in disassembly.splitlines():
        match = re.search(r"\b([0-9a-fA-F]{8})\s+([0-9a-fA-F]{4,})\s{2,}", line)
        if match:
            address = int(match.group(1), 16)
            byte_length = len(match.group(2)) // 2
            return address, byte_length
    raise ValueError(f"cannot parse disassembly response: {disassembly!r}")


def capture_breakpoint(socket_path: Path, destination: Path) -> dict[str, int]:
    registers_response = ipc.request(socket_path, "GET_CPU_REGS")
    registers = parse_registers(registers_response)
    pc = registers["PC"]
    a1 = registers["A1"]
    lines = [
        "GET_CPU_REGS " + registers_response,
        "DISASSEMBLE " + ipc.request(socket_path, "DISASSEMBLE", hex(pc), "8"),
        f"PC {pc:#x}",
        f"A1 {a1:#x}",
        f"A6 {registers['A6']:#x}",
    ]
    fields = {
        "io_Command": (28, 2),
        "io_Flags": (30, 1),
        "io_Error": (31, 1),
        "io_Unit": (24, 4),
        "io_Actual": (32, 4),
        "io_Length": (36, 4),
        # Standard IORequest layout: io_Data is at 40 and io_Offset follows it.
        "io_Offset": (44, 4),
    }
    for name, (offset, width) in fields.items():
        response = ipc.request(socket_path, "READ_MEM", hex(a1 + offset), str(width))
        lines.append(f"{name} {response}")
    destination.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return registers
