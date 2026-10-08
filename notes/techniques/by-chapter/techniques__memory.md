# Harvested techniques: Memory management on a 256 KB machine

Target: Part VI chapter in `src/techniques/` (or `src/howto/emulator-testing.md`). 8 entries. Raw reports and source caveats: [../raw/](../raw/) (paths relative to by-chapter/).

Evidence and licence notes are per entry. Describe in the book's own words; never copy code.

<!-- from D32XR -->
### Zone allocator with rover and coalescing
- Source: D32XR, z_zone.c:33-341, doomdef.h:678-698 (licence: id limited-use)
- What it does and why it is clever: The heap is a doubly linked list of adjacent blocks (no gaps, never two free blocks side by side). Allocation is next-fit from a rover and splits off a tail only if more than 64 bytes would be left. Free merges with both neighbours. Links are 16-bit short pointers. The zone is a parameter, so the texture cache runs its own zone carved out of the main one. Helpers report largest free block and iterate blocks for cache ageing.
- Key numbers: MINFRAGMENT 64; 4-byte alignment; block header = size + tag + id + 2 short links.
- Target chapter: NEW: Memory management on a 256 KB machine
- Evidence: code only

<!-- from D32XR -->
### 16-bit short pointers
- Source: D32XR, doomdef.h:51-90 (licence: id limited-use)
- What it does and why it is clever: An SPTR is `(ptr - 0x06000000) >> 2` in a uint16. That covers all 256 KB of SDRAM for 4-byte-aligned objects. It is used for mobj list, sector and blockmap links and zone block links, halving those fields.
- Key numbers: 65536 x 4 = 256 KB reach.
- Target chapter: NEW: Memory management on a 256 KB machine
- Evidence: code only

<!-- from D32XR -->
### Packed map structures
- Source: D32XR, r_local.h:80-149, 131-135; p_setup.c:114-159, 624-660 (licence: id limited-use)
- What it does and why it is clever:
  - **seg_t.** 6 bytes: `linedef<<1 | side`, v1, v2. The offset field is dropped and recomputed with an integer square root.
  - **side_t.** Textures as uint8 indices; a 12-bit x offset with the top 4 bits of a 12-bit row offset tucked into the same int16, recovered with `<<4 >>4` sign extension.
  - **Small fields.** VINT is short on MARS; sector light and special are bytes.
  - **Tags.** Moved out of the structures into small hash tables.
- Key numbers: seg 6 bytes; side 8 bytes; node 16 bytes.
- Target chapter: NEW: Memory management on a 256 KB machine
- Evidence: code only

<!-- from D32XR -->
### viswall and vissprite sharing one array
- Source: D32XR, r_local.h:516-586, r_main.c:898-909 (licence: id limited-use)
- What it does and why it is clever: `vd->vissprites = vd->viswalls`. Sprite records are written over the leading "early prep" fields of each viswall (centerangle to ceilingnewheight), which are dead after phase 7. The fields sprite clipping still needs (start, stop, scales, actionbits, clipbounds, vertices) sit after them. The comment requires that section to be big enough for a vissprite_t.
- Key numbers: MAXVISSPRITES = MAXWALLCMDS = 165.
- Target chapter: NEW: Memory management on a 256 KB machine
- Evidence: code only

<!-- from D32XR -->
### Mobj pools, truncated static objects and limbo
- Source: D32XR, p_mobj.c:60-95, 250-290, 354-375; doomdef.h:254-313; p_base.c:290-322 (licence: id limited-use; p_base.c is MIT)
- What it does and why it is clever: Objects that never move or think (MF_STATIC) are allocated only up to `offsetof(mobj_t, angle)`, a prefix of the full struct. Level load pre-allocates both kinds in bulk, plus 40 spare for puffs and missiles. Removed mobjs go to a limbo list and are recycled only at the end of the tic, so pointers held during the tic stay valid.
- Key numbers: +40 pre-spawned mobjs.
- Target chapter: NEW: Memory management on a 256 KB machine
- Evidence: code only

<!-- from D32XR -->
### Hashed tag tables
- Source: D32XR, p_maputl.c:520-617, p_setup.c:287-303, 596-612 (licence: id limited-use)
- What it does and why it is clever: Line and sector tags live in open-addressed `(object, tag)` pair tables instead of a field on every line. The table is rounded up to a multiple of 16 and probing starts at row `(obj % 16)·(n/16)`. Iterating by tag is a linear scan with a resumable cursor.
- Key numbers: LINETAGS_HASH_SIZE 16.
- Target chapter: NEW: Memory management on a 256 KB machine
- Evidence: code only

---

<!-- from MK2 -->
### SDRAM map of a 2D game (Mortal Kombat II)
- Source: MK2, SH-2 program; notes/games/mk2/ANALYSIS.md
- What it does and why it is clever: Program `0x06000000`-`0x06007E13` (32,276 bytes, of which about 13 KB is code and the rest palettes and tables); palette copy `0x0600A000`; Slave variables `0x0600A200`-`0x0600A22B`; Master variables and the 68000's state block from `0x0600A22C` (block at `0x0600A248`, 668 bytes); unpacked graphics at `0x06017170` and `0x06028530`; fonts at `0x06036B2C`-; stacks from the top (Master `0x06040000`, Slave `0x0603F000`). Graphics are unpacked per screen, not kept.
- Key numbers: as above.
- Target chapter: techniques/memory.md
- Evidence: ROM

<!-- from AB32X -->
### Decoded-sprite cache with ring allocation (After Burner Complete)
- Source: AB32X, SH-2 code at `0x060065BC`-`0x0600676C`
- What it does and why it is clever: Sprites are stored RLE-compressed in ROM. A 128-entry descriptor ring (shape, size, 24-bit offset, age) at `0x0601BA00` maps a shape to its decoded copy in an SDRAM ring buffer at `0x0601BE00`. A miss decodes into the next space and evicts descriptors whose range it overlaps. 16 frequently used images are pinned in SDRAM and bypass the cache (shape `$7Fxx`).
- Key numbers: 128 descriptors of 8 bytes; pinned images `$3A0` bytes each.
- Target chapter: techniques/memory
- Evidence: ROM
