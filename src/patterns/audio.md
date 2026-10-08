# Audio across PWM, FM and PSG

A 32X has two sound systems. The Mega Drive's is a YM2612 with six FM channels, one of which can play 8-bit samples instead, and a PSG with three square waves and a noise channel. The 32X adds two PWM channels, one per speaker, fed with samples by software. Four CPUs could drive them. This page is about the split: what each sound source is good for, how the shipped games divided music and effects between them, what each arrangement costs, how sound requests travel, and how to choose a music path. The hardware is covered elsewhere: [The Z80 and sound](../megadrive/sound.md), [YM2612](../megadrive/ym2612.md), [PSG](../megadrive/psg.md) and [PWM audio](../32x/pwm.md).

## What each source is for

| Source | Voices | Good at | What it needs |
|--------|--------|---------|---------------|
| YM2612 FM | 6 | Music: instruments from a few dozen register values each, so the data is tiny | A driver writing registers on time, waiting on the chip's busy flag between writes ([YM2612](../megadrive/ym2612.md#reaching-the-registers)) |
| PSG | 3 square + noise | Simple tones, percussion layered over FM | A few register writes per note ([PSG](../megadrive/psg.md)) |
| YM2612 DAC | 1, in place of FM channel 6 | One sample stream: drums, a voice clip | A CPU writing every sample at a steady rate, in practice the Z80 ([The DAC](../megadrive/ym2612.md#the-dac)) |
| PWM | 2 outputs, any number of voices mixed in software | Recorded sound: speech, effects, sampled music, many voices at once | A CPU coming back at least every three samples, for as long as sound plays ([Keeping it fed](../32x/pwm.md#keeping-it-fed)) |

The YM2612 and PSG make sound from almost no data, but only the sounds they can synthesise. PWM plays anything, at the cost of a CPU's attention and of ROM: a second of 8-bit sound at 11 kHz is about 11 KB, more than a whole FM song can take.

## What the shipped games did

| Game | Music | PWM | Who feeds PWM | How a sound is requested |
|------|-------|-----|---------------|--------------------------|
| Mortal Kombat II | A 2 KB Z80 program (not traced further) | 2 voices of 6-bit samples | The Slave, in its PWM interrupt | One word in a port, fire and forget |
| Star Wars Arcade | Sequenced by the 68000; the 68000 writes the PSG itself, and a 409-byte Z80 program writes FM registers and DAC samples for it | 1 voice, codebook-compressed | The Slave, in its PWM interrupt, between drawing jobs | A Master command, passed to the Slave once a frame |
| After Burner Complete | A 5,888-byte Z80 program for FM and PSG, and a sequencer on the Slave for PWM | 16 voices, interpolated and panned | The Slave's main loop, through a ring the interrupt empties | Every request goes to both the Z80 and the Slave |
| Knuckles' Chaotix | Not traced | 4 voices, panned, mixed from on-chip RAM | The Slave, in its PWM interrupt | One port per voice |
| Motocross Championship | A 6,278-byte Z80 program | 2 voices, one per speaker | **The 68000**, in its line interrupt | The 68000's own variables |

Sources: [MK2, 68000 code at `$0407EC`, `$0408CC`; SH-2 code at `0x06004F4C`; SWA, 68000 code at `$00EF2C`, `$00F2AE`; Z80 program at cartridge `$00FE68`; SH-2 code at `0x060007E4`, `0x060011FA`; AB32X, 68000 code at `$000C2E`, `$00091E`, `$009366`; SH-2 code at `0x060003C0`, `0x06000820`; CHAOTIX, SH-2 code at `0x06000284`, `0x060001F8`, cartridge `$07FC00`; MCX, 68000 code at `$00081A`, `$000E18`, `$025640`].

Three things stand out:

- **FM and PSG music stayed on the Mega Drive side** in every game whose music was traced. Only After Burner Complete also plays music parts through PWM.
- **The Slave owns PWM** in four games out of five, and in three of them it does nothing else. Star Wars Arcade's Slave draws as well, with the sound in an interrupt that takes priority over its drawing ([One SH-2 draws, the other plays sound](cpu-split.md#one-sh-2-draws-the-other-plays-sound)).
- **The 68000 can feed PWM too, at a price.** Motocross Championship does it from the line interrupt (below).

### Motocross Championship: PWM from the 68000

Motocross Championship's Slave sits idle even during a race, so its sound runs on the 68000 [MCX, profile]. At start-up the 68000 writes the PWM registers itself: both pulse widths to 1, the cycle to `$5B9` (1,465, so 15,718 samples a second, close to the line rate) and control to `$0105`. It turns on the Mega Drive VDP's line interrupt with register 10 = 1, one interrupt every second line [MCX, 68000 code at `$000E18`-`$000E5E`].

Each line interrupt writes one sample to each speaker, after waiting for room in that FIFO [MCX, 68000 code at `$00081A`-`$0008C6`]:

- **Right:** a looping voice, stepped by a fixed-point increment so that one sample can play at many pitches (an engine note, by the way the game uses it), or else a one-shot stream.
- **Left:** a second looping voice.
- **Volume:** each byte is multiplied by a volume and shifted right by 4. A result of 0 is raised to 1, because a pulse width of 0 is the loudest value, not silence ([Traps](../32x/pwm.md#traps)). The one-shot path has this check too, but it adds the 1 to the wrong register, so a scaled 0 in a stream is written as 0.

Each voice goes to one speaker, so nothing needs mixing or clamping. The costs:

- **The 68000's time.** In a PicoDrive run of 2,000 frames, the handler ran about 105 times a frame and took about 37,000 68000 clocks a frame, close to 30% of the 68000 <span class="tag emulator">emulator</span> [MCX, PicoDrive profile].
- **A gap every frame.** The line interrupt does not fire during vertical blank ([The line interrupt](../megadrive/vdp-timing.md#the-line-interrupt)), so for about 38 lines each frame no samples arrive. The FIFO runs dry and the output holds its last value for about 2.4 ms, sixty times a second.
- **Sample timing tied to the display.** Samples arrive in pairs of lines, about 7,900 a second during the picture, while the PWM plays 15,718. Each sample is therefore heard twice, and the pitch is set by the number of interrupts per frame.

Feeding PWM from the 68000 works for two voices with no mixing. It costs the 68000 a large share of its time and gives sound that stutters with the frame.

## What it costs

| Arrangement | Cost | Source |
|-------------|------|--------|
| Sega's Sound Driver V3 (68000 sequencer, Z80 samples) | About 9% of the 68000 while music plays, 1% idle | [Sega's V3](../megadrive/sound.md#segas-v3-sequencing-on-the-68000-samples-on-the-z80) |
| Two PWM voices from the 68000's line interrupt (Motocross Championship) | About 30% of the 68000 <span class="tag emulator">emulator</span> | Above |
| 16 interpolated PWM voices at 15.6 kHz on the Slave (After Burner Complete) | About 46% of the Slave mixing, 3% in the interrupt; the rest spare <span class="tag emulator">emulator</span> | [AB32X, PicoDrive profile] |
| A PWM interrupt per sample at 22 kHz | 22,000 interrupt entries a second, whatever the mixer does | [The PWM interrupt](../32x/pwm.md#1-the-pwm-interrupt-star-wars-arcade) |
| DMA feeding PWM (d32xr) | About 70 interrupts a second | [DMA](../32x/pwm.md#2-dma-d32xr) |

ROM is the other cost. Mortal Kombat II's packed 6-bit samples take about 8.1 KB per second of sound ([Sound: a fixed cost per sample](../techniques/compression.md#sound-a-fixed-cost-per-sample)). 4-bit ADPCM (adaptive differential coding: each sample stored as a small step from the last, with the step size adapting to the signal) at 11 kHz takes about 5.5 KB per second. Minutes of music stored that way take megabytes <span class="tag emulator">emulator</span> [S32X-SKILL, audio.md].

Bus time is the cost that is easiest to miss. A sound CPU polling a port, or fetching code and samples from SDRAM, takes bus cycles the drawing CPU needs ([Living with bus contention](bus.md)). Chaotix avoids almost all of it. Its Slave turns on two-way cache mode and copies 1 KB of mixer code into on-chip RAM. It keeps its stack and the four voices' state there too, and the PWM interrupt jumps straight into it [CHAOTIX, SH-2 code at `0x06000284`-`0x060002FE`; dispatcher table at `0x06000220`]. Only the sample bytes and the PWM writes go over the bus. See [Two-way mode](../sh2/cache.md#two-way-mode-2-kb-of-on-chip-ram).

## Getting requests to the sound CPU

The game logic runs on the 68000 in most of these programs, so every sound starts there and has to reach whichever CPU plays it. The shipped games show five ways to do it:

- **One word, fire and forget.** Mortal Kombat II writes the sound number with a "new" bit into one port. The Slave starts it and clears the word. The 68000 never waits, so a second request in the same moment replaces the first ([Bulk data through the ports](../32x/communication.md#bulk-data-through-the-ports)) [MK2, 68000 code at `$00E01A`].
- **One port per voice.** Chaotix gives each of its four voices its own port. The low byte is the sound number and the high byte holds a 4-bit left and a 4-bit right volume, so the request carries its own stereo position. The Slave reads each port twice until two reads agree, then clears it, which guards against catching a word half written ([The one hazard](../32x/communication.md#the-one-hazard-a-word-that-changes-while-you-read-it)) [CHAOTIX, cartridge `$07FD2C`, run at `0xC000012C`]. Voices never compete for one port, but the 68000 must choose the voice.
- **A command by interrupt.** After Burner Complete sends each request to the Slave as a command word with the CMD interrupt ([The CMD interrupt](../32x/communication.md#the-cmd-interrupt)), so the Slave never polls. The 68000 waits only if the previous command has not been taken yet [AB32X, 68000 code at `$009366`].
- **Once a frame, with a priority.** Star Wars Arcade's 68000 sends the Master a command. The Master writes the sound's address and priority into shared SDRAM, and the Slave looks once a frame: it starts the new sound only if its priority is at least that of the one playing, and otherwise drops it [SWA, SH-2 code at `0x060011FA`, `0x060007E4`-`0x06000878`]. One voice, and the important sound wins.
- **To every driver at once.** After Burner Complete's request routine puts each sound number into the first free slot of an 8-byte queue in Z80 RAM and also sends it to the Slave. Each driver plays whatever parts of that sound it owns [AB32X, 68000 code at `$009366`-`$0093C0`].

A sequence number in the request word makes a repeated request fire even when the value is the same as last time ([Sequence numbers](../32x/communication.md#repeating-a-command-sequence-numbers)). One homebrew game sends music and effects through separate ports this way <span class="tag emulator">emulator</span> [S32X-SKILL, audio.md].

## Keeping music and effects in step

When one piece of music is split between two drivers, they must share one clock. After Burner Complete's line interrupt, which fires twice a frame, does three things each time [AB32X, 68000 code at `$00091E`-`$00099E`; VDP register table at `$000F9A`]:

1. It increments a byte in Z80 RAM.
2. It passes on a flag the Z80 has left, if any, to the Slave.
3. It sends the Slave its sequencer tick.

Both sequencers advance from the same interrupt, so the FM parts and the PWM parts cannot drift apart. Two drivers timed separately, one by a YM2612 timer and one by counting PWM samples, would have nothing holding them together.

Inside a mixer, the sample count is a good clock. After Burner Complete works out each voice's position from the count of samples since the voice started, so its pitch never accumulates error ([Mixing](../32x/pwm.md#mixing)). d32xr updates its sound positions after a fixed number of samples (below), not once per game frame.

## Voices: who gets one

With a fixed number of voices, every new sound needs a rule for which one it takes:

- **Mortal Kombat II** (2 voices): voice A if free, else B, else whichever voice was not started last [MK2, SH-2 code at `0x06005178`].
- **Star Wars Arcade** (1 voice): a new sound replaces the current one if its priority is equal or higher (above).
- **d32xr** (several voices, in its DMA sound build) [D32XR, marssound.c]:
  - The same sound started twice at the same moment replaces the first only if it is louder.
  - Some sounds are marked as allowed to play only once at a time; a new one replaces the old.
  - A new sound from an object replaces whatever that object was already playing.
  - Otherwise the sound takes a free voice, then any voice playing something of equal or lower importance, and is dropped if there is none.
- **A homebrew tracker** lets an important effect take a music voice. The next note on that voice takes it back, so the number of voices never changes <span class="tag emulator">emulator</span> [S32X-SKILL, audio.md].

d32xr also saves ROM by playing one sample at different rates. Sounds missing from its data are mapped to existing ones played slower or faster: a monster's pain sound at 5,512 Hz stands in for the boss's, and the player's pain sound at 7,350 Hz for another creature's [D32XR, marssound.c].

## Mixing PWM with FM and PSG

The two sound systems meet in the console's analogue mixing. The rules:

- **Leave headroom.** Sega raised the PWM level on later boards and warned that both at full volume distort, PWM first ([Traps](../32x/pwm.md#traps)) [32X-TI item 20]. A homebrew guide suggests keeping FM carriers a few decibels below full, so that effects played through PWM can be heard over the music <span class="tag emulator">emulator</span> [S32X-SKILL, architecture.md].
- **Keep the silence level still.** A mixer's output must rest at the middle of the PWM range when nothing plays, and stay there when a voice starts or stops, or each start clicks. Mortal Kombat II's mixing formula keeps it within 2 of the same value whether one voice plays or two ([Keeping it fed](../32x/pwm.md#1-the-pwm-interrupt-star-wars-arcade)).
- **Panning is free per voice, and costs a multiply per voice when mixed.** Motocross Championship sends each voice to one speaker. Chaotix and After Burner Complete multiply each voice by a left and a right volume ([Mixing](../32x/pwm.md#mixing)).

### Cheap tricks in the mixers

- **Half rate, played twice.** Mortal Kombat II, Star Wars Arcade and Chaotix all store samples at half the output rate and play each twice. Chaotix improves on plain repetition: the first of each pair is the average of the previous and the new sample, a cheap linear interpolation [CHAOTIX, cartridge `$07FD98`-`$07FDEA`].
- **Work only when there is work.** After Burner Complete mixes only while its ring has room. d32xr stops clearing and mixing its buffers once two in a row have had nothing to play [D32XR, marssound.c].
- **Spatial sound at 15 Hz.** d32xr updates each sound's volume and stereo position every 1,470 samples, about 15 times a second. Distance is approximated as the larger difference plus half the smaller. Volume falls linearly from 200 to 1,224 units. The stereo position is the centre minus 96 times the sine of the angle to the sound [D32XR, marssound.c].

d32xr's mixer is only in builds made with DMA sound enabled. Its default build sends effects to a Mega CD's sound hardware when one is attached [D32XR, marssound.c, Makefile].

## Choosing a music path

| Path | Data size | CPU | Sounds like | Used by |
|------|-----------|-----|-------------|---------|
| FM and PSG driver on the Z80 | Smallest | The Z80; the 68000 only sends requests | Mega Drive music | Mortal Kombat II, After Burner Complete, Motocross Championship (Z80 programs) |
| Sequencer on the 68000 | Small | A few percent of the 68000; the Z80 writes chips or samples for it | Mega Drive music | Star Wars Arcade; Sega's Sound Driver V3; Virtua Racing Deluxe ([Who does the work](../megadrive/sound.md#who-does-the-work)) |
| Recorded register log (VGM) | Medium, compressed | The 68000 decompresses, the Z80 replays | Exactly the composer's FM | d32xr ([d32xr](../megadrive/sound.md#d32xr-decompress-on-the-68000-replay-on-the-z80)) |
| Sequencer and mixer on the Slave | Samples per instrument | Part of the Slave | Sampled instruments, many voices | After Burner Complete, with FM alongside |
| Streamed ADPCM on the Slave | Megabytes for a few tracks | Part of the Slave | Any recording | Homebrew <span class="tag emulator">emulator</span> [S32X-SKILL, audio.md] |

The last two leave the Mega Drive sound chips free for effects or for a second layer. The first three leave PWM for effects and speech, which is what the shipped games did.

## What to take away

- FM and PSG make music from tiny data. PWM plays anything, but needs a CPU every few samples and ROM for every sound.
- Give PWM to the Slave, ideally as its only job and from on-chip RAM, as Chaotix does. Feeding it from the 68000 costs about a third of the 68000 and stutters every vertical blank.
- Choose how requests reach the sound CPU: one port per voice, a CMD interrupt, or a once-a-frame pick-up with a priority. Each needs a rule for when two requests meet.
- If music is split between drivers, tick them from one interrupt.
- Decide in advance which sound takes a voice when all are busy.
- Leave headroom between FM and PWM, and keep the silence level fixed.

## Open questions

- What do Mortal Kombat II's and Chaotix's music drivers do, and how do their games request music?
- Is Motocross Championship's 2.4 ms gap in each frame audible on a console?
- Does the console's analogue mix favour PWM or FM on each board revision, and by how much?

## Sources

- [MK2](../appendices/bibliography.md#mk2): 68000 code at `$00E01A`, `$0407EC`, `$0408CC`; SH-2 code at `0x06004F4C`, `0x06005178`
- [SWA](../appendices/bibliography.md#swa): 68000 code at `$00EF2C`, `$00F2AE`; Z80 program at cartridge `$00FE68`; SH-2 code at `0x060007E4`-`0x06000878`, `0x060011FA`
- [AB32X](../appendices/bibliography.md#ab32x): 68000 code at `$000C2E`, `$00091E`, `$009366`; VDP register table at `$000F9A`; SH-2 code at `0x060003C0`, `0x06000820`; PicoDrive profile
- [CHAOTIX](../appendices/bibliography.md#chaotix): SH-2 code at `0x060001F8`, `0x06000284`-`0x060002FE`; on-chip code from cartridge `$07FC00`
- [MCX](../appendices/bibliography.md#mcx): 68000 code at `$00081A`-`$0008C6`, `$000E18`-`$000E5E`, `$025640`; PicoDrive profile
- [D32XR](../appendices/bibliography.md#d32xr): marssound.c, Makefile
- [S32X-SKILL](../appendices/bibliography.md#s32x-skill): audio.md, architecture.md
- [32X-TI](../appendices/bibliography.md#32x-ti): item 20
