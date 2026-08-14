"""Trace DN2 handler identity and DOS packet delivery across writable remount."""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

from . import ipc
from .debug_snapshot import live_dn2_processes, parse_registers, read_memory, resolve_dos_device_task


PUTMSG_LVO = 0x16E


def resolve_exec_vector(socket_path: Path, exec_base: int, lvo: int) -> int:
    """Resolve an Exec library vector trampoline to its implementation PC."""
    vector = exec_base - lvo
    opcode = read_memory(socket_path, vector, 2)
    if opcode == 0x4EF9:  # JMP absolute long
        return read_memory(socket_path, vector + 2, 4)
    if opcode == 0x4EB9:  # JSR absolute long
        return read_memory(socket_path, vector + 2, 4)
    return vector


def write_snapshot(log, socket_path: Path, label: str,
                   processes: list[dict[str, int | str]]) -> None:
    try:
        dn2_task = resolve_dos_device_task(socket_path, "DN2")
    except LookupError:
        dn2_task = 0
    log.write(f"SNAPSHOT label={label} count={len(processes)} dos_dn2_task={dn2_task:#x}\n")
    for process in processes:
        log.write(
            f"DN2 process={int(process['address']):#x} port={int(process['port']):#x} "
            f"state={process['state']} sigwait={int(process['sig_wait']):#x} "
            f"filesystem_task={int(process['filesystem_task']):#x}\n"
        )
    log.flush()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--socket", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--total-timeout", type=float, default=75.0)
    args = parser.parse_args(argv)
    socket_path = Path(args.socket)
    output = Path(args.output_dir)
    log_path = output / "dn2-handler-trace.log"
    deadline = time.monotonic() + args.total_timeout
    previous: set[int] = set()
    known_ports: dict[int, int] = {}
    try:
        # The runner paused before bridge startup. Arm Exec PutMsg before the
        # unchanged guest sequence can create or use either DN2 handler.
        exec_base = read_memory(socket_path, 4, 4)
        putmsg_vector = exec_base - PUTMSG_LVO
        putmsg = resolve_exec_vector(socket_path, exec_base, PUTMSG_LVO)
        ipc.request(socket_path, "SET_BREAKPOINT", hex(putmsg))
        with log_path.open("w", encoding="ascii") as log:
            log.write(f"PUTMSG_VECTOR {putmsg_vector:#x} PUTMSG_TARGET {putmsg:#x}\n")
            ipc.request(socket_path, "DEBUG_CONTINUE")
            while time.monotonic() < deadline:
                processes = live_dn2_processes(socket_path)
                current = {int(process["address"]) for process in processes}
                if current != previous:
                    label = "initial" if not previous else "dn2-set-changed"
                    write_snapshot(log, socket_path, label, processes)
                    previous = current
                known_ports = {int(process["port"]): int(process["address"]) for process in processes}

                registers = parse_registers(ipc.request(socket_path, "GET_CPU_REGS"))
                if registers.get("PC") == putmsg:
                    port = registers["A0"]
                    message = registers["A1"]
                    if port in known_ports:
                        packet = message + 20
                        packet_type = read_memory(socket_path, packet + 8, 4)
                        reply_port = read_memory(socket_path, message + 14, 4)
                        log.write(
                            f"PUTMSG dn2_process={known_ports[port]:#x} port={port:#x} "
                            f"message={message:#x} reply_port={reply_port:#x} "
                            f"packet={packet:#x} packet_type={packet_type:#x}\n"
                        )
                        log.flush()
                    ipc.request(socket_path, "DEBUG_CONTINUE")
                else:
                    time.sleep(0.05)
    finally:
        try:
            ipc.request(socket_path, "QUIT")
        except Exception:
            pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
