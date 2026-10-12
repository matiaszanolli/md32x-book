#!/usr/bin/env python3
"""Recursive-descent helper for the Virtua Fighter SH-2 image (sh-elf-objdump listing).

usage: vfa.py LISTING BIN map | funcs | func ADDR | refs HEXVALUE

LISTING is the objdump listing of the image at VMA 0x06000000 (see sh2dis.sh), BIN the image.
Follows branches, bsr, jsr/jmp through literal-loaded registers; extra seeds can be given
in SEEDS below or via the VFA_SEEDS environment variable (comma separated hex).
It is a crude tool: code reached only through tables that load addresses some other way is missed,
so the code map is a lower bound.
"""
import re, struct, sys, os, collections

BASE = 0x06000000
LIT = re.compile(r'^(mov\.[wl])\s+0x([0-9a-f]+),r(\d+)\s*(?:!\s*([0-9a-f]+))?')

class Img:
    def __init__(self, listing, binf):
        self.d = open(binf, 'rb').read()
        self.ins = {}
        for line in open(listing):
            m = re.match(r'\s*([0-9a-f]+):\s+((?:[0-9a-f]{2} )+)\s*(.*)$', line)
            if not m:
                continue
            a = int(m.group(1), 16)
            self.ins[a] = m.group(3).split('!')[0].strip(), m.group(3)
    def w(self, a):
        o = a - BASE
        return struct.unpack('>H', self.d[o:o+2])[0] if 0 <= o <= len(self.d) - 2 else None
    def l(self, a):
        o = a - BASE
        return struct.unpack('>I', self.d[o:o+4])[0] if 0 <= o <= len(self.d) - 4 else None
    def txt(self, a):
        return self.ins[a][0] if a in self.ins else None

DELAY = ('bra', 'bsr', 'jmp', 'jsr', 'rts', 'rte', 'braf', 'bsrf', 'bt.s', 'bf.s')

def litval(img, a):
    """value loaded by a PC-relative mov at a, or None"""
    t = img.txt(a)
    if not t:
        return None
    m = re.match(r'mov\.([wl])\s+0x([0-9a-f]+),r(\d+)', t)
    if not m:
        return None
    src = int(m.group(2), 16)
    if m.group(1) == 'l':
        v = img.l(src)
    else:
        v = img.w(src)
        if v is not None and v & 0x8000:
            v |= 0xFFFF0000
    return int(m.group(3)), v

def plausible(img, a, maxn=400):
    """trial walk: straight line from a; True if it reaches rts/rte/jmp/bra-end without an undefined opcode"""
    n = 0
    while n < maxn:
        t = img.txt(a)
        if t is None or t.startswith('.word') or t.startswith('sleep') or t.startswith('trapa'):
            return False
        op = t.split()[0]
        n += 1
        if op in ('rts', 'rte', 'jmp', 'bra', 'braf'):
            if n < 2:
                return False
            d = img.txt(a + 2)
            return d is not None and not d.startswith('.word')
        a += 2
    return False

