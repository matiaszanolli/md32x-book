#!/bin/sh
# usage: build.sh OUT_DIR
# Builds OUT_DIR/hellomd.bin, a Mega Drive cartridge image, and writes its
# checksum into the header. OUT_DIR must be outside the book's src/ tree.
set -e
OUT=${1:?usage: $0 OUT_DIR}
HERE=$(cd "$(dirname "$0")" && pwd)
mkdir -p "$OUT"; OUT=$(cd "$OUT" && pwd)
case "$OUT/" in "${HERE%/src/*}/src/"*) echo "OUT_DIR must be outside src/" >&2; exit 1;; esac
cd "$OUT"

m68k-linux-gnu-as -m68000 --register-prefix-optional -I "$HERE" -o hello.o "$HERE/hello.s"
m68k-linux-gnu-ld -Ttext=0 -e 0 --oformat=binary -o hellomd.bin hello.o

# Checksum: the 16-bit sum of every word from $200 to the end, at $18E.
python3 - hellomd.bin <<'PY'
import struct, sys
rom = bytearray(open(sys.argv[1], 'rb').read())
total = sum(struct.unpack('>%dH' % ((len(rom) - 0x200) // 2), rom[0x200:])) & 0xFFFF
rom[0x18E:0x190] = struct.pack('>H', total)
open(sys.argv[1], 'wb').write(rom)
print('checksum $%04X' % total)
PY
ls -l hellomd.bin
