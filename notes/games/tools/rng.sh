#!/bin/sh
# usage: rng.sh LISTING START END  (hex without 0x, e.g. mk2.txt 6000240 60002d8)
awk -v s="$2" -v e="$3" 'BEGIN{S=strtonum("0x" s);E=strtonum("0x" e)} {a=$1; sub(":","",a); v=strtonum("0x" a); if (v>=S && v<=E) print}' "$1"
