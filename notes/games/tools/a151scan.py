# usage: python3 a151scan.py ROM REG [REG ...] [--global aN]
#   REG: 68000-side 32X register address in hex (e.g. A15102 A15103).
# Linear capstone disassembly of the whole ROM (skips 2 bytes on a decode
# failure), listing every instruction that touches one of the given addresses,
# either absolute or through an address register loaded with lea/movea #$A151xx
# earlier in the same straight-line run (tracking ends at rts/rte/jmp or when
# the register is overwritten). --global aN also lists every (d,aN) access whose
# displacement matches, for programs that keep a base register for good
# (Mars Check keeps a5 = $A15100). Data decoded as code can give false hits:
# check each one in context with m68k.py.
import capstone, re, sys
args = sys.argv[1:]
glob = None
if '--global' in args:
    i = args.index('--global'); glob = args[i + 1]; del args[i:i + 2]
d = open(args[0], 'rb').read()
want = {int(a, 16) for a in args[1:]}
md = capstone.Cs(capstone.CS_ARCH_M68K, capstone.CS_MODE_BIG_ENDIAN | capstone.CS_MODE_M68K_000)
base = {}
off = 0x200
ea = re.compile(r'(-?\$?[0-9a-f]+|-?\d+)?\((a[0-7])\)')
def val(s):
    if s is None: return 0
    neg = s.startswith('-'); s = s.lstrip('-')
    v = int(s[1:], 16) if s.startswith('$') else int(s)
    return -v if neg else v
while off < len(d) - 1:
    got = False
    for i in md.disasm(d[off:off + 0x4000], off):
        got = True
        ops = i.op_str
        hit = False
        for m in re.finditer(r'\$([0-9a-f]+)\.l', ops):
            if int(m.group(1), 16) & 0xFFFFFF in want: hit = True
        for m in ea.finditer(ops):
            r = m.group(2)
            if r in base and base[r] + val(m.group(1)) in want: hit = True
            if glob and r == glob and (0xA15100 + val(m.group(1))) in want: hit = True
        if hit:
            print('%06X %-8s %s' % (i.address, i.mnemonic, ops))
        parts = [p.strip() for p in ops.split(',')]
        if i.mnemonic in ('lea.l', 'movea.l') and len(parts) == 2:
            src, dst = parts
            m2 = re.match(r'#?\$([0-9a-f]+)(\.l)?$', src)
            if m2 and (int(m2.group(1), 16) & 0xFFFF00) == 0xA15100:
                base[dst] = int(m2.group(1), 16) & 0xFFFFFF
            else:
                base.pop(dst, None)
        elif parts and parts[-1] in base and i.mnemonic not in ('cmpa.w', 'cmpa.l', 'tst.l') and not parts[-1].startswith('('):
            base.pop(parts[-1], None)
        if i.mnemonic in ('rts', 'rte', 'jmp'):
            base.clear()
        off = i.address + i.size
    if not got:
        off += 2; base.clear()
