# PWM audio

The 32X's own sound is two channels of pulse-width modulation (PWM). There is no synthesis: the program supplies every output sample, as a number that sets how long a pulse stays high in each sample period, and a filter turns the pulses into a waveform. The output is mixed with the Mega Drive's FM and PSG. This chapter covers the registers, how the cycle sets both the sample rate and the resolution, the three-sample FIFO, the three ways shipped and homebrew code keep it fed, and the traps.

## Registers

Five registers, reachable from both sides [32X-HWM §3.2.1, §3.4 pp.56-57]:

| 68000 | SH-2 | Register |
|-------|------|----------|
| `$A15130` | `0x20004030` | Control |
| `$A15132` | `0x20004032` | Cycle |
| `$A15134` | `0x20004034` | Left pulse width |
| `$A15136` | `0x20004036` | Right pulse width |
| `$A15138` | `0x20004038` | Mono pulse width: one write goes to both channels |

**Control:**

| Bits | Name | Meaning |
|------|------|---------|
| 11-8 | TM | Interrupt (and DREQ1) every TM samples; 0 means 16. Set from the SH-2 side only |
| 7 | RTP | 1 = also raise DREQ1 for SH-2 DMA channel 1. SH-2 side only |
| 3-2 | RMD | Right output: 00 off, 01 from the right channel, 10 from the left |
| 1-0 | LMD | Left output: 00 off, 01 from the left channel, 10 from the right |

Setting both outputs to the same source is not allowed (11 is invalid in each field). TM and RTP read back on the 68000 side but cannot be written from it [32X-HWM §3.2.1, PWM control register].

**Cycle** (bits 11-0): the length of one sample period, in SH-2 clocks, plus one.

**Pulse width** (left, right, mono): writes put bits 11-0 into the channel's FIFO. Reads return two flags: bit 15 FULL (no room) and bit 14 EMPTY. Reading bits 11-0 returns nothing useful [32X-HWM §3.2.1].

**Access sizes.** From the SH-2, write the pulse width registers as whole words; bytes are forbidden. Control and cycle accept bytes. From the 68000, byte writes to a pulse width register work if the high byte is written first <span class="tag manual">manual</span> [32X-TI item 19]. A longword write from the SH-2 to `0x20004034` becomes two word writes on the 16-bit bus, filling left then right with one instruction, which is what d32xr's DMA path relies on [D32XR, marssound.c].

## Cycle, sample rate and resolution

The off-by-one matters [32X-HWM §3.4 p.57] <span class="tag manual">manual</span>:

- A cycle value *c* gives a sample period of *c* − 1 clocks. So the sample rate is *f* / (*c* − 1), where *f* is the SH-2 clock (23.01 MHz NTSC, 22.80 MHz PAL), and the value to write is *f* / rate + 1.
- *c* = 0 gives the longest period, 4,095 clocks. *c* = 1 stops PWM altogether; never write it.
- A pulse width value *w* gives a pulse *w* − 1 clocks long. So 1 is the lowest output and *c* is the highest; **0 is not silence but the maximum** (it wraps to 4,095). Values above the cycle clip to the maximum.

At 23,011,361 Hz (NTSC):

