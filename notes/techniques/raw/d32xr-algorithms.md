# D32XR algorithm harvest: Doom 32X Resurrection

Repo root: `/tmp/claude-1000/-mnt-data-src-md32x-book/014ad006-fdd4-4f3e-a7ed-6836ee1471ee/scratchpad/d32xr`. All paths below are relative to it.

**Licence labels.** I applied your rule literally: a file is MIT only if its own header says MIT. Some files fall to "id limited-use" under that rule even though their headers say something else, so check these before quoting any of them:
- **CALICO header only, no MIT text:** `r_phase1.c` to `r_phase9.c`.
- **"Original code by Chilly Willy", no licence text:** `sh2_draw.s`, `sh2_drawlow.s`, `sh2_draw4b.s`.
- **Tim Ferguson's "You may freely use this source code":** `roq_read.c`.
- **No header at all:** `liblzss/lzss.c`, `marssound.c`, `f_wipe.c`.

**Build defaults that change what the code does:**
- **SH-2 mixer is off by default.** The Makefile defines `DISABLE_DMA_SOUND` unless `ENABLE_DMA_SOUND` is set.
- **No mipmaps by default.** `MIPLEVELS` defaults to 1, so the mip code is compiled out.
- **The fire effect is optional.** It needs `ENABLE_FIRE_ANIMATION`.
- **`USE_SMALL_LUMPS` is optional.** It makes the game read segs and nodes straight from ROM.

**Evidence.** No comment anywhere says something was measured or tested on hardware. Two comments come close, and I quote them where they apply: the DIVU cycle-count comment (a spec figure, not stated as measured) and the "minimize pipeline stalls" rationale.

---

## patterns/cpu-split.md

### Renderer phase map and two-CPU schedule
- Source: D32XR, r_main.c:1124-1183, mars.h:82-190, marsnew.c:355-405 (licence: id limited-use for r_main.c; MIT for mars.h and marsnew.c)
- What it does and why it is clever: The nine Jaguar phases survive as function names, but on the 32X they run in this order: R_Setup, then phase 1 (BSP walk, master), overlapped with phase 2 (wall late-prep and visplane marking, slave), then phase 6 (seg drawing, both CPUs), phase 7 (visplanes, both CPUs), phase 3 (sprite projection, master), phase 8 (sprites, screen split between CPUs) and phase 9 (texture-cache update, master). Phase 4 (late prep) just returns true and phase 5 (graphics caching) is an empty stub; their Jaguar bodies did LRU purging and LZSS-to-CRY decoding. The slave is a command loop that polls COMM4 and runs a whole multi-phase job per command; WALL_PREP chains WallPrep, SegCommands and PreDrawPlanes. Most per-frame synchronisation is therefore a single COMM register write.
- Key numbers: 12 secondary command codes (mars.h:36-58); FRT timestamps per phase.
- Target chapter: patterns/cpu-split.md
- Evidence: code only

### Producer/consumer pipeline between BSP and wall prep
- Source: D32XR, r_phase1.c:391-441, r_phase2.c:360-416, mars.h:91-108 (licence: id limited-use for the r_phase files; MIT for mars.h)
- What it does and why it is clever: Each time the master emits a viswall during BSP traversal, it increments a byte counter in COMM6 (Mars_R_WallNext). The slave polls that byte and runs R_WallLatePrep and R_SegLoop on every wall up to it. When BSP finishes the master writes -2, which tells the slave to read the final `lastwallcmd`. Front-to-back traversal and the projection and clip work therefore overlap without locks: the counter is a one-way, monotonic, single-writer channel.
- Key numbers: byte counters cap the list at 255 walls; MAXWALLCMDS = 165.
- Target chapter: patterns/cpu-split.md
- Evidence: code only

### Both CPUs drawing walls: claim flag plus replayed private clip state
- Source: D32XR, r_phase6.c:396-613 (licence: id limited-use)
- What it does and why it is clever: Both CPUs walk the same viswall list in order. CPU A waits until the slave's "ready" byte (COMM6+1) is past index i. It then takes a spin lock (`atomic_flag_test_and_set`, i.e. TAS.B) and sets AC_DRAWN to claim the seg, so each seg is drawn exactly once. Every CPU, whether or not it drew a seg, then copies that seg's new clip bounds into its own private `clipbounds[]` (post_draw). The occlusion state at index i depends only on segs before i, so each CPU rebuilds it independently and never shares it. A CPU that reaches the end writes -1 so the other stops early.
- Key numbers: clipbounds are 160 longs on the stack per CPU (two 16-bit entries per long).
- Target chapter: patterns/cpu-split.md
- Evidence: code only

### Splitting long walls for load balance
- Source: D32XR, r_phase1.c:391-441 (licence: id limited-use)
- What it does and why it is clever: R_StoreWallRange cuts any visible wall range longer than centerX/2 columns into several viswalls. A budget `splitspans` stops it splitting once 1.5x the viewport width in columns has been split. Small work items let the two CPUs' seg-drawing loops finish at about the same time, and the budget keeps the list under MAXWALLCMDS.
- Key numbers: chunk = centerX/2 (80 columns at 320 width); budget = 1.5 x viewportWidth.
- Target chapter: patterns/cpu-split.md
- Evidence: code only

### Visplane work queue sorted largest-first and by flat
- Source: D32XR, r_phase7.c:272-291, 480-566 (licence: id limited-use)
- What it does and why it is clever: The visplanes are insertion-sorted on a 16-bit key, `(127 - min(127, (maxx-minx-1)>>4)) << 8 | flat`, so wide planes come first and planes sharing a flat sit together. Both CPUs then pull the next plane index from a counter in COMM6 under a TAS lock. That is dynamic scheduling with longest jobs first, so the tail imbalance stays small. Grouping by flat keeps the same 4 KB flat in the CPU cache. Whichever CPU gets the lock first does the sort; the other waits.
- Key numbers: MAXVISPLANES 32; key = 7 bits of negated length plus 8 bits of flat. The comment reads "to minimize pipeline stalls, the larger planes must be drawn first".
- Target chapter: patterns/cpu-split.md
- Evidence: code only (rationale comment, not a measurement)

### Sprite screen split at the pixel-weighted centroid
- Source: D32XR, r_phase8.c:516-621, 397-465 (licence: id limited-use)
- What it does and why it is clever: The split column is the weighted mean `half = Σ (x1 + w/2)·w / Σ w` over every sprite, the weapon sprites and every masked mid-texture wall, where w is each one's pixel width. The master draws columns [0, half) and the slave [half, width). The sign of `sprscreenhalf` tells each CPU which side it owns (positive = left limit, negative = right start). Each CPU keeps its own sprite-opening array, so the load balances by drawn pixels rather than by sprite count.
- Key numbers: falls back to width/2 if the centroid is 0 or off-screen.
- Target chapter: patterns/cpu-split.md
- Evidence: code only

### Per-CPU thread-local state through GBR
- Source: D32XR, doomdef.h:1370-1395, sh2_draw.s:31-33, marsnew.c:368 (licence: id limited-use for doomdef.h and sh2_draw.s; MIT for marsnew.c)
- What it does and why it is clever: Each CPU points GBR at its own small TLS block holding the bank page, a bank-switch function pointer, its validcount array, column cache, current colormap, fuzz position and framebuffer base. The same assembly drawers fetch per-CPU state with one `mov.l @(disp,GBR),r0` each, so no CPU-id branch or extra argument is needed. The slave's validcount array sits right after the master's, so blockmap "already checked" marks never collide.
- Key numbers: TLS offsets 0, 4, 8, ..., 24 bytes (7 slots).
- Target chapter: patterns/cpu-split.md
- Evidence: code only

### Parallel, batched sight checks
- Source: D32XR, p_sight.c:367-543, p_base.c:270-288 (licence: MIT)
- What it does and why it is clever: Sight checks are not done on demand from AI code. Once per tic, both CPUs scan the mobj list for monsters whose `tics == 1` (about to change state) and that have a target, and set MF_SEETARGET. A TAS-locked shared cursor (`next_sight`) hands out mobjs; the slave purges cache lines for each mobj and target before reading them. The thinker later purges the cache line holding `flags` before it reads them, so it sees the other CPU's result.
- Key numbers: skipped in demos and real netgames.
- Target chapter: patterns/cpu-split.md
- Evidence: code only

