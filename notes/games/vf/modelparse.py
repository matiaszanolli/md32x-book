#!/usr/bin/env python3
"""modelparse.py SDRAM_DUMP ADDR [ADDR...]: parse the engine's polygon stream (overlay A, image 0x73B4) at SDRAM addresses.
Format: N, N2, N*(x,y,z) int16, then per polygon: flags, colour, new vertex indices (byte offsets), optional 3-halfword normal
(flags bit 5); flags bits 11-9 = variant (6 = end). Prints per part: vertices, polygons, colours."""
import sys, struct, collections
d = open(sys.argv[1], 'rb').read()
def h(a): return struct.unpack('>H', d[a-0x06000000:a-0x06000000+2])[0]
def sh(a): return struct.unpack('>h', d[a-0x06000000:a-0x06000000+2])[0]
newc = {0: (4, 3), 1: (2, 1), 2: (2, 1), 3: (2, 1), 4: (0, 0), 5: (0, 0)}
tot = collections.Counter()
for a0 in sys.argv[2:]:
    a = int(a0, 16)
    n = h(a); n2 = h(a + 2); a += 4
    verts = [(sh(a + 6*i), sh(a + 6*i + 2), sh(a + 6*i + 4)) for i in range(n)]
    a += 6 * n
    polys = []
    while True:
        fl = h(a); col = h(a + 2); a += 4
        var = (fl >> 9) & 7
        if var == 6: break
        k = newc[var][1 if col & 1 else 0]
        idx = [h(a + 2*i) for i in range(k)]; a += 2 * k
        if fl & 0x20: a += 6
        polys.append((fl, col, var, idx))
        if len(polys) > 200: break
    cols = collections.Counter(p[1] >> 8 for p in polys)
    modes = collections.Counter(p[1] & 3 for p in polys)
    fls = collections.Counter(p[0] & 0x1ff for p in polys)
    tri = sum(1 for p in polys if p[1] & 1)
    print('%s: N=%d N2=%d polys=%d tris=%d colours=%s lowbits=%s flags=%s' % (a0, n, n2, len(polys), tri, dict(cols), dict(modes), {hex(k): v for k, v in fls.items()}))
    tot['verts'] += n; tot['polys'] += len(polys)
print(dict(tot))
