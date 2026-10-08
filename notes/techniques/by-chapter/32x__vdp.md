# Harvested techniques: 32x/vdp.md

Target: `32x/vdp.md`. 19 entries. Raw reports and source caveats: [../raw/](../raw/) (paths relative to by-chapter/).

Evidence and licence notes are per entry. Describe in the book's own words; never copy code.

<!-- from S32X-SKILL -->
### Line-doubling through the per-line table
- Source: S32X-SKILL, references/optimization.md:361-364; references/architecture.md:47-50
- What it does and why it is clever: Render 112 rows and point two display lines at each row in the framebuffer line table, so the VDP doubles vertically for free.
- Key numbers: About 40% frame slack. Only worth it if that crosses a vblank boundary.
- Target chapter: 32x/vdp.md
- Evidence: Racer log.

<!-- from S32X-SKILL -->
### The palette is the top silent black-screen cause
- Source: S32X-SKILL, references/architecture.md:60-64; references/testing.md:276-281
- What it does and why it is clever: In 8bpp mode an unseeded CRAM maps every index to black. Seed before the first flip. Diagnostic: if `GFX_Clear(C_SKY)` comes out pure (0,0,0), the palette never landed or the CPU hung first; it is not a geometry problem.
- Key numbers: —
- Target chapter: 32x/vdp.md
- Evidence: Zepton black-screen ladder.

<!-- from S32X-SKILL -->
### CRAM word format
- Source: S32X-SKILL, references/testing.md:417-421
- What it does and why it is clever: `0x8000 | (B<<10) | (G<<5) | R`. Swapping R and B turns sky red. The skill says bit 15 clear = transparent (see problem 7).
- Key numbers: RGB555 + bit 15.
- Target chapter: 32x/vdp.md
- Evidence: Black-screen catalogue.

<!-- from S32X-SKILL -->
### Mode mis-set gives two half-width copies; re-assert every flip
- Source: S32X-SKILL, references/testing.md:422-429
- What it does and why it is clever: Left in direct-colour mode, each row consumes 640 bytes instead of 320, giving two half-width images with indices read as RGB555. Write every DISPMODE field explicitly and re-assert on each flip. Both buffers need a valid line table at init.
- Key numbers: 320 vs 640 bytes per row.
- Target chapter: 32x/vdp.md
- Evidence: racing-circuit-32x.

<!-- from S32X-SKILL -->
### Full-CRAM swaps for flashes and day/night
- Source: S32X-SKILL, references/software-3d.md:210-211; references/examples.md:105-106
- What it does and why it is clever: Uploading a reddened or whitened palette gives a full-screen damage or heal flash in one write with no redraw. Shifting the palette does day/night the same way.
- Key numbers: 512 bytes per CRAM upload.
- Target chapter: 32x/vdp.md
- Evidence: noudar, city builder.

---

<!-- from D32XR -->
### Using the back framebuffer's hidden part as scratch RAM
- Source: D32XR, marsnew.c:849-889, r_main.c:878-926, r_data.c:534-540, p_tick.c:546-550, p_setup.c:426 (licence: MIT for marsnew.c; id limited-use for the others)
- What it does and why it is clever: The visible picture uses only 320x224 bytes of each 128 KB framebuffer bank. Everything after line 225 (one blank line is reserved) holds per-frame renderer memory: visplanes and their open[] arrays, segclip openings, viswalls (aliased with vissprites), the sorted lists and both CPUs' column caches. The math LUTs live there too. Banks flip each frame, so the LUTs are rebuilt twice (`initmathtables = 2`). Level load also borrows it for temporary bbox arrays and mapthings.
- Key numbers: 128 KB bank minus 320 x 225 bytes, about 56 KB free.
- Target chapter: 32x/vdp.md
- Evidence: code only

<!-- from D32XR -->
### Overwrite-image writes as hardware transparency
- Source: D32XR, r_data.c:988-991, m_fire.c:367-445 (licence: id limited-use for r_data.c; MIT for m_fire.c)
- What it does and why it is clever: The overwrite alias of the framebuffer drops writes of byte 0. The game uses it twice. Second and later decals are composited through `dst | 0x20000`, so a masked patch overlays the column with no per-pixel test. The menu fire writes its upper rows through the overwrite image, so index 0 lets the title picture show through, then switches to the normal framebuffer for the solid bottom 18 lines.
- Key numbers: overwrite alias = framebuffer + 0x20000.
- Target chapter: 32x/vdp.md
- Evidence: code only

