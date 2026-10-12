#!/usr/bin/env python3
"""Extract the 68000 -> Master messages from PD_M68K_LOG files: parameter writes to COMM1-COMM7 ($A15122-$A1512F)
collected until a command is written (byte to $A15121 = simple command, or word to $A15120 with high byte 01 = picture
command), grouped by (command, sender PC). Prints per group: count, which COMM bytes were set, example values, first/last frame.
usage: msgs.py LOG [LOG ...]"""
import sys, collections
groups = collections.OrderedDict()
for fn in sys.argv[1:]:
    params = {}
    for ln in open(fn):
        if ln[0] == '#': continue
        p = ln.split()
        f = int(p[0]); pc = int(p[1], 16); op = p[2]; sz = int(p[3]); ad = int(p[4], 16); v = int(p[5], 16)
        if op != 'W' or not (0xA15120 <= ad <= 0xA1512F or ad == 0xA15103): continue
        if ad == 0xA15103: continue
        if ad == 0xA15121 and sz == 1:
            cmd = ('simple', '%02x' % v)
        elif ad == 0xA15120 and sz == 2 and (v >> 8) == 1:
            cmd = ('picture', '%04x' % v)
        elif ad == 0xA15120 and sz == 2 and v == 0:
            params.clear(); continue          # clears are not messages
        else:
            if sz == 1: params[ad] = v
            else: params[ad] = v >> 8; params[ad + 1] = v & 0xff
            continue
        k = (cmd, pc)
        g = groups.setdefault(k, {'n': 0, 'bytes': set(), 'ex': [], 'f0': f, 'f1': f})
        g['n'] += 1; g['f1'] = f; g['bytes'] |= set(params)
        if len(g['ex']) < 3 or (len(g['ex']) < 6 and params not in [e for e in g['ex']]):
            g['ex'].append(dict(params))
        params = {}
for (cmd, pc), g in sorted(groups.items(), key=lambda x: (x[0][0][0], x[0][0][1], x[0][1])):
    regs = ",".join("%X" % (a & 0xF) for a in sorted(g['bytes']))
    ex = "; ".join(" ".join("%X=%02x" % (a & 0xF, v) for a, v in sorted(e.items())) for e in g['ex'][:3])
    print("%s %s pc=%06x n=%d f=%d-%d params(A1512x)=%s  e.g. %s" % (cmd[0], cmd[1], pc, g['n'], g['f0'], g['f1'], regs, ex))
