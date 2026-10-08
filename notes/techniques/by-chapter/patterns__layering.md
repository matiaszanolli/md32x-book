# Harvested techniques: patterns/layering.md

Target: `patterns/layering.md`. 2 entries. Raw reports and source caveats: [../raw/](../raw/) (paths relative to by-chapter/).

Evidence and licence notes are per entry. Describe in the book's own words; never copy code.

<!-- from VRD/AU/MARSDEV -->
### 68K decides, SH-2 draws: map-layer lifecycle
- Source: AU-NOTES, disasm/32x/map_screen.asm:1-58; ROADMAP.md:1091-1170
- What it does and why it is clever: The game's screen id (`$FF9A1C` = 7) drives the layer from the V-Blank trampoline:
  1. **Switch on:** a new generation is posted and FM goes to the SH-2, which draws both buffers while the layer is still blank.
  2. **Show:** when the "drawn" reply carries a matching generation, the 68K takes FM back, mirrors the palette, shows the layer with PRI=0 and forces H40.
  3. **Switch off:** happens after the fade, because the screen id changes before the picture does.
  
  Plane B's map cells are filled with transparent tile 0 by a 5-byte same-length patch.
- Key numbers: 21 calling screens; 48-frame linger cap.
- Target chapter: patterns/layering.md
- Evidence: emulator measured (PicoDrive)

---

<!-- from MK2 -->
### Mega Drive arena, 32X characters (Mortal Kombat II)
- Source: MK2, frame-buffer renders and register reads in PicoDrive; notes/games/mk2/ANALYSIS.md
- What it does and why it is clever: The split follows what each chip does best. The Mega Drive's tile planes draw the scrolling arena and the HUD; the 32X draws only the fighters, which need many colours and large animation frames. The 32X layer is cleared and redrawn every frame (161 auto-fills plus RLE blits), while the arena costs the SH-2s nothing.
- Key numbers: 64-colour palette slice per fighter; clear of 224 × 368 bytes per frame.
- Target chapter: patterns/layering.md
- Evidence: ROM + emulator
