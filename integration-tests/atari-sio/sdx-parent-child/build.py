#!/usr/bin/env python3
"""Build disposable SDX parent/child ownership experiment (no SDX media)."""
import argparse
import re
import struct
import subprocess
import sys
from pathlib import Path
import tempfile
from allocation import reservation

p = argparse.ArgumentParser()
p.add_argument('output', type=Path)
p.add_argument('--resident-build', type=Path, help='build experimental actual resident loader fixture')
p.add_argument('--fault', choices=('missing-child', 'bad-magic', 'wrong-size', 'oom'), help='test-only failure fixture')
a = p.parse_args()
here = Path(__file__).resolve().parent
with tempfile.TemporaryDirectory(prefix='sdx-parent-child-') as temp:
    tmp = Path(temp)
    raw, labels = tmp/'parent.xex', tmp/'parent.lbl'
    defines = []
    if a.fault and not a.resident_build:
        raise SystemExit('--fault requires --resident-build')
    if a.resident_build:
        module = (a.resident_build/'nio.o65').read_bytes()
        alloc, allocated = reservation(module)
        defines = ['--asm-define', 'SDX_RESIDENT_PROTOTYPE=1', '--asm-define', f'PARENT_ALLOC={0xffff if a.fault == "oom" else allocated}']
    subprocess.run(['cl65', '-t', 'none', *defines, '-C', str(here/'parent.cfg'), '-Ln', str(labels),
                    '-o', str(raw), str(here/'parent.s')], check=True)
    syms = {name: int(address, 16) for address, name in re.findall(
        r'^al ([0-9A-Fa-f]+) \.(\w+_ref)$', labels.read_text(), re.M)}
    names = [('MALLOC', 'malloc_ref'), ('INSTALL', 'install_ref'),
             ('U_LOAD', 'uload_ref'), ('FILE_P', 'file_ref'), ('FLAG', 'flag_ref')]
    if set(syms) != {name for _, name in names}:
        raise SystemExit('missing symbols')
    binary = raw.read_bytes()
    start, end = struct.unpack_from('<HH', binary, 2)
    pos = 6 + end - start + 1
    if binary[:2] != b'\xff\xff' or start != 0x400 or binary[pos:pos+4] != b'\xe2\x02\xe3\x02' or pos + 6 != len(binary):
        raise SystemExit('unexpected parent XEX')
    refs = bytearray()
    for symbol, name in names:
        refs += b'\xfb\xff' + symbol.ljust(8).encode('ascii') + b'\x04\x00\xfd' + struct.pack('<H', syms[name]) + b'\xfc'
    parent = b'\xfa\xff' + binary[2:pos] + refs + b'\xfa\xff\xe0\x02\xe1\x02' + binary[pos+4:pos+6]
    if a.resident_build:
        root = here.parents[2]
        obj, module_path = tmp/'child.o', tmp/'child.o65'
        source = root/'repos/nio-core-apps/apps/platform/atari/resident/fnresident_o65_loader.s'
        subprocess.run(['ca65', '-D', 'DISK_SOURCE=1', '-D', 'ASM_RESIDENT=1', '-D', 'SDX_CHILD=1',
                        '-D', f'SDX_EXPECTED_ALLOC={alloc}', '-o', str(obj), str(source)], check=True)
        subprocess.run(['ld65', '-C', str(here/'child.cfg'), '-o', str(module_path), str(obj)], check=True)
        sys.path.insert(0, str(here.parent/'resident-relocation'))
        from verify_o65_api_closure import parse_reloc
        blob = module_path.read_bytes()
        if blob[:6] != b'\x01\x00o65\x00' or struct.unpack_from('<H', blob, 8)[0] != 0:
            raise ValueError('unexpected child o65 header')
        text_len, data_len, bss_len = (struct.unpack_from('<H', blob, x)[0] for x in (10, 14, 18))
        if data_len or bss_len:
            raise ValueError('child must use one initialized code segment')
        pos = 26
        while blob[pos]:
            pos += blob[pos]
        pos += 1
        text = blob[pos:pos+text_len]
        pos += text_len
        if struct.unpack_from('<H', blob, pos)[0]:
            raise ValueError('child has imports')
        pos += 2
        records, pos = parse_reloc(blob, pos, text_len)
        empty_data, pos = parse_reloc(blob, pos, 0)
        if empty_data or blob[pos:] != b'\x00\x00':
            raise ValueError('unexpected child exports or trailing data')
        fixups = bytearray((0xfe, 1))
        previous = 0
        for offset, kind, segment, _ in records:
            if kind != 0x80 or segment != 2 or offset < previous:
                raise ValueError('unsupported child relocation')
            delta = offset - previous
            while delta >= 0xfb:
                fixups.append(0xff)
                delta -= 250
            fixups.append(delta)
            previous = offset
        fixups.append(0xfc)
        child = (b'\xfe\xff\x01\x00\x00\x00' + struct.pack('<H', text_len) + text +
                 b'\xfd\xff\x01' + struct.pack('<H', len(fixups)) + fixups)
    else:
        # Position-independent child records its live MEMLO in scratch and returns.
        child_code = bytes.fromhex('ad e7 02 8d ac 06 ad e8 02 8d ad 06 a9 43 8d ae 06 60')
        child = b'\xfe\xff\x01\x00\x00\x00\x00\x10' + child_code + bytes(0x1000 - len(child_code))
    stage = tmp/'stage'
    stage.mkdir()
    (stage/'PARENT.COM').write_bytes(parent)
    if a.fault != 'missing-child':
        (stage/'CHILD.COM').write_bytes(child)
    if a.resident_build:
        for name in ('nio.o65', 'fnread.bas', 'fnwrite.bas', 'fnpost.bas'):
            data = (a.resident_build/name).read_bytes()
            if name == 'nio.o65' and a.fault == 'bad-magic':
                data = data[:22] + bytes((data[22] ^ 0xff,)) + data[23:]
            if name == 'nio.o65' and a.fault == 'wrong-size':
                data = data[:14] + struct.pack('<H', alloc + 1) + data[16:]
            (stage/name.upper()).write_bytes(data)
    result = tmp/'fixture.atr'
    subprocess.run(['dir2atr', '-m', '-S', str(result), str(stage)], check=True)
    if a.output.exists():
        raise SystemExit('output already exists')
    a.output.parent.mkdir(parents=True, exist_ok=True)
    a.output.write_bytes(result.read_bytes())
