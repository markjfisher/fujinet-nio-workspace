"""Compare final DiskDevice write payloads in an NIO log with a backing ADF."""

from __future__ import annotations

import argparse
import hashlib
import re
from pathlib import Path


WRITE_RE = re.compile(r"receive: id=(\d+) dev=0xFC cmd=0x04 .*payload=520")
HEX_RE = re.compile(r"\s[0-9a-f]{4}: ((?:[0-9a-f]{2} ?)+)", re.IGNORECASE)


def payloads(log_path: Path) -> list[tuple[int, int, bytes]]:
    lines = log_path.read_text(encoding="utf-8", errors="replace").splitlines()
    found: list[tuple[int, int, bytes]] = []
    index = 0
    while index < len(lines):
        match = WRITE_RE.search(lines[index])
        if not match:
            index += 1
            continue
        request_id = int(match.group(1))
        data = bytearray()
        index += 1
        while index < len(lines):
            if index > 0 and ("fujibus: receive:" in lines[index] or "fujibus: send:" in lines[index]):
                break
            hex_match = HEX_RE.search(lines[index])
            if hex_match:
                data.extend(bytes.fromhex(hex_match.group(1)))
            index += 1
        if len(data) < 8:
            raise ValueError(f"incomplete write payload for request {request_id}: {len(data)} bytes")
        lba = int.from_bytes(data[2:6], "little")
        found.append((request_id, lba, bytes(data[8:])))
    return found


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--log", required=True, type=Path)
    parser.add_argument("--adf", required=True, type=Path)
    parser.add_argument("--lba", type=int, nargs="+", default=[880, 881, 882, 883])
    args = parser.parse_args()
    final: dict[int, tuple[int, bytes]] = {}
    for request_id, lba, buffer in payloads(args.log):
        if lba in args.lba:
            final[lba] = (request_id, buffer)
    image = args.adf.read_bytes()
    for lba in args.lba:
        stored = image[lba * 512:(lba + 1) * 512]
        if lba not in final:
            print(f"LBA {lba}: no DiskDevice write payload; stored_sha256={digest(stored)}")
            continue
        request_id, submitted = final[lba]
        compared = min(len(submitted), len(stored))
        print(
            f"LBA {lba}: final_request={request_id} logged_bytes={len(submitted)} "
            f"submitted_prefix_sha256={digest(submitted)} "
            f"stored_prefix_sha256={digest(stored[:compared])} "
            f"prefix_equal={submitted == stored[:compared]}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
