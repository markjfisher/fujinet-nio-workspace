from __future__ import annotations

from dataclasses import dataclass

from .modes import validate_bitmap_geometry


@dataclass(frozen=True)
class OutputGeometry:
    width: int
    height: int
    bits_per_pixel: int

    @property
    def colours(self) -> int:
        return 1 << self.bits_per_pixel

    @property
    def pixels_per_byte(self) -> int:
        return 8 // self.bits_per_pixel

    @property
    def bytes_per_scanline(self) -> int:
        return self.width // self.pixels_per_byte

    @property
    def character_rows(self) -> int:
        return self.height // 8

    @property
    def byte_size(self) -> int:
        return self.bytes_per_scanline * self.height


def calculate_scaled_height(
    source_width: int,
    source_height: int,
    target_width: int,
) -> int:
    """Return the exact aspect-ratio-preserving output height.

    A fractional result is rejected rather than silently rounded, because a
    rounded image no longer preserves the source aspect ratio exactly.
    """
    if source_width <= 0 or source_height <= 0 or target_width <= 0:
        raise ValueError("source and target dimensions must be positive")

    numerator = source_height * target_width
    quotient, remainder = divmod(numerator, source_width)
    if remainder:
        exact = numerator / source_width
        raise ValueError(
            f"scaling {source_width}x{source_height} to width {target_width} "
            f"produces fractional height {exact:.6f}"
        )
    return quotient


def resolve_geometry(
    *,
    source_width: int,
    source_height: int,
    target_width: int,
    bits_per_pixel: int,
    target_height: int | None = None,
) -> OutputGeometry:
    height = (
        target_height
        if target_height is not None
        else calculate_scaled_height(source_width, source_height, target_width)
    )
    validate_bitmap_geometry(target_width, height, bits_per_pixel)
    return OutputGeometry(target_width, height, bits_per_pixel)


def compatible_dimensions(
    source_width: int,
    source_height: int,
    requested_width: int,
    bits_per_pixel: int,
    *,
    radius: int = 256,
    limit: int = 8,
) -> list[tuple[int, int]]:
    """Find nearby exact-aspect BBC-compatible dimensions."""
    pixels_per_byte = 8 // bits_per_pixel
    matches: list[tuple[int, int]] = []

    first = max(pixels_per_byte, requested_width - radius)
    last = requested_width + radius

    for width in range(first, last + 1):
        if width % pixels_per_byte:
            continue
        numerator = source_height * width
        if numerator % source_width:
            continue
        height = numerator // source_width
        if height > 0 and height % 8 == 0:
            matches.append((width, height))

    matches.sort(key=lambda item: (abs(item[0] - requested_width), item[0]))
    return matches[:limit]
