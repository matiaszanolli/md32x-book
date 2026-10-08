# Harvested techniques: First-person engines: raycasting, BSP, textured walls and floors

Target: Part VI chapter in `src/techniques/` (or `src/howto/emulator-testing.md`). 25 entries. Raw reports and source caveats: [../raw/](../raw/) (paths relative to by-chapter/).

Evidence and licence notes are per entry. Describe in the book's own words; never copy code.

<!-- from S32X-SKILL -->
### Quarter-resolution cast with a 2×2 expand using 32-bit stores
- Source: S32X-SKILL, references/software-3d.md:184-187
- What it does and why it is clever: Cast into a 128×80 8bpp buffer in SDRAM, then expand 2×2 into a 256×160 viewport. Each pair of source pixels `a,b` becomes one word `aabb`, stored to two rows, so the blit is aligned word writes. Casting at a quarter of the pixel count is the biggest single win.
- Key numbers: 128×80 = 10,240 casts → 256×160 viewport. 4 pixels per store.
- Target chapter: NEW: Raycasting
- Evidence: noudar-32x, 30 fps on one SH-2.

<!-- from S32X-SKILL -->
### One DDA per column with a column z-buffer
- Source: S32X-SKILL, references/software-3d.md:188-190
- What it does and why it is clever: Standard grid DDA per column. The one divide (ray to perpendicular distance) uses the hardware divider. Store each column's depth for occluding sprites later.
- Key numbers: 128 divides per frame at about 39 cycles each.
- Target chapter: NEW: Raycasting
- Evidence: noudar-32x.

<!-- from S32X-SKILL -->
### Per-cell textured floors and ceilings with a sky fallback
- Source: S32X-SKILL, references/software-3d.md:191-192
- What it does and why it is clever: Floors and ceilings are textured per grid cell, with animated flats (lava) and a scrolling sky wherever a cell has no ceiling.
- Key numbers: —
- Target chapter: NEW: Raycasting
- Evidence: noudar-32x.

<!-- from S32X-SKILL -->
### Two-pass billboards clipped against the column z-buffer
- Source: S32X-SKILL, references/software-3d.md:193-195
- What it does and why it is clever: Masked scenery (bars, arches, seals) is collected during the ray walk. Monsters, items and effects are depth-sorted and drawn as billboards, each column clipped against the wall z-buffer so walls occlude them correctly without a full-screen z-buffer.
- Key numbers: —
- Target chapter: NEW: Raycasting
- Evidence: noudar-32x.

<!-- from S32X-SKILL -->
### Shade-bank palette fog
- Source: S32X-SKILL, references/software-3d.md:197-205
- What it does and why it is clever: Replicate a 64-colour base palette as N darker copies in CRAM. A pixel index is `(shade<<6) | colour`, with `shade` chosen per column or billboard from depth. Fog costs nothing per pixel; it is just which bank the index lands in.
- Key numbers: 64 colours × 4 banks = 256 CRAM entries.
- Target chapter: NEW: Raycasting
- Evidence: noudar-32x.

<!-- from S32X-SKILL -->
### Shade lookup table for per-hue ramps
- Source: S32X-SKILL, references/software-3d.md:206-209
- What it does and why it is clever: When the palette is organised as 16-step brightness ramps per hue, `shade_lut[d][i] = (i & 0xF0) | min(0x0F, (i & 0x0F) + d)`. The blitter indexes through it, so one table read gives fog.
- Key numbers: depth × 256 bytes.
- Target chapter: NEW: Raycasting
- Evidence: breakfree-32x.

<!-- from S32X-SKILL -->
### Smooth camera over turn-based grid movement
- Source: S32X-SKILL, references/strategy-and-grid.md:18-20
- What it does and why it is clever: Logic moves one cell or 90° per turn. The camera slides 1/8 cell and 1/32 turn per frame, so a turn-based crawler scrolls like a free-look one.
- Key numbers: 8 frames per step, 8 frames per 90° turn.
- Target chapter: NEW: Raycasting
- Evidence: noudar-32x.

