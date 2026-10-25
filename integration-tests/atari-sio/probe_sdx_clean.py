#!/usr/bin/env python3
"""Boot the unmodified local SDX cartridge and test its DIR command."""
import argparse
import hashlib
import json
import shutil
from pathlib import Path
import run_boot_acceptance as a

p = argparse.ArgumentParser()
p.add_argument('car', type=Path)
p.add_argument('disk', type=Path)
p.add_argument('evidence', type=Path, help='new directory; disk writes use a copy')
args = p.parse_args()
if hashlib.sha256(args.car.read_bytes()).hexdigest() != 'e400cba0ba7e20dc62c60019ab99de04d11f4a4fa841e20cacca7c44099940a3':
    raise SystemExit('SDX cartridge checksum mismatch')
args.evidence.mkdir(parents=True, exist_ok=False)
disk = args.evidence / 'disposable.atr'
shutil.copyfile(args.disk, disk)
before = set(Path('/tmp').glob('altirra-bridge-*.token'))
cmd, env, temps = a.altirra_command(True, basic=True)
cmd[cmd.index(str(a.ATR))] = str(disk.resolve())
cmd += ['--cart', str(args.car.resolve())]
with (args.evidence / 'altirra.log').open('wb') as log:
    process = a.launch(cmd, env=env, stdout=log, stderr=-2)
    try:
        import sys
        sys.path.insert(0, str(a.SDK))
        from altirra_bridge import AltirraBridge
        with AltirraBridge.from_token_file(a.fresh_token(before)) as bridge:
            bridge.resume()
            def screen():
                return bridge.peek(bridge.peek16(0x58), 960)
            def enc(s):
                return bytes(c - 32 if 32 <= c < 96 else c for c in s.encode('ascii'))
            def wait(pattern):
                for _ in range(120):
                    bridge.frame(30)
                    if enc(pattern) in screen():
                        return
                raise RuntimeError(f'{pattern!r} not found on screen')
            def snapshot(label):
                hatabs = bridge.peek(a.HATABS_ADDR, a.HATABS_TOTAL_BYTES)
                tables = {chr(hatabs[i]): bridge.peek(a._u16(hatabs, i+1), 12).hex()
                          for i in range(0, a.HATABS_ENTRY_BYTES, 3) if hatabs[i]}
                state = {'memlo': bridge.peek16(0x2e7), 'memtop': bridge.peek16(0x2e5), 'driver_tables': tables,
                         'hatabs': bridge.peek(a.HATABS_ADDR, a.HATABS_TOTAL_BYTES).hex(),
                         'screen': screen().hex(), 'registers': bridge.regs()}
                (args.evidence / f'{label}.json').write_text(json.dumps(state, indent=2) + '\n')
                (args.evidence / f'{label}.png').write_bytes(bridge.screenshot())
                (args.evidence / f'{label}.loader-window.bin').write_bytes(bridge.memdump(0x6000, 0x1000))
                (args.evidence / f'{label}.diagnostic-window.bin').write_bytes(bridge.memdump(0x9380, 40))
            wait('D1:')
            snapshot('boot')
            boot_hatabs = bridge.peek(a.HATABS_ADDR, a.HATABS_TOTAL_BYTES)
            boot_memlo = bridge.peek16(0x2e7)
            a._type_atari_command(bridge, 'DIR')
            wait('FNREAD')
            wait('NIO')
            wait('PARENT')
            wait('CHILD')
            for _ in range(120):
                bridge.frame(30)
                if screen().count(enc('D1:')) >= 2:
                    break
            else:
                raise RuntimeError('DIR did not return to the command prompt')
            snapshot('dir')
    finally:
        a.stop([process])
        a.cleanup_temps(temps)
