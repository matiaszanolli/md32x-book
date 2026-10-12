#!/usr/bin/env python3
"""fprof.py LISTING BIN PCH [N]: executed-instruction histogram (from the VF_PCH log of the instrumented core)
grouped by function (vfa.py's recursive descent), top N per CPU."""
import sys, collections
sys.path.insert(0, __file__.rsplit('/', 1)[0])
import vfa, os
img = vfa.Img(sys.argv[1], sys.argv[2])
seeds = [0x60001cc, 0x6000278, 0x6000120, 0x6000150, 0x6000498, 0x6000350, 0x600856c, 0x6000528, 0x6000578]
cands = set()
for a in img.ins:
    r = vfa.litval(img, a)
    if r and r[1] and vfa.BASE <= r[1] < vfa.BASE + len(img.d) and not r[1] & 1:
        cands.add(r[1])
code, funcs, calls = vfa.descend(img, seeds, sorted(cands))
N = int(sys.argv[4]) if len(sys.argv) > 4 else 25
tot = {'M': collections.Counter(), 'S': collections.Counter()}
for l in open(sys.argv[3]):
    c, pc, n = l.split(); pc = int(pc, 16); n = int(n)
    if 0x06000000 <= pc < 0x06040000:
        f = code.get(pc)
        key = ('%08x' % f) if f else ('?%08x' % (pc & ~0xff))
    elif pc >= 0xC0000000:
        key = 'onchip+%04x' % ((pc - 0xC0000000) & ~0x3f)
    else:
        key = 'other%08x' % (pc & ~0xfff)
    tot[c][key] += n
for c in 'MS':
    s = sum(tot[c].values())
    print('CPU', c, 'instructions', s)
    for k, n in tot[c].most_common(N):
        print('  %-14s %9d %5.1f%%' % (k, n, 100.0 * n / s))
