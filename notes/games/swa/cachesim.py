# usage: python3 cachesim.py ROM DEBUG_OUT [DEBUG_OUT ...] [--sound HEX] [--pfrac F,F,...] [--empty]
# (--empty: model pictures with no polygons, only the purge, frame code and idle loop)
#
# Model, not a measurement: a 2-way, 64-entry, 16-byte-line LRU simulation of
# the Slave's cached reads in Star Wars Arcade, to estimate how many of the
# decoder-1 codebook's lines (256 x 4 bytes, read through the cached cartridge
# view) would still be in the cache at their first use after frame command
# $0C's purge (0x060007D0) if the purge were left out.
#
# Inputs that come from the game:
#   - polygon record pointers per picture: the Slave's flat list (0x060310E0 or
#     0x060326C8 by GBR+102 bit 0, counts GBR+104/+106), parsed from debug logs
#     made by the script in cachesurvey.py (PicoDrive run); 36 bytes per record
#   - trapezoids per picture: largest GBR+20 write-pointer offset seen with that
#     list (/24; the ring wraps at 1,000, so large counts are under-read)
#   - codebook index stream: the sound's bytes in the ROM (header long at C-4 =
#     samples/2, codebook at C, index bytes at C+0x400; one index byte per 8
#     samples, the 4-byte entry read once per sample, 0x060009CC)
#   - code, GBR (0x060075E4) and stack lines per interrupt, from the disassembly
# Timing that is assumed (estimates): picture = 768,000 clocks (2 TV frames);
# PWM interrupt every 1,046 clocks (cycle 1,047); watchdog interrupt every 480
# clocks for the 224-line clear, then every 512 clocks, one trapezoid each;
# producer phase spread evenly over PFRAC x picture; idle loop afterwards.
import sys, re, random

PIC = 768000
args = sys.argv[1:]
rom = open(args.pop(0), 'rb').read()
sounds = [0x0225D1D0, 0x0225F6EC, 0x0222BF0C, 0x0222F07C, 0x0221EA80]
pfracs = [0.1, 0.2, 0.3, 0.5]
logs = []
empty = False
while args:
    a = args.pop(0)
    if a == '--sound': sounds = [int(args.pop(0), 16)]
    elif a == '--pfrac': pfracs = [float(x) for x in args.pop(0).split(',')]
    elif a == '--empty': empty = True
    else: logs.append(a)

def mem(block, base):
    m = re.search(r'read slave 0x%08X \d+\n((?:[0-9A-F]{8}:.*\n)+)' % base, block)
    out = bytearray()
    for line in m.group(1).splitlines():
        out += bytes(int(x, 16) for x in line.split(':')[1].split())
    return out

L = lambda b, o: int.from_bytes(b[o:o+4], 'big')
W = lambda b, o: int.from_bytes(b[o:o+2], 'big')

