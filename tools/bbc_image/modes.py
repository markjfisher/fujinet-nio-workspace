from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class BbcMode:
    """The bitmap characteristics of a BBC Micro graphics mode."""

    number: int
    width: int
    height: int
    bits_per_pixel: int
    colours: int
    full_screen_bytes: int

    @property
    def pixels_per_byte(self) -> int:
        return 8 // self.bits_per_pixel

    @property
    def bytes_per_scanline(self) -> int:
        return self.width // self.pixels_per_byte


MODE_PRESETS: dict[int, BbcMode] = {
    0: BbcMode(0, 640, 256, 1, 2, 20 * 1024),
    1: BbcMode(1, 320, 256, 2, 4, 20 * 1024),
    2: BbcMode(2, 160, 256, 4, 16, 20 * 1024),
    4: BbcMode(4, 320, 256, 1, 2, 10 * 1024),
    5: BbcMode(5, 160, 256, 2, 4, 10 * 1024),
}


def get_mode(number: int) -> BbcMode:
    try:
        return MODE_PRESETS[number]
    except KeyError as exc:
        supported = ", ".join(str(mode) for mode in MODE_PRESETS)
        raise ValueError(
            f"BBC mode {number} is not a supported bitmap mode; choose {supported}"
        ) from exc


def validate_bitmap_geometry(width: int, height: int, bits_per_pixel: int) -> None:
    if bits_per_pixel not in (1, 2, 4):
        raise ValueError("bits per pixel must be one of 1, 2 or 4")
    if width <= 0 or height <= 0:
        raise ValueError("width and height must be positive")

    pixels_per_byte = 8 // bits_per_pixel
    if width % pixels_per_byte:
        raise ValueError(
            f"width {width} must be divisible by {pixels_per_byte} "
            f"for {bits_per_pixel}bpp output"
        )
    if height % 8:
        raise ValueError(
            f"height {height} must be divisible by 8 for BBC raster blocks"
        )
