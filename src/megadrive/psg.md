# PSG (SN76489)

The PSG is the Mega Drive's simple sound chip: three square-wave channels, one noise channel, and a volume control on each. It is built into the VDP rather than being a separate chip, and it is a close copy of the Texas Instruments SN76489 that Sega had already used in the Master System [MD-SWM, PSG chapter; GENVDP §18]. Everything about it is set with single-byte writes to one port. This page covers the port, the byte formats, how to get pitches and volumes out of it, and the noise channel. How the PSG fits into a sound driver is in [The Z80 and sound](sound.md).

## At a glance

| | |
|---|---|
| Channels | Tone 1, tone 2, tone 3 (square waves); noise |
| Port | `$C00011` from the 68000, `$7F11` from the Z80. Byte writes |
| Clock | Same as the Z80: 3,579,545 Hz NTSC, 3,546,895 Hz PAL ([clocks](architecture.md#clocks)) |
| Pitch | 10-bit period per tone channel. Lowest note about 109 Hz |
| Volume | 4-bit attenuation per channel, 2 dB steps, 15 = off |
| Reading back | Not possible. The port is write-only |
| Bus request | Not needed from either CPU |

Sources: [MD-TO pp.119-120; MD-SWM, sound software manual §IV; GENVDP §3].

What it does **not** have matters as much as what it has:

- **No envelopes.** A note's volume stays where you set it until you write a new one. Attack, decay and fades are done in software, one write per channel per frame. Sega's own driver says so in its feature list [SND-V3, specifications].
- **No stereo.** The VDP has a single PSG output pin, mixed into both sides [GENVDP §18].
- **No timers or interrupts.** The driver's timing comes from the vertical interrupt or from the YM2612's timers.

## Where to write it

The 68000 writes `$C00011`; the Z80 writes `$7F11`. Both can write at any time without a bus request, and both can write the same chip, so if both do, the program has to decide who writes when <span class="tag manual">manual</span> [MD-SWM, sound software manual §IV]. The PSG also answers at the next three odd addresses, `$C00013`, `$C00015` and `$C00017` (`$7F13-$7F17` for the Z80) [GENVDP §3]. Use the main address.

Use **byte writes** to the odd address. Every source and every driver we have read does. A word write to `$C00010` is a gamble: Seaborne's reference sheet says only its high byte reaches the PSG, though its own example writes bytes to `$C00011`, while every emulator we read sends the low byte <span class="tag disputed">disputed</span> ([discrepancy 16](../appendices/discrepancies.md)) [MD-REF, VDP registers; PICODRIVE, pico/memory.c].

The port is **write-only**, so a driver cannot ask the chip what it is playing. Keep a copy of the last value written to each channel in RAM and work from that.

**During DMA.** While a VRAM fill or copy runs, the 68000 keeps running and may still write the PSG, though not the VDP's data or control port <span class="tag manual">manual</span> [MD-TO p.42; GENVDP §11]. During a DMA from 68000 memory the 68000 is stopped, so its PSG writes wait until the transfer ends.

**On the 32X.** The Z80's PSG write is carried out on the 68000's bus at `$C000xx` [32X-TI item 22]. That is why the 32X rule on the Z80's bank register applies to PSG writes: the bank must point outside `$000000-$3FFFFF` and `$840000-$9FFFFF` when the Z80 writes the PSG <span class="tag manual">manual</span> [32X-TI item 22]. [The Z80 and sound](sound.md#the-rules) has the details. Writes from the 68000 are not affected.

**A note on Sega's PSG pages.** They talk about "output port `$7F`" and end with a code example that the "Mk3" runs at power-on [MD-TO pp.43, 119-120; MD-SWM, PSG chapter]. Both are left over from the Master System (Mark III) manual, where the PSG sits on Z80 I/O port `$7F`. On the Mega Drive there is no such port; use the addresses above.

## Register writes and the latch byte

The PSG has eight registers: a period and an attenuation for each tone channel, and a control byte and an attenuation for the noise channel. They are all written through the one port, with two kinds of byte.

| Byte | Bit 7 | Bits 6-5 | Bit 4 | Bits 3-0 |
|------|-------|----------|-------|----------|
| Latch byte | 1 | Channel: 0-2 tone 1-3, 3 noise | 0 = period or noise control, 1 = attenuation | Data: low 4 bits |
| Data byte | 0 | Bit 6 unused, write 0. Bit 5 and bits 4-0: high 6 bits of a period | | |

Source: [MD-TO pp.119-120].

A **latch byte** (bit 7 set) chooses a register and writes its low four bits. The chip remembers which register was latched last, and a **data byte** (bit 7 clear) goes to that register. In practice this gives eight starting values for the latch byte:

| Latch byte | Register | Bytes to write |
|------------|----------|----------------|
| `$80 + n` | Tone 1 period | Two: latch with the low 4 bits, then data with the high 6 |
| `$90 + a` | Tone 1 attenuation | One |
| `$A0 + n` | Tone 2 period | Two |
| `$B0 + a` | Tone 2 attenuation | One |
| `$C0 + n` | Tone 3 period | Two |
| `$D0 + a` | Tone 3 attenuation | One |
| `$E0 + c` | Noise control | One |
| `$F0 + a` | Noise attenuation | One |

Sources: [MD-TO pp.119-120]. Sega names the channels 1-3; drivers usually count from 0. Sega's Sound Driver V3 even identifies its PSG channels by these latch values: `$80`, `$A0`, `$C0` and `$E0` for the noise [SND-V3, identifying sound sources].

Sega's pages document only the forms in this table: two bytes for a period, one byte for everything else. Code that sticks to them depends on nothing else. In PicoDrive, a data byte that follows an attenuation or noise latch rewrites that register's low four bits, and a lone data byte after a period latch changes only the high six bits of the period <span class="tag emulator">emulator</span> [PICODRIVE, pico/sound/sn76496.c]. The second case can save a write in a vibrato loop, but only if nothing else has latched another register in between.

### Writing a period

Split the 10-bit period: the low four bits go into the latch byte, the high six into the data byte. This is the 68000 version, the same shape as the period update in Star Wars Arcade's sound driver [SWA, ROM `$00F2D0`]:

```asm
; d0.w = period (1-1023), d1.b = $80, $A0 or $C0 for tone 1, 2 or 3
psg_set_period:
        move.b  d0,d2
        andi.b  #$0F,d2
        or.b    d1,d2           ; latch byte: channel and low 4 bits
        lsr.w   #4,d0
        andi.b  #$3F,d0         ; data byte: high 6 bits
        move.b  d2,$C00011
        move.b  d0,$C00011
        rts
```

Aerobiz Supersonic's Z80 driver does the same with two `ld ($7F11),a` instructions in a row [AB-DISASM, Z80 driver at sound RAM `$084D`].

### The one hazard: something writing between the two bytes

The latch is shared state. If anything else writes the PSG between a latch byte and its data byte, the data byte lands in whatever register the other writer latched last. Say the main program writes the latch byte for tone 1's period, and the vertical interrupt handler then runs and writes `$B4` (tone 2 attenuation). The main program's data byte now goes into tone 2's attenuation, and tone 1 keeps half of its new period. The same happens if the 68000 and the Z80 both write.

So:

- **Give the PSG one owner.** Aerobiz, once Sega's start-up code has run, writes it only from the Z80 [AB-DISASM, Z80 driver].
- **If an interrupt handler writes the PSG, nothing else may**, or the other code must mask interrupts across each pair of bytes.

Between the two bytes the channel briefly plays with the new low bits and the old high bits <span class="tag emulator">emulator</span> [PICODRIVE, pico/sound/sn76496.c]. With the writes back to back that lasts a few microseconds and cannot be heard.

## Pitch

A tone channel counts its period down at one sixteenth of the PSG clock and flips its output each time the count runs out. A full cycle of the square wave is therefore 32 × period clocks:

> pitch = clock ÷ (32 × period), period from 1 to 1023

Sega's pages describe the countdown and say that a larger value gives a lower pitch, but give neither the clock nor this formula [MD-TO p.119]. The formula is PicoDrive's model <span class="tag emulator">emulator</span> [PICODRIVE, pico/sound/sn76496.c], and Sega's note table fits it: its first entry, 854, is 131.0 Hz (C3, 130.8 Hz), and its 22nd, 254, is 440.4 Hz (A4). The same table sits in both Star Wars Arcade and Virtua Racing Deluxe [SWA, ROM `$00F4DE`; VRD-NOTES, ROM `$030FE0`].

To build a table, compute `period = round(clock / (32 × pitch))` for each note, with the NTSC clock of 3,579,545 Hz.

| Period | Pitch (NTSC) | Note | One step of the period moves the pitch by |
|--------|--------------|------|------------------------------------------|
| 1023 | 109.3 Hz | about A2 | 1.7 cents |
| 854 | 131.0 Hz | C3 | 2.0 cents |
| 254 | 440.4 Hz | A4 | 6.8 cents |
| 127 | 880.8 Hz | A5 | 13.7 cents |
| 64 | 1,748 Hz | A6 | 27 cents |
| 27 | 4,143 Hz | about C8 | 65 cents |
| 10 | 11,186 Hz | | 182 cents |

A cent is a hundredth of a semitone. The table shows the PSG's three pitch problems:

- **Nothing below about 109 Hz.** The period cannot go past 1023. Bass parts either move up whole octaves or go to the FM chip. A converter that clamped low notes to the floor instead gave errors of almost 900 cents, nearly a ninth [S32X-SKILL, audio.md]. The noise channel can play lower, using tone 3 (see [below](#noise-pitched-by-tone-3)).
- **The top end goes out of tune.** The period's steps are fixed, so the higher the note, the coarser the tuning. Above about 2 kHz the nearest period can be a third of a semitone off, and above 4 kHz more than half. A music converter can measure how far each part would land from the right pitch and use that to decide which parts go to the PSG [S32X-SKILL, audio.md].
- **PAL consoles play flat.** Their PSG clock is 0.9% slower, so the same period sounds 16 cents (about a sixth of a semitone) lower. Against FM music that is tuned separately the difference can be heard. A driver that cares keeps a second table computed with 3,546,895 Hz.

A period of 0 is not described by Sega. PicoDrive plays it as 1 <span class="tag emulator">emulator</span> [PICODRIVE, pico/sound/sn76496.c]. Do not use it. Periods below about 5 are above the range of hearing.

## Volume

Each channel has a 4-bit **attenuation**: how far below full volume it plays. 0 is loudest, each step is 2 dB quieter, and 15 switches the channel off [MD-TO p.120].

| Attenuation | 0 | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 | 11 | 12 | 13 | 14 | 15 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| dB | 0 | −2 | −4 | −6 | −8 | −10 | −12 | −14 | −16 | −18 | −20 | −22 | −24 | −26 | −28 | off |
| Relative amplitude | 1.00 | 0.79 | 0.63 | 0.50 | 0.40 | 0.32 | 0.25 | 0.20 | 0.16 | 0.13 | 0.10 | 0.08 | 0.06 | 0.05 | 0.04 | 0 |

The amplitude row is computed from the decibels. Every three steps halves the amplitude.

What follows for code:

- **Higher numbers are quieter.** A driver that stores volume as loudness, 15 = loudest, has to invert it on the way out. Aerobiz's Z80 driver does this with `cpl` and `and $0F`, giving 15 − volume [AB-DISASM, Z80 driver at sound RAM `$065B`, `$0AA8`].
- **Volumes combine by adding.** Because each step is a fixed number of decibels, a note's envelope, the channel's volume and a master fade combine by adding their attenuations and clamping at 15.
- **Envelopes are tables.** A software envelope is a list of attenuations, one per frame, with a code for "loop" or "hold". Sega's V3 driver uses the PSG "timbre" number to pick one [SND-V3, identifying sound sources].

### Silencing it

Writing `$9F`, `$BF`, `$DF` and `$FF` sets all four attenuations to 15. Sega's standard initial program does this at start-up, and both retail ROMs we have carry those four bytes in it [MD-REF, PSG clear; AB-DISASM, ROM `$2F6`; VRD-NOTES, ROM `$50E`]. See [the code at `$200`](../howto/md-header.md#the-code-at-200) and, on the 32X, [Sega's initial program](../32x/boot.md#segas-initial-program-on-the-68000). A sound driver should do it again whenever it resets, and on pause, so that a held note does not drone on: Sega's own pages recommend that <span class="tag manual">manual</span> [MD-TO p.43]. Star Wars Arcade's sound driver has a routine that writes exactly these four bytes [SWA, ROM `$00F48C`], and Aerobiz's Z80 driver loops over the four channels to do the same [AB-DISASM, Z80 driver at sound RAM `$02F7`].

## Noise

The noise channel's control byte has three bits:

| Bit | Name | Meaning |
|-----|------|---------|
| 2 | FB | 0 = periodic noise, 1 = white noise |
| 1-0 | NF | Rate: 0, 1 or 2 = fixed; 3 = follow tone 3 |

Written as `$E0 + FB × 4 + NF`, so `$E4-$E7` are the white noise settings and `$E0-$E3` the periodic ones [MD-TO p.120].

The noise comes from a **shift register**: a row of bits that moves one place at each tick of the noise clock, with the bit that drops out at one end being the output. In PicoDrive's model of Sega's PSG it is 16 bits long <span class="tag emulator">emulator</span> [PICODRIVE, pico/sound/sn76496.c]:

- **White noise** feeds the XOR of two bits (0 and 3) back into the top. The pattern repeats only after 57,337 ticks, which sounds like hiss.
- **Periodic noise** puts the dropped bit straight back in the top. A single 1 bit circles round the 16 places, so the output is a narrow pulse once every 16 ticks: a buzzy tone at one sixteenth of the noise rate.

Texas Instruments' own SN76489 uses a 15-bit register with different feedback, which is why noise taken from other machines' sound logs sounds different on a Mega Drive [PICODRIVE, pico/sound/sn76496.c].

### Rates

Sega's table gives the three fixed rates as "clock ÷ 2, ÷ 4, ÷ 8" without saying which clock [MD-TO p.120]. In PicoDrive the register ticks at the PSG clock divided by 512, 1024 or 2048 <span class="tag emulator">emulator</span> [PICODRIVE, pico/sound/sn76496.c]. At NTSC that is:

| NF | Shift rate | Periodic noise pitch | Character |
|----|------------|----------------------|-----------|
| 0 | 6,991 Hz | 437 Hz | Highest, finest hiss |
| 1 | 3,496 Hz | 218 Hz | |
| 2 | 1,748 Hz | 109 Hz | Lowest, coarsest |
| 3 | Tone 3's pitch | Tone 3's pitch ÷ 16 | Follows tone 3's period |

### Writing the control byte restarts the noise

In PicoDrive every write to the noise control register reloads the shift register, even when the value is unchanged <span class="tag emulator">emulator</span> [PICODRIVE, pico/sound/sn76496.c]. Use this on purpose: writing the control byte at the start of each drum hit makes every hit start the same way. Avoid it by accident: a driver that rewrites the control byte every frame restarts periodic noise 60 times a second, which adds a buzz.

### Noise pitched by tone 3

With NF = 3 the noise ticks once per cycle of tone 3, so changing tone 3's period changes the noise. Sega suggests it for sweeps such as a jet engine winding up [MD-TO p.120]. Two uses come out of it:

- **Pitched noise.** White noise that follows tone 3 can be tuned for drums, or slid for engines and explosions. Aerobiz's Z80 driver works this way: one routine writes tone 3's period and then `$E7`, white noise following tone 3 [AB-DISASM, Z80 driver at sound RAM `$0866`].
- **Bass below the tone channels.** Periodic noise that follows tone 3 plays at clock ÷ (512 × period), sixteen times lower than tone 3 itself, down to about 7 Hz. For a note at pitch *f*, use tone 3 period = clock ÷ (512 × *f*); 55 Hz (A1) needs 127. The tuning steps are those of tone 3 four octaves up, so the bass is as well tuned as tone 3's mid range.

Either way, tone 3 still plays its own square wave. Set its attenuation to 15: the noise keeps following tone 3's period while tone 3 is silent <span class="tag emulator">emulator</span> [PICODRIVE, pico/sound/sn76496.c]. The cost is one tone channel, so the PSG is down to two tones and the noise. A driver has to treat tone 3 and the noise as a pair: whatever takes over one of them, a sound effect for example, has to silence or set up the other too.

## Open questions

- What does a period of 0 do on a real Mega Drive?
- Is the shift register really 16 bits with feedback from bits 0 and 3 on the Mega Drive's PSG, as PicoDrive models it, and does every control write reload it?
- Do data bytes after an attenuation or noise latch behave as PicoDrive models them?
- Which byte of a word write to `$C00010` reaches the PSG ([discrepancy 16](../appendices/discrepancies.md))?
- How long is a Z80 PSG write held up by a DMA from 68000 memory, given that it is carried out on the 68000's bus?
- What state is the PSG in at power-on, before Sega's initial program silences it?
- How loud is the PSG compared with the YM2612, and does that differ between console models?

## Sources

- [MD-TO](../appendices/bibliography.md#md-to): pp.119-120 (tone, noise, attenuators), p.43 (attenuation bytes, silencing example), p.42 (PSG access during DMA), §1 memory map
- [MD-SWM](../appendices/bibliography.md#md-swm): PSG chapter; sound software manual §IV
- [MD-REF](../appendices/bibliography.md#md-ref): VDP registers table; PSG clear
- [GENVDP](../appendices/bibliography.md#genvdp): §3 port map, §11 DMA, §18 pinout
- [SND-V3](../appendices/bibliography.md#snd-v3): specifications; identifying sound sources
- [32X-TI](../appendices/bibliography.md#32x-ti): item 22
- [PICODRIVE](../appendices/bibliography.md#picodrive): pico/sound/sn76496.c, pico/memory.c
- [S32X-SKILL](../appendices/bibliography.md#s32x-skill): audio.md
- [VRD-NOTES](../appendices/bibliography.md#vrd-notes): ROM (Sega's initial program, note table)
- [SWA](../appendices/bibliography.md#swa): ROM `$00F2D0` (period write), `$00F486` (mute), `$00F4DE` (note table)
- [AB-DISASM](../appendices/bibliography.md#ab-disasm): Z80 sound driver (ROM `$2696-$3BE7`, loaded at sound RAM `$0000`); Sega's initial program
