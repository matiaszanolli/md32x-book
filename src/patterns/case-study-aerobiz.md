# Case study: porting Aerobiz Supersonic to the 32X

Aerobiz Ultimate takes a finished Mega Drive game, Koei's *Aerobiz Supersonic* (1994, 1 MB), and moves it onto a 32X cartridge. It keeps the whole game and adds what the 32X can do. It is this book's worked example of a Mega Drive to 32X port. Both ends of the port are open to read. The original is a byte-identical disassembly that rebuilds the retail ROM [AB-DISASM]. The port is a fork of that disassembly, whose design, roadmap and history record every step, including the wrong turns [AU-NOTES].

This chapter follows the port in the order it was done. Each step says what the original did, what had to change, how the change was checked, and where the rest of this book covers the hardware behind it. Nothing here has run on a console yet. The port has been tested in PicoDrive, extended for the purpose, and in Ares, so every result is tagged <span class="tag emulator">emulator</span>.

## The game before the port

Five facts about the original shaped every later decision. Look for the same five in any game you plan to port.

| | Aerobiz Supersonic | Why it matters for the port |
|---|---|---|
| Where hardware is touched | Almost all of it through one dispatcher, `GameCommand` at `$000D64`: 47 handlers (VDP registers, DMA, sprites, input, the Z80 mailbox, frame waits), called from 306 places. Every memory-to-VRAM DMA source is programmed in one routine, `ConfigVDPDMA` | Few choke points means few places to hook. The port never had to touch the 306 callers |
| How it addresses its ROM | As `$000000-$0FFFFF`, everywhere: in code, in pointer tables, and in hand-encoded `jsr` instructions written as data words | Every one of those addresses is wrong on a 32X, where the 68000 sees the cartridge at `$880000` and `$900000` |
| Display mode | H32, 256 pixels wide, after the boot screens | The 32X layer requires H40 while it is visible |
| Free memory | None that is safe. Screens that never run together share one scratch area at `$FF1804` for decompressed graphics, the map canvas, the save image and scroll tables | 32X code cannot simply claim work RAM |
| Where its time goes | The 68000 idles 69.5% of play. The LZ decompressor is the largest single cost at 11.93%. The pauses players notice are screen loads, not thinking | The work worth moving to an SH-2 is graphics, not AI |

Sources: [AB-DISASM, GameCommand.asm, ConfigVDPDMA.asm, analysis/RAM_MAP.md]; [AU-NOTES, ROADMAP U-003, U-045; PORT_ARCHITECTURE §2]. The profile came from sampling the 68000's program counter once per frame over a complete 20-year game, 418,549 frames. Sampling at the same point in each frame catches a frame-locked loop waiting, so the idle figure is biased high; the ranking of the busy routines is what the decision rests on <span class="tag emulator">emulator</span> [AU-NOTES, ROADMAP U-045].

### Why this game suits the 32X

A turn-based strategy game is a forgiving first port. Nothing depends on cycle-exact timing, the 68000 has time to spare, and the game's weak points are visual: its world map is built from tiles, so routes are drawn in tile-sized steps and aircraft jump a tile at a time. The 32X adds things without taking any away. The 68000 still runs the game and the Mega Drive VDP, so the port can keep every line of game logic and spend the SH-2s and the bitmap layer on the map and the art [AU-NOTES, README; PORT_ARCHITECTURE §1].

## The plan: keep the game, add the 32X

| Milestone | Goal | State |
|-----------|------|-------|
| M0 | The fork still builds the original ROM byte for byte | Done |
| M1 | The 32X cartridge boots, both SH-2s report in, the layer stays blank | Done |
| M2 | The game, moved to `$900000`, reaches its title screen | Done, and audited |
| M3 | The whole game plays on the 32X, layer blank | Done: a complete 20-year game, save and load |
| M4 | The world map on the 32X layer | Working in a separate build; not in the shipping cartridge |
| M5 | The measured hot path on an SH-2 | LZ decompression ships |
| M6 | PWM sound | Not started |
| M7 | High-colour art, text and comfort features | Title art ships; the text engine is demonstrated |
| M8 | More scenarios, aircraft and airports | The reason for the port; under way |