---

## patterns/cache.md

### Hot code in SDRAM, compiled for size
- Source: D32XR, doomdef.h:65-72, mars-ssf.ld:104-118 (licence: id limited-use; the .ld has no header)
- What it does and why it is clever: The macro `ATTR_DATA_CACHE_ALIGN` puts a function in section `.sdata` and compiles it with `-Os`. The linker places `.sdata` inside `.data`, so crt0 copies it from ROM into SDRAM at boot. Every inner loop (BSP, seg loop, plane loop, the drawers, the mixer, FixedDiv, blockmap iterators) therefore runs from SDRAM rather than the slower cartridge ROM. Small code keeps the working set inside the 4 KB cache.
- Key numbers: SDRAM 0x06000000, 0x3F800 usable; the two stacks sit at the top.
- Target chapter: patterns/cache.md
- Evidence: code only

### Caching policy chosen per table
- Source: D32XR, tables.c:2589-2595, r_data.c:619-625, r_main.c:887-922 (licence: id limited-use)
- What it does and why it is clever: The large ROM trig tables (finesine, finetangent, tantoangle) are always read through the cache-through mirror (address + 0x20000000), so random lookups do not evict the hot working set. The small per-viewport tables (viewangletox, distscale, yslope, xtoviewangle) live in framebuffer scratch and are deliberately made cacheable by clearing that bit (`& ~0x20000000`, "enable caching for LUTs"). Map arrays are also aligned to 16-byte cache lines on load (p_setup.c:73-74 and others).
- Key numbers: 16-byte cache lines; uncached alias = +0x20000000.
- Target chapter: patterns/cache.md
- Evidence: code only

### Per-CPU column cache for composite textures
- Source: D32XR, r_phase6.c:126-147, r_data.c:936-1035, r_main.c:915-926 (licence: id limited-use)
- What it does and why it is clever: Multi-patch wall textures ("decals") are not stored pre-composited. When a column is first needed, R_CompositeColumn builds it into a small per-CPU buffer, and `lastcol` remembers which column is in there, so a wall that repeats a column in adjacent screen columns does not rebuild it. Later decals are written through the framebuffer overwrite alias (see 32x/vdp.md), so their transparent zero bytes need no per-pixel test.
- Key numbers: MAX_COLUMN_LENGTH 128; 2 textures x 128 bytes per CPU (x2 with mips); up to 3 decals per texture (`decals & 3`).
- Target chapter: patterns/cache.md
- Evidence: code only

---

## patterns/bus.md

### ROM-to-SDRAM texture cache: one upload per mip level per frame
- Source: D32XR, r_phase9.c:13-247, r_cache.c:84-250, r_main.c:570-596 (licence: id limited-use for r_phase9 and r_main; MIT for r_cache)
- What it does and why it is clever:
  - **Selection.** After each frame, R_UpdateCache walks the viswalls nearest-first. For each mip level it picks the first visible texture or flat not already resident, and copies only that one into a cache zone. Upload cost is spread out and the most prominent surfaces win.
  - **Swap and restore.** The texture's `data[]` pointer is swapped to the RAM copy; on eviction the ROM pointer (`userpold`) is put back, so drawing code never knows which copy it has.
  - **Back-pointer and alignment.** A pointer to the cache entry is stored in the 4 bytes before the pixel data, so "touch" is O(1) from the data pointer. The copy keeps the low 4 address bits of the ROM original.
  - **Lookup and ageing.** `R_InTexCache` classifies any pointer as ROM, RAM or cache with a range compare. Entries age by one per frame and are evicted after 3 untouched frames, or sooner if they are smaller than the request and were not touched this frame.
  - **Sizing.** At level start the zone is sized as the largest free block minus an 8 KB game margin.
  - **4bpp expansion.** 4bpp textures are expanded to 8bpp as they are cached.
- Key numbers: CACHE_FRAMES_WALLS/FLATS = 3; DEFAULT_GAME_ZONE_MARGIN 8 KB; minimum cache = one 64x64 flat plus header.
- Target chapter: patterns/bus.md
- Evidence: code only

### Virtual ROM addresses mapped through 512 KB bank windows
- Source: D32XR, marsnew.c:680-741, p_setup.c:347-365 (licence: MIT for marsnew.c; id limited-use for p_setup.c)
- What it does and why it is clever: Lump pointers beyond the directly mapped ROM are "virtual" addresses. `I_RemapPtr` turns one into a page number `(addr - 0x02000000) >> 19`, switches the current CPU's bank window to that page (cached in TLS, so it is skipped if already selected) and rebuilds the address inside the window. Level setup records which page holds SEGS (`segspage`), and the BSP, sight and sprite code re-select it on entry. That is how levels larger than the window are played straight from ROM.
- Key numbers: 512 KB pages.
- Target chapter: patterns/bus.md
- Evidence: code only

---

## sh2/divu.md

### FixedDiv and IDiv on the divide unit
- Source: D32XR, sh2_fixed.s:35-68 (licence: MIT)
- What it does and why it is clever: FixedDiv computes `(a<<16)/b` as a 64/32 divide. The high dividend word is `exts.w(swap.w a)` (that is, a>>16 sign-extended) and the low word is `a<<16`; writing the low word starts the divide and reading back the quotient stalls until it is ready. IDiv uses the 32/32 entry. The DIVU base 0xFFFFFF00 is a literal here; the inline C versions build it in two instructions instead (`mov #-128,rX; add rX,rX`).
- Key numbers: comment: "overflow returns 0x7FFFFFFF or 0x80000000 after 6 cycles; no overflow returns the quotient after 39 cycles".
- Target chapter: sh2/divu.md
- Evidence: code only (cycle figures are a spec comment, not stated as measured)

### Hiding divide latency: start the divide early, read it late
- Source: D32XR, r_phase6.c:190-247, r_phase7.c:82-140, r_phase8.c:66-98, r_phase2.c:188-229, r_main.c:96-127, p_sight.c:69-114, marsroq.c:891-896 (licence: id limited-use for r_phase and r_main; MIT for p_sight and marsroq)
- What it does and why it is clever: Every hot divide is issued through inline asm at the top of its loop and its quotient is read only after independent work is done. Examples:
  - **Wall column (R_DrawSeg).** Computes `iscale = 0xFFFFFFFF/scale` as a 64/32 divide with high = 0, low = -1, which is 1/scale in 16.16. Meanwhile it does the light and texture-column maths.
  - **Floor span (R_MapPlane).** Divides `lightcoef/distance` while computing the span steps.
  - **Wall prep (R_WallLatePrep).** Divides `scalestep = (scale2-scale1)/(stop-start)` while R_SetupCalc runs.
  - **R_PointToAngle (SlopeAngle).** Loads the tantoangle pointer during the divide.
  - **Masked segs (R_DrawMaskedSegRange).** Same pattern as the wall column.
  - **Sight checks.** The sight intercept uses a 64/32 divide.
  - **RoQ.** The player computes audio time as samplecount<<16 / 22050.
- Key numbers: the up-to-39-cycle divide overlaps about 10-20 instructions of other work per column or span.
- Target chapter: sh2/divu.md
- Evidence: code only

---

## sh2/isa.md

### FixedMul with dmuls.l and xtrct
- Source: D32XR, sh2_fixed.s:23-33, doomdef.h:625 (licence: MIT for sh2_fixed.s; id limited-use for doomdef.h)
- What it does and why it is clever: A 16.16 x 16.16 product needs the middle 32 bits of the 64-bit result. `dmuls.l` produces MACH:MACL and `xtrct mach,macl` pulls out bits 47..16 in one instruction (in the rts delay slot). C code mostly uses `((int64_t)a*b)>>16` and lets GCC emit the same thing. P_ApplyFriction switched from the Jaguar's `(x>>8)*(f>>8)` to FixedMul because arithmetic `>>8` is costly on the SH-2.
- Key numbers: 5 instructions including rts.
- Target chapter: sh2/isa.md
- Evidence: code only (p_base.c:56-64 explains "much slower on the SH-2")