---

<!-- from D32XR -->
### Front-to-back BSP walk with a bounding-box culling table
- Source: D32XR, r_phase1.c:51-65, 121-181, 686-741 (licence: id limited-use)
- What it does and why it is clever: At each node the near child is drawn first, and the far child is visited only if its bbox might still be visible. R_CheckBBox picks the box's 3x3 position relative to the viewer with comparisons; `checkcoord[12][4]` gives the two silhouette corners (inside the box returns visible). Their angles become screen columns. If the solid-seg list already covers that column span, the whole subtree is skipped.
- Key numbers: 12 x 4 corner table; MAXSEGS 32 clip ranges.
- Target chapter: NEW: BSP and portal rendering
- Evidence: code only

<!-- from D32XR -->
### Child bounding boxes quantised to 4 bits
- Source: D32XR, p_setup.c:316-381, r_phase1.c:670-684 (licence: id limited-use)
- What it does and why it is clever: Each child bbox is stored as four 4-bit counts of 1/16ths of the parent box, shrinking inward from each side, in one uint16. The parent is decoded recursively from the world bbox during traversal: `min + (len·n)>>4`. Encoding rounds outward, so the decoded box always contains the real one; culling stays conservative but node_t shrinks from 8 int16 of bboxes to 2 uint16.
- Key numbers: 16 bits per child bbox instead of 64.
- Target chapter: NEW: BSP and portal rendering
- Evidence: code only

<!-- from D32XR -->
### Solid-seg clip ranges for occlusion
- Source: D32XR, r_phase1.c:447-545, 723-741 (licence: id limited-use)
- What it does and why it is clever: `solidsegs[]` is a sorted list of fully occluded column ranges, with sentinels at [-2,-1] and [width, width+1]. A new seg is split into the visible gaps; each gap becomes a viswall. If the seg is solid (one-sided, or a closed door), its range is merged into the list. Ranges are packed into 32-bit words so insert and delete shift whole longs. Once the list covers the screen, every further bbox check fails and traversal ends.
- Key numbers: cliprange = 2 x int16, 4-byte aligned.
- Target chapter: NEW: BSP and portal rendering
- Evidence: code only

<!-- from D32XR -->
### Clipping to view edges through angle-to-column tables
- Source: D32XR, r_phase1.c:69-115, r_data.c:526-593 (licence: id limited-use)
- What it does and why it is clever:
  - **Clipping.** A seg's endpoint angles are clipped to ±clipangle with unsigned wraparound tricks (`tspan > 2·clipangle`), and segs spanning 180° or more are rejected.
  - **Mapping.** Angles become columns through `viewangletox[(angle+90°)>>19]`. That table is built from `focal = centerX / tan(FOV/2)`, `x = centerX - tan(a)·focal`, rounded up.
  - **Inverse.** `xtoviewangle[x]` holds the smallest angle mapping to each column (16-bit, angle>>16).
- Key numbers: viewangletox 4096 entries; xtoviewangle width+1.
- Target chapter: NEW: BSP and portal rendering
- Evidence: code only

<!-- from D32XR -->
### Endpoint angle cache and seg ordering
- Source: D32XR, r_phase1.c:550-585, p_setup.c:870-905 (licence: id limited-use)
- What it does and why it is clever: R_AddLine remembers the last seg's two vertex indices and angles, and reuses them when the next seg shares a vertex, which saves R_PointToAngle and its divide. At load, segs inside each subsector are insertion-sorted by linedef so segs sharing endpoints sit next to each other.
- Key numbers: 2-entry cache.
- Target chapter: NEW: BSP and portal rendering
- Evidence: code only

