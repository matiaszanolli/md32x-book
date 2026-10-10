# Harvested techniques: sh2/pipeline.md

Target: `sh2/pipeline.md`. 5 entries. Raw reports and source caveats: [../raw/](../raw/) (paths relative to by-chapter/).

Evidence and licence notes are per entry. Describe in the book's own words; never copy code.

<!-- from D32XR -->
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

<!-- from D32XR -->
### Hiding multiplier latency in point-on-side tests
- Source: D32XR, r_local.h:280-311, p_maputl.c:48-83, p_shoot.c:84-118 (licence: id limited-use for r_local.h and p_maputl.c; MIT for p_shoot.c)
- What it does and why it is clever: The side test `dy_node*dx <= dy*dx_node` is split across two asm blocks. The first `muls.w` is issued, `dy` is computed while it completes, then `sts macl` and the second `muls.w` follow. That hides MAC latency, and each product is a 16x16 multiply on integer map units instead of a 32x32 fixed multiply. The RoQ decoder does the same kind of thing for the square of its DPCM delta, using `mulu.w` rather than the `mul.l` GCC would pick ("slightly higher latency").
- Key numbers: node coordinates are int16.
- Target chapter: sh2/pipeline.md
- Evidence: code only

---

<!-- from VRD/AU/MARSDEV -->
### Load-ahead to hide load-use stalls
- Source: MARSDEV, sh_src/mars_start.s:690-713
- What it does and why it is clever: `word_8byte_copy` issues four loads, then four stores. Each load's result is not used by the next instruction, so the pipeline's load-use stall is filled with useful work; the remaining gaps are commented as "wasted cycle". The loop decrement (`dt`) is placed early.
- Key numbers: 8 bytes per iteration.
- Target chapter: sh2/pipeline.md
- Evidence: code only

<!-- from VRD/AU/MARSDEV -->
### Call overhead budgeting
- Source: VRD-NOTES, analysis/POLYGON_TRANSFORMATION_ANALYSIS.md:245-290
- What it does and why it is clever: BSR+RTS plus delay slots cost about 6 cycles. An indirect `JSR @R14` through a context callback costs 5-8. At about 3,200 calls per frame that is about 19,200 cycles (5%), which justified inlining the hot leaf.
- Key numbers: as stated.
- Target chapter: sh2/pipeline.md
- Evidence: code only (estimates), later confirmed by S-6 profiling

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


## Verification note: where d32xr's column loop sits (9 October 2026)

The book states the result only: at commit `957d3a8`, `do_col_loop` ends up at 16n + 10. Why that does not depend on the rest of the build:

- `sh2_draw.s` puts its code in `.sdata` with `.align 4` (16 bytes; `sh-elf-objdump -h` on the object shows `2**4`). Assembled with GNU as 2.47, `do_col_loop` is at offset `0x3A` (`sh-elf-nm`).
- A linker places each input section on its own alignment, so the offset mod 16 survives any link order. `--sort-section=alignment` in the Makefile reorders sections, it does not misalign them. `mars-ssf.ld` puts `.sdata` in `.data`, with VMA `0x06000000` (SDRAM).
- The Makefile expects an older toolchain (`/opt/toolchains/sega`, GCC 4.6.2 libraries). The assembler version cannot move the label: SH-2 instructions are all 2 bytes, there is no relaxation, the only padding before the label is `.p2alignw 1` (2-byte alignment, a no-op here), and the one literal the routine loads (`draw_width`) is at the end of the file (offset `0x1B4`).
- Not done: a full build of the game. Nothing in `sh2_draw.s` changed between `957d3a8` and `55bf94b` (5 October 2026).
