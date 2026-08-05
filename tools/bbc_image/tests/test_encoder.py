import unittest

from tools.bbc_image.encoder import (
    decode_screen,
    encode_screen,
    pack_pixels,
    unpack_pixels,
)
from tools.bbc_image.geometry import OutputGeometry


class EncoderTests(unittest.TestCase):
    def test_mode5_known_byte(self) -> None:
        self.assertEqual(pack_pixels((0, 1, 2, 3), 2), 0x35)
        self.assertEqual(unpack_pixels(0x35, 2), (0, 1, 2, 3))

    def test_solid_mode5_bytes(self) -> None:
        self.assertEqual(pack_pixels((0, 0, 0, 0), 2), 0x00)
        self.assertEqual(pack_pixels((1, 1, 1, 1), 2), 0x0F)
        self.assertEqual(pack_pixels((2, 2, 2, 2), 2), 0xF0)
        self.assertEqual(pack_pixels((3, 3, 3, 3), 2), 0xFF)

    def test_round_trip_all_depths(self) -> None:
        for bpp, width in ((1, 16), (2, 8), (4, 4)):
            with self.subTest(bpp=bpp):
                geometry = OutputGeometry(width, 16, bpp)
                colours = 1 << bpp
                pixels = [
                    (x + y) % colours
                    for y in range(geometry.height)
                    for x in range(geometry.width)
                ]
                encoded = encode_screen(pixels, geometry)
                self.assertEqual(len(encoded), geometry.byte_size)
                self.assertEqual(decode_screen(encoded, geometry), pixels)


if __name__ == "__main__":
    unittest.main()