<!-- from D32XR -->
### Wall classification bits, silhouettes and early rejection
- Source: D32XR, r_phase1.c:183-386, 593-623; r_local.h:503-514 (licence: id limited-use)
- What it does and why it is clever: R_WallEarlyPrep turns sector heights into an `actionbits` mask:
  - which floor and ceiling planes to add;
  - which top, middle and bottom textures to draw;
  - whether the wall updates clip bounds;
  - which sprite silhouettes it casts (TOPSIL, BOTTOMSIL, SOLIDSIL).
  
  Peg rules decide `texturemid`. Two-sided lines with identical sectors, no mid-texture and equal light are dropped (trigger lines). Sky-to-sky boundaries count as open, to avoid hall-of-mirrors artefacts. The renderer also sets ML_MAPPED, which drives the automap.
- Key numbers: 12 action bits.
- Target chapter: NEW: BSP and portal rendering
- Evidence: code only

<!-- from D32XR -->
### Packed 8:8 clip bounds and visplane marking
- Source: D32XR, r_phase2.c:235-356, r_main.c:965-990, r_local.h:366-371 (licence: id limited-use)
- What it does and why it is clever: Per column, the ceiling and floor clip are packed as `top<<8 | bottom` in a uint16. The array is initialised two entries per 32-bit store. Each seg column computes projected heights with one FixedMul each, clamps and writes the new bounds. A seg's private bounds array is a biased pointer (`lastsegclip - start`), so it is indexed by absolute x without a subtraction. Visplane `open[]` uses 0xFF00 as "unset", tested as `(int8_t)(v>>8) == -1`.
- Key numbers: MAXOPENINGS = 320·18 uint16.
- Target chapter: NEW: BSP and portal rendering
- Evidence: code only

<!-- from D32XR -->
### Hashed visplane lookup
- Source: D32XR, r_main.c:962-1036 (licence: id limited-use)
- What it does and why it is clever: Planes are found through a 32-bucket chained hash on `((height>>8) + light) ^ flat`. A plane is reused only if its open[] slot at the start column is still unmarked, so it never gets two spans in one column. Otherwise a new plane is allocated, with plane 0 as the overflow dummy. The bucket array lives on the slave's stack because only the slave marks planes.
- Key numbers: NUM_VISPLANES_BUCKETS 32; flatandlight = light<<16 | flat.
- Target chapter: NEW: BSP and portal rendering
- Evidence: code only

<!-- from D32XR -->
### Turning visplane columns into horizontal spans
- Source: D32XR, r_phase7.c:184-255 (licence: id limited-use)
- What it does and why it is clever: Walking adjacent columns' (top, bottom) pairs, rows present in the old column but not the new end a span (emitted from `spanstart[row]` to x-1), and rows newly covered record `spanstart[row] = x`. Sentinels (OPENMARK) at minx-1 and maxx+1 flush everything. Each pixel of the plane is visited once and output is row-coherent, which the span drawer needs.
- Key numbers: spanstart[180] on the stack.
- Target chapter: NEW: BSP and portal rendering
- Evidence: code only

---

<!-- from D32XR -->
### Per-column wall scale, texture column and vertical step
- Source: D32XR, r_phase2.c:47-64, 69-90, 130-230; r_phase6.c:75-153, 158-261 (licence: id limited-use)
- What it does and why it is clever:
  - **Scale at the ends.** `scale = stretchX·sin(visangle-normalangle) / (distance·sin(visangle-viewangle))`.
  - **Scale across the wall.** Linear across columns (`scalestep`), not perspective-correct, as in PC Doom.
  - **Texture column.** Perspective-correct per column: `col = (offset - distance·tan(centerangle + xtoviewangle[x])) >> 16 & 0xFF`.
  - **Vertical.** `iscale = 0xFFFFFFFF/scale` (16.16 texels per pixel); `frac0 = texturemid - (centerY - top)·iscale`; `top = centerY - scale·height`. Heights come from 12.4 storage.
- Key numbers: texture width up to 256 (&0xFF); MIPSCALE 0x20000 picks mip 1 when iscale ≥ 2 texels per pixel (only if MIPLEVELS > 1).
- Target chapter: NEW: Texture-mapped walls and floors
- Evidence: code only

