"""Minimal SH-2 interpreter, just enough to run ECCO's CinePak decoder over the real ROM.

usage: python3 -I eccosim.py ROM OUTDIR [PICTURES]

Loads the SH-2 program (ROM $00C000, 0xA000 bytes) to 0x06000000, puts the stack at the top of
SDRAM and calls the frame walker at 0x06001788 with the stream at 0x22020000, exactly as the
Master's main loop does. The vertical-blank wait in the blit routine is answered "blanking".

Writes to OUTDIR:
  staging.bin  every decoded picture as it stood at the start of the blit (256 x 160 RGB555, big
               endian, 80 KB each)
  fb_last.bin  the frame buffer after the last blit
  pics.json    one record per picture: counters "GROUP.insn" (instructions), "GROUP.clk" (clocks by
               Hitachi's issue table, no memory waits), "GROUP.loaduse" (loads whose result is used
               by the next instruction: one more clock each), and "GROUP.rd_REGIONn" /
               "GROUP.wr_REGIONn" (memory accesses of n bytes; _ct = cache-through address)
Record k holds picture k's decoding plus the copy of picture k - 1, because the boundary is the
start of the blit: use records 1 and up for the copy.

Not a general emulator: it knows the opcodes this decoder uses and stops on any other.
Checked against PicoDrive: its output equals PicoDrive's screen for every distinct picture of a
1,500-frame run (notes/games/ecco/ANALYSIS.md).
"""
import sys, collections, json

rom = open(sys.argv[1], 'rb').read()
outdir = sys.argv[2]
MAXPIC = int(sys.argv[3]) if len(sys.argv) > 3 else 180
M = 0xFFFFFFFF

sdram = bytearray(0x40000)
sdram[0:0xA000] = rom[0xC000:0xC000 + 0xA000]
fb = bytearray(0x40000)          # 0x24000000..
io = {}
SENT = 0xDEAD0000

# accounting ------------------------------------------------------------
stats = collections.Counter()    # (group, what) -> count
cur_group = [""]
pic_marks = []                   # (picture index, snapshot of counters)

GROUPS = [
    ('blit', 0x06000220, 0x06000272),
    ('raster', 0x060002B4, 0x060003DC),
    ('raster_inter', 0x060003EC, 0x06000548),
    ('convert', 0x06000F5C, 0x06001010),
    ('strip', 0x060010C4, 0x06001380),
    ('walker', 0x06001788, 0x06001814),
]
def group_of(pc):
    for n, a, b in GROUPS:
        if a <= pc <= b:
            return n
    return 'other'
GCACHE = {}

def region(a):
    h = a >> 24
    if h in (0x06,):
        return 'sdram_c'
    if h in (0x26,):
        return 'sdram_ct'
    if h in (0x02,):
        return 'rom_c'
    if h in (0x22,):
        return 'rom_ct'
    if h in (0x04,):
        return 'fb_c'
    if h in (0x24,):
        return 'fb_ct'
    if h == 0x20:
        return 'io'
    return 'other'

def rd(a, n):
    a &= M
    h = a >> 24
    g = cur_group[0]
    stats[(g, 'rd_' + region(a) + str(n))] += 1
    if h in (0x06, 0x26):
        o = a & 0x3FFFF
        return int.from_bytes(sdram[o:o + n], 'big')
    if h in (0x02, 0x22):
        o = a & 0x3FFFFF
        return int.from_bytes(rom[o:o + n], 'big')
    if h in (0x04, 0x24):
        o = a & 0x3FFFF
        return int.from_bytes(fb[o:o + n], 'big')
    if h == 0x20:
        if (a & 0xFFFF) == 0x410A and n == 1:
            return 0x80          # VBLK set: the wait loop falls through at once
        return io.get(a, 0) & ((1 << (8 * n)) - 1)
    raise Exception('read %08x' % a)

def wr(a, v, n):
    a &= M
    h = a >> 24
    g = cur_group[0]
    stats[(g, 'wr_' + region(a) + str(n))] += 1
    v &= (1 << (8 * n)) - 1
    if h in (0x06, 0x26):
        o = a & 0x3FFFF
        sdram[o:o + n] = v.to_bytes(n, 'big')
    elif h in (0x04, 0x24):
        o = a & 0x3FFFF
        fb[o:o + n] = v.to_bytes(n, 'big')
    elif h == 0x20:
        io[a] = v
    else:
        raise Exception('write %08x' % a)

