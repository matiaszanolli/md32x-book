#!/bin/sh
# usage: build_dma_core.sh WORKDIR
# Builds a copy of the VRD project's PicoDrive libretro core with a DMA log:
# with PD_DMA_LOG=FILE set, every 68000-to-VDP DMA writes one line
# "frame source(byte address) length(words) type(1 VRAM,3 CRAM,5 VSRAM) dest step".
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
p = 'pico/videoport.c'
s = open(p, newline='').read()          # the file has CRLF line endings
nl = '\r\n' if '\r\n' in s else '\n'
old = '  if (method < 2)' + nl + '    DmaSlow(len, source << 1); // 68000 to VDP'
new = nl.join([
  '  if (method < 2) {',
  '    static FILE *dmalog; static int dmainit;',
  '    if (!dmainit) { const char *f = getenv("PD_DMA_LOG"); dmainit = 1; if (f) dmalog = fopen(f, "w"); }',
  '    if (dmalog) fprintf(dmalog, "%u %06x %u %u %05x %u\\n", Pico.m.frame_count, (source << 1) & 0xffffff, len, pvid->type, pvid->addr | (pvid->addr_u << 16), pvid->reg[0xf]);',
  '    DmaSlow(len, source << 1); // 68000 to VDP',
  '  }'])
assert old in s, 'CommandDma has changed; update build_dma_core.sh'
open(p, 'w', newline='').write(s.replace(old, new))
PY
make -f Makefile.libretro -j"$(nproc)" GIT_REVISION=e0dc88d
echo "built $W/third_party/picodrive/picodrive_libretro.so"
