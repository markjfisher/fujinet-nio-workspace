#!/usr/bin/env python3
"""Check parent/child installer failure and repeat behavior in SDX."""
import argparse
import hashlib
import json
import shutil
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import run_boot_acceptance as a
p=argparse.ArgumentParser()
p.add_argument('cart',type=Path); p.add_argument('disk',type=Path); p.add_argument('evidence',type=Path)
p.add_argument('--case',choices=['oom','missing-child','bad-magic','wrong-size','no-slot','repeat','repeat-missing'],required=True)
args=p.parse_args()
if hashlib.sha256(args.cart.read_bytes()).hexdigest() != 'e400cba0ba7e20dc62c60019ab99de04d11f4a4fa841e20cacca7c44099940a3':
    raise SystemExit('cartridge checksum mismatch')
args.evidence.mkdir(parents=True,exist_ok=False)
disk=args.evidence/'disk.atr'; shutil.copyfile(args.disk,disk)
before=set(Path('/tmp').glob('altirra-bridge-*.token'))
cmd,env,temps=a.altirra_command(True,basic=True);cmd[cmd.index(str(a.ATR))]=str(disk.resolve());cmd+=['--cart',str(args.cart.resolve())]
with (args.evidence/'altirra.log').open('wb') as log:
    process=a.launch(cmd,env=env,stdout=log,stderr=-2)
    try:
        sys.path.insert(0,str(a.SDK));from altirra_bridge import AltirraBridge
        with AltirraBridge.from_token_file(a.fresh_token(before)) as b:
            b.resume();prompt=bytes.fromhex('24111a');screen=lambda:b.peek(b.peek16(0x58),960)
            def wait_prompt(count):
                for _ in range(120):
                    b.frame(30)
                    if screen().count(prompt)>=count:
                        return
                (args.evidence/'timeout.png').write_bytes(b.screenshot())
                raise RuntimeError('SDX prompt not reached')
            wait_prompt(1)
            boot_memlo=b.peek16(0x2e7);boot_hatabs=b.peek(a.HATABS_ADDR,35)
            if args.case=='no-slot':
                for index in range(0, a.HATABS_ENTRY_BYTES, 3):
                    if not boot_hatabs[index]:
                        for offset, value in enumerate((ord('Z'), boot_hatabs[16], boot_hatabs[17])):
                            b.poke(a.HATABS_ADDR + index + offset, value)
                boot_hatabs=b.peek(a.HATABS_ADDR,35)
            a._type_atari_command(b,'PARENT');wait_prompt(2)
            first=b.peek(0x6b0,40);first_memlo=b.peek16(0x2e7);first_hatabs=b.peek(a.HATABS_ADDR,35)
            if args.case in ('repeat','repeat-missing'):
                if first[:6]!=b'NRI!\x02\x00':raise RuntimeError('initial install failed')
                start,end=a._u16(first,12),a._u16(first,14)
                resident=b.memdump(start,end-start)
                if args.case == 'repeat-missing':
                    a._type_atari_command(b,'RENAME CHILD.COM CHILD.BAK');wait_prompt(3)
                a._type_atari_command(b,'PARENT');wait_prompt(4 if args.case == 'repeat-missing' else 3)
                second=b.peek(0x6b0,40)
                expected = bytes(6) if args.case == 'repeat-missing' else b'NRI!\x02\x01'
                if (second[:6]!=expected or b.peek16(0x2e7)!=first_memlo or
                    b.peek(a.HATABS_ADDR,35)!=first_hatabs or b.memdump(start,end-start)!=resident):
                    raise RuntimeError('repeat install changed resident allocation or HATABS')
                (args.evidence/'repeat-screen.bin').write_bytes(screen())
                (args.evidence/'repeat-result.bin').write_bytes(b.peek(0x6a0,80))
                if args.case == 'repeat-missing' and (b.peek(0x6a0,1)!=b'F' or bytes(c-32 if 32 <= c < 96 else c for c in b'170 File not found') not in screen()):
                    raise RuntimeError('missing child did not report visible failure')
            else:
                second=b''
                if first_memlo!=boot_memlo or first_hatabs!=boot_hatabs:
                    raise RuntimeError('failed install did not restore MEMLO and HATABS')
                if args.case=='no-slot' and first[:6]!=b'NRI!\x02\x05':
                    raise RuntimeError('child did not report full HATABS')
                if args.case in ('oom', 'bad-magic') and bytes(c-32 if 32 <= c < 96 else c for c in b'N: INSTALL FAILED') not in screen():
                    raise RuntimeError('installer did not report visible failure')
                if args.case == 'missing-child' and bytes(c-32 if 32 <= c < 96 else c for c in b'170 File not found') not in screen():
                    raise RuntimeError('SDX did not report missing child')
                if args.case in ('oom','missing-child') and b.peek(0x6a0,1)!=b'F':
                    raise RuntimeError('parent allocator did not report failure')
                if args.case in ('bad-magic','wrong-size') and first[:6]!=b'NRI!\x02\x06':
                    raise RuntimeError('child did not report format failure')
                if args.case=='bad-magic' and not 0<a._u16(first,12)<a._u16(first,14):
                    raise RuntimeError('failure was not after parent allocation')
            (args.evidence/'result.json').write_text(json.dumps({'boot_memlo':boot_memlo,'first_memlo':first_memlo,'boot_hatabs':boot_hatabs.hex(),'first_hatabs':first_hatabs.hex(),'first_result':first.hex(),'second_result':second.hex()},indent=2)+'\n')
            (args.evidence/'result.png').write_bytes(b.screenshot())
    finally:
        a.stop([process]);a.cleanup_temps(temps)
