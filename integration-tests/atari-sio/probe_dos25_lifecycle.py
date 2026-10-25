#!/usr/bin/env python3
"""Observe DOS 2.5 startup, DUP and RESET in an isolated local-disk emulator."""
import argparse
import hashlib
import json
import shutil
from pathlib import Path
import run_boot_acceptance as a

parser = argparse.ArgumentParser()
parser.add_argument('atr', type=Path)
parser.add_argument('evidence', type=Path, help='new directory for this run')
mode = parser.add_mutually_exclusive_group()
mode.add_argument('--clean', action='store_true')
mode.add_argument('--reset-only', action='store_true', help='reset directly from installed BASIC')
args = parser.parse_args()
args.evidence.mkdir(parents=True, exist_ok=False)
disk = args.evidence / 'disposable.atr'
shutil.copyfile(args.atr, disk)
before = set(Path('/tmp').glob('altirra-bridge-*.token'))
cmd, env, temps = a.altirra_command(True, basic=True)
cmd[cmd.index(str(a.ATR))] = str(disk.resolve())
with (args.evidence / 'altirra.log').open('wb') as log:
    process = a.launch(cmd, env=env, stdout=log, stderr=-2)
    try:
        import sys
        sys.path.insert(0, str(a.SDK))
        from altirra_bridge import AltirraBridge
        with AltirraBridge.from_token_file(a.fresh_token(before)) as bridge:
            bridge.resume()
            ready = bytes((0x32, 0x25, 0x21, 0x24, 0x39))
            def screen():
                return bridge.peek(bridge.peek16(0x58), 960)
            def wait_screen(pattern, *, changed_from=None, steps=120):
                for _ in range(steps):
                    bridge.frame(30)
                    current = screen()
                    if pattern in current and (changed_from is None or current != changed_from):
                        return True
                return False
            if not wait_screen(ready):
                raise RuntimeError('BASIC READY was not reached')
            install = bridge.peek(0x9380, 40)
            if not args.clean and (install[:5] != b'NRI!\x02' or install[5] != 0):
                raise RuntimeError('resident installer did not report success')
            start, end = (a._u16(install, 12), a._u16(install, 14)) if not args.clean else (0, 0)
            if not args.clean:
                hatabs = bridge.peek(a.HATABS_ADDR, a.HATABS_TOTAL_BYTES)
                entries = [i for i in range(0, a.HATABS_ENTRY_BYTES, 3) if hatabs[i] == ord('N')]
                if (not 0 < start < end <= bridge.peek16(0x2e5) or end - start > 3072
                        or bridge.peek16(0x2e7) != end or len(entries) != 1
                        or not start <= a._u16(hatabs, entries[0] + 1) < end):
                    raise RuntimeError('invalid resident range, MEMLO or N: HATABS registration')
            def snapshot(label):
                raw = bridge.memdump(start, end-start) if end > start else None
                state = {'ready_on_screen': ready in screen(), 'memlo': bridge.peek16(0x2e7),
                         'hatabs': bridge.peek(a.HATABS_ADDR, 35).hex(),
                         'resident_range': [start, end], 'registers': bridge.regs(),
                         'resident_sha256': hashlib.sha256(raw).hexdigest() if raw is not None else None,
                         'screen': screen().hex()}
                if raw is not None:
                    (args.evidence / f'{label}.resident.bin').write_bytes(raw)
                (args.evidence / f'{label}.json').write_text(json.dumps(state, indent=2) + '\n')
                (args.evidence / f'{label}.png').write_bytes(bridge.screenshot())
            snapshot('boot')
            if not args.clean:
                if not args.reset_only:
                    a._type_atari_command(bridge, 'DOS')
                    menu = bytes(c - 32 for c in b'SELECT ITEM')
                    if not wait_screen(menu):
                        raise RuntimeError('DUP menu was not reached')
                    menu_screen = screen()
                    if ready in menu_screen:
                        raise RuntimeError('DUP screen still contains READY; cannot prove new prompt')
                    snapshot('dup')
                    a._type_atari_command(bridge, 'B')
                    if not wait_screen(ready, changed_from=menu_screen):
                        raise RuntimeError('BASIC did not return from DUP')
                    snapshot('return')
                    # Isolated experiment only: no NetSIO service is attached.
                    a._type_atari_command(bridge, 'OPEN #1,4,0,"N:TEST"')
                    for _ in range(20):
                        bridge.frame(30)
                    snapshot('n-attempt')
                bridge.warm_reset()
                for _ in range(120):
                    bridge.frame(30)
                    hatabs = bridge.peek(a.HATABS_ADDR, a.HATABS_TOTAL_BYTES)
                    if (bridge.peek16(0x2e7) != end and
                            not any(hatabs[i] == ord('N') for i in range(0, a.HATABS_ENTRY_BYTES, 3)) and
                            ready in screen()):
                        break
                else:
                    snapshot('reset-failed')
                    raise RuntimeError('BASIC READY and cleared registration were not reached after RESET')
                snapshot('reset')
    finally:
        a.stop([process])
        a.cleanup_temps(temps)
