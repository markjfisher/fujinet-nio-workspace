#!/usr/bin/env python3
"""Build DOS 2.5 fixture disks from the pinned, locally provisioned ATR."""
import hashlib
import os
import sys
from pathlib import Path

SOURCE_SHA256 = 'c154f4d55330b2a5e197f21db07123835c877d5b8fae10694be811c3dd8bfa64'
FILES = [('fnresident-asm-disk-loader.xex', 'AUTORUN.SYS'),
         ('nio.o65', 'NIO.O65'), ('fnread.bas', 'FNREAD.BAS'),
         ('fnwrite.bas', 'FNWRITE.BAS'), ('fnpost.bas', 'FNPOST.BAS')]


def sector(image, number):
    return memoryview(image)[16 + (number - 1) * 128:16 + number * 128]


def add_file(image, name, data):
    directory = [sector(image, s) for s in range(361, 369)]
    entries = [d[i:i + 16] for d in directory for i in range(0, 128, 16)]
    stem, ext = name.split('.')
    encoded = (stem.ljust(8) + ext.ljust(3)).encode('ascii')
    if any(e[0] & 0x40 and bytes(e[5:16]) == encoded for e in entries):
        raise ValueError(f'{name} already exists')
    index = next((i for i, e in enumerate(entries) if not e[0] & 0x40), None)
    if index is None:
        raise ValueError('directory full')
    vtoc = sector(image, 360)
    free = [s for s in range(4, 720) if vtoc[10 + s // 8] & (0x80 >> (s % 8))]
    count = max(1, (len(data) + 124) // 125)
    if count > len(free):
        raise ValueError('disk full')
    chain = free[:count]
    for i, s in enumerate(chain):
        vtoc[10 + s // 8] &= ~(0x80 >> (s % 8))
        block = sector(image, s)
        chunk = data[i * 125:(i + 1) * 125]
        block[:] = bytes(128)
        block[:len(chunk)] = chunk
        nxt = chain[i + 1] if i + 1 < count else 0
        block[125] = (index << 2) | (nxt >> 8)
        block[126] = nxt & 255
        block[127] = len(chunk)
    remaining = int.from_bytes(vtoc[3:5], 'little') - count
    if remaining < 0:
        raise ValueError('invalid VTOC free count')
    vtoc[3:5] = remaining.to_bytes(2, 'little')
    entry = entries[index]
    entry[:] = bytes([0x42]) + count.to_bytes(2, 'little') + chain[0].to_bytes(2, 'little') + encoded


def aliases(a, b):
    return a.resolve() == b.resolve() or (a.exists() and b.exists() and os.path.samefile(a, b))


def validate_source(source):
    data = source.read_bytes()
    if hashlib.sha256(data).hexdigest() != SOURCE_SHA256:
        raise ValueError('DOS 2.5 source ATR SHA-256 does not match the recorded image')
    if len(data) != 16 + 720 * 128 or data[:2] != b'\x96\x02':
        raise ValueError('invalid single-density ATR')
    return data


def guard_aliases(protected, outputs):
    for i, output in enumerate(outputs):
        for other in protected + outputs[:i]:
            if aliases(output, other):
                raise ValueError(f'output {output} aliases {other}')


def preflight(source, out, outputs=(), protected=()):
    validate_source(source)
    guard_aliases([source, *protected], list(outputs))


def build_clean(source, out, protected=()):
    clean = out / 'dos25-clean.atr'
    preflight(source, out, [clean], protected)
    data = validate_source(source)
    out.mkdir(parents=True, exist_ok=True)
    clean.write_bytes(data)
    print(f'{clean}: {hashlib.sha256(data).hexdigest()}')


def build_resident(source, out, protected=()):
    clean = out / 'dos25-clean.atr'
    resident_path = out / 'dos25-resident.atr'
    inputs = [out / local for local, _ in FILES]
    preflight(source, out, [resident_path], [clean, *inputs, *protected])
    data = validate_source(clean)
    resident = bytearray(data)
    for local, name in FILES:
        add_file(resident, name, (out / local).read_bytes())
    resident_path.write_bytes(resident)
    print(f'{resident_path}: {hashlib.sha256(resident).hexdigest()}')


def build(source, out):
    """Build both images; useful for callers and synthetic tests."""
    inputs = [out / local for local, _ in FILES]
    preflight(source, out, [out / 'dos25-clean.atr', out / 'dos25-resident.atr'], inputs)
    build_clean(source, out, inputs)
    build_resident(source, out)


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('mode', choices=['preflight', 'clean', 'resident'])
    parser.add_argument('source', type=Path)
    parser.add_argument('out', type=Path)
    parser.add_argument('--output', action='append', default=[], type=Path)
    parser.add_argument('--protect', action='append', default=[], type=Path)
    args = parser.parse_args()
    try:
        if args.mode == 'preflight':
            preflight(args.source, args.out, args.output, args.protect)
        elif args.mode == 'clean':
            build_clean(args.source, args.out, args.protect)
        else:
            build_resident(args.source, args.out, args.protect)
    except (OSError, ValueError) as exc:
        raise SystemExit(str(exc))