def descend(img, seeds, cand_seeds=()):
    code = {}
    funcs = set(seeds)
    calls = collections.defaultdict(set)
    work = [(s, s, {}) for s in seeds]
    tables = []
    def push(a, f, regs):
        work.append((a, f, dict(regs)))
    def addfn(v, regs=None):
        if v not in funcs:
            funcs.add(v); work.append((v, v, {}))
    for c in cand_seeds:
        if plausible(img, c):
            addfn(c)
    while work:
        a, f, regs = work.pop()
        while True:
            if code.get(a) == f or a in code and a in funcs and a != f:
                break
            if a not in img.ins:
                break
            t = img.txt(a)
            if t.startswith('.word'):
                break
            code[a] = f
            r = litval(img, a)
            if r:
                regs[r[0]] = r[1]
            else:
                m = re.match(r'mov\s+r(\d+),r(\d+)', t)
                if m:
                    regs[int(m.group(2))] = regs.get(int(m.group(1)))
                else:
                    m = re.match(r'(?:mov\.[lwb]|add|extu\.[bw]|exts\.[bw]|shl\w*|shar|sub|and|or|xor|neg|swap\.\w|mova|stc|sts)\s.*,r(\d+)$', t)
                    if m:
                        regs.pop(int(m.group(1)), None)
                    m = re.match(r'mov\.l\s+@\(r0,r(\d+)\),r(\d+)', t)
                    if m and regs.get(int(m.group(1))):
                        tables.append(regs[int(m.group(1))])
                    if t.startswith('mova'):
                        tables.append(int(t.split()[1].split(',')[0], 16))
                        regs.pop(0, None)
            op = t.split()[0]
            tgt = None
            m = re.match(r'(bra|bsr|bt|bf|bt\.s|bf\.s)\s+0x([0-9a-f]+)', t)
            if m:
                tgt = int(m.group(2), 16)
            m2 = re.match(r'(jmp|jsr)\s+@r(\d+)', t)
            ind = regs.get(int(m2.group(2))) if m2 else None
            if op in DELAY:
                if a + 2 in img.ins and not img.txt(a + 2).startswith('.word'):
                    code[a + 2] = f
                if op == 'bsr':
                    calls[f].add(tgt); addfn(tgt)
                    regs = {k: v for k, v in regs.items() if k >= 8}
                    a += 4; continue
                if op == 'jsr':
                    if ind and BASE <= ind < BASE + len(img.d):
                        calls[f].add(ind); addfn(ind)
                    regs = {k: v for k, v in regs.items() if k >= 8}
                    a += 4; continue
                if op == 'bsrf':
                    a += 4; continue
                if op == 'bra':
                    a = tgt; continue
                if op == 'jmp':
                    if ind and BASE <= ind < BASE + len(img.d):
                        push(ind, f, regs)
                    break
                if op in ('bt.s', 'bf.s'):
                    push(tgt, f, regs); a += 4; continue
                break
            if op in ('bt', 'bf'):
                push(tgt, f, regs); a += 2; continue
            a += 2
        if not work and tables:
            ts = tables; tables = []
            for tb in ts:
                k = 0
                while True:
                    v = img.l(tb + 4 * k)
                    if v is None or v & 1 or not (BASE <= v < BASE + len(img.d)) or not plausible(img, v):
                        break
                    addfn(v); k += 1
    return code, funcs, calls

def main():
    img = Img(sys.argv[1], sys.argv[2])
    seeds = [0x60001cc, 0x6000278, 0x6000120, 0x6000150, 0x6000498, 0x6000350,
             0x600856c, 0x6000528, 0x6000578]
    # table seeds
    for t, n in ((0x6000304, 16), (0x6000604, 33)):
        for i in range(n):
            v = img.l(t + 4 * i)
            if v and BASE <= v < BASE + len(img.d):
                seeds.append(v)
    for s in os.environ.get('VFA_SEEDS', '').split(','):
        if s:
            seeds.append(int(s, 16))
    cands = set()
    if os.environ.get('VFA_CANDS', '1') == '1':
        for a in img.ins:
            r = litval(img, a)
            if r and r[1] and BASE <= r[1] < BASE + len(img.d) and not r[1] & 1:
                cands.add(r[1])
    code, funcs, calls = descend(img, sorted(set(seeds)), sorted(cands))
    cmd = sys.argv[3]
    if cmd == 'map':
        addrs = sorted(code)
        runs = []
        s = p = addrs[0]
        for a in addrs[1:]:
            if a - p > 2:
                runs.append((s, p + 2)); s = a
            p = a
        runs.append((s, p + 2))
        for s, e in runs:
            print('%08x-%08x  %5d' % (s, e, e - s))
        print('code bytes', len(code) * 2, 'funcs', len(funcs))
    elif cmd == 'funcs':
        for f in sorted(funcs):
            n = sum(1 for a in code if code[a] == f)
            print('%08x  %5d bytes  callees: %s' % (f, n * 2, ' '.join('%x' % c for c in sorted(calls.get(f, [])))))
    elif cmd == 'refs':
        v = int(sys.argv[4], 16)
        for a in sorted(img.ins):
            r = litval(img, a)
            if r and r[1] == v:
                print('%08x %s' % (a, img.txt(a)), 'fn %x' % code.get(a, 0))
if __name__ == '__main__':
    main()
