# Harvested techniques: 32x/compositing.md

Target: `32x/compositing.md`. 7 entries. Raw reports and source caveats: [../raw/](../raw/) (paths relative to by-chapter/).

Evidence and licence notes are per entry. Describe in the book's own words; never copy code.

<!-- from VRD/AU/MARSDEV -->
### PRI bit plus per-colour through bit
- Source: VRD-NOTES, analysis/RENDERING_PIPELINE.md:405-498
- What it does and why it is clever: With PRI=0 the Genesis layer is in front (VR's HUD over 3D). Bit 15 of a 32X colour inverts priority for that pixel. VR sets palette entry 1 to `$8000`, opaque black that sits in front of the Genesis layer, for masking. Index 0 on the 32X and colour 0 on the Genesis are transparent; when both are transparent the backdrop shows.
- Key numbers: CRAM entry format T|B5|G5|R5.
- Target chapter: 32x/compositing.md
- Evidence: manual

<!-- from VRD/AU/MARSDEV -->
### Covering a repeating Genesis plane with a through-bit sidebar
- Source: AU-NOTES, disasm/sh2/master/fb.c:426-460; HISTORY.md:1155-1170; HARDWARE_TESTS.md:261-289
- What it does and why it is clever: In H40 a 32-cell Genesis plane repeats columns 0-63 at 256-319. The map asset leaves that strip as index 0 and nothing else uses index 0. Setting the through bit on entry 0 alone puts just that strip in front of the Genesis layer under PRI=0, hiding the repeat at zero pixel cost.
- Key numbers: SIDEBAR_COLOUR `$2400 | $8000`.
- Target chapter: 32x/compositing.md
- Evidence: emulator measured (PicoDrive/Ares agree). PicoDrive adds one green step to through-bit colours.

<!-- from VRD/AU/MARSDEV -->
### H32 is illegal under a live layer
- Source: AU-NOTES, ROADMAP.md:191-228, 587-640
- What it does and why it is clever: The 32X video clock is EDCLK (always the H40 clock), so an H32 Genesis screen and the 32X layer differ in scale by 1.25×. The manual allows H32 only with the layer blank. The map screen therefore forces register 12 to H40 from the game's own register shadow each frame while the layer is up, and only then.
- Key numbers: H40 registration 100.00% pixel-identical; a nearest-neighbour stretch of H32 only 95.6%.
- Target chapter: 32x/compositing.md
- Evidence: emulator measured (PicoDrive; Ares agrees in H40)

<!-- from VRD/AU/MARSDEV -->
### Genesis CRAM mirrored into the 32X palette
- Source: AU-NOTES, disasm/32x/map_screen.asm:1-58, 295-343; HISTORY.md:1188-1206; KNOWN_ISSUES.md:640-647
- What it does and why it is clever:
  - **Mirror:** palette entries 16-31 track CRAM line 1, so Genesis fades, tints and dimming apply to the SH-2 map for free. The source is the game's RAM copy of CRAM at `$FF1400`, which needs no VDP read.
  - **Timing:** mirroring from V-Blank ran exactly one frame behind, because the game writes CRAM just after its V-Blank handler. The palette-writer routine is therefore hooked to mirror at the moment of the write, with PEN checked per word.
  - **Conversion:** a 512-entry assembler-generated table converts 9-bit Genesis colour to BGR555 by bit replication, `(v<<2)|(v>>1)`.
  - **Exit:** the layer leaves when the line-1 fade reaches black, or after 48 frames.
- Key numbers: copy equalled CRAM in 64 of 64 words over 222 states; the stale-frame bug showed 12,288 Genesis pixels new against 45,056 map pixels old; 71 of 71 frames exact through a turn change.
- Target chapter: 32x/compositing.md
- Evidence: emulator measured (PicoDrive)

<!-- from VRD/AU/MARSDEV -->
### A palette budget shared by every layer user
- Source: AU-NOTES, PORT_ARCHITECTURE.md:425-445
- What it does and why it is clever:

  | Range | Owner |
  |---|---|
  | 0 | sidebar / transparent |
  | 1-15 | engine UI |
  | 16-31 | CRAM mirror (never written by anything else) |
  | 32-63 | UI ramps |
  | 64-253 | content art, re-uploaded per screen in one PEN window |
  | 254-255 | text ink/paper |

  The layer is double-buffered but the palette is not, so ownership is declared per layer state.
- Key numbers: 256 BGR555 words.
- Target chapter: 32x/compositing.md
- Evidence: code only (design)

<!-- from VRD/AU/MARSDEV -->
### Seamless 32X-to-Genesis hand-off
- Source: AU-NOTES, disasm/sh2/master/fb.c:1270-1290; HISTORY.md:1598-1606; HARDWARE_TESTS.md:223-260
- What it does and why it is clever: When both buffers hold the identity frame, PRI is cleared in V-Blank so the identical Genesis logo takes the front, then the layer blanks unseen. This works around PicoDrive carrying PRI in the green LSB. On hardware, and on Ares, the Genesis DAC is nonlinear (0, 52, 87, 116, 144, 172, 206, 255) against the 32X's linear output, so a small colour step is expected at the first switch.
- Key numbers: level 7 is 255 on the Genesis against about 238 from the 32X palette.
- Target chapter: 32x/compositing.md
- Evidence: emulator measured (PicoDrive/Ares)

---

<!-- from MK2 -->
### 32X fighters in front of a Mega Drive arena (Mortal Kombat II)
- Source: MK2, palette and bitmap mode register read in PicoDrive at frames 900, 1140 and 1700; frame-buffer renders; notes/games/mk2/ANALYSIS.md
- What it does and why it is clever: The bitmap mode register reads `$8001` (packed pixel, PRI = 0, so the Mega Drive is in front). 255 of the 256 palette entries carry the through bit, so every non-zero 32X pixel flips to the front. During a fight the 32X frame buffer holds only the fighters and a few foreground objects (a hanging chain), so they appear over a Mega Drive arena and HUD. The menus (fighter select, Battle Plan) are drawn entirely on the 32X with the same palette rule.
- Key numbers: PRI 0, 255 through entries, packed pixel.
- Target chapter: 32x/compositing.md
- Evidence: ROM + emulator