| Target rate | Cycle | Actual rate | Useful pulse values | About |
|-------------|-------|-------------|---------------------|-------|
| 11,025 Hz | 2,088 | 11,026 Hz | 1-2,088 | 11 bits |
| 22,050 Hz | 1,045 | 22,041 Hz | 1-1,045 | 10 bits |
| 22 kHz (Sega's example) | 1,047 | 21,999 Hz | 1-1,047 | 10 bits |
| 44,100 Hz | 523 | 44,083 Hz | 1-523 | 9 bits |

The registers are 12 bits wide, but the resolution is set by the cycle: the faster the rate, the fewer distinct levels. Sega's materials say "11-bit resolution" in one place and "10 bits at 22 kHz" in another, and both fit this rule [32X-HWM §1; 32X-OV, hardware specifications]. The middle of the range, about *c* / 2, is silence.

**Use the right cycle for the region.** PAL machines run the SH-2 at 22.80 MHz, so the same cycle plays about 1% slower. d32xr picks its cycle from the 32X VDP's PAL bit, using 23,011,361 and 22,801,467 Hz as the two clocks [D32XR, marshw.c, src-md/vgm.c].

S32X-SKILL gives the cycle as clock / rate, without the + 1, and a "safe range" of about 2 to 1,032 [S32X-SKILL, audio.md, architecture.md]. The range is just d32xr's chosen limits for a cycle of 1,045. At another rate, the limits move with the cycle.

## The FIFO

Each channel has a FIFO three samples deep [32X-HWM §3.2.1, §3.4 p.57]:

- **Once per sample period** the oldest entry becomes the new pulse width. When the FIFO is empty, the last width is repeated.
- **Writing to a full FIFO throws away the oldest entry.** Nothing stops a program from overrunning it, so check FULL before each write.
- **When both outputs are off** (LMD = RMD = 00), the period counter stops. A FIFO that becomes full then stays full until an output is turned on, so a loop that waits for FULL to clear never ends. Turn an output on before filling. With one output on, the other channel's FIFO still drains, silently <span class="tag disputed">disputed</span> ([discrepancy 23](../appendices/discrepancies.md)).
- **After reset** the FIFO is empty and the output is 0.
- **When you write the channels separately, poll each channel's own register.** The manual does not say what the mono register's FULL and EMPTY bits report when the two FIFOs hold different amounts, and the three emulators read for this book give three answers (see [In emulators](#in-emulators)). Motocross Championship writes right and left one at a time, waiting on `$A15136` and then `$A15134` [MCX, 68000 code at `$000862`-`$000870`, `$0008B2`-`$0008C0`]. Writing through the mono register, or both channels with one longword at `0x20004034`, keeps the FIFOs level and avoids the question.

Three samples is 136 µs at 22 kHz. Whatever feeds the FIFO must come back at least that often, every time, or the output holds a level and clicks or buzzes.

## Keeping it fed

### 1. The PWM interrupt (Star Wars Arcade)

With TM = *n*, the PWM raises an interrupt at level 6 every *n* samples, on whichever SH-2s have it unmasked. The handler clears it at `0x2000401C` (see [Interrupt controller](../sh2/intc.md)). Because the FIFO holds only three samples, TM has to be small (1 to 3), and the handler must fill until FULL each time.

Star Wars Arcade, developed at Sega InterActive, does exactly this on the Slave [SWA, SH-2 code at `0x0600095C`-`0x06000AAE`]:

- **Set-up:** cycle = 1,047 (Sega's 22 kHz example), control = `$0105` (TM = 1, left from left, right from right, no DREQ1), then three writes of 127 to the mono register.
- **Interrupt** (level 6 in the Slave's table): if the mono register is not FULL, run the active decoder until it is. Then flip TOCR bit 1 (Sega's workaround), clear the PWM interrupt, and read the clear register back.
- **Samples:** 8-bit unsigned, written as (*s* + 1) × 4, so 0-255 becomes 4-1,024. When nothing is playing it writes 508 (127 × 4) until FULL.
- **Compression:** both decoders build the output from a codebook. Each data byte picks a short block of samples from a 256-entry table. Each sample is played twice, so the data is effectively 11 kHz played at 22 kHz. The first decoder uses fixed 4-byte blocks, one data byte per 8 output samples. The second has blocks of a set length and starts a new codebook stored inline every so many bytes.

The cost is an interrupt per sample: about 22,000 a second, 367 a frame, each with an entry, an exit, Sega's TOCR flip and five accesses to 32X registers. With the dispatcher that is about 70 instructions; PicoDrive charges about 28,000 clocks a frame for them, roughly 7% of the Slave's time, and a console more <span class="tag emulator">emulator</span> [SWA, PicoDrive per-instruction profile of the attract mode] ([Case study: Star Wars Arcade](../patterns/case-study-starwars.md#what-it-leaves-on-the-table)).

Mortal Kombat II, from an outside studio, uses the same scheme on its Slave, with a different sample format and two voices [MK2, SH-2 code at `0x0600515A`-`0x06005168`, `0x06004F4C`-`0x060050FC`]:

- **Set-up:** three writes of `$201` (513) to the mono register, then cycle = `$413` (1,043, so 22,084 Hz), then control = `$0105`. The Slave unmasks only the PWM interrupt; it does nothing else.
- **Samples:** 6 bits each, packed four to three bytes. Each is played twice, so the data rate is half the output rate: about 8.1 KB of ROM per second of sound.
- **Two voices, mixed so they never need clamping.** One voice is written as 2*s* + 255, two as 2*a* + 2*b* + 1. With 6-bit samples (0 to 252 in steps of 4), the middle value 128 gives 511 or 513 either way, so the silence level hardly moves when a second voice starts, and the largest sum, 1,009, is still below the cycle.
- **Voice choice:** a new sound takes voice A if it is free, else voice B, else whichever voice was not started last.
- **Requests** come from the 68000 through `$A1512E` (see [Communication](communication.md#bulk-data-through-the-ports)), and the sample table is reached through a pointer at cartridge `$000970`.

After Burner Complete, which Rutubo Games programmed for Sega, splits the work differently: the interrupt only copies, and the mixing happens outside it [AB32X, SH-2 code at `0x060002E2`-`0x06000336`, `0x06000390`-`0x060003BA`, `0x060003C0`-`0x0600046E`]:

- **Set-up:** control `$0105`, cycle `$5C3` (1,475, so about 15,610 Hz).
- **Main loop:** whenever there is room in a 64-entry ring of stereo samples, the Slave mixes one more (see [Mixing](#mixing)) and appends it. When the 68000's tick arrives (see [Communication](communication.md#one-call-per-object)), it also steps the music sequencer.
- **Interrupt:** takes the next ring entry and writes it with a single `mov.l` to `0x20004034`, which sets the left and right pulse widths at once. Then the TOCR flip, the clear and its read-back. It writes one sample per interrupt and does not test FULL, so the FIFO only ever holds a sample or two.
- **Ring indices in the user break controller.** The read and write positions are kept in `0xFFFFFF40` and `0xFFFFFF42`, the address registers of the SH-2's hardware breakpoint unit, and a sample counter in `0xFFFFFF60`. With no break condition enabled they are just three spare on-chip words: no SDRAM access and no bus cycle for the Master to wait on. A program that also uses the breakpoint unit could not do this.

The interrupt stays short whatever the mixer does, and a late mixer only lets the ring run lower, as long as it catches up within 64 samples (about 4 ms).

Knuckles' Chaotix, from a Sega team, keeps the whole driver off the bus [CHAOTIX, SH-2 code at `0x06000284`-`0x060002FE`, `0x060001F8`; on-chip code from cartridge `$07FC00`]:

- **Set-up:** the Slave switches to two-way cache mode (CCR `$19`), copies 1 KB of code from the cartridge into on-chip RAM at `0xC0000000` and puts its stack at the top of it. The code sets control `$0105` and cycle `$417` (1,047, Sega's 22 kHz example) and fills both FIFOs with 0.
- **Interrupt:** the Slave's dispatcher sends the PWM level straight to `0xC0000004`. The handler does Sega's TOCR flip and clears the interrupt. It then works on every second interrupt only, by rotating a word of alternating bits and testing the bit that falls out.
- **Four voices**, one per communication port from `0x20004028` to `0x2000402E`. Each 8-bit sample is scaled by a 4-bit left and right volume taken from the request. Each working interrupt makes two output samples per channel: the first is the average of the previous and the new sample, the second the new sample. The pair is written with a FULL check between them.

Only the sample bytes and the PWM writes use the bus; code, stack and voice state are all in on-chip RAM. See [Audio across PWM, FM and PSG](../patterns/audio.md) for how its requests arrive.

### 2. DMA (d32xr)

With RTP = 1, the same event that raises the interrupt also raises DREQ1, and SH-2 DMA channel 1 can write the next sample without the CPU [32X-HWM p.64; §5.3, DMA controller settings]. Sega calls DREQ1 the same signal as the timer interrupt, so with TM = *n* it asks for a transfer once every *n* samples, not every sample <span class="tag manual">manual</span> [32X-HWM §3.4 p.56]. Since each request moves one sample, DMA feeding PWM needs TM = 1; with TM = 2 it would deliver half the samples the output plays. PicoDrive and Ares raise DREQ1 with the interrupt in the same way; MAME does not model it <span class="tag emulator">emulator</span> [PICODRIVE, pico/32x/pwm.c; ARES, md/m32x/pwm.cpp; MAME, src/mame/shared/mega32x.cpp]. Sega's register values for this are in [DMA controller](../sh2/dmac.md#channel-1-pwm).

d32xr's sound mixer, when built with DMA sound enabled, does this on the Slave [D32XR, marssound.c, marshw.c]:
- Control `$0185` (TM = 1, RTP on) and 22,050 Hz.
- Channel 1 writes one longword per DREQ1 to `0x20004034`, so left and right are fed together.
- Two buffers of 316 stereo samples (about 70 per second): the DMA-complete interrupt starts DMA on the buffer just mixed and mixes the other.

The CPU then wakes up 70 times a second instead of 22,000. The catch: per Sega, a CPU that feeds PWM must not use auto-request DMA, because interrupts are accepted late while it runs ([DMA controller](../sh2/dmac.md)). d32xr's default build turns this path off (`DISABLE_DMA_SOUND`) [D32XR, Makefile].

### 3. From the 68000

The 68000 can feed PWM too. d32xr's 68000 main loop plays the samples of its VGM music: while the mono register is not FULL, it writes the next 8-bit sample, converted to signed and added to the centre (*c* / 2) [D32XR, src-md/crt0.s, src-md/vgm.c]. It sets control to `$05` from the 68000 side, which leaves TM and RTP as the SH-2s left them. Polling only works while the loop comes round faster than three samples; anything that holds the 68000 up stalls the sound.

S32X-SKILL's tracker player polls in the same way from an SH-2. Its notes warn that a full frame buffer redraw every frame then starves the FIFO into a frame-rate buzz [S32X-SKILL, audio.md] <span class="tag emulator">emulator</span>.

Motocross Championship, a retail game, feeds PWM from the 68000's line interrupt instead, set to every second line. Each interrupt waits for room and writes one sample to each channel, one voice per speaker, at a cycle of `$5B9` (15,718 Hz). It cost about 30% of the 68000 in a PicoDrive run, and since the line interrupt stops during vertical blank, the FIFO runs dry for about 2.4 ms in every frame <span class="tag emulator">emulator</span> [MCX, 68000 code at `$00081A`-`$0008C6`, `$000E18`]. Details in [Audio across PWM, FM and PSG](../patterns/audio.md#motocross-championship-pwm-from-the-68000).

## Mixing

PWM has no channels beyond left and right: any more voices are mixed in software. d32xr sizes its arithmetic so the result lands in range with no division [D32XR, sh2_mixer.s, marssound.c]:

- Each 8-bit sample becomes a signed 16-bit value ((*s* − 128) × 256).
- Each voice's left and right volumes are (255 − pan) and pan, times volume and a master scale, divided by 1,024. A full-volume voice therefore swings about ±510 after a final divide by 65,536.
- The mixed sum gets the centre (515) added and is clamped to 2-1,032.

After Burner Complete mixes 16 voices on its Slave, one stereo sample at a time [AB32X, SH-2 code at `0x060003C0`-`0x0600046E`]:

- **Position from a counter, not a running sum.** Each voice stores the global sample count at which it started and a 16.16 step. Its position is (count − start) × step, one `dmuls.l`. Pitch errors cannot build up, and a voice can be moved to any point by changing its start.
- **Linear interpolation.** The top half of the position picks two neighbouring 8-bit samples, and the top 8 bits of the fraction blend them: *s*₀ + ((*s*₁ − *s*₀) × *f*) / 256, one `muls.w`.
- **Volume and pan in one longword.** Left and right volumes are the two halves of one register; two `muls.w` produce the left and right contributions, added into two sums.
- **Scaling without a divide.** Each sum is multiplied by `$733C0` with `dmuls.l` and only MACH, the top 32 bits, is kept, which divides by about 9,100. Then the centre, 737, is added, and a result of 0 or below becomes 1. The code also tests for 1,474, the top of the range, but its branches skip that test for every positive value, so it never fires; a mix above the cycle would go to the PWM as it is, where by the manual it clips anyway [AB32X, SH-2 code at `0x06000442`-`0x0600045C`].
- **Per-voice behaviour through a pointer.** Each voice record holds the address of its own step routine; a finished voice switches its pointer to a routine that returns silence.

Sega's planned PWM driver offered 8-bit samples up to 44.1 kHz, looping, 32 volume steps and 3-cent pitch steps [32X-OV, PWM sound driver]. Its 68000 sound driver lists four PWM voices, and notes that a PWM sound, once started, cannot be stopped channel by channel [SND-V3, specifications].

## Traps

- **Pulse width 0 is full volume, not silence.** Clamp to at least 1. The manual says so, and the shipped mixers behave as if it were true: Star Wars Arcade never writes below 4, Mortal Kombat II's floor is 1, and After Burner Complete turns 0 or below into 1. Ares and MAME play 0 as silence, so a mixer that writes 0 sounds right there <span class="tag disputed">disputed</span> ([discrepancy 24](../appendices/discrepancies.md)).
- **Cycle 1 stops PWM.** Cycle 0 gives the longest period, not the shortest.
- **Turn an output on before waiting for FULL to clear.**
- **Ramp to the centre at start-up.** The output rests at 0, and jumping straight to *c* / 2 clicks. d32xr writes 1 three times, then ramps from its minimum to the centre over about two seconds, "to avoid click in audio (real 32X)" [D32XR, marshw.c]. Star Wars Arcade instead puts 127 in the FIFO and jumps to its silence level, 508, at the first interrupt. Mortal Kombat II fills the FIFO with its silence level, 513, before it turns the outputs on, so its one jump happens the moment the outputs start [MK2, SH-2 code at `0x0600515A`]. Knuckles' Chaotix turns the outputs on and then fills both FIFOs with 0, which by the manual is the maximum, before its first interrupt brings the level to its silence value, 512 [CHAOTIX, cartridge `$07FC08`-`$07FC32`].
- **Leave headroom when mixing with FM.** Sega raised the PWM output level on later boards to balance it with FM, and warned that with both at full volume the mix distorts. PWM distorts first at its peaks, because of its wider dynamic range [32X-TI item 20].
- **Early 32X chips.** The 315-5780 had a PWM bug and was to be replaced. It appeared on development hardware [32X-TI item 11].

## In emulators

- **PicoDrive** applies the − 1 to pulse width and cycle and clips at the cycle, as the manual describes. It keeps draining the FIFO when both outputs are off, against the manual; its source cites a test ROM ("mars test disagrees") without naming it. Sega's Mars Check Program is not a case of this: before each of its FIFO tests, on the 68000 and on the SH-2, it switches on the output it is testing (control `$01`, `$04` or `$05`), so it never runs the FIFO with both outputs off [MARS-CHECK, 68000 code at `$001CAA`-`$001E82`, SH-2 code at `0x06000AB0`-`0x06000CEE`]. Its mono register reports the right channel's FULL and EMPTY. An option, `POPT_PWM_IRQ_OPT`, adjusts the interrupt rate to save time, which changes when interrupts arrive <span class="tag emulator">emulator</span> [PICODRIVE, pico/32x/pwm.c].
- **Ares** stops the counter when both outputs are off, as the manual says. It stores pulse widths without the − 1, so 0 plays as the minimum instead of the maximum ([discrepancy 24](../appendices/discrepancies.md)). Its mono register reports FULL if either FIFO is full. It filters out the DC offset, which hides start-up clicks. It raises the PWM interrupt on both SH-2s, and DREQ1 when RTP is set <span class="tag emulator">emulator</span> [ARES, md/m32x/pwm.cpp, md/m32x/io-internal.cpp].

- **MAME** writes each pulse width straight to a 12-bit DAC, with no − 1 and no clip at the cycle, so 0 plays as the minimum, as in Ares. A cycle of 0 is treated as 4,095, and a cycle of 1 or both outputs off stops the timer, as the manual says. Its mono register reports FULL only when both FIFOs are full, and EMPTY only when both are empty. It has no DREQ1 <span class="tag emulator">emulator</span> [MAME, src/mame/shared/mega32x.cpp].

So a click, a wrong value for 0, or a hang waiting for FULL can each be missing from one emulator and present in another, or on the console.

## Open questions

- Does the FIFO keep draining when both outputs are off ([discrepancy 23](../appendices/discrepancies.md))?
- What does the mono register's FULL bit report when the two FIFOs differ? PicoDrive reports the right channel's, Ares FULL if either is full, MAME FULL only if both are; Sega's diagnostic only tests the two FIFOs filled together.
- How large is the start-up click on a console, and does Star Wars Arcade's start at 127 avoid it?

## Sources

- [32X-HWM](../appendices/bibliography.md#32x-hwm): §1, §3.2.1 PWM registers, §3.4 pp.56-57 (DREQ1 is the interrupt signal, p.56), p.64, §5.3
- [32X-TI](../appendices/bibliography.md#32x-ti): items 11, 19, 20
- [32X-OV](../appendices/bibliography.md#32x-ov): hardware specifications, PWM sound driver
- [SND-V3](../appendices/bibliography.md#snd-v3): specifications
- [MK2](../appendices/bibliography.md#mk2): SH-2 code at `0x06004F4C`-`0x060051E0`
- [AB32X](../appendices/bibliography.md#ab32x): SH-2 code at `0x060002E2`-`0x06000336`, `0x06000390`-`0x0600046E`
- [MAME](../appendices/bibliography.md#mame): src/mame/shared/mega32x.cpp
- [SWA](../appendices/bibliography.md#swa): SH-2 code at `0x0600095C`-`0x06000AAE`, Slave interrupt table at `0x06000540`
- [CHAOTIX](../appendices/bibliography.md#chaotix): SH-2 code at `0x060001F8`, `0x06000284`-`0x060002FE`; on-chip code from cartridge `$07FC00`
- [MCX](../appendices/bibliography.md#mcx): 68000 code at `$00081A`-`$0008C6`, `$000E18`
- [MARS-CHECK](../appendices/bibliography.md#mars-check): PWM FIFO tests, 68000 code at `$001CAA`-`$001E82`, SH-2 code at `0x06000AB0`-`0x06000CEE`
- [D32XR](../appendices/bibliography.md#d32xr): marshw.c, marssound.c, sh2_mixer.s, Makefile, src-md/crt0.s, src-md/vgm.c
- [S32X-SKILL](../appendices/bibliography.md#s32x-skill): audio.md, architecture.md
- [PICODRIVE](../appendices/bibliography.md#picodrive): pico/32x/pwm.c
- [ARES](../appendices/bibliography.md#ares): md/m32x/pwm.cpp, md/m32x/io-internal.cpp