### SH-2 micro-idioms used throughout
- Source: D32XR, r_local.h:280-311, r_data.c:901-915, sh2_draw.s:34-42, r_phase8.c:117-121, p_sight.c:303-319, r_phase1.c:605-621, roq_read.c:189-190, marssound.c:1150-1158 (licence: mixed; id limited-use except p_sight.c, which is MIT)
- What it does and why it is clever:
  - **Biased colormaps.** `mov.b` sign-extends, so texels are fetched as signed bytes and every colormap base is biased +128 (+256 for the 16-bit low-res maps). The signed index needs no `extu.b`. RoQ does the same with `cells = cells_u + 128`, and sector compares cast to `int8_t` "to get rid of the extu.w".
  - **Integer part without an arithmetic shift.** Compute `(unsigned)dx >> 16` (one `shlr16`), then `muls.w`, which only reads the low 16 bits as signed. The sign comes back for free.
  - **Cheap constants.** 0xFFFF = `mov #-1; extu.w`; 0x10000 = `mov #1; shll16`; 0xFFFFFF00 = `mov #-128; add r,r`. Constants are pinned in registers with `asm("mov")` so GCC does not reload them.
  - **Cheap address and leaf tests.** `y*320` = `shll8` plus `shlr2` and two adds. A BSP leaf test is `(int16_t)n < 0` instead of `& 0x8000`.
  - **1<<k without a barrel shifter.** `braf` jumps into a chain of seven `shll`, so k costs at most 7 single shifts (reject matrix).
  - **>>16 for free.** `swap.w` gives frac>>16 in every texture loop.
- Key numbers: n/a.
- Target chapter: sh2/isa.md
- Evidence: code only

---

## sh2/pipeline.md

### Column and span inner loops scheduled by hand
- Source: D32XR, sh2_draw.s:15-78 (column), 231-335 (span); sh2_drawlow.s:14-82, 246-465 (licence: id limited-use; header says only "Original code by Chilly Willy")
- What it does and why it is clever:
  - **Unrolling.** Loops are unrolled 2x and enter mid-loop for odd counts (`shlr count; movt; bt/s`). Branch delay slots hold useful work.
  - **Load-use spacing.** Each texel load is separated from its colormap lookup and store by independent ALU ops.
  - **Spans run backwards.** The start fracs are advanced by `step*count` with `dmuls.l`, and pixels are stored with pre-decrement `mov.b r,@-fb`, so the counter doubles as the loop end.
  - **Combined flat index.** The y-mask `(h-1)*h` comes from `mulu.w`, so `spot = ((yfrac>>16) & 63*64) | ((xfrac>>16) & 63)` needs no shift.
  - **NPO2 columns.** The non-power-of-two column drawer replaces the mask with compare-and-subtract wrap (the "tutti-frutti" fix).
- Key numbers: column = 7 instructions per pixel in the loop body; frame pitch is a constant 320.
- Target chapter: sh2/pipeline.md
- Evidence: code only

### Hiding multiplier latency in point-on-side tests
- Source: D32XR, r_local.h:280-311, p_maputl.c:48-83, p_shoot.c:84-118 (licence: id limited-use for r_local.h and p_maputl.c; MIT for p_shoot.c)
- What it does and why it is clever: The side test `dy_node*dx <= dy*dx_node` is split across two asm blocks. The first `muls.w` is issued, `dy` is computed while it completes, then `sts macl` and the second `muls.w` follow. That hides MAC latency, and each product is a 16x16 multiply on integer map units instead of a 32x32 fixed multiply. The RoQ decoder does the same kind of thing for the square of its DPCM delta, using `mulu.w` rather than the `mul.l` GCC would pick ("slightly higher latency").
- Key numbers: node coordinates are int16.
- Target chapter: sh2/pipeline.md
- Evidence: code only

---

## 32x/vdp.md

### Using the back framebuffer's hidden part as scratch RAM
- Source: D32XR, marsnew.c:849-889, r_main.c:878-926, r_data.c:534-540, p_tick.c:546-550, p_setup.c:426 (licence: MIT for marsnew.c; id limited-use for the others)
- What it does and why it is clever: The visible picture uses only 320x224 bytes of each 128 KB framebuffer bank. Everything after line 225 (one blank line is reserved) holds per-frame renderer memory: visplanes and their open[] arrays, segclip openings, viswalls (aliased with vissprites), the sorted lists and both CPUs' column caches. The math LUTs live there too. Banks flip each frame, so the LUTs are rebuilt twice (`initmathtables = 2`). Level load also borrows it for temporary bbox arrays and mapthings.
- Key numbers: 128 KB bank minus 320 x 225 bytes, about 56 KB free.
- Target chapter: 32x/vdp.md
- Evidence: code only

### Overwrite-image writes as hardware transparency
- Source: D32XR, r_data.c:988-991, m_fire.c:367-445 (licence: id limited-use for r_data.c; MIT for m_fire.c)
- What it does and why it is clever: The overwrite alias of the framebuffer drops writes of byte 0. The game uses it twice. Second and later decals are composited through `dst | 0x20000`, so a masked patch overlays the column with no per-pixel test. The menu fire writes its upper rows through the overwrite image, so index 0 lets the title picture show through, then switches to the normal framebuffer for the solid bottom 18 lines.
- Key numbers: overwrite alias = framebuffer + 0x20000.
- Target chapter: 32x/vdp.md
- Evidence: code only

### Line-table tricks: scroll, letterbox, shared margins
- Source: D32XR, marshw.c:112-142, m_fire.c:375-386, marsroq.c:400-436, roq_read.c:114-127 (licence: MIT for marshw, m_fire and marsroq; id limited-use for roq_read)
- What it does and why it is clever:
  - **Blank and letterbox lines.** Unused scanlines all point at one cleared blank line, which also gives the 240p letterbox.
  - **Title reveal.** The title picture is unrolled by rewriting line offsets (`lines[j] = (j-limit)*160 + 0x100`) rather than copying pixels.
  - **RoQ shared margins.** In 32K-colour mode RoQ uses a canvas pitch of `160 + width/2` words (rounded to 16). Line n's black right margin is then exactly line n+1's black left margin, so a centred letterboxed video fits in a bank where full 320-wide 16bpp lines would not.
- Key numbers: RoQ_MAX_CANVAS_SIZE = 288 x 224 words; 256 line-table entries.
- Target chapter: 32x/vdp.md
- Evidence: code only (the shared-margin reading is my inference from the pitch formula)

### Double-width rendering through 16-bit colormaps
- Source: D32XR, r_main.c:249-368, r_data.c:901-934, sh2_drawlow.s:14-82, 353-465, r_phase7.c:158-164, 313-319 (licence: id limited-use)
- What it does and why it is clever: In `lowres` mode the viewport width is halved and every drawer writes 16-bit words. The low-res colormap (`dc_lcolormaps`, from the lump two before COLORMAP, offset 256) holds 16-bit entries, so one lookup returns both bytes of the doubled pixel. The default `detmode_lowres` (when not in full lowres) is a hybrid: walls stay full width but floors and ceilings use the low-res span drawer with `x>>1` and centerX/2. Odd rows use `I_DrawSpanLowSwap`, which `swap.b`s the word; when an entry's two bytes differ this gives a 2x2 checkerboard (I could not check the lump contents).
- Key numbers: viewports 160x90, 224x128, 256x144, 320x180 (fullscreen default); split-screen variants 160x100 to 160x144.
- Target chapter: 32x/vdp.md
- Evidence: code only

