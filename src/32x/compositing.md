# Mixing 32X and Mega Drive graphics

The 32X does not draw into the Mega Drive's picture, and the Mega Drive does not draw into the 32X's. Each VDP makes a complete picture of its own, and a mixer in the 32X picks one of the two for every pixel on its way to the TV. This chapter covers the rule that makes that choice, how shipped games use it to split the work between the two VDPs, what the display modes must agree on, and what to watch for when colours from both sides have to match.

## Two pictures, one output

The Mega Drive's video leaves the console through the cartridge slot, into the 32X, and the 32X's video mixer combines it with its own VDP's output [32X-INTRO, block diagram]. Besides the picture itself, the Mega Drive sends a signal that tells the mixer where its picture is showing the backdrop, the colour of register 7 that fills every pixel no plane or sprite covers. PicoDrive's source names it /YS [PICODRIVE, pico/32x/draw.c]. The mixer needs three things to decide a pixel: whether the Mega Drive pixel there is backdrop, the 32X pixel's through bit, and the PRI bit of the 32X's bitmap mode register (bit 7 of `$A15180` / `0x20004100`).

## The rule for each pixel

PRI sets which picture is in front by default. The through bit, bit 15 of a 32X colour, reverses that for the pixels that carry it [32X-HWM §3.3, priority; 32X-INTRO, priority; 32X-OV, priority figure] <span class="tag manual">manual</span>:

| PRI | Through bit | Mega Drive pixel drawn | Mega Drive pixel is backdrop |
|-----|-------------|------------------------|------------------------------|
| 0 (initial) | 0 | Mega Drive | 32X |
| 0 | 1 | 32X | 32X |
| 1 | 0 | 32X | 32X |
| 1 | 1 | Mega Drive | 32X |

When the 32X is in blank mode (M1 M0 = 00), only the Mega Drive picture is shown, backdrop included.

The manual says the Mega Drive's colour 0 is transparent; the right-hand column is how both emulators read that: wherever the Mega Drive would show its backdrop, the 32X pixel shows, whatever its through bit <span class="tag emulator">emulator</span> [PICODRIVE, pico/32x/draw.c; ARES, md/m32x/vdp.cpp]. Put as one rule: the 32X pixel is shown if its through bit differs from PRI, or if the Mega Drive has nothing there.

What follows from that:

