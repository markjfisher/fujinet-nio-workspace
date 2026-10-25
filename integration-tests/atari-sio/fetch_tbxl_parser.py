#!/usr/bin/env python3
"""Fetch the pinned tbxl-parser release used for Atari BASIC fixtures."""
from __future__ import annotations

import argparse
import hashlib
import os
import stat
import tempfile
import urllib.request
import zipfile
from pathlib import Path

REVISION = "v12-0-ga877718"
URL = ("https://github.com/dmsc/tbxl-parser/releases/download/v12/"
       "basicParser-v12-0-ga877718-linux64.zip")
SHA256 = "f316cd1f61d8fd623890e493a0d7b7c7635ba1e4339c4b690fd72b1009a1259d"
MEMBER = f"basicParser-{REVISION}/basicParser"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--output", type=Path, required=True)
    ns = ap.parse_args()
    if ns.output.is_file():
        return 0
    ns.output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="tbxl-parser-") as tmp:
        archive = Path(tmp) / "tbxl-parser.zip"
        with urllib.request.urlopen(URL) as response:
            archive.write_bytes(response.read())
        if hashlib.sha256(archive.read_bytes()).hexdigest() != SHA256:
            raise SystemExit("tbxl-parser release checksum mismatch")
        with zipfile.ZipFile(archive) as zf:
            ns.output.write_bytes(zf.read(MEMBER))
    ns.output.chmod(ns.output.stat().st_mode | stat.S_IXUSR)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
