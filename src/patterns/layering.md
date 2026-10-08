# Using both video chips at once

A 32X game has two video chips, and the Mega Drive's keeps working while the SH-2s draw. Whatever the Mega Drive VDP draws costs the SH-2s nothing. Every shipped 32X game but one puts that to use. [Mixing 32X and Mega Drive graphics](../32x/compositing.md) explains how the two pictures are combined pixel by pixel. This page is about the design choice on top of that: what to give each chip, the one depth rule that limits the choice, what the shipped games did, and how to switch the 32X layer on and off cleanly.

## What each chip is good at

| | Mega Drive VDP | 32X VDP |
|---|---|---|
| Picture made of | Two scrolling tile planes, a window and up to 80 sprites | A bitmap the SH-2s write |
| Colours on screen | 61, from 512 | 256 from 32,768, or any of 32,768 in direct colour |
| Cost per picture once set up | Scrolling is a few register or table writes. Only what changes needs updating | Every pixel that changes must be written again, by a CPU or an auto fill |
| Limits | 64 KB of VRAM; about 7 KB of DMA per vertical blank; tiles on an 8-pixel grid; 20 sprites per line | SH-2 time and frame buffer bus time; a clear alone takes over a quarter of a frame |
| Good at | Large scrolling backgrounds, parallax, text, HUDs, anything built from repeated tiles | Many colours, scaling, rotation, polygons, large animation frames |

