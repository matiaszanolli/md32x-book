#!/usr/bin/env python3
"""Record chosen 68000 RAM ranges after every frame (headless PicoDrive, debugger script).
usage: framewatch.py RUNDIR OUT.pkl FRAMES ADDR:SIZE [ADDR:SIZE ...] [--rom vf.32x] [--input CSV] [--start N]
Reads are 4,096 bytes at most each. OUT.pkl is a pickle {(addr,size): [bytes per frame]} plus 'frames'.
Frame i of the list is the state after i+START+1 frames have run."""
import sys, subprocess, os, re, pickle
a = sys.argv[1:]
rundir, out = a[0], a[1]
rom = 'vf.32x'; env = dict(os.environ); start = 0
if '--rom' in a: i = a.index('--rom'); rom = a[i+1]; del a[i:i+2]
if '--input' in a: i = a.index('--input'); env['VRD_INPUT_SCRIPT'] = a[i+1]; del a[i:i+2]
if '--start' in a: i = a.index('--start'); start = int(a[i+1]); del a[i:i+2]
nframes = int(a[2]); ranges = []
for r in a[3:]:
    ad, sz = r.split(':'); ranges.append((int(ad, 16), int(sz, 0)))
cmds = []
if start: cmds.append('run %d' % start)
for f in range(nframes):
    cmds.append('run 1')
    for ad, sz in ranges: cmds.append('read 68k 0x%X %d' % (ad, sz))
cmds.append('quit')
cf = out + '.cmds'
open(cf, 'w').write('\n'.join(cmds) + '\n')
nfr = start + nframes + 2
if 'VRD_INPUT_SCRIPT' in env: nfr = sum(1 for _ in open(env['VRD_INPUT_SCRIPT'])) - 1
p = subprocess.run(['./frontend', rom, str(nfr), '--debug-script', cf], cwd=rundir, capture_output=True, text=True, env=env)
res = {r: [] for r in ranges}
idx = -1; cur = None; buf = None
for ln in p.stdout.splitlines():
    if ln.startswith('vrd-dbg> read 68k'):
        if buf is not None: res[cur].append(bytes(buf))
        idx += 1; cur = ranges[idx % len(ranges)]; buf = bytearray(); continue
    m = re.match(r'([0-9A-F]{8}): ((?:[0-9A-F]{2} ?)+)$', ln)
    if m and buf is not None: buf += bytes.fromhex(m.group(2).replace(' ', ''))
    elif ln.startswith('vrd-dbg>') and buf is not None:
        res[cur].append(bytes(buf)); buf = None
if buf is not None: res[cur].append(bytes(buf))
res['frames'] = nframes; res['start'] = start
pickle.dump(res, open(out, 'wb'))
print({str(k): len(v) for k, v in res.items() if k not in ('frames', 'start')})