### Palette shifts computed instead of stored
- Source: D32XR, r_main.c:611-673, 830-870 (licence: id limited-use)
- What it does and why it is clever: Doom keeps 14 tinted palettes. This port keeps only the base PLAYPALS and builds a tint when it changes: `c' = c + (target - c)·shift/steps`, clamped, from a 14-row table of (r, g, b, shift, steps). The table covers 8 red damage levels, 4 gold bonus levels, green radsuit and blue pause. It recomputes only when the palette index changes.
- Key numbers: saves 14 x 768 bytes of palettes.
- Target chapter: 32x/vdp.md
- Evidence: code only

---

## 32x/pwm.md

### Volume maths sized to land directly in PWM range
- Source: D32XR, sh2_mixer.s:46-102, marssound.c:8-15, 1170-1194 (licence: MIT for the mixer; id limited-use for marssound.c)
- What it does and why it is clever: Per channel, `left = (255-pan)·vol·scale >> 10` and `right = pan·vol·scale >> 10` (vol and scale each up to 64, so up to 1020). An 8-bit sample becomes `(s-128)<<8`, and `(sample·vol)>>16` is then about ±510, the half-range of a 10-bit PWM cycle. The final pass only adds the centre (515) and clamps to [2, 1032]; no division or renormalising.
- Key numbers: 22050 Hz; SAMPLE_MIN 2, MAX 1032, CENTER 515. The RoQ path maps a 16-bit accumulator to PWM with `>>6`.
- Target chapter: 32x/pwm.md
- Evidence: code only

---

## patterns/audio.md

### Packed-stereo resampling mixer (8-bit PCM)
- Source: D32XR, sh2_mixer.s:23-141, marssound.c:1007-1075, 1327-1409 (licence: MIT for the mixer; id limited-use for marssound.c)
- What it does and why it is clever: The mix buffer holds one 32-bit word per stereo frame, left in the high 16 bits and right in the low 16. Both scaled channel contributions are merged into one value and added with a single `add`, half the loads and stores of separate L/R buffers. Sample position is fixed point with 14 fractional bits, `increment = (freq<<14)/22050` capped at 1.0, and the sample index is `pos>>14`, computed as `shlr8, shll2, shlr8` (nearest-neighbour). Loop and end handling is a compare with optional `pos -= loop_length`.
- Key numbers: 316 frames per buffer (about 70 Hz at 22050).
- Target chapter: patterns/audio.md
- Evidence: code only

### IMA ADPCM decoded inside the mixer, with a merged index table
- Source: D32XR, sh2_mixer.s:143-620 (licence: MIT)
- What it does and why it is clever: The decoder emits a new sample only when the integer nibble position changes (`prev_pos`), so upsampling costs no extra decodes. It computes `diff = ((2n+1)·step)>>3` with one `muls.w` and three `shar`s, and clamps to int16. The step-index update and its 0..88 clamp are folded into one 2D byte table indexed `[index*8 + nibble]`, which stores the next index already doubled as a byte offset into step_table. A 2x variant, chosen when the increment is a power of two below 1.0 (11025 into 22050), writes each decoded sample to two output frames.
- Key numbers: step_table 89 words; merged index table 89x8 bytes.
- Target chapter: patterns/audio.md
- Evidence: code only

### Cheap 2D spatialisation at 15 Hz
- Source: D32XR, marssound.c:17-41, 355-522, 1131-1155 (licence: id limited-use)
- What it does and why it is clever:
  - **Distance.** Octagonal approximation `dx+dy-min(dx,dy)/2`.
  - **Volume.** `vol·(1224-d)/1024` between 200 and 1224 units.
  - **Pan.** `128 - 96·sin(angle to listener)`, clamped to [0, 255].
  - **Update rate.** Recomputed only every 1470 samples (about 15 Hz), not per buffer.
  - **Split screen.** Pan comes from the volume difference between the two listeners.
- Key numbers: S_CLIPPING_DIST 1224, S_CLOSE_DIST 200, S_STEREO_SWING 96.
- Target chapter: patterns/audio.md
- Evidence: code only

### Channel stealing and pitch-shifted sound reuse
- Source: D32XR, marssound.c:1229-1325, 524-600 (licence: id limited-use)
- What it does and why it is clever:
  - **Duplicate starts.** A second start of the same sound at the same instant only replaces the first if louder.
  - **Singular sounds** overlay their existing channel.
  - **One sound per source.** A new sound from the same mobj cuts that mobj's old one.
  - **Otherwise** it takes a dead channel, then any channel of lower or equal priority.
  - **Reuse for ROM space.** Missing sounds are mapped to existing samples at other playback rates (e.g. boss pain = imp pain at 5512 Hz, player-pod sounds at 7350 Hz).
- Key numbers: substitute rates 3675, 5512, 7350, 16500 Hz.
- Target chapter: patterns/audio.md
- Evidence: code only

### Double-buffered DMA mixing with idle detection
- Source: D32XR, marssound.c:1077-1124, 1197-1227 (licence: id limited-use)
- What it does and why it is clever: The DMA-complete handler on the slave starts DMA on the buffer it just filled, flips the index, drains the command queue and mixes the next buffer. A counter tracks consecutive buffers with nothing to mix. After more than 2 (both buffers silent and safe to leave playing) it stops clearing and mixing until a sound starts again.
- Key numbers: 2 x 316 longs.
- Target chapter: patterns/audio.md
- Evidence: code only

### RoQ square-law DPCM decode
- Source: D32XR, marsroq.c:87-291 (licence: MIT)
- What it does and why it is clever: Each byte is sign plus 7-bit magnitude m, and the delta is ±m². The accumulator is unsigned 16-bit, biased by 32768. Overflow above 65535 is caught by testing bit 16 with one AND against 0x10000 (`c_hi`) instead of a compare; the value is then clamped and `>>6` gives the 10-bit PWM value. Stereo channels interleave and the initial predictors come from the chunk header.
- Key numbers: 632 samples per buffer (35 Hz); 267 ms mix-ahead.
- Target chapter: patterns/audio.md
- Evidence: code only

---

## patterns/streaming.md

### Resumable LZSS decoder into a ring buffer
- Source: D32XR, liblzss/lzss.c:38-176, liblzss/lzss.h, w_wad.c:72-79, 695-708 (licence: id limited-use; lzss.c has no header)
- What it does and why it is clever:
  - **Format.** A flag byte covers 8 items LSB-first. A literal is one byte. A match is 2 bytes: a 12-bit distance (`b0<<4 | b1>>4`) and a 4-bit length+1. Length 1 is the end marker.
  - **Variant.** Windows larger than 4 KB use a 16-bit distance and 8-bit length.
  - **Streaming.** `lzss_read(chunk)` can stop mid-run and saves its state (run, runlen, runpos, flag bit), so callers pull exactly N bytes at a time: one picture row (DrawJagobjLump) or one VGM read-ahead block.
  - **Copies.** Output wraps by masking, and copies are split at the wrap. `lzss_copy` uses 16-bit moves when source and destination have the same alignment.
  - **Marking.** A compressed lump is flagged by bit 7 of its name's first character.
- Key numbers: LZSS_BUF_SIZE 0x1000.
- Target chapter: patterns/streaming.md
- Evidence: code only

### Streaming compressed VGM music on the 68000
- Source: D32XR, src-md/vgm.c:32-200 (licence: id limited-use; no header)
- What it does and why it is clever: The same LZSS state machine runs on the 68000. A song is decompressed a fixed read-ahead window at a time into a ring buffer for the Z80 player instead of being expanded whole. `lzss_compressed_size` finds where appended PCM data starts. RF5C68 sign-magnitude samples are converted to biased unsigned bytes in place, and loop markers (0xFF) are recorded on the way.
- Key numbers: VGM_READAHEAD / VGM_MAX_READAHEAD (constants in the 68k header).
- Target chapter: patterns/streaming.md
- Evidence: code only

