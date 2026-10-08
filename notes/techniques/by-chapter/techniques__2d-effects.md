# Harvested techniques: 2D drawing and effects: shapes, scaling, rotation, transitions

Target: Part VI chapter in `src/techniques/` (or `src/howto/emulator-testing.md`). 23 entries. Raw reports and source caveats: [../raw/](../raw/) (paths relative to by-chapter/).

Evidence and licence notes are per entry. Describe in the book's own words; never copy code.

<!-- from S32X-SKILL -->
### Clipped horizontal span as the only pixel writer
- Source: S32X-SKILL, assets/2d/gfx_shapes.c:15-25; references/2d-and-shmup.md:9-20
- What it does and why it is clever: `hspan(x0,x1,y,c)` rejects rows off-screen, orders x0/x1, clamps to [0, W−1] and fills bytes. Every shape reduces to spans, so clipping lives in one place.
- Key numbers: Stride = SCREEN_W (320).
- Target chapter: NEW: 2D drawing primitives
- Evidence: shmup32x.

<!-- from S32X-SKILL -->
### Triangle fill by per-row edge intersection
- Source: S32X-SKILL, assets/2d/gfx_shapes.c:27-43
- What it does and why it is clever: For each row in [ymin, ymax], intersect all three edges, `x = ax + (bx−ax)(y−ay)/(by−ay)`, and keep min/max as the span. Horizontal edges contribute both endpoints. It is order-independent with no vertex sort, simpler than the r3d version, but it does three integer divides per row; the edge-slope trick would remove them.
- Key numbers: Up to 3 divides per row.
- Target chapter: NEW: 2D drawing primitives
- Evidence: shmup32x.

<!-- from S32X-SKILL -->
### Circle fill by integer square root per row
- Source: S32X-SKILL, assets/2d/gfx_shapes.c:45-54
- What it does and why it is clever: For each dy in [−r, r], find the largest dx with `(dx+1)² ≤ r² − dy²` and draw `hspan(cx−dx, cx+dx)`. No floats and no divides. The linear-search square root makes it O(r²) overall; for big circles carry dx between rows (it only shrinks moving away from the centre) or use a midpoint circle.
- Key numbers: —
- Target chapter: NEW: 2D drawing primitives
- Evidence: shmup32x.

<!-- from S32X-SKILL -->
### Polygon fill as a triangle fan with scaling
- Source: S32X-SKILL, assets/2d/gfx_shapes.c:56-65
- What it does and why it is clever: Takes relative `signed char` point pairs scaled by `num/den` and fans triangles from (cx,cy). Correct for star-shaped outlines visible from the centre, such as ships and enemies. Scaling one shape table gives multiple sizes.
- Key numbers: 2 bytes per vertex.
- Target chapter: NEW: 2D drawing primitives
- Evidence: shmup32x.

<!-- from S32X-SKILL -->
### Faithful graphics reconstruction from the original's draw code
- Source: S32X-SKILL, references/2d-and-shmup.md:32-51
- What it does and why it is clever: Grep the original (canvas or PICO-8) for colour literals and build CRAM from the exact `#rrggbb` values. Grep `moveTo/lineTo` paths for vertices and reproduce them with FillPoly/FillTri/FillCircle, scaled to the hitbox.
- Key numbers: About 40 px ship on a 600 px canvas → about 20 px on 224.
- Target chapter: NEW: 2D drawing primitives
- Evidence: shmup32x.

<!-- from S32X-SKILL -->
### Stipple / Bayer transparency in 8bpp indexed mode
- Source: S32X-SKILL, references/2d-and-shmup.md:134-138
- What it does and why it is clever: With no hardware alpha, skip a fraction of pixel writes in an ordered pattern: 1-in-2 for 50%, a 4×4 Bayer threshold for 16 levels. Zero memory cost; the screen-door look is acceptable for fades.
- Key numbers: 4×4 Bayer gives 16 levels.
- Target chapter: NEW: 2D drawing primitives
- Evidence: pail-court-of-demon-king-32x (33 portraits).

<!-- from S32X-SKILL -->
### Blend lookup table
- Source: S32X-SKILL, references/2d-and-shmup.md:139-142
- What it does and why it is clever: `blend[src][dst] → index`, computed offline by mixing the two palette RGBs and snapping to the nearest palette entry. One table read per pixel for a true translucent blend.
- Key numbers: 64 KiB per level (256×256). Keep only the levels you use (25/50/75%).
- Target chapter: NEW: 2D drawing primitives
- Evidence: Described.

