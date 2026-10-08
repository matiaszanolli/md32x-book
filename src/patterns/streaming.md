# Moving data: DMA, FIFO and ROM

A 32X program moves data all the time: tiles and maps into the Mega Drive VDP's memory, scene data from the 68000 to the SH-2s, models and textures from the cartridge, finished pictures into the frame buffer, samples to PWM. Each kind of move has its own path, its own speed and its own way of holding up other work. The paths themselves have chapters of their own, linked below. This page compares them, shows what the shipped programs moved and how, and collects the software patterns that keep data flowing without stalling a frame.

## The paths

The most each path can carry in one NTSC frame, if the CPU doing the work does nothing else:

| Path | From → to | At most per frame | Who does the work |
|------|-----------|-------------------|-------------------|
| Mega Drive VDP DMA, in vertical blank | Work RAM or cartridge → VRAM | About 7,400 bytes (40 columns) | The VDP; the 68000 is stopped while it runs |
| The FIFO | 68000 → SDRAM or frame buffer | About 12,000-21,000 bytes | The 68000 writes every word; SH-2 DMA receives |
| The communication ports | Either way | 16 bytes at a time, plus a handshake per batch | Both CPUs, at every step |
| An SH-2 reading the cartridge, cached | Cartridge → SH-2 | About 45,000-94,000 bytes | One SH-2, sharing the bus |
| An SH-2 writing the frame buffer | SH-2 → frame buffer | About 150,000-250,000 bytes | One SH-2 |
| SH-2 DMA | Between SDRAM, the frame buffer and the cartridge | Bus speed, in 16-byte units from SDRAM | The DMA controller, cycle by cycle with the CPUs |