def s8(x): x &= 0xFF; return x - 256 if x & 0x80 else x
def s16(x): x &= 0xFFFF; return x - 65536 if x & 0x8000 else x
def s32(x): x &= M; return x - (1 << 32) if x & 0x80000000 else x

R = [0] * 16
SR = [0]       # T bit only (bit 0), others ignored
GBR = [0]; VBR = [0]; MACH = [0]; MACL = [0]; PR = [0]
PC = [0]
FETCH = collections.Counter()

def T(): return SR[0] & 1
def setT(b): SR[0] = (SR[0] & ~1) | (1 if b else 0)


# load-use tracking: a load followed at once by an instruction that reads its register costs one more clock
prev_dest = [None]

def load_dest(op):
    hi = op >> 12; n = (op >> 8) & 15; d = op & 15
    if hi == 0 and d in (0xC, 0xD, 0xE): return n
    if hi == 5: return n
    if hi == 6 and d in (0, 1, 2, 4, 5, 6): return n
    if hi == 8 and ((op >> 8) & 15) in (4, 5): return 0
    if hi == 9 or hi == 0xD: return n
    if hi == 0xC and ((op >> 8) & 15) in (4, 5, 6): return 0
    return None

def reads(op):
    hi = op >> 12; n = (op >> 8) & 15; m = (op >> 4) & 15; d = op & 15
    if hi == 0:
        if d in (4, 5, 6): return {m, n, 0}
        if d == 7: return {m, n}
        if d in (0xC, 0xD, 0xE): return {m, 0}
        return set()
    if hi == 1: return {m, n}
    if hi == 2 or hi == 3: return {m, n}
    if hi == 4: return {n}
    if hi == 5: return {m}
    if hi == 6: return {m}
    if hi == 7: return {n}
    if hi == 8:
        sub = n
        if sub in (0, 1): return {0, m}
        if sub in (4, 5): return {m}
        if sub == 8: return {0}
        return set()
    if hi == 0xC:
        if n in (0, 8, 9, 0xB): return {0}
        return set()
    return set()

def exec_tracked(op, pc):
    pd = prev_dest[0]
    if pd is not None and pd in reads(op):
        ld = load_dest(op)
        if not (ld == pd):          # a load into the same register does not wait
            stats[(cur_group[0], 'loaduse')] += 1
    prev_dest[0] = load_dest(op)
    return exec_op(op, pc)

class Stop(Exception): pass

def step():
    pc = PC[0]
    g = GCACHE.get(pc)
    if g is None:
        g = GCACHE[pc] = group_of(pc)
    cur_group[0] = g
    op = (sdram[pc & 0x3FFFF] << 8) | sdram[(pc & 0x3FFFF) + 1]
    stats[(g, 'insn')] += 1
    PC[0] = (pc + 2) & M
    cyc = exec_tracked(op, pc)
    stats[(g, 'clk')] += cyc

def delay(pc):
    """execute the delay-slot instruction at pc+2 (state changes count)."""
    cur = cur_group[0]
    op = (sdram[(pc + 2) & 0x3FFFF] << 8) | sdram[((pc + 2) & 0x3FFFF) + 1]
    stats[(cur, 'insn')] += 1
    save = PC[0]
    c = exec_tracked(op, pc + 2)
    stats[(cur, 'clk')] += c
    PC[0] = save

