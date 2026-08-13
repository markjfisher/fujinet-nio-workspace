"""Bounded host-side trace of fujinet-disk.device BeginIO requests."""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

from . import device_debug, ipc
from .debug_snapshot import capture_breakpoint, parse_registers, read_io_request


# These link-time offsets are verified below against the loaded instructions.
# device_begin_io is static, so it is anchored by its live device vector.
DEVICE_BEGIN_IO_LINK = 0x110E
FUJINET_DISK_WRITE_LINK = 0x05F6
WRITE_RETURN_LINK = 0x22E6
REPLY_MSG_LINK = 0x13F8
UPDATE_ENTRY_LINK = 0x159C
FLUSH_ENTRY_LINK = 0x0450
FLUSH_RETURN_LINK = 0x15A8
COMPLETION_LINK = 0x13E4
ADD_EXISTING_LINK = 0x1810
ADD_ALLOC_LINK = 0x1B72
ADD_REQUEST_STORE_LINK = 0x1B8C
ADD_TAIL_LINK = 0x1BA4
ADD_CLEAR_QUICK_LINK = 0x1840
COPY_WRITE_LBAS = (880, 882, 882, 883, 880, 882)


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


def wait_for_breakpoint_addresses(socket_path: Path, addresses: set[int], timeout: float) -> int:
    deadline = time.monotonic() + timeout
    last_pc: int | None = None
    while time.monotonic() < deadline:
        registers = parse_registers(ipc.request(socket_path, "GET_CPU_REGS"))
        last_pc = registers.get("PC")
        if last_pc in addresses:
            return last_pc
        time.sleep(0.05)
    raise TimeoutError(
        f"breakpoint not observed; last PC was {last_pc:#x}"
        if last_pc is not None else "breakpoint not observed"
    )


def request_record(registers: dict[str, int], request: dict[str, int], event: str,
                   result: int | None = None) -> str:
    offset = request["io_Offset"]
    fields = [
        f"event={event}", f"pc={registers['PC']:#x}",
        f"a1={registers['A1']:#x}", f"a3={registers.get('A3', 0):#x}",
        f"request={request['address']:#x}", f"command={request['io_Command']}",
        f"flags={request['io_Flags']:#x}", f"error={request['io_Error']:#x}",
        f"actual={request['io_Actual']}", f"length={request['io_Length']}",
        f"offset={offset}",
    ]
    if result is not None:
        fields.append(f"d0={result:#x}")
    if offset % 512 == 0:
        fields.append(f"lba={offset // 512}")
    return " ".join(fields)


def read_request(socket_path: Path, address: int) -> dict[str, int]:
    request = read_io_request(socket_path, address)
    request["address"] = address
    return request


def current_request_address(socket_path: Path, registers: dict[str, int], pc: int,
                            write_entry: int, write_return: int, reply_msg: int) -> int:
    if pc == reply_msg:
        # The common completion block has just loaded A1 for ReplyMsg().
        return registers["A1"]
    if pc in {write_entry, write_return}:
        # device_begin_io keeps the active IORequest in its A5 frame at -44.
        # A3 is the fujinet_disk_driver argument at the write call.
        return device_debug.read_word(socket_path, registers["A5"] - 44, 4)
    return registers["A1"]


def active_request_address(socket_path: Path, registers: dict[str, int]) -> int:
    """Get the processing-loop request retained in device_begin_io's frame."""
    return device_debug.read_word(socket_path, registers["A5"] - 56, 4)


