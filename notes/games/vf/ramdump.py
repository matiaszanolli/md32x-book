#!/usr/bin/env python3
"""Dump the 68000 work RAM ($FF0000-$FFFFFF) of Virtua Fighter at given frames, with the headless PicoDrive frontend.
usage: ramdump.py RUNDIR OUTDIR FRAME [FRAME ...] [--rom vf.32x] [--also ADDR:SIZE ...] [--input CSV]
RUNDIR holds `frontend`, picodrive_libretro.so and the ROM. Writes OUTDIR/ram_FRAME.bin (64 KB).
The debugger reads at most 4,096 bytes at a time, so 16 reads per dump."""
import sys, subprocess, os, re
a = sys.argv[1:]
rundir, outdir = a[0], a[1]
rom = 'vf.32x'
env = dict(os.environ)
if '--rom' in a:
    i = a.index('--rom'); rom = a[i+1]; del a[i:i+2]
if '--input' in a:
    i = a.index('--input'); env['VRD_INPUT_SCRIPT'] = a[i+1]; del a[i:i+2]
frames = sorted(int(x) for x in a[2:])
os.makedirs(outdir, exist_ok=True)
cmds = []
cur = 0
for f in frames:
    if f > cur: cmds.append('run %d' % (f - cur)); cur = f
    for k in range(16):
        cmds.append('read 68k 0x%X 4096' % (0xFF0000 + k * 4096))
cmds.append('quit')
cf = os.path.join(outdir, 'cmds.txt')
open(cf, 'w').write('\n'.join(cmds) + '\n')
nfr = max(frames) + 5
if 'VRD_INPUT_SCRIPT' in env:
    nfr = sum(1 for _ in open(env['VRD_INPUT_SCRIPT'])) - 1
out = subprocess.run(['./frontend', rom, str(nfr), '--debug-script', cf], cwd=rundir, capture_output=True, text=True, env=env).stdout
# parse
cur = None; data = {}
fr = 0; chunks = []
for ln in out.splitlines():
    m = re.match(r'Advanced (\d+) frames; session frame=(\d+)', ln)
    if m: fr = int(m.group(2)); data[fr] = bytearray(); continue
    m = re.match(r'([0-9A-F]{8}): ((?:[0-9A-F]{2} ?)+)', ln)
    if m and fr in data:
        data[fr] += bytes.fromhex(m.group(2).replace(' ', ''))
for f, b in data.items():
    assert len(b) == 65536, (f, len(b))
    open(os.path.join(outdir, 'ram_%d.bin' % f), 'wb').write(b)
print("wrote", sorted(data))
