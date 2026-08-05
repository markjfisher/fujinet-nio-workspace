from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable


RGB = tuple[int, int, int]


BBC_PHYSICAL_RGB: tuple[RGB, ...] = (
    (0, 0, 0),        # 0 black
    (255, 0, 0),      # 1 red
    (0, 255, 0),      # 2 green
    (255, 255, 0),    # 3 yellow
    (0, 0, 255),      # 4 blue
    (255, 0, 255),    # 5 magenta
    (0, 255, 255),    # 6 cyan
    (255, 255, 255),  # 7 white
)

BBC_COLOUR_NAMES: dict[str, int] = {
    "black": 0,
    "red": 1,
    "green": 2,
    "yellow": 3,
    "blue": 4,
    "magenta": 5,
    "cyan": 6,
    "white": 7,
}

@dataclass(frozen=True)
class Palette:
    name: str
    colours: tuple[RGB, ...]
    physical_colours: tuple[int, ...] | None = None

    def validate_for_bpp(self, bits_per_pixel: int) -> None:
        required = 1 << bits_per_pixel
        if len(self.colours) != required:
            raise ValueError(
                f"palette {self.name!r} has {len(self.colours)} colours, "
                f"but {bits_per_pixel}bpp requires exactly {required}"
            )
        if self.physical_colours is not None:
            if len(self.physical_colours) != required:
                raise ValueError("physical-colour list does not match palette")
            if any(value not in range(8) for value in self.physical_colours):
                raise ValueError("BBC physical colours must be in the range 0..7")


PALETTES: dict[str, Palette] = {
    "mono": Palette(
        "mono",
        (BBC_PHYSICAL_RGB[0], BBC_PHYSICAL_RGB[7]),
        (0, 7),
    ),
    "mode1": Palette(
        "mode1",
        (
            BBC_PHYSICAL_RGB[0],
            BBC_PHYSICAL_RGB[1],
            BBC_PHYSICAL_RGB[3],
            BBC_PHYSICAL_RGB[7],
        ),
        (0, 1, 3, 7),
    ),
    "mode5": Palette(
        "mode5",
        (
            BBC_PHYSICAL_RGB[0],
            BBC_PHYSICAL_RGB[1],
            BBC_PHYSICAL_RGB[3],
            BBC_PHYSICAL_RGB[7],
        ),
        (0, 1, 3, 7),
    ),
    "bbc16": Palette(
        "bbc16",
        BBC_PHYSICAL_RGB + BBC_PHYSICAL_RGB,
        tuple(range(8)) + tuple(range(8)),
    ),
}


def default_palette_name(bits_per_pixel: int) -> str:
    return {1: "mono", 2: "mode5", 4: "bbc16"}[bits_per_pixel]


def parse_rgb(value: str) -> RGB:
    text = value.strip().removeprefix("#")
    if len(text) != 6:
        raise ValueError(f"invalid RGB colour {value!r}; expected RRGGBB")
    try:
        number = int(text, 16)
    except ValueError as exc:
        raise ValueError(f"invalid RGB colour {value!r}") from exc
    return ((number >> 16) & 0xFF, (number >> 8) & 0xFF, number & 0xFF)


def parse_custom_palette(specification: str) -> Palette:
    rgb_colours: list[RGB] = []
    physical_colours: list[int] = []
    all_bbc_physical = True

    for token in specification.split(","):
        item = token.strip().lower()
        if not item:
            continue

        if item in BBC_COLOUR_NAMES:
            physical = BBC_COLOUR_NAMES[item]
            rgb_colours.append(BBC_PHYSICAL_RGB[physical])
            physical_colours.append(physical)
            continue

        colour = parse_rgb(item)
        rgb_colours.append(colour)

        try:
            physical = BBC_PHYSICAL_RGB.index(colour)
        except ValueError:
            all_bbc_physical = False
        else:
            physical_colours.append(physical)

    if not rgb_colours:
        raise ValueError("custom palette is empty")

    return Palette(
        "custom",
        tuple(rgb_colours),
        tuple(physical_colours) if all_bbc_physical else None,
    )

def get_palette(name_or_specification: str, bits_per_pixel: int) -> Palette:
    if "," in name_or_specification or name_or_specification.startswith("#"):
        palette = parse_custom_palette(name_or_specification)
    else:
        try:
            palette = PALETTES[name_or_specification]
        except KeyError as exc:
            choices = ", ".join(sorted(PALETTES))
            raise ValueError(
                f"unknown palette {name_or_specification!r}; "
                f"choose {choices}, or provide comma-separated RRGGBB values"
            ) from exc

    palette.validate_for_bpp(bits_per_pixel)
    return palette


def ula_logical_colour(palette_index: int, bits_per_pixel: int) -> int:
    """Return the logical colour selected by one ULA palette RAM index."""
    if not 0 <= palette_index <= 15:
        raise ValueError("ULA palette index must be 0..15")
    if bits_per_pixel == 1:
        return (palette_index >> 3) & 1
    if bits_per_pixel == 2:
        return (((palette_index >> 3) & 1) << 1) | ((palette_index >> 1) & 1)
    if bits_per_pixel == 4:
        return palette_index
    raise ValueError("bits per pixel must be 1, 2 or 4")


def make_ula_palette_bytes(palette: Palette, bits_per_pixel: int) -> bytes:
    """Create the 16 Video ULA palette programming bytes.

    This is only possible when every logical colour has an associated BBC
    physical colour number.
    """
    palette.validate_for_bpp(bits_per_pixel)
    if palette.physical_colours is None:
        raise ValueError(
            "a custom RGB palette cannot be represented by the BBC Video ULA; "
            "use one of the built-in BBC palettes"
        )

    values = bytearray()
    for palette_index in range(16):
        logical = ula_logical_colour(palette_index, bits_per_pixel)
        physical = palette.physical_colours[logical]
        values.append((palette_index << 4) | (physical ^ 7))
    return bytes(values)


def format_ca65_palette(values: bytes, label: str = "palette_values") -> str:
    if len(values) != 16:
        raise ValueError("a BBC ULA palette table must contain 16 bytes")
    lines = [f"{label}:"]
    for offset in range(0, 16, 4):
        group = ", ".join(f"${value:02X}" for value in values[offset:offset + 4])
        lines.append(f"        .byte {group}")
    return "\n".join(lines) + "\n"
