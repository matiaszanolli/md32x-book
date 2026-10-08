# usage: python3 profgroups.py GAME PC_CSV FRAMES
#        python3 profgroups.py GAME --samples DEBUG_OUT
# GAME is swa (Star Wars Arcade) or ab (After Burner Complete).
# Groups a VRD_PROFILE_PC log by role (waits, drawing, sound) and prints each
# group as clocks per frame and as a share of an NTSC frame (384,000 SH-2
# clocks, 128,000 68000 clocks). Shares are of executed cycles: PicoDrive puts
# a CPU to sleep when it polls a 32X register, so the rows do not sum to 100%
# (build_sleep_core.sh logs the sleeps). The stock profiler keeps only the top
# 200 PCs per CPU; the core from build_sleep_core.sh keeps them all.
# --samples instead reads the output of a debug script that runs
# `run 1` / `regs master` / `regs slave` per frame (for play, where
# VRD_PROFILE_PC hangs the game) and prints the share of frames whose PC falls
# in each group. All samples are taken at the same point of the frame, so they
# are a rough guide, not a profile.
import re
import sys
FRAME = 384000
SWA = {
    'Master': [
        ('idle, waiting for the 68000 (0E10)', 0x06000E10, 0x06000E24),
        ('waiting for the Slave (1030)', 0x06001030, 0x06001042),
        ('object call, waiting for 68000 (12CC)', 0x060012CC, 0x060012D0),
    ],
    'Slave': [
        ('waiting for Master command (0750)', 0x06000740, 0x0600077A),
        ('end of frame: ring drain (0B9A)', 0x06000B9A, 0x06000BA5),
        ('end of frame: FEN (0BAE)', 0x06000BAE, 0x06000BB3),
        ('flip: waiting for vblank (0BB4)', 0x06000BB4, 0x06000BC5),
        ('drawing handler FEN polls', 0xC0000594, 0xC0000599),
        ('drawing handler FEN polls', 0xC0000664, 0xC0000669),
        ('drawing handler, other', 0xC0000582, 0xC000074A),
        ('cutter (on-chip)', 0xC0000000, 0xC0000581),
        ('PWM handler and decoder', 0x06000980, 0x06000AAF),
        ('dispatcher', 0x0600051C, 0x0600053D),
    ],
    '68K': [
        ('vblank wait (FFFF0158)', 0xFFFF0158, 0xFFFF015D),
        ('command handshakes (FFFF3B6E-3C76)', 0xFFFF3B6E, 0xFFFF3C76),
    ],
}
# After Burner Complete. Frame-buffer work: the scaled sprite blits and the
# line table; everything else useful works in SDRAM or registers only.
AB = {
    'Master': [
        ('fill: polling FEN', 0x060082C0, 0x060082C3),
        ('fill: polling FEN', 0x060082D0, 0x060082D3),
        ('fill: polling FEN', 0x060082E6, 0x060082E9),
        ('fill: polling FEN', 0x06008304, 0x06008307),
        ('fill: polling FEN', 0x06008348, 0x0600834B),
        ('fill: polling FEN', 0x0600D0DA, 0x0600D0DD),
        ('fill: polling FEN', 0x0600D0E2, 0x0600D0E5),
        ('fill: polling FEN', 0x0600D0EC, 0x0600D0EF),
        ('fill: polling FEN', 0x06003A94, 0x06003A9B),
        ('fill: set-up', 0x06008280, 0x060084FF),
        ('fill: set-up', 0x0600D0C8, 0x0600D0F3),
        ('waiting for the 68000 (38E6)', 0x060038E6, 0x06003913),
        ('waiting for the flip (395C)', 0x0600395C, 0x06003967),
        ('FB: scaled sprite drawing', 0x06006778, 0x06006BEF),
        ('FB: line table (3C1C)', 0x06003C1C, 0x06003C2F),
        ('SDRAM: sprite list and cache', 0x060065A0, 0x06006777),
        ('SDRAM: horizon and runway set-up', 0x06006BF0, 0x0600724B),
        ('SDRAM: depth sort (3B66)', 0x06003B66, 0x06003C1B),
        ('SDRAM: command interrupt, projection', 0x06002000, 0x060038E5),
    ],
    'Slave': [
        ('ring full: spinning (03C0, 0820, 07F4)', 0x060003C0, 0x060003CB),
        ('ring full: spinning (03C0, 0820, 07F4)', 0x06000820, 0x06000827),
        ('ring full: spinning (03C0, 0820, 07F4)', 0x060007F4, 0x060007F5),
        ('mixer', 0x060003CC, 0x0600046F),
        ('PWM interrupt', 0x06000390, 0x060003BD),
    ],
    '68K': [
        ('vblank wait (890B8A)', 0x00890B8A, 0x00890B97),
        ('waiting for the Master to take a command (89C6CA)', 0x0089C6CA, 0x0089C6CF),
        ('waiting for the Master\'s answer (8873A8)', 0x008873A8, 0x008873AD),
        ('waiting for the Master\'s answer (88A038)', 0x0088A038, 0x0088A03D),
    ],
}
GAMES = {'swa': SWA, 'ab': AB}

def group(groups, pc):
    for name, a, b in groups:
        if a <= pc <= b:
            return name
    return 'other'


GROUPS = GAMES[sys.argv[1]]
del sys.argv[1]
if sys.argv[1] == '--samples':
    pcs = {'Master': [], 'Slave': []}
    for l in open(sys.argv[2]):
        m = re.match(r'(Master|Slave) SH2: PC=([0-9A-F]+)', l)
        if m:
            pcs[m.group(1)].append(int(m.group(2), 16))
    for cpu, arr in pcs.items():
        out = {}
        for pc in arr:
            name = group(GROUPS[cpu], pc)
            out[name] = out.get(name, 0) + 1
        print('%s: %d samples' % (cpu, len(arr)))
        for name, n in sorted(out.items(), key=lambda x: -x[1]):
            print('  %-40s %5.1f%%' % (name, 100 * n / len(arr)))
    sys.exit()

rows = [l.rstrip().split(',') for l in open(sys.argv[1]) if l[:2] in ('Ma', 'Sl', '68')]
frames = int(sys.argv[2])
for cpu, groups in GROUPS.items():
    out = {}
    total = 0
    for r in rows:
        if r[0] != cpu:
            continue
        pc, c = int(r[1], 16), int(r[2])
        total += c
        name = group(groups, pc)
        out[name] = out.get(name, 0) + c
    clk = FRAME if cpu != '68K' else FRAME // 3
    print('%s: executed %.0f clocks a frame (%.0f%%)' % (cpu, total / frames, 100 * total / frames / clk))
    for name, c in sorted(out.items(), key=lambda x: -x[1]):
        print('  %-40s %8.0f a frame  %5.1f%%' % (name, c / frames, 100 * c / frames / clk))
