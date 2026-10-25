"""Budget and link-closure regressions for the production CA65 image."""
import importlib.util
import struct
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
GATE = ROOT / 'repos/nio-core-apps/tools/check_atari_resident_ram.py'
spec = importlib.util.spec_from_file_location('resident_ram', GATE)
gate = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gate)


class ResidentRamTests(unittest.TestCase):
    def image(self, bss):
        return b'\x01\x00o65\x00\x00\x08' + struct.pack(
            '<9H', 0, 1000, 1000, 20, 1020, bss, 0, 26, 0)

    def test_gate_counts_bss_and_zero_page_at_exact_boundary(self):
        with tempfile.TemporaryDirectory() as directory:
            module = Path(directory) / 'resident.o65'
            link_map = Path(directory) / 'resident.map'
            link_map.write_text('fnresident-asm.o:\nSegment list:\n')
            for total in (3072, 3073):
                module.write_bytes(self.image(total - 1020 - 26))
                result = subprocess.run([sys.executable, str(GATE), '--module', str(module),
                                         '--map', str(link_map)], capture_output=True)
                self.assertEqual(result.returncode == 0, total == 3072)

    def test_runtime_or_other_object_is_rejected(self):
        with self.assertRaises(ValueError):
            gate.measure(self.image(100), 'fnresident-asm.o:\natari.lib(pushax.o):\nSegment list:\n')

    def test_production_image_is_below_budget_without_software_stack(self):
        binary = ROOT / 'repos/nio-core-apps/build/atari/bin/fnresident-asm.o65'
        if not binary.exists():
            self.skipTest('build fnresident-asm before checking its measured artifact')
        measured = gate.measure(binary.read_bytes(), binary.with_suffix('.map').read_text())
        self.assertLessEqual(measured['total'], 3072)
        self.assertEqual(measured['permanent_stack'], 0)
