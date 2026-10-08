#!/usr/bin/env python3
"""usage: vresscan.py ROM [ROM ...]

Whole-ROM scan for the two known defects of Sega's VRES sample (32X-TIA1):

  RV   the RV test after the VRES clear: which byte or word of 0x20004006 it
       reads. Matches 'clear VRES (write offset 20) then read offset 6 or 7 and
       tst #1', through GBR (mov.w r0,@(20,gbr) / mov.b @(n,gbr),r0) or through
       a register (mov.w r0,@(20,Rn) / mov.b|mov.w @(n,Rm),r0). Up to 6
       instructions may sit between the clear and the read.
  SLIP the CHCR0 store: 'mov.l @(disp,PC),Rn' loading the literal 0x000044E0,
       followed by 'mov.l r0,@Rn', which writes 0 to address 0x44E0 instead of
       writing 0x44E0 to CHCR0.

Addresses are printed as cartridge offsets; add the load address (for example
the user header's SDRAM destination) to get SH-2 addresses. A linear scan, so
check each hit in a disassembly (sh2dis.sh).
"""
import struct, sys

def words(d):
    return [struct.unpack_from('>H', d, i)[0] for i in range(0, len(d) - 1, 2)]

def scan(path):
    d = open(path, 'rb').read()
    w = words(d)
    hits = []
    for i, op in enumerate(w):
        # VRES clear: mov.w r0,@(20,gbr) = C10A ; mov.w r0,@(20,Rn) = 81nA (disp 10 words)
        if op == 0xC10A or (op & 0xFF0F) == 0x810A:
            for j in range(i + 1, min(i + 8, len(w) - 1)):
                o = w[j]
                kind = None
                if o in (0xC406, 0xC407):                 # mov.b @(6|7,gbr),r0
                    kind = 'byte %d via GBR' % (o & 0xF)
                elif o == 0xC503:                         # mov.w @(3*2,gbr),r0
                    kind = 'word 6 via GBR'
                elif (o & 0xFF00) == 0x8400 and (o & 0xF) in (6, 7):   # mov.b @(n,Rm),r0
                    kind = 'byte %d via r%d' % (o & 0xF, (o >> 4) & 0xF)
                elif (o & 0xFF0F) == 0x8503:              # mov.w @(6,Rm),r0
                    kind = 'word 6 via r%d' % ((o >> 4) & 0xF)
                if kind and w[j + 1] == 0xC801:           # tst #1,r0
                    hits.append((2 * j, 'RV   ' + kind))
                    break
        # SLIP: mov.l @(disp,PC),Rn = DnXX
        if (op & 0xF000) == 0xD000 and i + 1 < len(w):
            n = (op >> 8) & 0xF
            lit = ((2 * i + 4) & ~3) + (op & 0xFF) * 4
            if lit + 4 <= len(d) and struct.unpack_from('>I', d, lit)[0] == 0x44E0 \
                    and w[i + 1] == (0x2002 | (n << 8)):  # mov.l r0,@Rn
                hits.append((2 * i, 'SLIP literal 0x44E0 into r%d, then mov.l r0,@r%d' % (n, n)))
    return sorted(set(hits))

for p in sys.argv[1:]:
    print('==', p)
    for off, what in scan(p):
        print('   $%06X  %s' % (off, what))
