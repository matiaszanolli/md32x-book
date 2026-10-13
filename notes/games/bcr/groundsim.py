# usage: python3 groundsim.py ROM DUMP.txt
# Replays BC Racers' ground (span) loop for one picture over real data and
# counts what it costs the cache. DUMP.txt is the output of a debug script run
# from a race save state (see ANALYSIS.md, "Ground cache simulation"): lines
# "ADDR: bb bb ..." from `read master` of the row table 0x26032EB4 (1 KB), the
# tile table 0x260332B4 (4 KB), the map in the frame buffer 0x24012E00
# (32 KB) and the haze table pointer 0x260348D8.
# The loop arithmetic is that of 0x0600252E (haze) and 0x0600259E (plain);
# the Master draws rows 0-31 (the first 8 with haze), the Slave rows 32-63.
# Cache: SH7604, 4 KB, 4 ways, 64 entries of 16-byte lines, true LRU (the chip
# uses a pseudo-LRU), write-through without allocation. Only cached-area
# addresses (A31-A29 = 000) go through it: the frame buffer map (0x24...) is
# read cache-through and the stores go to 0x24..., so neither touches it. The
# loop's own instruction fetches (one per two instructions) are included.
# Each CPU starts with an empty cache ("cold"), which is close to the game,
# whose four logic steps run between two pictures; a second pass ("warm") is
# also given.
import sys, collections

rom = open(sys.argv[1], 'rb').read()
mem = {}
for l in open(sys.argv[2]):
    if ':' not in l: continue
    a, rest = l.split(':', 1)
    try: a = int(a, 16)
    except ValueError: continue
    for i, x in enumerate(rest.split()): mem[a + i] = int(x, 16)

def rd(a, n):
    p = a & 0x1fffffff
    if 0x02000000 <= p < 0x02400000:
        b = rom[p - 0x02000000:p - 0x02000000 + n]
    else:
        q = p | 0x20000000
        b = bytes(mem[q + i] for i in range(n))
    return int.from_bytes(b, 'big')

def sext(v, bits):
    return v - (1 << bits) if v & (1 << (bits - 1)) else v

class Cache:
    def __init__(self): self.sets = [[] for _ in range(64)]
    def access(self, a):
        e = (a >> 4) & 63; t = a >> 10; w = self.sets[e]
        if t in w: w.remove(t); w.insert(0, t); return True
        w.insert(0, t)
        if len(w) > 4: w.pop()
        return False

ROWS = 0x26032EB4; TILES = 0x060332B4; MAP = 0x24012E00
haze = rd(0x260348D8, 4) + 0x780
HAZE_CODE = range(0x0600254C, 0x0600258E, 4)
PLAIN_CODE = range(0x060025B8, 0x060025F8, 4)

def run(rows, haze_rows, cache, st):
    r1 = haze
    for n, row in enumerate(rows):
        e = ROWS + 16 * row
        r5 = (rd(e, 4) << 9) & 0xffffffff; r6 = (rd(e + 4, 4) << 9) & 0xffffffff
        r7 = (rd(e + 8, 4) << 2) & 0xffffffff; r8 = (rd(e + 12, 4) << 2) & 0xffffffff
        hz = n < haze_rows
        code = HAZE_CODE if hz else PLAIN_CODE
        for _ in range(160):
            for a in code:
                st['fetch', cache.access(a)] += 1
            r0 = ((r6 & 0xFE0000) >> 9) + ((r5 & 0xFE0000) >> 16)
            st['fb read'] += 1
            m = rd(MAP + r0, 2)
            for a in (TILES + sext(m, 16), TILES + sext(m, 16) + 4):
                st['sdram: tile table', cache.access(a)] += 1
            r9 = rd(TILES + sext(m, 16), 4); r10 = rd(TILES + sext(m, 16) + 4, 4)
            r11 = ((r6 & 0x1F000) << 2) & 0xffffffff
            r0 = ((((r5 & 0x1F000) >> 3) | r11) >> 8)
            r5 = (r5 + r7) & 0xffffffff
            a = (r10 + r0) & 0xffffffff
            st['cart: offset tables', cache.access(a)] += 1
            off = sext(rd(a, 2), 16)
            a = (r9 + off) & 0xffffffff
            st['cart: texels', cache.access(a)] += 1
            tx = sext(rd(a, 1), 8)
            if hz:
                a = (r1 + tx) & 0xffffffff
                st['cart: haze table', cache.access(a)] += 1
            r6 = (r6 + r8) & 0xffffffff
            st['fb write'] += 1
        if hz: r1 -= 0x100

for cpu, rows, hz in (('Master', range(0, 32), 8), ('Slave', range(32, 64), 0)):
    c = Cache()
    for p in ('cold', 'warm'):
        st = collections.Counter()
        run(rows, hz, c, st)
        tex = len(rows) * 160
        print('%s, %s cache: %d texels' % (cpu, p, tex))
        for k in sorted(set(x[0] for x in st if isinstance(x, tuple))):
            h, m = st[k, True], st[k, False]
            print('  %-20s %7d accesses %6d misses (%.3f a texel)' % (k, h + m, m, m / tex))
        cart = sum(v for k, v in st.items() if isinstance(k, tuple) and not k[1] and k[0].startswith('cart'))
        sd = sum(v for k, v in st.items() if isinstance(k, tuple) and not k[1] and not k[0].startswith('cart'))
        print('  frame buffer: %d reads, %d writes' % (st['fb read'], st['fb write']))
        print('  bus clocks by the manual (min-max): cart fills %d-%d, SDRAM fills %d, FB reads %d-%d, FB writes %d-%d'
              % (cart * 64, cart * 136, sd * 12, st['fb read'] * 7, st['fb read'] * 14, st['fb write'] * 3, st['fb write'] * 5))