### RoQ vector-quantised video decode
- Source: D32XR, roq_read.c:132-393, 424-471 (licence: id limited-use; header grants "You may freely use this source code" with attribution to Tim Ferguson)
- What it does and why it is clever:
  - **Block coding.** Frames are 16x16 macroblocks split into 8x8 and then 4x4 blocks, each tagged with a 2-bit code. MOT = skip. FCC = copy from the previous frame with a 4-bit x/y motion vector plus the chunk's mean offset. SLD = one 4x4 codebook entry at 2x. CCC = subdivide.
  - **Codebook.** 2x2 YUV cells, converted to RGB555 once per codebook chunk with integer maths (Y·8192, U·2816, V·5888, about 1.44V, 0.34U+0.72V and 1.72U), so the per-frame work is pure 32-bit copies.
  - **Flag reads.** One 16-bit flag word yields eight 2-bit codes through shift-and-mask.
- Key numbers: 256 cells, 256 quad-cells; clamp LUTs of 64 entries offset by 16, already shifted into BGR555 bit positions.
- Target chapter: patterns/streaming.md
- Evidence: code only

### RoQ pipeline: DMA-overlapped frame copy and audio-clock sync
- Source: D32XR, marsroq.c:438-560, 615-672, 711-937 (licence: MIT)
- What it does and why it is clever:
  - **Direct DMA into rings.** CD chunks are DMA'd straight into memory reserved in a video or audio ring buffer (zero copy). `roq_lazybuffer` asks for more data whenever both rings have over 1 KB free, called from busy-wait loops.
  - **Previous-frame copy.** Motion compensation needs the last frame, so after each 16-row band is decoded, SH-2 DMA channel 1 copies that band to `canvascopy` while the CPU decodes the next band.
  - **Audio as the clock.** `sndtime = samples<<16/22050 + 267 ms`; frames whose deadline has passed skip the wait.
  - **Spare memory.** Canvas memory a small video does not need is given to the audio ring.
- Key numbers: video ring 0xE000, audio ring 0x5000 (up to 0xF000); frametics = 16.16 vblanks per frame.
- Target chapter: patterns/streaming.md
- Evidence: code only

### Contiguous-allocation ring buffer (bip buffer) between CPUs
- Source: D32XR, mars_newrb.c:34-281, mars_newrb.h (licence: MIT)
- What it does and why it is clever:
  - **Two-phase API.** `walloc`/`wcommit` and `ralloc`/`rcommit` always hand out contiguous blocks, so DMA and parsers never see a wrap.
  - **Early wrap.** If the tail is too short, the writer records `maxreadpos` (where data ends) and wraps to 0.
  - **Positions.** They run in [0, 2·size) and are reduced only when both read and write pass `size`, which separates full from empty without a counter.
  - **Locking.** A TAS spin lock with a roughly 512-iteration backoff limits bus traffic; the lock can be disabled for single-producer cases.
- Key numbers: header aligned to 16 bytes; 3 cache lines purged per operation.
- Target chapter: patterns/streaming.md
- Evidence: code only

### Jaguar-era decompress-and-convert (historical)
- Source: D32XR, r_phase5.c:37-201 (licence: id limited-use)
- What it does and why it is clever: The original phase 5 decoded LZSS textures into the zone and turned each 8-bit literal into 16-bit CRY colour through `vgatojag[]` in the same pass. The output is twice the input size. A bespoke LRU allocator (`R_Malloc`) purged blocks not locked by the current `framecount`. It is compiled out on the 32X but shows the "stream, decode and convert at once" pattern the MARS cache replaced.
- Key numbers: MINFRAGMENT 64; 8-byte phrase alignment.
- Target chapter: patterns/streaming.md
- Evidence: code only

---

## 32x/communication.md

### Single-producer, single-consumer queue in cache-line units
- Source: D32XR, mars_ringbuf.h:36-215, marssound.c:612-656, 1411-1453 (licence: MIT for the header; id limited-use for marssound.c)
- What it does and why it is clever: The read and write cursors each own a 16-byte-aligned cache line and are only touched through the uncached alias. Payload advances in 8-word (16-byte) steps, so a cache line belongs to one side at a time. The writer gets a cache-through pointer for its payload; the reader purges the payload lines before reading. Writes are refused if the queue is more than `128 - max(wcnt, 64)` words full. The game sends 8-word sound commands to the slave this way without locks.
- Key numbers: 16 lines = 128 words = 256 bytes.
- Target chapter: 32x/communication.md
- Evidence: code only

### TAS spin locks for shared counters
- Source: D32XR, r_phase6.c:328-337, r_phase7.c:257-291, f_wipe.c:30-58, p_sight.c:387-399 (licence: id limited-use; p_sight.c is MIT)
- What it does and why it is clever: Every shared work cursor is guarded by a one-byte lock taken with `tas.b`: next seg, next visplane (kept in COMM6), next melt column, next sight mobj. GCC's `atomic_flag_test_and_set` emits it under `-mtas`; f_wipe uses inline `tas.b`/`movt`. The lock covers only a read-increment-write, and the unlock is a plain byte store.
- Key numbers: lock = 1 byte.
- Target chapter: 32x/communication.md
- Evidence: code only

---

## patterns/60fps.md

### Variable-timestep game loop with a 15 Hz tic
- Source: D32XR, d_main.c:376-475, marsnew.c:1057-1124, p_user.c:30-31, 153, p_base.c:195, p_tick.c:357-405 (licence: id limited-use except marsnew.c, which is MIT)
- What it does and why it is clever: `vblsinframe` (vblanks the last frame took, capped at 8) scales player momentum and gravity every frame, so control responsiveness follows the frame rate. Monster thinkers, sight checks and specials run only when `gamevbls/4` advances a 15 Hz gametic. I_Update busy-waits until at least `ticsperframe` (2 to 4) vblanks have passed: 30 fps cap at 2, forced to 3 at full width in P_Update, and 4 during demos to keep them deterministic.
- Key numbers: TICRATE 15; TICVBLS 4; MIN/MAXTICSPERFRAME 2/4.
- Target chapter: patterns/60fps.md
- Evidence: code only

---

## howto/profiling.md

### Per-phase FRT timing and diagnostic draw modes
- Source: D32XR, r_main.c:1124-1183, marsnew.c:960-1025, marshw.c:86-93, 253, r_cache.c:241-247 (licence: id limited-use for r_main; MIT for the rest)
- What it does and why it is clever: The renderer timestamps BSP, prep, segs, planes, sprites and total with the free-running timer into 4-entry ring arrays; the overlay averages them with `>>2`. Ticks become milliseconds through a 16.16 reciprocal computed once (`4096·1000/clock·65536`), so no division. Debug modes (cycled with MODE in the options menu) cover:
  - FPS only, or all counters plus wall, plane and sprite counts;
  - texture cache disabled;
  - a no-op drawer, so geometry cost can be measured with no fill;
  - each texture-cache entry painted a flat colour from its id, to show residency on screen.
- Key numbers: 10 overlay lines.
- Target chapter: howto/profiling.md
- Evidence: code only

---

## NEW: Fixed-point maths

### Angles as 32-bit binary fractions of a turn, and fine-angle indices
- Source: D32XR, doomdef.h:136-171, r_local.h:24-35, 353-355 (licence: id limited-use)
- What it does and why it is clever:
  - **Angles.** `angle_t` is unsigned 32-bit with 2^32 = 360° (ANG90 = 0x40000000), so wraparound is free and differences are just subtraction.
  - **Fine angles.** Tables are indexed by `angle >> 19`, giving 8192 fine angles; FIELDOFVIEW = 2048 fine angles (90°); the sky uses `>>22`.
  - **Other formats.** Coordinates are 16.16 `fixed_t`. Wall heights in viswalls are 12.4 int16 (HEIGHTFRACBITS 4). Map vertices and nodes are int16 whole units.
- Key numbers: FINEANGLES 8192; SLOPERANGE 2048 (11 bits); DBITS 5.
- Target chapter: NEW: Fixed-point maths
- Evidence: code only

