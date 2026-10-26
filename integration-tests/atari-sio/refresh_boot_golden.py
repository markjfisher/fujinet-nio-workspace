#!/usr/bin/env python3
"""Refresh the pinned Atari boot-image golden after an intentional boot disk change.

    python3 integration-tests/atari-sio/refresh_boot_golden.py [--check]

disk_v1.json pins the production boot image (the nio-core-apps build output): its
SHA-256 and the literal bytes, checksum and hash of its first four sectors, and the
test in tests/test_disk_v1_fixtures.py repeats the image hash on purpose so that an
accidental edit of the JSON alone cannot hide a change. Sectors 1-3 are the PicoBoot
loader; sector 4 starts the first file, so it changes whenever that program does (its
XEX header carries the end address).

When the boot disk changes on purpose (rebuild it with `make TARGET=atari boot-disk` in
repos/nio-core-apps), run this to rewrite the pinned values from the built image. It
changes only values that differ, refuses if an expected value is not found exactly once,
and --check only reports. Review the diff, then run the Atari tests.
"""
import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

WORKSPACE = Path(__file__).resolve().parents[2]
FIXTURE = WORKSPACE / "repos/fujinet-nio/tests/fixtures/atari-sio/disk_v1.json"
MANIFEST = WORKSPACE / "repos/fujinet-nio/tests/fixtures/atari-sio/disk_v1.manifest.json"
TEST = WORKSPACE / "integration-tests/atari-sio/tests/test_disk_v1_fixtures.py"


def sio_checksum(data: bytes) -> int:
    total = 0
    for byte in data:
        total += byte
        total = (total & 0xFF) + (total >> 8)
    return total & 0xFF


def hex_bytes(data: bytes) -> str:
    return " ".join(f"{b:02x}" for b in data)


def replace_exactly(text: str, old: str, new: str, expected: int, what: str) -> str:
    found = text.count(old)
    if found != expected:
        sys.exit(f"refusing: {what}: expected {expected} occurrence(s) of the old value, found {found}")
    return text.replace(old, new)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--check", action="store_true", help="report what would change and exit 1 if anything would")
    args = ap.parse_args()

    fixture_text = FIXTURE.read_text()
    fixture = json.loads(fixture_text)
    source = fixture["source_image"]
    image_path = WORKSPACE / source["path"]
    if not image_path.exists():
        sys.exit(f"the built image is missing: {image_path}\nbuild it: make TARGET=atari boot-disk in repos/nio-core-apps")
    image = image_path.read_bytes()
    if image[: source["atr_header_bytes"]] != bytes.fromhex(source["atr_header"].replace(" ", "")):
        sys.exit("the ATR header changed (the image size or format differs); that needs a deliberate fixture edit")

    manifest_text = MANIFEST.read_text()
    test_text = TEST.read_text()
    changes = []

    new_image_sha = hashlib.sha256(image).hexdigest()
    if new_image_sha != source["sha256"]:
        changes.append(f"image sha256 {source['sha256'][:12]}... -> {new_image_sha[:12]}...")
        fixture_text = replace_exactly(fixture_text, source["sha256"], new_image_sha, 1, "image sha256 in the fixture")
        test_text = replace_exactly(test_text, source["sha256"], new_image_sha, 1, "image sha256 in the test")

    for number, golden in source["sectors"].items():
        start = golden["atr_offset"]
        new = image[start : start + golden["bytes"]]
        old = bytes.fromhex(golden["data"].replace(" ", ""))
        if new == old:
            continue
        old_sum, new_sum = golden["checksum"], f"{sio_checksum(new):02x}"
        new_sha = hashlib.sha256(new).hexdigest()
        changes.append(f"sector {number}: bytes changed, checksum {old_sum} -> {new_sum}")

        scenarios = [s for s in fixture["scenarios"] if s.get("source_image_sector") == int(number)]
        # the literal bytes appear in the source image block and in each scenario that serves them
        fixture_text = replace_exactly(fixture_text, golden["data"], hex_bytes(new), 1 + len(scenarios),
                                       f"sector {number} bytes")
        fixture_text = replace_exactly(fixture_text, golden["sha256"], new_sha, 1, f"sector {number} sha256")
        fixture_text = replace_exactly(fixture_text, f'"checksum": "{old_sum}"', f'"checksum": "{new_sum}"', 1,
                                       f"sector {number} checksum")
        with_sum = [s for s in scenarios if f"sum:{old_sum}" in s.get("phases", [])]
        fixture_text = replace_exactly(fixture_text, f'"sum:{old_sum}"', f'"sum:{new_sum}"', len(with_sum),
                                       f"sector {number} reply checksum in the scenarios")
        manifest_text = replace_exactly(manifest_text, f"sum:{old_sum}", f"sum:{new_sum}", len(with_sum),
                                        f"sector {number} reply checksum in the manifest")

    if not changes:
        print("boot golden already matches the built image")
        return 0
    for line in changes:
        print(("would change: " if args.check else "changed: ") + line)
    if args.check:
        return 1
    json.loads(fixture_text)
    json.loads(manifest_text)
    FIXTURE.write_text(fixture_text)
    MANIFEST.write_text(manifest_text)
    TEST.write_text(test_text)
    print("now run: python3 -m unittest discover -s integration-tests/atari-sio/tests")
    return 0


if __name__ == "__main__":
    sys.exit(main())