Source: [AU-NOTES, PORT_ARCHITECTURE §6; ROADMAP, state of play]. M3 is the gate: before it everything is plumbing, after it everything is added on top of a game that already works.

## Step 1: a cartridge that boots

The cartridge is 2 MB, laid out so that everything new stays visible whichever bank is selected [AU-NOTES, PORT_ARCHITECTURE §2]:

| Cartridge | Holds | The 68000 sees it at |
|-----------|-------|----------------------|
| `$000000-$0003EF` | Vectors, header, jump table, 32X user header | `$880000` |
| `$0003F0-$0007FF` | Sega's initial program, copied from another cartridge at build time and never committed | `$8803F0` |
| `$000800-$07FFFF` | The port's own 68000 code, the SH-2 program and new data | `$880800-$8FFFFF`, always |
| `$100000-$1FFFFF` | The original 1 MB game, unchanged in layout | `$900000-$9FFFFF`, as bank 1 |

The first build did not boot, for three reasons, all misreadings of the manual rather than coding slips: the copied initial program was too short, the port's own code was placed inside it, and the boot handshake waited on the wrong communication word [AU-NOTES, ROADMAP U-001; HISTORY]. Each of the three now has its rule in this book: [Boot](../32x/boot.md#the-verdict) and [32X header and security code](../howto/32x-header.md).

## Step 2: moving the game into bank 1