<!-- from D32XR -->
### Line-table tricks: scroll, letterbox, shared margins
- Source: D32XR, marshw.c:112-142, m_fire.c:375-386, marsroq.c:400-436, roq_read.c:114-127 (licence: MIT for marshw, m_fire and marsroq; id limited-use for roq_read)
- What it does and why it is clever:
  - **Blank and letterbox lines.** Unused scanlines all point at one cleared blank line, which also gives the 240p letterbox.
  - **Title reveal.** The title picture is unrolled by rewriting line offsets (`lines[j] = (j-limit)*160 + 0x100`) rather than copying pixels.
  - **RoQ shared margins.** In 32K-colour mode RoQ uses a canvas pitch of `160 + width/2` words (rounded to 16). Line n's black right margin is then exactly line n+1's black left margin, so a centred letterboxed video fits in a bank where full 320-wide 16bpp lines would not.
- Key numbers: RoQ_MAX_CANVAS_SIZE = 288 x 224 words; 256 line-table entries.
- Target chapter: 32x/vdp.md
- Evidence: code only (the shared-margin reading is my inference from the pitch formula)

<!-- from D32XR -->
### Double-width rendering through 16-bit colormaps
- Source: D32XR, r_main.c:249-368, r_data.c:901-934, sh2_drawlow.s:14-82, 353-465, r_phase7.c:158-164, 313-319 (licence: id limited-use)
- What it does and why it is clever: In `lowres` mode the viewport width is halved and every drawer writes 16-bit words. The low-res colormap (`dc_lcolormaps`, from the lump two before COLORMAP, offset 256) holds 16-bit entries, so one lookup returns both bytes of the doubled pixel. The default `detmode_lowres` (when not in full lowres) is a hybrid: walls stay full width but floors and ceilings use the low-res span drawer with `x>>1` and centerX/2. Odd rows use `I_DrawSpanLowSwap`, which `swap.b`s the word; when an entry's two bytes differ this gives a 2x2 checkerboard (I could not check the lump contents).
- Key numbers: viewports 160x90, 224x128, 256x144, 320x180 (fullscreen default); split-screen variants 160x100 to 160x144.
- Target chapter: 32x/vdp.md
- Evidence: code only

<!-- from D32XR -->
### Palette shifts computed instead of stored
- Source: D32XR, r_main.c:611-673, 830-870 (licence: id limited-use)
- What it does and why it is clever: Doom keeps 14 tinted palettes. This port keeps only the base PLAYPALS and builds a tint when it changes: `c' = c + (target - c)·shift/steps`, clamped, from a 14-row table of (r, g, b, shift, steps). The table covers 8 red damage levels, 4 gold bonus levels, green radsuit and blue pause. It recomputes only when the palette index changes.
- Key numbers: saves 14 x 768 bytes of palettes.
- Target chapter: 32x/vdp.md
- Evidence: code only

---

<!-- from VRD/AU/MARSDEV -->
### Packed-pixel line table, and the one-pass word-write rules
- Source: AU-NOTES, PORT_ARCHITECTURE.md:329-351; disasm/sh2/master/fb.c:1-110; VRD-NOTES, analysis/graphics-vdp/32X_FRAME_BUFFER_FORMAT.md:52-131
- What it does and why it is clever:
  - **Layout:** a 256-word line table heads each buffer, each entry the word address of a line. Pixel data starts at word 256, 160 words (320 px) per line.
  - **Rules:**
    - The VDP always shows 320 px, so short rows display garbage.
    - Byte writes cannot store 0, so use word writes.
    - FM=1 hands both the framebuffer and the VDP registers to the SH-2, so the 68K must set the mode first.
  - **VRD's variant:** a power-of-two `$200`-byte stride (320 px used), so line address = base + y<<9.
