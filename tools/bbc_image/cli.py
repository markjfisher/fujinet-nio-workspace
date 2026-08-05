from __future__ import annotations

import argparse
import sys
from pathlib import Path

from PIL import UnidentifiedImageError

from .converter import ConversionOptions, RESAMPLING, convert_image
from .dither import DITHER_CHOICES
from .geometry import compatible_dimensions
from .modes import MODE_PRESETS, get_mode
from .palettes import (
    PALETTES,
    default_palette_name,
    format_ca65_palette,
    get_palette,
    make_ula_palette_bytes,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="bbc-image",
        description=(
            "Scale and quantise an image, then encode it in BBC Micro bitmap "
            "screen-memory order."
        ),
    )
    parser.add_argument("input", type=Path, help="source image")
    parser.add_argument("output", type=Path, help="raw BBC screen-data output")

    format_group = parser.add_argument_group("BBC output format")
    format_group.add_argument(
        "--mode",
        type=int,
        choices=sorted(MODE_PRESETS),
        help=(
            "BBC bitmap mode preset. Supplies width and colour depth; a "
            "calculated partial-screen height is permitted."
        ),
    )
    format_group.add_argument(
        "-w",
        "--width",
        type=int,
        help="target pixel width; overrides the selected mode width",
    )
    format_group.add_argument(
        "--height",
        type=int,
        help=(
            "explicit target height. By default it is calculated exactly from "
            "the source aspect ratio and target width."
        ),
    )
    format_group.add_argument(
        "--bpp",
        type=int,
        choices=(1, 2, 4),
        help="bits per pixel; overrides the selected mode depth",
    )

    colour_group = parser.add_argument_group("colour reduction")
    colour_group.add_argument(
        "--palette",
        help=(
            "built-in palette name or comma-separated RRGGBB values. "
            f"Built-ins: {', '.join(sorted(PALETTES))}"
        ),
    )
    colour_group.add_argument(
        "-d",
        "--dither",
        choices=DITHER_CHOICES,
        default="none",
        help="colour-reduction algorithm; default: none",
    )
    colour_group.add_argument(
        "--dither-strength",
        type=float,
        default=1.0,
        help="ordered-dither perturbation strength; default: 1.0",
    )
    colour_group.add_argument(
        "--map-source-levels",
        action="store_true",
        help=(
            "map distinct source colours to logical indices by luminance rank "
            "instead of using nearest-colour matching"
        ),
    )

    image_group = parser.add_argument_group("image preparation")
    image_group.add_argument(
        "--resample",
        choices=tuple(RESAMPLING),
        default="lanczos",
        help="scaling filter; default: lanczos",
    )
    image_group.add_argument("--autocontrast", action="store_true")
    image_group.add_argument("--contrast", type=float, default=1.0)
    image_group.add_argument("--brightness", type=float, default=1.0)
    image_group.add_argument("--invert", action="store_true")

    output_group = parser.add_argument_group("additional output")
    output_group.add_argument(
        "--preview",
        type=Path,
        help="write an indexed PNG preview of the exact logical pixels",
    )
    output_group.add_argument(
        "--ula-palette",
        type=Path,
        help="write a 16-byte BBC Video ULA palette table",
    )
    output_group.add_argument(
        "--ula-palette-asm",
        type=Path,
        help="write the Video ULA table as ca65 source",
    )

    return parser


def resolve_format(args: argparse.Namespace) -> tuple[int, int]:
    mode = get_mode(args.mode) if args.mode is not None else None

    width = args.width if args.width is not None else (mode.width if mode else 160)
    bpp = (
        args.bpp
        if args.bpp is not None
        else (mode.bits_per_pixel if mode else 2)
    )
    return width, bpp


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    width, bpp = resolve_format(args)

    palette_name = args.palette or default_palette_name(bpp)

    try:
        palette = get_palette(palette_name, bpp)
        result = convert_image(
            args.input,
            ConversionOptions(
                target_width=width,
                target_height=args.height,
                bits_per_pixel=bpp,
                palette=palette,
                dither=args.dither,
                ordered_strength=args.dither_strength,
                resample=args.resample,
                autocontrast=args.autocontrast,
                contrast=args.contrast,
                brightness=args.brightness,
                invert=args.invert,
                map_source_levels=args.map_source_levels,
            ),
        )
    except FileNotFoundError:
        print(f"error: input file not found: {args.input}", file=sys.stderr)
        return 1
    except (OSError, UnidentifiedImageError, ValueError) as error:
        print(f"error: {error}", file=sys.stderr)

        # Offer useful dimensions when the aspect-ratio or raster-block checks
        # reject the requested width.
        try:
            from PIL import Image

            with Image.open(args.input) as source:
                nearby = compatible_dimensions(
                    source.width,
                    source.height,
                    width,
                    bpp,
                )
            if nearby:
                suggestions = ", ".join(f"{w}x{h}" for w, h in nearby)
                print(
                    f"nearby exact BBC-compatible dimensions: {suggestions}",
                    file=sys.stderr,
                )
        except Exception:
            pass
        return 1

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(result.raw_data)

    if args.preview:
        args.preview.parent.mkdir(parents=True, exist_ok=True)
        result.preview.save(args.preview, format="PNG", optimize=False)

    try:
        ula_values = None
        if args.ula_palette or args.ula_palette_asm:
            ula_values = make_ula_palette_bytes(result.palette, bpp)

        if args.ula_palette:
            args.ula_palette.parent.mkdir(parents=True, exist_ok=True)
            args.ula_palette.write_bytes(ula_values or b"")

        if args.ula_palette_asm:
            args.ula_palette_asm.parent.mkdir(parents=True, exist_ok=True)
            args.ula_palette_asm.write_text(
                format_ca65_palette(ula_values or b""),
                encoding="utf-8",
            )
    except ValueError as error:
        print(f"error: {error}", file=sys.stderr)
        return 1

    geometry = result.geometry
    print(f"Input:           {args.input}")
    print(f"Output:          {geometry.width}x{geometry.height}")
    print(f"Depth:           {geometry.bits_per_pixel} bpp")
    print(f"Logical colours: {geometry.colours}")
    print(f"Palette:         {result.palette.name}")
    print(f"Dithering:       {args.dither}")
    print(f"Character rows:  {geometry.character_rows}")
    print(f"Raw bytes:       {len(result.raw_data)}")
    print(f"Wrote:           {args.output}")
    if args.preview:
        print(f"Preview:         {args.preview}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
