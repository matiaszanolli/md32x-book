#!/bin/sh
# usage: build_nopoll_core.sh WORKDIR
# Builds a copy of the VRD project's PicoDrive libretro core with the 68000's
# poll detection (m68k_poll_detect in pico/32x/memory.c) switched off, by
# raising POLL_THRESHOLD. With detection on, a 68000 loop that keeps reading
# one communication port is put to sleep until the port changes, so a counted
# wait on a value that never arrives never runs out. Put the .so next to the
# frontend (build_frontend.sh) in a scratch directory.
# The VRD copy is never modified; WORKDIR mirrors its layout because its
# libretro.c includes files from ../../../../tools/libretro-profiling.
set -e
W=${1:?usage: $0 WORKDIR}
VRD=/mnt/data/src/32x-playground
mkdir -p "$W/third_party"
rsync -a --exclude '*.o' --exclude '*.so' --exclude .git "$VRD/third_party/picodrive/" "$W/third_party/picodrive/"
ln -sfn "$VRD/tools" "$W/tools"
cd "$W/third_party/picodrive"
sed -i 's/^#define POLL_THRESHOLD 11 .*/#define POLL_THRESHOLD 1000000000/' pico/32x/memory.c
grep -q '^#define POLL_THRESHOLD 1000000000' pico/32x/memory.c
make -f Makefile.libretro -j"$(nproc)" GIT_REVISION=e0dc88d
echo "built $W/third_party/picodrive/picodrive_libretro.so"
