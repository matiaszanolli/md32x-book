#!/usr/bin/env python3
"""cagg.py CALLS CPU DEPTH [MIN]: aggregate inclusive instruction counts per call target at a given tree depth
(depth 1 = calls made from the CPU's top-level loop), over the whole log. Prints target, calls, total inclusive instr,
and the callsite(s)."""
import sys, collections
f = sys.argv[1]; cpu = sys.argv[2]; depth = int(sys.argv[3]); mini = int(sys.argv[4]) if len(sys.argv) > 4 else 0
stack = []   # entries: [tgt, start, kind, site, ret]
agg = collections.defaultdict(lambda: [0, 0, set()])
def close(d, ni):
    for x in stack[d:]:
        pass
    top = stack[d]
    if d + 1 == depth:
        a = agg[top[0]]; a[0] += 1; a[1] += ni - top[1]; a[2].add(top[3])
for l in open(f):
    p = l.split()
    if p[1][0] != cpu: continue
    k = p[1][1]; ni = int(p[4])
    if k == 'C':
        site = int(p[2], 16); stack.append([int(p[3], 16), ni, 'C', site, site + 4])
    elif k == 'I':
        stack.append([int(p[3], 16), ni, 'I', int(p[2], 16), int(p[2], 16)])
    elif k == 'R':
        pr = int(p[3], 16)
        for d in range(len(stack) - 1, -1, -1):
            if stack[d][2] == 'C' and stack[d][4] == pr:
                for e in range(len(stack) - 1, d - 1, -1): close(e, ni)
                del stack[d:]
                break
    elif k == 'E':
        for d in range(len(stack) - 1, -1, -1):
            if stack[d][2] == 'I':
                for e in range(len(stack) - 1, d - 1, -1): close(e, ni)
                del stack[d:]
                break
for t, (n, tot, sites) in sorted(agg.items(), key=lambda x: -x[1][1]):
    if tot >= mini: print('%08x calls=%6d incl=%10d  sites=%s' % (t, n, tot, ' '.join('%x' % s for s in sorted(sites)[:4])))
