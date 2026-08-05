# BBC image converter

A reusable Python module and CLI for converting ordinary images into raw BBC
Micro bitmap screen-memory data.

It supports the bitmap formats used by Modes 0, 1, 2, 4 and 5, including
shortened custom screens whose height is a multiple of eight raster lines.

## Requirements

Python 3.10 or newer and Pillow:

```bash
uv run --with Pillow python -m tools.bbc_image.cli --help
```

or install Pillow into the current environment:

```bash
python -m pip install Pillow
```

## Examples

Create the current 160x96 four-colour Mode 5 splash data:

```bash
uv run --with Pillow python -m tools.bbc_image.cli \
    source.png SCREEN \
    --mode 5 \
    --palette mode5 \
    --dither none \
    --preview preview.png \
    --ula-palette-asm palette.inc
```

Create a black/white ordered-dithered partial Mode 4 image. The output height
is calculated from the source aspect ratio:

```bash
uv run --with Pillow python -m tools.bbc_image.cli \
    source.png SCREEN \
    --mode 4 \
    --width 320 \
    --palette mono \
    --dither bayer4 \
    --preview preview.png
```

Use a custom four-colour RGB palette:

```bash
uv run --with Pillow python -m tools.bbc_image.cli \
    source.png SCREEN \
    --width 160 \
    --bpp 2 \
    --palette 000000,0055ff,ffcc00,ffffff \
    --dither floyd-steinberg \
    --preview preview.png
```

A custom RGB palette can produce raw logical pixel data and a preview, but it
cannot generate a Video ULA table unless those colours correspond to BBC
physical colours. Use a built-in palette when requesting `--ula-palette` or
`--ula-palette-asm`.

## Geometry rules

The target width must contain a whole number of bytes:

- 1bpp: width divisible by 8
- 2bpp: width divisible by 4
- 4bpp: width divisible by 2

The target height must be divisible by 8 because BBC bitmap memory is arranged
in eight-raster-line character rows.

When `--height` is omitted, the converter preserves the source aspect ratio
exactly. It rejects fractional target heights rather than silently rounding
them and suggests nearby compatible dimensions when possible.

## Output format

The raw file is arranged exactly as BBC bitmap screen memory:

```text
character row
    byte column
        raster line 0..7
```

Pixels within each byte use the BBC Video ULA's interleaved bit-plane layout.

The module can also be imported:

```python
from pathlib import Path

from tools.bbc_image.converter import ConversionOptions, convert_image
from tools.bbc_image.palettes import get_palette

result = convert_image(
    Path("source.png"),
    ConversionOptions(
        target_width=160,
        bits_per_pixel=2,
        palette=get_palette("mode5", 2),
        dither="none",
    ),
)

Path("SCREEN").write_bytes(result.raw_data)
result.preview.save("preview.png")
```

## Tests

From the repository root:

```bash
python -m unittest discover -s tools/bbc_image/tests
```
