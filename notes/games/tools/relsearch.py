#!/usr/bin/env python3
"""usage: relsearch.py ROM WORD [WORD ...]

Relative search: find each WORD (letters only) stored with an unknown
encoding in which consecutive letters have consecutive codes, as in most
tile-index fonts. Searches bytes and big-endian 16-bit words at every
alignment, and prints each hit's cartridge offset, element size and the
code for 'A', so the text around it can be decoded with that offset.
"""
import struct, sys

def hits(seq, word):
    d = [ord(b) - ord(a) for a, b in zip(word, word[1:])]
    n = len(word)
    for i in range(len(seq) - n + 1):
        ok = True
        for k in range(n - 1):
            if seq[i + k + 1] - seq[i + k] != d[k]:
                ok = False; break
        if ok:
            yield i, seq[i] - (ord(word[0]) - ord('A'))

def main():
    rom = open(sys.argv[1], 'rb').read()
    words16 = [list(struct.unpack_from('>%dH' % ((len(rom) - a) // 2), rom, a)) for a in (0, 1)]
    for w in sys.argv[2:]:
        w = w.upper()
        for i, a in hits(rom, w):
            print('%-10s byte  $%06X  A=%d' % (w, i, a))
        for al in (0, 1):
            for i, a in hits(words16[al], w):
                print('%-10s word  $%06X  A=$%04X' % (w, al + 2 * i, a & 0xFFFF))

main()
