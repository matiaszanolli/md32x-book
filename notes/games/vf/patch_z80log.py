#!/usr/bin/env python3
"""Third patch (after patch_m68klog.py / patch_vdplog.py): with PD_Z80_LOG=FILE log every 68000 write into the
Z80 area ($A00000-$A0FFFF) as   frame pc Z|Y|P|B ...   Z addr val (Z80 RAM), Y port val (YM2612 $A04000-3, port 0-3),
P val (PSG via $A07F11 mirror), B val (Z80 bank register), and the 68000 writes to the PSG at $C00011 and the YM2612
busy reads are not logged.   usage: patch_z80log.py PICODRIVE_DIR"""
import sys
p = sys.argv[1] + '/pico/memory.c'
s = open(p, newline='').read()
nl = '\r\n' if '\r\n' in s else '\n'
def rep(old, new):
    global s
    old = old.replace('\n', nl); new = new.replace('\n', nl)
    assert s.count(old) == 1, old
    s = s.replace(old, new)
rep('''static void PicoWrite8_z80(u32 a, u32 d)
{''', '''#include <stdio.h>
#include <stdlib.h>
static FILE *zl_log; static int zl_init;
#define ZL(...) do { if (!zl_init) { const char *f = getenv("PD_Z80_LOG"); zl_init = 1; if (f) zl_log = fopen(f, "w"); } if (zl_log) fprintf(zl_log, __VA_ARGS__); } while (0)
static void PicoWrite8_z80(u32 a, u32 d)
{''')
rep('''  if ((a & 0x4000) == 0x0000) { // z80 RAM
    PicoMem.zram[a & 0x1fff] = (u8)d;
    return;
  }
  if ((a & 0x6000) == 0x4000) { // FM Sound''', '''  if ((a & 0x4000) == 0x0000) { // z80 RAM
    ZL("%d %06x Z %04x %02x\\n", Pico.m.frame_count, SekPc, a & 0x1fff, d & 0xff);
    PicoMem.zram[a & 0x1fff] = (u8)d;
    return;
  }
  if ((a & 0x6000) == 0x4000) { // FM Sound
    ZL("%d %06x Y %d %02x\\n", Pico.m.frame_count, SekPc, a & 3, d & 0xff);''')
rep('''  if ((a & 0x7ff9) == 0x7f11) { // PSG Sound
    psg_write_68k(d);''', '''  if ((a & 0x7ff9) == 0x7f11) { // PSG Sound
    ZL("%d %06x P %02x\\n", Pico.m.frame_count, SekPc, d & 0xff);
    psg_write_68k(d);''')
open(p, 'w', newline='').write(s)
print('ok')
