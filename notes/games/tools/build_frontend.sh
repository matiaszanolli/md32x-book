#!/bin/sh
# usage: build_frontend.sh OUT
# Builds the VRD project's headless libretro frontend (the committed binary
# predates video dumps). Run it from ../32x-playground/tools/libretro-profiling,
# where it finds picodrive_libretro.so.
SRC=/mnt/data/src/32x-playground/tools/libretro-profiling/profiling_frontend.c
gcc -O2 -o "${1:?usage: $0 OUT}" "$SRC" -ldl
