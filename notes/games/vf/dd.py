#!/usr/bin/env python3
"""dd.py LISTING BIN START END [SYMS]: compact disassembly of an address range.
Strips the hex bytes, marks PC-relative literal-pool words as .long/.word data (resolved values shown on the loads),
and annotates literal values with names from SYMS (lines 'HEXADDR name'; default syms.txt next to this script)."""
import sys, re, os, struct
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import vfa
img = vfa.Img(sys.argv[1], sys.argv[2])
s = int(sys.argv[3], 16); e = int(sys.argv[4], 16)
symf = sys.argv[5] if len(sys.argv) > 5 else os.path.join(os.path.dirname(os.path.abspath(__file__)), 'syms.txt')
syms = {}
if os.path.exists(symf):
    for l in open(symf):
        l = l.split('#')[0].split()
        if len(l) >= 2: syms[int(l[0], 16)] = l[1]
def nm(v):
    if v in syms: return ' <%s>' % syms[v]
    return ''
# pool words: targets of pc-relative loads / mova
pool = {}
for a in img.ins:
    t = img.txt(a)
    m = re.match(r'mov\.([wl])\s+0x([0-9a-f]+),r\d+', t)
    if m:
        pool[int(m.group(2), 16)] = m.group(1)
    elif t.startswith('mova'):
        pool.setdefault(int(t.split()[1].split(',')[0], 16), 'a')
a = s
while a <= e:
    t = img.txt(a)
    if t is None: a += 2; continue
    if a in pool and pool[a] == 'l' and a % 4 == 0:
        v = img.l(a); print('%08x  .long 0x%08x%s' % (a, v, nm(v))); a += 4; continue
    if a in pool and pool[a] == 'w':
        v = img.w(a); print('%08x  .word 0x%04x' % (a, v)); a += 2; continue
    full = img.ins[a][1]
    c = ''
    if '!' in full:
        c = full.split('!')[1].strip()
        try: c = '  ! %s%s' % (c, nm(int(c, 16)))
        except ValueError: c = '  ! ' + c
    m = re.match(r'(.*?)\s+0x([0-9a-f]+)$', t)
    tt = t
    if m and t.split()[0] in ('bra', 'bsr', 'bt', 'bf', 'bt.s', 'bf.s', 'jmp'):
        tt = '%s 0x%s%s' % (m.group(1), m.group(2), nm(int(m.group(2), 16)))
    print('%08x  %s%s' % (a, tt, c))
    a += 2
