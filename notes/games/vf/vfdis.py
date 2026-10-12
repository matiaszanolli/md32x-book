#!/usr/bin/env python3
"""68000 disassembly of Virtua Fighter (32X) by 68000 address.

usage: vfdis.py ADDR LEN [--bank N] [--ram FILE[:BASE]]
  ADDR, LEN: hex.  ADDR in $880000-$8FFFFF reads the cartridge at ADDR-$880000
  ($880000 window, fixed first megabyte); $900000-$9FFFFF reads cartridge
  N*$100000 + (ADDR-$900000) (banked window, --bank N, default 1);
  $FF0000-$FFFFFF reads a work-RAM image (default: the boot copy of cartridge
  $1A23E at $FF0000, 0x2BB8 bytes; or --ram FILE[:BASE] for an emulator dump).
Uses GNU objdump (m68k-linux-gnu-objdump), which decodes the 68000 fully.
"""
import sys, subprocess, tempfile, os
import os
ROM = os.environ.get("VFROM", "/home/matias/Downloads/Sega-32x-Romset-us/Virtua Fighter (Japan, USA).32x")

def bytes_at(rom, addr, n, bank=1, ram=None):
    if 0x880000 <= addr < 0x900000:
        o = addr - 0x880000
        return rom[o:o+n]
    if 0x900000 <= addr < 0xA00000:
        o = bank*0x100000 + addr - 0x900000
        return rom[o:o+n]
    if 0xFF0000 <= addr <= 0xFFFFFF:
        if ram is None:
            ram = (0xFF0000, rom[0x1A23E:0x1A23E+0x2BB8])
        base, data = ram
        return data[addr-base:addr-base+n]
    raise SystemExit("address not mapped")

def main():
    a = sys.argv[1:]
    bank = 1; ram = None
    if '--bank' in a:
        i = a.index('--bank'); bank = int(a[i+1], 0); del a[i:i+2]
    if '--ram' in a:
        i = a.index('--ram'); s = a[i+1]; del a[i:i+2]
        f, _, b = s.partition(':')
        ram = (int(b, 16) if b else 0xFF0000, open(f, 'rb').read())
    rom = open(ROM, 'rb').read()
    addr = int(a[0], 16); n = int(a[1], 16)
    data = bytes_at(rom, addr, n + 16, bank, ram)
    with tempfile.NamedTemporaryFile(delete=False) as t:
        t.write(data); p = t.name
    out = subprocess.run(["m68k-linux-gnu-objdump", "-D", "-b", "binary", "-m", "m68k:68000",
                          "--adjust-vma=0x%x" % addr, p], capture_output=True, text=True).stdout
    os.unlink(p)
    import re
    lines = out.split("<.data>:\n", 1)[-1].split("\n")
    res = []
    for ln in lines:
        m = re.match(r'\s*([0-9a-f]+):\t(.*)$', ln)
        if not m:
            continue
        ad = int(m.group(1), 16)
        parts = m.group(2).split("\t")
        if len(parts) == 1:
            continue          # continuation line (extra opcode words)
        if ad >= addr + n:
            break
        txt = parts[-1]
        # decimal immediates -> hex, so constants can be read
        def hx(mm):
            v = int(mm.group(1))
            return '#-$%x' % -v if v < 0 and v >= -0x80 else ('#$%x' % (v & 0xffffffff) if v < 0 else '#$%x' % v)
        txt = re.sub(r'#(-?\d+)', hx, txt)
        res.append("%06x  %s" % (ad, txt))
    print("\n".join(res))
main()
