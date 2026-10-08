# Using more cartridge space

A 32X cartridge can hold 4 MB without extra hardware, and more with Sega's bank chip. The SH-2s see all 4 MB at once, but the 68000 sees only 1.5 MB of it at a time (4 MB only while RV = 1), so the two see it differently, and a game written for a plain Mega Drive assumed the cartridge started at address 0. This chapter covers how to fit a game and its new data into a bigger cartridge: how each CPU sees the space, how big a cartridge really is, moving a whole game into a bank, adding data, going past 4 MB, and what to check before trusting a result on hardware.

## Who sees what

| Who | Where the cartridge appears | Notes |
|-----|-----------------------------|-------|
| 68000 | `$880000-$8FFFFF`: the first 512 KB, always | The fixed window. 32X games put their 68000 code here |
| 68000 | `$900000-$9FFFFF`: one megabyte, 0 to 3, chosen at `$A15104` | The banked window |
| 68000 and Mega Drive VDP DMA | `$000000-$3FFFFF`, the plain Mega Drive layout | Only while RV = 1, which shuts the SH-2s out of the cartridge |
| SH-2 | `0x02000000-0x023FFFFF`, all 4 MB, through the cache | `0x22000000` for the same bytes without the cache |

The details are in [Architecture](../32x/architecture.md#after-the-32x-is-switched-on-aden--1), [The RV bit](../32x/architecture.md#the-rv-bit) and [`$A15104`](../32x/registers.md#a15104-bank-set). Sega's Mars Check Program, a 32 Mbit diagnostic cartridge, tests exactly this layout. Each megabyte of it ends with a marker, `BK00` to `BK11`. The 68000 selects each bank in turn and reads the marker at `$9FFFFC`, and each SH-2 reads all four through `0x220FFFFC`, `0x221FFFFC`, `0x222FFFFC` and `0x223FFFFC` [MARS-CHECK, 68000 code at `$19FC`, SH-2 code at `0x06000E90`].

So the SH-2s see everything at once, and the 68000 sees 1.5 MB at a time. What the retail games did with that:

| Game | Size | Bank selected for the 68000 |
|------|------|------------------------------|
| After Burner Complete | 2 MB | 1, once, at start-up [AB32X, 68000 code at `$000900`] |
| Knuckles' Chaotix | 3 MB | 2, at start-up and again later [CHAOTIX, 68000 code at `$0009EE`, `$00188C`] |
| Mortal Kombat II | 4 MB | Never written by an absolute address [MK2, ROM searched] |
| Star Wars Arcade | 2.5 MB | Never written by an absolute address [SWA, ROM searched] |
| Motocross Championship | 2 MB | Never written by an absolute address [MCX, ROM searched] |

Mortal Kombat II's tables of 68000 pointers all lead into the first megabyte through `$900000`, while its SH-2s read the whole cartridge ([Architecture](../32x/architecture.md#after-the-32x-is-switched-on-aden--1)). A search like this can miss a write made through a base register, which is why three rows say "by an absolute address".

## How big is the cartridge?

The header says, in the ROM end address at `$1A4`. Every retail dump this book uses is exactly as long as its header says, and the sizes are not all powers of two: Star Wars Arcade is 2.5 MB, Chaotix and Virtua Racing Deluxe 3 MB [SWA; CHAOTIX; VRD-NOTES, header]. A cartridge only has to hold what the game needs.

Two warnings:

- **Development discs are careless about it.** Several of Sega's sample programs declare 128 KB in a much larger file [EGYPT; GNU-SIERRA]. Trust the header only on retail dumps.
- **What a real cartridge returns past its end is not in any dump.** It depends on the board: a mirror of the chip, open bus, or whatever is wired there. The VRD project treats its game as a 4 MB cartridge with an empty last megabyte that dumps leave out [VRD-NOTES, ROM_SIZE_CLARIFICATION]. The game's own header gives `$2FFFFF`, 3 MB, the same as the dump, so that rests on the project's account alone.

When you extend a game you are making a new cartridge: set the end address to the new size, pad the image, and recompute the checksum or set it to 0 ([The checksum](../32x/boot.md#the-checksum)). Before going over 16 Mbit, see [Beyond 16 Mbit](#beyond-16-mbit-and-beyond-4-mb).

## Moving a Mega Drive game into a bank

A game written for a plain Mega Drive addresses its code and data from `$000000`. On a 32X cartridge the 68000 no longer sees it there, and the fixed window is only 512 KB. Aerobiz Ultimate solves this for a 1 MB game with one choice: the whole original image goes at cartridge `$100000`, the 68000 selects bank 1, and the game appears unbroken at `$900000-$9FFFFF`. Moving it becomes adding one constant, `$900000`. The new 68000 code and the SH-2 program live in the fixed window, so they stay reachable whatever bank is selected <span class="tag emulator">emulator</span> [AU-NOTES, PORT_ARCHITECTURE §2].

Adding the constant is the easy part. Finding every place that holds an address is the work:

- **Rewrite each address as `ROM_BASE + offset`.** One source then builds both games: with `ROM_BASE` = 0 it must still produce the original ROM byte for byte, which proves no instruction changed size or encoding [AU-NOTES, PORT_ARCHITECTURE §2].
- **Sort the candidates by how sure you can be.** An operand that is an address by construction (an address register load, `lea`, `pea`, an absolute operand, a branch target) can be rewritten mechanically. An immediate that merely falls in the ROM's range, such as a mask, a multiplier or a price, needs evidence. Aerobiz Ultimate's first count was 1,990 certain and 896 doubtful sites [AU-NOTES, PORT_ARCHITECTURE §2].
- **Let the encoding decide what it can.** The moved addresses are `$9xxxxx`, which no byte or word immediate can hold. That excluded 336 of the 899 doubtful sites without anyone judging them. The rest collapsed to 93 distinct values, and tracing each into the code settled them: none was an address. Two doubtful sites had already turned out to be real addresses, the hard way: every city in the game lost its airport slots until they were fixed [AU-NOTES, ROADMAP U-011].
- **Expect the scanner to miss things.** The true count was 3,872, not 2,886. The scanner had missed `jsr` instructions written out as data words (971 of them), lines with several `dc.l` values, PC-relative operands, `dbne`, mnemonics written in capitals, and instructions inside blocks never turned back into code [AU-NOTES, ROADMAP U-010]. Each of those would have jumped into unmapped memory.
- **The byte-identical check cannot see a wrong rewrite.** With `ROM_BASE` = 0, a data word mistakenly marked as an address assembles the same. Aerobiz Ultimate found 41 such rewrites among 1,858, in palettes, index tables and tile pixels. The way to tell is how the code reads a table: through a longword read into an address register, it holds pointers; through word reads, it holds data <span class="tag emulator">emulator</span> [AU-NOTES, KNOWN_ISSUES; ROADMAP U-014].
- **Low addresses need their own search.** A game that reads its own header at `$0001F0` gets nothing there while RV = 0. Aerobiz Ultimate found this only when Ares, which maps the cartridge as the manual says, showed the game's region lockout screen [AU-NOTES, HISTORY 2026-09-15; [Architecture](../32x/architecture.md#after-the-32x-is-switched-on-aden--1)].

## Adding data

Where new data goes depends on who reads it:

- **Data the 68000 reads: the fixed window first.** It is always mapped, so no bank switch can hide it. Aerobiz Ultimate put its new event tables at cartridge `$030000`, which the 68000 reads at `$8B0000`. The game's own modules reach them through alternative addresses of exactly the same size, chosen at assembly time. The original tables are still in the game image, so a reader that was missed keeps the original behaviour instead of crashing <span class="tag emulator">emulator</span> [AU-NOTES, HISTORY].
- **Data in another megabyte: switch banks from code that stays put.** Code running from `$900000` disappears when the bank changes, so switch from the fixed window or work RAM, and don't leave an interrupt handler pointing into the banked window. Chaotix's bank writes are both in its fixed-window code [CHAOTIX, 68000 code at `$0009EE`, `$00188C`].
- **Data only the SH-2s read: anywhere.** They see all 4 MB without switching. Read it through the cache if it is reused, and through `0x22000000` if it streams past once ([Living with bus contention](../patterns/bus.md#what-each-program-did)). The same bytes can serve both CPUs if the SH-2 converts the 68000's addresses: Mortal Kombat II adds `0x01700000` to its 68000 pointers ([Architecture](../32x/architecture.md#after-the-32x-is-switched-on-aden--1)).
- **More SH-2 code.** The VRD project placed new Slave code in its game's unused space, read by the SH-2 from the cartridge <span class="tag emulator">emulator</span> [VRD-NOTES, ROM_SIZE_CLARIFICATION]. Code that runs from the cartridge pays the costs in [Code that runs from the cartridge](toolchain.md#code-that-runs-from-the-cartridge).

## Beyond 16 Mbit, and beyond 4 MB

**Over 16 Mbit, run Sega's initialisation.** Sega required every 32X game larger than 16 Mbit to read `$A130F1` once and then call the vector ROM's routine at `$0000C0` with 0 in `d0`, interrupts masked <span class="tag manual">manual</span> [32X-TI item 8]. Knuckles' Chaotix does it; Mortal Kombat II and Star Wars Arcade do not, and still work ([Cartridges over 16 Mbit](../32x/bugs.md#cartridges-over-16-mbit)). Do it.

**Save RAM over 16 Mbit shares its addresses with ROM.** The register the initialisation writes, `$A130F1`, is the one that chooses between ROM and save RAM at `$200000`. Chaotix, the only one of the three with save RAM, keeps 512 bytes on the odd addresses of `$200001-$2003FF`, inside its own ROM. To reach them it sets RV from a routine in work RAM, switches the save RAM in, copies the data, and switches ROM back ([Save RAM on the 32X](../megadrive/cartridge.md#save-ram-on-the-32x)) [CHAOTIX, header; 68000 code at `$03E322`-`$03E4B8`]. A game that adds saves to a cartridge over 16 Mbit has to do the same, and setting RV obliges it to check RV in its VRES handler ([Reset while RV = 1](../32x/bugs.md#reset-while-rv--1)).

**Over 4 MB, use Sega's bank chip.** The 315-5709 maps any 512 KB page of up to 32 MB into each 512 KB area of the cartridge space except the first. Its registers at `$A130F3`-`$A130FF` can only be written while RV = 1 ([Bank switching beyond 4 MB](../megadrive/cartridge.md#bank-switching-beyond-4-mb)). Emulators enable it when the header's system name is `SEGA SSF` instead of `SEGA 32X` <span class="tag emulator">emulator</span> [S32X-SKILL, architecture].

d32xr is the worked example, in a build that declares a 5 MB ROM [D32XR, `crt0.s`]:

- **Each SH-2 owns one area.** The Master switches pages in area 6 (`0x02300000`) and the Slave in area 7 (`0x02380000`), so neither can pull data out from under the other [D32XR, `marsnew.c`].
- **Pointers stay in one address space.** The game treats the ROM as if the SH-2 could see all of it from `0x02000000` up. A function translates any pointer at or above `0x02300000`: it works out the 512 KB page, has that page put into the CPU's own area, and returns the address inside the area. The page switch clears the cache, because the same addresses now hold different bytes [D32XR, `marsnew.c`, `I_RemapPtr`].
- **The 68000 does the switching.** The SH-2 posts a command with the area and page numbers through a communication port and waits. The 68000 masks its interrupts, parks both SH-2s off the cartridge, sets RV, writes the page number to the area's register, clears RV and releases them [D32XR, `marshw.c`, `src-md/crt0.s`].
- **The ROM size comes from the header.** The SH-2 code reads the start and end addresses at `$1A0` and `$1A4` and only translates pointers when the ROM is larger than 4 MB [D32XR, `marshw.c`].

Each switch stops both SH-2s for a moment. When a level loads, d32xr notes which page holds the level's wall segments, which its renderer walks constantly, and selects that page again at the start of every frame [D32XR, `p_setup.c`, `r_main.c`].

## Real cartridges, development boards and flash carts

The cartridge the game ships on is part of the program:

- **Sega's development boards** had two memory modes: 32M mode with working bank registers, and 16M mode with ROM below `$200000` and save RAM above, where the bank registers must not be written. The SRAM board starts write-protected ([Sega's development boards](../megadrive/cartridge.md#segas-development-boards)).
- **Emulators decide the mapping from the ROM**, mostly from the header, and so do flash carts. None of this book's sources documents how a particular flash cart maps a 32X image over 16 Mbit, with save RAM, or with `SEGA SSF`. Test the exact combination on the cart you will use, and list it with the questions in [Testing on real hardware](real-hardware.md).
- **Ares and PicoDrive disagree at the edges.** Ares hides the cartridge's low addresses while RV = 0, as the manual says, and upstream PicoDrive does not ([Architecture](../32x/architecture.md#after-the-32x-is-switched-on-aden--1)). Run a moved game in Ares before believing it.

## What to take away

- The SH-2s see all 4 MB; the 68000 sees the first 512 KB plus one megabyte it chooses at `$A15104`.
- Put a whole Mega Drive game in one bank, and the glue code and new 68000 data in the fixed window.
- Rewrite addresses so the original build still comes out byte for byte, and remember that this check cannot catch data mistaken for an address.
- Size the header for the cartridge you are making, and run Sega's initialisation if it is over 16 Mbit. Save RAM on such a cartridge shares `$200000` with ROM and is switched in with RV set.
- Past 4 MB, give each SH-2 its own bank area and let the 68000 do the switching.

## Open questions

- What does a retail 32X cartridge return past the end its header gives?
- Do flash carts map 32X images over 16 Mbit, with save RAM or `SEGA SSF`, as Sega's cartridges do?
- What does a cartridge that switches save RAM or banks into `$200000-$3FFFFF` show there at power-on, before Sega's initialisation ([Hardware bugs](../32x/bugs.md#open-questions))? Cartridges with ROM only evidently need nothing: Mortal Kombat II and Star Wars Arcade skip it and work.

## Sources

- [32X-TI](../appendices/bibliography.md#32x-ti): item 8
- [MARS-CHECK](../appendices/bibliography.md#mars-check): bank test (68000 `$19FC`); ROM read test (SH-2 `0x06000E90`)
- [AB32X](../appendices/bibliography.md#ab32x), [CHAOTIX](../appendices/bibliography.md#chaotix), [MK2](../appendices/bibliography.md#mk2), [SWA](../appendices/bibliography.md#swa), [MCX](../appendices/bibliography.md#mcx): headers and bank register writes; Chaotix's save RAM code at `$03E322`-`$03E4B8`
- [EGYPT](../appendices/bibliography.md#egypt), [GNU-SIERRA](../appendices/bibliography.md#gnu-sierra): headers
- [AU-NOTES](../appendices/bibliography.md#au-notes): PORT_ARCHITECTURE §2; ROADMAP U-010, U-011, U-014; KNOWN_ISSUES; HISTORY
- [VRD-NOTES](../appendices/bibliography.md#vrd-notes): ROM_SIZE_CLARIFICATION; header
- [D32XR](../appendices/bibliography.md#d32xr): `crt0.s`, `marsnew.c`, `marshw.c`, `src-md/crt0.s`, `p_setup.c`, `r_main.c`
- [S32X-SKILL](../appendices/bibliography.md#s32x-skill): architecture
