#!/usr/bin/env python3
"""Python port of Virtua Fighter's byte-oriented LZ decoder at $881038 (read from the disassembly; same bit layout as
the Kosinski format used in Sonic games, but see the end test).   usage: kosdec.py ADDR  (ADDR = $9xxxxx banked window or $88xxxx)"""
import sys
ROM = open("/home/matias/Downloads/Sega-32x-Romset-us/Virtua Fighter (Japan, USA).32x", "rb").read()
def decode(off):
    p = off; out = bytearray()
    def u8():
        nonlocal p
        v = ROM[p]; p += 1; return v
    desc = u8(); left = 8
    def bit():
        nonlocal desc, left
        if left == 0:
            desc = u8(); left = 8
        b = desc & 1; desc >>= 1; left -= 1
        return b
    while True:
        if bit():
            out.append(u8()); continue
        if bit():
            lo = u8(); hi = u8()
            w = (hi << 8) | lo
            if w == 0: break
            off_ = (w >> 3) - 0x2000          # arithmetic shift of $FFFF0000|w
            cnt = lo & 7
            if cnt == 0:
                cnt = u8() + 1                 # extended count byte: copy cnt bytes
            else:
                cnt += 1 + 0                   # asm: addqw #1,d3 then dbf copies d3+1  => cnt+2 bytes
                cnt = (lo & 7) + 2
        else:
            c = (bit() << 1) | bit()
            off_ = u8() - 256
            cnt = c + 2
        for _ in range(cnt):
            out.append(out[-(-off_)]) if False else out.append(out[len(out) + off_])
    return bytes(out), p
if __name__ == '__main__':
    a = int(sys.argv[1], 16)
    off = a - 0x900000 if a >= 0x900000 else a - 0x880000
    d, end = decode(off)
    print("%d bytes from %d packed (ends at cart %x)" % (len(d), end - off, end))
