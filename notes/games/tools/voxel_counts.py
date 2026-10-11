"""Counts behind src/techniques/voxel.md: pixels, samples and cells for zepton32x's two voxel
methods, worked out from the code and scale S32X-SKILL's voxel-landscape.md lists (the game's own
source was not available), plus the sample-cost bound from the two measured rates.

usage: python3 -I voxel_counts.py

Scale from the notes: CELL = 1 unit, CELLZ = 98,304 (1.5 units in 16.16), FOCAL = 120, NEAR = 12
units, 32 x 28 cells, 320 x 224 packed 8-bit screen. Projection as listed: zz = wz >> 8,
rf = (FOCAL << 12) / zz, size = (256 * rf) >> 12. Method A draws a (size + 1) x (2 size + 2) block
per cell plus a one-line ridge when size >= 2; nothing is clipped here, so the block counts are
upper bounds for the near rows. Method B's rays cross the whole screen at every depth.
"""
import math

FOCAL, NEAR, CELLZ, NX, NZ, W, H = 120, 12 * 65536, 98304, 32, 28, 320, 224
CLK, FRAME = 23.01e6, 1 / 59.92                    # SH-2 clock (NTSC), frame time


def slices(frac):
    """-> [(depth in units, size in pixels)] for each slice, near to far, at scroll fraction
    frac (0..65535 of a row)"""
    sub = (frac * CELLZ) >> 16
    out = []
    for s in range(NZ):
        wz = NEAR + s * CELLZ - sub
        rf = (FOCAL << 12) // (wz >> 8)
        out.append((wz / 65536, max(1, (256 * rf) >> 12)))
    return out