<!-- from S32X-SKILL -->
### Software zoom by fixed-point source stepping
- Source: S32X-SKILL, references/2d-and-shmup.md:143-152
- What it does and why it is clever: Walk the destination rectangle with `src += (1<<16)·srcW/dstW` and read `src>>16`, skipping index 0. The step is computed once. Zoom and alpha are tweened over elapsed vblanks so animation keeps real time when the frame rate varies.
- Key numbers: 100-1000% zoom, 0-100% transparency.
- Target chapter: NEW: 2D drawing primitives
- Evidence: Pail RM2K port.

<!-- from S32X-SKILL -->
### Directional sprites by horizontal flip
- Source: S32X-SKILL, references/strategy-and-grid.md:70-74
- What it does and why it is clever: Store east-facing frames only and mirror them for west-facing directions.
- Key numbers: Halves directional sprite ROM.
- Target chapter: NEW: 2D drawing primitives
- Evidence: warcraft-32x.

<!-- from S32X-SKILL -->
### Split-screen viewports
- Source: S32X-SKILL, references/2d-and-shmup.md:111-124
- What it does and why it is clever: Run the render pass twice with separate cameras and HUDs, each clipped to its half of the 320×224 framebuffer. Pixel writes double, so the 60/n budget gets tighter. Cohen-Sutherland clipping is also mentioned for this collection (examples.md:199).
- Key numbers: Two passes = 2× fill.
- Target chapter: NEW: 2D drawing primitives
- Evidence: dmar collection.

---

<!-- from D32XR -->
### Doom-style fire with a precomputed random table
- Source: D32XR, m_fire.c:51-90, 97-151, 155-203, 212-323, 354-447 (licence: MIT)
- What it does and why it is clever:
  - **Spread rule.** Each cell copies to the row above, moved left by 0..2 and losing 0 or 1 heat: `r = rnd&3; dst = src - r + 1 - W; new = p - (r&1)`.
  - **Randomness.** A 256-entry table of `M_Random()&3` is cycled instead of calling the RNG.
  - **Colours.** The 26-colour ramp is matched to the game palette by minimum squared RGB distance at start-up.
  - **Shutdown.** Random amounts are subtracted from the bottom 7 rows, 4 cells per 32-bit word.
  - **CPUs.** The slave spreads non-stop while the master scrolls the title and blits 2 fire pixels per 16-bit store, with no sync (tearing accepted).
- Key numbers: 320x72 cells; 26 colours; 18-line solid base.
- Target chapter: NEW: 2D effects and transitions
- Evidence: code only

<!-- from D32XR -->
### Screen melt
- Source: D32XR, f_wipe.c:10-27, 61-195, marsnew.c:1431-1456 (licence: id limited-use for f_wipe; MIT for marsnew)
- What it does and why it is clever:
  - **Columns.** 160 two-pixel word columns, with random start delays (each column within ±1 of its neighbour, clamped to [-15, 0]).
  - **Speed.** Each column speeds up (dy = y+1 for the first 16 lines) and then moves a constant 4 lines (5 on PAL), half Doom's rate because of double buffering.
  - **Where the screens live.** The new screen is parked in Mega Drive VRAM. Each step reloads the strip uncovered last step from VRAM, then the old image is shifted down by dy in place, bottom-up with a Duff-style copy.
  - **CPUs.** Both share the column list through a TAS-locked counter.
- Key numbers: WIPEWIDTH 160; `yy[i] = oy<<8 | dy`.
- Target chapter: NEW: 2D effects and transitions
- Evidence: code only

<!-- from D32XR -->
### Anti-aliased automap lines split across both CPUs
- Source: D32XR, am_main.c:214-376, 570-740, 849-866 (licence: id limited-use)
- What it does and why it is clever:
  - **Anti-aliasing.** Wu-style: each step plots two pixels whose intensity comes from the fractional coordinate (3 bits), as `colour - shade`, because automap colours are ramps of 8 darkening entries.
  - **Horizontal lines.** A fast path writes 2 pixels per word on two rows (dim and bright).
  - **Rejection.** 2-bit outcodes discard off-screen lines.
  - **CPUs.** The master draws the top half and the slave the bottom half, each clipping lines to its own rows.
- Key numbers: 8 shades; 320-byte rows.
- Target chapter: NEW: 2D effects and transitions
- Evidence: code only

