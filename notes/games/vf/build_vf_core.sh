#!/bin/sh
# usage: build_vf_core.sh WORKDIR
# Builds the instrumented PicoDrive core used for the Virtua Fighter notes (notes/games/vf/SH2.md):
# first the sleep core of build_sleep_core.sh (a copy of the VRD project's libretro core), then vf_trace.patch on top
# (SH-2 access/instruction/call tracing; see SH2.md "Tools"). Interpreter only: set VRD_PROFILE_PC=1 so the hooks run.
set -e
W=${1:?usage: $0 WORKDIR}
HERE=$(cd "$(dirname "$0")" && pwd)
sh "$HERE/../tools/build_sleep_core.sh" "$W"
cd "$W/third_party/picodrive"
patch -p1 < "$HERE/vf_trace.patch"
make -f Makefile.libretro -j"$(nproc)" GIT_REVISION=e0dc88d
echo "built $W/third_party/picodrive/picodrive_libretro.so"
