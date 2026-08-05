"""Compress raw bytes with the config-nio LZ-style packer."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any, Iterable, Sequence


def find_best_seq(data: bytes, dst: int, max_offset: int = 256, max_seq_len: int = 129) -> tuple[int, int]:
    best_from = 0
    best = 0
    for src in range(max(dst - max_offset, 0), dst):
        limit = min(len(data) - dst, max_seq_len)
        for num in range(limit):
            if data[src + num] != data[dst + num]:
                break
            matched = num + 1
            if matched > best:
                best_from = src
                best = matched
    return best_from, best


def compress(data: bytes) -> bytes:
    out = bytearray()
    dst = 0
    raw_copy_len = 0
    raw_len_addr = 0
    while dst < len(data):
        src, best = find_best_seq(data, dst)
        if best >= 2 + (1 if raw_copy_len else 0):
            if raw_copy_len:
                out[raw_len_addr] = raw_copy_len
                raw_copy_len = 0
            out.append((best - 2) | 0x80)
            out.append((src - dst + 0x100) & 0xFF)
            dst += best
        else:
            if raw_copy_len == 127:
                out[raw_len_addr] = raw_copy_len
                raw_copy_len = 0
            if not raw_copy_len:
                raw_len_addr = len(out)
                out.append(0)
            out.append(data[dst])
            raw_copy_len += 1
            dst += 1
    if raw_copy_len:
        out[raw_len_addr] = raw_copy_len
    out.append(0)
    return bytes(out)


def chunked(data: Sequence[int], size: int) -> Iterable[Sequence[int]]:
    for i in range(0, len(data), size):
        yield data[i : i + size]


def format_ca65(data: bytes, values_per_line: int = 16, label: str | None = None) -> str:
    """Output CA65-compatible .byte directives (16 hex bytes per row by default)."""
    lines: list[str] = []

    if label:
        lines.append(f"{label}:")

    for row in chunked(list(data), values_per_line):
        items = ", ".join(f"${v:02X}" for v in row)
        lines.append(f"        .byte {items}")

    return "\n".join(lines) + "\n"


def read_input(path: Path | None) -> bytes:
    if path is None:
        return sys.stdin.buffer.read()
    return path.read_bytes()


def write_output(path: Path | None, data: bytes | str, *, binary: bool) -> None:
    if path is None:
        if binary:
            assert isinstance(data, (bytes, bytearray))
            sys.stdout.buffer.write(data)
        else:
            assert isinstance(data, str)
            sys.stdout.write(data)
        return

    if binary:
        assert isinstance(data, (bytes, bytearray))
        path.write_bytes(data)
    else:
        assert isinstance(data, str)
        path.write_text(data, encoding="utf-8")


def cmd_compress(args: argparse.Namespace) -> int:
    data = read_input(args.input)
    packed = compress(data)

    if args.target == "ca65":
        output: bytes | str = format_ca65(packed, label=(args.label or None))
        write_output(args.output, output, binary=False)
    else:
        write_output(args.output, packed, binary=True)

    return 0


def register_subcommands(subparsers: Any) -> None:
    parser = subparsers.add_parser(
        "compress",
        help="Compress raw bytes with the config-nio LZ-style packer",
        description=(
            "Reads uncompressed input, writes compressed output. "
            "Default I/O is stdin/stdout (binary). "
            "Use --target ca65 for CA65 .byte directives."
        ),
    )
    parser.add_argument(
        "-i", "--input",
        type=Path,
        help="Input file (default: stdin).",
    )
    parser.add_argument(
        "-o", "--output",
        type=Path,
        help="Output file (default: stdout).",
    )
    parser.add_argument(
        "--target",
        choices=("binary", "ca65"),
        default="binary",
        help="Output format (default: binary).",
    )
    parser.add_argument(
        "--label",
        default="",
        help="Optional label for --target ca65 output. Empty omits the label.",
    )
    parser.set_defaults(fn=cmd_compress)
