"""Compare full DiskDevice read responses in an NIO log with a backing ADF."""

from __future__ import annotations

import argparse
import hashlib
import re
from pathlib import Path


RECEIVE_RE = re.compile(r"receive: id=(\d+) dev=0xFC cmd=0x03 .*payload=8")
SEND_RE = re.compile(r"send: dev=0xFC status=0 cmd=0x03 payload=523")
HEX_RE = re.compile(r"\s[0-9a-f]{4}: ((?:[0-9a-f]{2} ?)+)", re.IGNORECASE)


def payload_after(lines: list[str], index: int, expected: int) -> tuple[bytes, int]:
    data = bytearray()
    index += 1
    while index < len(lines):
        if data and ("fujibus: receive:" in lines[index] or "fujibus: send:" in lines[index]):
            break
        match = HEX_RE.search(lines[index])
        if match:
            data.extend(bytes.fromhex(match.group(1)))
        index += 1
        if len(data) >= expected:
            break
    if len(data) != expected:
        raise ValueError(f"expected {expected} payload bytes, got {len(data)}")
    return bytes(data), index


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--log", required=True, type=Path)
    parser.add_argument("--adf", required=True, type=Path)
    parser.add_argument("--lba", type=int, nargs="+", default=[880, 881, 882, 883])
    args = parser.parse_args()
    lines = args.log.read_text(encoding="utf-8", errors="replace").splitlines()
    image = args.adf.read_bytes()
    pending: dict[int, tuple[int, int]] = {}
    responses: dict[int, tuple[int, bytes]] = {}
    index = 0
    while index < len(lines):
        receive = RECEIVE_RE.search(lines[index])
        if receive:
            payload, index = payload_after(lines, index, 8)
            request_id = int(receive.group(1))
            pending[request_id] = (payload[1], int.from_bytes(payload[2:6], "little"))
            continue
        if SEND_RE.search(lines[index]):
            payload, index = payload_after(lines, index, 523)
            # Response has no explicit request id; match the oldest pending
            # DiskDevice read for its echoed slot/LBA.
            slot = payload[4]
            lba = int.from_bytes(payload[5:9], "little")
            matches = [(request_id, item) for request_id, item in pending.items()
                       if item == (slot, lba)]
            if matches:
                request_id, _ = min(matches)
                pending.pop(request_id)
                responses[lba] = (request_id, payload[11:])
            continue
        index += 1
    for lba in args.lba:
        stored = image[lba * 512:(lba + 1) * 512]
        response = responses.get(lba)
        if response is None:
            print(f"LBA {lba}: no matching full read response")
            continue
        request_id, returned = response
        print(
            f"LBA {lba}: request_id={request_id} returned_sha256={digest(returned)} "
            f"stored_sha256={digest(stored)} equal={returned == stored}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
