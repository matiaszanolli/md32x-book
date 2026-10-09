# Cycles per drawn picture in After Burner Complete's background routines.
#
#   python3 bgcost.py PC_CSV WATCH_CSV
#
# PC_CSV: VRD_PROFILE_PC log. WATCH_CSV: VRD_WATCH log of 0x26003AFC:2 (Master
# frame counter), 0x26003C14:4 (ring being drawn), 0x2601818E:2,
# 0x26018DB6:2, 0x260199DE:2 (the three rings' mode words). Pictures are
# counted by the counter; each picture's mode is the drawn ring's mode word in
# the last frame before the counter moves on (1 = split fills 0x06008280,
# 2 = runway 0x06006F1C + 0x06008350, 0 = plain clear 0x0600D0C8).
import sys, csv, collections
RING = {0x06017588: '0x2601818E', 0x060181B0: '0x26018DB6', 0x06018DD8: '0x260199DE'}
GROUPS = [
    ('split fills 0x06008280-0x060082F7: FEN polls', [(0x060082C0, 0x060082C3), (0x060082D0, 0x060082D3), (0x060082E6, 0x060082E9)]),
    ('split fills 0x06008280-0x060082F7: total', [(0x06008280, 0x060082F7)]),
    ('split table build 0x06006BF0-0x06006F1B', [(0x06006BF0, 0x06006F1B)]),
    ('runway 0x060082FC-0x06008437: FEN polls', [(0x06008304, 0x06008307), (0x06008348, 0x0600834B), (0x06008384, 0x06008387), (0x060083F4, 0x060083F7)]),
    ('runway 0x060082FC-0x06008437: total', [(0x060082FC, 0x06008437)]),
    ('runway tables 0x06006F1C-0x0600724B', [(0x06006F1C, 0x0600724B)]),
    ('plain clear 0x0600D0C8-0x0600D0F3', [(0x0600D0C8, 0x0600D0F3)]),
    ('pre-sprite FEN wait 0x06003A94-0x06003A9B', [(0x06003A94, 0x06003A9B)]),
]
prof = [r for r in csv.DictReader(open(sys.argv[1])) if r['cpu'].lower().startswith('m')]
w = list(csv.DictReader(open(sys.argv[2])))
last = collections.OrderedDict()
for r in w: last[int(r['0x26003AFC'], 16)] = r
modes = collections.Counter()
for c, r in list(last.items())[1:-1]:          # drop the partial first and last
    ring = int(r['0x26003C14'], 16)
    modes[int(r[RING[ring]], 16) if ring in RING else None] += 1
n = sum(modes.values())
total = sum(int(r['total_cycles']) for r in prof)
print('frames %d, pictures %d, mode per picture %s; Master profile rows %d, smallest %s cycles'
      % (len(w), n, dict(modes), len(prof), min(int(r['total_cycles']) for r in prof)))
for name, rngs in GROUPS:
    s = sum(int(r['total_cycles']) for r in prof if any(a <= int(r['pc'], 16) <= b for a, b in rngs))
    print('%-48s %12d cycles  %9.0f per picture  %5.1f%% of executed' % (name, s, s / n, 100.0 * s / total))
