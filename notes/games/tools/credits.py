#!/usr/bin/env python3
"""usage: credits.py [-k REGEX] [-c N] ROM [ROM ...]

Print printable-ASCII runs (6+ chars) that match a credits keyword, with
their cartridge offsets and the N runs on each side, so a developer credit
can be cited by offset. Only finds plain ASCII; credits drawn from tiles or
compressed text will not show.
"""
import re, sys

KEYS = (r'develop|programm?ed by|reprogrammed|produced by|production|studio|'
        r'software|games\b|team\b|\(c\)|copyright|interactive|entertainment|'
        r'rutubo|artech|probe|sculptured|iguana|bits corp|zyrinx|novotrade|'
        r'core design|interplay|id software|cri\b|csk|sega of america|am\d')

def runs(d):
    for m in re.finditer(rb'[\x20-\x7e]{6,}', d):
        yield m.start(), m.group().decode('ascii')

def main(argv):
    key, ctx, paths = KEYS, 1, []
    it = iter(argv)
    for a in it:
        if a == '-k': key = next(it)
        elif a == '-c': ctx = int(next(it))
        else: paths.append(a)
    rx = re.compile(key, re.I)
    for p in paths:
        print('==', p)
        r = list(runs(open(p, 'rb').read()))
        shown = set()
        for i, (_, s) in enumerate(r):
            if rx.search(s) and 'MARS Initial' not in s and 'DEVELOPED FOR USE' not in s:
                for j in range(max(0, i - ctx), min(len(r), i + ctx + 1)):
                    if j not in shown:
                        shown.add(j)
                        print('   $%06X  %s' % (r[j][0], r[j][1][:160]))
                print('   --')

main(sys.argv[1:])