<!-- from VRD/AU/MARSDEV -->
### Inverse-mapped affine blit, and why it costs more than scaling
- Source: AU-NOTES, /mnt/data/src/aerobiz-ultimate/disasm/sh2/master/fb.c:699-735, 805-862; ROADMAP.md:967-1004
- What it does and why it is clever: Each display pixel steps source coordinates by `(dudx,dvdx)` along the row and `(dudy,dvdy)` per row, all in 16.16, with `dudx=cos/s`, `dvdx=sin/s`, `dudy=−sin/s`, `dvdy=cos/s`. Two source samples are packed per frame-buffer word. Once source Y varies along a scanline, line-table sharing (the free vertical scaling, see 32x/vdp.md) is impossible, so every display line is rasterized. The inner loop also carries two bounds tests and a row multiply. Correctness is checked by blitting the identity matrix and comparing its checksum with the 1:1 scaler.
- Key numbers: full screen 5.75 frames (about 10 fps) versus 2.13 for the 1:1 scale; a 128×128 region (23% of the screen) is about one frame; identity checksum $8040EA91 matches the 1:1 blit; Q15 sine table of 256 entries (512 B).
- Target chapter: NEW: Software 2D effects on the SH-2
- Evidence: emulator measured (PicoDrive)

<!-- from VRD/AU/MARSDEV -->
### SEGA logo spin/zoom: precomputed inverse matrices, ease curve, V-Blank-indexed frames
- Source: AU-NOTES, tools/make_sega_logo.py:1-163; disasm/sh2/master/fb.c:1156-1297; HISTORY.md:1554-1625
- What it does and why it is clever:
  - **Build time:** a Python script decodes the logo from the ROM and computes, per frame, the Q16.16 inverse matrix `(u0,v0,dudx,dvdx,dudy,dvdy)` and a clipped even-x bounding box. The SH-2 does no trig or division.
  - **Motion:** ease-out `e = 1−(1−t)³`. Scale `s = S0^(1−e)` interpolates in log space, so the zoom feels uniform. Angle is `2 turns·2π·(1−e)`.
  - **Self-check:** the script rasterizes the last frame exactly as the SH-2 does and fails the build unless it lands pixel-for-pixel on the Genesis logo.
  - **Playback:** the SH-2 picks the frame from the V-Blank count, so a slow frame is dropped rather than overrunning the Genesis hold. It clears only the previous box of each buffer, keeping two boxes, one per buffer.
- Key numbers: 96×32 logo; 110 animation frames plus 16 hold frames; S0 = 0.06; 127 frames drawn, 0 skipped (PicoDrive); layer on frames 28-154.
- Target chapter: NEW: Software 2D effects on the SH-2
- Evidence: emulator measured (PicoDrive/Ares; Ares judged "smoothest spin" by eye only)

<!-- from VRD/AU/MARSDEV -->
### Horizontal 2× stretch in place with RGB555 averaging
- Source: MARSDEV, /mnt/data/src/marsdev/examples/32x-skeleton/sh_src/mars_start.s:785-858
- What it does and why it is clever: `ScreenStretch` doubles each direct-colour line in place by walking right-to-left, so the source is not overwritten before it is read. Each source word becomes a longword: pixel and pixel, or pixel and blend. The blend `((prev & 0x7BDE) + (cur & 0x7BDE)) >> 1` averages all three RGB555 channels in one add, because masking off each channel's low bit stops carries crossing channels.
- Key numbers: mask $7BDE; pitch 640 B.
- Target chapter: NEW: Software 2D effects on the SH-2
- Evidence: code only

---

<!-- from AB-DISASM -->
### A 256×176 map stored as unique tiles, with Bresenham line drawing
- Source: AB-DISASM, disasm/modules/68k/graphics/DrawTilemapLine.asm:1-274 ($01DA34); disasm/modules/68k/graphics/DrawRouteLines.asm:1-80 ($0098D2); disasm/modules/68k/graphics/LoadScreenGfx.asm:6-44 ($0068CA)
- What it does and why it is clever:
  - The world map is LZ-decompressed into RAM as 704 unique tiles (32×22). This makes it a linear 4bpp bitmap with byte address = (x>>3)×32 + ((x>>2)&1)×2 + (y>>3)×$400 + (y&7)×4.
  - Pixels are plotted with an AND mask from the table at $05F9B6 and an OR of the colour. The colour is pre-shifted into the four nibble positions (<<12, <<8, <<4, <<0) and selected by x&3.
  - Integer Bresenham steps along the major axis.
  - Each player's route is coloured 1 or 2 depending on whether it is profitable.
  - The finished bitmap is uploaded as $2C0 tiles and shown with a static nametable.
