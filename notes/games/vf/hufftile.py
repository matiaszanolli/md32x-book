#!/usr/bin/env python3
"""Python port of Virtua Fighter's 68000 tile decompressor at $880D10 (Huffman-coded nibble runs, read from
disassembly; see M68K.md).  usage: hufftile.py ADDR [OUTFILE]   (ADDR = 68000 address, $9xxxxx = cartridge offset ADDR-$900000)
Returns the decompressed 32-bit words (tile rows, 8 longs = 1 tile), prints a summary."""
import sys, struct
ROM = open("/home/matias/Downloads/Sega-32x-Romset-us/Virtua Fighter (Japan, USA).32x", "rb").read()

def decode(off):
    p = off
    def u8():
        nonlocal p
        v = ROM[p]; p += 1; return v
    hdr = (ROM[p] << 8) | ROM[p+1]; p += 2
    xor = bool(hdr & 0x8000)
    count = ((hdr << 3) & 0xFFFF)      # a5: number of longs (tiles*8)
    if count & 0x8000: count -= 0x10000    # moveaw sign-extends; never expected negative
    # table build ($880DFE): entries are  FIRST (bit 7 set: low nibble = pixel value)  then any number of
    # (SECOND, CODE) pairs, SECOND < $80: bits 6-4 = run length - 1, bits 3-0 = code length (1-8), CODE = the code,
    # right-aligned.  A byte >= $80 where a SECOND is expected starts a new FIRST.  $FF ends the table.
    tab = [0] * 256                    # word entries indexed by the next 8 bits of the stream
    d0 = u8()
    while d0 != 0xFF:
        d7 = d0
        while True:
            d0 = u8()
            if d0 >= 0x80: break
            d7 = (d7 & 0x0F) | (d0 & 0x70)
            ln = d0 & 0x0F
            d7 |= ln << 8
            sh = 8 - ln
            c = u8() << sh
            for k in range(1 << sh):
                tab[(c + k) & 0xFF] = d7
    # bit buffer
    d5 = (u8() << 8) | u8()
    d6 = 16
    out = []; d4 = 0; d3 = 8; prev = 0
    remaining = count
    def emit_long(v):
        nonlocal prev
        if xor:
            prev ^= v; out.append(prev)
        else:
            out.append(v)
    while True:
        d7 = d6 - 8
        d1 = (d5 >> d7) & 0xFFFF
        d1 = d1 if d1 < 0x10000 else d1 & 0xFFFF
        if (d1 & 0xFF) >= 0xFC and (d1 >> 0) < 0x100 + 0:  # unreachable guard
            pass
        d1b = d1 & 0xFF if d7 >= 0 else d1
        # the asm: movew d5,d1; lsrw d7,d1; cmpib #-4,d1 (byte compare of low byte)
        d1 = ((d5 & 0xFFFF) >> d7) & 0xFFFF
        low = d1 & 0xFF
        if low >= 0xFC:
            # literal escape ($880DA6)
            d6 -= 6
            if d6 < 9: d6 += 8; d5 = ((d5 << 8) & 0xFFFF) | u8()
            d6 -= 7
            d1 = ((d5 & 0xFFFF) >> d6) & 0xFFFF
            d0 = d1; d1 &= 0x0F; d0 &= 0x70
            if not (d6 >= 9):
                d6 += 8; d5 = ((d5 << 8) & 0xFFFF) | u8()
            cnt = d0 >> 4; nib = d1
        else:
            e = tab[low]
            length = (e >> 8) & 0xFF
            d6 -= length
            if d6 < 9: d6 += 8; d5 = ((d5 << 8) & 0xFFFF) | u8()
            nib = e & 0x0F; cnt = (e & 0xF0) >> 4
        for _ in range(cnt + 1):
            d4 = ((d4 << 4) | nib) & 0xFFFFFFFF
            d3 -= 1
            if d3 == 0:
                emit_long(d4)
                remaining -= 1
                if remaining == 0:
                    return out, p
                d4 = 0; d3 = 8
    return out, p

if __name__ == '__main__':
    a = int(sys.argv[1], 16)
    off = a - 0x900000 if a >= 0x900000 else a - 0x880000
    out, end = decode(off)
    print("decoded %d longs (%d tiles), consumed up to cart offset %x (%d bytes)" % (len(out), len(out)//8, end, end-off))
    if len(sys.argv) > 2:
        open(sys.argv[2], 'wb').write(b''.join(struct.pack('>I', x) for x in out))
