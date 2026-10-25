#!/usr/bin/env python3
"""Protect local inputs before generating SDX fixture artifacts offline."""
import argparse
import hashlib
import os
from pathlib import Path
p=argparse.ArgumentParser()
p.add_argument('--car',type=Path,required=True);p.add_argument('--parser',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
a=p.parse_args()
root=Path(__file__).resolve().parents[3]
here=Path(__file__).resolve().parent
boot=here.parent/'boot-app'
for path,digest in [(a.car,'e400cba0ba7e20dc62c60019ab99de04d11f4a4fa841e20cacca7c44099940a3'),(a.parser,'ac65c8308d4c3fd851057aa61bd66a80fce61f54f56da0ef3e378835ce141200')]:
    if hashlib.sha256(path.read_bytes()).hexdigest()!=digest:
        raise SystemExit(f'{path}: checksum mismatch')
if not os.access(a.parser,os.X_OK):raise SystemExit('BASIC parser is not executable')
outputs=[a.out/name for name in ('sdx-fixture.atr','nio.o65','fnread.bas','fnwrite.bas','fnpost.bas')]
protected=[a.car,a.parser,*here.glob('*.py'),here/'parent.s',here/'parent.cfg',here/'child.cfg',boot/'Makefile',
           here.parent/'make_resident_o65_image.py',here.parent/'resident-relocation/verify_o65_api_closure.py',
           boot/'fnresident_basic_read.bas',boot/'fnresident_basic_write.bas',boot/'fnresident_basic_post.bas',
           root/'repos/nio-core-apps/apps/platform/atari/resident/fnresident_o65_loader.s',
           root/'repos/fujinet-nio/distfiles/boot/atari/autorun.atr',root/'repos/fujinet-nio/distfiles/esp32-data/boot/atari/autorun.atr',
           root/'repos/nio-core-apps/build/atari/disk/boot/autorun.atr',
           *[root/('repos/nio-core-apps/build/atari/bin/fnresident-asm.'+ext) for ext in ('o65','lbl','map','o')]]
def alias(a,b):return a.resolve()==b.resolve() or (a.exists() and b.exists() and os.path.samefile(a,b))
for i,out in enumerate(outputs):
    if any(alias(out,other) for other in protected+outputs[:i]):raise SystemExit(f'{out}: output aliases a protected input or output')
if outputs[0].exists():raise SystemExit(f'{outputs[0]} already exists; choose a new OUT')
