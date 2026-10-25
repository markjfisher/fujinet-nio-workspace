#!/usr/bin/env python3
"""Measure SDX parent allocation and relocatable child's lifetime."""
import argparse
import hashlib
import json
import shutil
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import run_boot_acceptance as a

p = argparse.ArgumentParser()
p.add_argument('cart', type=Path)
p.add_argument('disk', type=Path)
p.add_argument('evidence', type=Path)
args = p.parse_args()
if hashlib.sha256(args.cart.read_bytes()).hexdigest() != 'e400cba0ba7e20dc62c60019ab99de04d11f4a4fa841e20cacca7c44099940a3':
    raise SystemExit('cartridge checksum mismatch')
args.evidence.mkdir(parents=True, exist_ok=False)
disk = args.evidence/'disk.atr'
shutil.copyfile(args.disk, disk)
before = set(Path('/tmp').glob('altirra-bridge-*.token'))
cmd, env, temps = a.altirra_command(True, basic=True)
cmd[cmd.index(str(a.ATR))] = str(disk.resolve())
cmd += ['--cart', str(args.cart.resolve())]
with (args.evidence/'altirra.log').open('wb') as log:
    process = a.launch(cmd, env=env, stdout=log, stderr=-2)
    try:
        sys.path.insert(0, str(a.SDK))
        from altirra_bridge import AltirraBridge
        with AltirraBridge.from_token_file(a.fresh_token(before)) as b:
            b.resume()
            prompt = bytes.fromhex('24111a')
            screen = lambda: b.peek(b.peek16(0x58), 960)
            for _ in range(120):
                b.frame(30)
                if prompt in screen():
                    break
            else:
                raise RuntimeError('SDX prompt missing')
            baseline = {'memlo': b.peek16(0x2e7), 'hatabs': b.peek(a.HATABS_ADDR, 35).hex()}
            a._type_atari_command(b, 'PARENT')
            for _ in range(120):
                b.frame(30)
                if b.peek(0x6a0, 4) == b'PROK' and screen().count(prompt) >= 2:
                    break
            else:
                (args.evidence/'failure.png').write_bytes(b.screenshot())
                (args.evidence/'failure.bin').write_bytes(b.peek(0x6a0, 16))
                raise RuntimeError('parent did not return successfully')
            raw = b.peek(0x6a0, 16)
            base, after_parent, after_child = (a._u16(raw, 4), a._u16(raw, 6), a._u16(raw, 8))
            child_memlo = a._u16(raw, 12)
            state = {'baseline': baseline, 'trace': raw.hex(), 'allocation': base,
                     'parent_memlo': after_parent, 'child_memlo': child_memlo,
                     'post_child_memlo': after_child, 'dos_memlo': b.peek16(0x2e7),
                     'parent_marker': b.peek(base, 1).hex(), 'hatabs': b.peek(a.HATABS_ADDR, 35).hex()}
            (args.evidence/'result.json').write_text(json.dumps(state, indent=2)+'\n')
            (args.evidence/'result.png').write_bytes(b.screenshot())
            if (raw[14] != ord('C') or after_child != after_parent or child_memlo < after_parent + 0x1000
                    or b.memdump(base, 0x91f) != b'\xa5' * 0x91f or b.peek16(0x2e7) < base + 0x91f
                    or state['hatabs'] != baseline['hatabs']):
                raise RuntimeError('parent/child allocation ownership invariant failed')
            ready = bytes.fromhex('3225212439')
            a._type_atari_command(b, 'BASIC')
            for _ in range(120):
                b.frame(30)
                if ready in screen():
                    break
            else:
                raise RuntimeError('BASIC READY missing')
            if b.memdump(base, 0x91f) != b'\xa5' * 0x91f or b.peek16(0x2e7) < base + 0x91f:
                raise RuntimeError('BASIC damaged parent allocation')
            (args.evidence/'basic.png').write_bytes(b.screenshot())
            before_dos = screen().count(prompt)
            a._type_atari_command(b, 'DOS')
            for _ in range(120):
                b.frame(30)
                if screen().count(prompt) > before_dos:
                    break
            else:
                raise RuntimeError('DOS prompt missing after BASIC')
            if b.memdump(base, 0x91f) != b'\xa5' * 0x91f or b.peek16(0x2e7) < base + 0x91f:
                raise RuntimeError('DOS transition damaged parent allocation')
            if b.peek(a.HATABS_ADDR, 35).hex() != baseline['hatabs']:
                raise RuntimeError('transition damaged HATABS')
            (args.evidence/'dos-return.png').write_bytes(b.screenshot())
    finally:
        a.stop([process])
        a.cleanup_temps(temps)
