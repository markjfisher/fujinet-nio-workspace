from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from amiga_emulator.run import AmigaRunner, parse_args


class AmigaRunnerTests(unittest.TestCase):
    def test_argument_aliases(self) -> None:
        args = parse_args(["--adf", "test.adf", "--timeout", "2", "--external-nio"])
        self.assertEqual(args.disk, "test.adf")
        self.assertEqual(args.timeout, 2)
        self.assertTrue(args.external_nio)

    def test_command_contains_transport_and_profile_settings(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            disk = root / "test.hdf"
            rom = root / "kickstart.rom"
            ffs = root / "FastFileSystem"
            for path in (disk, rom, ffs):
                path.write_bytes(b"test")
            environment = {
                "AMIGA_RUN_DIR": str(root / "run"),
                "AMIBERRY_KICKSTART": str(rom),
                "AMIBERRY_FAST_FILE_SYSTEM": str(ffs),
                "AMIBERRY_EXTRA_SETTINGS": "chipmem_size=512;fastmem_size=8",
            }
            with patch.dict(os.environ, environment, clear=False):
                runner = AmigaRunner(parse_args(["--disk", str(disk)]))
                command = runner.amiberry_command(None)

        self.assertIn("serial_port=tcp://127.0.0.1:23462", command)
        self.assertIn("-W", command)
        self.assertIn("DH0:" + str(disk), command)
        self.assertIn("chipmem_size=512", command)
        self.assertIn("fastmem_size=8", command)
        self.assertIn("serial_direct=true", command)


if __name__ == "__main__":
    unittest.main()