- **No 32X colour is transparent.** Palette index 0 is special only to writes through the overwrite image, which skip zero bytes ([Writing pixels](vdp.md#the-normal-and-overwrite-images)). On screen, index 0 is a colour like any other, with its own through bit. The VRD project's notes say index 0 lets the Mega Drive show through [VRD-NOTES, analysis/RENDERING_PIPELINE.md §9]; neither the manual nor either emulator agrees.
- **The Mega Drive's backdrop colour disappears while the layer is on.** Every backdrop pixel takes the 32X pixel instead. A screen that relied on register 7 for its background colour must draw that colour on the 32X <span class="tag emulator">emulator</span> [AU-NOTES, ROADMAP.md U-003].
- **PRI only flips the meaning of the bit.** Any picture made with PRI = 0 can be made with PRI = 1 by flipping the through bit of every colour in use. So choose PRI by which group of colours is smaller, or by which change you want to make with one register write (see [handing over](#handing-the-screen-from-one-layer-to-the-other)).
- **In direct colour mode each pixel carries its own through bit**, as bit 15 of its 16-bit word. In packed pixel and run length modes it comes from the palette entry [32X-HWM §3.3, direct color mode, run length mode].
- **PRI can change between lines.** The VDP reads its registers at the end of each horizontal blank, so a new PRI applies from the next line [32X-HWM §3.3, VDP register]. Changing it from an H interrupt would put the 32X in front on part of the screen only. No program in our sources does this.

## How games split the work

Four retail games and two of the book's projects, by what each VDP draws:

| Program | PRI | Through bits | Mega Drive draws | 32X draws |
|---------|-----|--------------|------------------|-----------|
| Star Wars Arcade | 0 | None, in play | Cockpit, score, timer | Space, ships, hyperspace |
| Virtua Racing Deluxe | 0 | Entry 1 only (`$8000`) | Race HUD | The 3D scene |
| After Burner Complete | 0 | None, in play | Player's jet, HUD, crosshair | Sky and sea, ground detail, enemies, clouds, explosions |
| Mortal Kombat II | 0 | All entries but 0 | Arena, energy bars | Fighters, foreground objects, menus |
| Knuckles' Chaotix | 1 | Entry 0 and 122 others | The level | Characters and some objects |
| Aerobiz Ultimate, world map | 0 | Entry 0 only | Panels and text | The map |
| Aerobiz Ultimate, SEGA logo | 1, then 0 | | The final logo | The spinning logo |

Sources: [SWA], [MK2], [AB32X], [CHAOTIX], bitmap mode register and palette read in PicoDrive, and 32X frame buffers dumped (SWA at frame 1600, MK2 at frames 900-1700, After Burner Complete at frames 300 and 700 of play, Chaotix at attract frames 4300 and 4400); [VRD-NOTES, analysis/RENDERING_PIPELINE.md §9]; [AU-NOTES, disasm/sh2/master/fb.c, disasm/32x/map_screen.asm] <span class="tag emulator">emulator</span>.

### Mega Drive in front: HUDs and cockpits

The default, PRI = 0 and no through bits, puts the Mega Drive on top. The 32X draws the full screen behind it, and the Mega Drive's tiles cover it wherever they are not transparent. Star Wars Arcade does exactly this. Its 32X frame buffer holds only the scene, and the X-wing cockpit, score and timer are Mega Drive tiles in front of it [SWA, 32X frame buffer at frame 1600]. Virtua Racing does the same with its race HUD [VRD-NOTES, analysis/RENDERING_PIPELINE.md §9]. In After Burner Complete the Mega Drive draws the player's own jet as well as the HUD, so the one object that is always on screen, and always the same size, costs the SH-2 nothing [AB32X, 32X frame buffer during play].

What this buys: the HUD costs the SH-2s nothing, never has to be redrawn into the frame buffer, and can change on the 68000's schedule. Text, which the Mega Drive draws well from a font in VRAM, stays off the 32X entirely. The 32X has to fill every pixel of its layer each frame, because anything not covered by a Mega Drive tile is visible.

### Mega Drive behind: 32X objects over a tile background

Mortal Kombat II turns it round. PRI stays 0, but 255 of its 256 palette entries have the through bit set; entry 0 alone does not, and holds `$0000` [MK2, palette read in PicoDrive at frames 900, 1140 and 1700]. In a fight the 32X frame buffer holds only the two fighters and a few foreground objects such as a hanging chain, on a field of index 0. The fighters come out in front of everything the Mega Drive draws. The index 0 field sits behind the Mega Drive's arena, which covers the whole screen, so it never shows.

By the rule above this is the same picture as PRI = 1 with the through bit on entry 0 only. Knuckles' Chaotix makes its picture the other way: PRI = 1, with the through bit on entry 0, the field its characters are drawn on, and on 122 other entries [CHAOTIX, bitmap mode register `$8081` and palette read in PicoDrive]. The choice costs nothing either way: the palette data carries the bit, so it is set once when the palette is built.

What this buys: the arena is Mega Drive tiles, scrolled and animated by the Mega Drive VDP at no cost to the SH-2s. The SH-2s draw only the fighters. The rest of the frame buffer is reset to index 0 each frame by the VDP's auto fill, with no CPU writes ([The 32X VDP](vdp.md#auto-fill)). The fighters get the 32X's colour range, and the backgrounds stay in the Mega Drive's.

Homebrew written for PicoDrive often sets the through bit on every entry for the same reason: with PRI = 0 and no through bits, a frame drawn on the 32X is hidden wherever the Mega Drive's planes hold opaque tiles [S32X-SKILL, testing.md] <span class="tag emulator">emulator</span>.

### Masks: one entry that reverses the default

A single colour with the opposite through bit can hide part of the other layer.

- **Virtua Racing** sets palette entry 1 to `$8000`: black, with the through bit. Under PRI = 0, any pixel drawn with index 1 covers the Mega Drive HUD, so the 3D renderer can black out a region of the HUD <span class="tag emulator">emulator</span> [VRD-NOTES, analysis/RENDERING_PIPELINE.md §9]. Mortal Kombat II's Battle Plan screen has the same `$8000` in entry 1 [MK2, palette read at frame 1140].
- **Aerobiz Ultimate's world map** covers a Mega Drive artefact. In the 320-pixel mode a 32-tile-wide Mega Drive plane repeats, so columns 0-63 appear again at 256-319. The map's art leaves that strip as index 0, and nothing else in the map uses index 0. With the through bit on entry 0 alone, only the strip comes in front of the Mega Drive and hides the repeat. This costs no drawing at all <span class="tag emulator">emulator</span> [AU-NOTES, disasm/sh2/master/fb.c, HARDWARE_TESTS.md §9].

## The display modes must match

While the 32X layer is visible, the Mega Drive must use the 320-pixel (H40) mode, and its line count must match the 32X's (224, or 240 on PAL). The 256-pixel (H32) modes are allowed only while the 32X is blank <span class="tag manual">manual</span> [32X-HWM §3.3, display mode possible combinations].

The reason is the clock. The 32X takes its pixel clock from EDCLK on the cartridge slot, which always runs at the H40 rate. In H32 the Mega Drive fills the same width of the screen with 256 wider pixels, so the two layers sit at scales 1.25× apart and no 32X pixel lines up with a Mega Drive pixel. PicoDrive's source says the combination does work on a console, with the layers 4 pixels apart; Ares draws it about 3¼ pixels apart <span class="tag disputed">disputed</span> ([discrepancy 26](../appendices/discrepancies.md)) [PICODRIVE, pico/32x/draw.c; ARES, md/vdp/main.cpp]. Aerobiz Ultimate measured the mismatch: in H40 the two layers register pixel for pixel, while the best 256-to-320 stretch of an H32 screen matches only 95.6% of pixels <span class="tag emulator">emulator</span> [AU-NOTES, ROADMAP.md U-003].

A game that runs in H32 can still use the layer on some screens. Aerobiz runs in H32. Its port switches register 12 to H40 every frame while the map layer is up, from the game's own copy of the register, and puts the game's value back when the layer goes blank. While the SH-2 is still drawing, the layer is blank and H32 is allowed, so nothing is forced [AU-NOTES, disasm/32x/map_screen.asm].

The 240-line mode exists only on PAL, where the Mega Drive must be in its 30-row mode too ([The 32X VDP](vdp.md#what-the-vdp-shows)).

## Sharing colours between layers

### One palette, many users

There is one 256-entry palette, and it is not double-buffered like the frame buffers ([Colours and the palette](vdp.md#colours-and-the-palette)). When several parts of a program draw on the layer, it helps to give each a fixed range of entries. Aerobiz Ultimate's plan [AU-NOTES, PORT_ARCHITECTURE.md]:

| Entries | Used for |
|---------|----------|
| 0 | The through-bit sidebar, or transparent background |
| 1-15 | Interface colours of the engine |
| 16-31 | Copy of Mega Drive palette line 1 (written by nothing else) |
| 32-63 | Interface colour ramps |
| 64-253 | Art for the current screen, loaded in one palette window |
| 254-255 | Text ink and paper |

### Following the Mega Drive's palette

Fades, flashes and dimmed backgrounds on the Mega Drive are changes to its CRAM, which the 32X never sees. If the 32X layer must fade with the rest of the screen, its palette has to follow. Aerobiz Ultimate keeps entries 16-31 equal to the game's CRAM line 1 <span class="tag emulator">emulator</span> [AU-NOTES, disasm/32x/map_screen.asm]:

- **Source.** The game keeps a copy of CRAM in work RAM, so the copy needs no Mega Drive VDP reads. Over 222 sampled states, fades included, the copy matched CRAM in all 64 words every time.
- **Conversion.** A Mega Drive colour has 3 bits per channel; the 32X has 5. A 512-entry table converts each 9-bit colour, widening each channel by repeating its top bits: `(v << 2) | (v >> 1)`, so 7 becomes 31.
- **Timing.** Copying in the 68000's V-Blank handler ran one frame late, because the game writes CRAM just after that handler returns. On every fade step, the Mega Drive part of the screen changed a frame before the map. The fix was to hook the game's own palette-write routine and copy at the moment of the write, checking PEN before each word. The V-Blank copy stays as a fallback.
- **Exit.** The layer is switched off once the copied line has faded to black, so the switch cannot be seen.

### The two DACs differ

The Mega Drive turns its 8 levels per channel into voltages through an uneven scale. No source gives the 32X's output levels, and both emulators treat its 32 levels as evenly spaced. So a 32X colour converted from a Mega Drive colour by repeating bits will not match it exactly on screen. Ares models this. It uses measured levels (0, 52, 87, 116, 144, 172, 206, 255 out of 255) for the Mega Drive and a straight scale for the 32X <span class="tag emulator">emulator</span> [ARES, md/vdp/color.cpp]. With bit repetition the two ends agree, but the steps between do not. Mega Drive level 1 shows at 52, its 32X copy (4 of 31) at about 33; level 6 shows at 206, its copy (27) at about 222. A 32X palette built to match one emulator's Mega Drive levels shows a step in the other: Aerobiz Ultimate's SEGA logo expects its white to brighten by about 17 of 255 under Ares when the Mega Drive takes over [AU-NOTES, HARDWARE_TESTS.md §8]. PicoDrive does not show the difference. See [Real output levels](../megadrive/vdp-color.md#real-output-levels).

Where an object has to cross from one layer to the other, plan for a small colour step, or build the 32X colours from a measured Mega Drive table rather than by repeating bits.

## Handing the screen from one layer to the other

Aerobiz Ultimate's SEGA logo spins on the 32X layer with PRI = 1, then stops exactly on the still logo the Mega Drive has been showing behind it all along. To leave the layer without a visible change <span class="tag emulator">emulator</span> [AU-NOTES, disasm/sh2/master/fb.c, HARDWARE_TESTS.md §8]:

1. Draw the final frame into both frame buffers, so a late swap cannot show anything else.
2. In V-Blank, clear PRI. The Mega Drive logo is now in front, covering the identical 32X one.
3. A few frames later, in V-Blank, set the layer to blank.

Any colour difference between the two DACs shows at step 2, as the logo stops, where the eye expects a change. Nothing changes at step 3. Mode and priority changes apply from the next line, so both writes go in V-Blank, not mid-picture.

## In emulators

- **Both** implement the table above, including the backdrop rule. They differ on what counts as backdrop. PicoDrive compares the Mega Drive pixel's colour index with register 7. A tile or sprite pixel drawn with the same CRAM entry as the backdrop therefore lets the 32X through as well. Ares has the Mega Drive VDP flag real backdrop pixels <span class="tag disputed">disputed</span> ([discrepancy 27](../appendices/discrepancies.md)) [PICODRIVE, pico/32x/draw.c; ARES, md/vdp/dac.cpp, md/m32x/vdp.cpp].
- **PicoDrive's usual 16-bit output** keeps the front-or-behind decision in the lowest green bit of each 32X colour. Every 32X pixel that wins priority comes out one green step brighter than its palette value, and no 32X colour in front can equal a Mega Drive colour exactly. Aerobiz Ultimate's hand-off clears PRI partly because of this <span class="tag emulator">emulator</span> [PICODRIVE, pico/32x/draw.c; AU-NOTES, disasm/sh2/master/fb.c].
- **H32 under a live layer** works in both, with different offsets (see above). Neither failing nor working in an emulator says anything about a console.
- **Shadow and highlight** on the Mega Drive side are applied to its pixels before the mix in both, and the backdrop rule ignores them. How a console's /YS signal behaves for shadowed backdrop is not documented.

## Open questions

- What exactly does the Mega Drive signal as "nothing here": backdrop pixels only, or any pixel using the backdrop's CRAM entry ([discrepancy 27](../appendices/discrepancies.md))? Is a shadowed or highlighted backdrop still backdrop?
- What does a console show with H32 under a visible 32X layer ([discrepancy 26](../appendices/discrepancies.md))?
- Is the 32X's colour output linear, and how large is the step between a Mega Drive colour and its bit-repeated 32X copy on a real TV?
- Does changing PRI from an H interrupt split the screen cleanly at a line, as the register latch timing suggests?

## Sources

- [32X-HWM](../appendices/bibliography.md#32x-hwm): §3.3 priority, VDP register, direct color mode, run length mode, display mode possible combinations
- [32X-INTRO](../appendices/bibliography.md#32x-intro): block diagram, priority
- [32X-OV](../appendices/bibliography.md#32x-ov): priority figure
- [SWA](../appendices/bibliography.md#swa): bitmap mode register, palette and frame buffer read in PicoDrive
- [MK2](../appendices/bibliography.md#mk2): bitmap mode register, palette and frame buffer read in PicoDrive
- [CHAOTIX](../appendices/bibliography.md#chaotix): bitmap mode register, palette and frame buffer read in PicoDrive
- [AB32X](../appendices/bibliography.md#ab32x): bitmap mode register, palette and frame buffer read in PicoDrive
- [VRD-NOTES](../appendices/bibliography.md#vrd-notes): analysis/RENDERING_PIPELINE.md §9
- [AU-NOTES](../appendices/bibliography.md#au-notes): ROADMAP.md U-003, PORT_ARCHITECTURE.md, HARDWARE_TESTS.md §8-9, disasm/32x/map_screen.asm, disasm/sh2/master/fb.c
- [S32X-SKILL](../appendices/bibliography.md#s32x-skill): testing.md
- [PICODRIVE](../appendices/bibliography.md#picodrive): pico/32x/draw.c
- [ARES](../appendices/bibliography.md#ares): md/m32x/vdp.cpp, md/vdp/main.cpp, md/vdp/dac.cpp, md/vdp/color.cpp