print('full clear: %d pixels' % (W * H))
for frac in (0, 32768, 65535):
    sz = slices(frac)
    blocks = sum(NX * (s + 1) * (2 * s + 2) for _, s in sz)
    ridges = sum(NX * (s + 1) for _, s in sz if s >= 2)
    tall = sum(NX * (s + 1) * 3 * s for _, s in sz)
    # B: distinct cells one slice's 160 two-pixel columns land in, if each step is snapped to a cell
    cells = sum(len({math.floor((sx + 1 - W // 2) * z / FOCAL) for sx in range(0, W, 2)}) for z, _ in sz)
    # a like-for-like B: rays stop at A's 32 columns (world x in [-16, 16))
    inside = sum(1 for z, _ in sz for sx in range(0, W, 2)
                 if -NX // 2 <= (sx + 1 - W // 2) * z / FOCAL < NX // 2)
    print('scroll fraction %5d: sizes %s' % (frac, [s for _, s in sz]))
    print('  A: blocks %d + ridges %d = %d pixel writes (3 x size blocks: %d); far slice %.0f px wide'
          % (blocks, ridges, blocks + ridges, tall, NX * FOCAL / sz[-1][0]))
    print('  B: rays span %.0f cells at the front, %.0f at the back; %d distinct cells of %d samples;'
          ' stopped at A\'s columns, %d steps over %d cells'
          % (W * sz[0][0] / FOCAL, W * sz[-1][0] / FOCAL, cells, 160 * NZ, inside, NX * NZ))

# measured rates: A about 19, B about 8 pictures per 60 frames. Each picture lasts whole frames,
# so the true gap lies between the rounded extremes.
a, b = 60 / 19, 60 / 8
print('A %.1f ms, B %.1f ms a picture' % (a * FRAME * 1e3, b * FRAME * 1e3))
for name, da, db in (('rates as given', a, b), ('smallest gap', a, b - 1), ('largest gap', a - 1, b)):
    gap = (db - da) * FRAME
    c = gap / (160 * NZ - NX * NZ)
    print('%-15s gap %.1f ms -> each extra ray step >= %.1f us = %.0f clocks; 896 such = %.1f ms'
          % (name, gap * 1e3, c * 1e6, c * CLK, NX * NZ * c * 1e3))

# software divides: libgcc ___sdivsi3 for -m2 is 77 instructions (the same in GCC 12.1's source,
# marsdev's 15.1 and 16.2); about 80 clocks with the call
for what, n in (('per cell, three each', 3 * NX * NZ), ('the notes\' count', 1800),
                ('per slice', NZ), ('B as listed, one per step', 160 * NZ)):
    print('%-26s %5d divides = %7d clocks = %.1f ms' % (what, n, n * 80, n * 80 / CLK * 1e3))
# pixel time in PicoDrive (instruction clocks only). GFX_FillRect's code is not in the notes, so
# these are store loops of plausible shape, not the game's: per row a few clocks of set-up (6), per
# pixel 0.5 (longwords), 1 (words) or 3 (bytes with loop); B's 2-pixel strips: store, pointer step,
# dt, bf per line (6 clocks)
sz = slices(0)
rows = sum(NX * (2 * s + 2) + (NX if s >= 2 else 0) for _, s in sz)
px = sum(NX * (s + 1) * (2 * s + 2) + (NX * (s + 1) if s >= 2 else 0) for _, s in sz)
for per in (0.5, 1, 3):
    a_clk = rows * 6 + px * per + W * H * per          # blocks + full clear at the same rate
    print('A pixel time at %.1f clocks a pixel: %.1f ms (%d rows)' % (per, a_clk / CLK * 1e3, rows))
print('B pixel time, at most %d strip rows at 6 clocks: %.1f ms' % (W * H // 2, W * H // 2 * 6 / CLK * 1e3))
extra = 160 * NZ - NX * NZ                          # B's extra steps
pix_worst = (W * H // 2 * 6 - (rows * 6 + px * 0.5 + W * H * 0.5)) / CLK   # B's pixels slower by
gap_min = (b - 1 - a) * FRAME - pix_worst
print('floor with both assumptions at worst: gap %.1f ms -> %.0f clocks a step, %.0f after the divide'
      % (gap_min * 1e3, gap_min / extra * CLK, gap_min / extra * CLK - 80))
# frame mix behind the averages: A 16 x 3 + 3 x 4 frames, B 4 x 7 + 4 x 8. With a cost that varies
# little, A sits just under 3 frames and B near 7, the boundaries the mixes straddle.
gap_mix = (7 - 3) * FRAME
step_mix = gap_mix / extra * CLK
print('frame mix: A ~%.1f ms, B ~%.1f ms, gap ~%.1f ms -> about %.0f clocks a step'
      % (3 * FRAME * 1e3, 7 * FRAME * 1e3, gap_mix * 1e3, step_mix))
# a B on A's terms (one divide per slice, rays stopped at A's columns), from B's cost: the shown
# average for the floors, about 7 frames for the frame mix. Off-grid steps are assumed to cost as
# much as the average step. Then the extra a ring of kept heights saves B over A, if the sample were
# all of a step's cost after the divide.
inside = [sum(1 for z, _ in slices(f) for sx in range(0, W, 2)
              if -NX // 2 <= (sx + 1 - W // 2) * z / FOCAL < NX // 2) for f in (0, 65535)]
for name, step, b_ms, a_ms in (('floor (360)', (b - 1 - a) * FRAME / extra * CLK, b, a),
                               ('combined floor', gap_min / extra * CLK, b, a),
                               ('frame mix', step_mix, 7, 3)):
    rest = step - 80
    like = (b_ms * FRAME - (160 * NZ - NZ) * 80 / CLK - (160 * NZ - max(inside)) * rest / CLK) * 1e3
    gain = [(n - NX * NZ) * rest / CLK * 1e3 for n in inside]
    print('%-15s step %.0f: A cells %.1f ms; like-for-like B ~%.0f ms + side clear against A %.0f;'
          ' ring gains B %.1f-%.1f ms more than A'
          % (name, step, NX * NZ * rest / CLK * 1e3, like, a_ms * FRAME * 1e3, min(gain), max(gain)))
saved = (160 * NZ - NZ) * 80 / CLK
print('B with its scale factors in a 28-entry table: %.1f ms a picture (%.2f frames)'
      % ((b * FRAME - saved) * 1e3, b - saved / FRAME))