def exec_op(op, pc):
    n = (op >> 8) & 15; m = (op >> 4) & 15; d = op & 15
    hi = op >> 12
    if hi == 0:
        lo = op & 0xFF
        if d == 4: wr(R[n] + R[0], R[m], 1); return 1
        if d == 5: wr(R[n] + R[0], R[m], 2); return 1
        if d == 6: wr(R[n] + R[0], R[m], 4); return 1
        if d == 7:
            MACL[0] = (s32(R[n]) * s32(R[m])) & M; return 2
        if d == 0xC: R[n] = s8(rd(R[m] + R[0], 1)) & M; return 1
        if d == 0xD: R[n] = s16(rd(R[m] + R[0], 2)) & M; return 1
        if d == 0xE: R[n] = rd(R[m] + R[0], 4); return 1
        if op == 0x0009: return 1
        if op == 0x000B:
            t = PR[0]; delay(pc); PC[0] = t; return 2
        if op == 0x0008: setT(0); return 1
        if op == 0x0018: setT(1); return 1
        if lo == 0x02: R[n] = SR[0]; return 1
        if lo == 0x12: R[n] = GBR[0]; return 1
        if lo == 0x22: R[n] = VBR[0]; return 1
        if lo == 0x0A: R[n] = MACH[0]; return 1
        if lo == 0x1A: R[n] = MACL[0]; return 1
        if lo == 0x2A: R[n] = PR[0]; return 1
        if lo == 0x29: R[n] = T(); return 1
        raise Exception('op %04x at %08x' % (op, pc))
    if hi == 1:
        wr(R[n] + d * 4, R[m], 4); return 1
    if hi == 2:
        if d == 0: wr(R[n], R[m], 1); return 1
        if d == 1: wr(R[n], R[m], 2); return 1
        if d == 2: wr(R[n], R[m], 4); return 1
        if d == 4: R[n] = (R[n] - 1) & M; wr(R[n], R[m], 1); return 1
        if d == 5: R[n] = (R[n] - 2) & M; wr(R[n], R[m], 2); return 1
        if d == 6: R[n] = (R[n] - 4) & M; wr(R[n], R[m], 4); return 1
        if d == 8: setT((R[n] & R[m]) == 0); return 1
        if d == 9: R[n] &= R[m]; return 1
        if d == 0xA: R[n] ^= R[m]; return 1
        if d == 0xB: R[n] |= R[m]; return 1
        if d == 0xD: R[n] = ((R[m] << 16) | (R[n] >> 16)) & M; return 1
    if hi == 3:
        if d == 0: setT(R[n] == R[m]); return 1
        if d == 2: setT(R[n] >= R[m]); return 1
        if d == 3: setT(s32(R[n]) >= s32(R[m])); return 1
        if d == 6: setT(R[n] > R[m]); return 1
        if d == 7: setT(s32(R[n]) > s32(R[m])); return 1
        if d == 8: R[n] = (R[n] - R[m]) & M; return 1
        if d == 0xC: R[n] = (R[n] + R[m]) & M; return 1
    if hi == 4:
        lo = op & 0xFF
        if lo == 0x00: setT(R[n] >> 31); R[n] = (R[n] << 1) & M; return 1
        if lo == 0x01: setT(R[n] & 1); R[n] >>= 1; return 1
        if lo == 0x08: R[n] = (R[n] << 2) & M; return 1
        if lo == 0x09: R[n] >>= 2; return 1
        if lo == 0x18: R[n] = (R[n] << 8) & M; return 1
        if lo == 0x19: R[n] >>= 8; return 1
        if lo == 0x28: R[n] = (R[n] << 16) & M; return 1
        if lo == 0x29: R[n] >>= 16; return 1
        if lo == 0x10:
            R[n] = (R[n] - 1) & M; setT(R[n] == 0); return 1
        if lo == 0x11: setT(s32(R[n]) >= 0); return 1
        if lo == 0x15: setT(s32(R[n]) > 0); return 1
        if lo == 0x21:
            setT(R[n] & 1); R[n] = (s32(R[n]) >> 1) & M; return 1
        if lo == 0x0B:
            t = R[n]; PR[0] = (pc + 4) & M; delay(pc); PC[0] = t; return 2
        if lo == 0x2B:
            t = R[n]; delay(pc); PC[0] = t; return 2
        if lo == 0x0E: SR[0] = R[n] & 0x3F3; return 1
        if lo == 0x1E: GBR[0] = R[n]; return 1
        if lo == 0x2E: VBR[0] = R[n]; return 1
        if lo == 0x1A: MACL[0] = R[n]; return 1
        if lo == 0x2A: PR[0] = R[n]; return 1
        if lo == 0x22:
            R[n] = (R[n] - 4) & M; wr(R[n], PR[0], 4); return 1
        if lo == 0x26:
            PR[0] = rd(R[n], 4); R[n] = (R[n] + 4) & M; return 1
    if hi == 5:
        R[n] = rd(R[m] + d * 4, 4); return 1
    if hi == 6:
        if d == 0: R[n] = s8(rd(R[m], 1)) & M; return 1
        if d == 1: R[n] = s16(rd(R[m], 2)) & M; return 1
        if d == 2: R[n] = rd(R[m], 4); return 1
        if d == 3: R[n] = R[m]; return 1
        if d == 4:
            v = s8(rd(R[m], 1)) & M
            if m != n: R[m] = (R[m] + 1) & M
            R[n] = v; return 1
        if d == 5:
            v = s16(rd(R[m], 2)) & M
            if m != n: R[m] = (R[m] + 2) & M
            R[n] = v; return 1
        if d == 6:
            v = rd(R[m], 4)
            if m != n: R[m] = (R[m] + 4) & M
            R[n] = v; return 1
        if d == 7: R[n] = (~R[m]) & M; return 1
        if d == 0xC: R[n] = R[m] & 0xFF; return 1
        if d == 0xD: R[n] = R[m] & 0xFFFF; return 1
        if d == 0xE: R[n] = s8(R[m]) & M; return 1
        if d == 0xF: R[n] = s16(R[m]) & M; return 1
    if hi == 7:
        R[n] = (R[n] + s8(op)) & M; return 1
    if hi == 8:
        sub = (op >> 8) & 15; lo4 = op & 15; r = (op >> 4) & 15
        if sub == 0: wr(R[r] + lo4, R[0], 1); return 1
        if sub == 1: wr(R[r] + lo4 * 2, R[0], 2); return 1
        if sub == 4: R[0] = s8(rd(R[r] + lo4, 1)) & M; return 1
        if sub == 5: R[0] = s16(rd(R[r] + lo4 * 2, 2)) & M; return 1
        if sub == 8: setT(s32(R[0]) == s8(op)); return 1
        if sub in (9, 0xB, 0xD, 0xF):
            disp = s8(op) * 2
            tgt = (pc + 4 + disp) & M
            cond = T() if sub in (9, 0xD) else (1 - T())
            if sub in (9, 0xB):
                if cond: PC[0] = tgt; return 3
                return 1
            if cond:
                delay(pc); PC[0] = tgt; return 2
            return 1
    if hi == 9:
        R[n] = s16(rd(pc + 4 + (op & 0xFF) * 2, 2)) & M; return 1
    if hi == 0xA:
        disp = op & 0xFFF
        if disp & 0x800: disp -= 0x1000
        tgt = (pc + 4 + disp * 2) & M
        delay(pc); PC[0] = tgt; return 2
    if hi == 0xB:
        disp = op & 0xFFF
        if disp & 0x800: disp -= 0x1000
        tgt = (pc + 4 + disp * 2) & M
        PR[0] = (pc + 4) & M
        delay(pc); PC[0] = tgt; return 2
    if hi == 0xC:
        sub = (op >> 8) & 15
        if sub == 7: R[0] = ((pc + 4) & ~3) + (op & 0xFF) * 4; return 1
        if sub == 8: setT((R[0] & (op & 0xFF)) == 0); return 1
        if sub == 9: R[0] &= op & 0xFF; return 1
        if sub == 0xB: R[0] |= op & 0xFF; return 1
        if sub == 4: R[0] = s8(rd(GBR[0] + (op & 0xFF), 1)) & M; return 1
        if sub == 0: wr(GBR[0] + (op & 0xFF), R[0], 1); return 1
        if sub == 6: R[0] = rd(GBR[0] + (op & 0xFF) * 4, 4); return 1
    if hi == 0xD:
        R[n] = rd(((pc + 4) & ~3) + (op & 0xFF) * 4, 4); return 1
    if hi == 0xE:
        R[n] = s8(op) & M; return 1
    raise Exception('op %04x at %08x' % (op, pc))

