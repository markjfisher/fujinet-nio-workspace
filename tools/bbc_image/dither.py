from __future__ import annotations

from collections.abc import Sequence

from PIL import Image

from .palettes import Palette, RGB


BAYER_2X2 = (
    (0, 2),
    (3, 1),
)

BAYER_4X4 = (
    (0, 8, 2, 10),
    (12, 4, 14, 6),
    (3, 11, 1, 9),
    (15, 7, 13, 5),
)

BAYER_8X8 = (
    (0, 32, 8, 40, 2, 34, 10, 42),
    (48, 16, 56, 24, 50, 18, 58, 26),
    (12, 44, 4, 36, 14, 46, 6, 38),
    (60, 28, 52, 20, 62, 30, 54, 22),
    (3, 35, 11, 43, 1, 33, 9, 41),
    (51, 19, 59, 27, 49, 17, 57, 25),
    (15, 47, 7, 39, 13, 45, 5, 37),
    (63, 31, 55, 23, 61, 29, 53, 21),
)

DITHER_CHOICES = (
    "none",
    "bayer2",
    "bayer4",
    "bayer8",
    "floyd-steinberg",
)


def colour_distance(left: RGB, right: RGB) -> int:
    """Weighted squared RGB distance, biased towards human luminance."""
    red = left[0] - right[0]
    green = left[1] - right[1]
    blue = left[2] - right[2]
    return 30 * red * red + 59 * green * green + 11 * blue * blue


def nearest_palette_index(colour: RGB, palette: Sequence[RGB]) -> int:
    return min(
        range(len(palette)),
        key=lambda index: colour_distance(colour, palette[index]),
    )


def nearest_quantise(image: Image.Image, palette: Palette) -> list[int]:
    rgb = image.convert("RGB")
    return [
        nearest_palette_index(pixel, palette.colours)
        for pixel in rgb.getdata()
    ]


def ordered_quantise(
    image: Image.Image,
    palette: Palette,
    matrix: tuple[tuple[int, ...], ...],
    *,
    strength: float = 1.0,
) -> list[int]:
    """Ordered dither by perturbing RGB before nearest-palette matching."""
    rgb = image.convert("RGB")
    width, height = rgb.size
    pixels = rgb.load()
    matrix_height = len(matrix)
    matrix_width = len(matrix[0])
    levels = matrix_height * matrix_width
    result: list[int] = []

    for y in range(height):
        for x in range(width):
            threshold = (matrix[y % matrix_height][x % matrix_width] + 0.5) / levels
            offset = int((threshold - 0.5) * 255 * strength)
            source = pixels[x, y]
            adjusted = (
                max(0, min(255, source[0] + offset)),
                max(0, min(255, source[1] + offset)),
                max(0, min(255, source[2] + offset)),
            )
            result.append(nearest_palette_index(adjusted, palette.colours))
    return result


def floyd_steinberg_quantise(image: Image.Image, palette: Palette) -> list[int]:
    rgb = image.convert("RGB")
    width, height = rgb.size
    source = [
        [list(rgb.getpixel((x, y))) for x in range(width)]
        for y in range(height)
    ]
    result = [0] * (width * height)

    def add_error(x: int, y: int, error: tuple[float, float, float], factor: float) -> None:
        if not (0 <= x < width and 0 <= y < height):
            return
        pixel = source[y][x]
        for channel in range(3):
            pixel[channel] = max(0.0, min(255.0, pixel[channel] + error[channel] * factor))

    for y in range(height):
        for x in range(width):
            old = tuple(int(round(value)) for value in source[y][x])
            index = nearest_palette_index(old, palette.colours)
            result[y * width + x] = index
            new = palette.colours[index]
            error = (
                old[0] - new[0],
                old[1] - new[1],
                old[2] - new[2],
            )
            add_error(x + 1, y, error, 7 / 16)
            add_error(x - 1, y + 1, error, 3 / 16)
            add_error(x, y + 1, error, 5 / 16)
            add_error(x + 1, y + 1, error, 1 / 16)

    return result


def quantise(
    image: Image.Image,
    palette: Palette,
    algorithm: str,
    *,
    ordered_strength: float = 1.0,
) -> list[int]:
    if algorithm == "none":
        return nearest_quantise(image, palette)
    if algorithm == "bayer2":
        return ordered_quantise(
            image, palette, BAYER_2X2, strength=ordered_strength
        )
    if algorithm == "bayer4":
        return ordered_quantise(
            image, palette, BAYER_4X4, strength=ordered_strength
        )
    if algorithm == "bayer8":
        return ordered_quantise(
            image, palette, BAYER_8X8, strength=ordered_strength
        )
    if algorithm == "floyd-steinberg":
        return floyd_steinberg_quantise(image, palette)
    raise ValueError(f"unknown dithering algorithm {algorithm!r}")
