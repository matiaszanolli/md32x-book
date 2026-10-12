#!/usr/bin/env python3
"""regmap.py LISTING BIN PCH_MERGED: classify each 128-byte block of the SH-2 image as E (executed in the emulator runs),
C (reached by recursive descent but not executed), D (neither). Prints runs."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import vfa
img = vfa.Img(sys.argv[1], sys.argv[2])
seeds = [0x60001cc, 0x6000278, 0x6000120, 0x6000150, 0x6000498, 0x6000350, 0x600856c, 0x6000528, 0x6000578]
cands = set()
for a in img.ins:
    r = vfa.litval(img, a)
    if r and r[1] and vfa.BASE <= r[1] < vfa.BASE + len(img.d) and not r[1] & 1: cands.add(r[1])
code, funcs, calls = vfa.descend(img, seeds, sorted(cands))
ex = set()
for l in open(sys.argv[3]):
    c, pc, n = l.split(); pc = int(pc, 16)
    if 0x06000000 <= pc < 0x06040000: ex.add(pc)
B = 128
cls = []
for b in range(len(img.d) // B):
    lo = 0x06000000 + b * B
    e = sum(1 for a in range(lo, lo + B, 2) if a in ex)
    c = sum(1 for a in range(lo, lo + B, 2) if a in code)
    cls.append('E' if e >= 6 else ('C' if c >= 12 else 'D'))
runs = []
for i, k in enumerate(cls):
    if runs and runs[-1][0] == k: runs[-1][2] = i
    else: runs.append([k, i, i])
for k, a, b in runs:
    print('%s %08x-%08x %5d' % (k, 0x06000000 + a * B, 0x06000000 + (b + 1) * B, (b - a + 1) * B))
