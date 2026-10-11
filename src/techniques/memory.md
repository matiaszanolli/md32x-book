# Memory on a 256 KB machine

The two SH-2s share 256 KB of SDRAM for code, data, stacks and everything decoded from the cartridge. The 68000 has its own 64 KB of work RAM. There is no memory management unit and no operating system, and nothing to tell you when one structure has run into another. This chapter covers how shipped games and d32xr lay their memory out, and how they make it go further: leaving data in the cartridge, borrowing the frame buffer, allocating in zones and pools, packing structures, and caching decoded data.

## What there is

| Memory | Size | Who reaches it | Notes |
|--------|------|----------------|-------|
| SDRAM | 256 KB | Both SH-2s | Cached at `0x06000000`, cache-through at `0x26000000` ([The SH-2 memory map](../32x/architecture.md#the-sh-2-memory-map)) |
| Frame buffer, the one not on screen | 128 KB | The SH-2s while FM = 1, the 68000 while FM = 0 | Byte writes of 0 are ignored; reads are slow ([The 32X VDP](../32x/vdp.md)) |
| On-chip RAM | 2 KB per SH-2, in two-way cache mode | Its own SH-2 only | One clock per access ([Two-way mode](../sh2/cache.md#two-way-mode-2-kb-of-on-chip-ram)) |
| Cartridge ROM | Up to 4 MB in one piece | Both SH-2s, and the 68000 through windows | Read-only and slow; an SH-2 that reads it is stalled while RV = 1 ([The RV bit](../32x/architecture.md#the-rv-bit)) |
| Mega Drive work RAM | 64 KB | The 68000; the Z80 can write it through its bank window but not read it ([The bank window](../megadrive/architecture.md#the-bank-window)) | Not reachable from the SH-2s |

Most SDRAM goes to one of three things: the program, which the boot copies from the cartridge; whatever the game decodes; and working data. Each game in the sources makes a different trade between them. None of the three below uses on-chip RAM, which needs two-way cache mode: After Burner Complete and Mortal Kombat II never set the cache control register, and d32xr only ever writes four-way settings [AB32X, MK2, D32XR, crt0.s, 32x.h]. Star Wars Arcade and Knuckles' Chaotix do ([Cache choices](../patterns/cache.md)).

## Three SDRAM maps

**After Burner Complete** gives more than half of SDRAM to one cache [AB32X, user header, SH-2 code at `0x06002120`, `0x06000200`, `0x06003B66`, `0x060065A0`; notes/games/ab/ANALYSIS.md]:

| Address | Size | What |
|---------|------|------|
| `0x06000000`-`0x06019FFF` | 104 KB | The program as copied by the boot: both CPUs' code, tables and variables, 29 KB of uncompressed images, and from `0x06017588` three rings of 194 object entries (16 bytes each, 9 KB), which the cartridge holds as zeros |
| `0x06019A00`-`0x0601B9FF` | 8 KB | The depth-sort buckets: 256 of 32 bytes, a count and up to 30 entry numbers. The first 1.5 KB lie inside the program's range above; the other 6.5 KB (`0x0601A000` up) are past the end of the image |
| `0x0601BA00` | 1 KB | 128 descriptors for the sprite cache |
| `0x0601BE00`-`0x0603D9FF` | 135 KB | Decoded sprites |
| `0x0603DA00`-`0x0603FFFF` | 9.5 KB | Both stacks (the Master's from `0x0603F000`, the Slave's from `0x0603F600`) and the Slave's sound state |

**Mortal Kombat II** keeps its program small and unpacks graphics into large buffers [MK2, SH-2 program; notes/games/mk2/ANALYSIS.md]:

| Address | What |
|---------|------|
| `0x06000000`-`0x06007E13` | The program, 31.5 KB. Its last third, from `0x060051E2`, is palettes and tables |
| `0x0600A000` | A copy of the palette, then the Slave's few variables (`0x0600A200`-`0x0600A22B`), then the Master's, including the block the 68000 sends each frame (`0x0600A248`) |
| `0x0600A248`-`0x06017170` | About 52 KB I have not mapped. The program's literal pools point at 116 distinct addresses in it, up to `0x06016E18` (variables, object lists, tables), so it is in use, not free. Between the program's end and `0x0600A000` there are 8.6 KB more, not looked at |
| `0x06017170`, `0x06028530` | Graphics unpacked from the cartridge; the distances to the next buffer are about 69 KB and 57 KB |
| `0x06036B2C` onwards | Three fonts, unpacked (at `0x06036B2C`, `0x06037F60`, `0x06038F28`). Up to the Slave's stack top at `0x0603F000` there are 34 KB, and the program also refers to addresses `0x0603AD40`, `0x0603B400` and `0x0603EFF8` in it, which I have not identified |
| Top of SDRAM | Stacks: the Master's from `0x06040000`, the Slave's from `0x0603F000` |

**d32xr** puts nearly everything in one zone and lets an allocator share it out. It calls its two CPUs Primary and Secondary; they are the Master and the Slave [D32XR, mars-ssf.ld, marsnew.c, crt0.s, Makefile]:

- The program's data, and the routines that must run fast, which it links into SDRAM rather than leaving in the cartridge.
- A zone of 210 KB in the default build, a single static array: `BASE_ZONE_SIZE` is `0x33000` (204 KB) in `marsnew.c`, and `0x1800` (6 KB) more when `DISABLE_DMA_SOUND` is defined, which the Makefile does unless `ENABLE_DMA_SOUND` is set. The other 46 KB of SDRAM hold everything else: initialised data, the other variables, the routines linked into SDRAM, and both stacks. I did not build the program, so I cannot split that further.
- Stacks at the top: the Primary's from `0x0603F400`, the Secondary's from `0x06040000`, which gives the Secondary 3 KB before it meets the Primary's stack top.
- Per-picture working data in the frame buffer, not in SDRAM (see [Borrowing the frame buffer](#borrowing-the-frame-buffer)).

The three side by side, in KB of the 256 (approximate where the map is):

| | Program image and fixed data | Decoded or loaded data | Working data and the rest | Room for the upper stack |
|---|---|---|---|---|
| After Burner Complete | 104 | 136 (sprite cache and its descriptors) | 16 (sort buckets past the image 6.5; stacks and sound state 9.5) | The Slave's, under 1.5: its range also holds the Slave's sound ring and variables |
| Mortal Kombat II | 31.5 | about 160 (`0x06017170` up to the Slave's stack top; three fonts included) | about 65 (61 between the program and the first buffer; the Master's stack 4) | The Master's, 4 |
| d32xr | 46 for everything outside the zone, not split | 210 (the zone: level data, texture cache, objects) | none | The Secondary's, 3 |

All three put the stacks at the top and grow them down towards the data. Nothing checks that they do not meet. A stack that grows into a buffer corrupts it without warning, so measure each stack's deepest use (fill it with a pattern, run the game, see how much was overwritten) and leave a margin.

Mortal Kombat II and After Burner Complete also share no SDRAM between the two CPUs: each CPU's variables are in a range the other never touches, and they talk only through the communication ports. That removes the cache problems between the two CPUs ([Keeping the views in step](../sh2/cache.md#keeping-the-views-in-step)).

## Leave it in the cartridge

The SH-2 sees the whole cartridge directly, so data that is only read does not have to be copied at all:

- **d32xr uses uncompressed lumps where they lie.** Looking one up returns a pointer into the cartridge, with no copy. Wall textures are drawn straight from the cartridge unless the texture cache has a copy ([Caches with a lifetime in pictures](#caches-with-a-lifetime-in-pictures)). A build option goes further and reads the level's segs and nodes from the cartridge instead of loading them [D32XR, w_wad.c, r_main.c, p_setup.c `USE_SMALL_LUMPS`].
- **After Burner Complete keeps its sprites compressed in the cartridge** and decodes only the ones on screen.

Reading the cartridge costs time. Each cache miss fills a 16-byte line, which takes 64 to 136 clocks from the cartridge against 12 from SDRAM ([What a 16-bit bus costs](../sh2/bsc.md#what-a-16-bit-bus-costs)). The 68000 also uses that bus, and an SH-2 that reads the cartridge is stalled while the 68000 has RV set (SH-2 code running from SDRAM is not) ([The RV bit](../32x/architecture.md#the-rv-bit)). Data read once per picture, in order, is fine in the cartridge. Data read often, or at random, should be copied or cached.

## Borrowing the frame buffer

The frame buffer not on screen is 128 KB of memory the SH-2s can use whenever they hold FM. A 320 × 224 picture in packed pixel mode (one byte a pixel) uses 70 KB of it; the rest is spare, and before the first picture is drawn all of it is. d32xr uses it twice [D32XR, marsnew.c `I_TempBuffer`, `I_WorkBuffer`; r_main.c]:

- **While a level loads**, up to about 127 KB of it is a temporary buffer. Compressed lumps are unpacked into it, and the level loader stages data there. The buffer is cleared first, because byte writes of 0 are ignored ([Compression](compression.md#d32xrs-lzss-byte-aligned-and-resumable)).
- **Every picture**, the space below the visible lines of the buffer being drawn, about 58 KB at 224 lines, holds the renderer's working arrays: visible planes, the clip lists, the wall and sprite records, the sorted lists, and two column caches. Each picture builds them from scratch, so it does not matter that the two buffers swap after every picture.

The frame buffer is slower than SDRAM: reads take 7 to 14 clocks. Use it for data that is written once and read a few times, through the cache-through address unless it is the same in both buffers ([A safe use of the cached frame buffer](../sh2/cache.md#a-safe-use-of-the-cached-frame-buffer)). Wide guard bands use the same spare memory, so the two compete for the same 58 KB and a program has to split it ([Guard bands](../32x/vdp.md#guard-bands-drawing-without-clipping)).

Aerobiz Ultimate does the same in the other direction: its SH-2 decompressor leaves its results in a 56 KB area of the frame buffer for the 68000 to collect, which works only while the 32X layer is blank [AU-NOTES, ROADMAP.md U-046].

## A zone allocator

d32xr allocates almost everything from its zone, with an allocator inherited from Jaguar Doom [D32XR, z_zone.c, doomdef.h]:

- **The zone is a list of blocks that cover it exactly**, each with a 12-byte header: size, tag, a check word, and links to the next and previous blocks. There are no gaps.
- **Allocation is next-fit.** A pointer, the rover, remembers where the last allocation ended. The search starts there, skips blocks in use, wraps round at the end, and fails if it gets back to where it started. Sizes are rounded up to 4 bytes.
- **A free block is split only if more than 64 bytes would be left over.** Otherwise the caller gets the whole block. Tiny free fragments, which nothing could use, are never made.
- **Freeing merges with both neighbours** if they are free, so two free blocks are never next to each other.
- **Tags give each block a lifetime.** Blocks tagged for the level are all freed at once when it ends. There is no automatic purging of blocks the way PC Doom has; a failed allocation stops the game with an error, unless the caller asked for a null result instead.
- **The zone is a parameter.** The texture cache runs its own zone, made from one large block of the main zone ([Caches with a lifetime in pictures](#caches-with-a-lifetime-in-pictures)).
- **A check at every level change.** The allocator walks the whole chain of blocks and verifies it.

Before the zone is set up, the same memory is lent to the intro's video player [D32XR, d_main.c].

The allocator's blocks are only 4-byte aligned. The level loader asks for 16 bytes more than it needs and rounds the pointer up to a cache line by hand, so that each map array starts on a line boundary; the source comment says no more than that. Only the start is aligned. The size is not rounded, so unless an array's size is a multiple of 16 its last line can still be shared with the next block's header, and purging that line would reach the neighbour [D32XR, p_setup.c, vertexes, segs, sectors, nodes, lines and sides].

## Pools instead of a heap

For objects that come and go during play, d32xr does not use the zone each time [D32XR, p_mobj.c, p_setup.c; p_base.c]:

- **Pre-allocate at level load.** The loader counts the things the level will spawn, adds 40 for bullet puffs and missiles, and allocates them in two arrays in one go, each element threaded onto a free list. Spawning takes from the free list and only falls back to the zone if the list is empty.
- **Objects that never move are shorter.** Decorations that never move or think are allocated only up to the first field that moving objects need: 52 bytes instead of 80. Code that would touch the missing fields checks the flag first.
- **Removed objects wait until the end of the tic.** A removed moving object goes to a "limbo" list, and only at the end of the game tic does it go back on the free list. Any pointer to it that other code holds during the tic still points at a valid, if dead, object.

## Smaller structures

Doom's map structures are made for a PC with megabytes of memory. d32xr shrinks them [D32XR, doomdef.h, r_local.h, p_setup.c, p_maputl.c, r_phase1.c, r_phase2.c]:

- **16-bit pointers.** A pointer to a 4-byte-aligned object in SDRAM is stored as (address − `0x06000000`) ÷ 4, in 16 bits. That reaches all 256 KB. Object lists, sector lists, blockmap chains and the allocator's own links all use them, halving each field. The source warns that an object at exactly `0x06000000` would come out as the null pointer. Only cached SDRAM addresses work: nothing in the cartridge, the frame buffer or on-chip RAM can be linked this way, which matters because this chapter also recommends leaving data in the cartridge. Those objects are reached by ordinary pointers.
- **Fields cut to size.**

  | Structure | In the map file | In memory | How |
  |-----------|-----------------|-----------|-----|
  | Seg | 12 bytes | 6 | Side folded into the line number's low bit; angle and offset dropped. The offset is recomputed when drawn, with a 16-bit integer square root |
  | Side | 30 bytes | 8 | Textures as byte indices (so at most 256 wall textures); two 12-bit offsets in 3 bytes, recovered by shifting left and right again to restore the sign |
  | Node | 28 bytes | 16 | Each child's bounding box as four 4-bit fractions of the parent's box, rounded outwards so it only grows |
  | Line | 14 bytes | 10 | Side and vertex numbers as 16 bits; flags and special type as bytes; the tag is gone (see below) |
  | Sector | 26 bytes | 24 | Two 32-bit heights; picture names became byte indices, light level and special type bytes; the tag is gone; three 16-bit object links |

  The reject table, which says which sectors can see each other, is stored as a triangle on the assumption that it is symmetrical.
- **Rare fields moved out.** Only a few lines and sectors have a tag, the number that links a switch to a door. d32xr takes the tag field out of both structures and keeps (object, tag) pairs in small tables, 4 bytes for each tagged object. The tables are hash tables with linear probing: a lookup starts at a slot worked out from the object's number and steps forwards, wrapping at the end, until it finds the object. Nothing marks the end of a probe sequence, so a lookup for an object with no tag (most of them) checks every entry in the table before it returns 0. Finding every sector with a given tag is a plain scan that remembers where it stopped [D32XR, p_maputl.c `P_GetTag`, `P_SetTag`, `P_IterateTag`].

## One array, two uses

d32xr's renderer has an array of wall records and an array of sprite records, and they are the same memory [D32XR, r_main.c, r_local.h, r_phase3.c]. The renderer works in phases: walls and planes are drawn first, then sprites are prepared and drawn. Each wall record's first 32 bytes hold values that only wall and plane drawing need. A sprite record is exactly 32 bytes, so once the walls are drawn, the sprite records are written over those first 32 bytes. Sprite clipping still needs the rest of each wall record, its extent and scale, and that is beyond byte 32. A comment in the structure marks the block that must stay big enough.

The two arrays are one array of 165 records (`MAXWALLCMDS`), and the sprite pointer steps through it with the wall record's size, about 76 bytes by my count of its fields. Both limits are 165, so the walls and the sprites are each limited by the array. A picture with more than 165 wall pieces stops adding walls. The sprite preparation stops adding world sprites at 165 minus the two slots kept for the player's weapon sprites, and drops the rest without any message. The sorted lists of planes and of sprites share a buffer the same way.

The method: list which phase uses each field, and let data whose phases do not overlap share memory. It needs a comment at the structure, because a later change that reads one of the overwritten fields after the switch breaks silently.

Aerobiz Supersonic does a simpler case of the same idea on the 68000: not two record layouts overlaid by phase, but one scratch buffer reused at different times. The buffer at `$FF1804` that receives decompressed graphics is also where the game builds its save data [AB-DISASM, analysis/RAM_MAP.md].

## A cache of decoded sprites

After Burner Complete stores its sprites compressed in the cartridge, decodes each shape the first time it is needed, and scales it from the decoded copy in every picture after that [AB32X, SH-2 code at `0x060065A0`-`0x0600676C`]:

- **Descriptors.** A ring of 128 entries of 8 bytes at `0x0601BA00`: a 16-bit shape number, a 16-bit decoded size in bytes, then one longword whose top byte is the lap number and whose low 24 bits are the byte offset in the buffer.
- **Lookup** walks back from the newest entry to the oldest, comparing shape numbers. A hit gives the offset and changes nothing: the replacement policy is first in, first out, and a shape used every frame is dropped as soon as the ring reaches it, like any other. The bits of the shape number that choose mirroring and scaling mode are cleared first, so every mode of a shape shares one decoded copy.
- **A miss** decodes the shape ([Decoded once, into a cache](compression.md#decoded-once-into-a-cache-after-burner-complete)) into the 135 KB buffer, straight after the newest entry. Entries are dropped from the oldest end for as long as they overlap the space the new shape needs. If the descriptor ring is full, the oldest entry goes too.
- **Wrapping.** When the shape would run past the end of the buffer, it goes at the start. Leftovers from the previous lap may still sit at the end of the buffer, beyond the newest entries, and would never be reached by the overlap check, so the cache keeps a lap number in each entry and drops everything older than the current lap first.
- **No fragmentation.** The buffer is filled strictly in order, like a queue, so there are never holes to search for. The price is that the oldest shape is dropped even if it is still on screen; it is decoded again when next needed.
- **Some images skip the cache.** Shapes numbered `$7Fxx` come from 32 images of 928 bytes kept uncompressed in the program, 29 KB in all, with their own drawing path (`0x060064CC`).

In PicoDrive's per-address profile of 2,000 frames of play, the sprite list and the cache's lookup and decoding together take 3.5% of the Master's time, and the scaler that reads the decoded copies 26.0% <span class="tag emulator">emulator</span> [AB32X, PC profile in PicoDrive; notes/games/ab/ANALYSIS.md, "Where the waits go"]. The profile counts PicoDrive's emulated cycles for each address, and upstream PicoDrive charges no cycles for SH-2 memory accesses ([How sure we are](../conventions.md#how-sure-we-are)). So these shares leave out what this chapter is about, the extra clocks of cartridge, SDRAM and frame buffer reads, and the cache's real share is probably larger. The Master also spent 25.4% of the run not executing (asleep in polls the emulator recognised) and 18.3% waiting for fills, which are counted separately.

## Caches with a lifetime in pictures

d32xr's texture cache keeps SDRAM copies of the wall textures and floor textures in view, which are faster to draw from than the cartridge [D32XR, r_cache.c, r_main.c, r_phase9.c]:

- **Its size is whatever is left.** After a level loads, the cache takes the largest free block of the zone, less 8 KB (16 KB on maps with a boss that spawns monsters) left free for allocations during play.
- **Each entry has a lifetime of 3 pictures** (`CACHE_FRAMES_WALLS` and `CACHE_FRAMES_FLATS`). During a picture, each texture drawn resets its entry's count to 3. At the end of the picture, every entry's count goes down by one. An entry drawn this picture therefore ends it at 2, and reaches 0 after two more pictures without being drawn.
- **When there is no room**, entries at 0 are freed, along with those not used in this picture that are smaller than the new texture. If that does not free enough space in one piece, the texture is simply not cached in this picture. The game draws it from the cartridge as before.
- **One new texture a picture** at most, in the default build. The cost of filling the cache is spread out.
- **The pointer is swapped.** Adding an entry points the texture's data pointer at the copy and keeps the old cartridge pointer; dropping it puts the old pointer back. The drawing code never knows whether it is reading a copy. The 4 bytes in front of each copy point back to its entry, so a texture pointer leads to its entry with no search.

Nothing depends on the cache: a texture that is not in it is drawn correctly, only more slowly. That is what makes it safe to fill it from whatever memory is left over.

## What to take away

- Write down the SDRAM map, including the stacks, and keep the stacks' worst case measured.
- Leave read-only data in the cartridge if it is read rarely and in order; copy or cache what is read often.
- The hidden frame buffer is spare memory for setup and per-picture scratch, if you can live with slow reads and dropped zero bytes.
- Allocate per level, with lifetimes, and free in bulk. Pool objects that come and go, and do not reuse a freed object until nothing can still hold it.
- Shrink structures: 16-bit pointers, fields recomputed instead of stored, rare fields moved to side tables, and memory shared between phases that never overlap.
- Cache decoded data with a policy that cannot fragment (a first-in first-out ring) or a lifetime in pictures, and make every miss harmless.

## Open questions

- How deep do the stacks of these games actually go? Each game's upper stack has a fixed room before it meets the lower stack's top or other data: After Burner Complete's Slave under 1.5 KB (the range also holds its sound ring and variables), Mortal Kombat II's Master 4 KB, d32xr's Secondary 3 KB. The lower stack's limit is the data under it, which I did not pin down for any of them.
- What fills Mortal Kombat II's 52 KB between its variables and its first buffer, and the 8.6 KB between its program and `0x0600A000`?
- How much of d32xr's 46 KB outside the zone is the program's data, how much is bss and how much is stack? It needs a build.
- Does a real console agree with the profile's share for After Burner Complete's cache, once the cartridge and SDRAM costs are counted?
- How often does After Burner Complete's cache miss in play, and how does that change with the ring's size?
- How much faster is a cached texture on a console, and is the cartridge read or the cache refill the larger cost?

## Sources

- [AB32X](../appendices/bibliography.md#ab32x): user header; SH-2 code at `0x06000200`, `0x06002120`, `0x06003B66`, `0x0600257C`, `0x060064CC`, `0x060065A0`-`0x0600676C`; PC profile in PicoDrive; notes/games/ab/ANALYSIS.md
- [MK2](../appendices/bibliography.md#mk2): SH-2 program; notes/games/mk2/ANALYSIS.md
- [D32XR](../appendices/bibliography.md#d32xr): z_zone.c, doomdef.h, r_local.h, r_main.c, r_cache.c, r_phase1.c, r_phase2.c, r_phase9.c, r_phase3.c, p_setup.c, p_mobj.c, p_maputl.c, p_base.c, w_wad.c, marsnew.c, d_main.c, crt0.s, mars-ssf.ld, 32x.h, Makefile
- [AU-NOTES](../appendices/bibliography.md#au-notes): ROADMAP.md U-046
- [AB-DISASM](../appendices/bibliography.md#ab-disasm): analysis/RAM_MAP.md
