from __future__ import annotations

from collections.abc import Sequence

from .geometry import OutputGeometry


def pack_pixels(pixels: Sequence[int], bits_per_pixel: int) -> int:
    """Pack one BBC bitmap byte.

    BBC pixels are stored in interleaved bit planes. For example, at 2bpp four
    left-to-right pixels A,B,C,D become:

        bit 7..0 = A1 B1 C1 D1 A0 B0 C0 D0
    """
    if bits_per_pixel not in (1, 2, 4):
        raise ValueError("bits per pixel must be 1, 2 or 4")

    pixels_per_byte = 8 // bits_per_pixel
    if len(pixels) != pixels_per_byte:
        raise ValueError(
            f"{bits_per_pixel}bpp requires {pixels_per_byte} pixels per byte"
        )

    maximum = (1 << bits_per_pixel) - 1
    value = 0

    for pixel_position, colour in enumerate(pixels):
        if not 0 <= colour <= maximum:
            raise ValueError(
                f"logical colour {colour} does not fit in {bits_per_pixel} bits"
            )
        horizontal_bit = pixels_per_byte - 1 - pixel_position
        for colour_bit in range(bits_per_pixel):
            destination_bit = colour_bit * pixels_per_byte + horizontal_bit
            value |= ((colour >> colour_bit) & 1) << destination_bit

    return value


def unpack_pixels(value: int, bits_per_pixel: int) -> tuple[int, ...]:
    if not 0 <= value <= 0xFF:
        raise ValueError("byte value must be 0..255")
    pixels_per_byte = 8 // bits_per_pixel
    pixels: list[int] = []

    for pixel_position in range(pixels_per_byte):
        horizontal_bit = pixels_per_byte - 1 - pixel_position
        colour = 0
        for colour_bit in range(bits_per_pixel):
            source_bit = colour_bit * pixels_per_byte + horizontal_bit
            colour |= ((value >> source_bit) & 1) << colour_bit
        pixels.append(colour)

    return tuple(pixels)


def encode_screen(indices: Sequence[int], geometry: OutputGeometry) -> bytes:
    """Encode row-major logical pixels into BBC character-row memory order."""
    expected = geometry.width * geometry.height
    if len(indices) != expected:
        raise ValueError(f"expected {expected} pixels, got {len(indices)}")

    data = bytearray()
    pixels_per_byte = geometry.pixels_per_byte
    byte_columns = geometry.bytes_per_scanline

    for character_row in range(geometry.character_rows):
        y_start = character_row * 8
        for byte_column in range(byte_columns):
            x_start = byte_column * pixels_per_byte
            for raster in range(8):
                y = y_start + raster
                row_offset = y * geometry.width
                start = row_offset + x_start
                data.append(
                    pack_pixels(
                        indices[start:start + pixels_per_byte],
                        geometry.bits_per_pixel,
                    )
                )

    if len(data) != geometry.byte_size:
        raise AssertionError(
            f"encoder produced {len(data)} bytes, expected {geometry.byte_size}"
        )
    return bytes(data)


def decode_screen(data: bytes, geometry: OutputGeometry) -> list[int]:
    if len(data) != geometry.byte_size:
        raise ValueError(
            f"expected {geometry.byte_size} bytes, got {len(data)}"
        )

    result = [0] * (geometry.width * geometry.height)
    pixels_per_byte = geometry.pixels_per_byte
    byte_columns = geometry.bytes_per_scanline
    offset = 0

    for character_row in range(geometry.character_rows):
        y_start = character_row * 8
        for byte_column in range(byte_columns):
            x_start = byte_column * pixels_per_byte
            for raster in range(8):
                y = y_start + raster
                row_offset = y * geometry.width
                pixels = unpack_pixels(data[offset], geometry.bits_per_pixel)
                offset += 1
                result[
                    row_offset + x_start:
                    row_offset + x_start + pixels_per_byte
                ] = pixels

    return result
