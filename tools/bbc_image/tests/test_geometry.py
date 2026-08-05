import unittest

from tools.bbc_image.geometry import (
    calculate_scaled_height,
    compatible_dimensions,
    resolve_geometry,
)


class GeometryTests(unittest.TestCase):
    def test_exact_scale(self) -> None:
        self.assertEqual(calculate_scaled_height(1600, 960, 160), 96)

    def test_fractional_height_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "fractional height"):
            calculate_scaled_height(1000, 333, 160)

    def test_height_must_be_multiple_of_eight(self) -> None:
        with self.assertRaisesRegex(ValueError, "divisible by 8"):
            resolve_geometry(
                source_width=1600,
                source_height=1000,
                target_width=160,
                bits_per_pixel=2,
            )

    def test_compatible_dimensions_contains_160_by_96(self) -> None:
        matches = compatible_dimensions(1600, 960, 160, 2)
        self.assertIn((160, 96), matches)


if __name__ == "__main__":
    unittest.main()
