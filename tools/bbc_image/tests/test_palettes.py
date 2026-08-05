import unittest

from tools.bbc_image.palettes import (
    PALETTES,
    make_ula_palette_bytes,
    ula_logical_colour,
)


class PaletteTests(unittest.TestCase):
    def test_mode5_alias_groups(self) -> None:
        groups = {
            0: {0, 1, 4, 5},
            1: {2, 3, 6, 7},
            2: {8, 9, 12, 13},
            3: {10, 11, 14, 15},
        }
        for logical, aliases in groups.items():
            actual = {
                index
                for index in range(16)
                if ula_logical_colour(index, 2) == logical
            }
            self.assertEqual(actual, aliases)

    def test_mode5_palette_programs_all_aliases(self) -> None:
        values = make_ula_palette_bytes(PALETTES["mode5"], 2)
        expected_physical = (0, 1, 3, 7)
        for index, command in enumerate(values):
            logical = ula_logical_colour(index, 2)
            physical = (command & 7) ^ 7
            self.assertEqual(physical, expected_physical[logical])


if __name__ == "__main__":
    unittest.main()
