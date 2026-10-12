#!/usr/bin/env python3
"""Second patch for the PicoDrive copy (after patch_m68klog.py): with PD_VDP_LOG=FILE logs every
Mega Drive VDP register write and every 68000-to-VDP / fill / copy DMA command as
  frame pc V reg value                      (register write)
  frame pc D type dest len src2 inc         (DMA: src2 = byte source address, from 68000 side)
  frame pc F type dest len                  (DMA fill start)
and, with PD_VDP_DUMP=PREFIX and PD_VDP_DUMP_FRAMES=a,b,c, writes PREFIX_FRAME.{vram,cram,vsram,reg}
at the start of those frames.   usage: patch_vdplog.py PICODRIVE_DIR"""
import sys
d = sys.argv[1]
p = d + '/pico/videoport.c'
s = open(p, newline='').read()
nl = '\r\n' if '\r\n' in s else '\n'
def rep(old, new):
    global s
    old = old.replace('\n', nl); new = new.replace('\n', nl)
    assert s.count(old) == 1, old
    s = s.replace(old, new)
helper = '''#include <stdio.h>
#include <stdlib.h>
static FILE *vl_log; static int vl_init;
static void vl_open(void) { const char *f = getenv("PD_VDP_LOG"); vl_init = 1; if (f) vl_log = fopen(f, "w"); }
#define VL(...) do { if (!vl_init) vl_open(); if (vl_log) fprintf(vl_log, __VA_ARGS__); } while (0)
'''
rep('static void DmaSlow(int len, u32 source)\n{', helper + 'static void DmaSlow(int len, u32 source)\n{')
rep('''  elprintf(EL_VDPDMA, "DmaSlow[%i] %06x->%04x len %i inc=%i blank %i [%u] @ %06x",''',
    '''  VL("%d %06x D %d %05x %d %06x %d\\n", Pico.m.frame_count, SekPc, pvid->type, a, len, source, inc);
  elprintf(EL_VDPDMA, "DmaSlow[%i] %06x->%04x len %i inc=%i blank %i [%u] @ %06x",''')
rep('''  else {
    pvid->status |= SR_DMA|PVS_DMAFILL;
    return;
  }''', '''  else {
    VL("%d %06x F %d %05x %d\\n", Pico.m.frame_count, SekPc, pvid->type, pvid->addr | (pvid->addr_u << 16), len);
    pvid->status |= SR_DMA|PVS_DMAFILL;
    return;
  }''')
rep('''  if (method < 2)
    DmaSlow(len, source << 1); // 68000 to VDP
  else if (method == 3)
    DmaCopy(len); // VRAM Copy''', '''  if (method < 2)
    DmaSlow(len, source << 1); // 68000 to VDP
  else if (method == 3)
    { VL("%d %06x C %d %05x %d\\n", Pico.m.frame_count, SekPc, pvid->type, pvid->addr | (pvid->addr_u << 16), len); DmaCopy(len); } // VRAM Copy''')
rep('''        pvid->reg[num] = d;

        switch (num)''', '''        VL("%d %06x V %02x %02x\\n", Pico.m.frame_count, SekPc, num, d);
        pvid->reg[num] = d;

        switch (num)''')
open(p, 'w', newline='').write(s)
# frame dump hook in pico.c
p = d + '/pico/pico.c'
s = open(p, newline='').read()
nl = '\r\n' if '\r\n' in s else '\n'
rep('''void PicoFrame(void)
{''', '''#include <stdio.h>
#include <stdlib.h>
#include <string.h>
static void vl_dump(void)
{
  static char *list; static int init; const char *pre = getenv("PD_VDP_DUMP");
  char name[512], key[32]; FILE *f; char *q;
  if (!init) { init = 1; list = getenv("PD_VDP_DUMP_FRAMES"); }
  if (!pre || !list) return;
  snprintf(key, sizeof key, ",%d,", Pico.m.frame_count);
  { char tmp[4096]; snprintf(tmp, sizeof tmp, ",%s,", list); q = strstr(tmp, key); if (!q) return; }
  snprintf(name, sizeof name, "%s_%d.vram", pre, Pico.m.frame_count); if ((f = fopen(name, "wb"))) { fwrite(PicoMem.vram, 1, 0x10000, f); fclose(f); }
  snprintf(name, sizeof name, "%s_%d.cram", pre, Pico.m.frame_count); if ((f = fopen(name, "wb"))) { fwrite(PicoMem.cram, 1, 0x80, f); fclose(f); }
  snprintf(name, sizeof name, "%s_%d.vsram", pre, Pico.m.frame_count); if ((f = fopen(name, "wb"))) { fwrite(PicoMem.vsram, 1, 0x80, f); fclose(f); }
  snprintf(name, sizeof name, "%s_%d.reg", pre, Pico.m.frame_count); if ((f = fopen(name, "wb"))) { fwrite(Pico.video.reg, 1, 0x20, f); fclose(f); }
}
void PicoFrame(void)
{
  vl_dump();''')
open(p, 'w', newline='').write(s)
print('ok')