These figures are the frame's clocks divided by the manual's cost per unit, not measurements <span class="tag manual">manual</span>. The sources: [How much fits in a frame](../megadrive/vdp-dma.md#how-much-fits-in-a-frame); [What it costs](../32x/fifo.md#what-it-costs); [Bulk data through the ports](../32x/communication.md#bulk-data-through-the-ports); [What a 16-bit bus costs](../sh2/bsc.md#what-a-16-bit-bus-costs), which gives 64-136 clocks per 16-byte line from the cartridge; [Moving data without paying twice](bus.md#moving-data-without-paying-twice), which gives 3-5 clocks per frame buffer word; [Sharing the bus](../sh2/dmac.md#sharing-the-bus).

The table explains the shape of every program below. The SH-2s can reach the cartridge themselves, faster than anything the 68000 can hand them, so the 68000 should send *decisions*, not data. The Mega Drive VDP can take only a few kilobytes per frame, so Mega Drive graphics have to be loaded ahead of time or in slices.

## What the shipped programs moved

| Program | 68000 → SH-2s, per frame | What the SH-2s read for themselves |
|---------|--------------------------|------------------------------------|
| Mortal Kombat II | A 668-byte block of game state through the ports, ten bytes per handshake ([Bulk data through the ports](../32x/communication.md#bulk-data-through-the-ports)) | Fighter graphics, drawn straight from their run-length form in the cartridge; packed data, unpacked by the Master ([Compression](../techniques/compression.md#propack-on-the-sh-2-mortal-kombat-ii)) |
| After Burner Complete | One call per object: its parameters in the ports and in the FIFO's unused address and length registers ([One call per object](../32x/communication.md#one-call-per-object)) | Compressed sprites, decoded on first use into a cache in SDRAM ([A cache of decoded sprites](../techniques/memory.md#a-cache-of-decoded-sprites)) |
| Star Wars Arcade | Numbered commands through the ports | Its 2 KB on-chip drawing routine, copied from the cartridge ([Two-way mode](../sh2/cache.md#two-way-mode-2-kb-of-on-chip-ram)); the rest not traced |
| Motocross Championship | Commands through the ports | Its whole SH-2 program, run in place from the cartridge ([Living with bus contention](bus.md#what-each-program-did)) |
| ECCO CinePak demo | Nothing | The movie, read a byte at a time through the cache-through cartridge view ([Cache discipline](cache.md#data-from-outside)) |
| d32xr | Nothing in its cartridge build; in its Mega-CD build, video chunks through the FIFO | Its whole data file, used in place in the cartridge, with textures copied into a cache when needed ([Leave it in the cartridge](../techniques/memory.md#leave-it-in-the-cartridge)) |

Sources: [MK2; AB32X; SWA; MCX; ECCO; D32XR, as linked]. None of the four retail games arms the FIFO ([DREQ and the FIFO](../32x/fifo.md#agreeing-on-start-and-end)); Knuckles' Chaotix, the fifth read for this book, sends the Master its command lists through it ([Knuckles' Chaotix: command lists](../32x/fifo.md#knuckles-chaotix-command-lists)). Their 68000s send small amounts every frame, and the SH-2s fetch the bulk themselves.

## Drawing off screen and copying: Motocross Championship

Motocross Championship's menus and race screens use the 32X's direct-colour mode, 15 bits a pixel. Its Master does not draw them into the frame buffer. It draws into a buffer in SDRAM, and a separate routine copies the finished picture into the frame buffer, one word per store: 64,960 words (126.9 KB) from `0x06003EF0` to the frame buffer just past its line table [MCX, SH-2 code at `0x020295B0`-`0x020295CA`]. That is 320 × 203 pixels at two bytes each, so the staging buffer takes half of SDRAM. The routine that sets the display mode decides whether the copy runs: it clears the copy's enable flag when it selects direct colour, and sets it, turning the copy off, when it selects packed pixels [MCX, SH-2 code at `0x0202C140`-`0x0202C166`].

The copy is expensive. Each word takes a load, a store, a count, a test and a taken branch, about 7 to 9 clocks with the cache misses on the SDRAM side. That makes 450,000 to 580,000 clocks per picture, more than a whole frame of the Master's time <span class="tag manual">manual</span>. The game shows a new picture every four frames ([What the shipped games ran at](60fps.md#what-the-shipped-games-ran-at)), so the copy takes about a third of the Master's time for each picture.

What the copy buys is not stated in the code. Drawing in SDRAM gives cached, burst-speed reads of the picture being drawn, and leaves the frame buffer free until the picture is finished. The cheaper way to get the second benefit is the 32X's own double buffering: draw into the back buffer and flip FS ([Frame buffers and the FS bit](../32x/vdp.md#frame-buffers-and-the-fs-bit)). A direct-colour picture fits in one frame buffer, so both buffers remain available.

## Never stall a whole frame

A big job done in one go stops everything else: the music stutters, input is missed, the screen freezes. Shipped code cuts big jobs into pieces and does one piece per frame:

- **Uploads in chunks.** Aerobiz Supersonic splits large tile sets into 4 KB DMA transfers with frame waits between them ([DMA in a real game](../megadrive/vdp-dma.md#dma-in-a-real-game)) [AB-DISASM, VRAMBulkLoad.asm].
- **Slicing inside the interrupt.** Its vertical interrupt fills or reads back name table rectangles four rows at a time and keeps the running VDP command in RAM, so the next frame resumes where this one stopped ([Organising the frame](../megadrive/vdp-timing.md#organising-the-frame)) [AB-DISASM, VInt_Handler2.asm, VInt_Handler3.asm].
- **Decompressors that can stop.** d32xr's LZSS decoder produces at most a requested number of bytes and saves its state, so a caller can take one picture line or one block of music at a time ([d32xr's LZSS](../techniques/compression.md#d32xrs-lzss-byte-aligned-and-resumable)) [D32XR, lzss.c].
- **A faster CPU for the job.** Aerobiz Ultimate's largest decompression took 62 frames on the 68000 and about 4.4 on an SH-2 <span class="tag emulator">emulator</span> ([Moving decompression to an SH-2](../techniques/compression.md#moving-decompression-to-an-sh-2)) [AU-NOTES, ROADMAP.md U-046].

## Rings between a producer and a consumer

When one CPU produces data and another consumes it at its own pace, a ring buffer sits between them: the writer adds at one position, the reader takes from another, and each only waits when the ring is full or empty. Most of the programs here use one: After Burner Complete's 64-sample ring between its mixer and its PWM interrupt ([PWM audio](../32x/pwm.md#1-the-pwm-interrupt-star-wars-arcade)), d32xr's 32 KB ring of music between its decompressor and the Z80 ([d32xr](../megadrive/sound.md#d32xr-decompress-on-the-68000-replay-on-the-z80)), and d32xr's sound command ring between the two SH-2s ([Between the two SH-2s](../32x/communication.md#between-the-two-sh-2s)).

A plain ring hands out data in two pieces when a block wraps past the end. That is awkward for a DMA transfer or a parser that wants one contiguous block. d32xr's video player uses a ring that never splits a block [D32XR, mars_newrb.c]:

- **Reserve, then commit.** The writer asks for a block of a given size and gets a pointer to contiguous space, or nothing. It fills the space, by DMA or by hand, and then commits it. The reader does the same in reverse. Until a block is committed, the other side cannot see it.
- **Wrap early.** If the space left before the end is too short, the writer records where the data stops and starts again at the beginning. The reader jumps back when it reaches that mark.
- **Full or empty without a counter.** Positions run from 0 up to twice the size, and are brought back down only when both have passed the size. Equal positions mean empty; positions a whole size apart mean full.
- **Shared safely.** The ring's header sits on its own 16-byte lines, and each operation purges three lines before reading them ([Keeping the views in step](../sh2/cache.md#keeping-the-views-in-step)). A test-and-set lock guards it, and a request that cannot be met waits 512 loop passes before returning, so a waiting CPU does not flood the bus.

## Overlapping the transfer with the work

d32xr's Mega-CD build plays video by streaming it from the disc. Its player shows three ways to keep data moving while the CPU works [D32XR, marsroq.c, src-md/scd_roq.c]:

- **DMA straight into the rings.** The 68000 feeds each chunk from the disc through the FIFO. The SH-2's receiving code reserves space for the chunk in the video or the sound ring and gives that address to the DMA, so the data is never copied again ([DREQ and the FIFO](../32x/fifo.md)).
- **Copy the last band while decoding the next.** The decoder needs the previous frame for motion. After each band of 16 rows is decoded, SH-2 DMA copies that band to the previous-frame buffer while the CPU decodes the next band ([DMA controller](../sh2/dmac.md#sharing-the-bus)).
- **Refill while waiting.** Every loop that waits, for a DMA to end or for the time to show the next frame, asks for more disc data whenever both rings have more than 1 KB free.

It also times the picture by the sound. The time of a frame is worked out from the count of sound samples played so far, plus a fixed 267 ms allowance for the sound buffered ahead. A frame that is already late is shown at once, without waiting. Video timed by the audio clock stays in step with the sound however the decoding time varies.

## Hooking the choke point

A port of an existing game has to catch data where the game moves it, not where it is stored. The Aerobiz Ultimate project shows both sides of this <span class="tag emulator">emulator</span>:

- **Replace the routine, not the callers.** Its SH-2 decompressor is reached through an 8-byte patch at the start of the 68000 routine. Every caller is redirected without being touched ([Moving decompression to an SH-2](../techniques/compression.md#moving-decompression-to-an-sh-2)).
- **Forward what the game uploads, not what the cartridge holds.** Its SH-2 redraws the world map in 256 colours, first from the clean asset in the cartridge. But the game edits the map's tiles before uploading them: it draws route lines into them and overwrites some with a title bar. So the project hooks both places where tiles reach the Mega Drive VDP, the 68000 copy loop and the DMA routine. It passes the uploaded words that fall inside the map's tile range to the SH-2 through the frame buffer, in blocks of `$800` words. The SH-2 decodes them into its own copy and redraws only when something actually changed [AU-NOTES, PORT_ARCHITECTURE.md §4.1; disasm/sh2/master/fb.c].

## What to take away

- The SH-2s can read the cartridge themselves, at several times the rate the 68000 can feed them. Send decisions from the 68000, and let the SH-2s fetch the data.
- The Mega Drive VDP takes a few kilobytes per frame. Load its graphics ahead of time, or in slices.
- Never let one transfer or one decompression take a whole frame. Chunk it, and make decoders resumable.
- Put a ring between any producer and consumer that run at different paces. Give out contiguous blocks if DMA or a parser fills them.
- Overlap transfers with work: DMA into the destination directly, and refill while you wait.
- Copying a finished picture into the frame buffer can cost more than a frame. Flip FS instead where you can.

## Open questions

- Why does Motocross Championship draw into SDRAM and copy, when a direct-colour picture fits in either frame buffer?
- How fast does SH-2 DMA move SDRAM to the frame buffer in 16-byte units, measured on a console?
- How much does a cartridge DMA on the Mega Drive side, with RV set, delay SH-2s that are streaming from the cartridge?

## Sources

- [MCX](../appendices/bibliography.md#mcx): SH-2 code at `0x020295B0`-`0x020295CA`, `0x0202C140`-`0x0202C166`
- [MK2](../appendices/bibliography.md#mk2), [AB32X](../appendices/bibliography.md#ab32x), [SWA](../appendices/bibliography.md#swa), [ECCO](../appendices/bibliography.md#ecco): as linked
- [D32XR](../appendices/bibliography.md#d32xr): lzss.c, mars_newrb.c, marsroq.c, src-md/scd_roq.c
- [AB-DISASM](../appendices/bibliography.md#ab-disasm): VRAMBulkLoad.asm, VInt_Handler2.asm, VInt_Handler3.asm
- [AU-NOTES](../appendices/bibliography.md#au-notes): ROADMAP.md U-046; PORT_ARCHITECTURE.md §4.1; disasm/sh2/master/fb.c
- [32X-HWM](../appendices/bibliography.md#32x-hwm): §4.4 pp.77-78
- [MD-SWM](../appendices/bibliography.md#md-swm): §2.7
