#!/usr/bin/env python3
"""From a PD_M68K_LOG (with cycles-in-frame column): for every picture request (68000 write of $0184/$0186 to
$A15120 = COMM0, in the vertical-blank handler) find the first later read of COMM0's high byte (A15120) that returned 00,
and print the time between them in 68000 cycles (127,856 per NTSC frame), and the frame/cycle of the following FS flip
(write to $A1518B).   usage: picturetime.py LOG [CMDWORD ...]   (default 0186 0184)"""
import sys, statistics
FR = 127856
cmds = sys.argv[2:] or ['0186', '0184']
ev = []
for ln in open(sys.argv[1]):
    if ln[0] == '#': continue
    p = ln.split()
    ev.append((int(p[0]), int(p[1], 16), p[2], p[4], p[5], int(p[6])))
go = None; res = []
for f, pc, op, ad, v, cy in ev:
    t = f * FR + cy
    if op == 'W' and ad == 'a15120' and v in cmds:
        go = (t, f); done = None; flip = None
    elif go and op == 'R' and ad == 'a15120' and v == '00' and done is None:
        done = t
    elif go and done and op == 'W' and ad == 'a1518b':
        res.append((go[1], done - go[0], t - go[0])); go = None
if not res: sys.exit('no pictures')
d = [r[1] for r in res]; fl = [r[2] for r in res]
print("pictures:", len(res))
print("go -> COMM0 high byte seen 0 (68000 cycles): min %d median %d mean %d max %d (frames: %.2f / %.2f / %.2f / %.2f)" % (
    min(d), statistics.median(d), statistics.mean(d), max(d), min(d)/FR, statistics.median(d)/FR, statistics.mean(d)/FR, max(d)/FR))
print("go -> FS flip written: min %d median %d max %d" % (min(fl), statistics.median(fl), max(fl)))
import collections
c = collections.Counter(round(x/FR, 1) for x in d)
print("histogram of go->done in tenths of a frame:", sorted(c.items()))
