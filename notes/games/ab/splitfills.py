# Count the auto fills issued by the split-fill routine 0x06008280 per drawn picture.
#
#   python3 splitfills.py samples.jsonl [FIRST LAST]
#
# samples.jsonl from dbgsample.py with reads of 68k 0xFF0060 (stage index),
# master 0x26003AFC (frame counter), 0x26003C14 (ring being drawn), the three
# rings' mode words (+$C06: 0x2601818E, 0x26018DB6, 0x260199DE) and the split
# table 0x26007674 (448 bytes). For each frame-counter value the sample from the
# last frame before it changes is taken as that picture's table (the table is
# built before the sprites, the counter is bumped after them). Pictures whose
# ring mode word is not 1 did not run 0x06008280 and are listed separately.
#
# Per line, the code at 0x060082A0-0x060082BC (32-bit, mov.w sign-extends):
#   r1 = w >> 1 (logical); if r1 > 0x2A8 (signed): r1 -= 0x100, colours swapped
#   r8 = 0x2A8 - r1 - 1; borrow -> one fill; else r8 >= 0x9F -> one fill; else two.
import sys, json, collections, statistics

RINGS = {0x06017588: '0x2601818E', 0x060181B0: '0x26018DB6', 0x06018DD8: '0x260199DE'}

def fills_for_line(w):
    if w & 0x8000: w |= 0xFFFF0000
    r1 = (w & 0xFFFFFFFF) >> 1
    s = lambda x: x - (1 << 32) if x & 0x80000000 else x
    if s(r1) > 0x2A8: r1 = (r1 - 0x100) & 0xFFFFFFFF
    r8 = 0x2A8 - r1 - 1
    if r8 < 0 or r1 > 0x2A7: return 1     # borrow (r1 unsigned > 0x2A7)
    return 1 if r8 >= 0x9F else 2

def main():
    rows = [json.loads(l) for l in open(sys.argv[1])]
    lo, hi = (int(sys.argv[2]), int(sys.argv[3])) if len(sys.argv) > 3 else (0, 1 << 30)
    rows = [r for r in rows if lo <= r['frame'] <= hi]
    pics = collections.OrderedDict()
    for r in rows:
        pics[int(r['0x26003AFC'], 16)] = r          # last sample per counter value
    per = []; modes = collections.Counter(); stages = collections.Counter()
    for c, r in pics.items():
        ring = int(r['0x26003C14'], 16)
        mode = int(r[RINGS[ring]], 16) if ring in RINGS else None
        modes[mode] += 1
        if mode != 1: continue
        t = bytes.fromhex(r['0x26007674'])
        ws = [int.from_bytes(t[i:i+2], 'big') for i in range(0, 448, 2)]
        n = sum(fills_for_line(w) for w in ws)
        per.append((r['frame'], c, int(r['0xFF0060'], 16), n))
        stages[int(r['0xFF0060'], 16)] += 1
    print('pictures', len(pics), 'mode word per picture', dict(modes))
    print('mode-1 pictures by stage index', dict(sorted(stages.items())))
    ns = [p[3] for p in per]
    if not ns: return
    print('fills per mode-1 picture: min %d median %g max %d mean %.1f' %
          (min(ns), statistics.median(ns), max(ns), statistics.mean(ns)))
    one = sum(448 - n for n in ns)              # lines with one fill
    print('one-fill lines: %d of %d (%.1f%%)' % (one, 224 * len(ns), 100.0 * one / (224 * len(ns))))
    h = collections.Counter(ns)
    print('pictures with 448 fills: %d; with 224: %d' % (h[448], h[224]))
    dec = collections.Counter((n - 224) // 22 for n in ns)
    print('histogram of two-fill lines (bins of 22 lines):',
          ', '.join('%d-%d: %d' % (b * 22, b * 22 + 21, dec[b]) for b in sorted(dec)))
    for st in sorted(stages):
        v = [p[3] for p in per if p[2] == st]
        print('  stage index %d: %d pictures, fills min %d median %g max %d' %
              (st, len(v), min(v), statistics.median(v), max(v)))

main()