pictures = []           # (list base, [record pointers], trapezoids)
for fn in logs:
    last = None
    for blk in re.split(r'vrd-dbg> run 1\n', open(fn).read())[1:]:
        g = mem(blk, 0x260075E4)
        tog = W(g, 102)
        base, n = (0x060310E0, W(g, 104)) if tog & 1 else (0x060326C8, W(g, 106))
        lst = mem(blk, base | 0x20000000)
        ptrs = tuple(L(lst, 4*i) for i in range(min(n, len(lst) // 4)))
        trap = (L(g, 20) - 0x06039CB0) // 24
        if not ptrs: continue
        if last and last[1] == ptrs:
            last[2] = max(last[2], trap)
        else:
            last = [base, ptrs, trap]
            pictures.append(last)

if empty:                 # pictures with no polygons: purge, frame code, idle only
    pictures = [[0x060310E0, (), 0]]

def lines_of(a, size):
    return list(range(a >> 4, (a + size - 1 >> 4) + 1))

DISP = [0x06000510 >> 4, 0x06000520 >> 4, 0x06000530 >> 4, 0x06000550 >> 4]
PWM_CODE = [x >> 4 for x in (0x06000980, 0x06000990, 0x060009A0, 0x060009B0, 0x060009C0,
                             0x060009D0, 0x060009E0, 0x060009F0, 0x06000A00, 0x06000A20)]
PWM_GBR = [0x06007600 >> 4, 0x06007610 >> 4]
WDT_GBR = [x >> 4 for x in (0x060075F0, 0x06007650, 0x06007660, 0x06007670)]
STACK = [x >> 4 for x in (0x0603FDD0, 0x0603FDE0, 0x0603FDF0)]
FRAME_CODE = [x >> 4 for x in list(range(0x06000740, 0x060007A0, 16)) +
              list(range(0x060007D0, 0x060008B0, 16)) + list(range(0x06000BD0, 0x06000C30, 16))]
PROD_CODE = [x >> 4 for x in (0x060008C0, 0x060008D0, 0x060008E0)]
PROD_GBR = [x >> 4 for x in (0x060075F0, 0x06007650, 0x06007660)]
IDLE = [0x06000750 >> 4, 0x06000760 >> 4]
FLIP = [x >> 4 for x in (0x06000B90, 0x06000BA0, 0x06000BB0, 0x06000BC0)]

def picture_events(pic, pfrac, rnd):
    """Non-sound accesses of one picture as (time, line)."""
    base, ptrs, T = pic
    T = max(T, len(ptrs) // 3)
    ev = [(0, l) for l in FRAME_CODE + STACK]
    if not ptrs:
        return ev + [(t, l) for t in range(3000, PIC, 1000) for l in IDLE]
    P = pfrac * PIC
    t0 = 3000
    n = len(ptrs)
    prod_t = []
    for i, p in enumerate(ptrs):
        t = t0 + i * P / n
        ev += [(t, l) for l in PROD_CODE + PROD_GBR + [(base + 4*i) >> 4] + lines_of(p, 36)]
    for k in range(T):              # trapezoids produced evenly; slope table reads
        t = t0 + k * P / T
        prod_t.append(t)
        for _ in range(2):
            ev.append((t, (0x06035CB0 + 2 * rnd.randint(1, 80)) >> 4))
    # watchdog: 224 clear interrupts, then one trapezoid per interrupt
    t = t0; k = 0
    for _ in range(224):
        ev += [(t, l) for l in DISP + WDT_GBR + STACK[:2]]
        t += 480
    while k < T:
        t = max(t, prod_t[k])
        ev += [(t, l) for l in DISP + WDT_GBR + STACK[:2] +
               lines_of(0x06039CB0 + 24 * (k % 1000), 24)]
        k += 1; t += 512
    end_draw = t
    ev += [(end_draw + 500 * j, l) for j in range(4) for l in FLIP]
    tt = end_draw + 2000
    while tt < PIC:
        ev += [(tt, l) for l in IDLE]
        tt += 1000
    return ev

def run(sound, pfrac, purge, seed=1):
    rnd = random.Random(seed)
    o = sound - 0x02000000
    samples = 2 * L(rom, o - 4)
    idx = rom[o + 0x400:o + 0x400 + samples // 8]
    cb_lines = set(range(sound >> 4, (sound + 0x3FF >> 4) + 1))
    cache = {}
    miss = hit = 0
    first_after = []          # per picture: codebook misses / first uses
    s = 0                      # sample counter
    for pn in range(len(idx) * 8 * 1046 // PIC):
        pic = pictures[pn % len(pictures)]
        ev = picture_events(pic, pfrac, rnd)
        tp = 0.0
        while tp < PIC:        # PWM interrupts
            b = idx[(s // 8) % len(idx)]
            lines = DISP + PWM_CODE + PWM_GBR + STACK + [(sound + 4 * b) >> 4]
            if s % 8 == 7:
                lines.append((sound + 0x400 + s // 8) >> 4)
            ev += [(tp + 1, l) for l in lines]
            s += 1; tp += 1046
        ev.sort(key=lambda e: e[0])
        if purge: cache.clear()
        seen = set(); fm = fu = 0
        for _, l in ev:
            e = l & 63
            w = cache.get(e)
            if w is None:
                cache[e] = [l, None]; m = True
            elif w[0] == l: m = False
            elif w[1] == l: w[0], w[1] = l, w[0]; m = False
            else: w[0], w[1] = l, w[0]; m = True
            if l in cb_lines:
                if m: miss += 1
                else: hit += 1
                if l not in seen:
                    seen.add(l); fu += 1; fm += m
        first_after.append((fu, fm))
    return miss, hit, first_after

print('%d distinct pictures, records per picture %d-%d' % (
    len(pictures), min(len(p[1]) for p in pictures), max(len(p[1]) for p in pictures)))
for snd in sounds:
    for pf in pfracs:
        r = {}
        for purge in (True, False):
            r[purge] = run(snd, pf, purge)
        pics = len(r[True][2])
        mp, mn = r[True][0] / pics, r[False][0] / pics
        fu = sum(x[0] for x in r[False][2]) / pics
        fmn = sum(x[1] for x in r[False][2]) / pics
        print('sound %08X pfrac %.1f: %d pictures; codebook lines used per picture %.1f; '
              'codebook misses per picture: purge %.1f, no purge %.1f (saved %.1f); '
              'first uses that miss without purge %.1f of %.1f' % (
                  snd, pf, pics, fu, mp, mn, mp - mn, fmn, fu))
