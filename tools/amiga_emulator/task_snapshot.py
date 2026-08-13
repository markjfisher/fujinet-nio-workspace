"""Capture one bounded live Exec task snapshot from Amiberry IPC."""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

from . import ipc
from .debug_snapshot import capture_task_snapshot


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--socket", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--delay", type=float, default=35.0)
    args = parser.parse_args(argv)
    socket_path = Path(args.socket)
    output = Path(args.output_dir)
    time.sleep(args.delay)
    try:
        ipc.request(socket_path, "DEBUG_ACTIVATE")
        capture_task_snapshot(socket_path, output / "task-timeout-snapshot.log")
    finally:
        try:
            ipc.request(socket_path, "QUIT")
        except Exception:
            pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
