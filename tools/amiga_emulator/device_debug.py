"""Live Exec/device resolution through Amiberry IPC memory reads."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from . import ipc


# Values mirror the installed NDK headers:
# exec/nodes.h: ln_Succ=0, ln_Name=10
# exec/libraries.h: LIB_OPEN=-6, LIB_CLOSE=-12, LIB_EXPUNGE=-18,
#                   LIB_RESERVED=-24, LIB_VECTSIZE=6
NODE_SUCC = 0
NODE_NAME = 10
LIB_OPEN = -6
LIB_CLOSE = -12
LIB_EXPUNGE = -18
LIB_RESERVED = -24
DEV_BEGIN_IO = -30
DEV_ABORT_IO = -36

# ExecBase has LibNode followed by the static/dynamic fields and system lists.
# This is generated from exec/execbase.h layout for the m68k NDK ABI.
EXEC_DEVICE_LIST = 350
AMIGA_ADDRESS_MAX = 0x00FFFFFF
EXEC_LIST_TAIL = 0xFFFFFFFF


def plausible_address(value: int, alignment: int = 2) -> bool:
    return (value != 0 and value <= AMIGA_ADDRESS_MAX and
            value % alignment == 0)


@dataclass(frozen=True)
class DeviceVectors:
    base: int
    open: int
    close: int
    expunge: int
    reserved: int
    begin_io: int
    abort_io: int


def _value(response: str) -> int:
    """Parse the numeric result from an OK response."""
    token = response.split("\t", 1)[-1].strip()
    return int(token, 0)


def read_word(socket_path: Path, address: int, width: int) -> int:
    return _value(ipc.request(socket_path, "READ_MEM", hex(address), str(width)))


def read_vector(socket_path: Path, base: int, offset: int) -> int:
    """Decode an Amiga six-byte JMP absolute-long library vector."""
    opcode = read_word(socket_path, base + offset, 2)
    if opcode != 0x4EF9:
        raise ValueError(f"unexpected vector opcode {opcode:#x} at {base + offset:#x}")
    return read_word(socket_path, base + offset + 2, 4)


def read_c_string(socket_path: Path, address: int, limit: int = 64) -> str:
    if not plausible_address(address, 1):
        raise ValueError(f"implausible string pointer {address:#x}")
    data = bytearray()
    for offset in range(limit):
        value = read_word(socket_path, address + offset, 1)
        if value == 0:
            break
        data.append(value)
    return data.decode("ascii", errors="replace")


def resolve_device(socket_path: Path, name: str = "fujinet-disk.device",
                   max_nodes: int = 256) -> tuple[int, DeviceVectors, list[str]]:
    """Walk Exec's live device list and resolve one device's vectors."""
    exec_base = read_word(socket_path, 4, 4)
    if not plausible_address(exec_base, 2):
        raise ValueError(f"implausible ExecBase pointer {exec_base:#x}")
    head = read_word(socket_path, exec_base + EXEC_DEVICE_LIST, 4)
    if head and not plausible_address(head, 2):
        raise ValueError(f"implausible device-list head {head:#x}")
    seen: set[int] = set()
    names: list[str] = []
    node = head
    for _ in range(max_nodes):
        if node == 0 or node in seen:
            break
        if not plausible_address(node, 2):
            raise ValueError(f"implausible device-list node {node:#x}")
        seen.add(node)
        name_ptr = read_word(socket_path, node + NODE_NAME, 4)
        if name_ptr and not plausible_address(name_ptr, 1):
            raise ValueError(f"implausible ln_Name pointer {name_ptr:#x}")
        node_name = read_c_string(socket_path, name_ptr) if name_ptr else ""
        names.append(node_name)
        if node_name == name:
            vectors = DeviceVectors(
                base=node,
                open=read_vector(socket_path, node, LIB_OPEN),
                close=read_vector(socket_path, node, LIB_CLOSE),
                expunge=read_vector(socket_path, node, LIB_EXPUNGE),
                reserved=read_vector(socket_path, node, LIB_RESERVED),
                begin_io=read_vector(socket_path, node, DEV_BEGIN_IO),
                abort_io=read_vector(socket_path, node, DEV_ABORT_IO),
            )
            return exec_base, vectors, names
        node = read_word(socket_path, node + NODE_SUCC, 4)
        if node == EXEC_LIST_TAIL:
            break
        if node and not plausible_address(node, 2):
            raise ValueError(f"implausible successor pointer {node:#x}")
    raise LookupError(f"device {name!r} not found; walked {names!r}")


def write_resolution_log(socket_path: Path, destination: Path,
                         link_offsets: dict[str, int]) -> DeviceVectors:
    """Resolve and persist the live vectors and validated relocation delta."""
    exec_base, vectors, names = resolve_device(socket_path)
    deltas = {
        key: value - link_offsets[key]
        for key, value in {
            "begin_io": vectors.begin_io,
            "close": vectors.close,
            "abort_io": vectors.abort_io,
        }.items()
    }
    if len(set(deltas.values())) != 1:
        raise RuntimeError(f"vector relocation mismatch: {deltas}")
    lines = [
        f"EXEC_BASE {exec_base:#x}",
        f"DEVICE_LIST_OFFSET {EXEC_DEVICE_LIST}",
        f"DEVICES {' | '.join(names)}",
        f"DEVICE_BASE {vectors.base:#x}",
        f"VECTOR_OPEN {vectors.open:#x}",
        f"VECTOR_CLOSE {vectors.close:#x}",
        f"VECTOR_EXPUNGE {vectors.expunge:#x}",
        f"VECTOR_RESERVED {vectors.reserved:#x}",
        f"VECTOR_BEGIN_IO {vectors.begin_io:#x}",
        f"VECTOR_ABORT_IO {vectors.abort_io:#x}",
        f"RELOCATION_DELTAS {deltas}",
    ]
    destination.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return vectors