Placing the original image at cartridge `$100000` and selecting bank 1 puts the whole game at `$900000-$9FFFFF`. Moving it is then a matter of adding one constant, `ROM_BASE` = `$900000`, to every address. Finding every address took three days and two real bugs. [Moving a Mega Drive game into a bank](../howto/large-cartridges.md#moving-a-mega-drive-game-into-a-bank) gives the method. The numbers:

- **3,872 address sites**, against a first estimate of about 330 and a first scan of 2,886. The biggest miss: 971 `jsr` instructions written out as data words, invisible to any pattern that looks for an instruction [AU-NOTES, ROADMAP U-010].
- **899 doubtful constants**, values that merely fall in the ROM's range. The encoding excluded 336, because no byte or word immediate can hold a `$9xxxxx` address. The rest came down to 93 distinct values, each traced through the code; none was an address. But two doubtful sites had already been real addresses, and until they were fixed every city in the game had no airport slots [AU-NOTES, ROADMAP U-011].
- **Pointers stored in data.** The first build to reach the title screen showed a screen full of `$FF`: the code that loads a pointer had been moved, but the pointer it loaded had not, and it pointed into padding. 567 such pointers were found by reading the code that uses them, not by looking at the data [AU-NOTES, ROADMAP U-013].
- **Data mistaken for pointers.** The same passes turned 41 values into addresses that were really palettes, index tables and tile pixels. That gave the green SEGA screen and the damaged logo. An audit of the remaining 1,817 found no others, by checking that every table of pointers is read a longword at a time [AU-NOTES, ROADMAP U-014].

The result is checkable in one figure. The game half is the same length as the original and differs from it in 5,793 bytes, every one an isolated byte where an address's high byte went from `$0x` to `$9x`. No run of changed bytes means nothing moved [AU-NOTES, ROADMAP U-012].

### The rule that follows: the layout may not change

Every address is written as `ROM_BASE` plus its *original* offset. If a 32X-only change added a single byte to shared code, everything after it would move while the addresses still named the old offsets, and the original build, where `ROM_BASE` is 0, would not notice. So 32X-only code can go in three places only [AU-NOTES, PORT_ARCHITECTURE §2]:

1. **The new code in the fixed window**, which is not part of the moved image and can be any size.
2. **Work RAM below the stack pointer.** Nothing else is reliably free. Two regions that a reference scan called unused were filled with a marker and then overwritten by the game, all 896 and 4,096 bytes of them: the scan saw fixed addresses and missed writes through computed ones.
3. **Patches of exactly the original size** in shared code, assembled only for the 32X. A six-byte `jsr` replaced by another six-byte `jsr` is the typical one.

## Step 3: DMA from the cartridge

The original loads its graphics by DMA straight from ROM. On a 32X the Mega Drive VDP cannot fetch from the `$900000` window, and the 68000 has to set RV for the length of each transfer, which brings its own rules: interrupts off, the trigger running from RAM, and the SH-2s kept off the cartridge ([DMA on the 32X](../megadrive/vdp-dma.md#dma-on-the-32x)).

The first idea was a second constant, moving DMA sources to their cartridge offsets instead of `$900000`. It was dropped, for a reason worth keeping: the same pointer is often read by the 68000 too, which needs the `$900000` form, and one value cannot be both. Working out which pointers feed DMA alone would need tracing values through the wrappers that pass them on. Instead the conversion happens at the one routine that programs a DMA source, at the moment it is used [AU-NOTES, PORT_ARCHITECTURE §2.1]:

- **The hook.** That routine already ends with a hand-encoded six-byte `jsr` to a trigger in work RAM. The 32X build points those six bytes at a larger routine in the fixed window. No caller changes.
- **The window.** For a cartridge source, the routine converts the address, reprograms the source registers, and copies a short sequence to the stack. That sequence sets RV, starts the transfer, waits for it and clears RV, all from RAM.

Over 3,000 frames the routine ran 616 times, 31 of them from the cartridge, and none in the first 900 frames. An earlier sample of just those 900 frames had concluded the game never DMAs from ROM [AU-NOTES, ROADMAP U-020]. Then the whole game ran: setup, turns, save and load, and a complete 20-year game of 900,000 frames, with no exception on either build [AU-NOTES, ROADMAP U-021].

## Step 4: one source, two builds

`make genesis` must still produce the retail ROM, checked by MD5 on every build. That is the port's main safety net: any change to shared code that alters one byte of the original is a bug [AU-NOTES, PORT_ARCHITECTURE §3]. Its blind spot is the one shown above, a wrong rewrite that is invisible when `ROM_BASE` is 0. So the two audits from step 2 are kept as tools that fail on any new unjudged site. They are rerun after any change that touches an address.

Comparing the two builds while they run takes care:

- **Compare work RAM, not pictures.** The Mega Drive build is 256 pixels wide, the 32X composite 320, so frame hashes never agree. 68000 work RAM does not depend on the width [AU-NOTES, ROADMAP U-021].
- **Don't compare two long AI games.** Moving the setup button presses by one frame changed the original's own game length from 433,515 frames to 172,286, so the 32X's few frames of start-up reseed the game by themselves. Use runs with no input, or short ones with identical input [AU-NOTES, ROADMAP U-021].
- **Match frames by content.** When builds drift apart in time, pair frames by what is on screen, not by frame number ([Testing in emulators](../howto/emulator-testing.md)).

Ares found what PicoDrive had hidden. It maps the cartridge as the manual says, so the game's region check, which reads the header at `$0001F0`, found nothing and showed the game's lockout screen [AU-NOTES, ROADMAP, state of play].

## Step 5: measure before moving work

The original plan put the AI and the economy on an SH-2, because the pause between turns felt slow. The profile above said there was nothing to gain: no AI or economy routine is in the top 25 [AU-NOTES, ROADMAP U-045]. Two more measurements decided how work should cross:

- **A call costs more than most routines.** One round trip from the 68000 to the SH-2 and back through the communication ports costs about 560 68000 clocks, whatever the job. The first test subject, the game's 32-bit divide, works on the SH-2 and matches the original on every test value, but its slow path is never called in play, because the game never divides by `$10000` or more. Work has to be sent in batches, not call by call [AU-NOTES, ROADMAP U-039, U-044; PORT_ARCHITECTURE §4.2].
- **The hot path moved.** LZ decompression now runs on the Master SH-2, 14 times faster for the decoding alone and about 8 times for a whole job, and is in the shipping cartridge ([Moving decompression to an SH-2](../techniques/compression.md#moving-decompression-to-an-sh-2)). The longest screen-loading stall went from 74-76 frames to about 8-10, by the project's own frame counts [AU-NOTES, ROADMAP U-046].

Each moved routine keeps its 68000 version, chosen at assembly time, so the two can be compared, and a control build (`32x-nolz`) leaves decompression on the 68000.

## Step 6: the 32X layer

### The display mode

The original runs in H32, and in H32 the two layers sit at scales 1.25 times apart, because the 32X always takes the H40 pixel clock. So the map screen switches to H40 while the layer is up, and everything else stays H32 with the layer blank ([The display modes must match](../32x/compositing.md#the-display-modes-must-match)) [AU-NOTES, ROADMAP U-003]. A 32-cell plane shown in a 40-cell screen repeats its first 64 pixels at the right; one palette entry with the through bit hides the repeat ([Masks](../32x/compositing.md#masks-one-entry-that-reverses-the-default)).

The obvious next step, widening the map's Mega Drive plane to 64 cells, was blocked. The game keeps live data in the plane's off-screen rows at fixed VRAM addresses, and one DMA writes 192 bytes there at an absolute address the plane cannot move. Changing the plane's shape slid the visible screen onto that data. So the map reaches the screen through the 32X frame buffer instead [AU-NOTES, PORT_ARCHITECTURE §5.6].

### The map

The SH-2 draws the world map in packed-pixel mode, 256 colours. Direct colour would need 143,360 bytes for 320 × 224, more than a frame buffer holds [AU-NOTES, PORT_ARCHITECTURE §4.1].

- **Zoom.** Vertical scaling is nearly free: display lines that land on the same source row share one line in the frame buffer, so only the line table changes ([Scaling the whole layer](../techniques/2d-effects.md#scaling-the-whole-layer-the-line-table-does-the-vertical-half)). Horizontal scaling is a per-pixel loop. On the Master alone, a full-screen blit took 2.13 frames at 1×, 1.06 at 2× and 0.53 at 4× in PicoDrive. Ares, which models the SH-2's memory timing more closely, gave 2-3 frames for the 1× case [AU-NOTES, ROADMAP U-035, U-090].
- **Rotation.** A rotated picture cannot share lines, so it costs 5.75 frames full-screen: an effect for part of the screen, not all of it. Its one shipping use is the SEGA logo, which spins and zooms on the 32X layer and lands exactly on the Mega Drive logo ([Handing the screen from one layer to the other](../32x/compositing.md#handing-the-screen-from-one-layer-to-the-other)) [AU-NOTES, ROADMAP U-037].
- **Level of detail.** The 89 cities are numbered with the 32 major airports first, so "draw this airport at this zoom?" is one comparison of the city number. The 57 secondary airports appear only when a source pixel covers at least two screen pixels. No new data was needed [AU-NOTES, ROADMAP U-077].

### The map inside the game

In the build that puts the map into play (`32x-mapscreen`), the layer follows the game's screen number from the vertical interrupt. It is drawn before it is shown and leaves under a fade ([Switching the layer on and off](layering.md#switching-the-layer-on-and-off)). Two things the game does to its Mega Drive map had to reach the layer too:

- **Fades and tints.** 32X palette entries 16-31 copy the game's CRAM line 1 at the moment the game writes it ([Following the Mega Drive's palette](../32x/compositing.md#following-the-mega-drives-palette)).
- **Edited tiles.** The game draws route lines into the map's tiles before uploading them, so the SH-2 must draw what the game uploads, not the clean picture in the cartridge. Both upload paths are hooked ([Hooking the choke point](streaming.md#hooking-the-choke-point)). A per-frame comparison with what the original would show matched 113 of 114 comparable frames. The last case is a tile set the game uploads once per session and the layer wipes on every visit; it needs the 68000 to read the tiles back out of VRAM [AU-NOTES, PORT_ARCHITECTURE §4.1, §5.7].

One 256-entry palette serves every user of the layer, so the port fixed a budget before adding more: entry 0 for the mask, 16-31 for the copied CRAM line, 64-253 for the current screen's art, 254-255 for text ([One palette, many users](../32x/compositing.md#one-palette-many-users)).

### Text and art

The title screen is the project's own art, reduced to 253 colours at entries 1-253, and it ships [AU-NOTES, ROADMAP U-061, U-090]. A text engine for the layer is demonstrated in its own build:

- **Fonts.** A tool turns a desktop font into proportional 1-bit glyphs.
- **Drawing.** The SH-2 measures, wraps and draws text with ink in entry 254 and paper in 255, never 0, because a byte write of 0 to the frame buffer is skipped ([The normal and overwrite images](../32x/vdp.md#the-normal-and-overwrite-images)).
- **Palette loading.** Palette writes wait for PEN, a word at a time [AU-NOTES, ROADMAP U-090].

## Step 7: sound

The original's 5,458-byte Z80 driver plays the music and effects, and the port keeps it unchanged. PWM is planned as an addition on an SH-2, keeping in mind Sega's rule that the CPU feeding PWM must not use auto-request DMA. None of it has been built yet [AU-NOTES, PORT_ARCHITECTURE §4.3; ROADMAP M6]. [Audio across PWM, FM and PSG](audio.md) shows how the shipped games split sound between the two systems.

## What shipped, and what was believed and turned out wrong

The shipping cartridge gives the SH-2s four jobs: the SEGA logo, LZ decompression, the divide that is never called, and the title art. The map in play, the zoom with route arcs and airport tiers, and the affine demo are each built and measured in their own build, but not shipped [AU-NOTES, ROADMAP, state of play].

The port's roadmap keeps a list of the measurements that overturned its own earlier statements. Most are general lessons:

| Believed | Found |
|----------|-------|
| AI and economy are slow; move them to an SH-2 | The 68000 idles 69.5% of the time; the cost is decompression and screen loading |
| Any routine can be handed to an SH-2 call by call | A round trip costs about 560 68000 clocks; send batches |
| The map screen can stay in H32 | The layers are 1.25 times apart in H32; the manual also requires H40 |
| The plane can be widened at one call site | The game keeps live data in off-screen plane rows |
| Matching screens prove the move to `$900000` is finished | 41 data values had been rewritten as pointers, invisible to the byte-identical check |
| The doubtful constants are paperwork | Two were real addresses, and every city had lost its airport slots |
| The emulator's SH-2 timings are measurements | It modelled no cache and no memory latency; they were instruction counts until a model was added |
| The game never DMAs from ROM | It does, after the first 900 frames |
| `$0001F0` is readable | Not while RV = 0; only Ares showed it |

Sources: [AU-NOTES, ROADMAP, state of play; U-020; U-013].

## What still needs a console

The project's hardware checklist lists what no emulator can settle. Among them: whether the `$880000` and `$900000` windows really disappear while RV = 1; whether the Mega Drive backdrop is transparent under the layer in H32; what the map zoom costs with a real cache and real SDRAM timing; and whether the SEGA logo hand-off is seamless on a real TV [AU-NOTES, HARDWARE_TESTS items 1-9]. [Testing on real hardware](../howto/real-hardware.md) describes how to design such tests.

## What to take away

- Before porting, find the game's choke points, its display mode, its free memory and its profile. They decide the plan.
- Put the original image in one bank and add one constant. Then audit every address, both ways: numbers that are addresses, and addresses that are numbers.
- Keep the original build byte-identical as a test, and know what it cannot see.
- Add 32X code only where it cannot move the original's layout: in the fixed window, below the stack, or in patches of exactly the same size.
- Hook the one routine every caller goes through, not the callers.
- Measure before moving work to an SH-2, and send it in batches.
- Use the 32X layer where the Mega Drive is weakest, and make it follow the game's own fades, tiles and screens.

## Open questions

- Every result here is from PicoDrive and Ares. The project's hardware checklist will fill in the console results once the cartridge runs on a 32X.
- How much do the SH-2's reads from the cartridge stall while the 68000 holds RV for a DMA, in the shipping build?
- Can the map's tiles be read back from VRAM fast enough to close the last mismatch?

## Sources

- [AB-DISASM](../appendices/bibliography.md#ab-disasm): README; disasm/modules/68k/game/GameCommand.asm; vdp/ConfigVDPDMA.asm; analysis/RAM_MAP.md
- [AU-NOTES](../appendices/bibliography.md#au-notes): README; PORT_ARCHITECTURE §1-§6; ROADMAP (state of play, U-001, U-003, U-010-U-014, U-020, U-021, U-035, U-037, U-039, U-044-U-046, U-061, U-077, U-090, M6); HARDWARE_TESTS; HISTORY
- [32X-HWM](../appendices/bibliography.md#32x-hwm): §3.1 cartridge mapping, §3.2.1 bank set register, §3.3 display modes
