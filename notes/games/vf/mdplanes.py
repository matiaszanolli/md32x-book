#!/usr/bin/env python3
"""Render the Mega Drive planes (A at reg2, B at reg4) from a PD_VDP_DUMP dump (see patch_vdplog.py)
as a PNG, ignoring scroll and priority.   usage: mdplanes.py DUMP_PREFIX_FRAME OUT.png  (e.g. vdp/d_1500)"""
import sys, struct
from PIL import Image
pre, out = sys.argv[1], sys.argv[2]
v = open(pre + '.vram', 'rb').read(); c = open(pre + '.cram', 'rb').read(); r = open(pre + '.reg', 'rb').read()
pal = []
for i in range(64):
    w = struct.unpack('<H', c[i*2:i*2+2])[0]
    pal.append((((w >> 1) & 7) * 36, ((w >> 5) & 7) * 36, ((w >> 9) & 7) * 36))
a = (r[2] & 0x38) << 10; b = (r[4] & 7) << 13
w, h = {0: 32, 1: 64, 3: 128}[r[16] & 3], {0: 32, 1: 64, 3: 128}[(r[16] >> 4) & 3]
def plane(base):
    im = Image.new('RGB', (64*8, 32*8))
    for cy in range(32):
        for cx in range(64):
            e = struct.unpack('>H', v[base + (cy * w + cx) * 2: base + (cy * w + cx) * 2 + 2])[0]
            t = e & 0x7ff; p = (e >> 13) & 3; fx = e & 0x800; fy = e & 0x1000
            for y in range(8):
                for x in range(8):
                    sx = 7 - x if fx else x; sy = 7 - y if fy else y
                    byte = v[t * 32 + sy * 4 + sx // 2]
                    n = (byte >> 4) if sx % 2 == 0 else (byte & 15)
                    if n: im.putpixel((cx*8+x, cy*8+y), pal[p*16+n])
    return im
A = plane(a); B = plane(b)
sh = Image.new('RGB', (512, 512*2//2 + 256))
sh = Image.new('RGB', (512*2, 256), (40, 0, 40)); sh.paste(A, (0, 0)); sh.paste(B, (512, 0))
sh.save(out); print('A at %x B at %x size %dx%d' % (a, b, w, h))
