#!/bin/sh
# usage: build_sleep_core.sh WORKDIR
# Builds a copy of the VRD project's PicoDrive libretro core that records how
# long each SH-2 sleeps in PicoDrive's poll detection. With PD_SLEEP_LOG=FILE
# set, it writes one line per CPU and polled address at exit:
# "cpu address sleeps m68k_cycles" (Master 0, Slave 1; the address has the
# cache-through bit cleared; one 68000 cycle = 3 SH-2 clocks). The profiler
# (VRD_PROFILE_PC) counts only executed cycles, so this accounts for the rest.
# It also writes every PC to VRD_PROFILE_PC_LOG, not only the top 200 per CPU.
# The VRD copy is never modified; WORKDIR mirrors its layout because its
# libretro.c includes files from ../../../../tools/libretro-profiling.
set -e
W=${1:?usage: $0 WORKDIR}
VRD=/mnt/data/src/32x-playground
mkdir -p "$W/third_party"
rsync -a --exclude '*.o' --exclude '*.so' --exclude .git "$VRD/third_party/picodrive/" "$W/third_party/picodrive/"
ln -sfn "$VRD/tools" "$W/tools"
cd "$W/third_party/picodrive"
python3 - <<'PY'
p = 'pico/32x/memory.c'
s = open(p, newline='').read()
nl = '\r\n' if '\r\n' in s else '\n'
helpers = nl.join([
  '',
  'static struct { u32 addr; int cpu; unsigned long long cyc; unsigned n; } sl_tab[256];',
  'static int sl_cnt, sl_init; static FILE *sl_log;',
  'static u32 sl_start[2], sl_addr[2]; static int sl_on[2];',
  'static void sl_dump(void) {',
  '  int i; for (i = 0; i < sl_cnt; i++)',
  '    fprintf(sl_log, "%d %08x %u %llu\\n", sl_tab[i].cpu, sl_tab[i].addr, sl_tab[i].n, sl_tab[i].cyc);',
  '  fclose(sl_log); }',
  'static void sl_begin(SH2 *sh2, u32 a) {',
  '  if (!sl_init) { const char *f = getenv("PD_SLEEP_LOG"); sl_init = 1;',
  '    if (f && (sl_log = fopen(f, "w"))) atexit(sl_dump); }',
  '  if (!sl_log || sl_on[sh2->is_slave]) return;',
  '  sl_on[sh2->is_slave] = 1; sl_addr[sh2->is_slave] = a;',
  '  sl_start[sh2->is_slave] = sh2_cycles_done_m68k(sh2); }',
  'static void sl_end(SH2 *sh2, u32 now) {',
  '  int c = sh2->is_slave, i; u32 d;',
  '  if (!sl_on[c]) return; sl_on[c] = 0;',
  '  d = now - sl_start[c]; if ((int)d < 0) d = 0;',
  '  for (i = 0; i < sl_cnt; i++) if (sl_tab[i].addr == sl_addr[c] && sl_tab[i].cpu == c) break;',
  '  if (i == sl_cnt) { if (sl_cnt == 256) return; sl_cnt++; sl_tab[i].addr = sl_addr[c]; sl_tab[i].cpu = c; }',
  '  sl_tab[i].cyc += d; sl_tab[i].n++; }',
  ''])
anchor = 'void NOINLINE p32x_sh2_poll_detect(u32 a, SH2 *sh2, u32 flags, int maxcnt)'
assert s.count(anchor) == 1, 'poll_detect has changed; update build_sleep_core.sh'
s = s.replace(anchor, helpers + anchor)
old = '      sh2->state |= flags;' + nl + '      sh2_end_run(sh2, 0);'
assert s.count(old) == 1, 'poll_detect body has changed; update build_sleep_core.sh'
s = s.replace(old, '      sl_begin(sh2, a);' + nl + old)
old = '    pevt_log_sh2_o(sh2, EVT_POLL_END);' + nl + '    sh2->state &= ~flags;'
assert s.count(old) == 1, 'poll_event has changed; update build_sleep_core.sh'
s = s.replace(old, old + nl + '    if (!(sh2->state & (SH2_STATE_CPOLL|SH2_STATE_VPOLL|SH2_STATE_RPOLL)))' + nl +
              '      sl_end(sh2, CYCLES_GT(m68k_cycles, sh2->m68krcycles_done) ? m68k_cycles : sh2->m68krcycles_done);')
open(p, 'w', newline='').write(s)
p = 'platform/libretro/libretro.c'
s = open(p, newline='').read()
old = 'for (i = 0; i < n && i < 200; i++) {'
assert s.count(old) == 1, 'profile output loop has changed; update build_sleep_core.sh'
open(p, 'w', newline='').write(s.replace(old, 'for (i = 0; i < n; i++) {'))
PY
make -f Makefile.libretro -j"$(nproc)" GIT_REVISION=e0dc88d
echo "built $W/third_party/picodrive/picodrive_libretro.so"
