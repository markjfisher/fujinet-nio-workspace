"""Client for Amiberry's optional Unix IPC socket."""

from __future__ import annotations

import argparse
import os
import socket
import sys
import time
from pathlib import Path


def socket_candidates() -> list[Path]:
    """Return the standard Amiberry socket locations, including instances."""
    candidates: list[Path] = []
    runtime = os.environ.get("XDG_RUNTIME_DIR")
    if runtime:
        candidates.append(Path(runtime) / "amiberry.sock")
    candidates.append(Path("/tmp/amiberry.sock"))
    # Amiberry appends an instance suffix when the default is occupied.
    for base in list(candidates):
        candidates.extend(base.with_name(f"{base.name}.{number}") for number in range(1, 10))
    return candidates


def request(path: Path, command: str, *arguments: str, timeout: float = 2.0) -> str:
    """Send one tab-separated command and return Amiberry's response."""
    message = "\t".join((command, *arguments)) + "\n"
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as connection:
        connection.settimeout(timeout)
        connection.connect(str(path))
        connection.sendall(message.encode("utf-8"))
        response = bytearray()
        while b"\n" not in response:
            try:
                chunk = connection.recv(4096)
            except socket.timeout:
                # Amiberry's IPC replies are not newline-terminated in all
                # released builds. A received chunk is a complete response
                # when the peer leaves the connection open.
                if response:
                    break
                raise
            if not chunk:
                break
            response.extend(chunk)
    result = response.decode("utf-8", errors="replace").strip()
    if result.startswith("ERROR"):
        raise RuntimeError(result)
    return result


def find_socket(explicit: str | None = None, timeout: float = 2.0) -> Path:
    """Find a live Amiberry socket, preferring an explicitly supplied path."""
    candidates = [Path(explicit)] if explicit else socket_candidates()
    deadline = time.monotonic() + timeout
    while True:
        for path in candidates:
            try:
                # Amiberry versions have returned both OK and PONG for PING.
                # A non-empty, non-ERROR response proves that this is a live
                # IPC endpoint; request() already rejects ERROR responses.
                if request(path, "PING", timeout=min(0.25, max(0.05, timeout))):
                    return path
            except OSError:
                continue
        if explicit or time.monotonic() >= deadline:
            break
        time.sleep(0.05)
    locations = ", ".join(str(path) for path in candidates)
    raise FileNotFoundError(f"No live Amiberry IPC socket found ({locations})")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--socket", dest="socket_path", help="Amiberry socket path")
    parser.add_argument("--timeout", type=float, default=2.0)
    parser.add_argument("command", help="IPC command, for example GET_STATUS")
    parser.add_argument("argument", nargs="*")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    path = find_socket(args.socket_path, args.timeout)
    print(request(path, args.command, *args.argument, timeout=args.timeout))
    return 0


if __name__ == "__main__":
    sys.exit(main())
