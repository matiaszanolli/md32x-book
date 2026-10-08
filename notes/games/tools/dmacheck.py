#!/usr/bin/env python3
"""usage: dmacheck.py LOG [LOG ...]
Summarise a PD_DMA_LOG file (see build_dma_core.sh): how many DMAs read ROM,
and which cross a 64 KB line inside a 128 KB block or a 128 KB line.
DMAs from work RAM ($E00000 up) are skipped: RAM repeats every 64 KB, so
they cannot tell a 64 KB wrap from a 128 KB one."""
import sys, collections
for log in sys.argv[1:]:
    rows = [l.split() for l in open(log)]
    rom = c64 = c128 = 0
    ex = collections.OrderedDict()
    for fr, src, ln, typ, dst, inc in rows:
        s = int(src, 16); n = int(ln) or 0x10000; e = s + 2 * n - 2
        if s >= 0xE00000:
            continue
        rom += 1
        if (s >> 17) != (e >> 17):
            c128 += 1; ex.setdefault((s, n, '128K'), (fr, typ, dst))
        elif (s >> 16) != (e >> 16):
            c64 += 1; ex.setdefault((s, n, '64K'), (fr, typ, dst))
    print(f'{log}: {len(rows)} DMAs, {rom} from ROM, {c64} cross 64K inside 128K, {c128} cross 128K')
    for (s, n, k), (fr, typ, dst) in list(ex.items())[:8]:
        print(f'  {k:4} ${s:06X}-${s + 2 * n - 1:06X} ({n} words) type {typ} dst ${int(dst, 16):04X} frame {fr}')
