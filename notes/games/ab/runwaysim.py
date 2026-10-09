# Replay the runway routine 0x06008350 on sampled tables and count its writes.
#
#   python3 runwaysim.py SH2_BIN samples.jsonl
#
# SH2_BIN: the SH-2 program (sh2dis.sh ... ab gives ab.bin); the run patterns at
# 0x060084C0 and colour groups at 0x060084A0 are static (checked against SDRAM).
# samples.jsonl as for runwaytab.py. Per mode-2 picture: auto fills (solid
# lines + runs of 28 pixels or more, the cmp/hs at 0x060083E4) and runs written
# by the CPU (shorter), each CPU run preceded by a FEN poll (0x060083F4).
import sys, json, collections, statistics
RINGS = {0x06017588: '0x2601818E', 0x060181B0: '0x26018DB6', 0x06018DD8: '0x260199DE'}
b = open(sys.argv[1], 'rb').read()
WD = lambda a: int.from_bytes(b[a - 0x06000000:a - 0x06000000 + 2], 'big')
W = lambda h: [int.from_bytes(bytes.fromhex(h)[i:i+2], 'big') for i in range(0, len(h) // 2, 2)]

def line(x, ph):
    if x & 0x800: return 1, 0, 0
    row = x & 0x1FF; a = 0x060084C0 + (row & ~1) * 16
    r13 = ph[row]
    while True:                                   # phase skip, 0x060083C4-0x060083CE
        w = WD(a); a += 2; r13 -= w & 0xFFF
        if r13 < 0: break
    r13 = -r13; r11 = 320; fills = cpu = cpub = 0
    while True:
        if r13 >= r11: r13 = r11                   # clip, 0x060083D6
        if r13 >= 28: fills += 1                   # 0x060083E2-0x060083E6
        else: cpu += 1; cpub += r13
        r11 -= r13
        if r11 == 0: return fills, cpu, cpub
        w = WD(a); a += 2; r13 = w & 0xFFF

rows = [json.loads(l) for l in open(sys.argv[2])]
pics = collections.OrderedDict()
for r in rows: pics[int(r['0x26003AFC'], 16)] = r
F, C, B = [], [], []
for c, r in pics.items():
    ring = int(r['0x26003C14'], 16)
    if ring not in RINGS or int(r[RINGS[ring]], 16) != 2: continue
    t = W(r['0x26007474']); ph = W(r['0x26007A74'])
    f = cp = by = 0
    for x in t:
        a1, a2, a3 = line(x, ph); f += a1; cp += a2; by += a3
    F.append(f); C.append(cp); B.append(by)
for name, v in (('auto fills', F), ('CPU runs', C), ('CPU-written pixels', B)):
    print('%-20s per picture: min %d median %g max %d mean %.1f' % (name, min(v), statistics.median(v), max(v), statistics.mean(v)))
print('pictures', len(F))
