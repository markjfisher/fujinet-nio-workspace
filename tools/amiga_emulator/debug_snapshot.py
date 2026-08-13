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

# m68k NDK v1.3 layout offsets, derived from exec/execbase.h, exec/tasks.h,
# exec/nodes.h, and dos/dosextens.h.  Keep these explicit rather than relying
# on host ABI layout.
EXEC_THIS_TASK = 0x114
EXEC_TASK_READY = 0x196
EXEC_TASK_WAIT = 0x1A4
NODE_SUCC = 0
NODE_TYPE = 8
NODE_NAME = 10
TASK_STATE = 15
TASK_SIG_WAIT = 22
TASK_SIG_RECVD = 26
# Verified with m68k-amigaos-gcc against the installed NDK headers:
# sizeof(struct Task)=92, offsetof(Process, pr_FileSystemTask)=0xa8,
# offsetof(Process, pr_CLI)=0xac.
TASK_SIZE = 92
PROCESS_FILE_SYSTEM_TASK = 0xA8
PROCESS_CLI = 0xAC
PROCESS_MSG_PORT = 0x5C
MSGPORT_FLAGS = 0x0E
MSGPORT_SIGBIT = 0x0F
MSGPORT_SIGTASK = 0x10
MSGPORT_MSGLIST = 0x14
MESSAGE_REPLY_PORT = 0x0E
MESSAGE_LENGTH = 0x12
DOSPACKET_LINK = 0x00
DOSPACKET_PORT = 0x04
DOSPACKET_TYPE = 0x08
DOSPACKET_RES1 = 0x0C
DOSPACKET_RES2 = 0x10
DOSPACKET_ARG1 = 0x14
MESSAGE_SIZE = 20
CLI_COMMAND_NAME = 0x10
CLI_CURRENT_INPUT = 0x20
CLI_COMMAND_FILE = 0x24
CLI_CURRENT_OUTPUT = 0x30
CLI_MODULE = 0x3C
EXEC_LIST_TAIL = 0xFFFFFFFF
TASK_STATES = {
    0: "INVALID", 1: "ADDED", 2: "RUN", 3: "READY", 4: "WAIT",
    5: "EXCEPT", 6: "REMOVED",
}


def read_memory(socket_path: Path, address: int, width: int) -> int:
    response = ipc.request(socket_path, "READ_MEM", hex(address), str(width))
    return int(response.split("\t", 1)[-1].strip(), 0)


def read_io_request(socket_path: Path, request_address: int) -> dict[str, int]:
    return {
        name: read_memory(socket_path, request_address + offset, width)
        for name, (offset, width) in IOREQUEST_FIELDS.items()
    }


def read_c_string(socket_path: Path, address: int, limit: int = 80) -> str:
    if not address:
        return ""
    chars = bytearray()
    for offset in range(limit):
        value = read_memory(socket_path, address + offset, 1)
        if value == 0:
            break
        chars.append(value)
    return chars.decode("ascii", errors="replace")


def read_b_string(socket_path: Path, bptr: int, limit: int = 80) -> str:
    """Read an Amiga BCPL BSTR referenced through a BPTR."""
    if not bptr:
        return ""
    address = bptr << 2
    length = min(read_memory(socket_path, address, 1), limit)
    chars = bytearray(read_memory(socket_path, address + 1 + offset, 1) for offset in range(length))
    return chars.decode("ascii", errors="replace")


def read_task(socket_path: Path, address: int, list_name: str) -> dict[str, int | str]:
    node_type = read_memory(socket_path, address + NODE_TYPE, 1)
    name = read_c_string(socket_path, read_memory(socket_path, address + NODE_NAME, 4))
    state = read_memory(socket_path, address + TASK_STATE, 1)
    task: dict[str, int | str] = {
        "address": address, "list": list_name, "type": node_type, "name": name,
        "state": state, "sig_wait": read_memory(socket_path, address + TASK_SIG_WAIT, 4),
        "sig_recvd": read_memory(socket_path, address + TASK_SIG_RECVD, 4),
    }
    if node_type == 13:  # NT_PROCESS
        task["filesystem_task"] = read_memory(socket_path, address + PROCESS_FILE_SYSTEM_TASK, 4)
        task["cli"] = read_memory(socket_path, address + PROCESS_CLI, 4)
    return task


def walk_task_list(socket_path: Path, list_address: int, list_name: str) -> list[dict[str, int | str]]:
    tasks: list[dict[str, int | str]] = []
    node = read_memory(socket_path, list_address, 4)
    seen: set[int] = set()
    # Exec List.lh_Tail points at the in-place tail sentinel at list+4.
    tail = list_address + 4
    while node not in {0, EXEC_LIST_TAIL, tail} and node not in seen and len(tasks) < 256:
        seen.add(node)
        tasks.append(read_task(socket_path, node, list_name))
        node = read_memory(socket_path, node + NODE_SUCC, 4)
    return tasks


def read_process_port(socket_path: Path, process: int) -> dict[str, int | list[dict[str, int]]]:
    address = process + PROCESS_MSG_PORT
    return {
        "address": address,
        "flags": read_memory(socket_path, address + MSGPORT_FLAGS, 1),
        "sigbit": read_memory(socket_path, address + MSGPORT_SIGBIT, 1),
        "sigtask": read_memory(socket_path, address + MSGPORT_SIGTASK, 4),
        "messages": walk_port_messages(socket_path, address),
    }