def assert_instruction(socket_path: Path, address: int, expected: int, name: str) -> None:
    opcode = device_debug.read_word(socket_path, address, 2)
    if opcode != expected:
        raise RuntimeError(f"{name} opcode mismatch at {address:#x}: {opcode:#x}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--socket", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--limit", type=int, default=140)
    parser.add_argument("--total-timeout", type=float, default=55.0)
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
            delta = vectors.begin_io - DEVICE_BEGIN_IO_LINK
            write_entry = delta + FUJINET_DISK_WRITE_LINK
            write_return = delta + WRITE_RETURN_LINK
            reply_msg = delta + REPLY_MSG_LINK
            update_entry = delta + UPDATE_ENTRY_LINK
            flush_entry = delta + FLUSH_ENTRY_LINK
            flush_return = delta + FLUSH_RETURN_LINK
            completion = delta + COMPLETION_LINK
            add_existing = delta + ADD_EXISTING_LINK
            add_alloc = delta + ADD_ALLOC_LINK
            add_request_store = delta + ADD_REQUEST_STORE_LINK
            add_tail = delta + ADD_TAIL_LINK
            add_clear_quick = delta + ADD_CLEAR_QUICK_LINK
            assert_instruction(socket_path, write_entry, 0x4FEF, "fujinet_disk_write")
            assert_instruction(socket_path, write_return, 0x4FEF, "write return")
            assert_instruction(socket_path, reply_msg, 0x4EAE, "ReplyMsg")
            assert_instruction(socket_path, update_entry, 0x7620, "CMD_UPDATE entry")
            assert_instruction(socket_path, flush_entry, 0x518F, "fujinet_disk_flush")
            assert_instruction(socket_path, flush_return, 0x508F, "flush return")
            assert_instruction(socket_path, completion, 0x226D, "completion")
            assert_instruction(socket_path, add_existing, 0x226D, "ADDCHANGEINT existing")
            assert_instruction(socket_path, add_alloc, 0x2C79, "ADDCHANGEINT allocation")
            assert_instruction(socket_path, add_request_store, 0x276D, "registration request store")
            assert_instruction(socket_path, add_tail, 0x4EAE, "registration AddTail")
            assert_instruction(socket_path, add_clear_quick, 0x226D, "ADDCHANGEINT quick clear")
            ipc.request(socket_path, "SET_CPU_SPEED", "10")
            trace.write(
                f"EXEC_BASE {exec_base:#x}\nDEVICE_BASE {vectors.base:#x}\n"
                f"BEGIN_IO {vectors.begin_io:#x}\nRELOCATION_DELTA {delta:#x}\n"
                f"WRITE_ENTRY {write_entry:#x}\nWRITE_RETURN {write_return:#x}\n"
                f"REPLY_MSG {reply_msg:#x}\nUPDATE_ENTRY {update_entry:#x}\n"
                f"FLUSH_ENTRY {flush_entry:#x}\nFLUSH_RETURN {flush_return:#x}\n"
                f"COMPLETION {completion:#x}\nDEVICES {names}\n"
            )
            trace.flush()
            (output / "beginio-trace-armed").write_text("\n", encoding="ascii")
            ipc.request(socket_path, "DEBUG_CONTINUE")
            copy_records: list[dict[str, int]] = []
            target_requests: dict[int, int] = {}
            internal_armed = False
            final_write_returned = False
            await_next_begin = False
            update_request: int | None = None
            await_next_after_update = False
            change_request: int | None = None
            change_registration: int | None = None
            change_events = 0
            change_begin_seen = False
            while hits < args.limit and time.monotonic() < deadline:
                try:
                    pc = wait_for_breakpoint_addresses(
                        socket_path,
                        {vectors.begin_io, write_entry, write_return, reply_msg,
                         update_entry, flush_entry, flush_return, completion,
                         add_existing, add_alloc, add_request_store, add_tail, add_clear_quick},
                        timeout=min(args.hit_timeout, deadline - time.monotonic()),
                    )
                except TimeoutError:
                    capture_breakpoint(socket_path, timeout_path)
                    trace.write(f"TIMEOUT index={hits}\n")
                    break
                registers = parse_registers(ipc.request(socket_path, "GET_CPU_REGS"))
                if pc == vectors.begin_io:
                    request = read_request(socket_path, registers["A1"])
                    if await_next_after_update and request["io_Command"] != 20:
                        trace.write("event=post-update " + request_record(registers, request, "begin") + "\n")
                        trace.flush()
                    if await_next_begin:
                        if (request["io_Command"] == 4 and request["io_Flags"] == 0x1 and
                                request["io_Offset"] == 0 and request["io_Length"] == 0):
                            update_request = request["address"]
                            await_next_begin = False
                            ipc.request(socket_path, "CLEAR_BREAKPOINT", hex(reply_msg))
                            ipc.request(socket_path, "SET_BREAKPOINT", hex(update_entry), "1")
                            ipc.request(socket_path, "SET_BREAKPOINT", hex(flush_entry), "2")
                            ipc.request(socket_path, "SET_BREAKPOINT", hex(flush_return), "3")
                            ipc.request(socket_path, "SET_BREAKPOINT", hex(completion), "4")
                            trace.write("event=update-begin " + request_record(registers, request, "begin") + "\n")
                            trace.flush()
                        else:
                            trace.write("event=unexpected-after-copy " + request_record(registers, request, "begin") + "\n")
                            trace.flush()
                            break
                    elif (request["io_Command"] == 20 and update_request is not None and
                          change_request is None):
                        change_request = request["address"]
                        change_begin_seen = True
                        ipc.request(socket_path, "CLEAR_BREAKPOINT", hex(update_entry))
                        ipc.request(socket_path, "CLEAR_BREAKPOINT", hex(flush_entry))
                        ipc.request(socket_path, "CLEAR_BREAKPOINT", hex(flush_return))
                        ipc.request(socket_path, "CLEAR_BREAKPOINT", hex(completion))
                        ipc.request(socket_path, "SET_BREAKPOINT", hex(add_existing), "1")
                        ipc.request(socket_path, "SET_BREAKPOINT", hex(add_alloc), "2")
                        ipc.request(socket_path, "SET_BREAKPOINT", hex(add_clear_quick), "3")
                        trace.write("event=addchange-begin " + request_record(registers, request, "begin") + "\n")
                        trace.flush()
                    lba = request["io_Offset"] // 512 if request["io_Offset"] % 512 == 0 else None
                    if (request["io_Command"] == 3 and request["io_Length"] == 512 and
                            len(copy_records) < len(COPY_WRITE_LBAS) and
                            lba == COPY_WRITE_LBAS[len(copy_records)]):
                        record = len(copy_records) + 52
                        copy_records.append(request)
                        target_requests[request["address"]] = record
                        trace.write(f"record={record} " + request_record(registers, request, "begin") + "\n")
                        if not internal_armed:
                            ipc.request(socket_path, "SET_BREAKPOINT", hex(write_entry), "1")
                            ipc.request(socket_path, "SET_BREAKPOINT", hex(write_return), "2")
                            ipc.request(socket_path, "SET_BREAKPOINT", hex(reply_msg), "3")
                            internal_armed = True
                    hits += 1
                else:
                    if pc in {update_entry, flush_entry, flush_return, completion}:
                        request_address = active_request_address(socket_path, registers)
                    else:
                        request_address = current_request_address(
                            socket_path, registers, pc, write_entry, write_return, reply_msg
                        )
                    if request_address in target_requests:
                        request = read_request(socket_path, request_address)
                        if pc in {write_entry, write_return, reply_msg}:
                            event = {
                                write_entry: "write-entry",
                                write_return: "write-return",
                                reply_msg: "pre-reply",
                            }[pc]
                            result = registers["D0"] if pc == write_return else None
                            trace.write(
                                f"record={target_requests[request_address]} " +
                                request_record(registers, request, event, result) + "\n"
                            )
                            if event == "write-return" and target_requests[request_address] == 57:
                                # The six Copy writes have all reached the driver
                                # return. Stop pausing on later reused IORequests
                                # and leave only BeginIO plus ReplyMsg armed.
                                ipc.request(socket_path, "CLEAR_BREAKPOINT", hex(write_entry))
                                ipc.request(socket_path, "CLEAR_BREAKPOINT", hex(write_return))
                                final_write_returned = True
                    elif update_request is not None and request_address == update_request:
                        request = read_request(socket_path, request_address)
                        event = {
                            update_entry: "update-entry",
                            flush_entry: "flush-entry",
                            flush_return: "flush-return",
                            completion: "update-completion",
                        }[pc]
                        result = registers["D0"] if pc == flush_return else None
                        trace.write("event=update " + request_record(registers, request, event, result) + "\n")
                        if pc == completion:
                            trace.write("UPDATE_COMPLETION_CAPTURED\n")
                            await_next_after_update = True
                            update_request = None
                    elif change_request is not None and pc in {add_existing, add_alloc, add_request_store, add_tail, add_clear_quick}:
                        active = active_request_address(socket_path, registers)
                        if active == change_request:
                            if pc in {add_existing, add_request_store, add_tail}:
                                change_registration = registers.get("A3", change_registration)
                            event = {
                                add_existing: "addchange-existing-or-converged",
                                add_alloc: "addchange-alloc",
                                add_request_store: "addchange-request-store",
                                add_tail: "addchange-addtail",
                                add_clear_quick: "addchange-before-clear-quick",
                            }[pc]
                            request = read_request(socket_path, change_request)
                            trace.write(
                                f"event=addchange registration={(change_registration or 0):#x} " +
                                request_record(registers, request, event) + "\n"
                            )
                            if pc == add_alloc:
                                ipc.request(socket_path, "CLEAR_BREAKPOINT", hex(add_alloc))
                                ipc.request(socket_path, "SET_BREAKPOINT", hex(add_request_store), "2")
                            elif pc == add_request_store:
                                ipc.request(socket_path, "CLEAR_BREAKPOINT", hex(add_request_store))
                                ipc.request(socket_path, "SET_BREAKPOINT", hex(add_tail), "2")
                            change_events += 1
                trace.flush()
                if final_write_returned and pc == reply_msg:
                    # One completion boundary per target is enough; the next
                    # BeginIO after record 57 is captured by the live vector.
                    if all(any(f"record={record} " in line and "event=pre-reply" in line
                               for line in trace_path.read_text(encoding="utf-8").splitlines())
                           for record in range(52, 58)):
                        trace.write("COPY_COMPLETION_BOUNDARY_CAPTURED\n")
                        await_next_begin = True
                if change_request is not None and change_begin_seen and pc == vectors.begin_io:
                    request = read_request(socket_path, registers["A1"])
                    if request["address"] == change_request and request["io_Command"] != 22:
                        trace.write("LIFECYCLE_VIOLATION_REUSED_REQUEST\n")
                        break
                    trace.write("event=after-addchange " + request_record(registers, request, "begin") + "\n")
                    change_events += 1
                    if change_events >= 8:
                        trace.write("ADDCHANGE_FOLLOWING_COMMANDS_CAPTURED\n")
                        break
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