### Quarter-wave sine and half-period tangent tables
- Source: D32XR, tables.c:2067-2587 (data), 2589-2625 (accessors) (licence: id limited-use)
- What it does and why it is clever: Only sin over [0°, 90°) is stored, as 2048 unsigned 16-bit values (1.0 ≈ 65535). `finesine` takes the quadrant q = angle/2048 and looks up a pointer offset `{0, +4096, -4096, +8192}` words. For odd quadrants it indexes with `~angle`, which equals `-angle-1` and mirrors the quarter, and it negates for q ≥ 2. One table read with no branchy symmetry code. `finetangent` stores 2048 entries and uses `tan(θ) = -tan(π-θ)` through `~angle`.
- Key numbers: sine 4 KB instead of 40 KB (10240 x 4 bytes); tangent 8 KB instead of 16 KB; tantoangle 2049 entries.
- Target chapter: NEW: Fixed-point maths
- Evidence: code only

### R_PointToAngle by octant folding and an arctangent table
- Source: D32XR, r_main.c:96-197 (licence: id limited-use)
- What it does and why it is clever: The vector is folded into the first octant (0 ≤ y ≤ x) while recording a base angle and a sign n per octant. The result is `base + n·tantoangle[min(2048, (num<<3)/(den>>8))]`; the quotient is the slope scaled to 11 bits, from the hardware divider. A denominator below 2 short-circuits to the 45° entry.
- Key numbers: 8 octants; one 32/32 divide.
- Target chapter: NEW: Fixed-point maths
- Evidence: code only

### Distance without square roots, and an integer square root where needed
- Source: D32XR, r_phase2.c:23-42, 92-128; p_maputl.c:29-36 (licence: id limited-use)
- What it does and why it is clever:
  - **R_PointToDist.** Order the axes so dy ≤ dx, look up θ = atan(dy/dx), return `dx / cos θ`: one divide each way, no sqrt.
  - **P_AproxDistance.** `dx+dy - min/2`, an octagonal norm.
  - **P_SegOffset.** Because segs no longer store their offset along the line, it uses a 16-step bitwise square root: try each bit from 0x8000 down and keep it if g² ≤ n.
- Key numbers: isqrt = 16 iterations.
- Target chapter: NEW: Fixed-point maths
- Evidence: code only

---

## NEW: BSP and portal rendering

### Front-to-back BSP walk with a bounding-box culling table
- Source: D32XR, r_phase1.c:51-65, 121-181, 686-741 (licence: id limited-use)
- What it does and why it is clever: At each node the near child is drawn first, and the far child is visited only if its bbox might still be visible. R_CheckBBox picks the box's 3x3 position relative to the viewer with comparisons; `checkcoord[12][4]` gives the two silhouette corners (inside the box returns visible). Their angles become screen columns. If the solid-seg list already covers that column span, the whole subtree is skipped.
- Key numbers: 12 x 4 corner table; MAXSEGS 32 clip ranges.
- Target chapter: NEW: BSP and portal rendering
- Evidence: code only

### Child bounding boxes quantised to 4 bits
- Source: D32XR, p_setup.c:316-381, r_phase1.c:670-684 (licence: id limited-use)
- What it does and why it is clever: Each child bbox is stored as four 4-bit counts of 1/16ths of the parent box, shrinking inward from each side, in one uint16. The parent is decoded recursively from the world bbox during traversal: `min + (len·n)>>4`. Encoding rounds outward, so the decoded box always contains the real one; culling stays conservative but node_t shrinks from 8 int16 of bboxes to 2 uint16.
- Key numbers: 16 bits per child bbox instead of 64.
- Target chapter: NEW: BSP and portal rendering
- Evidence: code only

### Solid-seg clip ranges for occlusion
- Source: D32XR, r_phase1.c:447-545, 723-741 (licence: id limited-use)
- What it does and why it is clever: `solidsegs[]` is a sorted list of fully occluded column ranges, with sentinels at [-2,-1] and [width, width+1]. A new seg is split into the visible gaps; each gap becomes a viswall. If the seg is solid (one-sided, or a closed door), its range is merged into the list. Ranges are packed into 32-bit words so insert and delete shift whole longs. Once the list covers the screen, every further bbox check fails and traversal ends.
- Key numbers: cliprange = 2 x int16, 4-byte aligned.
- Target chapter: NEW: BSP and portal rendering
- Evidence: code only

### Clipping to view edges through angle-to-column tables
- Source: D32XR, r_phase1.c:69-115, r_data.c:526-593 (licence: id limited-use)
- What it does and why it is clever:
  - **Clipping.** A seg's endpoint angles are clipped to ±clipangle with unsigned wraparound tricks (`tspan > 2·clipangle`), and segs spanning 180° or more are rejected.
  - **Mapping.** Angles become columns through `viewangletox[(angle+90°)>>19]`. That table is built from `focal = centerX / tan(FOV/2)`, `x = centerX - tan(a)·focal`, rounded up.
  - **Inverse.** `xtoviewangle[x]` holds the smallest angle mapping to each column (16-bit, angle>>16).
- Key numbers: viewangletox 4096 entries; xtoviewangle width+1.
- Target chapter: NEW: BSP and portal rendering
- Evidence: code only

### Endpoint angle cache and seg ordering
- Source: D32XR, r_phase1.c:550-585, p_setup.c:870-905 (licence: id limited-use)
- What it does and why it is clever: R_AddLine remembers the last seg's two vertex indices and angles, and reuses them when the next seg shares a vertex, which saves R_PointToAngle and its divide. At load, segs inside each subsector are insertion-sorted by linedef so segs sharing endpoints sit next to each other.
- Key numbers: 2-entry cache.
- Target chapter: NEW: BSP and portal rendering
- Evidence: code only

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

### Packed 8:8 clip bounds and visplane marking
- Source: D32XR, r_phase2.c:235-356, r_main.c:965-990, r_local.h:366-371 (licence: id limited-use)
- What it does and why it is clever: Per column, the ceiling and floor clip are packed as `top<<8 | bottom` in a uint16. The array is initialised two entries per 32-bit store. Each seg column computes projected heights with one FixedMul each, clamps and writes the new bounds. A seg's private bounds array is a biased pointer (`lastsegclip - start`), so it is indexed by absolute x without a subtraction. Visplane `open[]` uses 0xFF00 as "unset", tested as `(int8_t)(v>>8) == -1`.
- Key numbers: MAXOPENINGS = 320·18 uint16.
- Target chapter: NEW: BSP and portal rendering
- Evidence: code only

### Hashed visplane lookup
- Source: D32XR, r_main.c:962-1036 (licence: id limited-use)
- What it does and why it is clever: Planes are found through a 32-bucket chained hash on `((height>>8) + light) ^ flat`. A plane is reused only if its open[] slot at the start column is still unmarked, so it never gets two spans in one column. Otherwise a new plane is allocated, with plane 0 as the overflow dummy. The bucket array lives on the slave's stack because only the slave marks planes.
- Key numbers: NUM_VISPLANES_BUCKETS 32; flatandlight = light<<16 | flat.
- Target chapter: NEW: BSP and portal rendering
- Evidence: code only

### Turning visplane columns into horizontal spans
- Source: D32XR, r_phase7.c:184-255 (licence: id limited-use)
- What it does and why it is clever: Walking adjacent columns' (top, bottom) pairs, rows present in the old column but not the new end a span (emitted from `spanstart[row]` to x-1), and rows newly covered record `spanstart[row] = x`. Sentinels (OPENMARK) at minx-1 and maxx+1 flush everything. Each pixel of the plane is visited once and output is row-coherent, which the span drawer needs.
- Key numbers: spanstart[180] on the stack.
- Target chapter: NEW: BSP and portal rendering
- Evidence: code only

---

## NEW: Texture-mapped walls and floors

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

### Sky with fixed vertical mapping
- Source: D32XR, r_phase6.c:266-326 (licence: id limited-use)
- What it does and why it is clever: The sky column is `(viewangle + xtoviewangle[x]) >> 22 & 0xFF`, so it depends only on angle and wraps 4 times per turn. Vertically it uses constants, `frac = top·72816`, `step = 65536+7281` (about 1.111 texels per pixel), independent of distance. Each column is one direct drawcol call. 4bpp skies use the 4bpp drawer and a 64-byte pitch.
- Key numbers: sky texture 128 tall.
- Target chapter: NEW: Texture-mapped walls and floors
- Evidence: code only

