#!/bin/sh
# usage: build_miss_core.sh WORKDIR
# Builds the core of build_bios_core.sh (interpreter only, real boot ROMs with
# PD_32X_BIOS_DIR, VRD_SH2_TIMING=1 works) with these additions for finding
# where the timing model's wait cycles go:
#   - the changes of build_sleep_core.sh (patch_sleep_log.py): PD_SLEEP_LOG,
#     and every PC in VRD_PROFILE_PC_LOG, not only the top 200 per CPU;
#   - with VRD_MISS_LOG=FILE, the timing model writes at exit, per CPU, its
#     counts by region (cached read hits, cached read misses, uncached reads,
#     writes, and the wait cycles of each), then every 1 KB block of memory
#     that had a cache miss, with its miss count. Blocks are by physical
#     address (cache-through bit cleared), "cpu block_address misses".
# Counters start when the timing model is reset, i.e. at power-on, and a save
# state does not reset them: load a state and the log covers the whole run
# from the state.
#   - VRD_TIMING_CCR=VALUE starts both CPUs' cache model with that CCR. The
#     model learns CCR only from writes, and loading a save state replays none,
#     so without it a run from a state is charged as uncached. Use the value
#     the game had when the state was saved (PD_CCR_LOG shows the writes).
# The VRD copy is never modified.
set -e
W=${1:?usage: $0 WORKDIR}
T=$(cd "$(dirname "$0")" && pwd)
sh "$T/build_bios_core.sh" "$W"
cd "$W/third_party/picodrive"
python3 "$T/patch_sleep_log.py"
python3 - <<'PY'
p = 'pico/32x/vrd_timing.c'
s = open(p, newline='').read()
nl = '\r\n' if '\r\n' in s else '\n'
helpers = nl.join([
  '',
  '#include <stdio.h>',
  '/* build_miss_core.sh: per-region counters and a miss map by 1 KB block. */',
  'static unsigned long long ms_n[2][RGN_NONE][4], ms_w[2][RGN_NONE][4];',
  'static unsigned int *ms_blk[2];',
  'static void ms_count(int cpu, int rgn, int kind, unsigned int addr, int cost) {',
  '  ms_n[cpu][rgn][kind]++; ms_w[cpu][rgn][kind] += cost > 1 ? cost - 1 : 0;',
  '  if (kind == 1) {',
  '    unsigned int b = (addr & 0x1fffffff) >> 10;',
  '    if (b < 0x80000) { if (!ms_blk[cpu]) ms_blk[cpu] = calloc(0x80000, 4); if (ms_blk[cpu]) ms_blk[cpu][b]++; } } }',
  'static void ms_dump(void) {',
  '  static const char *rn[] = { "bootrom", "sysreg", "vdpreg", "palette", "cart", "framebuf", "sdram" };',
  '  static const char *kn[] = { "hit", "miss", "uncached-read", "write" };',
  '  const char *f = getenv("VRD_MISS_LOG"); FILE *o; int c, r, k; unsigned int b;',
  '  if (!f || !(o = fopen(f, "w"))) return;',
  '  for (c = 0; c < 2; c++) for (r = 0; r < RGN_NONE; r++) for (k = 0; k < 4; k++)',
  '    if (ms_n[c][r][k]) fprintf(o, "R %d %s %s %llu %llu\\n", c, rn[r], kn[k], ms_n[c][r][k], ms_w[c][r][k]);',
  '  for (c = 0; c < 2; c++) if (ms_blk[c]) for (b = 0; b < 0x80000; b++)',
  '    if (ms_blk[c][b]) fprintf(o, "B %d %08x %u\\n", c, b << 10, ms_blk[c][b]);',
  '  fclose(o); }',
  ''])
anchor = '/* --- entry points'
assert s.count(anchor) == 1, 'vrd_timing.c has changed; update build_miss_core.sh'
s = s.replace(anchor, helpers + anchor)
# hit
old = '      vrd_timing_stats[cpu].cache_hits++;' + nl + '      return 0;'
assert s.count(old) == 1, 'hit path has changed; update build_miss_core.sh'
s = s.replace(old, '      vrd_timing_stats[cpu].cache_hits++;' + nl + '      ms_count(cpu, rgn, 0, addr, 0);' + nl + '      return 0;')
# miss
old = '    cost = cost > 1 ? cost - 1 : 0;' + nl + '    vrd_timing_stats[cpu].wait_cycles += cost;'
assert s.count(old) == 1, 'miss path has changed; update build_miss_core.sh'
s = s.replace(old, '    ms_count(cpu, rgn, 1, addr, cost);' + nl + old)
# uncached / write
old = '  vrd_timing_stats[cpu].wait_cycles += (cost > 1 ? cost - 1 : 0);' + nl + '  return cost > 1 ? cost - 1 : 0;'
assert s.count(old) == 1, 'uncached path has changed; update build_miss_core.sh'
s = s.replace(old, '  ms_count(cpu, rgn, is_write ? 3 : 2, addr, cost);' + nl + old)
# initial CCR for runs from a save state
old = '  memset(cache, 0, sizeof(cache));' + nl + '}'
assert s.count(old) == 1, 'vrd_timing_reset has changed; update build_miss_core.sh'
s = s.replace(old, '  memset(cache, 0, sizeof(cache));' + nl +
  '  { const char *c = getenv("VRD_TIMING_CCR"); if (c && *c) cache[0].ccr = cache[1].ccr = (unsigned char)strtoul(c, 0, 0) & ~0x10; }' + nl + '}')
# dump at report
old = '  if (!vrd_timing_enabled()) return;' + nl + '  for (cpu = 0; cpu < 2; cpu++) {'
assert s.count(old) == 1, 'report has changed; update build_miss_core.sh'
s = s.replace(old, '  if (!vrd_timing_enabled()) return;' + nl + '  ms_dump();' + nl + '  for (cpu = 0; cpu < 2; cpu++) {')
open(p, 'w', newline='').write(s)
PY
make -f Makefile.libretro use_sh2drc=0 -j"$(nproc)" GIT_REVISION=e0dc88d
echo "built $W/third_party/picodrive/picodrive_libretro.so"