def walk_port_messages(socket_path: Path, port: int) -> list[dict[str, int]]:
    messages: list[dict[str, int]] = []
    node = read_memory(socket_path, port + MSGPORT_MSGLIST, 4)
    seen: set[int] = set()
    # MsgPort.mp_MsgList is an Exec List at port+0x14; its tail sentinel is
    # stored in-place at list+4 and must not be decoded as a Message.
    tail = port + MSGPORT_MSGLIST + 4
    while node not in {0, EXEC_LIST_TAIL, tail} and node not in seen and len(messages) < 64:
        seen.add(node)
        packet = node + MESSAGE_SIZE
        messages.append({
            "address": node,
            "reply_port": read_memory(socket_path, node + MESSAGE_REPLY_PORT, 4),
            "length": read_memory(socket_path, node + MESSAGE_LENGTH, 2),
            "packet": packet,
            "packet_link": read_memory(socket_path, packet + DOSPACKET_LINK, 4),
            "packet_port": read_memory(socket_path, packet + DOSPACKET_PORT, 4),
            "packet_type": read_memory(socket_path, packet + DOSPACKET_TYPE, 4),
            "packet_res1": read_memory(socket_path, packet + DOSPACKET_RES1, 4),
            "packet_res2": read_memory(socket_path, packet + DOSPACKET_RES2, 4),
            "packet_arg1": read_memory(socket_path, packet + DOSPACKET_ARG1, 4),
        })
        node = read_memory(socket_path, node + NODE_SUCC, 4)
    return messages


def append_process_port_snapshot(lines: list[str], socket_path: Path,
                                 task: dict[str, int | str]) -> None:
    process = int(task["address"])
    port = read_process_port(socket_path, process)
    cli_bptr = int(task.get("cli", 0))
    command_name = read_b_string(socket_path, read_memory(
        socket_path, (cli_bptr << 2) + CLI_COMMAND_NAME, 4
    )) if cli_bptr else ""
    command_file = read_b_string(socket_path, read_memory(
        socket_path, (cli_bptr << 2) + CLI_COMMAND_FILE, 4
    )) if cli_bptr else ""
    current_input = read_memory(socket_path, (cli_bptr << 2) + CLI_CURRENT_INPUT, 4) if cli_bptr else 0
    current_output = read_memory(socket_path, (cli_bptr << 2) + CLI_CURRENT_OUTPUT, 4) if cli_bptr else 0
    module = read_memory(socket_path, (cli_bptr << 2) + CLI_MODULE, 4) if cli_bptr else 0
    signal_mask = 1 << int(port["sigbit"])
    lines.append(
        f"PROCESS name={task['name']!r} address={process:#x} cli_bptr={cli_bptr:#x} "
        f"command_name={command_name!r} command_file={command_file!r} "
        f"current_input_bptr={current_input:#x} current_output_bptr={current_output:#x} "
        f"module_bptr={module:#x} "
        f"port={int(port['address']):#x} port_flags={int(port['flags']):#x} "
        f"sigbit={int(port['sigbit'])} signal_mask={signal_mask:#x} "
        f"sigtask={int(port['sigtask']):#x} queued={len(port['messages'])}"
    )
    for message in port["messages"]:
        lines.append(
            f"MESSAGE owner={process:#x} address={message['address']:#x} "
            f"reply_port={message['reply_port']:#x} length={message['length']} "
            f"packet={message['packet']:#x} packet_link={message['packet_link']:#x} "
            f"packet_port={message['packet_port']:#x} packet_type={message['packet_type']:#x} "
            f"res1={message['packet_res1']:#x} res2={message['packet_res2']:#x} "
            f"arg1={message['packet_arg1']:#x}"
        )


def capture_task_snapshot(socket_path: Path, destination: Path) -> list[dict[str, int | str]]:
    """Capture live Exec task/process state using NDK-derived offsets."""
    registers_response = ipc.request(socket_path, "GET_CPU_REGS")
    registers = parse_registers(registers_response)
    exec_base = read_memory(socket_path, 4, 4)
    current = read_memory(socket_path, exec_base + EXEC_THIS_TASK, 4)
    tasks = [read_task(socket_path, current, "CURRENT")]
    tasks.extend(walk_task_list(socket_path, exec_base + EXEC_TASK_READY, "READY"))
    tasks.extend(walk_task_list(socket_path, exec_base + EXEC_TASK_WAIT, "WAIT"))
    lines = [
        "GET_CPU_REGS " + registers_response,
        "DISASSEMBLE " + ipc.request(socket_path, "DISASSEMBLE", hex(registers["PC"]), "8"),
        f"EXEC_BASE {exec_base:#x}", f"THIS_TASK {current:#x}",
        "OFFSETS ThisTask=0x114 TaskReady=0x196 TaskWait=0x1a4 "
        "tc_State=0x0f tc_SigWait=0x16 tc_SigRecvd=0x1a "
        "pr_FileSystemTask=0xa8 pr_CLI=0xac",
    ]
    for task in tasks:
        state = TASK_STATES.get(int(task["state"]), str(task["state"]))
        line = (
            f"TASK list={task['list']} address={int(task['address']):#x} "
            f"type={task['type']} name={task['name']!r} state={state} "
            f"sig_wait={int(task['sig_wait']):#x} sig_recvd={int(task['sig_recvd']):#x}"
        )
        if "filesystem_task" in task:
            line += (f" filesystem_task={int(task['filesystem_task']):#x}"
                     f" cli={int(task['cli']):#x}")
        lines.append(line)
    # Decode the shell and every DN2 process independently.  Duplicate DN2
    # names are valid: only the live process/port addresses establish role.
    for task in tasks:
        if task["type"] == 13 and task["name"] in {"Initial CLI", "DN2"}:
            append_process_port_snapshot(lines, socket_path, task)
    destination.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return tasks


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
