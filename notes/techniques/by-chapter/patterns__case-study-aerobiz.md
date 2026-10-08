# Harvested techniques: patterns/case-study-aerobiz.md

Target: `patterns/case-study-aerobiz.md`. 9 entries. Raw reports and source caveats: [../raw/](../raw/) (paths relative to by-chapter/).

Evidence and licence notes are per entry. Describe in the book's own words; never copy code.

<!-- from VRD/AU/MARSDEV -->
### A byte-identical dual-target build as the regression oracle
- Source: AU-NOTES, PORT_ARCHITECTURE.md:172-203, 277-300
- What it does and why it is clever: One source tree builds the Genesis ROM (`ROM_BASE`=0, MD5-verified identical to the original) and the 32X ROM (`ROM_BASE`=`$900000`). Literals carry original offsets, so the 32X image must keep the Genesis layout byte for byte. All 32X behaviour lives in the boot half, below the stack pointer, or in same-size `ifne ROM_BASE` patches. The Genesis check cannot see a constant wrongly rebased, hence the separate audits.
- Key numbers: game half differs in 5,793 isolated single bytes (`$0X` → `$9X`); no runs.
- Target chapter: patterns/case-study-aerobiz.md
- Evidence: emulator measured (MD5 plus playthroughs)

<!-- from VRD/AU/MARSDEV -->
### Level-of-detail airports for free
- Source: AU-NOTES, ROADMAP.md:2622-2668
- What it does and why it is clever: The city index already encodes the tier (index < 32 is major), so level of detail is one comparison: draw secondaries when `step ≤ FP_ONE/2` (a source pixel covers at least two dots). Markers drawn into shared line-table slots scale with the zoom automatically.
- Key numbers: 32 major and 57 secondary airports; all majors on exact coordinates at 1:1.
- Target chapter: patterns/case-study-aerobiz.md
- Evidence: emulator measured (PicoDrive)

<!-- from VRD/AU/MARSDEV -->
### A text engine and 32X-native menus
- Source: AU-NOTES, ROADMAP.md:1962-2070, 2875-2965; disasm/sh2/master/text.c:1-60, 391-480
- What it does and why it is clever: A PC tool turns DejaVu into 1bpp variable-width glyphs. The SH-2 engine measures, wraps and draws them with ink 254 and paper 255 (never 0, so byte writes are safe). Menus pulse the highlight by animating one palette entry, with no pixel redraw. Fades follow PEN. A 68K timeout falls back to the stock screen. Title art is quantized to 253 colours; its letterbox colour is sampled from the art.
- Key numbers: 16-frame fades; menu repeat ramps from 10 to 5/3/2 frames.
- Target chapter: patterns/case-study-aerobiz.md
- Evidence: emulator measured (PicoDrive; Ares sign-off by eye)

---

One thing outside the task: several claude.ai connectors (Atlassian, Google Calendar, Google Drive) need authorizing in claude.ai's connector settings before they can be used. The GitHub plugin failed to connect (bad Authorization header). Neither affected this research.

<!-- from AB-DISASM -->
### A trap-style "BIOS": GameCommand, 47 assembly services called from C
- Source: AB-DISASM, disasm/modules/68k/game/GameCommand.asm:1-46 ($000D64, 306 call sites)
- What it does and why it is clever: The C-compiled game logic pushes long arguments and calls one entry point with a command number.
  - The entry saves SR before LINK, loads A5 = $FFF010 and A4 from a 47-entry jump table, and returns with RTR.
  - An out-of-range number locks up deliberately.
  - Handlers cover VDP register access, DMA, rectangle fill and blit, sprites, input, Z80 mailbox commands, frame waits, and so on.

  This splits hardware code from portable game code: Koei's PC-98 title becomes C plus a small hand-written Mega Drive back end.
- Key numbers: 47 handlers; arguments start at $E(a6).
- Target chapter: patterns/case-study-aerobiz.md
- Evidence: code only (shipped)

