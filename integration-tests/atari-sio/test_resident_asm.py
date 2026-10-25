#!/usr/bin/env python3
"""Run unchanged behavioural CIO controls against the CA65 resident image."""
from pathlib import Path
import subprocess
import struct
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from compose_resident_o65_xex import segments

# Staged test payload, transient installer, launcher and CIO caller must not
# overwrite each other before installation (the streamed DOS path is separate).
ranges = sorted((start, end) for start, end, _ in segments(
    Path("build/fnresident-asm-open.xex").read_bytes()))
assert all(a[1] < b[0] for a, b in zip(ranges, ranges[1:])), ranges

for name in ('open', 'get_close', 'put'):
    source = Path(f'fnresident_o65_{name}.txt').read_text()
    source = source.replace('build/fnresident-o65-stage.xex', 'build/fnresident-asm-stage.xex')
    source = source.replace('build/fnresident-o65-loader.xex', 'build/fnresident-asm-loader.xex')
    # The prototype-only software-stack canaries do not describe this image.
    source = '\n'.join(line for line in source.splitlines() if '#0x3d' not in line)
    generated = Path(f'build/fnresident-asm-{name}.txt')
    generated.write_text(source)
    subprocess.run(['soft65c02_tester', '-i', str(generated)], check=True)

# Exercise each output method with the strict literal SIO peer. The peer
# checks both method and BODY_UNKNOWN on the actual OPEN request.
for mode in (8, 12):
    subprocess.run(['cl65', '-t', 'none', '--asm-define', f'OPEN_MODE={mode}',
                    '-C', 'fnresident-o65-loader-control.cfg', '-o',
                    f'build/fnresident-asm-output-{mode}.bin', 'fnresident_o65_put_control.s'], check=True)
    defines = ['--asm-define', 'ASM_OUTPUT_TEST=1']
    if mode == 12:
        defines += ['--asm-define', 'ASM_POST_TEST=1']
    subprocess.run(['cl65', '-t', 'none', *defines, '-C', 'fnresident-o65-open-siov.cfg', '-o',
                    f'build/fnresident-asm-output-{mode}-siov.xex', 'fnresident_o65_put_siov.s'], check=True)
    source = Path('fnresident_o65_put.txt').read_text()
    source = source.replace('build/fnresident-o65-put-control.bin', f'build/fnresident-asm-output-{mode}.bin')
    source = source.replace('build/fnresident-o65-put-siov.xex', f'build/fnresident-asm-output-{mode}-siov.xex')
    source = source.replace('build/fnresident-o65-stage.xex', 'build/fnresident-asm-stage.xex')
    source = source.replace('build/fnresident-o65-loader.xex', 'build/fnresident-asm-loader.xex')
    source = '\n'.join(line for line in source.splitlines() if '#0x3d' not in line)
    generated = Path(f'build/fnresident-asm-output-{mode}.txt')
    generated.write_text(source)
    subprocess.run(['soft65c02_tester', '-i', str(generated)], check=True)

allocation = struct.unpack_from('<H', Path('build/nio.o65').read_bytes(), 14)[0]
end = 0x1ee8 + allocation
subprocess.run(['cl65', '-t', 'none', '--asm-define', f'RESIDENT_ALLOCATION={allocation}',
                '-C', 'fnresident-o65-disk-control.cfg', '-o',
                'build/fnresident-asm-disk-control.bin', 'fnresident_o65_disk_control.s'], check=True)
source = Path('fnresident_o65_disk.txt').read_text()
source = source.replace('fnresident-o65-disk-control.bin', 'fnresident-asm-disk-control.bin')
source = source.replace('fnresident-o65-disk-loader.xex', 'fnresident-asm-disk-loader.xex')
source = source.replace('#0x02e7 = 0x72', f'#0x02e7 = 0x{end & 255:02x}')
source = source.replace('#0x02e8 = 0x56', f'#0x02e8 = 0x{end >> 8:02x}')
source = source.replace('#0x1ee8 = 0xa5', '#0x1ee8 = 0xa9')
generated = Path('build/fnresident-asm-disk.txt')
generated.write_text(source)
subprocess.run(['soft65c02_tester', '-i', str(generated)], check=True)

