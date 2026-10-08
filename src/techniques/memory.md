# Memory on a 256 KB machine

The two SH-2s share 256 KB of SDRAM for code, data, stacks and everything decoded from the cartridge. The 68000 has its own 64 KB of work RAM. There is no memory management unit and no operating system, and nothing to tell you when one structure has run into another. This chapter covers how shipped games and d32xr lay their memory out, and how they make it go further: leaving data in the cartridge, borrowing the frame buffer, allocating in zones and pools, packing structures, and caching decoded data.

## What there is

| Memory | Size | Who reaches it | Notes |
|--------|------|----------------|-------|
| SDRAM | 256 KB | Both SH-2s | Cached at `0x06000000`, cache-through at `0x26000000` ([The SH-2 memory map](../32x/architecture.md#the-sh-2-memory-map)) |
| Frame buffer, the one not on screen | 128 KB | The SH-2s while FM = 1, the 68000 while FM = 0 | Byte writes of 0 are ignored; reads are slow ([The 32X VDP](../32x/vdp.md)) |
| On-chip RAM | 2 KB per SH-2, in two-way cache mode | Its own SH-2 only | One clock per access ([Two-way mode](../sh2/cache.md#two-way-mode-2-kb-of-on-chip-ram)) |
| Cartridge ROM | Up to 4 MB in one piece | Both SH-2s, and the 68000 through windows | Read-only, slow, and blocked while RV = 1 ([The RV bit](../32x/architecture.md#the-rv-bit)) |
| Mega Drive work RAM | 64 KB | 68000, and the Z80 through its bank window | Not reachable from the SH-2s |

Most SDRAM goes to one of three things: the program, which the boot copies from the cartridge; whatever the game decodes; and working data. Each game in the sources makes a different trade between them.

## Three SDRAM maps

**After Burner Complete** gives more than half of SDRAM to one cache [AB32X, user header, SH-2 code at `0x06002120`, `0x06000200`, `0x060065BC`]:

| Address | Size | What |
|---------|------|------|
| `0x06000000`-`0x06019FFF` | 104 KB | The program as copied by the boot: both CPUs' code, tables and variables, and 29 KB of uncompressed images |
| `0x0601BA00` | 1 KB | 128 descriptors for the sprite cache |
| `0x0601BE00`-`0x0603D9FF` | 135 KB | Decoded sprites |
| `0x0603DA00`-`0x0603FFFF` | 9.5 KB | Both stacks (the Master's from `0x0603F000`, the Slave's from `0x0603F600`) and the Slave's sound state |

**Mortal Kombat II** keeps its program small and unpacks graphics into large buffers [MK2, SH-2 program; notes/games/mk2/ANALYSIS.md]:

| Address | What |
|---------|------|
| `0x06000000`-`0x06007E13` | The program, 31.5 KB, most of it past `0x060051E2` palettes and tables |
| `0x0600A000` | A copy of the palette, then the Slave's few variables (`0x0600A200`-`0x0600A22B`), then the Master's, including the block the 68000 sends each frame (`0x0600A248`) |
| `0x06017170`, `0x06028530` | Graphics unpacked from the cartridge; the gaps to the next buffer are about 69 KB and 57 KB |
| `0x06036B2C` onwards | Three fonts, unpacked |
| Top of SDRAM | Stacks: the Master's from `0x06040000`, the Slave's from `0x0603F000` |

**d32xr** puts nearly everything in one zone and lets an allocator share it out [D32XR, mars-ssf.ld, marsnew.c, crt0.s]:

- The program's data, and the routines that must run fast, which it links into SDRAM rather than leaving in the cartridge.
- A zone of 210 KB in the default build, a single static array.
- Stacks at the top: the Primary's from `0x0603F400`, the Secondary's from `0x06040000`, which gives the Secondary 3 KB.
- Per-frame working data in the frame buffer, not in SDRAM (see [Borrowing the frame buffer](#borrowing-the-frame-buffer)).

All three put the stacks at the top and grow them down towards the data. Nothing checks that they do not meet. A stack that grows into a buffer corrupts it without warning, so measure each stack's deepest use (fill it with a pattern, run the game, see how much was overwritten) and leave a margin.

Mortal Kombat II and After Burner Complete also share no SDRAM between the two CPUs: each CPU's variables are in a range the other never touches, and they talk only through the communication ports. That removes cache problems entirely ([Keeping the views in step](../sh2/cache.md#keeping-the-views-in-step)).

## Leave it in the cartridge

The SH-2 sees the whole cartridge directly, so data that is only read does not have to be copied at all:

- **d32xr uses uncompressed lumps where they lie.** Looking one up returns a pointer into the cartridge, with no copy. Wall textures are drawn straight from the cartridge unless the texture cache has a copy ([Caches with a lifetime in frames](#caches-with-a-lifetime-in-frames)). A build option goes further and reads the level's segs and nodes from the cartridge instead of loading them [D32XR, w_wad.c, r_main.c, p_setup.c `USE_SMALL_LUMPS`].
- **After Burner Complete keeps its sprites compressed in the cartridge** and decodes only the ones on screen.

Reading the cartridge costs time. Each cache miss fills a 16-byte line, which takes 64 to 136 clocks from the cartridge against 12 from SDRAM ([What a 16-bit bus costs](../sh2/bsc.md#what-a-16-bit-bus-costs)). The 68000 also uses that bus, and an SH-2 is stalled entirely while the 68000 has RV set. Data read once per frame, in order, is fine in the cartridge. Data read often, or at random, should be copied or cached.

## Borrowing the frame buffer

The frame buffer not on screen is 128 KB of memory the SH-2s can use whenever they hold FM. A 320 × 224 picture uses 70 KB of it; the rest is spare, and before the first frame is drawn all of it is. d32xr uses it twice [D32XR, marsnew.c `I_TempBuffer`, `I_WorkBuffer`; r_main.c]:

- **While a level loads**, up to about 127 KB of it is a temporary buffer. Compressed lumps are unpacked into it, and the level loader stages data there. The buffer is cleared first, because byte writes of 0 are ignored ([Compression](compression.md#d32xrs-lzss-byte-aligned-and-resumable)).
- **Every frame**, the space below the visible lines of the buffer being drawn, about 58 KB at 224 lines, holds the renderer's working arrays: visible planes, the clip lists, the wall and sprite records, the sorted lists, and two column caches. Each frame builds them from scratch, so it does not matter that the two buffers swap at every frame.

The frame buffer is slower than SDRAM: reads take 7 to 14 clocks. Use it for data that is written once and read a few times, through the cache-through address unless it is the same in both buffers ([A safe use of the cached frame buffer](../sh2/cache.md#a-safe-use-of-the-cached-frame-buffer)). Wide guard bands use the same spare memory, so a program cannot have both ([Guard bands](../32x/vdp.md#guard-bands-drawing-without-clipping)).

Aerobiz Ultimate does the same in the other direction: its SH-2 decompressor leaves its results in a 56 KB area of the frame buffer for the 68000 to collect, which works only while the 32X layer is blank [AU-NOTES, ROADMAP.md U-046].

## A zone allocator

d32xr allocates almost everything from its zone, with an allocator inherited from Jaguar Doom [D32XR, z_zone.c, doomdef.h]:

- **The zone is a list of blocks that cover it exactly**, each with a 12-byte header: size, tag, a check word, and links to the next and previous blocks. There are no gaps, and two free blocks are never next to each other.
- **Allocation is next-fit.** A pointer, the rover, remembers where the last allocation ended. The search starts there, skips blocks in use, wraps round at the end, and fails if it gets back to where it started. Sizes are rounded up to 4 bytes.
- **A free block is split only if more than 64 bytes would be left over.** Otherwise the caller gets the whole block. Tiny free fragments, which nothing could use, are never made.
- **Freeing merges with both neighbours** if they are free, so free space never stays in pieces next to each other.
- **Tags give each block a lifetime.** Blocks tagged for the level are all freed at once when it ends. There is no automatic purging of blocks the way PC Doom has; a failed allocation stops the game with an error, unless the caller asked for a null result instead.
- **The zone is a parameter.** The texture cache runs its own zone, made from one large block of the main zone ([Caches with a lifetime in frames](#caches-with-a-lifetime-in-frames)).
- The allocator checks the whole chain of blocks at every level change.

Before the zone is set up, the same memory is lent to the intro's video player [D32XR, d_main.c].

The allocator's blocks are only 4-byte aligned. The level loader asks for 16 bytes more than it needs and rounds the pointer up to a cache line by hand, so that purging a structure's lines does not touch its neighbours [D32XR, p_setup.c].

## Pools instead of a heap

For objects that come and go during play, d32xr does not use the zone each time [D32XR, p_mobj.c, p_setup.c; p_base.c]:

- **Pre-allocate at level load.** The loader counts the things the level will spawn, adds 40 for bullet puffs and missiles, and allocates them in two arrays in one go, each element threaded onto a free list. Spawning takes from the free list and only falls back to the zone if the list is empty.
- **Objects that never move are shorter.** Decorations that never move or think are allocated only up to the first field that moving objects need: 52 bytes instead of 80. Code that would touch the missing fields checks the flag first.
- **Removed objects wait until the end of the tic.** A removed moving object goes to a "limbo" list, and only at the end of the game tic does it go back on the free list. Any pointer to it that other code holds during the tic still points at a valid, if dead, object.

## Smaller structures

Doom's map structures are made for a PC with megabytes of memory. d32xr shrinks them [D32XR, doomdef.h, r_local.h, p_setup.c, p_maputl.c, r_phase1.c, r_phase2.c]:

- **16-bit pointers.** A pointer to a 4-byte-aligned object in SDRAM is stored as (address − `0x06000000`) ÷ 4, in 16 bits. That reaches all 256 KB. Object lists, sector lists, blockmap chains and the allocator's own links all use them, halving each field. The source warns that an object at exactly `0x06000000` would come out as the null pointer. Only cached SDRAM addresses work.
- **Fields cut to size.**

  | Structure | In the map file | In memory | How |
  |-----------|-----------------|-----------|-----|
  | Seg | 12 bytes | 6 | Side folded into the line number's low bit; angle and offset dropped. The offset is recomputed when drawn, with a 16-bit integer square root |
  | Side | 30 bytes | 8 | Textures as byte indices (so at most 256 wall textures); two 12-bit offsets in 3 bytes, recovered by shifting left and right again to restore the sign |
  | Node | 28 bytes | 16 | Each child's bounding box as four 4-bit fractions of the parent's box, rounded outwards so it only grows |

  Lines are 10 bytes and sectors 24, with light levels and special types as bytes. The reject table, which says which sectors can see each other, is stored as a triangle on the assumption that it is symmetrical.
- **Rare fields moved out.** Only a few lines and sectors have a tag, the number that links a switch to a door. d32xr takes the tag field out of both structures and keeps (object, tag) pairs in small tables, 4 bytes for each tagged object. A lookup starts at a slot worked out from the object's number and steps forwards until it finds it. Finding every sector with a given tag is a plain scan that remembers where it stopped.

## One array, two uses

d32xr's renderer has an array of wall records and an array of sprite records, and they are the same memory [D32XR, r_main.c, r_local.h]. The renderer works in phases: walls and planes are drawn first, then sprites are prepared and drawn. Each wall record's first 32 bytes hold values that only wall and plane drawing need. A sprite record is exactly 32 bytes, so once the walls are drawn, the sprite records are written over those first 32 bytes. Sprite clipping still needs the rest of each wall record, its extent and scale, and that is beyond byte 32. A comment in the structure marks the block that must stay big enough. The sorted lists of planes and of sprites share a buffer the same way.

The method: list which phase uses each field, and let data whose phases do not overlap share memory. It needs a comment at the structure, because a later change that reads one of the overwritten fields after the switch breaks silently.

Aerobiz Supersonic does the same on the 68000. The buffer at `$FF1804` that receives decompressed graphics is also where the game builds its save data [AB-DISASM, analysis/RAM_MAP.md].

## A cache of decoded sprites

After Burner Complete stores its sprites compressed in the cartridge, decodes each shape the first time it is needed, and scales it from the decoded copy every frame after that [AB32X, SH-2 code at `0x060065BC`-`0x0600676C`]:

- **Descriptors.** A ring of 128 entries of 8 bytes: shape number, decoded size, offset in the buffer, and a lap number.
- **Lookup** walks back from the newest entry to the oldest, comparing shape numbers. A hit gives the offset. The bits of the shape number that choose mirroring and scaling mode are cleared first, so every mode of a shape shares one decoded copy.
- **A miss** decodes the shape ([Decoded once, into a cache](compression.md#decoded-once-into-a-cache-after-burner-complete)) into the 135 KB buffer, straight after the newest entry. Entries are dropped from the oldest end for as long as they overlap the space the new shape needs. If the descriptor ring is full, the oldest entry goes too.
- **Wrapping.** When the shape would run past the end of the buffer, it goes at the start. Leftovers from the previous lap may still sit at the end of the buffer, beyond the newest entries, and would never be reached by the overlap check, so the cache keeps a lap number in each entry and drops everything older than the current lap first.
- **No fragmentation.** The buffer is filled strictly in order, like a queue, so there are never holes to search for. The price is that the oldest shape is dropped even if it is still on screen; it is decoded again when next needed.
- **Some images skip the cache.** Shapes numbered `$7Fxx` come from 32 images of 928 bytes kept uncompressed in the program, 29 KB in all, with their own drawing path.

In a profile of 2,000 frames of play, the cache's lookup and decoding take about 2% of the Master's time <span class="tag emulator">emulator</span> [AB32X, PC profile in PicoDrive]. The scaler, reading the decoded copies, takes about 45%.

## Caches with a lifetime in frames

d32xr's texture cache keeps SDRAM copies of the wall textures and floor textures in view, which are faster to draw from than the cartridge [D32XR, r_cache.c, r_main.c, r_phase9.c]:

- **Its size is whatever is left.** After a level loads, the cache takes the largest free block of the zone, less 8 KB (16 KB on maps with a boss that spawns monsters) left free for allocations during play.
- **Each entry has a lifetime of 3 frames.** Every frame, each texture drawn resets its entry's count to 3, and then every entry's count goes down by one. An entry not drawn for 3 frames reaches 0.
- **When there is no room**, entries at 0 are freed, along with those not used this frame that are smaller than the new texture. If that does not free enough space in one piece, the texture is simply not cached this frame. The game draws it from the cartridge as before.
- **One new texture a frame** at most, in the default build. The cost of filling the cache is spread out.
- **The pointer is swapped.** Adding an entry points the texture's data pointer at the copy and keeps the old cartridge pointer; dropping it puts the old pointer back. The drawing code never knows whether it is reading a copy. The 4 bytes in front of each copy point back to its entry, so a texture pointer leads to its entry with no search.

Nothing depends on the cache: a texture that is not in it is drawn correctly, only more slowly. That is what makes it safe to fill it from whatever memory is left over.

## What to take away

- Write down the SDRAM map, including the stacks, and keep the stacks' worst case measured.
- Leave read-only data in the cartridge if it is read rarely and in order; copy or cache what is read often.
- The hidden frame buffer is spare memory for setup and per-frame scratch, if you can live with slow reads and dropped zero bytes.
- Allocate per level, with lifetimes, and free in bulk. Pool objects that come and go, and do not reuse a freed object until nothing can still hold it.
- Shrink structures: 16-bit pointers, fields recomputed instead of stored, rare fields moved to side tables, and memory shared between phases that never overlap.
- Cache decoded data with a policy that cannot fragment (a ring) or a lifetime in frames, and make every miss harmless.

## Open questions

- How deep do the stacks of these games actually go? After Burner Complete leaves 1.5 KB between its two stack tops, and Mortal Kombat II 4 KB.
- How often does After Burner Complete's cache miss in play, and how does that change with the ring's size?
- How much faster is a cached texture on a console, and is the cartridge read or the cache refill the larger cost?

## Sources

- [AB32X](../appendices/bibliography.md#ab32x): user header; SH-2 code at `0x06000200`, `0x06002120`, `0x060064CC`-`0x0600676C`; PC profile in PicoDrive
- [MK2](../appendices/bibliography.md#mk2): SH-2 program; notes/games/mk2/ANALYSIS.md
- [D32XR](../appendices/bibliography.md#d32xr): z_zone.c, doomdef.h, r_local.h, r_main.c, r_cache.c, r_phase1.c, r_phase2.c, r_phase9.c, p_setup.c, p_mobj.c, p_maputl.c, p_base.c, w_wad.c, marsnew.c, d_main.c, crt0.s, mars-ssf.ld
- [AU-NOTES](../appendices/bibliography.md#au-notes): ROADMAP.md U-046
- [AB-DISASM](../appendices/bibliography.md#ab-disasm): analysis/RAM_MAP.md
