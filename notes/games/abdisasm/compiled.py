#!/usr/bin/env python3
"""Classify Aerobiz Supersonic's functions (AB-DISASM) as compiled C or hand-written.

usage: compiled.py AEROBIZ_DISASM_REPO [--list]
Reads every function module included by disasm/sections/section_0[0-3]*.asm,
takes its size from the "N bytes | $start-$end" header, and counts compiler marks.
"""
import re, sys, os, collections

root = sys.argv[1]
mods = []
for sec in sorted(os.listdir(os.path.join(root, 'disasm', 'sections'))):
    for line in open(os.path.join(root, 'disasm', 'sections', sec)):
        m = re.match(r'\s*include\s+"([^"]+)"', line)
        if m and 'modules/68k' in m.group(1):
            mods.append(m.group(1))

CALL = re.compile(r'^\s+((bsr(\.[bws])?|jsr)\s|dc\.w\s+\$4eb[9a],)', re.I)
CLEAN = re.compile(r'^\s+(addq\.[wl]\s+#\$?[0-9a-f]+,sp|lea\s+\$?[0-9a-f]+\(sp\),sp|adda\.[wl]\s+#\$?[0-9a-f]+,sp)', re.I)
PUSH = re.compile(r'^\s+(move|pea|clr)\.?[bwl]?\s+.*-\(sp\)\s*(;|$)', re.I)
STACKARG = re.compile(r'\$[0-9a-f]+\((sp|a6)\)', re.I)
rows = []
for mod in mods:
    path = os.path.join(root, mod)
    txt = open(path).read()
    lines = txt.split('\n')
    m = re.search(r'^[A-Za-z_]\w*:.*?;\s*\$([0-9A-Fa-f]{6})', txt, re.M) or re.search(r'\$([0-9A-Fa-f]{6})-\$[0-9A-Fa-f]{6}', txt)
    start = int(m.group(1), 16) if m else None
    size = None  # filled in below from the next function's start
    code = [l for l in lines if l.startswith((' ', '\t')) and l.strip() and not l.strip().startswith(';')]
    code = [re.sub(r';.*', '', l) for l in code]
    f = collections.Counter()
    for i, l in enumerate(code):
        s = l.strip().lower()
        if s.startswith('link'): f['link'] += 1
        if s.startswith('unlk'): f['unlk'] += 1
        if s.startswith('rte'): f['rte'] += 1
        if s.startswith('ext.l'): f['ext.l'] += 1
        if re.match(r'andi\.l\s+#\$(00)?ff,', s) or re.match(r'andi\.l\s+#\$0*ffff,', s): f['andi.l'] += 1
        if CALL.match(l):
            f['calls'] += 1
            if i + 1 < len(code) and CLEAN.match(code[i + 1]): f['cleanup_next'] += 1
            if i > 0 and PUSH.match(code[i - 1]): f['pushcall'] += 1
        if CLEAN.match(l): f['cleanup'] += 1
        if STACKARG.search(l) and not re.search(r'-\(sp\)', l): f['stackref'] += 1
        if re.search(r'\$00?c0000[048]\b|\$c0000[048]\b', s): f['vdpport'] += 1
        if re.search(r'\$a1110[0-9]|\$a00000|\$a01', s): f['z80'] += 1
    rows.append((mod, start, size, f))

starts = sorted(r[1] for r in rows if r[1] is not None)
nxt = {a: b for a, b in zip(starts, starts[1:] + [0x40000])}
rows = [(m, st, (nxt[st] - st) if st is not None else 0, f) for m, st, _, f in rows]

def compiled(f):
    return f['link'] > 0 or f['cleanup'] > 0 or f['stackref'] > 0

tot = collections.Counter(); bys = collections.Counter()
bydir = collections.defaultdict(lambda: [0, 0, 0, 0])
for mod, start, size, f in rows:
    c = compiled(f)
    d = mod.split('/')[3]
    tot['c' if c else 'h'] += 1
    bys['c' if c else 'h'] += size or 0
    bydir[d][0 if c else 1] += 1
    bydir[d][2 if c else 3] += size or 0
print(f"functions: {len(rows)}  compiled-looking {tot['c']} ({bys['c']} bytes)  other {tot['h']} ({bys['h']} bytes)")
print(f"link a6: {sum(1 for r in rows if r[3]['link'])} functions; calls {sum(r[3]['calls'] for r in rows)}, stack clean-ups {sum(r[3]['cleanup'] for r in rows)} in {sum(1 for r in rows if r[3]['cleanup'])} functions")
print(f"ext.l total {sum(r[3]['ext.l'] for r in rows)}, andi.l #$ff/#$ffff total {sum(r[3]['andi.l'] for r in rows)}")
print("by directory: compiled n / other n / compiled bytes / other bytes")
for d, v in sorted(bydir.items()):
    print(f"  {d:10s} {v[0]:4d} {v[1]:4d} {v[2]:7d} {v[3]:7d}")
if '--list' in sys.argv:
    for mod, start, size, f in rows:
        if not compiled(f):
            print('OTHER', f'${start:06X}' if start is not None else '?', size, mod, dict(f))