<!-- from AB-DISASM -->
### One shared scratch arena for mutually exclusive screens
- Source: AB-DISASM, analysis/RAM_MAP.md:250-270 ($FF1804); users: disasm/modules/68k/graphics/LoadScreenGfx.asm:11-19, disasm/modules/68k/game/PackSaveState.asm:22-25, disasm/modules/68k/game/PackScrollDeltaToVRAM.asm:9-15, disasm/modules/68k/game/DecompressGraphicsData.asm:8-9
- What it does and why it is clever: The block at $FF1804 is reused for different jobs on different screens:
  - the LZ output buffer
  - the 22.5 KB map bitmap canvas
  - the save image (header + payload)
  - the H-scroll table builder (at +$5000)
  - portrait decompression

  Only one of these screens is ever active, so there is no allocator: each screen owns the arena while it runs. That is static overlaying, and it is how a 64 KB machine runs a large strategy game.
- Key numbers: at least $5800 bytes for the map canvas, plus the +$5000 H-scroll area.
- Target chapter: patterns/case-study-aerobiz.md
- Evidence: code only (shipped)

<!-- from AB-DISASM -->
### RNG: C's LCG mixed with the HV counter
- Source: AB-DISASM, disasm/modules/68k/math/RandRange.asm:1-34 ($01D6A4, 64 calls); disasm/modules/68k/vdp/CmdGetVDPStatus.asm ($00046A, reads $C00008)
- What it does and why it is clever: The state at $FFA7E0 advances as s = s×1103515245 + 12345 (the ANSI C constants), using Multiply32. The value returned is (low word of the *previous* state + the VDP H/V counter) mod (max − min + 1), plus min. Mixing in the raster position adds entropy that depends on when the player pressed a button, at the cost of one port read.
- Key numbers: multiplier $41C64E6D, increment $3039; range via SignedMod.
- Target chapter: patterns/case-study-aerobiz.md
- Evidence: code only (shipped)

<!-- from AB-DISASM -->
### Economy formulas as integer percentage chains
- Source: AB-DISASM, disasm/modules/68k/game/CalcOptimalTicketPrice.asm:60-120 ($00F75E); disasm/modules/68k/game/CalcQuarterBonus.asm ($0140DC)
- What it does and why it is clever: Prices are pure integer maths with no fixed point:
  - market = (cap + 20)(skill + 1)(frame/3 + 30) / 100
  - cost = (cap×15×2 + 600)(skill + 1) / 2, with ×15 done as `(x<<4) − x` and the halving done with sign-correct rounding (+1 if negative, then `asr`)
  - The frame counter is used as a slow time-varying "market" term.
  - Bonuses are ×20 / k, clamped to 100%.
- Key numbers: base 600 ($258); /100 percentages.
- Target chapter: patterns/case-study-aerobiz.md (or NEW: Fixed-point maths)
- Evidence: code only (shipped)

<!-- from AB-DISASM -->
### Region membership as a range test on sorted city IDs
- Source: AB-DISASM, disasm/sections/section_000200.asm:529-591 (RangeLookup $00D648, 114 calls); disasm/modules/68k/game/FindBitInField.asm:1-42 ($009DC4)
- What it does and why it is clever: The 89 cities are numbered so that each of the 8 regions owns a contiguous run in two ID blocks (0-31 and 32-88). A table of (startA, countA, startB, countB) turns "which region is city n in?" into a scan of 8 entries. FindBitInField uses the same start values to turn a per-player 32-bit ownership mask into global IDs, starting from bit = 1 << start.
- Key numbers: 8 regions × 4 bytes at $05ECBC.
- Target chapter: patterns/case-study-aerobiz.md
- Evidence: code only (shipped)

<!-- from AB-DISASM -->
### Idempotent fade guards (misnamed ResourceLoad / ResourceUnload)
- Source: AB-DISASM, disasm/modules/68k/game/ResourceLoad.asm:1-16 ($01D71C, 106 calls); ResourceUnload ($01D748, 95 calls)
- What it does and why it is clever: Before drawing, every screen calls a guarded "fade out if not already faded" that fades all 64 colours over 8 steps of 2 frames and sets a flag. After drawing it calls the matching fade-in. The flag lets calls nest safely, so screens can be drawn in any order without double fades.
- Key numbers: 64 colours, 8 steps × 2 frames ≈ 0.27 s.
- Target chapter: patterns/case-study-aerobiz.md
- Evidence: code only (shipped)

---