source = '''memory flush
memory load #0x8000 "build/fnresident-asm-disk-control.bin"
memory load #0x9500 "build/nio.o65"
memory load atari "build/fnresident-asm-disk-loader.xex"
memory write #0x031a 0x(4e)
memory write #0x031b 0x(00)
memory write #0x031c 0x(18)
memory write #0x1810 0x(46)
memory write #0x1811 0x(4e)
memory write #0x1812 0x(52)
memory write #0x1813 0x(31)
memory write #0x1ee8 0x(a7)
registers flush
run #0x8000 until (#0x0680 = 0x01 OR cycle_count > 0x800000)
assert #0x9385 = 0x04 $$prototype FNR1 marker is foreign to production FNA1$$
assert #0x031b = 0x00 $$prototype table low unchanged$$
assert #0x031c = 0x18 $$prototype table high unchanged$$
assert #0x1ee8 = 0xa7 $$prototype rejection writes no candidate image$$
assert #0x02e7 = 0xe8 $$prototype rejection preserves MEMLO$$
'''
generated = Path('build/fnresident-asm-prototype-foreign.txt')
generated.write_text(source)
subprocess.run(['soft65c02_tester', '-i', str(generated)], check=True)

# Reject a wrapper that exceeds permanent RAM or asks for a C stack before
# copying any payload, regardless of whether it passed an offline build gate.
for name, patches in (('budget', {0x950e: 0xe7, 0x950f: 0x0b}),
                      ('cstack', {0x9512: 1})):
    source = '''memory flush
memory load #0x8000 "build/fnresident-asm-disk-control.bin"
memory load #0x9500 "build/nio.o65"
memory load atari "build/fnresident-asm-disk-loader.xex"
memory write #0x1ee8 0x(a7)
'''
    source += ''.join(f'memory write #0x{address:04x} 0x({value:02x})\n'
                      for address, value in patches.items())
    source += '''registers flush
run #0x8000 until (#0x0680 = 0x01 OR cycle_count > 0x800000)
assert #0x9385 = 0x06 $$invalid permanent reservation rejected$$
assert #0x031a = 0x00 $$invalid wrapper never publishes N$$
assert #0x1ee8 = 0xa7 $$invalid wrapper never copies resident payload$$
assert #0x02e7 = 0xe8 $$invalid wrapper preserves MEMLO$$
assert #0x0684 = 0x01 $$invalid wrapper closes source file$$
'''
    generated = Path(f'build/fnresident-asm-reject-{name}.txt')
    generated.write_text(source)
    subprocess.run(['soft65c02_tester', '-i', str(generated)], check=True)

subprocess.run(['cl65', '-t', 'none', '--asm-define', 'ASM_FAILURE_TEST=1',
                '-C', 'fnresident-o65-loader-control.cfg', '-o',
                'build/fnresident-asm-fault-control.bin', 'fnresident_o65_put_control.s'], check=True)
subprocess.run(['cl65', '-t', 'none', '-C', 'fnresident-o65-open-siov.cfg', '-o',
                'build/fnresident-asm-fault-siov.xex', 'fnresident_asm_fault_siov.s'], check=True)