# run the frame walker --------------------------------------------------
R[15] = 0x06040000
R[4] = 0x06010000; R[5] = 0x200; R[6] = 0x22020000
PR[0] = SENT
PC[0] = 0x06001788

STAGE = 0x06010000
snaps = []
last = collections.Counter()
pics = []
BLIT = 0x06000220
nins = 0
while PC[0] != SENT:
    if PC[0] == BLIT:
        # picture boundary: snapshot staging and counters
        snaps.append(bytes(sdram[STAGE & 0x3FFFF:(STAGE & 0x3FFFF) + 0x200 * 160]))
        cur = collections.Counter(stats)
        pics.append(cur - last)
        last = cur
        if len(snaps) >= MAXPIC:
            break
    step()
    nins += 1

import os
os.makedirs(outdir, exist_ok=True)
with open(os.path.join(outdir, 'staging.bin'), 'wb') as f:
    for s in snaps: f.write(s)
with open(os.path.join(outdir, 'fb_last.bin'), 'wb') as f:
    f.write(bytes(fb))
out = []
for p in pics:
    d = collections.defaultdict(int)
    for (g, w), v in p.items(): d['%s.%s' % (g, w)] = v
    out.append(d)
json.dump(out, open(os.path.join(outdir, 'pics.json'), 'w'))
print('pictures', len(snaps), 'instructions', nins)
