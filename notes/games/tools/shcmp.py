#!/usr/bin/env python3
"""usage: shcmp.py [--align] [--regs] LIST_A START_A LIST_B START_B [COUNT]

Compare COUNT instructions (default 60) of two sh-elf-objdump listings
(sh2dis.sh output) from the given SH-2 addresses, side by side. Each line is
normalised before comparing: PC-relative loads are replaced by the literal
they load (objdump's '! value' comment) and branch targets by their distance
from the start address, so the same code at different addresses compares
equal. Marks '=' for identical, '~' for the same mnemonic with different
operands, and ' ' otherwise; prints the counts at the end. Literal pools
decoded as instructions are compared too, so stop COUNT at the end of the code.

--align  align the two runs with difflib instead of comparing in lockstep, and
         print each matching block of 3+ instructions with both addresses.
--regs   also replace register names by rN, to compare shape only.
"""
import re, sys

def load(path):
    rows = {}
    for line in open(path):
        m = re.match(r'\s*([0-9a-f]+):\s+(?:[0-9a-f]{2} ){2}\s*(.*)', line)
        if m:
            rows[int(m.group(1), 16)] = m.group(2).strip()
    return rows

def norm(text, base):
    text = re.sub(r'\s+', ' ', text)
    m = re.match(r'(mov\.[lw]) 0x[0-9a-f]+,(r\d+)(?: ! ([0-9a-f]+))?', text)
    if m:
        return '%s #lit %s,%s' % (m.group(1), m.group(3) or '?', m.group(2))
    m = re.match(r'(bra|bsr|bt|bf|bt/s|bf/s) 0x([0-9a-f]+)$', text)
    if m:
        return '%s .%+d' % (m.group(1), int(m.group(2), 16) - base)
    return text

def seq(rows, start, n):
    out, a = [], start
    while len(out) < n and a in rows:
        out.append((a, rows[a], norm(rows[a], start)))
        a += 2
    return out

args = [a for a in sys.argv[1:] if not a.startswith('--')]
ALIGN, REGS = '--align' in sys.argv, '--regs' in sys.argv
la, sa, lb, sb = args[0], int(args[1], 16), args[2], int(args[3], 16)
n = int(args[4]) if len(args) > 4 else 60
A, B = seq(load(la), sa, n), seq(load(lb), sb, n)
if REGS:
    A = [(a, t, re.sub(r'\br\d+\b', 'rN', x)) for a, t, x in A]
    B = [(a, t, re.sub(r'\br\d+\b', 'rN', x)) for a, t, x in B]
if ALIGN:
    import difflib
    sm = difflib.SequenceMatcher(None, [x[2] for x in A], [x[2] for x in B], autojunk=False)
    tot = 0
    for i, j, k in sm.get_matching_blocks():
        if k >= 3:
            tot += k
            print('match %3d instr: %08x-%08x = %08x-%08x' % (k, A[i][0], A[i + k - 1][0], B[j][0], B[j + k - 1][0]))
    print('matched %d of %d / %d instructions' % (tot, len(A), len(B)))
    sys.exit()
same = alike = 0
for (aa, ta, na), (ab, tb, nb) in zip(A, B):
    mark = '=' if na == nb else '~' if na.split(' ')[0] == nb.split(' ')[0] else ' '
    same += mark == '='; alike += mark == '~'
    print('%08x %-34s %s %08x %s' % (aa, ta[:34], mark, ab, tb[:34]))
print('identical %d, same mnemonic %d, other %d, of %d' % (same, alike, min(len(A), len(B)) - same - alike, min(len(A), len(B))))
