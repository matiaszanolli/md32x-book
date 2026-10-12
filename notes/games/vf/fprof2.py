#!/usr/bin/env python3
"""fprof2.py PCH CALLS [N]: exclusive executed-instruction counts per function, where a function is the nearest preceding
observed call target (from the VF_CALLS log of the same run) in the same address space. Top N per CPU."""
import sys, collections
pch, calls = sys.argv[1], sys.argv[2]; N = int(sys.argv[3]) if len(sys.argv) > 3 else 30
tg = {'M': set(), 'S': set()}
for l in open(calls):
    p = l.split()
    if p[1][1] == 'C': tg[p[1][0]].add(int(p[3], 16))
import bisect
srt = {c: sorted(v) for c, v in tg.items()}
tot = {'M': collections.Counter(), 'S': collections.Counter()}
for l in open(pch):
    c, pc, n = l.split(); pc = int(pc, 16); n = int(n)
    s = srt[c]; i = bisect.bisect_right(s, pc) - 1
    f = s[i] if i >= 0 and (s[i] >> 28) == (pc >> 28) else 0
    tot[c][f] += n
for c in 'MS':
    t = sum(tot[c].values()); print('CPU', c, t)
    for f, n in tot[c].most_common(N): print('  %08x %9d %5.1f%%' % (f, n, 100.0 * n / t))
