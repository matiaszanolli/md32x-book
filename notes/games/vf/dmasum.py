#!/usr/bin/env python3
"""Summarise the 'D' (68000-to-VDP DMA) lines of a PD_VDP_LOG: one line per (PC, type, destination, length) with count,
frame range and the source addresses.   usage: dmasum.py VDP_LOG"""
import sys, collections
g = collections.OrderedDict()
for ln in open(sys.argv[1]):
    p = ln.split()
    if p[2] == 'D':
        k = (p[1], p[3], int(p[4], 16), int(p[5]))
        e = g.setdefault(k, [0, int(p[0]), 0, set()])
        e[0] += 1; e[2] = int(p[0]); e[3].add(p[6])
for k in sorted(g, key=lambda k: (k[0], k[2])):
    n, f0, f1, srcs = g[k]; s = sorted(srcs)
    print("pc=%s type=%s dest=$%05x len=%d words n=%d f=%d-%d src=%s%s" % (k[0], k[1], k[2], k[3], n, f0, f1, ",".join("$" + x for x in s[:3]), " ... (%d)" % len(s) if len(s) > 3 else ""))
