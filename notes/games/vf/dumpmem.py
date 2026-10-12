#!/usr/bin/env python3
"""dumpmem.py FRONTEND_DIR ROM STATE NFRAMES OUT.bin [KIND]
Load STATE (or none: '-'), run NFRAMES frames, then dump the SDRAM (256 KB, from 0x26000000 read through the Master)
and the Master/Slave on-chip RAM views are not readable by the debugger, so only SDRAM is dumped.
Writes OUT.bin (262144 bytes)."""
import subprocess, sys, os, re
d, rom, st, n, out = sys.argv[1:6]
cmd = ['run %s' % n] if int(n) > 0 else []
for a in range(0, 0x40000, 0x1000):
    cmd.append('read master 0x%08x 0x1000' % (0x26000000 + a))
cmd.append('quit')
open(d + '/_dump.cmd', 'w').write('\n'.join(cmd) + '\n')
env = dict(os.environ)
if st != '-': env['VRD_LOAD_STATE'] = st
r = subprocess.run(['./frontend', rom, str(int(n) + 2), '--debug-script', '_dump.cmd'], cwd=d, env=env, capture_output=True, text=True)
buf = bytearray(0x40000)
for l in r.stdout.splitlines():
    m = re.match(r'([0-9A-F]{8}): ((?:[0-9A-F]{2} ?)+)$', l.strip())
    if m:
        a = int(m.group(1), 16) - 0x26000000
        b = bytes.fromhex(m.group(2).replace(' ', ''))
        buf[a:a + len(b)] = b
open(out, 'wb').write(buf)
print('wrote', out)