for fault in range(1, 10):
    source = f'''memory flush
memory load #0x4700 "build/fnresident-asm-fault-control.bin"
memory load atari "build/fnresident-asm-loader.xex"
memory load atari "build/fnresident-asm-stage.xex"
memory load atari "build/fnresident-asm-fault-siov.xex"
memory write #0x06df 0x({fault:02x})
registers flush
run #0x4700 until (#0x06d0 = 0x01 OR cycle_count > 0xb00000)
assert #0x06d0 = 0x01 $$fault {fault} control returns$$
assert #0x06d1 = 0x01 $$OPEN succeeded before fault$$
assert #0x06d2 = 0x90 $$uncertain PUT reports error$$
assert #0x06d3 = 0x90 $$CLOSE retains write error$$
assert #0x06d7 = 0x85 $$CLOSE retires local ownership despite fault$$
assert #0x06d8 = 0x01 $$new OPEN can reuse released slot$$
assert #0x06c0 = 0x04 $$only OPEN body CLOSE and new OPEN with no W replay$$
assert #0x06c1 = 0x00 $$uncertain body never automatically committed$$
assert #0x06c2 = 0x01 $$one remote CLOSE$$
'''
    generated = Path(f'build/fnresident-asm-fault-{fault}.txt')
    if fault == 5:
        source = source.replace('#0x06d2 = 0x90', '#0x06d2 = 0x00')
        source = source.replace('#0x06d3 = 0x90', '#0x06d3 = 0x01')
        source = source.replace('#0x06c0 = 0x04', '#0x06c0 = 0x06')
        source = source.replace('#0x06c1 = 0x00', '#0x06c1 = 0x01')
        source = source.replace('uncertain PUT reports error', 'partial acknowledgements finish the complete body')
        source = source.replace('CLOSE retains write error', 'partial acknowledgement CLOSE succeeds')
        source = source.replace('only OPEN body CLOSE and new OPEN with no W replay', 'exactly two body writes plus commit and session lifecycle')
        source = source.replace('uncertain body never automatically committed', 'acknowledged body committed once')
        source += 'assert #0x06c7 = 0x00 $$every partial suffix byte and offset is exact$$\n'
    if fault == 9:
        source = source.replace('#0x06c0 = 0x04', '#0x06c0 = 0x08')
        source = source.replace('#0x06c1 = 0x00', '#0x06c1 = 0x01')
        source = source.replace('#0x06c2 = 0x01', '#0x06c2 = 0x02')
        source = source.replace('only OPEN body CLOSE and new OPEN with no W replay', 'two independent sessions complete without replay')
        source = source.replace('uncertain body never automatically committed', 'only the unaffected session commits')
        source = source.replace('one remote CLOSE', 'one CLOSE per independent session')
        source += 'assert #0x06db = 0x01 $$second IOCB opens$$\n'
        source += 'assert #0x06dc = 0x01 $$second IOCB buffers before fault$$\n'
        source += 'assert #0x06dd = 0x01 $$second IOCB accepts byte after first fault$$\n'
        source += 'assert #0x06de = 0x01 $$second IOCB closes successfully$$\n'
        source += 'assert #0x06c7 = 0x00 $$second IOCB sends its own exact bytes$$\n'
    if fault == 8:
        source += 'assert #0x06c0 = 0x04 $$short current response is drained without replay$$\n'
    if fault == 7:
        source = source.replace('#0x06d2 = 0x90', '#0x06d2 = 0x00')
        source = source.replace('#0x06c0 = 0x04', '#0x06c0 = 0x05')
        source = source.replace('#0x06c1 = 0x00', '#0x06c1 = 0x01')
        source = source.replace('uncertain PUT reports error', 'full body write succeeds before commit')
        source = source.replace('only OPEN body CLOSE and new OPEN with no W replay', 'OPEN body commit CLOSE and new OPEN without replay')
        source = source.replace('uncertain body never automatically committed', 'one uncertain commit never repeated')
        source += 'assert #0x06d9 = 0x90 $$lost commit completion fails STATUS$$\n'
        source += 'assert #0x06da = 0x90 $$repeated STATUS does not retry commit$$\n'
    generated.write_text(source)
    subprocess.run(['soft65c02_tester', '-i', str(generated)], check=True)

# Repeat the uncertain W, partial acknowledgement and uncertain-commit cases
# through POST/update; neither repeated STATUS nor CLOSE may replay a commit.
subprocess.run(['cl65', '-t', 'none', '--asm-define', 'ASM_FAILURE_TEST=1',
                '--asm-define', 'OPEN_MODE=12', '-C', 'fnresident-o65-loader-control.cfg',
                '-o', 'build/fnresident-asm-post-fault-control.bin',
                'fnresident_o65_put_control.s'], check=True)
for fault in (2, 5, 7):
    source = Path(f'build/fnresident-asm-fault-{fault}.txt').read_text()
    source = source.replace('build/fnresident-asm-fault-control.bin',
                            'build/fnresident-asm-post-fault-control.bin')
    generated = Path(f'build/fnresident-asm-post-fault-{fault}.txt')
    generated.write_text(source)
    subprocess.run(['soft65c02_tester', '-i', str(generated)], check=True)