### 16-colour textures with their own colormaps
- Source: D32XR, r_main.c:430-436, r_phase6.c:381-392, sh2_draw4b.s:14-100, r_phase9.c:218-242 (licence: id limited-use)
- What it does and why it is clever: A texture whose header has depth 2 and flag 0x8 stores 4-bit texels plus its own 33x16 lighting table at the end of the lump. The 4bpp drawer turns `light>>3` into an index into that table, uses the shifted-out bit of `shlr` (T flag) to choose the nibble, and the nibbles are pre-swapped in the data to save address maths. Half-size textures in ROM; expanded to 8bpp when cached.
- Key numbers: 33·16·2 bytes of tables per texture.
- Target chapter: NEW: Texture-mapped walls and floors
- Evidence: code only

### "Potato" solid-colour floors
- Source: D32XR, r_phase7.c:167-179, 329; marsdraw.c:505-585; r_phase9.c:98 (licence: id limited-use for r_phase files; MIT for marsdraw.c)
- What it does and why it is clever: The potato plane mapper skips distance, step and light maths. Each span is filled with one lit colour: texel 513 of the flat (row 8, col 1) through the plane's constant colormap. The fill uses 16-bit stores, 2 pixels per write, with byte fix-ups at odd edges. Flats are also left out of the texture-cache budget in this mode.
- Key numbers: 1 lookup per span.
- Target chapter: NEW: Texture-mapped walls and floors
- Evidence: code only

### Spectre fuzz effect
- Source: D32XR, r_main.c:31-42, r_data.c:613-617, sh2_draw.s:164-223 (licence: id limited-use)
- What it does and why it is clever: A 64-entry ±1 table is pre-scaled to ±320 (one framebuffer row). Each pixel reads the framebuffer pixel above or below and darkens it through colormap 12. The table position persists per CPU in TLS, and the first and last rows are skipped to stay in bounds.
- Key numbers: FUZZTABLE 64.
- Target chapter: NEW: Texture-mapped walls and floors
- Evidence: code only

### Optional mipmaps for walls and flats
- Source: D32XR, r_data.c:244-321, r_main.c:416-495, r_phase6.c:110-121 (licence: id limited-use)
- What it does and why it is clever: Mip chains are detected by whether the lump is long enough for halved sizes after level 0. A texture with decals is limited to its decals' smallest mip count. When drawing, frac, step and column are shifted per level. Each wall records its min and max mip used so phase 9 caches only the levels actually needed. Compiled out by default.
- Key numbers: MIPLEVELS build option.
- Target chapter: NEW: Texture-mapped walls and floors
- Evidence: code only

---

## NEW: Software 3D on the SH-2

### Sprite projection, rotation pick and culling
- Source: D32XR, r_phase3.c:17-192 (licence: id limited-use)
- What it does and why it is clever:
  - **View space.** Translate into view space with 4 FixedMuls.
  - **Culling.** Reject depth below MINZ (4 units). Reject |tx| > 4·tz before any per-frame lookup. Cull vertically with `gzt·xscale` against centerY.
  - **Scale.** `xscale = centerX/tz`; yscale = xscale·stretch for aspect.
  - **Rotation.** `rot = (angle_to_thing - thing_angle + 9·ANG45/2) >> 29` picks one of 8 views.
  - **Flags in the lump number.** Flip and single-sided status ride in its top bits, so there is no separate frame table.
- Key numbers: SL_SINGLESIDED 0x8000, SL_FLIPPED 0x4000.
- Target chapter: NEW: Software 3D on the SH-2
- Evidence: code only

### Sprite sort key and insertion sort
- Source: D32XR, r_phase8.c:533-590, d_main.c:169-183 (licence: id limited-use)
- What it does and why it is clever: Each sprite gets the int key `(xscale<<7) + index`, depth in the high bits and slot in the low 7. A plain insertion sort on these ints orders sprites back to front; the low bits recover the sprite with `& 0x7F`. The same D_isort sorts visplanes. Insertion sort suits the small and often nearly sorted lists.
- Key numbers: 7-bit index field (128 sprites) with MAXVISSPRITES 165, so a mismatch is possible.
- Target chapter: NEW: Software 3D on the SH-2
- Evidence: code only

### Clipping sprites against wall silhouettes and interleaving masked walls
- Source: D32XR, r_phase8.c:257-395, 21-143, 397-465 (licence: id limited-use)
- What it does and why it is clever:
  - **Clip list.** Each CPU builds the list of walls that cast silhouettes or have masked mid-textures. For each sprite it walks them; a wall is behind the sprite if both end scales are smaller, or if a cross-product side test says so.
  - **Walls behind.** Their masked mid-texture columns are drawn there and then, and each column is marked OPENMARK so it is drawn once.
  - **Walls in front.** They narrow the sprite's top and bottom openings: byte-wise for top-only or bottom-only silhouettes, both bytes for both, the whole column for solid.
  - **Masked mid-textures.** Phase 6 stored `light|colnum` per column for them.
- Key numbers: silhouette = actionbits / AC_TOPSIL (1, 2, 3 or ≥4 = solid).
- Target chapter: NEW: Software 3D on the SH-2
- Evidence: code only

### Drawing masked patch columns
- Source: D32XR, r_phase8.c:145-252 (licence: id limited-use)
- What it does and why it is clever: Sprites are Doom posts (topdelta, length, data offset) per column. Each post's screen top is rounded up with `+0xFFFF` (built in two instructions) and clipped to the opening; frac starts at `(clip - top)·iscale`. Columns are stepped by `xiscale`, negative when flipped. Shadow sprites switch to the fuzz drawer through a negative colormap value.
- Key numbers: posts end at 0xFF.
- Target chapter: NEW: Software 3D on the SH-2
- Evidence: code only

### Viewport aspect stretch and weapon placement
- Source: D32XR, r_main.c:232-305, r_phase3.c:197-292 (licence: id limited-use)
- What it does and why it is clever: `stretch = (16·h/180·22)/w` in 16.16 (28 instead of 22 for anamorphic). It scales wall heights through `stretchX = stretch·centerX` and sprites through yscale, so any viewport keeps Doom's 2.2 pixel aspect. Weapon sprites use a fixed x scale (halved in low-res) and a vertical offset chosen per viewport height.
- Key numbers: 4 viewport presets x 2 (single or split screen).
- Target chapter: NEW: Software 3D on the SH-2
- Evidence: code only

---

## NEW: Memory management on a 256 KB machine

### Zone allocator with rover and coalescing
- Source: D32XR, z_zone.c:33-341, doomdef.h:678-698 (licence: id limited-use)
- What it does and why it is clever: The heap is a doubly linked list of adjacent blocks (no gaps, never two free blocks side by side). Allocation is next-fit from a rover and splits off a tail only if more than 64 bytes would be left. Free merges with both neighbours. Links are 16-bit short pointers. The zone is a parameter, so the texture cache runs its own zone carved out of the main one. Helpers report largest free block and iterate blocks for cache ageing.
- Key numbers: MINFRAGMENT 64; 4-byte alignment; block header = size + tag + id + 2 short links.
- Target chapter: NEW: Memory management on a 256 KB machine
- Evidence: code only

### 16-bit short pointers
- Source: D32XR, doomdef.h:51-90 (licence: id limited-use)
- What it does and why it is clever: An SPTR is `(ptr - 0x06000000) >> 2` in a uint16. That covers all 256 KB of SDRAM for 4-byte-aligned objects. It is used for mobj list, sector and blockmap links and zone block links, halving those fields.
- Key numbers: 65536 x 4 = 256 KB reach.
- Target chapter: NEW: Memory management on a 256 KB machine
- Evidence: code only