- Key numbers: 71,680 B per packed screen; direct colour needs 143,360 B, so only about 204 lines fit.
- Target chapter: 32x/vdp.md
- Evidence: manual, plus emulator measured (Aerobiz U-002 gradient test)

<!-- from VRD/AU/MARSDEV -->
### Line-table vertical scaling for free (zoom)
- Source: AU-NOTES, ROADMAP.md:1301-1410; disasm/sh2/master/fb.c:269-353; MARSDEV, sh_src/mars.c:26-70
- What it does and why it is clever: Nothing forbids two line-table entries pointing at the same row. Each distinct source row is rasterized once into the next free slot, and every display line that maps to it reuses the slot. Vertical magnification is free; cost = distinct rows × 320. X scaling is a per-pixel 16.16 loop packing two samples per word. The window is clamped inside the source rather than bounds-tested per pixel. Overlays drawn into a slot scale automatically. marsdev's `lineskip` uses the same idea for line doubling.
- Key numbers: 224/112/56 rows at 1×/2×/4×, giving 2.13/1.06/0.53 frames per blit (28, 56, 60-capped fps); 1:1 output 100.00% identical to a straight copy.
- Target chapter: 32x/vdp.md
- Evidence: emulator measured (PicoDrive; Ares 2-3 frames for a 1:1 redraw)

<!-- from VRD/AU/MARSDEV -->
### SFT is panning, not scaling
- Source: AU-NOTES, ROADMAP.md:1316-1326; PORT_ARCHITECTURE.md:349-351
- What it does and why it is clever: Line-table addresses are word units, so 2-dot granularity. The SFT bit adds 1-dot horizontal panning but cannot scale. It is ignored when the low byte of the line-table base address is `$FF`.
- Key numbers: see above.
- Target chapter: 32x/vdp.md
- Evidence: manual

<!-- from VRD/AU/MARSDEV -->
### Frame swap rules: paint, wait V-Blank, flip, wait for FS to change
- Source: AU-NOTES, KNOWN_ISSUES.md:739-751; disasm/sh2/master/fb.c:461-475; text.c:416-440; VRD-NOTES, KNOWN_ISSUES.md:544-550
- What it does and why it is clever: FS written during display is deferred to the next V-Blank (manual). Only the back buffer may be touched, and only after FS reads back changed. VRD found that a main-loop swap plus a V-INT swap at the same V-Blank cancel out. Aerobiz found that PicoDrive drops an out-of-V-Blank FS write outright, so a full-page paint must come before the V-Blank wait. Both buffers are painted for static screens.
- Key numbers: see above.
- Target chapter: 32x/vdp.md
- Evidence: emulator measured (PicoDrive/Ares disagree; Ares follows the manual)

<!-- from VRD/AU/MARSDEV -->
### Palette window (PEN): poll per word, retry next frame
- Source: AU-NOTES, KNOWN_ISSUES.md:160-166, 753-763; disasm/sh2/master/text.c:442-465; HISTORY.md:157-189
- What it does and why it is clever: In packed mode the palette is word-only and writable only while PEN=1, finishing within about 1 µs of PEN falling. It is always writable while the layer is blank, so the full palette is loaded before raising the layer. Fades check PEN before each entry and simply retry next frame. PicoDrive opens PEN only in V-Blank while Ares also opens it in each H-Blank, so phase assumptions break on one emulator or the other.
- Key numbers: 16-step fades.
- Target chapter: 32x/vdp.md
- Evidence: emulator measured (PicoDrive/Ares)

<!-- from VRD/AU/MARSDEV -->
### Auto-fill hardware and a DIVS delay
- Source: VRD-NOTES, analysis/RENDERING_PIPELINE.md:342-356; disasm/modules/68k/game/render/mars_dma_xfer_vdp_fill.asm:41-62
- What it does and why it is clever: Writing length, address and data registers clears a run in hardware; the code polls FEN. VRD's 68K clears 192 lines of 160 words, stepping the address `$100` words per line. It burns the fill latency with a `DIVS #$378` (a roughly 140-cycle instruction as a cheap delay) before polling.
- Key numbers: fill time = 7 + 3 × length cycles; length up to 256 words.
- Target chapter: 32x/vdp.md
- Evidence: code only

