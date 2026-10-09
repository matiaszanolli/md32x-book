# Per-frame memory sampling with the headless frontend's debugger.
#
#   python3 dbgsample.py gen OUT.dbg FRAMES [--start N] [--every K] [--save N:PATH ...] CPU:ADDR:SIZE ...
#       writes a debug script: run START (default 10), then FRAMES times
#       "run K" followed by one "read CPU ADDR SIZE" per spec; --save N:PATH
#       saves a state after frame N (session frames).
#   python3 dbgsample.py parse DEBUG_OUT > samples.jsonl
#       one JSON object per sample: {"frame": F, "ADDR": "hex bytes", ...}
#       (ADDR as written in the spec, e.g. "0x26007674").
#
# SH-2 addresses: read cache-through (0x2xxxxxxx). The debugger cannot read SH-2
# memory before frame 2, so START must be at least 10. 4,096 bytes per read at most.
import sys, re, json
from typing import Any

def gen(argv):
    out, frames = argv[0], int(argv[1])
    start, every, saves, specs = 10, 1, {}, []
    i = 2
    while i < len(argv):
        a = argv[i]
        if a == '--start': start = int(argv[i+1]); i += 2; continue
        if a == '--every': every = int(argv[i+1]); i += 2; continue
        if a == '--save':
            n, p = argv[i+1].split(':', 1); saves[int(n)] = p; i += 2; continue
        cpu, addr, size = a.split(':'); specs.append((cpu, addr, size)); i += 1
    L = ['run %d' % start]
    f = start
    for _ in range(frames):
        L.append('run %d' % every); f += every
        L.append('status')
        for cpu, addr, size in specs:
            L.append('read %s %s %s' % (cpu, addr, size))
        if f in saves: L.append('save %s' % saves[f])
    L.append('quit')
    open(out, 'w').write('\n'.join(L) + '\n')

def parse(path):
    cur: dict[str, Any] | None = None; key = None
    for line in open(path, errors='replace'):
        line = line.rstrip('\n')
        m = re.match(r'Session frame: (\d+)', line)
        if m:
            if cur: print(json.dumps(cur))
            cur = {'frame': int(m.group(1))}; key = None; continue
        m = re.match(r'vrd-dbg> read \S+ (\S+) \S+', line)
        if m and cur is not None:
            key = m.group(1); cur[key] = ''; continue
        m = re.match(r'([0-9A-F]{8}):((?: [0-9A-F]{2})+)$', line)
        if m and key and cur is not None:
            cur[key] += m.group(2).replace(' ', ''); continue
    if cur: print(json.dumps(cur))

if __name__ == '__main__':
    {'gen': gen, 'parse': lambda a: parse(a[0])}[sys.argv[1]](sys.argv[2:])
