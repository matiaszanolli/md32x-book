# Summarise the runway routine's tables per drawn picture (mode word 2).
#
#   python3 runwaytab.py samples.jsonl [FRAME ...]
#
# samples.jsonl from dbgsample.py with master reads of 0x26003AFC (frame
# counter), 0x26003C14 (ring being drawn), the rings' mode words (0x2601818E,
# 0x26018DB6, 0x260199DE), 0x26007474 (448: per-line word), 0x26007A74 (1024:
# phase per row), 0x26007E74 (1024: per-row word, colour group in bits 7-8).
# Prints, over mode-2 pictures: first ground line, row step per line
# (mean/min/max), phase values; for each FRAME given, the per-line rows.
import sys, json, collections
RINGS = {0x06017588: '0x2601818E', 0x060181B0: '0x26018DB6', 0x06018DD8: '0x260199DE'}
W = lambda h: [int.from_bytes(bytes.fromhex(h)[i:i+2], 'big') for i in range(0, len(h) // 2, 2)]
rows = [json.loads(l) for l in open(sys.argv[1])]
show = set(int(a) for a in sys.argv[2:])
pics = collections.OrderedDict()
for r in rows: pics[int(r['0x26003AFC'], 16)] = r
first = collections.Counter(); steps = collections.Counter(); phases = collections.Counter()
npic = 0; frames = []
for c, r in pics.items():
    ring = int(r['0x26003C14'], 16)
    if ring not in RINGS or int(r[RINGS[ring]], 16) != 2: continue
    npic += 1; frames.append(r['frame'])
    t = W(r['0x26007474']); ph = W(r['0x26007A74'])
    g = [x for x in t if not x & 0x800]
    if len(g) < 2: continue
    first[t.index(g[0])] += 1
    d = [g[i+1] - g[i] for i in range(len(g) - 1)]
    steps[(round((g[-1] - g[0]) / (len(g) - 1), 2), min(d), max(d))] += 1
    phases[tuple(sorted(set(ph[k] for k in set(g))))] += 1
print('mode-2 pictures', npic, 'frames %d-%d' % (min(frames), max(frames)) if frames else '')
print('first ground line:', first.most_common(6), '...', len(first), 'values')
print('(mean, min, max) row step per line:', steps.most_common(6))
print('phase values used by visible rows:', [(k[:4], n) for k, n in phases.most_common(6)])
for r in rows:
    if r['frame'] in show:
        t = W(r['0x26007474']); pr = W(r['0x26007E74'])
        print('frame', r['frame'])
        for y in range(224):
            x = t[y]
            print('  line %3d: %s' % (y, 'solid colour %d' % (x & 15) if x & 0x800 else
                  'row %3d (step %s) group %d' % (x, x - t[y-1] if y and not t[y-1] & 0x800 else '-', (pr[x] >> 7) & 3)))
