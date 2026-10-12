#!/usr/bin/env python3
"""fbrender.py DEBUGOUT OUT.png  : render a frame-buffer dump (reads of 0x24000000.. and 68K reads of $A15200 palette)
taken with a debug script, using the line table in the first 0x200 bytes."""
import sys, re
from PIL import Image
fb = bytearray(0x20000); pal = bytearray(0x200)
for l in open(sys.argv[1]):
    m = re.match(r'([0-9A-F]{8}): ((?:[0-9A-F]{2} ?)+)$', l.strip())
    if not m: continue
    a = int(m.group(1), 16); b = bytes.fromhex(m.group(2).replace(' ', ''))
    if 0x24000000 <= a < 0x24020000: fb[a - 0x24000000:a - 0x24000000 + len(b)] = b
    elif 0xA15200 <= a < 0xA15400: pal[a - 0xA15200:a - 0xA15200 + len(b)] = b
def col(i):
    v = (pal[2*i] << 8) | pal[2*i+1]
    r = (v & 31) * 255 // 31; g = ((v >> 5) & 31) * 255 // 31; b = ((v >> 10) & 31) * 255 // 31
    return (r, g, b)
im = Image.new('RGB', (320, 224))
px = []
for y in range(224):
    lt = (fb[2*y] << 8) | fb[2*y+1]
    base = lt * 2
    for x in range(320):
        px.append(col(fb[(base + x) & 0x1ffff]))
im.putdata(px); im = im.resize((640, 448), Image.NEAREST); im.save(sys.argv[2])
print('line table first entries', [(fb[2*y] << 8) | fb[2*y+1] for y in range(6)])
