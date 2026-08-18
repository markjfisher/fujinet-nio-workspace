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
                "AMIBERRY_EXTRA_ARGS": "-w -1",
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
        self.assertEqual(command[command.index("-w") + 1], "-1")

    def test_vhd_harddrive_uses_amiberry_harddisk_option(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            disk = root / "workbench.vhd"
            rom = root / "kickstart.rom"
            ffs = root / "FastFileSystem"
            for path in (disk, rom, ffs):
                path.write_bytes(b"test")
            environment = {
                "AMIGA_RUN_DIR": str(root / "run"),
                "AMIBERRY_KICKSTART": str(rom),
                "AMIBERRY_FAST_FILE_SYSTEM": str(ffs),
            }
            with patch.dict(os.environ, environment, clear=False):
                runner = AmigaRunner(parse_args(["--harddrive", str(disk)]))
                command = runner.amiberry_command(None)

        self.assertIn("-W", command)
        self.assertIn("DH0:" + str(disk), command)
        self.assertNotIn("-0", command)

    def test_amiga_forever_rom_key_is_staged_beside_kickstart(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            disk = root / "test.adf"
            rom = root / "encrypted.rom"
            rom_key = root / "rom.key"
            for path in (disk, rom, rom_key):
                path.write_bytes(b"test")
            environment = {
                "AMIGA_RUN_DIR": str(root / "run"),
                "AMIBERRY_KICKSTART": str(rom),
                "AMIBERRY_ROM_KEY": str(rom_key),
            }
            with patch.dict(os.environ, environment, clear=False):
                runner = AmigaRunner(parse_args(["--disk", str(disk)]))
                runner.stage_rom_files()
                self.assertEqual(
                    (runner.rom_dir / "rom.key").read_bytes(), b"test"
                )

    def test_uae_config_is_loaded_before_profile_overrides(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            disk = root / "workbench.hdf"
            rom = root / "kickstart.rom"
            ffs = root / "FastFileSystem"
            uae_config = root / "base.uae"
            for path in (disk, rom, ffs, uae_config):
                path.write_bytes(b"test")
            environment = {
                "AMIGA_RUN_DIR": str(root / "run"),
                "AMIBERRY_KICKSTART": str(rom),
                "AMIBERRY_FAST_FILE_SYSTEM": str(ffs),
                "AMIBERRY_UAE_CONFIG": str(uae_config),
                "AMIBERRY_EXTRA_SETTINGS": "cpu_model=68030;rtgmem_size=16",
            }
            with patch.dict(os.environ, environment, clear=False):
                runner = AmigaRunner(parse_args(["--harddrive", str(disk)]))
                command = runner.amiberry_command(None)

        config_position = command.index(str(uae_config))
        override_position = command.index("cpu_model=68030")
        self.assertLess(config_position, override_position)


if __name__ == "__main__":
    unittest.main()
