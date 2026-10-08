# Color, shadow/highlight and interlace

This chapter covers how the VDP turns tile and sprite pixels into colours. That means the palette memory, the order in which layers cover each other, shadow and highlight (which give each colour a darker and a brighter version), and the two interlace modes. It ends with palette effects from shipped code.

## Colour RAM

CRAM holds 64 colours, four palettes of 16. Each entry is one word [MD-SWM §2.12; GENVDP §9]:

```
bit  15-12  11-9  8   7-5  4   3-1  0
     0000   BBB   0   GGG  0   RRR  0
```

Three bits per component give 512 possible colours. In hex, a colour is `$0BGR` with each digit even: `$0EEE` is white, `$000E` full red, `$0E00` full blue.

| CRAM address | Palette | Colours |
|--------------|---------|---------|
| `$00-$1E` | 0 | 0-15 |
| `$20-$3E` | 1 | 0-15 |
| `$40-$5E` | 2 | 0-15 |
| `$60-$7E` | 3 | 0-15 |

Colour *c* of palette *p* is at CRAM address (*p* × 16 + *c*) × 2. Colour 0 of every palette is transparent in tiles and sprites, whatever it holds. Any of the 64 entries, colour 0s included, can be the backdrop through register 7 [MD-SWM §2.12; GENVDP §17]. In shadow/highlight mode, palette 3's colours 14 and 15 have a special meaning in sprites ([below](#operator-sprites)).

A CRAM write takes effect at once, even in the middle of a line. PicoDrive times CRAM writes to the pixel being drawn for this reason <span class="tag emulator">emulator</span> [PICODRIVE, pico/videoport.c]. Changing colours on the visible part of the screen therefore shows up as a change part way along a line. Do palette updates in vertical blank, or from a line interrupt where a change between lines is the point. Aerobiz's palette animation checks the status register's VB bit and skips the frame's update if it has run into the display [AB-DISASM, VInt_Sub1.asm]. On PAL in 28-row mode, the bottom border is visible, so even the start of vertical blank is on screen ([Timing](vdp-timing.md#a-frame-line-by-line)).

Register 0 bit 2 must be 1. With it at 0, GENVDP found that only the lowest bit of each component counts, leaving 8 colours [GENVDP §17; see [Registers](vdp-registers.md)].

### Real output levels

Sega's manual draws the 8 levels of a component as an even staircase from dark to bright. It draws shadow as the same staircase compressed into the lower half, and highlight as the same in the upper half [MD-SWM §2.12, RGB bit and display]. Measured consoles are less tidy, and our sources disagree on the details:

| Source | Normal | Shadow | Highlight |
|--------|--------|--------|-----------|
| MD-SWM (drawn) | Even steps, 0 to full | Lower half | Upper half |
| PicoDrive | 2 × *c* on a 0-14 scale, with a bigger step from 0 to 1 and from 6 to 7 | *c* | *c* + 7 |
| GENVDP | — | — | "Not much brighter" than normal; exact doubling looks wrong in most games |

Sources: [MD-SWM §2.12; PICODRIVE, pico/draw.c; GENVDP §16]. PicoDrive's comment cites the colour test in Knuckles' Chaotix as evidence of the uneven first step <span class="tag emulator">emulator</span>. For art made in a PC tool, the practical points are:

- The darkest non-black level is brighter than a linear scale suggests.
- Highlight is a lift towards white, not a doubling.

