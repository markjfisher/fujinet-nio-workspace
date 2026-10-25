"""Validate the production resident reservation before building an SDX bootstrap."""
import struct


def reservation(module):
    if len(module) < 22 or module[:4] != b'FNR1':
        raise ValueError('invalid resident FNR wrapper')
    alloc = struct.unpack_from('<H', module, 14)[0]
    stack = struct.unpack_from('<H', module, 18)[0]
    zp = struct.unpack_from('<H', module, 20)[0]
    # This SDX child is compiled for the assembly resident, whose existing
    # contract forbids a C stack and charges its conservative cc65 ZP bank.
    if stack or zp != 26 or alloc == 0:
        raise ValueError('unsupported resident reservation')
    size = alloc + stack + 1  # one byte for two-byte alignment
    if size > 0xffff or size + zp > 3072:
        raise ValueError('resident reservation exceeds permanent budget')
    return alloc, size
