#!/usr/bin/env python3
"""Patch a copy of the VRD project's PicoDrive (pico/32x/memory.c) so that,
with PD_M68K_LOG=FILE, every 68000 access to $A15100-$A151FF (32X system
registers and 32X VDP registers) and to the $A130F0 mapper bytes is logged as
  frame pc R|W size address value cycles_in_frame
Reads are logged only when (pc, address, value) differs from the last logged
read of that register, so polling loops show once per change.
Writes to the 32X palette ($A15200) are counted, not logged.
usage: patch_m68klog.py PICODRIVE_DIR"""
import sys, re
p = sys.argv[1] + '/pico/32x/memory.c'
s = open(p, newline='').read()
nl = '\r\n' if '\r\n' in s else '\n'
helper = nl.join([
'#include <stdio.h>', '#include <stdlib.h>',
'static FILE *vf_log; static int vf_init; static unsigned vf_lpc[256], vf_lval[256]; static unsigned long vf_palw;',
'static void vf_pal_dump(void){ if (vf_log) fprintf(vf_log, "# palette writes: %lu\\n", vf_palw); fclose(vf_log);}',
'static void vf_ev(int w, int size, u32 a, u32 d) {',
'  if (!vf_init) { const char *f = getenv("PD_M68K_LOG"); vf_init = 1; if (f) { vf_log = fopen(f, "w"); if (vf_log) atexit(vf_pal_dump);} }',
'  if (!vf_log) return;',
'  a &= 0xffff;',
'  if (a >= 0x5200 && a < 0x5400) { vf_palw += w; return; }',
'  if ((a < 0x5100 || a >= 0x5200) && a != 0x30f0 && a != 0x30f1) return;',
'  if (!w) { unsigned i = a & 0xff; if (vf_lpc[i] == SekPc && vf_lval[i] == (d & 0xffff) + 1) return; vf_lpc[i] = SekPc; vf_lval[i] = (d & 0xffff) + 1; }',
'  fprintf(vf_log, "%d %06x %c %d %06x %0*x %u\\n", Pico.m.frame_count, SekPc, w ? \'W\' : \'R\', size, 0xa10000 | a, size * 2, d & (size == 1 ? 0xff : 0xffff), (unsigned)(SekCyclesDone() - Pico.t.m68c_frame_start));',
'}',
''])
# insert helper before first function that uses it: after the includes -> before p32x_reg_read16
anchor = 'static u32 p32x_reg_read16(u32 a)'
assert s.count(anchor) == 1
s = s.replace(anchor, helper + anchor)
def rep(old, new, count=1):
    global s
    assert s.count(old) == count, (old, s.count(old))
    s = s.replace(old, new)
# reads after ADEN
rep('''out_16to8:
  if (a & 1)
    d &= 0xff;
  else
    d >>= 8;

out:
  elprintf(EL_32X, "m68k 32x r8  [%06x]   %02x @%06x", a, d, SekPc);''',
'''out_16to8:
  if (a & 1)
    d &= 0xff;
  else
    d >>= 8;

out:
  vf_ev(0, 1, a, d);
  elprintf(EL_32X, "m68k 32x r8  [%06x]   %02x @%06x", a, d, SekPc);''')
rep('''out:
  elprintf(EL_32X, "m68k 32x r16 [%06x] %04x @%06x", a, d, SekPc);
#ifdef __LIBRETRO__''', '''out:
  vf_ev(0, 2, a, d);
  elprintf(EL_32X, "m68k 32x r16 [%06x] %04x @%06x", a, d, SekPc);
#ifdef __LIBRETRO__''')
rep('''static void PicoWrite8_32x_on(u32 a, u32 d)
{
''', '''static void PicoWrite8_32x_on(u32 a, u32 d)
{
  vf_ev(1, 1, a, d);
''')
rep('''static void PicoWrite16_32x_on(u32 a, u32 d)
{
''', '''static void PicoWrite16_32x_on(u32 a, u32 d)
{
  vf_ev(1, 2, a, d);
''')
# before ADEN
rep('''u32 PicoRead8_32x(u32 a)
{
  u32 d = 0;
''', '''u32 PicoRead8_32x(u32 a)
{
  u32 d = 0;
''')
rep('''out:
  elprintf(EL_32X, "m68k 32x r8  [%06x]   %02x @%06x", a, d, SekPc);
  return d;
}''', '''out:
  vf_ev(0, 1, a, d);
  elprintf(EL_32X, "m68k 32x r8  [%06x]   %02x @%06x", a, d, SekPc);
  return d;
}''')
rep('''out:
  elprintf(EL_32X, "m68k 32x r16 [%06x] %04x @%06x", a, d, SekPc);
  return d;
}''', '''out:
  vf_ev(0, 2, a, d);
  elprintf(EL_32X, "m68k 32x r16 [%06x] %04x @%06x", a, d, SekPc);
  return d;
}''')
rep('''void PicoWrite8_32x(u32 a, u32 d)
{
''', '''void PicoWrite8_32x(u32 a, u32 d)
{
  vf_ev(1, 1, a, d);
''')
rep('''void PicoWrite16_32x(u32 a, u32 d)
{
''', '''void PicoWrite16_32x(u32 a, u32 d)
{
  vf_ev(1, 2, a, d);
''')
# mapper bytes
for nm in ['PicoWrite8_32x_on_io', 'PicoWrite8_32x_on_io_cd', 'PicoWrite8_32x_on_io_ssf2']:
    rep('static void %s(u32 a, u32 d)\n{\n' % nm if '\r\n' not in s else 'static void %s(u32 a, u32 d)\r\n{\r\n' % nm,
        ('static void %s(u32 a, u32 d)\n{\n  vf_ev(1, 1, a, d);\n' % nm) if '\r\n' not in s else ('static void %s(u32 a, u32 d)\r\n{\r\n  vf_ev(1, 1, a, d);\r\n' % nm))
open(p, 'w', newline='').write(s)
print("patched", p)
