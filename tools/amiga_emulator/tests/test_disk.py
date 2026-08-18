from __future__ import annotations

import unittest

from amiga_emulator.disk import startup_command_offset, validate_volume_label


class AmigaDiskTests(unittest.TestCase):
    def test_volume_label_validation(self) -> None:
        self.assertEqual(validate_volume_label("AmigaOS3.1"), "AmigaOS3.1")
        for invalid in ("", "bad:name", "bad/name", "x" * 31):
            with self.assertRaises(ValueError):
                validate_volume_label(invalid)

    def test_startup_command_matches_plain_and_prefixed_loadwb(self) -> None:
        for line in ("LoadWB\n", "C:LoadWB\n", "  c:loadwb delay\n"):
            startup = "C:SetPatch QUIET\n" + line + "C:EndCLI\n"
            offset = startup_command_offset(startup, "LoadWB")
            self.assertEqual(offset, len("C:SetPatch QUIET\n"))

    def test_startup_command_does_not_match_comment_text(self) -> None:
        self.assertIsNone(
            startup_command_offset("; LoadWB is deliberately disabled\n", "LoadWB")
        )


if __name__ == "__main__":
    unittest.main()
