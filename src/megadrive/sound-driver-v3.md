# Sega's Sound Driver V3

When the 32X arrived, Sega shipped a sound driver with it: a 68000 program, with its own Z80 companion, that drives every sound source in the machine — the YM2612, the PSG, the 32X's PWM channels and up to two sample channels — behind one interface and one set of tempo, volume and vibrato rules. This page is the reference: what the driver costs, how it is started, its system calls, its request-number and sequence language, its data formats, and the quirks that matter when using it. The design trade-offs against writing a driver yourself are in [The Z80 and sound](sound.md#segas-v3-sequencing-on-the-68000-samples-on-the-z80).

The source is Sega's preliminary specification [SND-V3], marked as such, and it shows: the title says version 3.00, the introduction 3.03, and one usage example contradicts the document's own request-number table (see [Quirks](#quirks)). The tables below follow the document's specification tables, not its examples.

## What the driver takes

| | |
|---|---|
| Sound sources | FM 5 or 6 channels; PSG 3 tone + 1 noise; PWM 4 channels; PCM 0-2 channels, 8-bit linear or Sega 4-bit delta |
| ROM | About `$3000` bytes including the Z80 part; about `$1300` less if PCM is not used |
| Work RAM | About `$B00` bytes, at `$FFF000` (fixed) |
| 68000 load | About 1% idle, about 9% while music plays, about 0.5% per playing effect channel |
| Z80 load | 100% — the Z80 belongs to the driver |
| Tracks | Music 14-16 (it depends on the PCM driver), effects 5 (fixed) |

Sources: [SND-V3, specifications and notes]. <span class="tag manual">manual</span>

The driver's selling point in its own specification is uniformity: a software envelope for the PSG and two kinds of software vibrato exist so that a note behaves the same whichever chip plays it, and an FM channel can be turned into a drum kit [SND-V3, specifications].

## Running it

Two obligations, and only two [SND-V3, activating the sound driver]:

1. At start-up, call system call `$00` (initialise) with the machine's video standard.
2. Call the driver's entry point **every vertical interrupt**, about every 16 ms. The driver does a frame of sequencing and chip writing per call.

The driver code can sit anywhere the 68000 can execute it. The work space is fixed at `$FFF000` <span class="tag manual">manual</span> [SND-V3, notes], and the last `$200` bytes of it are the YM2612 write buffer — the driver batches its register writes there, which is why a 68000-side driver does not have to hold the Z80 bus per write.

A block of fill-in data at driver start + `$0C` ties the driver to its data: work space address and size, the PCM format, the number of channels per sound source, track totals, and a version string [SND-V3, fill-in data]. In Sega's toolchain this block was filled in when linking; the driver reads it rather than embedding constants, which is what lets one driver binary serve games with different channel layouts.

## System calls

Number in `d0`, arguments in `d1`, then `jsr` to the driver's start address plus 8 [SND-V3, how to call]. Calls may also be issued by writing request numbers into the data stream (next section), which is how music triggers effects on its own.

| # | Call | `d1` argument | Clobbers |
|---|------|---------------|----------|
| `$00` | Initialise driver and hardware | 0 NTSC, 1 PAL | — |
| `$01` | Request music | Music number | `d0`/`a0` |
| `$02` | Request effect | Effect number | `d0`/`a0` |
| `$03` | Fade in or out | Depth in the high byte, speed in the low | — |
| `$04` | Music master volume | `$00` loudest to `$7F` muted | — |
| `$05` | Effect master volume | as `$04` | — |
| `$06` | Music master transpose | Semitones, two's complement | — |
| `$07` | Effect master transpose | as `$06` | — |
| `$08` | Pause | — | — |
| `$09` | Unpause | — | — |
| `$0A` | Write communication byte | The byte | — |
| `$0B` | Read communication byte | — (returns in `d1`) | — |
| `$0C` | Stop music | — | `d0`/`a0`/`a2` |
| `$0D` | Stop effects | — | — |

Source: [SND-V3, list of system calls]. The volume convention is inverted like the YM2612's own: zero is loudest. A fade's depth is negative (two's complement) to fade in; its speed runs `$00-$7F` in vertical-interrupt units. The request pipe is four entries deep, shared by music and effects, so at most four requests take effect per frame — and the numbers are not range-checked, so an out-of-range effect number can start a piece of music [SND-V3, details on system calls].

A minimum session: initialise for NTSC, request music `$80` (the first music number), set music volume to `$20`, ask for effect `$10`, then fade out with depth `$08`, speed `$10`:

```asm
    moveq   #$00,d0         ; initialise
    moveq   #$00,d1         ; NTSC
    jsr     SoundDriver+8
    moveq   #$01,d0         ; request music
    moveq   #$80,d1
    jsr     SoundDriver+8
    moveq   #$04,d0         ; music master volume
    moveq   #$20,d1
    jsr     SoundDriver+8
    moveq   #$02,d0         ; request effect
    moveq   #$10,d1
    jsr     SoundDriver+8
    moveq   #$03,d0         ; fade out
    move.w  #$0810,d1       ; depth $08, speed $10
    jsr     SoundDriver+8
```

## Request numbers

Request numbers are one byte, split by range [SND-V3, data request numbers]:

| Range | Meaning |
|-------|---------|
| `$01-$7F` | Effect number |
| `$80-$EF` | Music number |
| `$F0-$FD` | Effect command: fade in/out, stop music, stop effects, pause/unpause, master transpose up/down, master volume up/down — one step each |
| `$FE`/`$FF` | Initialise the driver |

The `$F0` range exists so that a single request byte can perform the small operations without a register-setting call — useful from scripts and from the communication channel.

## The sequence language

Music and effect data are byte streams the driver interprets per channel. The shape [SND-V3, details of sequence commands]:

- **Notes are length and pitch apart.** `$01-$7F` is a note length; `$81-$8C` is a scale step (C to B) in the current octave; `$80` is a rest. Octave commands set and move it (`$EA` absolute, `$EB`/`$EC` up and down, no overflow check).
- **Per-voice expression.** Velocity `$D0-$DF` (sixteen steps, added to the volume, from `$3C` at `D0` down to `$00` at `DF`), absolute and relative volume `$E1`/`$E2`, pan `$E3` (FM and PWM only), detune `$E4` in 1/32-semitone units, portamento `$E5`, pitch bend `$E7` (13-bit after an internal 3-bit shift), table vibrato `$E8` and its switch `$E9`, timbre and envelope change `$E0`.
- **Flow control.** Subroutine jump and return `$F3`/`$F4` (first in, first out), repeat loops `$F5`-`$FA` with three nesting levels, and end-of-track `$FF`, which can loop to a `$FE` marker.
- **Tempo** `$F0` takes separate NTSC and PAL values; PAL is the NTSC value times 6/5, and effects are fixed at tempo 150 [SND-V3, F0].
- **Escape hatches.** `$C5` writes any YM2612 register directly, `$C2` pokes the work space, `$C6` turns an FM channel into drum mode, `$EE` carries per-source commands (FM channel 2's special mode, FM channel 6's FM/PCM switch, PSG noise, PWM Qsound on/off). Sega points to the YM2612 Application Manual and Tone Editor Manual for these — documents not in this book's sources — and disclaims responsibility for work-space damage from `$C2` and register damage from `$C5`.

## Sound source IDs

A music file names its channels by ID [SND-V3, identifying sound sources]:

| Source | IDs | Source | IDs |
|--------|-----|--------|-----|
| FM 0-2, 4, 5 | `$00`, `$01`, `$02`, `$05`, `$06` | FM 3 | `$04` |
| PCM 0, 1 | `$40`, `$41` | PWM 0-3 | `$08`, `$0A`, `$0C`, `$0E` |
| PSG 0-2 | `$80`, `$A0`, `$C0` | PSG noise | `$E0` |

## Data layout

One top vector, eight offset addresses in 4 bytes each, points at everything: PCM and PWM information, music, effects, envelope and vibrato tables, the FM rhythm kit and the FM timbres [SND-V3, sound data]. Notable pieces:

- **PCM blocks** hold a playback speed that the document calls a Z80 weight value, not a sampling rate, a 4-byte address and a 2-byte size — and the two-byte fields are **little-endian**, unlike everything else the 68000 side reads.
- **Music information** stores NTSC and PAL tempo together, then per-channel blocks: PCM, FM 0-5 (FM 5 optional), PSG 3+noise, PWM 0-3.
- **Effect information** states how many channels it needs and its priority, then per-track setup — so the driver can refuse an effect that would starve the music.
- **Envelope and vibrato tables** are `$100` bytes each, values plus four loop commands (`$80` restart, `$81` hold, `$82` jump, `$83` neutral or key-off). Vibrato values are two's complement around 0.
- **An FM timbre is 25 bytes**, partially packed so the driver can write them more or less straight into YM2612 registers, in slot order 1, 3, 2, 4.

## Quirks

Collected for anyone wiring this driver into a build today:

- **Volume is inverted** everywhere: `$00` loudest, `$7F` silent — the YM2612's convention, applied to every source. The per-source notes table admits some sources cannot reach every level [SND-V3, notes].
- **The request pipe is four deep, shared, and unchecked.** More than four requests in one frame are dropped; a mis-numbered request plays the wrong kind of thing.
- **PWM channels cannot be stopped individually** — the pause and stop calls each carry a note saying so, because the PWM hardware has no per-channel key-off [SND-V3, `$08`, `$0C`, `$0D`].
- **FM channel 6 versus the DAC** is chosen by leaving the FM 5 track empty or with command `$EE` [SND-V3, notes].
- **The specification is preliminary and not self-consistent.** Its title page says 3.00 and its introduction 3.03; its worked example requests "SE number `$80`", which by its own table is the first *music* number. The tables, not the examples, are authoritative here.
- **Qsound for PWM is named but not explained** — a pan-pot value in MIDI units (`$00`-`$40`-`$7F`) switches on with `$EE`; the details sit in manuals this book does not have.

## Open questions

- No 32X game in this book's sources is identified as shipping V3. Which titles used it, and whether the shipped binary matches this preliminary specification, is unverified.
- What "Qsound" positioning actually does on the PWM channels, and what the Tone Editor's drum mode (`$C6`) produces.

## Sources

- [SND-V3](../appendices/bibliography.md#snd-v3): specifications, activation, memory maps, fill-in data, system calls, request numbers, sequence commands, sound source IDs, sound data, notes, usage example
- [The Z80 and sound](sound.md): V3's place among the four driver designs
- [PWM audio](../32x/pwm.md): the PWM channels V3 drives
