#!/usr/bin/env python3
"""picturetime_by_frame.py LOG [CMDWORD]: from a PD_M68K_LOG, for every picture request (68000 write of $0186, or CMDWORD,
to COMM0) the time of the 68000's first read of COMM0 afterwards ("first look") and of the first read that returns a high
byte of 0 ("done"), in frames; prints the totals, how many pictures were already done at the first look, and the median and
maximum of 'done' per 100 frames of the run."""
import sys, statistics
FR = 127856
cmd = sys.argv[2] if len(sys.argv) > 2 else '0186'
ev = []
for ln in open(sys.argv[1]):
    if ln[0] == '#': continue
    p = ln.split(); ev.append((int(p[0]), p[2], p[4], p[5], int(p[6])))
go = None; first = None; res = []
for f, op, ad, v, cy in ev:
    t = f * FR + cy
    if op == 'W' and ad == 'a15120' and v == cmd: go = (t, f); first = None
    elif go and op == 'R' and ad == 'a15120':
        if first is None: first = (t - go[0]) / FR
        if v == '00': res.append((go[1], (t - go[0]) / FR, first)); go = None
print('pictures', len(res))
print('done: min %.3f median %.3f max %.3f' % (min(r[1] for r in res), statistics.median(r[1] for r in res), max(r[1] for r in res)))
print('first look: min %.3f median %.3f max %.3f' % (min(r[2] for r in res), statistics.median(r[2] for r in res), max(r[2] for r in res)))
print('already done at the first look:', sum(1 for r in res if r[1] == r[2]))
for lo in range(0, 6000, 100):
    s = [r[1] for r in res if lo <= r[0] < lo + 100]
    if s: print('frames %d-%d: %d pictures, median %.3f, max %.3f' % (lo, lo + 99, len(s), statistics.median(s), max(s)))
