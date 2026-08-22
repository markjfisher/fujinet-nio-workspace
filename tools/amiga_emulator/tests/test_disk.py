from __future__ import annotations

import unittest

from amiga_emulator.disk import (
    DISK_LOAD_RESIDENT,
    NIO_LOAD_RESIDENT,
    prepend_fujinet_resident_loads,
    startup_command_offset,
    startup_sequence_needs_patch,
    validate_fujinet_resident_load_flags,
    validate_volume_label,
)


class AmigaDiskTests(unittest.TestCase):
    def test_volume_label_validation(self) -> None:
        self.assertEqual(validate_volume_label("AmigaOS3.1"), "AmigaOS3.1")
        for invalid in ("", "bad:name", "bad/name", "x" * 31):
            with self.assertRaises(ValueError):
                validate_volume_label(invalid)

    def test_load_driver_without_load_nio_is_rejected(self) -> None:
        with self.assertRaises(SystemExit) as caught:
            validate_fujinet_resident_load_flags(load_driver=True, load_nio=False)
        self.assertEqual(str(caught.exception), "--load-driver requires --load-nio")
        validate_fujinet_resident_load_flags(load_driver=False, load_nio=True)
        validate_fujinet_resident_load_flags(load_driver=False, load_nio=False)

    def test_load_driver_with_load_nio_is_valid_and_nio_first(self) -> None:
        validate_fujinet_resident_load_flags(load_driver=True, load_nio=True)
        generated = "C:Assign T: RAM:\nC:wifitest >DH0:wifitest.result\n"
        patched = prepend_fujinet_resident_loads(
            generated, load_driver=True, load_nio=True
        )
        self.assertEqual(
            patched,
            NIO_LOAD_RESIDENT + DISK_LOAD_RESIDENT + generated,
        )
        nio_at = patched.find(NIO_LOAD_RESIDENT.strip())
        disk_at = patched.find(DISK_LOAD_RESIDENT.strip())
        self.assertLess(nio_at, disk_at)

    def test_load_nio_is_first_on_generated_and_interactive_startup(self) -> None:
        generated = "C:Assign T: RAM:\nC:wifitest >DH0:wifitest.result\n"
        patched = prepend_fujinet_resident_loads(
            generated, load_driver=True, load_nio=True
        )
        self.assertTrue(patched.startswith(NIO_LOAD_RESIDENT))
        self.assertIn(DISK_LOAD_RESIDENT, patched)
        nio_at = patched.find(NIO_LOAD_RESIDENT.strip())
        disk_at = patched.find(DISK_LOAD_RESIDENT.strip())
        self.assertLess(nio_at, disk_at)

        interactive = prepend_fujinet_resident_loads("", load_nio=True)
        self.assertEqual(interactive, NIO_LOAD_RESIDENT)

    def test_interactive_load_nio_requires_startup_patch(self) -> None:
        self.assertTrue(
            startup_sequence_needs_patch(interactive=True, load_nio=True)
        )
        payload = prepend_fujinet_resident_loads("", load_nio=True)
        self.assertTrue(payload.startswith(NIO_LOAD_RESIDENT))

        self.assertFalse(
            startup_sequence_needs_patch(interactive=True)
        )

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