Convert colours with a table measured from a console, not with `component × 255 / 7`. Our sources do not contain one ([open question](#open-questions)).

## Priority

Every pixel on screen comes from the frontmost non-transparent layer at that spot. With the priority bits from name table entries and sprite entries, the order from back to front is [GENVDP §14; MD-SWM §2.11]:

1. Backdrop colour
2. Plane B, low priority
3. Plane A (or the window), low priority
4. Sprites, low priority
5. Plane B, high priority
6. Plane A (or the window), high priority
7. Sprites, high priority

A transparent pixel (colour 0) shows whatever is next down the list.

The sprite priority bit only places a sprite among the planes. Between sprites, the link list decides alone ([Sprites](vdp-sprites.md#the-link-list)). A low-priority sprite earlier in the list covers a high-priority sprite later in it, in the places where no high-priority plane tile covers the low-priority one. Some games use that to hide parts of sprites [GENVDP §14].

Uses that fall out of the order:

- **Foreground objects.** High-priority tiles in plane A (a tree trunk, a doorway) cover low-priority sprites walking behind them. The sprite needs no clipping.
- **Status bars and dialog boxes.** High-priority tiles in the window or plane A sit above every low-priority sprite. Aerobiz sets the priority bit on every tile of its dialog boxes for this reason [AB-DISASM, DrawBox.asm].
- **A sprite above everything.** Give it high priority and put it first in the link list.

## Shadow and highlight

Setting register 12 bit 3 (S/TE) turns on shadow/highlight mode. Every pixel can then be shown at normal brightness, darker (shadow) or brighter (highlight), which triples the colours available on screen without touching CRAM [MD-SWM §2.11, §2.12]. Which version a pixel gets depends on priority bits and on special sprite colours.

### Planes and backdrop

- Where **both** planes have a low-priority tile, the pixel is shadowed, whatever layer it comes from: plane B, plane A, a low-priority sprite or the backdrop [MD-SWM §2.11; GENVDP §16].
- Where **either** plane has a high-priority tile, everything at that spot is shown at normal brightness. This holds even if that tile's pixel there is transparent, and it covers the backdrop and sprites too [GENVDP §16].
- A high-priority sprite pixel is always at normal brightness [MD-SWM §2.11].
- The border outside the active picture is never shadowed [GENVDP §16].

So, with S/TE set and every tile left at low priority, the whole picture turns dark. Normal brightness has to be switched on area by area with priority bits. Ranger-X uses this: a column of transparent high-priority tiles lights up everything that passes behind it [GENVDP §16].

One exception: in sprites, colour 14 of palettes 0, 1 and 2 is never shadowed. GENVDP calls it a probable hardware bug, and PicoDrive reproduces it [GENVDP §16; PICODRIVE, pico/draw.c].

### Operator sprites

Two sprite colours do not draw anything. Instead they change the brightness of what lies underneath [MD-SWM §2.11]:

| Sprite pixel | Effect on the pixel below |
|--------------|---------------------------|
| Palette 3, colour 14 (CRAM entry `$3E`) | Highlight: normal → bright, or shadowed → normal |
| Palette 3, colour 15 (CRAM entry `$3F`) | Shadow: normal → dark; already dark stays dark |

Sources: [MD-SWM §2.11; MD-TO pp.61, 68; ACC-SDS p.23; PICODRIVE, pico/draw.c] <span class="tag manual">manual</span>. GENVDP gives these two colours the other way round; it is the only source that does, and every emulator follows the manuals ([discrepancy 14](../appendices/discrepancies.md)). What the CRAM entries `$3E` and `$3F` contain makes no difference to the effect [GENVDP §16].

Operators act on the planes and backdrop under them, and their own priority bit still counts: a low-priority operator sprite cannot darken a high-priority tile [MD-SWM §2.11]. Typical uses are a round shadow under a character, a spotlight, or darkening the playfield behind a pause menu with one large sprite.

Because both colours belong to palette 3, a game that uses operators gives up two colours of that palette for sprites. Planes can still use them normally.

## Interlace

Register 12 bits 2-1 select the scan mode [MD-SWM §2.13; GENVDP §17]:

| LSM1, LSM0 | Mode | Picture |
|------------|------|---------|
| `00` | No interlace | 224 (or 240) lines, the same lines every frame |
| `01` | Interlace | Alternate frames are drawn half a line apart, with the same picture in both |
| `11` | Interlace, double resolution ("mode 2") | 448 (or 480) lines: alternate frames show alternate lines of a taller picture |
| `10` | Not allowed | GENVDP: same as no interlace |

GENVDP reports that a change to these bits takes effect only outside the active display [GENVDP §17]. The status register's ODD bit tells which frame of the pair is being shown [MD-SWM §2.4].

Interlace mode 2 changes most of the VDP's units [MD-SWM §2.8, §2.10, §2.13; GENVDP §5, §13]:

- **Tiles are 8 × 16 pixels**, 64 bytes each. Bit 0 of a tile number is ignored, so tile numbers effectively count in 64-byte steps, and VRAM holds half as many tiles.
- **Sprites** are twice as tall. Their y is 10 bits, and the screen starts at y = 256.
- **Vertical scroll** values are 11 bits.
- **The H/V counter's** line byte puts line bit 8 in place of bit 0.

How the horizontal scroll table works in mode 2 is not documented. A table with one entry per line would need twice the room [GENVDP §13].

Sega warns that interlace can blur badly in the vertical direction on some displays [MD-SWM §2.13]. Mode 1 shows the same picture as normal mode, only interlaced. Mode 2 is the only way to get 448 lines out of the VDP. It doubles the tile memory each screen needs, and each line is refreshed only 30 times a second.

## Palette effects in practice

Colours are 3 bits per component, so fades have at most 8 steps. Aerobiz shows three ways to make the most of them, and one way to avoid needing a palette at all.

**Fade by subtraction** [AB-DISASM, FadePalette.asm]. To fade to black over levels L = 7 down to 0, each component *c* becomes max(0, *c* − (7 − L)). There is no multiply, and the fade takes exactly 8 steps. Dim components reach zero first, so colours drift slightly in hue as they darken. The routine unpacks each colour with the masks `$0E00`, `$00E0` and `$000E`, works on all 64 colours in a buffer on the stack, and uploads the result.

**Cross-fade that arrives together** [AB-DISASM, RenderColorTileset.asm]. To fade from one palette to another in 8 steps, each component moves by at most 1 per step. Components that must fall start falling at once. A component that must rise waits until its target is greater than 7 − step, so every rising component reaches its target on the last step, without any division.

**Shimmer from a moving window** [AB-DISASM, InitAnimTable.asm, UpdateAnimTimer.asm]. The boot logo's colours 2-12 are an 11-colour window into a 31-entry gradient that runs bright, dark, bright. Every two frames the window moves by one entry, and the vertical blank handler copies it into CRAM with the command `$C0040000` (CRAM address 4, colour 2).

**Recolour the tiles instead** [AB-DISASM, ApplyPaletteMask.asm]. To show the same graphics in each player's colour without spending a palette per player, Aerobiz changes the tile data before uploading it. Every 4-bit pixel equal to one colour index is replaced with another, one nibble at a time.

Palette animation by DMA is in [DMA](vdp-dma.md#dma-in-a-real-game).

## Open questions

- Measure the output levels of a few console revisions for normal, shadow and highlight, and publish a conversion table.
- What does a highlight operator do over a high-priority tile?
- How do the horizontal scroll table, sprites and VSRAM behave in interlace mode 2?

## Sources

- [MD-SWM](../appendices/bibliography.md#md-swm): §2.11 priority and shadow/highlight, §2.12 colour palette, §2.13 interlace, §2.8 and §2.10 interlace effects on tiles and sprites
- [MD-TO](../appendices/bibliography.md#md-to): pp.61 and 68, the highlight and shadow operators
- [ACC-SDS](../appendices/bibliography.md#acc-sds): p.23, shadow/highlight mode
- [GENVDP](../appendices/bibliography.md#genvdp): §9 CRAM, §13, §14 priority, §16 shadow/highlight, §17 registers 0 and 12
- [PICODRIVE](../appendices/bibliography.md#picodrive): `pico/draw.c` (output levels, operator colours), `pico/videoport.c` (CRAM write timing)
- [AB-DISASM](../appendices/bibliography.md#ab-disasm): FadePalette, RenderColorTileset, InitAnimTable, UpdateAnimTimer, ApplyPaletteMask, VInt_Sub1, DrawBox
