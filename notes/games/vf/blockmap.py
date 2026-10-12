#!/usr/bin/env python3
"""Coarse map of a ROM: per BLOCK bytes, print the Shannon entropy (bits/byte), share of 0x00/0xFF,
and runs of similar blocks.   usage: blockmap.py ROM [BLOCK=0x4000]"""
import sys, math, collections
d = open(sys.argv[1], 'rb').read(); B = int(sys.argv[2], 0) if len(sys.argv) > 2 else 0x4000
rows = []
for o in range(0, len(d), B):
    b = d[o:o+B]; c = collections.Counter(b); n = len(b)
    e = -sum(v/n*math.log2(v/n) for v in c.values())
    rows.append((o, e, (c[0] + c[255]) / n))
for o, e, z in rows:
    print("%06x %.2f %3d%% %s" % (o, e, z*100, '#' * int(e * 4)))
