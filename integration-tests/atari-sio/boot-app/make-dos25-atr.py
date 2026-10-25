#!/usr/bin/env python3
"""Derive a clean-start baseline and resident fixture from the verified source ATR."""
import hashlib
import os
import shutil
import subprocess
import sys
from pathlib import Path

SOURCE_SHA256 = '6b90fcfc9ca1765bb9d6eb2d27b174287a5c2d619d910b4d60057db708fbcb2e'
source = Path(sys.argv[1])
out = Path(sys.argv[2])
if hashlib.sha256(source.read_bytes()).hexdigest() != SOURCE_SHA256:
    raise SystemExit('DOS 2.5 source ATR SHA-256 does not match the recorded image')
out.mkdir(parents=True, exist_ok=True)
clean = out / 'dos25-clean.atr'
install = out / 'dos25-resident.atr'
for target in (clean, install):
    if source.resolve() == target.resolve() or (target.exists() and os.path.samefile(source, target)):
        raise SystemExit(f'source ATR aliases output {target}')
if clean.resolve() == install.resolve() or (clean.exists() and install.exists() and os.path.samefile(clean, install)):
    raise SystemExit('output ATRs alias each other')
shutil.copyfile(source, clean)
subprocess.run(['atr', str(clean), 'rm', 'autorun.sys'], check=True)
shutil.copyfile(clean, install)
for local, name in [('fnresident-asm-disk-loader.xex', 'AUTORUN.SYS'),
                    ('nio.o65', 'NIO.O65'), ('fnread.bas', 'FNREAD.BAS'),
                    ('fnwrite.bas', 'FNWRITE.BAS'), ('fnpost.bas', 'FNPOST.BAS')]:
    subprocess.run(['atr', str(install), 'put', str(out / local), name], check=True)
for path in (clean, install):
    print(f'{path}: {hashlib.sha256(path.read_bytes()).hexdigest()}')
