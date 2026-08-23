from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from amiga_emulator.ffs import resolve_fast_file_system


class FastFileSystemResolveTests(unittest.TestCase):
    def test_prefers_explicit_env_path(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            ffs = root / "FastFileSystem"
            ffs.write_bytes(b"ffs")
            found = resolve_fast_file_system(
                root, environment={"AMIBERRY_FAST_FILE_SYSTEM": str(ffs)}
            )
            self.assertEqual(found, str(ffs.resolve()))

    def test_uses_manifest_sibling_when_recorded_missing(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            env_dir = root / "build" / "amiga-envs" / "wb32" / "a1200-030"
            env_dir.mkdir(parents=True)
            ffs = env_dir / "FastFileSystem"
            base = env_dir / "base.hdf"
            ffs.write_bytes(b"ffs")
            base.write_bytes(b"hdf")
            (env_dir / "manifest.json").write_text(
                json.dumps({"base_hdf": str(base), "kickstart": "/tmp/kick"}),
                encoding="utf-8",
            )
            found = resolve_fast_file_system(
                root,
                environment={
                    "AMIGA_ENV_ID": "wb32",
                    "AMIGA_MACHINE_ID": "a1200-030",
                    "AMIBERRY_FAST_FILE_SYSTEM": "",
                },
            )
            self.assertEqual(found, str(ffs.resolve()))

    def test_falls_back_to_expanded_tree(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            expanded = root / "os"
            ffs = expanded / "L" / "FastFileSystem"
            ffs.parent.mkdir(parents=True)
            ffs.write_bytes(b"ffs")
            found = resolve_fast_file_system(
                root,
                environment={
                    "AMIGA_WB32_EXPANDED": str(expanded),
                    "AMIBERRY_FAST_FILE_SYSTEM": "",
                },
            )
            self.assertEqual(found, str(ffs.resolve()))


if __name__ == "__main__":
    unittest.main()
