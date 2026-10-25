#!/usr/bin/env python3
"""Check the actual parent builder's reservation gate."""
import struct
from allocation import reservation

def fnr(alloc, stack=0, zp=26):
    data = bytearray(22)
    data[:4] = b'FNR1'
    struct.pack_into('<H', data, 14, alloc)
    struct.pack_into('<H', data, 18, stack)
    struct.pack_into('<H', data, 20, zp)
    return bytes(data)

assert reservation(fnr(2334)) == (2334, 2335)
assert reservation(fnr(3045)) == (3045, 3046)
for sample in (fnr(3046), fnr(65535), fnr(1, stack=1), fnr(1, zp=27), fnr(0), b'FNR1'):
    try:
        reservation(sample)
    except ValueError:
        continue
    raise AssertionError('invalid resident allocation was accepted')
print('SDX parent allocation and permanent budget checks passed')