- Key numbers: 22,528-byte canvas ($5800); 40 routes per player; x wraps mod 256.
- Target chapter: NEW: Software rendering into tile memory
- Evidence: code only (shipped)

<!-- from AB-DISASM -->
### Shortest-path line wrap on a cylindrical map, plus a one-line data patch
- Source: AB-DISASM, disasm/modules/68k/graphics/DrawTilemapLineWrap.asm:5-70 ($01DC26)
- What it does and why it is clever: The map wraps horizontally at 256 px. If $100 − dx is smaller than dx, the line is drawn the other way round the globe: dx becomes $100 − dx and x0 is shifted by +256, with each plotted x reduced mod 256. So Pacific routes wrap across the seam. Both line routines also contain a hard-coded check: when the endpoints are exactly (32,34)→(220,102), y0 is decremented. That fixes the look of one specific route in code instead of in the data.
- Key numbers: wrap width $100.
- Target chapter: NEW: Software rendering into tile memory (also howto/reverse-engineering.md)
- Evidence: code only (shipped)

---

<!-- from MK2 -->
### Guard bands instead of clipping (Mortal Kombat II)
- Source: MK2, SH-2 code at `0x060010B0` (line table), `0x06002CEC`/`0x06002D04` (clip)
- What it does and why it is clever: Lines are 368 bytes apart and line 0 starts 96 lines into the buffer, so a sprite can hang 48 pixels off either side or 96 lines off the top and still land in memory that is never shown. The clipper only rejects sprites that are entirely off-screen; the blitters never clip per pixel. Costs most of the 128 KB buffer.
- Key numbers: 368-byte pitch; 96 hidden lines above; x ≥ −48 accepted.
- Target chapter: techniques/2d-effects.md
- Evidence: ROM

<!-- from MK2 -->
### Mirrored sprites from one copy of the data (Mortal Kombat II)
- Source: MK2, SH-2 code at `0x0600271E` (draw), `0x0600292C` (mirrored blitter)
- What it does and why it is clever: A flag in the sprite record selects a second blitter that decodes the same RLE data but steps the destination pointer down instead of up, and negates the hotspot. No mirrored copies of the frames are stored.
- Key numbers: two blitters per format.
- Target chapter: techniques/2d-effects.md
- Evidence: ROM

<!-- from MK2 -->
### Overwrite image as hardware transparency (Mortal Kombat II)
- Source: MK2, SH-2 code at `0x06004CC0`, `0x06004CF2`, `0x060016AC`
- What it does and why it is clever: Every sprite, rectangle and glyph is written through the frame buffer's overwrite image (`0x24020000` + offset), where zero bytes are ignored. Word copies of shapes with holes need no masks, and glyphs are written pixel by pixel without testing for 0.
- Key numbers: —
- Target chapter: techniques/2d-effects.md
- Evidence: ROM

<!-- from AB32X -->
### Scaled sprites with a carry-chained DDA (After Burner Complete)
- Source: AB32X, SH-2 code at `0x06006778`-`0x06006A44`; notes/games/ab/ANALYSIS.md
- What it does and why it is clever: Four instructions per output word: `addc` on the fraction register, `mov.w @(r0,r0)` (r0 holds half the source address; the addressing mode doubles it), `addc` on the integer register picking up the carry, `mov.w r1,@-r6`. Unrolled 8 times, entered by a computed jump on width mod 8. Rows by a 16.16 counter and one `muls.w` per line. Mirroring by `swap.b` and writing right to left; a 2×2 fat-pixel mode doubles each source byte into a word and writes two lines. Writes go through the overwrite image so zero pixels need no test.
- Key numbers: Up to 92 sprites per drawn frame in play, 143 on the title, 30 fps.
- Target chapter: techniques/2d-effects
- Evidence: ROM + emulator

<!-- from AB32X -->
### Rotating objects built from sprites (After Burner Complete title)
- Source: AB32X, title sequence; notes/games/ab/ANALYSIS.md
- What it does and why it is clever: The spinning "II" logo is a cluster of sphere sprites. Rotation is applied to their 3D positions, then each sphere is projected and drawn as a scaled sprite, so nothing rotates pixels. The roll in play works the same way for sprite positions, plus the horizon fills.
- Key numbers: 127 sprites median, 143 max per drawn frame.
- Target chapter: techniques/2d-effects
- Evidence: ROM + emulator