Sources: [The Mega Drive VDP](../megadrive/vdp.md); [How much fits in a frame](../megadrive/vdp-dma.md#how-much-fits-in-a-frame); [The 32X VDP](../32x/vdp.md); [What one frame holds](60fps.md#what-one-frame-holds).

The cost row is the argument for layering. A Mega Drive background, once in VRAM, scrolls for the price of a few register writes. The same background on the 32X would have to be drawn again in every picture in which it moves.

## The depth rule: in front of everything, or behind it

The Mega Drive VDP sorts its own planes and sprites by their priority bits and hands the mixer one finished picture. The mixer then decides each pixel between that picture and the 32X's ([The rule for each pixel](../32x/compositing.md#the-rule-for-each-pixel)). It follows that every 32X pixel is either in front of the whole Mega Drive picture at that point, or behind everything the Mega Drive draws there and visible only where the Mega Drive shows its backdrop.

So the 32X layer has exactly two depths relative to the Mega Drive:

- **A 32X object cannot sit between two Mega Drive layers.** It cannot pass behind plane A and in front of plane B, or between a Mega Drive sprite and a plane.
- **Each colour picks its depth.** In packed-pixel mode the through bit belongs to the palette entry, so a colour is either a "front" colour or a "back" colour. To show the same colour at both depths, put it in the palette twice, once with the bit and once without. In direct colour each pixel carries its own bit ([The rule for each pixel](../32x/compositing.md#the-rule-for-each-pixel)).
- **Whatever must overlap in both directions goes on one chip.** Mortal Kombat II draws foreground objects such as a hanging chain on the 32X, because they must cover the fighters, and the fighters must cover the Mega Drive arena ([Mega Drive behind](../32x/compositing.md#mega-drive-behind-32x-objects-over-a-tile-background)) [MK2, frame buffer read in PicoDrive].

## What the shipped games put where

| Game | Mega Drive layer | 32X layer | Which is in front |
|------|------------------|-----------|-------------------|
| Star Wars Arcade | Cockpit, score, timer | The space scene | Mega Drive (PRI 0, no through bits) |
| After Burner Complete | The player's jet, HUD, crosshair | Sky, sea and everything else | Mega Drive (PRI 0, no through bits) |
| Mortal Kombat II | Arena, energy bars | Fighters and foreground objects, on a field of entry 0 | 32X (PRI 0; every entry but 0 has the through bit) |
| Knuckles' Chaotix | The level | Characters and some objects, on a field of entry 0 | 32X (PRI 1; entry 0 and 122 others have the through bit) |
| Motocross Championship | Nothing visible | Everything, HUD included | — |

Sources: [How games split the work](../32x/compositing.md#how-games-split-the-work) for the first three; [CHAOTIX, bitmap mode register `$8081`, palette and frame buffer read in PicoDrive at attract frames 4300 and 4400]; [MCX, frame buffer dumps; notes] <span class="tag emulator">emulator</span>.

Three designs, then:

- **Mega Drive in front, 32X filling the screen behind it.** Star Wars Arcade and After Burner Complete draw a full 3D or scaled scene on the 32X and lay a Mega Drive cockpit or HUD over it. The HUD costs the SH-2s nothing, and text stays in the Mega Drive's font. The price: the 32X must cover every pixel in every picture, because whatever it leaves shows through. After Burner Complete makes that cheap by drawing its sky and sea as auto fills, which double as the clear ([Getting the frame time down](60fps.md#draw-less)).
- **32X objects in front of a Mega Drive world.** Mortal Kombat II and Chaotix leave the scrolling scenery to the Mega Drive and draw only the characters on the 32X, on a field of one colour that sits behind the Mega Drive picture. They reach the same picture by opposite settings: Mortal Kombat II has PRI 0 and through bits on the character colours, Chaotix PRI 1 and the through bit on the background colour. The field still has to be cleared for every picture, but only with auto fills of one value. Chaotix gives that job to its Slave, so its Master draws while the clear runs ([Living with bus contention](bus.md#what-each-program-did)). Mortal Kombat II does the clear on its Master and waits for it ([What one frame holds](60fps.md#what-one-frame-holds)).
- **32X only.** Motocross Championship puts its whole presentation on the 32X in direct colour, HUD included, and leaves the Mega Drive planes empty [MCX, frame buffer dumps]. It pays for every pixel: its Master draws into a staging buffer and copies the finished picture across, and the game shows a new picture every fourth frame ([Drawing off screen and copying](streaming.md#drawing-off-screen-and-copying-motocross-championship)).

## Sprites over and under the 32X layer

Mega Drive sprites are part of the Mega Drive picture, so they take its side of the depth rule:

- **Over the 32X**, where the 32X pixel is a back colour. After Burner Complete's jet is a Mega Drive object in front of the whole 32X scene, and since it is always on screen and always the same size, it is the one object the SH-2s never draw ([Mega Drive in front](../32x/compositing.md#mega-drive-in-front-huds-and-cockpits)).
- **Under the 32X**, where the 32X pixel is a front colour. In the Mortal Kombat II and Chaotix arrangement, any Mega Drive sprite passes behind the 32X characters.
- **Both at once**, by colour. A Mega Drive sprite passes in front of 32X pixels drawn in back colours and behind those in front colours. A 32X object drawn in front colours overlaps Mega Drive sprites; one in back colours is overlapped by them.

The Mega Drive's limits still apply: 20 sprites per line in the 320-pixel mode, which the 32X layer requires while it is visible ([The display modes must match](../32x/compositing.md#the-display-modes-must-match)).

## Switching the layer on and off

A game that shows the 32X layer on some screens only has to bring it in and take it out without a visible jump. The Aerobiz Ultimate project shows its world map on the 32X while the rest of the game stays on the Mega Drive. Its 68000 decides everything from the vertical interrupt, following the game's own screen number <span class="tag emulator">emulator</span> [AU-NOTES, disasm/32x/map_screen.asm]:

1. **Switch on.** When the screen number says "world map", the 68000 posts a new generation number and gives the frame buffer to the SH-2 (FM = 1). The layer stays blank while the SH-2 draws the map into both frame buffers.
2. **Show.** The SH-2 answers with the same generation number. A stale "drawn" left over from an earlier visit therefore cannot be mistaken for this one. From the next vertical interrupt the 68000 takes the frame buffer back, copies the game's palette line into the 32X palette, switches the Mega Drive to the 320-pixel mode, and shows the layer with PRI 0.
3. **Switch off.** The game changes its screen number before the old screen fades out, so the layer stays up until the copied palette line has faded to black. It goes at once if that line changes to anything else, and after 48 frames regardless. Then the layer is blanked and the game's own display mode is put back.

Mega Drive cells under the map are filled with tile 0, which is fully transparent, so the 32X shows through where the game's own map was. A layer that goes away exactly at the end of a fade, or under an identical Mega Drive picture ([Handing the screen from one layer to the other](../32x/compositing.md#handing-the-screen-from-one-layer-to-the-other)), cannot be seen to go.

## What to take away

- Give the Mega Drive VDP everything built from tiles that scrolls or stays still: backgrounds, HUDs, text. It costs the SH-2s nothing per frame.
- Give the 32X what needs colours, scaling or free shapes, and keep its area small if you can.
- A 32X pixel is either in front of the whole Mega Drive picture or behind it. Choose each colour's depth with its through bit, and put anything that must overlap both ways on one chip.
- If the 32X fills the screen, make the clear part of the drawing (fills as backgrounds). If it draws objects over a Mega Drive world, clear with auto fills, on the CPU that is not drawing.
- Bring the layer in only once both frame buffers hold a finished picture, and take it out where the change cannot be seen.

## Open questions

- What do Chaotix's Mega Drive planes hold during play, and does its 32X layer ever cover them with front colours across the whole screen, for example on special stages?
- Does Motocross Championship use the Mega Drive VDP at all once its game is running?
- Can a PRI change from an H interrupt put the 32X in front on part of the screen only, on a console ([Open questions](../32x/compositing.md#open-questions))?

## Sources

- [CHAOTIX](../appendices/bibliography.md#chaotix): bitmap mode register, palette and frame buffer read in PicoDrive; SH-2 code at `0x0600032C`, `0x06004B12`
- [MK2](../appendices/bibliography.md#mk2), [SWA](../appendices/bibliography.md#swa), [AB32X](../appendices/bibliography.md#ab32x): as in [Mixing 32X and Mega Drive graphics](../32x/compositing.md#sources)
- [MCX](../appendices/bibliography.md#mcx): frame buffer dumps; SH-2 code at `0x020295B0`
- [AU-NOTES](../appendices/bibliography.md#au-notes): disasm/32x/map_screen.asm
- [32X-HWM](../appendices/bibliography.md#32x-hwm): §3.3 priority, display mode possible combinations
