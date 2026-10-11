"""Aerobiz's two LZ decoders against each other, over the blocks the original ROM names.

usage: python3 -I aerobiz_lzcheck.py ROM LIBLZ.so [RAM.bin]

Runs tools/lz_decompress.py (the Aerobiz Ultimate project's Python port of the 68000 routine at
$003FEC) and disasm/sh2/master/lz.c (the SH-2 version, compiled for the PC) over every compressed
block that a `jsr $003FEC` in ROM names, and compares the output. Build the C side with

    printf '#define LZ_ITERS 1\n' > timing_config.h
    echo 'volatile unsigned long sh2_vint_count;' > shim.c
    gcc -O1 -fPIC -shared -I. -w -o liblz.so ../aerobiz-ultimate/disasm/sh2/master/lz.c shim.c

ROM is Aerobiz Supersonic (USA).gen. The optional RAM.bin is a 64 KB 68000 work RAM snapshot (offset 0
= $FF0000); blocks whose output sits in it at $FF1804 or $FF899C are compared with what the real
routine left there. The Aerobiz Ultimate repository is expected at ../aerobiz-ultimate (set AU_TOOLS to
its tools directory otherwise).

A call site is resolved when its destination push is `pea (RAM).l` (or another push) and the source
push just before it is `pea imm.l`, `move.l #imm,-(sp)`, `move.l (abs).l,-(sp)` (a ROM pointer) or
`move.l (a0,d0.l),-(sp)` after `movea.l #table,a0` (every table entry that the reference decodes
cleanly is tried). The rest compute their source and are not covered.

Result of 10 October 2026 on the original ROM: 123 call sites, 107 resolved (39 immediate, 46 through a
ROM pointer, 22 through 12 tables), 316 distinct blocks, 683,456 bytes out, largest 27,872 bytes, all
identical in both decoders; two blocks (2,272 bytes at $FF1804, 960 at $FF899C) equal the snapshot.
"""
import sys, struct, ctypes, collections
import os
sys.path.insert(0, os.environ.get('AU_TOOLS', os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..', '..', 'aerobiz-ultimate', 'tools')))
import lz_decompress as ref
rom = open(sys.argv[1], 'rb').read()
lib = ctypes.CDLL(sys.argv[2])
lib.lz_decompress.restype = ctypes.c_ulong
lib.lz_decompress.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_ulong]
padded = ctypes.create_string_buffer(rom + b'\0' * 4096, len(rom) + 4096)
out = ctypes.create_string_buffer(1 << 20)
L = lambda o: struct.unpack('>I', rom[o:o + 4])[0]

calls = [i for i in range(0, len(rom) - 5, 2) if rom[i:i + 6] == bytes.fromhex('4EB900003FEC')]
print('jsr $003FEC call sites:', len(calls))
kinds = collections.Counter()
direct = {}          # source address -> call sites
tables = {}          # table base -> call sites
unresolved = []

def is_push(o, size):
    """a 2-, 4- or 6-byte instruction that pushes one longword on the stack"""
    w = (rom[o] << 8) | rom[o + 1]
    if size == 2: return (w & 0xFFF0) == 0x2F00 or (w & 0xFFF8) == 0x2F08     # move.l Dn/An,-(a7)
    if size == 4: return (w & 0xFFF8) == 0x2F30 or (w & 0xFFF8) == 0x2F28 or w == 0x486E or (w & 0xFFF8) == 0x4868
    if size == 6: return w in (0x4879, 0x2F3C, 0x2F39)
    return False

def resolve(j):
    for dsize in (6, 4, 2):
        d = j - dsize
        if not is_push(d, dsize): continue
        for ssize in (6, 4):
            s = d - ssize
            w = (rom[s] << 8) | rom[s + 1]
            if ssize == 6 and w in (0x4879, 0x2F3C) and L(s + 2) < len(rom):
                return ('immediate source', L(s + 2))
            if ssize == 6 and w == 0x2F39 and L(s + 2) < len(rom) - 3 and L(L(s + 2)) < len(rom):
                return ('source through a ROM pointer', L(L(s + 2)))
            if ssize == 4 and rom[s:s + 4] == bytes.fromhex('2F300800'):
                for k in range(s - 2, s - 30, -2):
                    if rom[k:k + 2] == b'\x20\x7c':
                        return ('source from a pointer table', ('table', L(k + 2)))
    return ('source computed or not recognised', None)

for j in calls:
    kind, v = resolve(j)
    kinds[kind] += 1
    if v is None: unresolved.append(j)
    elif isinstance(v, tuple): tables.setdefault(v[1], []).append(j)
    else: direct.setdefault(v, []).append(j)
print(dict(kinds))

# expand the tables: take entries while they are plausible ROM pointers that the reference decodes
cand = dict(direct)
for base, js in tables.items():
    n = 0
    a = base
    while a + 4 <= len(rom):
        p = L(a)
        if not (0x200 <= p < len(rom)): break
        try:
            ref.decompress(rom, p, limit=1 << 20)
        except Exception:
            break
        cand.setdefault(p, []).append(('table %06X' % base))
        a += 4; n += 1
print('distinct compressed blocks named:', len(cand), '(%d directly, the rest through %d tables)' % (len(direct), len(tables)))

ok = bad = err = 0
total = big = 0
sizes = []
for s_, js in sorted(cand.items()):
    try:
        a = ref.decompress(rom, s_, limit=1 << 20)
    except Exception:
        err += 1; continue
    n = lib.lz_decompress(ctypes.addressof(padded) + s_, ctypes.addressof(out), 1 << 20)
    b = out.raw[:n] if n != 0xFFFFFFFFFFFFFFFF else None
    if b == a:
        ok += 1; total += len(a); big = max(big, len(a)); sizes.append(len(a))
    else:
        bad += 1; print('MISMATCH at $%06X: ref %d bytes, C %s' % (s_, len(a), n))
print('blocks decoded by both with identical output:', ok, '; different:', bad, '; reference failed:', err)
print('bytes compared: %d; largest block %d; median %d' % (total, big, sorted(sizes)[len(sizes) // 2] if sizes else 0))

# optional: compare with a 68000 work RAM snapshot (64 KB, offset 0 = $FF0000) taken from the running game,
# in which the real routine's last outputs sit at $FF1804 and $FF899C
if len(sys.argv) > 3:
    ram = open(sys.argv[3], 'rb').read()
    hits = []
    for s_ in sorted(cand):
        a = ref.decompress(rom, s_, limit=1 << 20)
        if len(a) < 64: continue
        for base in (0x1804, 0x899C):
            m = min(len(a), len(ram) - base)
            if ram[base:base + m] == a[:m] or ram[base:base + 64] == a[:64]:
                same = sum(1 for x, y in zip(ram[base:base + m], a[:m]) if x == y)
                hits.append((s_, base, len(a), same))
    print('blocks whose output appears in the RAM snapshot at $FF1804 or $FF899C:', len(hits))
    for h in hits: print('  source $%06X at RAM+$%04X: %d bytes decoded, %d equal to the snapshot' % h)
