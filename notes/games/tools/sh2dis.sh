#!/bin/sh
# usage: sh2dis.sh ROM OFFSET SIZE NAME   (offset and size in hex, e.g. 978 7e14)
# Extracts the SH-2 program (loaded to 0x06000000) to NAME.bin and disassembles
# it to NAME.txt with sh-elf-objdump, which decodes exactly the SH-2's 142
# instructions (capstone's SH2 mode also decodes SH-2A/SH-4A words).
[ $# -eq 4 ] || { echo "usage: $0 ROM OFFSET SIZE NAME" >&2; exit 1; }
python3 -c "import sys; d=open(sys.argv[1],'rb').read(); o=int(sys.argv[2],16); n=int(sys.argv[3],16); open(sys.argv[4]+'.bin','wb').write(d[o:o+n])" "$1" "$2" "$3" "$4"
sh-elf-objdump -b binary -m sh2 -EB -D --adjust-vma=0x06000000 "$4.bin" > "$4.txt"
