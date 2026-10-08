#!/bin/sh
# usage: build_bios_core.sh WORKDIR
# Builds a copy of the VRD project's PicoDrive libretro core, interpreter only
# (use_sh2drc=0, so VRD_SH2_TIMING=1 works), that can run the real 32X boot
# ROMs. Neither the libretro core nor PicoDrive's own frontends ever load them:
# the loader in platform/common/emu.c is compiled out (#if 0), so every run
# takes the HLE start in pico/32x/32x.c, which never writes CCR. With
# PD_32X_BIOS_DIR=DIR set, this core reads 32X_G_BIOS.BIN (256 bytes),
# 32X_M_BIOS.BIN (2 KB) and 32X_S_BIOS.BIN (1 KB) from DIR before the game
# loads, and the boot ROMs run instead. Unset, it behaves as the stock core.
# With PD_CCR_LOG=FILE it also appends one line per CCR write, however the
# address was formed: CPU, PC and value.
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
p = 'platform/libretro/libretro.c'
s = open(p, newline='').read()
nl = '\r\n' if '\r\n' in s else '\n'
helper = nl.join([
  '',
  '#include <fcntl.h>',
  '#include <unistd.h>',
  '/* libretro.c maps stdio onto libretro VFS, so use POSIX calls here. */',
  'static void *pd_bios_load(const char *dir, const char *name, size_t size) {',
  '  char path[1024]; int fd; void *b;',
  '  snprintf(path, sizeof(path), "%s/%s", dir, name);',
  '  if ((fd = open(path, O_RDONLY)) < 0) { lprintf("pd_bios: cannot open %s\\n", path); exit(1); }',
  '  b = malloc(size);',
  '  if (read(fd, b, size) != (ssize_t)size) { lprintf("pd_bios: short read %s\\n", path); exit(1); }',
  '  close(fd); lprintf("pd_bios: loaded %s\\n", path); return b; }',
  'static void pd_bios_setup(void) {',
  '  const char *d = getenv("PD_32X_BIOS_DIR");',
  '  if (!d || !*d) return;',
  '  p32x_bios_g = pd_bios_load(d, "32X_G_BIOS.BIN", 256);',
  '  p32x_bios_m = pd_bios_load(d, "32X_M_BIOS.BIN", 2048);',
  '  p32x_bios_s = pd_bios_load(d, "32X_S_BIOS.BIN", 1024); }',
  ''])
anchor = 'bool retro_load_game(const struct retro_game_info *info)' + nl + '{'
assert s.count(anchor) == 1, 'retro_load_game has changed; update build_bios_core.sh'
s = s.replace(anchor, helper + anchor)
old = '   size_t i;' + nl
i = s.index(anchor) + len(anchor)
j = s.index(old, i)
assert j - i < 400, 'retro_load_game declarations have changed; update build_bios_core.sh'
s = s[:j + len(old)] + nl + '   pd_bios_setup();' + nl + s[j + len(old):]
open(p, 'w', newline='').write(s)
p = 'pico/32x/sh2soc.c'
s = open(p, newline='').read()
old = '  case 0x092: // CCR - cache control; keep the timing model\'s cache in step' + nl
assert s.count(old) == 1, 'CCR write hook has changed; update build_bios_core.sh'
s = s.replace(old, old + '    { const char *f = getenv("PD_CCR_LOG"); int l;  /* POSIX: stdio is libretro VFS here */' + nl +
  '      if (f && *f && (l = open(f, O_WRONLY | O_CREAT | O_APPEND, 0644)) >= 0) { dprintf(l, "%s pc=%08x ccr=%02x\\n", sh2->is_slave ? "slave" : "master", sh2_pc(sh2), d & 0xff); close(l); } }' + nl)
s = '#include <fcntl.h>' + nl + '#include <unistd.h>' + nl + s
open(p, 'w', newline='').write(s)
PY
make -f Makefile.libretro clean >/dev/null 2>&1 || true
make -f Makefile.libretro use_sh2drc=0 -j"$(nproc)" GIT_REVISION=e0dc88d
echo "built $W/third_party/picodrive/picodrive_libretro.so"
