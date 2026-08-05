from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from PIL import Image, ImageEnhance, ImageOps

from .dither import quantise
from .encoder import encode_screen
from .geometry import OutputGeometry, resolve_geometry
from .palettes import Palette


RESAMPLING = {
    "nearest": Image.Resampling.NEAREST,
    "bilinear": Image.Resampling.BILINEAR,
    "bicubic": Image.Resampling.BICUBIC,
    "lanczos": Image.Resampling.LANCZOS,
}


@dataclass(frozen=True)
class ConversionOptions:
    target_width: int
    bits_per_pixel: int
    palette: Palette
    target_height: int | None = None
    dither: str = "none"
    ordered_strength: float = 1.0
    resample: str = "lanczos"
    autocontrast: bool = False
    contrast: float = 1.0
    brightness: float = 1.0
    invert: bool = False


@dataclass(frozen=True)
class ConversionResult:
    geometry: OutputGeometry
    palette: Palette
    indices: tuple[int, ...]
    raw_data: bytes
    preview: Image.Image


def make_indexed_preview(
    width: int,
    height: int,
    indices: list[int],
    palette: Palette,
) -> Image.Image:
    preview = Image.new("P", (width, height))
    table: list[int] = []
    for red, green, blue in palette.colours:
        table.extend((red, green, blue))
    table.extend([0] * (768 - len(table)))
    preview.putpalette(table)
    preview.putdata(indices)
    return preview


def convert_image(
    input_path: Path,
    options: ConversionOptions,
) -> ConversionResult:
    if options.resample not in RESAMPLING:
        raise ValueError(f"unknown resampling filter {options.resample!r}")
    if options.contrast <= 0 or options.brightness <= 0:
        raise ValueError("contrast and brightness must be greater than zero")
    if options.ordered_strength < 0:
        raise ValueError("ordered dither strength must not be negative")

    options.palette.validate_for_bpp(options.bits_per_pixel)

    with Image.open(input_path) as source:
        source.load()
        geometry = resolve_geometry(
            source_width=source.width,
            source_height=source.height,
            target_width=options.target_width,
            target_height=options.target_height,
            bits_per_pixel=options.bits_per_pixel,
        )
        working = source.convert("RGB").resize(
            (geometry.width, geometry.height),
            RESAMPLING[options.resample],
        )

    if options.autocontrast:
        working = ImageOps.autocontrast(working)
    if options.brightness != 1.0:
        working = ImageEnhance.Brightness(working).enhance(options.brightness)
    if options.contrast != 1.0:
        working = ImageEnhance.Contrast(working).enhance(options.contrast)
    if options.invert:
        working = ImageOps.invert(working)

    indices = quantise(
        working,
        options.palette,
        options.dither,
        ordered_strength=options.ordered_strength,
    )
    raw_data = encode_screen(indices, geometry)
    preview = make_indexed_preview(
        geometry.width,
        geometry.height,
        indices,
        options.palette,
    )
    return ConversionResult(
        geometry=geometry,
        palette=options.palette,
        indices=tuple(indices),
        raw_data=raw_data,
        preview=preview,
    )