### Packed map structures
- Source: D32XR, r_local.h:80-149, 131-135; p_setup.c:114-159, 624-660 (licence: id limited-use)
- What it does and why it is clever:
  - **seg_t.** 6 bytes: `linedef<<1 | side`, v1, v2. The offset field is dropped and recomputed with an integer square root.
  - **side_t.** Textures as uint8 indices; a 12-bit x offset with the top 4 bits of a 12-bit row offset tucked into the same int16, recovered with `<<4 >>4` sign extension.
  - **Small fields.** VINT is short on MARS; sector light and special are bytes.
  - **Tags.** Moved out of the structures into small hash tables.
- Key numbers: seg 6 bytes; side 8 bytes; node 16 bytes.
- Target chapter: NEW: Memory management on a 256 KB machine
- Evidence: code only

### viswall and vissprite sharing one array
- Source: D32XR, r_local.h:516-586, r_main.c:898-909 (licence: id limited-use)
- What it does and why it is clever: `vd->vissprites = vd->viswalls`. Sprite records are written over the leading "early prep" fields of each viswall (centerangle to ceilingnewheight), which are dead after phase 7. The fields sprite clipping still needs (start, stop, scales, actionbits, clipbounds, vertices) sit after them. The comment requires that section to be big enough for a vissprite_t.
- Key numbers: MAXVISSPRITES = MAXWALLCMDS = 165.
- Target chapter: NEW: Memory management on a 256 KB machine
- Evidence: code only

### Mobj pools, truncated static objects and limbo
- Source: D32XR, p_mobj.c:60-95, 250-290, 354-375; doomdef.h:254-313; p_base.c:290-322 (licence: id limited-use; p_base.c is MIT)
- What it does and why it is clever: Objects that never move or think (MF_STATIC) are allocated only up to `offsetof(mobj_t, angle)`, a prefix of the full struct. Level load pre-allocates both kinds in bulk, plus 40 spare for puffs and missiles. Removed mobjs go to a limbo list and are recycled only at the end of the tic, so pointers held during the tic stay valid.
- Key numbers: +40 pre-spawned mobjs.
- Target chapter: NEW: Memory management on a 256 KB machine
- Evidence: code only

### Hashed tag tables
- Source: D32XR, p_maputl.c:520-617, p_setup.c:287-303, 596-612 (licence: id limited-use)
- What it does and why it is clever: Line and sector tags live in open-addressed `(object, tag)` pair tables instead of a field on every line. The table is rounded up to a multiple of 16 and probing starts at row `(obj % 16)·(n/16)`. Iterating by tag is a linear scan with a resumable cursor.
- Key numbers: LINETAGS_HASH_SIZE 16.
- Target chapter: NEW: Memory management on a 256 KB machine
- Evidence: code only

---

## NEW: Collision, physics and line-of-sight

### Blockmap iteration with a per-CPU validcount
- Source: D32XR, p_maputl.c:254-484, p_setup.c:724-748 (licence: id limited-use)
- What it does and why it is clever: Lines are bucketed in 128-unit cells. A line seen in several cells is checked once by stamping `validcount[line] = vc`, using the current CPU's array from TLS. The thing chains (blocklinks) use 256-unit cells (`blocklinksadjust`), which cuts that array to a quarter. Thing queries halve their cell range to match.
- Key numbers: MAPBLOCKUNITS 128; MAXRADIUS 32.
- Target chapter: NEW: Collision, physics and line-of-sight
- Evidence: code only

### P_TryMove, line crossing and sub-stepped movement
- Source: D32XR, p_move.c:44-334, p_maputl.c:88-133, p_base.c:74-133 (licence: MIT for p_move and p_base; id limited-use for p_maputl)
- What it does and why it is clever:
  - **Position check.** Gathers the tightest floor, ceiling and drop-off from every crossed line and checks things in a box widened by MAXRADIUS.
  - **Box against line.** P_BoxCrossLine tests one box diagonal, picked by the line slope's sign, against the line with two cross products.
  - **Sub-steps.** Big moves are halved until under MAXMOVE.
  - **Move rules.** A move needs room for the object's height, a step up of at most 24 units, and (for non-floaters) a drop-off of at most 24.
  - **Re-entrancy.** All state is in a stack-allocated work struct, so it can run on either CPU.
- Key numbers: step height 24; FRICTION 0xD240 (≈0.82); STOPSPEED 0x1000.
- Target chapter: NEW: Collision, physics and line-of-sight
- Evidence: code only

### Player wall sliding
- Source: D32XR, p_slide.c:61-160, 162-334, 488-546 (licence: MIT)
- What it does and why it is clever:
  - **Contact.** The player is a 23-unit circle. Each blocking line's unit normal (axis-aligned shortcuts, otherwise from R_PointToAngle and sine) gives signed distances, and the move fraction is `d1/(d1-d2)` measured from the circle's contact point.
  - **Slide.** The move is cut to the smallest blocking fraction, and the leftover is projected onto the blocking wall's direction.
  - **Limits.** Up to 3 bumps; fractions under 1/16 are treated as solid.
  - **Specials.** Lines crossed by the final move are found separately with segment-segment side tests.
- Key numbers: CLIPRADIUS 23; ON_SIDE_EPSILON 1/128; 3 iterations.
- Target chapter: NEW: Collision, physics and line-of-sight
- Evidence: code only

### Reject matrix stored as a triangle
- Source: D32XR, p_setup.c:671-714, p_sight.c:277-342 (licence: id limited-use for p_setup; MIT for p_sight)
- What it does and why it is clever: The reject table is assumed symmetric, so only the upper triangle is kept. Bit index = `s1·n + s2 - s1(s1+1)/2` with s1 ≤ s2, about half the original n² bits. The bit mask is built with a computed `braf` into a run of `shll` (see sh2/isa.md). Things in the same subsector skip the test.
- Key numbers: n(n+1)/2 bits.
- Target chapter: NEW: Collision, physics and line-of-sight
- Evidence: code only

### Line-of-sight by BSP walk with narrowing slopes
- Source: D32XR, p_sight.c:61-272, 347-365 (licence: MIT)
- What it does and why it is clever:
  - **Traversal.** The sight line is pushed through the BSP; only nodes it crosses are split, and only subsectors it passes through are visited, with each linedef tested once.
  - **Openings.** Each two-sided line narrows `topslope` and `bottomslope` (from eye height, 3/4 of the looker's height) by the window opening divided by the intercept fraction. Sight fails when they meet.
  - **Integer maths.** Uses int16 integer map units throughout.
  - **No degenerate cases.** Endpoints are snapped to odd integers (`(x & ~0x1FFFF) | 0x10000`) so the trace never passes exactly through a vertex.
- Key numbers: int16 divlines; one 64/32 divide per intercept.
- Target chapter: NEW: Collision, physics and line-of-sight
- Evidence: code only

### Hitscan by BSP order with a one-intercept delay
- Source: D32XR, p_shoot.c:297-523 (licence: MIT)
- What it does and why it is clever:
  - **Ordering.** Front-to-back BSP order replaces sorting all intercepts. Within a subsector, a one-element buffer (`old_intercept`) swaps each new hit with the held one so the nearer of the two is processed first.
  - **Thing tests.** Things are hit-tested against one corner-to-corner diagonal, chosen by the trace direction's sign.
  - **Bullet puff.** The first node that split the trace is remembered so the puff's subsector lookup starts deeper in the tree. The wall impact point is pulled back 4 units.
- Key numbers: aim slopes ±100/160.
- Target chapter: NEW: Collision, physics and line-of-sight
- Evidence: code only

### Deferred side-effects ("latecall")
- Source: D32XR, p_base.c:96-118, 290-322 (licence: MIT)
- What it does and why it is clever: Collisions found while moving (skull slam, missile hit, explosion, removal) are not resolved straight away. They are recorded in a 4-bit `latecall` field plus a short pointer, and applied in a second pass after all thinkers have run. Thinkers never change the list they are iterating, which keeps the base pass simple and lets it run alongside the slave's sight checks.
- Key numbers: 4-bit latecall code.
- Target chapter: NEW: Collision, physics and line-of-sight
- Evidence: code only

---

## NEW: 2D effects and transitions

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
