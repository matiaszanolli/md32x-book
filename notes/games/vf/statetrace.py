#!/usr/bin/env python3
"""From a framewatch.py pickle that includes the range FF0000:64: print, for every distinct (main-state, blank-task) pair
of the 68000's main loop, the first and last frame and the number of frames, in order of first appearance.
usage: statetrace.py FW.pkl"""
import sys, pickle, struct, collections
d = pickle.load(open(sys.argv[1], 'rb'))
code = d[(0xFF0000, 64)]
c = collections.OrderedDict()
for f, b in enumerate(code):
    k = (struct.unpack('>I', b[2:6])[0], struct.unpack('>I', b[0x38:0x3c])[0])
    e = c.setdefault(k, [f + 1, f + 1, 0]); e[1] = f + 1; e[2] += 1
for (m, v), (a, b, n) in c.items():
    print("main=%06x vbl=%06x first=%d last=%d frames=%d" % (m, v, a, b, n))
