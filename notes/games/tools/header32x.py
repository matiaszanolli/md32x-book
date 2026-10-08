#!/usr/bin/env python3
"""Parse and verify a 32X cartridge: MD header, checksum, 32X user header.

Usage: header32x.py ROM [ROM ...]

Checksum rule (src/howto/32x-header.md): the Master SH-2 sums words from
$000200 to the ROM end address stored at $1A4 and compares with $18E.
"""
import hashlib
import struct
import sys


def word(rom, off):
    return struct.unpack_from(">H", rom, off)[0]


def long_(rom, off):
    return struct.unpack_from(">I", rom, off)[0]


def text(rom, off, n):
    return rom[off:off + n].decode("ascii", "replace").rstrip()


def main(paths):
    for path in paths:
        rom = open(path, "rb").read()
        print(f"== {path}")
        print(f"   size {len(rom)} ({len(rom) * 8 // (1 << 20)} Mbit)  "
              f"md5 {hashlib.md5(rom).hexdigest()}")
        print(f"   $100 system  '{text(rom, 0x100, 16)}'")
        print(f"   $120 domestic '{text(rom, 0x120, 48)}'")
        print(f"   $150 overseas '{text(rom, 0x150, 48)}'")
        print(f"   $180 serial   '{text(rom, 0x180, 14)}'")
        print(f"   $190 devices  '{text(rom, 0x190, 16)}'"
              f"  $1F0 regions '{text(rom, 0x1F0, 3)}'")
        end = long_(rom, 0x1A4)
        stored = word(rom, 0x18E)
        last = min(end, len(rom) - 2)
        note = "" if end <= len(rom) - 2 else f" (file is {len(rom):X} bytes)"
        total = sum(word(rom, off) for off in range(0x200, last + 1, 2)) & 0xFFFF
        if stored == 0:
            ok = "zero: check skipped"
        elif total == stored:
            ok = "matches"
        else:
            ok = f"MISMATCH (sum {total:04X})"
        print(f"   $1A4 rom end  {end:06X}{note}   $18E checksum {stored:04X}  {ok}")
        name = rom[0x3C0:0x3D0].decode("ascii", "replace").rstrip()
        src, dst, size = long_(rom, 0x3D4), long_(rom, 0x3D8), long_(rom, 0x3DC)
        me, se, mvb, svb = (long_(rom, x) for x in (0x3E0, 0x3E4, 0x3E8, 0x3EC))
        print(f"   user hdr '{name}'  SH-2 image ${src:06X} -> SDRAM+${dst:06X}, "
              f"${size:06X} bytes")
        print(f"   entries M ${me:08X} S ${se:08X}   VBR M ${mvb:08X} S ${svb:08X}")


if __name__ == "__main__":
    main(sys.argv[1:])
