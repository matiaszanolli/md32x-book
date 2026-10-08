# The Z80 and sound

The Mega Drive's sound comes from two chips: a Yamaha YM2612 FM synthesiser and a PSG (a simple square-wave chip built into the VDP). A Z80 with 8 KB of its own RAM is there mainly to drive them. This page explains what each part does, who may touch what, and the rules from Sega's manuals and bulletins. Its main subject is the design choice behind every sound driver: which CPU does which part of the work. Four real drivers, each splitting it differently, show the trade-offs. The details of each chip and of the Z80 are in the sub-chapters listed [at the end](#where-to-go-next).

## The parts

| Part | What it does | Reached from the Z80 | Reached from the 68000 |
|------|--------------|----------------------|------------------------|
| YM2612 | Six FM channels. Channel 6 can instead play 8-bit samples (the DAC). Two timers, an LFO, stereo panning | `$4000-$4003` | `$A04000-$A04003`, Z80 bus held |
| PSG | Three square-wave channels and one noise channel | `$7F11` | `$C00011`, at any time |
| Z80 | 3.58 MHz CPU (NTSC) that runs the sound program | — | Its RAM at `$A00000-$A01FFF`, Z80 bus held |
| Sound RAM | 8 KB for the Z80's program and data | `$0000-$1FFF` | Byte access only |

Sources: [MD-SWM §4.4-4.5, sound software manual §I-IV, FM sound source overview]. The Z80's memory map, its window onto the 68000's memory and its clock are in [System architecture](architecture.md#the-z80-memory-map).

What the hardware does **not** give you matters as much:

- **The YM2612's timers do not raise interrupts.** Software has to poll them [MD-SWM, FM sound source overview].
- **There is no sample DMA.** To play a sample, a CPU writes each byte to the DAC at the right moment, so sample rate and quality depend entirely on how evenly that CPU can keep the timing. While the DAC is on, FM channel 6 is silent [MD-SWM, FM sound source overview].
- **The Z80 gets one interrupt**: vertical blank, every 16 ms, about 64 µs long [MD-SWM, sound software manual §I.2]. A driver that wants any other rhythm counts cycles or polls a YM2612 timer.
- **Stereo** reaches only the headphone socket on the original console model [MD-SWM, FM sound source overview].

On the 32X a third source is added, two channels of PWM driven by the SH-2s, mixed with the Mega Drive's sound. See [PWM audio](../32x/pwm.md).

## The rules

Sega's manuals and bulletins add these rules. [Z80 bus control](z80.md) has the full procedures.

**Getting at the Z80's side.** The 68000 must hold the Z80 bus to touch sound RAM or the YM2612. It writes `$0100` to `$A11100`, then waits until bit 8 of `$A11100` reads 0, then makes its accesses and writes `$0000` to release the bus [MD-SWM §4.4]. Use byte accesses for everything in the Z80 area, the YM2612 included [MD-SWM §4.5]. The PSG needs no bus request from either CPU. If both CPUs write it, though, they have to agree who writes when [MD-SWM, sound software manual §IV].

The sound manual bound into the same document describes the bus status bit the other way round: 1 for "the 68000 can access" <span class="tag disputed">disputed</span> ([discrepancy 15](../appendices/discrepancies.md)). Shipped code settles it. Aerobiz Supersonic and d32xr both wait for the bit to read 0 [AB-DISASM, Z80_RequestBus.asm; D32XR, src-md/crt0.s].

**Starting the Z80.** The Z80 is held in reset at power-on [MD-SWM §4.4]. Load its program while it is held in reset with the bus requested, then release the reset and the bus. Resetting the Z80 also resets the YM2612 [MD-SWM, sound software manual §II.1]. Aerobiz's start-up routine follows this order: mask interrupts, request the bus and assert reset, copy its 5,458-byte driver into sound RAM byte by byte, then release reset and bus [AB-DISASM, Z80_SoundInit.asm].

**Interrupts and bus requests.** Requests do not nest. If an interrupt handler requests and releases the Z80 bus while the main program holds it, the main program goes on writing sound RAM with the Z80 running. Disable interrupts around every bus request in the main program <span class="tag manual">manual</span> [MD-TB #7; MD-SDM §5.5].

**Reading the YM2612's busy flag.** Read it at `$4000` (68000: `$A04000`) and nowhere else. Reading it at `$4001` can return "not busy" while the chip is busy, and the sound stops during play <span class="tag manual">manual</span> [MD-TB #11; MD-SDM §5.5].

**On the 32X,** two more rules apply to the Z80 <span class="tag manual">manual</span>:

- Writing to `$840000-$9FFFFF` or `$A15100-$A153FF` locks up the 68000. Reading is fine [32X-TI item 15; [discrepancy 5](../appendices/discrepancies.md)].
- Whenever the Z80 writes the PSG, its bank register must point outside `$000000-$3FFFFF` and `$840000-$9FFFFF`. Otherwise the 32X can mistake the end of the PSG write for an access by the 68000, hand the 68000 wrong data and corrupt its own registers. Sega warns this varies from console to console and may not show up in testing [32X-TI item 22].

A driver that streams samples from the cartridge through the bank window and also writes the PSG must therefore point the bank elsewhere first, work RAM for example, on a 32X.

## Who does the work

A sound driver has three jobs. It **sequences** music and effects: reads note data, runs envelopes and vibrato, decides what to write when. It **writes the chips**. And if samples are used, it **feeds the DAC** at a steady rate. Either CPU can do any of them. Where each job runs decides what the sound costs the game and how good the samples sound.

| Driver | Sequencing | FM and PSG writes | DAC | Talking between the CPUs |
|--------|-----------|-------------------|-----|--------------------------|
| Sega's Sound Driver V3 | 68000, called once per vertical interrupt | Z80 | Z80, using all its time | System calls on the 68000 side |
| Virtua Racing Deluxe | 68000, once per frame | 68000, holding the Z80 bus for each FM write | Z80, a 653-byte player | Three bytes at the top of sound RAM |
| Aerobiz Supersonic | Z80 | Z80 | — | Commands written into sound RAM, then a wait |
| d32xr | 68000 decompresses a recorded register log (VGM) | Z80 replays the log | Z80 | Buffers in sound RAM, requests written into 68000 work RAM |

Sources: [SND-V3, specifications; VRD-NOTES, analysis/SOUND_DRIVER_ARCHITECTURE.md; AB-DISASM, sound modules; D32XR, src-md/z80_vgm.s80, src-md/crt0.s, src-md/vgm.c].

### Sega's V3: sequencing on the 68000, samples on the Z80

Sega's own driver for 32X games is a 68000 program called once per vertical interrupt. It plays up to 16 music tracks and 5 effect tracks over FM, PSG, the 32X's PWM and up to two sample channels. Sega gives its cost as about 1% of the 68000 when idle and about 9% while music plays, plus about 0.5% per effect channel. The Z80 is entirely given over to the sample channels. The driver takes about 12 KB of ROM with its Z80 part, and about 2.8 KB of work RAM [SND-V3, specifications]. The game talks to it through a list of system calls: start music, start an effect, fade, volume, pause and so on [SND-V3, system calls; see [Sega's Sound Driver V3](sound-driver-v3.md)].

### Virtua Racing Deluxe: almost everything on the 68000

As the disassembly project describes it, from a ROM copy that is not quite the retail original (see [Sources](../appendices/bibliography.md#vrd-notes)), VRD's driver is a 68000 sequencer that writes the YM2612 and the PSG itself. Every FM write takes the Z80 bus, waits for the busy flag, writes, and releases the bus. The Z80 runs only a 653-byte sample player. The 68000 talks to it through three bytes at the top of sound RAM: volume, sample number, and a busy flag the Z80 sets [VRD-NOTES, analysis/SOUND_DRIVER_ARCHITECTURE.md]. The game itself never calls the driver. It leaves sound requests in three mailbox bytes in work RAM (music, effects, background), and the frame code passes them on once per frame, dropping an effect that repeats the last one sent.

The design is simple and keeps all sound logic in one language. Its costs are 68000 time, and a Z80 that stops for every FM write, which disturbs sample timing.

### Aerobiz Supersonic: everything on the Z80

Aerobiz's 5,458-byte Z80 driver does all the work [AB-DISASM, README; Z80_SoundInit.asm]. The 68000 sends it commands through sound RAM [AB-DISASM, CmdSendZ80Param.asm]:

1. Mask interrupts and take the Z80 bus.
2. Write the command's parameters and number into fixed bytes of sound RAM, and set a "busy" byte to 2.
3. Release the bus and spin for 6,350 loop passes, about 63,500 68000 cycles or half a frame.
4. Take the bus again and check whether the Z80 has cleared the busy byte. If not, go back to step 3.
5. Read the result byte, release the bus, unmask interrupts.

Every sound command can therefore cost the 68000 half a frame or more, with interrupts masked the whole time. That is acceptable for a turn-based strategy game and would not be for an action game. Larger uploads work the same way. One command copies up to three 39-byte records into sound RAM (most likely FM instrument settings) and sets a bit mask of which are present. Another packs three channels' data into fixed 16-byte slots, so that the Z80 only ever reads fixed-size records [AB-DISASM, CmdSendZ80Param.asm].

### d32xr: decompress on the 68000, replay on the Z80

d32xr's music is a recorded stream of chip register writes (VGM), stored compressed [D32XR, src-md/vgm.c, src-md/z80_vgm.s80, src-md/crt0.s]:

- **The 68000 decompresses** the stream into a 32 KB buffer in work RAM. In its main loop it copies the next blocks into eight 512-byte buffers that fill the top 4 KB of sound RAM.
- **The Z80 replays** the register writes from those buffers at the right times, and also plays samples.
- **The Z80 asks for more without a bus request.** At start-up it points its bank window at the top 32 KB of 68000 work RAM and leaves it there. To make a request, it writes a byte at the top of work RAM, which the 68000's main loop simply reads. The Z80 only ever writes there, which the 32X allows (and the bank setting also satisfies the PSG rule above).
- **A critical-section flag.** The Z80 sets a byte in sound RAM while it updates shared state. After taking the bus, the 68000 backs off if it finds that byte set.

Each CPU does what it is best at: the 68000 has the memory and speed for decompression, and the Z80 has the steady timing for playback. Neither waits for the other.

### Choosing

- **Count the 68000's time.** Sequencing on the 68000 typically costs a few percent of each frame (Sega's 9%). Every FM write from the 68000 also stops the Z80.
- **Protect the DAC's timing.** If samples matter, give the Z80 as few interruptions as possible: no bus requests from the 68000 during playback, and a stream that does not need the 68000's bus.
- **Mind the bank window.** Each Z80 read through the window borrows the 68000's bus (see [System architecture](architecture.md#the-bank-window)), and a long VDP DMA delays it.
- **Never wait on the Z80 with interrupts masked** in an action game. Post a request and check for the answer next frame, or do not wait at all. The [communication chapter](../32x/communication.md#repeating-a-command-sequence-numbers) shows a sequence-number scheme for requests that need no reply.

## Talking to a Z80 driver

Whatever the split, the 68000 and the Z80 share sound RAM as a mailbox. The habits that work:

- **Keep bus requests short.** Take the bus, write a few bytes, release it. The Z80 is stopped for the whole time, and so is its sample playback.
- **Write the data first and the "go" byte last**, and let the Z80 clear it when it has taken the request. This is the same rule as the [32X communication ports](../32x/communication.md#the-one-hazard-a-word-that-changes-while-you-read-it).
- **Give each byte one writer**, or pass ownership with its value.
- **Pre-format on the 68000.** Aerobiz's fixed-size slots and d32xr's ready-to-play buffers both move work from the slower CPU to the faster one.

## Where to go next

| Chapter | Covers |
|---------|--------|
| [Z80 bus control](z80.md) | Bus request and reset in detail, loading a program, the bank window, Z80 interrupts |
| [YM2612 FM synthesis](ym2612.md) | Registers, operators and algorithms, channel 3's special mode, the DAC, timers, write timing |
| [PSG (SN76489)](psg.md) | Register writes, the volume table, noise |
| [Sega's Sound Driver V3](sound-driver-v3.md) | The official driver's system calls and costs |
| [PWM audio](../32x/pwm.md) | The 32X's sample channels |

## Open questions

- How long must the Z80 be held in reset, and does the YM2612 need longer? The sound manual gives a figure that does not read cleanly in our copy.
- What does a 68000 write to the YM2612 without the Z80 bus actually do on each console model?

## Sources

- [MD-SWM](../appendices/bibliography.md#md-swm): §4.4 Z80 control, §4.5 Z80 area; sound software manual §I-IV; FM sound source overview
- [MD-SDM](../appendices/bibliography.md#md-sdm): §5.5 Z80 bus requests and sound access
- [MD-TB](../appendices/bibliography.md#md-tb): #7 and #11
- [32X-TI](../appendices/bibliography.md#32x-ti): items 15 and 22
- [SND-V3](../appendices/bibliography.md#snd-v3): specifications, system calls
- [AB-DISASM](../appendices/bibliography.md#ab-disasm): Z80_SoundInit, Z80_RequestBus, CmdSendZ80Param, README
- [VRD-NOTES](../appendices/bibliography.md#vrd-notes): analysis/SOUND_DRIVER_ARCHITECTURE.md
- [D32XR](../appendices/bibliography.md#d32xr): src-md/z80_vgm.s80, src-md/vgm.c, src-md/crt0.s
