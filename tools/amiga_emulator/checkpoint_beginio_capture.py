"""Arm a public BeginIO capture before releasing a guest checkpoint."""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

from .debug_snapshot import parse_registers
from . import rendezvous


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--socket", required=True)
    parser.add_argument("--run-dir", required=True)
    parser.add_argument("--image", required=True)
    parser.add_argument("--device", default="fujinet-disk.device")
    parser.add_argument("--checkpoint", default="fmount-rendezvous.marker")
    parser.add_argument("--timeout", type=float, default=90.0)
    args = parser.parse_args()
    socket_path = Path(args.socket)
    run_dir = Path(args.run_dir)
    transcript = run_dir / "checkpoint-beginio-ipc.jsonl"
    try:
        rendezvous.wait_for_hdf_checkpoint(Path(args.image), args.checkpoint, args.timeout)
        rendezvous.log_event(transcript, "checkpoint_detected",
                             image=args.image, guest_path=args.checkpoint)
        vectors = rendezvous.resolve_device(socket_path, transcript, args.device)
        rendezvous.request(socket_path, transcript, "DEBUG_ACTIVATE")
        rendezvous.arm_breakpoint(socket_path, transcript, vectors.begin_io)
        rendezvous.log_event(transcript, "breakpoint_armed",
                             address=hex(vectors.begin_io))
        # The marker was published before Ask. Confirm no target device call is
        # in flight while the guest remains at the local gate.
        gate_deadline = time.monotonic() + 0.5
        while time.monotonic() < gate_deadline:
            registers = parse_registers(rendezvous.request(socket_path, transcript, "GET_CPU_REGS"))
            if registers.get("PC") == vectors.begin_io:
                raise RuntimeError("BeginIO occurred before guest release")
            time.sleep(0.02)
        rendezvous.request(socket_path, transcript, "DEBUG_CONTINUE")
        rendezvous.release_guest(socket_path, transcript)
        rendezvous.log_event(transcript, "guest_released", key="Return")
        deadline = time.monotonic() + args.timeout
        while time.monotonic() < deadline:
            registers = parse_registers(rendezvous.request(socket_path, transcript, "GET_CPU_REGS"))
            if registers.get("PC") == vectors.begin_io:
                record = rendezvous.capture_raw(socket_path, transcript, registers["A1"])
                (run_dir / "checkpoint-beginio-capture.json").write_text(
                    json.dumps(record, indent=2) + "\n", encoding="utf-8")
                rendezvous.request(socket_path, transcript, "DEBUG_CONTINUE")
                return 0
            time.sleep(0.02)
        raise TimeoutError("target BeginIO was not observed after guest release")
    except Exception as error:
        with transcript.open("a", encoding="utf-8") as out:
            out.write(json.dumps({"event": "controller_error",
                                  "error": repr(error)}) + "\n")
        # Diagnostic timeout intentionally leaves the guest untouched.
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
