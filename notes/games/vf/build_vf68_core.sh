#!/bin/sh
# usage: build_vf68_core.sh WORKDIR
# Builds a copy of the VRD project's PicoDrive libretro core with the three logging patches used for the
# Virtua Fighter 68000 notes (M68K.md):  PD_M68K_LOG, PD_VDP_LOG / PD_VDP_DUMP(_FRAMES), PD_Z80_LOG.
# The VRD copy is only read (rsync), never modified. Run the frontend from a directory holding the built
# picodrive_libretro.so next to ../32x-playground/tools/libretro-profiling/profiling_frontend (see notes/games/tools/README.md).
set -e
W=${1:?usage: $0 WORKDIR}
HERE=$(cd "$(dirname "$0")" && pwd)
VRD=/mnt/data/src/32x-playground
mkdir -p "$W/third_party"
rsync -a --exclude '*.o' --exclude '*.so' --exclude .git "$VRD/third_party/picodrive/" "$W/third_party/picodrive/"
ln -sfn "$VRD/tools" "$W/tools"
cd "$W/third_party/picodrive"
python3 "$HERE/patch_m68klog.py" .
python3 "$HERE/patch_vdplog.py" .
python3 "$HERE/patch_z80log.py" .
make -f Makefile.libretro -j"$(nproc)" GIT_REVISION=e0dc88d
echo "built $W/third_party/picodrive/picodrive_libretro.so"
