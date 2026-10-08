# The VDP

The VDP (Video Display Processor, Sega part 315-5313) makes the Mega Drive's picture. It has 64 KB of video memory of its own (VRAM) and two small memories on the chip, one for colours and one for vertical scroll values. Each frame it builds the picture from small tiles laid out in tables in VRAM. Neither CPU can address any of that memory: everything goes through two ports at `$C00000` [MD-SWM §2.2; see [System architecture](architecture.md)].

This page explains how those ports work, which is the part every other VDP chapter relies on. It also shows what lives where in the VDP's memory, and what the chip can and cannot do. The details are in the sub-chapters listed [at the end](#where-to-go-next).

On a 32X this VDP is still there, unchanged. The 32X adds a second, separate video chip whose picture is mixed with this one; see [The 32X VDP](../32x/vdp.md) and [Mixing 32X and Mega Drive graphics](../32x/compositing.md). "VDP" on its own in this book means the Mega Drive one.

## What it does, and what it does not

The VDP draws four layers, back to front [MD-SWM §2; MD-TO, system overview]:

| Layer | What it is |
|-------|------------|
| Backdrop | One colour filling every pixel nothing else covers, chosen by register 7 |
| Plane B | A scrolling grid of 8 × 8 tiles |
| Plane A, or the window | A second scrolling grid. The window is a non-scrolling area that replaces plane A in part of the screen |
| Sprites | Up to 80 movable objects, each 1 to 4 tiles wide and 1 to 4 tiles high |

Planes and sprites each carry a priority bit, so a high-priority tile in plane B can still cover a low-priority sprite [MD-SWM §2.11]. Along with drawing, the VDP:

- scrolls each plane horizontally as a whole, per row of tiles or per line, and vertically as a whole or per column two tiles wide [MD-TO, system overview];
- shows 64 colours at once out of 512, as four palettes of 16 [MD-SWM §2.12];
- can darken or brighten pixels (shadow and highlight) and can double the vertical resolution (interlace) [MD-SWM §2.11, §2.13];
- copies data into its memories by DMA, either from 68000 memory or within VRAM, and can fill VRAM with a value [MD-SWM §2.7];
- raises all three of the 68000's interrupts: vertical blank, a programmable line interrupt, and an external one from the controller port [MD-SWM §2.3];
- reports where the beam is through its H/V counter [MD-SWM §2.6, HV counter];
- contains the PSG sound chip [MD-SWM §2].

Just as useful is what it **cannot** do:

- **There is no bitmap mode.** Every pixel on the screen comes from a tile, so to draw freely you must redraw tiles, as a software renderer on a Mega Drive does. The 32X exists largely to fix this.
- **No scaling and no rotation.** Line and column scrolling are the only per-line effects the hardware gives you. Everything else is done by changing tiles or registers while the picture is being drawn.
- **Colour 0 of every palette is transparent.** A tile or sprite can use 15 colours of its palette. Four palettes give 60 colours, plus the backdrop: 61 on screen without mid-frame palette changes [MD-TO, system overview].
- **Sprites per line are limited.** At most 20 sprites and 320 sprite pixels on one line in 40-column mode, or 16 sprites and 256 pixels in 32-column mode. Anything beyond that is not drawn [MD-SWM §2.10, sprite display capacity].
- **The registers cannot be read back.** Only the status register can be read, so a program that needs to know a register's value keeps its own copy (see [Registers and access](vdp-registers.md)).
- **It does not reset with the console's reset button.** Reset restarts the 68000, but a DMA the VDP was running carries on. Code that runs after Sega's initial program should check the status register's DMA busy bit before touching the VDP <span class="tag manual">manual</span> [MD-SDM, precautions: repeated reset].

The screen is 320 or 256 pixels wide (40 or 32 columns of tiles, "H40" and "H32") and 224 lines high. PAL consoles can also show 240 [MD-SWM §2.1].

## The ports

The VDP takes up a few addresses at `$C00000` [MD-SWM §2.4; GENVDP §3]:

| Address | Read | Write |
|---------|------|-------|
| `$C00000` (mirror `$C00002`) | Data from VRAM, CRAM or VSRAM | Data to VRAM, CRAM or VSRAM |
| `$C00004` (mirror `$C00006`) | Status register | Register settings and memory commands |
| `$C00008` (mirrors to `$C0000E`) | H/V counter | — |
| `$C00011` | — | PSG (byte writes) |

