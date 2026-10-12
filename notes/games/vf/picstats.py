#!/usr/bin/env python3
"""picstats.py CALLS [RINGA RINGB]: per-picture figures from the interpreter-run logs of build_vf_core.sh
(VF_CALLS call/return log, and the SDRAM write logs of ring A and ring B).

CALLS lines: "cycle KIND pc target ninst", cycle in 68000 cycles, KIND = {M,S}{C,J,R,I}.
Prints, per picture (a picture starts at the Master's call of the render task 0x0600969C, go = the first of each pair
of Master interrupts):
  - calls of overlay A (jsr at 0x06007378)
  - instructions from the go to the transform (call of 0x060071C4), the pose part (0x969C to 0x7398), the transform
    loop (0x71C4 to 0x194A8), stage 3 (0x194A8 to the overlay B return at 0xC000004E)
  - entries into overlay B's polygon routine (0xC0000068) and returns through its reject exit (0xC00000D6)
  - the Slave's command 1 (call of 0x06007948 to the jump to 0x06000724): instructions, frames, SH-2 clocks per instruction
RINGA (Slave status writes) and RINGB (Master status writes) add the slot and record counts per picture."""
import sys, bisect
FR = 127856
ev = [l.split() for l in open(sys.argv[1]) if len(l.split()) >= 5]
M = [(int(e[0]), e[1], e[2], e[3], int(e[4])) for e in ev if e[1][0] == 'M']
S = [(int(e[0]), e[1], e[2], e[3], int(e[4])) for e in ev if e[1][0] == 'S']
def calls(lst, kind, tgt): return [(t, n) for t, k, pc, tg, n in lst if k == kind and tg == tgt]
mi = [(t, n) for t, k, pc, tg, n in M if k == 'MI'][0::2]
p969 = [t for t, n in calls(M, 'MC', '0600969c')]
t71 = calls(M, 'MC', '060071c4'); t94 = calls(M, 'MC', '060194a8'); m98 = calls(M, 'MC', '06007398')
r4e = [(t, n) for t, k, pc, tg, n in M if k == 'MR' and pc == 'c000004e']
def nxt(lst, t): i = bisect.bisect_right([x[0] for x in lst], t); return lst[i] if i < len(lst) else None
print('picture: calls(A) go->transform | poses | transform loop | stage 3 | entries B | rejects | frames go->0x194A8')
starts = p969 + [10**18]
# windows run from one call of the render task to the next; the last, truncated window is dropped
P = [t for t, n in calls(M, 'MC', '0600969c')]
mis = [t for t, n in mi]
for k in range(len(P) - 1):
    lo, hi = P[k], P[k + 1]
    b = nxt(t94, lo); a = nxt(t71, lo); pm = nxt(m98, lo)
    if not (a and b) or b[0] >= hi: continue
    e = nxt(r4e, b[0])
    g = [x for x in mi if x[0] < lo and x[0] > (P[k - 1] if k else 0)]
    nA = sum(1 for t, kk, pc, tg, n in M if kk == 'MC' and pc == '06007378' and tg == 'c0000000' and lo <= t < hi)
    ent = sum(1 for t, kk, pc, tg, n in M if kk == 'MC' and tg == 'c0000068' and lo <= t < hi)
    rej = sum(1 for t, kk, pc, tg, n in M if kk == 'MR' and pc == 'c00000d6' and lo <= t < hi)
    print('%d: A=%d go->xform %s | poses %d | loop %d | stage3 %s | B in %d | rej %d | go->0x194A8 %s frame' % (
        k, nA, (a[1] - g[0][1]) if g else '-', pm[1] - nxt([(t, n) for t, n in calls(M, 'MC', '0600969c')], lo - 1)[1],
        b[1] - a[1], (e[1] - b[1]) if e else '-', ent, rej, '%.3f' % ((b[0] - g[0][0]) / FR) if g else '-'))
print('Slave command 1:')
st = [(t, n) for t, k, pc, tg, n in S if k == 'SC' and tg == '06007948']
en = [(t, n) for t, k, pc, tg, n in S if k == 'SJ' and tg == '06000724']
for t, n in st:
    x = nxt(en, t)
    if x: print('  %d instructions, %.3f frames, %.2f SH-2 clocks per instruction' % (x[1] - n, (x[0] - t) / FR, 3 * (x[0] - t) / (x[1] - n)))
if len(sys.argv) > 3:
    A = [int(l.split()[0]) for l in open(sys.argv[2]) if len(l.split()) >= 6 and l.split()[1] == 'S' and l.split()[2] == 'W4' and l.split()[3] == '060072ba']
    B = []
    for l in open(sys.argv[3]):
        p = l.split()
        if len(p) >= 6 and p[1] == 'M' and p[2] == 'W2':
            ad = int(p[4], 16)
            if (ad & 0x3f) == 0x1c and 0x06038000 <= ad < 0x0603c000 and int(p[5], 16) in (4, 6): B.append(int(p[0]))
    lastb = max(B) if B else 0
    for k in range(len(p969) - 1):
        nb = sum(1 for t in B if p969[k] <= t < p969[k+1])
        print('picture %d: ring A slots %d, ring B records %s' % (k, sum(1 for t in A if p969[k] <= t < p969[k+1]), nb if p969[k+1] <= lastb else 'n/a (log ends)'))
