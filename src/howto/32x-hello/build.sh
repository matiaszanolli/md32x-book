#!/bin/sh
# usage: build.sh RETAIL_32X_ROM OUT_DIR
# Builds OUT_DIR/hello32x.32x. Sega's initial program ($3F0-$7FF) is copied
# from the given 32X cartridge dump at build time; it is never stored here.
# OUT_DIR must be outside the book's src/ tree, which is published.
set -e
ROM=${1:?usage: $0 RETAIL_32X_ROM OUT_DIR}
OUT=${2:?usage: $0 RETAIL_32X_ROM OUT_DIR}
HERE=$(cd "$(dirname "$0")" && pwd)
mkdir -p "$OUT"; OUT=$(cd "$OUT" && pwd)
case "$OUT/" in "${HERE%/src/*}/src/"*) echo "OUT_DIR must be outside src/" >&2; exit 1;; esac
cd "$OUT"

dd if="$ROM" of=security.bin bs=1 skip=$((0x3F0)) count=1040 status=none

sh-elf-as -o sh2.o "$HERE/sh2.s"
sh-elf-ld -Ttext=0x06000000 -e master_start -o sh2.elf sh2.o
sh-elf-objcopy -O binary -j .text sh2.elf sh2.bin
# pad to a multiple of 4: the boot ROM copies longwords
python3 -c "import sys;d=open('sh2.bin','rb').read();open('sh2.bin','wb').write(d+bytes(-len(d)%4))"

m68k-linux-gnu-as -m68000 --register-prefix-optional -I . -o md.o "$HERE/md.s"
m68k-linux-gnu-ld -Ttext=0 -e 0 --oformat=binary -o hello32x.32x md.o
ls -l hello32x.32x
