# usage: python3 cachesurvey.py DEBUG_OUT
# Parses a debug-script log made of repeated
#   run 1 / read 68k 0xA1518A 2 / read slave 0x260075E4 160 /
#   read slave 0x260310E0 4096 / read slave 0x260326C8 4096 / regs slave
# and prints, per sampled frame: FS, sound state (GBR+28 priority, +36 samples
# left, +44 codebook base x2), polygon list counts (+104, +106, toggle +102),
# trapezoids written since the clear (write pointer GBR+20), Slave PC, and the
# distinct 16-byte lines and cache entries the current list's records span.
import sys, re, collections
txt = re.split(r'vrd-dbg> run 1\n', open(sys.argv[1]).read())[1:]
def mem(block, base):
    out = bytearray()
    m = re.search(r'read slave 0x%08X \d+\n((?:[0-9A-F]{8}:.*\n)+)' % base, block)
    for line in m.group(1).splitlines():
        out += bytes(int(x, 16) for x in line.split(':')[1].split())
    return out
L = lambda b, o: int.from_bytes(b[o:o+4], 'big')
W = lambda b, o: int.from_bytes(b[o:o+2], 'big')
rows = []
for blk in txt:
    fs = re.search(r'00A1518A: (\w\w) (\w\w)', blk)
    g = mem(blk, 0x260075E4); la = mem(blk, 0x260310E0); lb = mem(blk, 0x260326C8)
    pc = re.search(r'Slave SH2: PC=(\w+)', blk).group(1)
    tog = W(g, 102); na, nb = W(g, 104), W(g, 106)
    ptrs = [L(la, 4*i) for i in range(min(na, 1024))] if tog & 1 else [L(lb, 4*i) for i in range(min(nb, 1024))]
    lines = set()
    for p in ptrs:
        for a in range(p, p + 36): lines.add(a >> 4)   # 36 = quad record, upper bound
    rows.append(dict(fs=int(fs.group(2), 16) & 1, pri=L(g, 28), left=L(g, 36), cb=L(g, 44) >> 1,
                     tog=tog, n=len(ptrs), trap=((L(g, 20) - 0x06039CB0) // 24), pc=pc,
                     lines=len(lines), entries=len({l & 63 for l in lines}),
                     lo=min(ptrs) if ptrs else 0, hi=max(ptrs) if ptrs else 0))
for i, r in enumerate(rows):
    print('%3d fs%d pri%08X left%6d cb%08X tog%d n%3d trap%4d lines%4d ent%2d %08X-%08X pc %s' % (
        i, r['fs'], r['pri'], r['left'], r['cb'], r['tog'], r['n'], r['trap'], r['lines'], r['entries'], r['lo'], r['hi'], r['pc']))