<!-- from D32XR -->
### Floor and ceiling span maths with 64x64 addressing
- Source: D32XR, r_phase7.c:64-165, 293-397; r_data.c:595-611 (licence: id limited-use)
- What it does and why it is clever:
  - **Per row.** `distance = |planeheight|·yslope[y]`, with `yslope[y] = (width/2·stretch)/|y - h/2 + 0.5|`.
  - **Span start.** `length = distance·distscale[x]·2`, where distscale = 1/|cos(xangle)| stored halved in uint16. Start = view position + (cos, sin)(view+xangle)·length.
  - **Steps.** `xstep = distance·cos(view-90°)/centerX`, ystep likewise.
  - **Addressing.** `yfrac` and `ystep` are pre-multiplied by 64, so the drawer's index is `(y>>16 & 63·64) | (x>>16 & 63)`.
  - **Mips.** Optional mip level = distance / 2^24.
- Key numbers: FLATSIZE 64; yslope 180 entries; distscale 320 entries.
- Target chapter: NEW: Texture-mapped walls and floors
- Evidence: code only

<!-- from D32XR -->
### Distance lighting folded into the colormap offset
- Source: D32XR, r_local.h:48, r_phase6.c:465-554, 218-228; r_phase7.c:399-464, 131-156 (licence: id limited-use)
- What it does and why it is clever:
  - **Colormap index.** HWLIGHT = `((255-light)>>3 & 31)·256`, a byte offset into 32 colormaps of 256 bytes.
  - **Wall range.** lightmax = sector + extralight; lightmin = `light - 2·(255 - light - light/2)`. Light is a linear ramp in scale, clamped.
  - **Precomputation.** The negate, add 255 and divide by 8 of HWLIGHT are applied to the coefficients once per wall, so each column needs only one FixedMul, a subtract, a clamp and `>>16 <<8` to get the offset. Walls with equal light at both ends skip it.
  - **Floors.** The same ramp is driven by `lightcoef/distance` (the overlapped DIVU).
  - **Fake contrast.** Axis-aligned walls get ±8 light.
- Key numbers: 32 light levels; 160/800 ramp endpoints; INVERSECOLORMAP = 32·256.
- Target chapter: NEW: Texture-mapped walls and floors
- Evidence: code only

<!-- from D32XR -->
### Sky with fixed vertical mapping
- Source: D32XR, r_phase6.c:266-326 (licence: id limited-use)
- What it does and why it is clever: The sky column is `(viewangle + xtoviewangle[x]) >> 22 & 0xFF`, so it depends only on angle and wraps 4 times per turn. Vertically it uses constants, `frac = top·72816`, `step = 65536+7281` (about 1.111 texels per pixel), independent of distance. Each column is one direct drawcol call. 4bpp skies use the 4bpp drawer and a 64-byte pitch.
- Key numbers: sky texture 128 tall.
- Target chapter: NEW: Texture-mapped walls and floors
- Evidence: code only

<!-- from D32XR -->
### 16-colour textures with their own colormaps
- Source: D32XR, r_main.c:430-436, r_phase6.c:381-392, sh2_draw4b.s:14-100, r_phase9.c:218-242 (licence: id limited-use)
- What it does and why it is clever: A texture whose header has depth 2 and flag 0x8 stores 4-bit texels plus its own 33x16 lighting table at the end of the lump. The 4bpp drawer turns `light>>3` into an index into that table, uses the shifted-out bit of `shlr` (T flag) to choose the nibble, and the nibbles are pre-swapped in the data to save address maths. Half-size textures in ROM; expanded to 8bpp when cached.
- Key numbers: 33·16·2 bytes of tables per texture.
- Target chapter: NEW: Texture-mapped walls and floors
- Evidence: code only