Use word or longword accesses on the data and control ports. Sega's manual described byte access to the VDP's memories as possible, and a later bulletin corrected that to word and longword only <span class="tag manual">manual</span> [MD-TB #13]. A byte write does reach the VDP, but as a word with the same byte in both halves [GENVDP §7]. A longword access counts as two word accesses, high word first, so one `move.l` can carry two register settings or a whole memory command [MD-SWM §2.4].

### Two kinds of control word

Everything you write to the control port is one of two things, told apart by the top two bits [MD-SWM §2.4; GENVDP §7]:

**A register setting**, one word: `%100r rrrr vvvv vvvv`, with the register number in bits 12-8 and the value in bits 7-0. In hex it is `$8000 + (register << 8) + value`, so `$8174` sets register 1 to `$74` and `$8F02` sets register 15 to 2. There are 24 registers, 0 to 23; the [register chapter](vdp-registers.md) explains each bit.

**A memory command**, two words, which says which memory the data port should use, in which direction and from what address. The 6-bit code CD5-CD0 picks the operation, and the 16-bit address is split across both words:

| Bits | 31-30 | 29-16 | 15-8 | 7-4 | 3-2 | 1-0 |
|------|-------|-------|------|-----|-----|-----|
| Holds | CD1-CD0 | A13-A0 | 0 | CD5-CD2 | 0 | A15-A14 |

| Operation | Code CD5-CD0 | Command for address 0 |
|-----------|--------------|-----------------------|
| VRAM write | `%000001` | `$40000000` |
| CRAM write | `%000011` | `$C0000000` |
| VSRAM write | `%000101` | `$40000010` |
| VRAM read | `%000000` | `$00000000` |
| CRAM read | `%001000` | `$00000020` |
| VSRAM read | `%000100` | `$00000010` |

Sources: [MD-SWM §2.6; GENVDP §7]. CD5 set to 1 (`$80` in the low word) makes the command start a DMA instead of waiting for the data port; CD4 is used only by DMA's VRAM copy [GENVDP §7]. Both are explained in [DMA](vdp-dma.md).

Once you know the layout, a command can be built from any address:

```c
/* cd = operation code (0-63), addr = 0-$FFFF */
#define VDP_CMD(cd, addr) \
    ((((cd) & 3UL) << 30) | (((addr) & 0x3FFFUL) << 16) | \
     (((cd) >> 2) << 4)   | ((addr) >> 14))
```

The same in 68000 code, without a table:

```asm
; d0.l = VRAM address (high word 0) -> d0.l = VRAM write command
        lsl.l   #2,d0            ; A15-A14 move up into bits 17-16
        lsr.w   #2,d0            ; A13-A0 back down to bits 13-0
        swap    d0               ; A13-A0 to the high word, A15-A14 to the low
        ori.l   #$40000000,d0    ; CD1-CD0 = 01: VRAM write
```

Aerobiz Supersonic builds every command with shifts and a `swap` like this, then adds `$40000000`, `$C0000000` or `$40000010` for the memory, plus `$80` for DMA [AB-DISASM, CmdSetupDMA.asm, VRAMWriteExtended.asm].

Reading constant commands is just as useful when you study other people's code. Aerobiz's region-lock screen writes `$C0020000` and then the word `$0EEE`. CD1-CD0 = `11` with all other code bits 0 is a CRAM write, and the address is 2, so this sets colour 1 to white. The disassembly's comment reads it as a VRAM write to `$0200`, which the code bits rule out [AB-DISASM, EarlyInit.asm].

### Using the data port

After a write command, each word written to `$C00000` goes to the current address, and the VDP then adds the value of register 15 to the address. After a read command, each word read comes from the current address in the same way [MD-SWM §2.6]:

- **Set register 15 to 2** for ordinary word-by-word copying. Other values are for patterns such as writing one column of a name table (an increment of 2 × the table width).
- **Data must match the command.** Writing after a read command, or reading after a write command, is ignored [GENVDP §7]. Sega's manual is harsher: a write after a read command only moves the address on, and a read after a write command stops the 68000 for good <span class="tag manual">manual</span> [MD-SDM §4.1].
- **No read-modify-write instructions on the data port.** `clr`, `not`, `neg`, `tas`, the bit instructions (`bset` and so on), memory shifts, and `addi`/`ori`/`subq`-style instructions on memory all read their target before writing it. Aimed at the data port, they hang the 68000 or write nothing. `tas` never writes on a Mega Drive anyway [MD-SDM §4.1]. To clear VDP memory, write a register holding 0.
- **VRAM is reached in bytes inside the chip.** A word written to an odd VRAM address arrives with its two bytes swapped [MD-SWM §2.6; GENVDP §8]. Keep VRAM addresses even.
- **A VRAM read needs a pause before the next command.** After reading, wait more than 116 68000 cycles during the display (more than 12 during vertical blank) before writing a new address, or the data may be wrong. A run of reads from one command is fine <span class="tag manual">manual</span> [MD-TB #15].

Reading the control port returns the status register: FIFO empty and full, vertical interrupt pending, sprite overflow and collision, odd or even frame in interlace, vertical and horizontal blank, DMA busy, and PAL or NTSC [MD-SWM §2.4]. The bits are explained in [Registers and access](vdp-registers.md).

### The VDP remembers half a command

The VDP keeps three pieces of state between writes: the address, the code, and a flag that says "the first half of a memory command has arrived, waiting for the second" [GENVDP §7]:

- The flag is set by the first word of a memory command. It is cleared by the second word, and also by any data port access or any read of the control port.
- While the flag is set, the next control word is taken as the second half of a command, even if it looks like a register setting.
- A register setting clears the code. Code that writes a register and then expects to go on writing data finds its writes going nowhere. Golden Axe II and Sonic 3D depend on this behaviour, and an emulator that leaves it out draws them wrongly [GENVDP §7].

So **read the control port once before programming the VDP from an unknown state.** Sega's initial program does exactly this: its first VDP access is a read of `$C00004`, and only then does it write the 24 registers [AB-DISASM, initial program at `$22E`].

The same state also explains the most common VDP bug in games. If an interrupt handler sets a new address while the main program is in the middle of a copy, the main program's remaining words land at the handler's address. Sega's fix is one of two rules: mask interrupts from the address write until the copy ends, or have the main program raise a "busy" flag that interrupt handlers check before touching the VDP <span class="tag manual">manual</span> [MD-TB #20]. Many games avoid the problem completely by making the vertical blank handler the only code that touches the VDP. The rest of the game leaves requests for it in RAM; see [Timing, interrupts and counters](vdp-timing.md).

### When the CPU can get in

The VDP spends most of each display line fetching tiles and sprites. The CPU gets only a few access slots per line during the display, but nearly all of them during vertical blank [MD-SWM §2.6, access timing]:

| | 32 columns | 40 columns |
|---|---|---|
| Slots per line during display | 16 | 18 |
| Slots per line during vertical blank | 167 | 205 |
| Longest wait for a full FIFO | about 5.96 µs | about 4.77 µs |

A VRAM slot moves one byte and a CRAM or VSRAM slot moves one word. A four-word FIFO absorbs short bursts, but a tight copy loop during the display soon fills it, and the 68000 then waits. During vertical blank it never waits. That is why big updates belong in vertical blank, and why DMA runs at about 205 bytes per line there [MD-TO, system overview]. The exact timing is in [DMA](vdp-dma.md) and [Timing, interrupts and counters](vdp-timing.md).

## The three memories

| Memory | Size | Word format | Holds |
|--------|------|-------------|-------|
| VRAM | 64 KB, addresses `$0000-$FFFF` | Any | Tiles, the plane and window name tables, the sprite table, the horizontal scroll table |
| CRAM | 64 words, addresses `$00-$7F` | `----bbb-ggg-rrr-` | Four palettes of 16 colours, 3 bits per component |
| VSRAM | 40 words, addresses `$00-$4F` | Scroll value in the low 10 bits (11 in interlace mode 2) | Vertical scroll for plane A and plane B, as a whole or per 2-tile column |

Sources: [MD-SWM §2.2, §2.6, §2.8 V scroll; GENVDP §8-10]. CRAM and VSRAM addresses are byte addresses even though the memories are word-wide, so colour *n* is at CRAM address 2*n*. Address bit 0 is ignored, and writes past the end of VSRAM have no effect [GENVDP §9-10].

Clearing everything at start-up is three loops over those sizes. Aerobiz does it with the commands `$40000000` (32,768 words of VRAM), `$C0000000` (64 words of CRAM) and `$40000010` (40 words of VSRAM) [AB-DISASM, VDP_Init1.asm].

### What lives where in VRAM

VRAM has no fixed layout. Tiles always count from address 0, 32 bytes each, and the five tables go wherever the registers put them. The tables may even overlap if two layers are meant to share one [MD-SWM §5]:

| Table | Register | Size | Alignment |
|-------|----------|------|-----------|
| Tiles (planes and sprites) | none: always from `$0000` | 32 bytes each | — |
| Plane A name table | 2 | Up to 8 KB, 2 bytes per tile | `$2000` |
| Plane B name table | 4 | Up to 8 KB | `$2000` |
| Window name table | 3 | 2 KB (H32) or 4 KB (H40) | `$800` (H32), `$1000` (H40) |
| Sprite table | 5 | 512 bytes (H32) or 640 of 1 KB (H40) | `$200` (H32), `$400` (H40) |
| Horizontal scroll table | 13 | Up to 1 KB, 896 bytes for 224 lines | `$400` |

Sources: [MD-SWM §2.5, §5; GENVDP §17]. Sega's initial program, which every cartridge starts with, sets a layout that many games keep. Its register table, in Aerobiz Supersonic at ROM `$2A8`, gives [AB-DISASM, initial program; MD-SDM §2]:

```
$0000-$BFFF  tiles: 1536 tiles of 32 bytes
$C000-$CFFF  plane A, 64 x 32 tiles        register 2  = $30
$D800-$DA7F  sprite table, 80 sprites      register 5  = $6C
$DC00-$DF7F  horizontal scroll table       register 13 = $37
$E000-$EFFF  plane B, 64 x 32 tiles        register 4  = $07
$F000-$FFFF  window                        register 3  = $3C
```

It also selects H40 with register 12 = `$81` and a 64 × 32 plane size with register 16 = `$01`. It then writes `$40000080` to the control port and a 0 to the data port. That is a VRAM fill (a DMA with CD5 set), which clears VRAM while the program goes on to set up the Z80 [AB-DISASM, initial program at `$242`]. The 11-bit tile number in a name table entry could address 2048 tiles, but the tables take the top 16 KB, so the 1536 tiles below `$C000` are the real limit in this layout. Moving or shrinking tables is how a game wins back tile space; see [Planes and scrolling](vdp-planes.md).

## Where to go next

| Chapter | Covers |
|---------|--------|
| [Registers and access](vdp-registers.md) | Every register bit, the status register, keeping copies of the registers in RAM |
| [Planes and scrolling](vdp-planes.md) | Name table entries, plane sizes, scroll modes, the window |
| [Sprites](vdp-sprites.md) | The sprite table, the link list, per-line limits |
| [Color, shadow/highlight and interlace](vdp-color.md) | CRAM format and real output levels, priority, shadow/highlight, interlace |
| [DMA](vdp-dma.md) | The three DMA modes, transfer rates, the 128 KB boundary, DMA on the 32X |
| [Timing, interrupts and counters](vdp-timing.md) | Lines per frame, the H/V counter, interrupt timing, when the CPU may touch VRAM |

## What to take away

- The VDP is driven entirely through two ports. A control word is either a register setting (`$8rvv`) or a two-word memory command that sets the code and the address. After that, the data port streams words with auto-increment.
- The VDP keeps state between writes. Read the control port before starting from an unknown state, and never let an interrupt handler change the address in the middle of a copy.
- Keep VRAM addresses even, and keep register 15 at 2 unless you mean otherwise.
- Do big updates in vertical blank. During the display the CPU gets only 16 or 18 slots per line.
- VRAM is yours to lay out. Sega's default puts the tables in the top 16 KB and leaves 1536 tiles below them.

## Open questions

- Byte writes to the data port are documented by GENVDP as a word with the byte in both halves. Is that the same on the later VDP revisions in the Model 2 and 3 consoles?

## Sources

- [MD-SWM](../appendices/bibliography.md#md-swm): §2.1-2.6 (display, structure, interrupts, ports, registers, VDP RAM access and timing), §5 VRAM mapping, §2.7-2.13
- [MD-TO](../appendices/bibliography.md#md-to): system overview, video and DMA figures
- [MD-TB](../appendices/bibliography.md#md-tb): #13 (word access only), #15 (VRAM read wait), #20 (VDP access from interrupts)
- [MD-SDM](../appendices/bibliography.md#md-sdm): §2 initial program, precautions for repeated resets
- [GENVDP](../appendices/bibliography.md#genvdp): §3 port map, §7 ports and command words, §8-10 memories, §17 registers
- [AB-DISASM](../appendices/bibliography.md#ab-disasm): Sega's initial program, VDP_Init1, CmdSetupDMA, EarlyInit