<!-- from VRD/AU/MARSDEV -->
### Framebuffer write FIFO and the 16-bit DRAM bus
- Source: VRD-NOTES, analysis/POLYGON_TRANSFORMATION_ANALYSIS.md:43-51; analysis/RENDERING_PIPELINE.md:335-340
- What it does and why it is clever: The four-word write FIFO gives 3 + 3 + 3 + 5 = 14 cycles per four writes (3.5 per word) only for back-to-back writes. The framebuffer DRAM is 16-bit, so an SH-2 `MOV.L` becomes two word writes with no gain. The overwrite image at `$04020000`/`$860000` treats zero bytes as transparent.
- Key numbers: 3.5 cycles per word in a burst.
- Target chapter: 32x/vdp.md
- Evidence: manual. VRD's plan to apply this to `unrolled_data_copy` is invalidated (B-009).

---

<!-- from D32XR (hardware survey) -->
### d32xr hardware survey: Frame buffer and 32X VDP
- `Mars_InitVideo` waits for FM, sets 224/240 lines + packed pixel (marshw.c:241-276). PAL uses a letterboxed 240-line mode with an 8-line offset (marsnew.c:426-431; marshw.c:121-125).
- Line table (`Mars_InitLineTable`, marshw.c:112-142): `lines[j] = j*160 + 0x100` (word offsets); unused entries point to one cleared blank line. Drawing base = frame buffer + 0x100 words (marsnew.c:81-83); 320-byte stride (sh2_draw.s:338-339). Menu fire unrolls the title picture by rewriting line-table entries (m_fire.c:375-386). RoQ remaps lines for its canvas pitch (marsroq.c:421-429). Line-table words 0xF0-0xFF used as a 68000 mailbox (marshw.c:388, 656, 679).
- Viewports: 160x90, 224x128, 256x144, 320x180; split-screen 160x100 to 160x144 (r_main.c:232-237). `lowres` halves the width (r_main.c:260-261) by pixel doubling in the drawers: 16-bit colormap entries (r_data.c:911-914), low drawers store words (sh2_drawlow.s:30, 64-66). Low-detail flats alternate `I_DrawSpanLow` / `I_DrawSpanLowSwap` per line (r_phase7.c:164); Swap does `swap.b` on the pixel pair (sh2_drawlow.s:441); purpose not stated. "Potato" mode fills spans with one texel (marsdraw.c:505-585). Anamorphic option changes a stretch constant 22 to 28 (r_main.c:273-282).
- Frame swap: `Mars_FlipFrameBuffers` toggles FS (marshw.c:100-105); `Mars_WaitFrameBuffersFlip` polls FS (:95-98). `I_Update` flips without waiting, then waits ticsperframe vblanks (marsnew.c:1101-1110); next frame waits for the flip before touching the back buffer (marsnew.c:871; r_main.c:253).
- Overwrite image used for text, word-aligned picture blits and the fire (marsnew.c:904-907; marsonly.c:155; marsdraw.c:658, 675-683; m_fire.c:367). Comment marsnew.c:859: "clear the buffer so the fact that 32x ignores 0-byte writes goes unnoticed".
- Palette uploaded in the master VBlank handler (marshw.c:1101-1110, 158-188), skipped and retried if the SH-2 does not own the VDP (:164-165); PEN never checked.
- Auto fill: not used. Direct colour only for RoQ (marsroq.c:434-435). Priority bit toggled for menu/wipe (`Mars_SetVDPPri`, marshw.c:786-793).


<!-- from AB32X -->
### Auto fill as a background renderer (After Burner Complete)
- Source: AB32X, SH-2 code at `0x06008280`-`0x060082F6`
- What it does and why it is clever: Each of 224 lines is two auto fills: sky colour left of a per-line split column, sea colour right of it (colours swap with roll direction). This draws a rolled horizon and clears the frame at once. FEN is polled with a single `tst.b #2,@(r0,gbr)` (GBR = `0x20004100`, r0 = 11).
- Key numbers: 448 fills per drawn frame; manual estimate about 110,700 clocks.
- Target chapter: 32x/vdp
- Evidence: ROM + emulator