<!-- from D32XR -->
### "Potato" solid-colour floors
- Source: D32XR, r_phase7.c:167-179, 329; marsdraw.c:505-585; r_phase9.c:98 (licence: id limited-use for r_phase files; MIT for marsdraw.c)
- What it does and why it is clever: The potato plane mapper skips distance, step and light maths. Each span is filled with one lit colour: texel 513 of the flat (row 8, col 1) through the plane's constant colormap. The fill uses 16-bit stores, 2 pixels per write, with byte fix-ups at odd edges. Flats are also left out of the texture-cache budget in this mode.
- Key numbers: 1 lookup per span.
- Target chapter: NEW: Texture-mapped walls and floors
- Evidence: code only

<!-- from D32XR -->
### Spectre fuzz effect
- Source: D32XR, r_main.c:31-42, r_data.c:613-617, sh2_draw.s:164-223 (licence: id limited-use)
- What it does and why it is clever: A 64-entry ±1 table is pre-scaled to ±320 (one framebuffer row). Each pixel reads the framebuffer pixel above or below and darkens it through colormap 12. The table position persists per CPU in TLS, and the first and last rows are skipped to stay in bounds.
- Key numbers: FUZZTABLE 64.
- Target chapter: NEW: Texture-mapped walls and floors
- Evidence: code only

<!-- from D32XR -->
### Optional mipmaps for walls and flats
- Source: D32XR, r_data.c:244-321, r_main.c:416-495, r_phase6.c:110-121 (licence: id limited-use)
- What it does and why it is clever: Mip chains are detected by whether the lump is long enough for halved sizes after level 0. A texture with decals is limited to its decals' smallest mip count. When drawing, frac, step and column are shifted per level. Each wall records its min and max mip used so phase 9 caches only the levels actually needed. Compiled out by default.
- Key numbers: MIPLEVELS build option.
- Target chapter: NEW: Texture-mapped walls and floors
- Evidence: code only

---

<!-- from D32XR (hardware survey) -->
### d32xr hardware survey: Column and span drawers
- Calling convention r4-r7 + stack; colormap and frame-buffer base from GBR (sh2_draw.s:31-33). `y*320` = `(y<<8)+(y<<6)` (:34-42). Delay-slot branches; loops unrolled 2x with mid-loop entry for odd counts (:50-54); `.p2alignw` on loop heads (:56).
- `I_DrawColumnA` (sh2_draw.s:17-78): 16.16 texture coordinate, `swap.w` for the integer part, mask by texheight-1; per pixel load texel, load colormap, store, add 320: 16 instructions per 2 pixels.
- Non-power-of-2 column wrap by subtracting texheight<<16 (sh2_draw.s:88-154; "tutti frutti" fix explained at marsdraw.c:120-124).
- Fuzz reads the frame buffer at +-320 (sh2_draw.s:166-223; r_data.c:613-617).
- Span drawer (sh2_draw.s:233-335) draws right to left with pre-decrement stores; end coordinates by `dmuls.l step,count` (:276-290); flat index `((yfrac>>16) & 63*64) | ((xfrac>>16) & 63)` with y pre-multiplied by FLATSIZE in C (r_phase7.c:117-119, 378-380); y-mask built with `mulu.w` (sh2_draw.s:267-274).
- Lighting: `HWLIGHT(l) = ((255-l)>>3 & 31)*256`, 32 rows of 256 bytes (r_local.h:47-48). Colormap base is the lump + 128 so the sign-extended `mov.b` texel works as a signed index (r_data.c:906-908; marsdraw.c:98).
- 4-bit textures (sh2_draw4b.s, sh2_drawlow4b.s): two texels per byte; `shlr` halves the index and leaves the nibble select in T. Comment sh2_draw4b.s:61-63: nibbles pre-swapped in the data to save address maths. Per-texture 16-colour x 33-level x 2-byte colormap at the end of the lump (r_main.c:434-436). Expanded to 8-bit when copied to the SDRAM texture cache (r_phase9.c:218-241).
- MIPLEVELS defaults to 1 (r_local.h:151-152).

