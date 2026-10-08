# Case study: After Burner Complete

*After Burner Complete* (Sega, October 1994) brings Sega's 1987 arcade jet game to the 32X on a 2 MB cartridge. The arcade original has no polygons: it builds its 3D world from flat colour and hundreds of scaled sprites. The 32X version keeps that approach, and so it shows a different kind of 3D from Star Wars Arcade's polygons or Virtua Racing's. Sega published it, but did not write it: the cartridge's credits say the game was "reprogrammed by Rutubo Games", an outside studio that also converted Space Harrier for the 32X [AB32X, credits at cartridge `$01C25C`; 32X-ROMSET, Space Harrier, `$041F06`; WP-32XLIST]. The two games share their reset code, which avoids one of the two slips that many games copied from Sega's sample and keeps the other ([Sega's sample code in the games](../appendices/sample-code.md)).

It is not, however, an efficient program. By PicoDrive's measure each of the three CPUs spends between about two-fifths and two-thirds of its time waiting, and the game runs at 30 pictures a second, half the rate that two retrospectives give for the arcade original. Like the Virtua Racing Deluxe project's account of that game ([Case study: Virtua Racing Deluxe](case-study-vr.md)), it shows a design that works and ships but leaves much of the machine unused. The two share their reset recovery and nothing else that was compared: not the interrupt dispatcher, the start-up code or the way the 68000 sends commands ([How much else the three share](../appendices/sample-code.md#how-much-else-the-three-share)). So the idle time is not one inherited design; each team arrived at its own. This chapter follows one picture through the whole machine, then measures what is left on the table. The details of each technique are in the chapters it links to.

## How far the evidence goes

Everything here comes from the retail dump, which is clean: its header checksum matches, and its start-up code is Sega's standard initial program [AB32X]. The code was read by disassembly. The game was also run headless in PicoDrive, to watch counters and lists and to profile where each CPU spends its time.

That gives two levels of confidence. What the code does is certain: it shipped, and it ran on consoles. How long it takes is PicoDrive's account, tagged <span class="tag emulator">emulator</span> below. PicoDrive does not model the SH-2 caches or bus contention, shortens polling loops, and in one case below disagrees with the manual's timing by a factor of about three. Nothing here has been timed on a console.

## How the game divides the work

| CPU | Job |
|-----|-----|
| 68000 | The game: control, enemies, collisions, stage scripts. The Mega Drive VDP draws the player's jet, the score and the crosshair in front of the 32X picture. Every object in the scene goes to the Master as a call. Sound requests go to the Z80 and to the Slave |
| Master SH-2 | All of the 32X picture: projects each object, sorts by depth, draws the sky and sea with auto fills and everything else as scaled sprites |
| Slave SH-2 | Sound only: a music sequencer and a 16-voice PWM mixer |

Sources: [AB32X, SH-2 code at `0x06002120` (Master start), `0x06000200` (Slave start), `0x06003890` (Master main loop); 68000 code at `$887348`-`$8873BC`]. The game draws 30 pictures a second, in play and on the title, by the Master's own count of pictures drawn, watched over 2,000 frames <span class="tag emulator">emulator</span> [AB32X, watch log].

The split is lopsided on purpose. One SH-2 does all the graphics and the other does nothing but sound, so the two never share data, never purge each other's lines, and never wait for each other ([Splitting work across three CPUs](cpu-split.md)). Neither changes its cache mode or uses DMA, and the 68000-to-SH-2 FIFO is never used [AB32X, start-up code at `0x06002120`, `0x06000200`].

## One picture, from game logic to the screen

**1. The 68000 calls the Master once per object.** For every enemy, cloud, tree, wave or explosion, the 68000 writes the object's position and shape into the communication ports, raises the Master's command interrupt, and spins until the answer comes back. The answer says whether the object is on screen and where. There are about 75 calls per picture in play, up to 87. The FIFO's address and length registers, which the game never uses for transfers, carry 13 extra bytes of parameters ([One call per object](../32x/communication.md#one-call-per-object)). It also sends lists of ready-made entries, one command each (command 1), with its own interrupts masked. Each waits until the Master's interrupt has taken the last one, and the Master appends the entry to its object list without projecting it [AB32X, 68000 code at `$89C6A8`-`$89C6EE`; SH-2 code at `0x060036FC`-`0x0600373A`].

**2. The Master projects inside the interrupt.** Command 15 divides by depth with a 16-step division (`$7FE0` / (*z* / 32 + 32), the + 32 keeping the divisor away from 0), scales with multiplies, and appends a 16-byte entry to an object list. There are three lists in rotation, so the 68000 fills one while the Master draws another ([Projection: dividing by depth](../techniques/software-3d.md#projection-dividing-by-depth)) [AB32X, SH-2 code at `0x0600257C`-`0x060025A8`].

**3. The Master sorts by depth.** Its main loop drops each entry into one of 256 buckets of 32 bytes, each with room for 30 entries, spilling into the next bucket when one is full. Walking the buckets gives the back-to-front order ([Bucket sorts](../techniques/software-3d.md#bucket-sorts)) [AB32X, SH-2 code at `0x06003B66`].

**4. The background is auto fills.** For each of the 224 lines, the Master reads a split column from a table and starts two hardware fills, sky colour to the left and sea or ground colour to the right. When the plane banks, the split moves along the lines and the horizon tilts. The fills also wipe out the old picture, so there is no separate clear. On the base landings a second routine draws a runway from per-line runs ([Flat colour and a tilting horizon](../techniques/roads-mode7.md#flat-colour-and-a-tilting-horizon-after-burner-complete); [A runway from runs](../techniques/roads-mode7.md#a-runway-from-runs)).

**5. Everything else is a scaled sprite.** In sorted order, each sprite is looked up in a cache of decoded images in SDRAM. On a miss, its run-length data is unpacked from the cartridge into the cache, which is a ring that evicts the oldest images in the way ([A cache of decoded sprites](../techniques/memory.md#a-cache-of-decoded-sprites); [Decoded once, into a cache](../techniques/compression.md#decoded-once-into-a-cache-after-burner-complete)). The scaler then draws it with four instructions per two pixels, in one of four modes: normal, mirrored, and two that double each pixel for nearby objects ([After Burner Complete's scaler](../techniques/2d-effects.md#after-burner-completes-scaler)). It writes through the overwrite image, so the hardware skips transparent pixels and the loop has no test for them ([The normal and overwrite images](../32x/vdp.md#the-normal-and-overwrite-images)). Up to 92 sprites a picture in play and 143 on the title screen, whose logo is a cluster of sprites turned by rotating their positions in 3D <span class="tag emulator">emulator</span>.

**6. The Master flips the frame buffer.** It asks for the swap, waits for the 68000's go-ahead for the next picture and sorts it. Only then does it wait for the swap to happen at vertical blank, before drawing again [AB32X, SH-2 code at `0x060038CE`-`0x06003966`].

The Mega Drive picture goes over the top: jet, score and crosshair are tiles and sprites on the Mega Drive VDP, in front of the 32X layer ([Using both video chips at once](layering.md)).

## Sound on its own CPU

The Slave runs a complete sound system: a music sequencer and 16 voices, each resampled with linear interpolation and panned in stereo, mixed at about 15.6 kHz. The mixer works ahead into a 64-sample ring, and the PWM interrupt only copies one ring entry per sample to both channels with a single longword write. The ring's read and write positions live in the user break controller's registers, three on-chip words that cost no bus cycles ([Mixing](../32x/pwm.md#mixing); [Cheap tricks in the mixers](audio.md#cheap-tricks-in-the-mixers)).

Requests reach it by command interrupt, so the Slave never polls. The 68000 collects each request from the Z80 and sends it to both drivers; FM and PSG parts play on the Mega Drive's chips, PWM parts on the Slave ([Audio across PWM, FM and PSG](audio.md)) [AB32X, SH-2 code at `0x06000684`; 68000 code at `$88091E`].

## Compared with the arcade original

The arcade game runs on Sega's X Board. Its frame rate is not settled here. Two retrospectives say it runs at 60 frames a second and the 32X version at half that [HG101-AB; REGISTER-AB], but neither says how that was measured, and no arcade dump was run for this book. MAME's driver shows a screen of about 60 Hz but not how often the game redraws, which the game decides by when it swaps its sprite list [MAME, segaxbd.cpp, sega16sp.cpp]. As far as the evidence goes, the 32X version differs in these ways:

| | Arcade (X Board) | 32X |
|---|---|---|
| Pictures a second | 60, by two retrospectives; not measured | 30 <span class="tag emulator">emulator</span> |
| Scaling | Sprite hardware scales every sprite pixel by pixel, from a list of up to 256 a picture | A software scaler on the Master, up to 92 sprites a picture in play. Large, close sprites are drawn at half resolution, each source pixel as a 2 × 2 block, to save time ([After Burner Complete's scaler](../techniques/2d-effects.md#after-burner-completes-scaler)) |
| Colours | An 8,192-entry palette of 15-bit colours, with shadow and highlight; each sprite picks one of 256 palettes of 16 | 256 colours for the whole 32X picture, plus the Mega Drive's own palette for the jet and the score |
| Sound | A YM2151 FM chip and a 16-channel PCM chip at 31.25 kHz, driven by a Z80 | The Mega Drive's FM and PSG chips, driven by a Z80, and 16 voices mixed in software on the Slave at about 15.6 kHz |
| CPUs | Two 68000s at 12.5 MHz and a Z80 | The Mega Drive's 68000 at 7.67 MHz and Z80, and two SH-2s at 23 MHz |

Sources: [MAME, segaxbd.cpp (CPUs, palette RAM, screen, sound chips), sega16sp.cpp (sprite list of 16-byte entries in 4 KB, zoom, 4-bit pixels with a per-sprite palette), segapcm.cpp (16 voices, clock ÷ 128)]; this chapter for the 32X column. How many sprites the arcade game uses in the same scenes was not measured, so the sprite rows compare a hardware limit with a count.

The clearest concession is the half-resolution mode. The arcade hardware scales each sprite at full resolution for free; on the 32X every pixel costs Master time, and the game halves the cost of the biggest sprites by drawing them coarser.

## Where the time goes

A per-instruction profile of 1,990 frames of play gives this picture. The shares are of the whole run's time, every frame counted, not of one picture <span class="tag emulator">emulator</span> [AB32X, PicoDrive profile from a state saved at frame 1,200, with a copy of PicoDrive that also logs the time each CPU spends asleep, 6 October 2026]:

| CPU | Doing useful work | Waiting |
|-----|-------------------|---------|
| 68000 | About 57%: the game, and setting up its calls | 23% for the Master to take each entry of a list, 10% for the Master's answers to its object calls, 10% for vertical blank |
| Master | About 41%: 26 points drawing scaled sprites into the frame buffer, about 15 points of work that never touches it (projection in the command interrupt, the sprite cache and list, the sort, set-up) | About 38% on fills (18% polling the fill busy bit, 20% asleep while polling it), 15% waiting for the 68000's go-ahead, 5% asleep waiting for the flip |
| Slave | About 29% mixing, 2% in the PWM interrupt | About two-thirds, spinning or asleep until its ring has room |

**What "asleep" means.** When PicoDrive catches a CPU polling a 32X register, it stops running it until the register changes. A profile counts only the instructions a CPU runs, so the sleep shows up as time missing from the profile: a quarter of the Master's time in this run. The modified PicoDrive shows where it goes. About four-fifths is in the poll of the fill busy bit, the rest in the poll that waits for the flip. Each sleep in the fill poll lasts on average 700 to 850 clocks, longer than the longest fill the routine starts (about 490 clocks by the manual), so PicoDrive wakes the Master late.

That is why its fill waits come out so large. Counting polling and sleep, they take about 318,000 clocks per picture, against about 110,000 by the manual's formula for the picture's 448 fills: about 245 clocks a fill. On a console the figure should be nearer the manual's. The profiled run also draws a little slower than a normal one, 928 pictures in 2,000 frames against 995, because the profiler switches PicoDrive's SH-2s to its interpreter. So "per picture" here means 2.16 video frames.

The rest of the pattern does not depend on PicoDrive's fills: on every CPU a large share of the time is spent waiting.

## What it leaves on the table

Each of the waits has a known cure, used elsewhere in this book, but not every cure buys much:

- **The Master waits for every fill, but little can run during one.** During a fill the CPUs may not touch the frame buffer, though they may use SDRAM, registers and the palette ([Auto fill](../32x/vdp.md#auto-fill)). The Master's largest job, drawing scaled sprites, writes to the frame buffer, so it cannot overlap. What can is the work that never touches it, about 15 points of the run or 121,000 clocks a picture. Some of that already does: projection runs in the command interrupt, which the Master leaves enabled while it polls, so a call from the 68000 that lands during a fill is served then. The ceiling is the fills' own time, about 110,000 clocks a picture by the manual. Star Wars Arcade overlaps its long fills with work, pacing them with a timer ([Star Wars Arcade: polygons as auto fills](../techniques/software-3d.md#star-wars-arcade-polygons-as-auto-fills)).
- **The 68000 and the Master take turns.** Each object call stops the 68000 until the Master answers, and each entry of a list waits until the Master has taken the last: a third of the 68000's time in PicoDrive. The answer the 68000 needs is mostly "visible or not", which it could get one picture late from a list the Master writes ([When moving a job pays](cpu-split.md#when-moving-a-job-pays)). Star Wars Arcade makes the same round trip per object ([Case study: Star Wars Arcade](case-study-starwars.md#what-it-leaves-on-the-table)).
- **Two-thirds of the Slave is idle.** Sound takes about a third of it, and nothing else uses the rest. Decoding sprites ahead of the Master, or drawing part of the picture, would need shared lists and cache purges, which the design avoids at the cost of the spare capacity ([Balancing per picture, not per task](cpu-split.md#balancing-per-picture-not-per-task); [Cache discipline](cache.md)).
- **The 68000 has no frame to spare either.** It waits for vertical blank only 10% of its time. Its own work, the game and the set-up of its calls, is about 57% of the run, about 1.2 video frames per picture. Even with every wait removed it would not fit in one frame ([Why the rate is 60, 30, 20 or 15](60fps.md#why-the-rate-is-60-30-20-or-15)).

**What the idle time could buy at 30.** The picture rate is the same as the arcade's only if the retrospectives are wrong; either way, the spare time could have bought fidelity without touching the rate:

- **Full resolution for close sprites.** The half-resolution modes take about 10% of the run. Drawing those sprites at full resolution would cost up to twice as much, roughly 80,000 more clocks a picture. By the manual's fill timing the Master's work for a picture, about 336,000 clocks plus 110,000 for fills, leaves room for that within two frames (768,000).
- **The arcade's sound rate.** Mixing at 31.25 kHz, as the arcade's PCM chip plays, would roughly double the mixer's 29% and the interrupt's 2%. Two-thirds of the Slave is idle.

**What 60 would take.** Reaching the arcade's 60, if that is its rate, needs each picture in one frame on every CPU. By PicoDrive's account the Master's work for a picture is about 0.87 of a frame: 0.56 drawing sprites, 0.31 for the rest. The fills take about 0.29 of a frame by the manual, and no sprite can be drawn during them. With every wait gone and the rest of the work hidden under the fills, the Master would need 0.56 + 0.29 = 0.85 of a frame, plus the 0.02 that does not fit under them. That is 0.87, almost no margin, before a console's costs for cache misses and frame-buffer writes, which PicoDrive barely charges. The 68000 needs about 1.2 frames for its own work. So 60 would take a faster game loop on the 68000, and a Slave that draws part of the picture: the costliest cure above. These are emulator figures, and a console is slower, not faster. The Virtua Racing Deluxe project is the warning: it found a serialised design, set out to raise its frame rate, and later withdrew the results it first reported ([Case study: Virtua Racing Deluxe](case-study-vr.md#what-the-project-changed)).

## Built to survive

The code is careful about failure in ways Star Wars Arcade and Mortal Kombat II are not; its reset recovery it shares with Space Harrier and Virtua Racing Deluxe:

- **A lost command interrupt is recovered.** The Master's main loop counts down from 1,500,000 while it waits for the next command. If nothing arrives, it clears the command interrupt and the busy flag and waits again [AB32X, SH-2 code at `0x060038E6`]. On the 68000's side, every request waits for its acknowledgement.
- **Reset is acknowledged.** After the reset button, the Master's VRES handler writes the letters `VRES` into a communication port, and the 68000's restart path looks for them before it starts the SH-2s again. If they never appear, it raises the command interrupt on both CPUs and runs the normal handshake ([Pressing reset](../32x/boot.md#pressing-reset)) [AB32X, SH-2 code at `0x06002266`; 68000 code at `$880840`-`$880908`]. Space Harrier, from the same studio, has the same handshake, and so does Virtua Racing Deluxe, a Sega game from another team; no other 32X game in the sources has it ([The `VRES` handshake](../appendices/sample-code.md#the-vres-handshake-rutubo-games-and-virtua-racing-deluxe)).
- **Sega's sample slip is fixed.** Sega's VRES sample, which Star Wars Arcade and Mortal Kombat II copy, writes its DMA control value to the wrong address. After Burner Complete writes it where it belongs ([Handlers in practice](../sh2/intc.md#handlers-in-practice)). Space Harrier has the same handler, and Virtua Racing Deluxe a simpler one with the same core ([Sega's sample code in the games](../appendices/sample-code.md)).
- **One check is still wrong, and never matters.** Both VRES handlers test the wrong byte for RV, the bit that hands the cartridge back to the Mega Drive. The game never sets RV, so the reset path it guards never runs ([Reset while RV = 1](../32x/bugs.md#reset-while-rv--1); [discrepancy 33](../appendices/discrepancies.md)).

## Compared with the other games

| Game | 3D method | Who draws | Who plays sound |
|------|-----------|-----------|-----------------|
| After Burner Complete | Scaled sprites over flat colour | Master | Z80 (FM, PSG) and Slave (PWM) |
| Star Wars Arcade | Flat polygons as auto fills | Master transforms, Slave draws | 68000 and Z80 (FM, PSG), Slave (PWM) |
| Virtua Racing Deluxe | Polygons | Unclear ([discrepancy 28](../appendices/discrepancies.md)) | 68000 and Z80 |
| Mortal Kombat II | None (2D) | Master | A Z80 program (not traced) and Slave (PWM) |

Sources: this chapter; [Splitting work across three CPUs](cpu-split.md); [Case study: Virtua Racing Deluxe](case-study-vr.md).

Star Wars Arcade spreads its drawing over both SH-2s in a pipeline and overlaps its long fills with work. After Burner Complete keeps one SH-2 free of graphics altogether and waits for each fill. After Burner holds 30 pictures a second; Star Wars Arcade is unlocked and runs at 32 to 34 in play, unevenly. Both make the 68000 call the Master once per object, and both give the Mega Drive's VDP the parts of the screen that do not move in 3D. The two come from different developers, Sega InterActive and Rutubo Games, and share no code beyond Sega's samples that a comparison found ([How much else the three share](../appendices/sample-code.md#how-much-else-the-three-share)). So the per-object call is a design two teams reached separately, not a habit one copied from the other, which makes it more likely to be what the 32X's ports and CMD interrupt invite.

## What the design teaches

What it does well, and worth copying:

- **Choose the renderer to suit the art.** Scaled sprites give After Burner its arcade look at a cost per object, and the scaler's inner loop needs four instructions for two pixels, with transparency left to the hardware.
- **Let the hardware draw the big areas.** Auto fill draws the sky and sea, tilts the horizon and clears the old picture in one job, with no pixel writes by the CPU.
- **Decode once, draw many times.** The sprite cache keeps unpacked images in SDRAM for as long as there is room, so a sprite on screen for many pictures is unpacked once.
- **Expect handshakes to fail.** The watchdog and the `VRES` marker cost a few instructions and turn a hang into a recovery.

What it gets wrong, and worth avoiding:

- **Never wait for hardware with nothing to do.** If a fill takes a few hundred clocks (about 245 on average here, by the manual), give the CPU that much work that stays off the frame buffer, or let a timer interrupt bring it back as Star Wars Arcade does. Check first how much such work there is: here it is about as much as the fills take, and the part done in the command interrupt overlaps already.
- **Don't make one CPU wait for another per item.** A round trip per object is simple to write but takes turns where the CPUs could run side by side. Batch the work in lists and read the results one picture later.
- **Keeping the CPUs apart is not free.** A sound-only Slave shares nothing and needs no purges, but it leaves two-thirds of a CPU unused. Decide that with the numbers in hand, not by default.
- **Spend spare time on fidelity when the rate cannot move.** At 30 pictures a second the idle time was enough to draw close sprites at full resolution or to mix sound at the arcade's rate.
- **Profile the waiting, not only the work.** In this game the waits are larger than any single piece of work, and they only show up when every CPU's idle time is measured ([Profiling](../howto/profiling.md)).

## Open questions

- How long does the Master really wait for its fills? PicoDrive's figure, about three times the manual's, comes mostly from waking the Master late; a console measurement would decide whether the fills or the sprites limit the frame rate.
- How often does the arcade game redraw? The retrospectives say 60; a run of the arcade dump in MAME, counting sprite-list swaps, would settle it.
- How much of the 68000's wait for the Master to take each list entry is real? The Master takes commands in an interrupt, and PicoDrive's late wake-ups may delay it.
- Is the player's jet always a Mega Drive sprite? A frame-buffer dump from stage 8 shows a jet in the 32X layer, which was not followed up ([Sprites over and under the 32X layer](layering.md#sprites-over-and-under-the-32x-layer)).
- When the plane banks, are the ground sprites drawn from pre-rotated art? The shape numbers have not been checked against the roll angle.
- How much faster would it run with the fills overlapped and the per-object calls batched? Only a rebuilt game, timed on a console, can say.

## Sources

- [AB32X](../appendices/bibliography.md#ab32x): credits at cartridge `$01C25C`; SH-2 code at `0x06000200`, `0x06000684`, `0x06002120`, `0x06002266`, `0x0600257C`-`0x060025A8`, `0x060036FC`-`0x0600373A`, `0x06003890`, `0x060038CE`-`0x06003966`, `0x060038E6`, `0x06003B66`, `0x06006778`-`0x06006BEF`, `0x06008280`-`0x060082F6`; 68000 code at `$880840`-`$880908`, `$88091E`, `$887348`-`$8873BC`, `$88A020`-`$88A06A`, `$890B8A`, `$89C6A8`-`$89C6EE`; PicoDrive watch logs, per-instruction profiles and sleep log
- [32X-ROMSET](../appendices/bibliography.md#32x-romset): Space Harrier's credits (`$041F06`); the `VRES` handshake in Space Harrier and Virtua Racing Deluxe
- [WP-32XLIST](../appendices/bibliography.md#wp-32xlist): developer and publisher
- [MAME](../appendices/bibliography.md#mame): the X Board driver, sprite generator and PCM chip
- [HG101-AB](../appendices/bibliography.md#hg101-ab), [REGISTER-AB](../appendices/bibliography.md#register-ab): the arcade's frame rate as the press gives it
- The chapters linked above, which cite each technique in detail
