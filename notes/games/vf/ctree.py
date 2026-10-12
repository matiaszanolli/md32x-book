#!/usr/bin/env python3
"""ctree.py CALLS CPU [MAXDEPTH] [MININSTR] [T0 T1]
Rebuild a call tree with inclusive instruction counts from the instrumented core's VF_CALLS log
(lines: time cpu+kind callsite target ninstr; kinds C call, J jmp@rn, R rts, E rte, I interrupt).
jmp @rn is treated as a tail transfer: it replaces the top of the stack.
Prints the tree of the first top-level activation window between T0 and T1 (if given)."""
import sys, collections
f = sys.argv[1]; cpu = sys.argv[2]
maxd = int(sys.argv[3]) if len(sys.argv) > 3 else 4
mini = int(sys.argv[4]) if len(sys.argv) > 4 else 500
t0 = int(sys.argv[5]) if len(sys.argv) > 5 else 0
t1 = int(sys.argv[6]) if len(sys.argv) > 6 else 1 << 62
class N:
    __slots__ = ('tgt', 'start', 'end', 'kids', 'kind', 'site', 'ret')
    def __init__(s, tgt, start, kind, site, ret): s.tgt = tgt; s.start = start; s.end = None; s.kids = []; s.kind = kind; s.site = site; s.ret = ret
root = N(0, 0, 'root', 0, None)
stack = [root]
ni = 0
for l in open(f):
    p = l.split()
    t = int(p[0]); c = p[1][0]; k = p[1][1]
    if c != cpu or t < t0 or t > t1: continue
    ni = int(p[4])
    if k == 'C':
        site = int(p[2], 16)
        n = N(int(p[3], 16), ni, 'C', site, site + 4); stack[-1].kids.append(n); stack.append(n)
    elif k == 'I':
        n = N(int(p[3], 16), ni, 'I', int(p[2], 16), int(p[2], 16)); stack[-1].kids.append(n); stack.append(n)
    elif k == 'R':
        pr = int(p[3], 16)
        for d in range(len(stack) - 1, 0, -1):
            if stack[d].kind == 'C' and stack[d].ret == pr:
                for x in stack[d:]: x.end = ni
                del stack[d:]
                break
    elif k == 'E':
        for d in range(len(stack) - 1, 0, -1):
            if stack[d].kind == 'I':
                for x in stack[d:]: x.end = ni
                del stack[d:]
                break
last = ni
def incl(n): return (n.end if n.end is not None else last) - n.start
def agg(kids):
    # merge consecutive kids with same target into (count, instr)
    out = []
    for n in kids:
        if out and out[-1][0].tgt == n.tgt and out[-1][0].kind == n.kind:
            out[-1][1].append(n)
        else:
            out.append((n, [n]))
    return out
def show(n, d, pre=''):
    if d > maxd: return
    for rep, grp in agg(n.kids):
        tot = sum(incl(x) for x in grp)
        if tot < mini and rep.kind != 'I': continue
        sub = []
        for x in grp: sub += x.kids
        print('%s%s%08x x%d  incl=%d  (from %08x)' % (pre, 'IRQ ' if rep.kind == 'I' else '', rep.tgt, len(grp), tot, rep.site))
        tmp = N(0, 0, 'm', 0); tmp.kids = sub
        show(tmp, d + 1, pre + '  ')
show(root, 1)
