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
T=$(cd "$(dirname "$0")" && pwd)
W=${1:?usage: $0 WORKDIR}
VRD=/mnt/data/src/32x-playground
mkdir -p "$W/third_party"
rsync -a --exclude '*.o' --exclude '*.so' --exclude .git "$VRD/third_party/picodrive/" "$W/third_party/picodrive/"
ln -sfn "$VRD/tools" "$W/tools"
cd "$W/third_party/picodrive"
python3 "$T/patch_sleep_log.py"
make -f Makefile.libretro -j"$(nproc)" GIT_REVISION=e0dc88d
echo "built $W/third_party/picodrive/picodrive_libretro.so"
