# Pipeline and cycle counting

The SH-2 finishes most instructions in one clock, but only when nothing gets in the way. This chapter covers what does get in the way: slow fetches, data accesses that collide with fetches, loads whose result is used too soon, the multiplier, and branches. It then counts a real inner loop, lists patterns from shipped code, and says what emulators show. The rules here are Hitachi's. No emulator we use applies them, not even the one build that models the cache (see [In emulators](#in-emulators)). Nothing in this chapter has been timed on a console, and [a test program](#a-console-test) is ready for anyone who can.

## Five stages

Each instruction passes through up to five stages [SH-PM §7.1 p.168]:

| Stage | Job | Clocks |
|-------|-----|--------|
| IF | Fetch the instruction | However long the fetch takes |
| ID | Decode it | 1 |
| EX | Do the arithmetic, or work out an address | 1 |
| MA | Read or write data memory | However long the access takes |
| WB | Put loaded data into the register | 1 |

Every instruction has IF, ID and EX. Loads also have MA and WB, stores have MA only, and register-to-register instructions have neither. A new instruction enters every clock, so five can be in flight at once.

Hitachi counts time in **slots**. A slot is one step of the pipeline, and it lasts as long as the slowest stage in it: a slot holding a 12-clock fetch is 12 clocks long, and every instruction in it waits [SH-PM §7.2.3 p.170]. An instruction's cost is the time from the start of its EX to the start of the next instruction's EX [SH-PM §7.3 p.171]. So "one clock per instruction" really means every stage takes one clock and no two instructions want the same thing.

## Where the clocks go

### Fetching

A fetch from the cache, or from the 2 KB on-chip RAM of [two-way mode](cache.md#two-way-mode-2-kb-of-on-chip-ram), reads a longword: two instructions. If the first of the pair sits at an address that is a multiple of 4, the second needs no fetch of its own. Hitachi writes such a free fetch in lower case, `if`. A branch to an address of the form 4*n* + 2 fetches only the one instruction there, and the next fetch reads a full pair again [SH-PM §7.4.2 p.173].

A fetch that misses the cache stalls the whole pipeline while the line fills: 12 clocks from SDRAM, 64 to 136 from cartridge ROM (see [Bus controller and memory timing](bsc.md#what-a-16-bit-bus-costs)). Every other rule in this chapter is worth a clock or two. A missed line costs ten times that, so code that runs often must stay in the cache.

### When a data access meets a fetch

IF and MA both use memory, and they cannot both use it at once. If an instruction's MA falls in the same slot as a real fetch (an `IF`, not an `if`), the slot splits. The data access goes first, then the fetch, and the slot costs the sum of the two. With both in the cache that is 2 clocks instead of 1 [SH-PM §7.4.1 p.172].

A free `if` does not split the slot [SH-PM §7.4.3 p.174]. The MA of the instruction at position *k* lines up with the fetch of instruction *k* + 3, which gives a simple rule for code that runs from the cache <span class="tag manual">manual</span>:

- **A load or store at an address that is a multiple of 4 costs nothing extra.** Its MA meets the free `if` of an instruction at 4*n* + 2.
- **A load or store at 4*n* + 2 costs one extra clock.** Its MA meets a real `IF`.

Here is the rule for two loads in a row, the first at 4*n*, then three instructions without a memory access. Columns are slots; the fifth slot splits into two clocks, the load's MA first and then everything else [SH-PM Figure 7.8 p.175]:

```text
slot                     1    2    3    4    5a   5b   6    7
4n     load              IF   ID   EX   MA   WB
4n+2   load                   if   ID   EX   MA   WB
4n+4   add                         IF   ID   --   EX
4n+6   add                              if   --   ID   EX
4n+8   add                                   --   IF   ID   EX
```

The first load's MA (slot 4) meets the `if` of the instruction at 4*n* + 6, which fetches nothing, so slot 4 takes one clock. The second load's MA (slot 5) meets the `IF` at 4*n* + 8, which fetches the next pair, so slot 5 takes two. Five instructions cost six clocks. Put one of the `add`s between the two loads and both loads sit at multiples of 4: both MAs meet an `if`, and the five instructions cost five clocks.

Hitachi states these rules for on-chip memory and the on-chip cache alike, so they apply to code and data that both hit the cache [SH-PM §7.4.2-7.4.3 pp.173-175]. The SH7604 manual has no section of its own on this. It does say that the CPU reaches the cache over a single cache bus, and that the cache answers one read per cycle [SH7604 §7.11.2, §8.4.1], which leaves no room for a fetch and a data access in the same cycle. That fits the programming manual's rule; neither manual gives a timing measured on the SH7604 itself.

Hitachi's own advice is to put instructions with a memory access on longword boundaries wherever possible [SH-PM §7.6 p.176].

### Using a load's result too soon

A load writes its register in WB, at the very end. If the next instruction reads that register, the slot holding the load's MA and that instruction's EX splits, which costs one clock from the cache [SH-PM §7.5 pp.175-176]. One unrelated instruction in between removes the wait. Hitachi names two cases that do not wait: when the next instruction is another load into the same register, and when it is a `MAC.W` or `MAC.L` that uses the loaded register as one of its two address registers (`@Rm+` or `@Rn+`). The same rule applies to `STS MACH`/`MACL` into a register, to `LDS.L @Rm+,PR` and to `LDC.L` [SH-PM Table 7.2 pp.182-183].

The wait is about the loaded register only. Hitachi lists none for the address register of a post-increment load (`@Rm+`).

### Data accesses outside the cache

A data access is as slow as the memory behind it. A load from a cache-through address waits for the whole bus cycle, plus one extra clock while the chip works out where the access goes [SH7604 §7.11.2]. Stores are cheaper. The bus controller holds one pending write, so the CPU moves on as soon as the write is handed over. Only the next access that needs the bus waits for it to finish. A cache hit does not need the bus. So a store to the frame buffer, followed by several instructions that only touch the cache, costs about a clock [SH7604 §7.11.2]. See the write buffer in [Bus controller and memory timing](bsc.md#sdram-built-for-cache-fills).

## What each instruction costs

Hitachi's table of costs with nothing in the way [SH-PM Table 7.2 pp.177-183; Appendix B p.289] <span class="tag manual">manual</span>:

| Instructions | Clocks |
|--------------|--------|
| Register moves, arithmetic (including `DT`, `DIV1`, `DIV0S`), logic, shifts, `NOP`, `LDC`/`STC`/`LDS`/`STS` to and from registers | 1 |
| Loads and stores (`MOV` with memory), `LDS.L`/`STS.L` of PR, MACH or MACL | 1, plus memory time |
| `BT`, `BF` | 3 if taken, 1 if not |
| `BT/S`, `BF/S` | 2 if taken, 1 if not |
| `BRA`, `BSR`, `BRAF`, `BSRF`, `JMP`, `JSR`, `RTS` | 2 |
| `MULS.W`, `MULU.W` | 1 to 3 |
| `DMULS.L`, `DMULU.L`, `MUL.L` | 2 to 4 |
| `MAC.W` | 3 (2 next to other multiplier instructions) <span class="tag disputed">disputed</span> ([discrepancy 47](../appendices/discrepancies.md)) |
| `MAC.L` | 3 (2 to 4 next to other multiplier instructions) <span class="tag disputed">disputed</span> |
| `STC.L` to memory | 2 |
| `LDC.L` from memory | 3 |
| `AND.B`, `OR.B`, `TST.B`, `XOR.B` `#imm,@(R0,GBR)` | 3 |
| `TAS.B` | 4 |
| `RTE` | 4 |
| `TRAPA` | 8 |
| `SLEEP` | 3 |

The ranges in the multiply rows depend on the instructions around them (see [below](#the-multiplier)). Count multiplies from Hitachi's pipeline figures, which this table summarises. For `MAC.W` and `MAC.L` the two disagree: the figures hold the next instruction back one slot, as they do after `DMULS.L`, which makes 2 clocks with nothing else in the way, while the table says 3 ([discrepancy 47](../appendices/discrepancies.md)).

### Branches

- **A taken `BT` or `BF` throws away the two instructions already fetched behind it** and starts fetching at the target. Hence 3 clocks [SH-PM §7.7.5 pp.239-240].
- **`BT/S` and `BF/S` run the instruction after them** (the [delay slot](isa.md#delayed-branches)) before the branch takes effect. Only one fetched instruction is wasted, so a taken branch costs 2 clocks, and the delay slot instruction does useful work [SH-PM §7.7.5 pp.240-241].
- **Unconditional branches, calls and returns cost 2,** plus whatever is in the delay slot. A `BSR` and `RTS` with useful work in both delay slots cost 4 clocks more than inline code [SH-PM §7.7.5 pp.241-242]. A `JSR`, which a call needs when its target is beyond `BSR`'s reach of about 4 KB, also needs the target address in a register: usually one more instruction, a `MOV.L` from a literal pool, with a data access that costs a clock more if it meets a real fetch ([Addressing modes](isa.md#addressing-modes)). That makes 5 or 6 clocks unless the address can stay in a register across calls.

So a loop should end in `DT` and `BF/S`, with useful work in the delay slot: 3 clocks of loop overhead, and the delay slot instruction is not wasted. The SH-2 has no branch prediction. A taken branch always costs the same.

## The multiplier

Multiplies run in a separate unit that keeps working after the instruction has left the pipeline. Hitachi marks those extra clocks `mm`. Each instruction that uses the multiplier reaches it in one particular MA stage [SH-PM §7.7.2 pp.196, 204, 222, 229-230; Table 7.2 p.183]:

| Instruction | Reaches the multiplier in | `mm` clocks after that | Next instruction held back |
|-------------|---------------------------|------------------------|----------------------------|
| `MULS.W`, `MULU.W` | Its MA, 1 clock after its EX | 2 | No |
| `DMULS.L`, `DMULU.L`, `MUL.L` | Its second MA, 2 clocks after its EX | 4 | One slot |
| `MAC.W` | Its second MA, 2 clocks after its EX | 2 | One slot |
| `MAC.L` | Its second MA, 2 clocks after its EX | 4 | One slot |
| `STS` or `STS.L` from MACH or MACL, `LDS` or `LDS.L` to them, `CLRMAC` | Its MA, 1 clock after its EX | None | No |

Instructions that do not touch the multiplier carry on while it works. One that does touch it can still start early: **its multiplier MA may fall in the last `mm` clock of the instruction before.** If it would fall earlier, it stretches until that last `mm` clock, and everything behind it waits as long. Hitachi draws both cases for `MULS.W` <span class="tag manual">manual</span> [SH-PM Figure 7.56 p.224]:

```text
clock        1    2    3    4    5    6    7    8
MULS.W       IF   ID   EX   MA   mm   mm
MULS.W            IF   ID   EX   M---------A    mm   mm
next                   IF   ID   EX   --   MA

MULS.W       IF   ID   EX   MA   mm   mm
other             IF   ID   EX
MULS.W                 IF   ID   EX   MA   mm   mm
```

Back to back, the second `MULS.W` would reach the multiplier in clock 5, so its MA stretches over clocks 5 and 6 and the pipeline loses one clock. With one unrelated instruction between them, its MA falls in clock 6, the first one's last `mm`, and nothing waits.

The same counting gives every case. After a `DMULS.L` at EX clock *t*, the next instruction is held to *t* + 2 and the `mm` clocks run from *t* + 3 to *t* + 6. A following `DMULS.L` reaches the multiplier two clocks after its own EX, so it needs its EX at *t* + 4 or later: two instructions between. A `MULS.W` reaches it one clock after its EX, so it needs its EX at *t* + 5: three instructions between. Hitachi gives these spacings in words for every pair of multiplies [SH-PM pp.197-199, 205-209, 223-225, 230-233]; the `STS` and `LDS` rows follow from the same rule and the figures for those instructions:

| First | Then | Clocks lost if adjacent | Unrelated instructions between for no loss |
|-------|------|-------------------------|---------------------------------------------|
| `MULS.W` or `MAC.W` | `MULS.W`, `STS`, `LDS` | 1 | 1 |
| `MULS.W` or `MAC.W` | `DMULS.L`, `MAC.W`, `MAC.L` | 0 | 0 |
| `DMULS.L` or `MAC.L` | `DMULS.L`, `MAC.W`, `MAC.L` | 2 | 2 |
| `DMULS.L` or `MAC.L` | `MULS.W`, `STS`, `LDS` | 3 | 3 |

The clocks lost come on top of the one-slot hold after a `DMULS.L` or a `MAC`. So back-to-back `MAC.W`s do not collide, and a `MULS.W` right after a `DMULS.L` holds the pipeline three clocks. The rule is the same as for the [division unit](divu.md#timing): start the multiply, do other work, and read the result last. Hitachi's own guidance is to keep multiplier instructions apart, and to keep a multiply apart from the `STS` that reads its result [SH-PM §7.6 p.176].

Use `MULS.W` or `MULU.W` when both numbers fit in 16 bits. The result is the same 32-bit product, and the multiplier is busy half as long as with `MUL.L` or `DMULS.L`.

**d32xr** uses both ideas in its side-of-line tests [D32XR, r_local.h, p_maputl.c]. A point is on one side of a line if `dy_line × dx ≤ dy × dx_line`. The coordinates are whole map units, so each product is a 16 × 16 `MULS.W` rather than a 32-bit multiply. The code issues the first `MULS.W`, then works out `dy` (a subtraction and a shift) while it runs, then reads MACL and starts the second. The second product is read straight away, so only the first multiply's time is hidden, and the last `STS` loses a clock. Its floor-span setup puts two instructions between each of two `DMULS.L`s and the `STS` that reads it: two loads the first time, a `SWAP.W` and an `AND` the second [D32XR, sh2_draw.s]. By the table that is one short, so each `STS` still loses a clock. These run once per span, not once per pixel.

## Worked example: a texture column loop

d32xr's wall drawer, `I_DrawColumnA`, draws one vertical strip of a textured wall. For each pixel it loads a texel, looks it up in the light table, stores it to the frame buffer, and moves down one line. The inner loop does two pixels per pass in 16 instructions [D32XR, sh2_draw.s]:

| *k* | Instruction | What it does |
|-----|-------------|--------------|
| 0 | `mov.b @(r0,r5),r0` | Load texel |
| 1 | `add r3,r2` | Step the texture position |
| 2 | `mov.b @(r0,r7),r9` | Look up its colour for this light level |
| 3 | `swap.w r2,r0` | Integer part of the texture position |
| 4 | `mov.b r9,@r8` | Store pixel |
| 5 | `and r4,r0` | Wrap to the texture height |
| 6 | `add r1,r8` | Down one line (320 bytes) |
| 7 | `dt r6` | Count down |
| 8-13 | Same as 0-5 | Second pixel |
| 14 | `bf/s` to *k* = 0 | Loop |
| 15 | `add r1,r8` | Delay slot: down one line |

Counting it with the rules above, first with the code, the texels and the light table all in the cache:

- **16 instructions:** 16 clocks.
- **Taken `BF/S`:** 1 more.
- **Load-use waits: none.** Each load is followed by an unrelated instruction before its result is used: *k* = 1 after the texel load, *k* = 3 after the colour load.
- **Frame-buffer stores: about free.** The write buffer takes each one, and the next access that needs the bus is the next store, eight instructions later. The frame buffer takes 3 to 5 clocks per write.
- **Data accesses meeting fetches: 6 more.** The loop starts at an address of the form 4*n* + 2, so all six loads and stores, at even *k*, sit at 4*n* + 2, and each one splits a slot.

That gives 23 clocks per two pixels, 11.5 a pixel <span class="tag manual">manual</span>. Moved by 2 bytes, for example with one `nop` before the loop label that runs once, every memory instruction would land on a multiple of 4. The prediction is then 17 clocks per two pixels, 8.5 a pixel. The alignment saves 3 clocks a pixel, a quarter of the loop.

**Where the loop sits.** At commit `957d3a8` the file puts its code in the `.sdata` section with 16-byte alignment (`.align 4`), and the loop label `do_col_loop` is at offset `0x3A`, as assembled here with GNU as 2.47 [D32XR, sh2_draw.s]. A linker always places an input section on its own alignment, so the label's final address is 16*n* + 10 whatever else is linked. d32xr's linker script puts `.sdata` in the data section, which runs from SDRAM at `0x06000000` through the cache [D32XR, mars-ssf.ld]. The project's Makefile expects an older toolchain (GCC 4.6.2 libraries under `/opt/toolchains/sega`), but the offset does not depend on it: SH-2 instructions are all 2 bytes, the only padding before the label is a `.p2alignw 1`, which aligns to 2 bytes and so adds nothing, and the literal it loads is out of the way at the end of the file. We did not build the whole game; the offset and the section's alignment are what fix the address.

**Where the texels come from.** The count above assumes they are in the cache, and a column of wall reads a fresh run of them. d32xr keeps a texture cache in SDRAM. After each picture it copies into it at most one new texture per mip level, from the cartridge, expanding 4-bit textures to 8 bits on the way. An entry can be evicted once three pictures have passed without a wall using it [D32XR, r_phase9.c, r_cache.c, r_local.h]. A wall texture not copied yet is drawn straight from the cartridge: by a 4-bit drawer if the texture has a 4-bit form and no decals, otherwise by the 8-bit drawer, which is `I_DrawColumnA` for textures whose height is a power of two [D32XR, r_phase6.c, r_main.c, doomdef.h]. So `I_DrawColumnA` reads its texels from SDRAM or from the cartridge, through the cache either way. A texture column is a run of bytes, one per texel, so one column of wall touches at most the texture's height ÷ 16 cache lines of texels, one more if the run does not start on a line: 8 or 9 for a texture 128 texels high. Each line costs 12 clocks from SDRAM and 64 to 136 from the cartridge ([What a 16-bit bus costs](bsc.md#what-a-16-bit-bus-costs)). For a column 100 pixels tall that covers the whole texture, in clocks:

| | Loop at 4*n* + 2 | Loop at 4*n* | Saved |
|-|------------------|--------------|-------|
| Loop, everything in the cache | 1,150 | 850 | 300, 26% |
| Plus 8 texel lines from SDRAM | 1,246 | 946 | 300, 24% |
| Plus 8 texel lines from the cartridge | 1,662 to 2,238 | 1,362 to 1,938 | 300, 13% to 18% |

The 3 clocks a pixel do not depend on the misses; the share they make does. A frame at 23.01 MHz is about 384,000 clocks. A picture that drew 20,000 wall pixels would save 60,000 of them, about a sixth of a frame, whatever the texels cost. This is a prediction from Hitachi's rules alone. It has not been measured, and the emulators cannot show it (see below).

The non-power-of-two variant, `I_DrawColumnNPo2A`, wraps the texture position by comparing and subtracting instead of masking [D32XR, sh2_draw.s]. That costs a compare and a conditional subtract per pixel, but lets the wall textures have any height.

### Other patterns in real code

- **Group the loads, then the stores.** marsdev's `word_8byte_copy` loads four words into four registers, then stores all four [MARSDEV, examples/32x-skeleton/sh_src/mars_start.s]. No store needs a value loaded by the instruction just before it. Its comments mark three "wasted" clocks between the loads. By Hitachi's rules, a load followed by a load into a different register does not wait, so any time lost there comes from memory or from fetches meeting data accesses, not from load-use.
- **Store backwards.** The SH-2 can step a pointer down as part of a store (`@-Rn`) but has no store that steps it up, so a loop that writes from the end saves an `ADD` per store. d32xr's span drawer moves its texture position to the end of the span with one `DMULS.L` (step × count), then draws right to left with `mov.b r10,@-r8` [D32XR, sh2_draw.s].
- **Unroll by two and enter halfway for an odd count.** Both d32xr drawers halve the count with `SHLR`, which leaves the odd bit in T, and branch into the second half when it is set [D32XR, sh2_draw.s].
- **Unroll for the common case of a decoder.** Mortal Kombat II's sprite format packs a run length of 1 to 3 into each data byte, with 0 meaning "the length is in the next byte". Its blitter handles the short runs with a straight chain of up to three stores, each followed by `DT` and a `BT/S` out, and keeps a counted loop only for the long runs [MK2, SH-2 code at `0x060028C0`]. Most runs in a fighter sprite are short, so most bytes never enter a loop.
- **Unroll by eight and jump into the middle.** After Burner Complete's sprite scaler repeats its four-instruction step eight times. It enters the run with a computed `JMP` that skips just enough steps for the first pass to cover the remainder (width mod 8, or a full eight), so one loop handles any width with one counter test per eight words. Each step puts an independent `ADDC` between the load and the store that uses it, so the load result is ready in time [AB32X, SH-2 code at `0x060067B4`-`0x0600684C`]. The same game's run-length decoder enters its 8-store loop the same way for runs of zeros [AB32X, SH-2 code at `0x060066B6`].
- **Inline small, hot leaf functions.** The Virtua Racing Deluxe project inlined a 34-byte coordinate routine that the Slave calls four times for each polygon, about 3,200 times a picture. It is called from four places: one in a routine that could be moved on its own, and three in a 278-byte block that had to be moved whole, which [Reverse engineering](../howto/reverse-engineering.md#changing-it) describes. The project estimated the call and return at 6 clocks a call, about 19,200 clocks a picture, and counted that as 5% of the Slave's time against its own figure of about 383,000 clocks a frame (this book uses 384,000). Its notes then give the routine's share as about 12%, down from the 17% of an earlier profile. That 12% is the 17% less the estimate, not a new measurement: the change was checked with a 3,600-frame PicoDrive run that did not crash, and no later profile is recorded [VRD-NOTES, OPTIMIZATION_PLAN.md S-6, commit `6232c88`, analysis/optimization/COORD_TRANSFORM_INLINING_INFEASIBILITY.md]. By Hitachi's table a `BSR` and `RTS` cost 4 clocks when both delay slots do useful work and 6 when they hold `NOP`s, so the estimate is the most the change could save.

## In emulators

- **PicoDrive** charges each instruction a fixed number of clocks, close to Hitachi's figures with nothing in the way: 1 for most, 2 for unconditional branches and the 32-bit multiplies, 2 or 3 for taken conditional branches, 3 for `MAC` <span class="tag emulator">emulator</span> [PICODRIVE, cpu/sh2/mame/sh2.c, cpu/sh2/compiler.c]. Stock PicoDrive has no cache, no wait for a load's result, no slot splits and no multiplier waits.
- **Aerobiz Ultimate's build of PicoDrive** adds, when `VRD_SH2_TIMING=1` is set and only in its interpreter core, the SH-2 wait states of each memory region from the 32X hardware manual and a model of the cache that keeps tags but no data. A hit, fetch or data, costs nothing; a miss costs a line fill, 12 clocks from SDRAM. It keeps PicoDrive's fixed instruction costs, so it has no slot splits, load-use waits or multiplier waits either. It has no write buffer: every write is charged its full bus time. And it charges a cartridge line fill as four longword accesses, about 32 to 68 clocks, half this book's figure, because it leaves open whether a longword read from the 16-bit cartridge is one bus cycle or two <span class="tag emulator">emulator</span> [AU-NOTES, ROADMAP.md U-093; VRD-NOTES, third_party/picodrive pico/32x/vrd_timing.c at commit `dfe7c36`]. Its figures are the right tool for cache misses and slow memory, the large costs, and say nothing about the small ones in this chapter.
- **Ares** charges one clock for every instruction in its interpreter, whatever the instruction, plus the bus costs listed in [Bus controller and memory timing](bsc.md#emulators-do-not-show-this) and 12 clocks per cache line fill <span class="tag emulator">emulator</span> [ARES, component/processor/sh2/instruction.cpp, md/m32x/sh7604.cpp]. Branches, multiplies, load-use waits and slot splits all cost nothing extra.

So no emulator we use can show any gain from the scheduling in this chapter. A loop that loses a quarter of its time to alignment runs at the same speed in all three. The test program below shows it: in ares 148 with the interpreter, both alignments of the column loop take 23.93 clocks a pass (counts `$BF82` and `$BF83`). PicoDrive does not run the free-running timer, so there the counts read 0. Profiles from any of them rank functions well enough, but the cycle counts inside a function have to be worked out by hand, or measured on a console with a timer (see [Keeping time on the 32X](timers.md#keeping-time-on-the-32x)).

## A console test

`pipeline-test` is a small 32X program that answers the second open question below on any console. The Master runs the column loop of the worked example twice, once with its label at 16*n* + 10 (4*n* + 2, where d32xr's sits) and once at 16*n* + 12 (4*n*), 16,384 passes each, reading texels and colours from SDRAM through the cache and storing to the frame buffer. Its stores go two bytes apart rather than a line apart, to stay inside the frame buffer; the step is a register, so the timing is the same. It times each run with the free-running timer at the CPU clock ÷ 8, after a first run that fills the cache, and leaves the two counts in COMM8 and COMM10. The 68000 prints them. No interrupts are used. The loop is the same 16 instructions as d32xr's, written for this book:

```text
{{#include ../howto/pipeline-test/sh2.s:loop}}
```

The screen shows three rows. Row `A` is the loop at 4*n* + 2 and row `B` the loop at 4*n*. Each gives the predicted clocks per pass × 100 (2300 and 1700), the measured clocks per pass × 100, and the raw count in hex. Row `AB` gives the ratio A ÷ B × 1000: 1353 predicted, then measured. If Hitachi's rules hold, the measured row `B` is near 1700 and the ratio near 1353; if fetches and data accesses from the cache do not compete, the two rows match, as they do in ares. The frame buffer is in blank mode during the test, so writes to it may be faster than during display; at one store every eight or more clocks this should not matter.

Build it with the same tools as [Hello world on the 32X](../howto/32x-hello.md#building), from a 32X cartridge dump that supplies Sega's initial program:

```sh
src/howto/pipeline-test/build.sh RETAIL_32X_ROM OUT_DIR
```

The build script prints the address of every texel load, so a rebuild with another assembler can be checked; with GNU as 2.47 each loop's first is at `0x0600028A` and `0x060002EC`. Reports from a console, with its model, are welcome.

## Open questions

- Do Hitachi's rules predict real 32X timings for code running from the cache, from SDRAM through the cache-through address, and from cartridge ROM?
- Does d32xr's column loop, moved by 2 bytes, really save about 6 clocks per two pixels on a console? [The console test](#a-console-test) answers this: rows `A` and `B` near 2300 and 1700.
- Does a data access that hits the cache really split a slot with a fetch that hits it? The programming manual says so for the cache; the SH7604 manual only implies it. The same test settles it: if they do not compete, rows `A` and `B` match.
- Does `MAC.W` take 2 clocks or 3 with nothing else in the way ([discrepancy 47](../appendices/discrepancies.md))?
- How long does a store to the frame buffer hold the write buffer, and does a following cache miss wait for all of it?
- How often does d32xr's column drawer read texels from the cartridge rather than its SDRAM texture cache, in a typical level?

## Sources

- [SH-PM](../appendices/bibliography.md#sh-pm): §7.1-7.6 pp.168-176 (Figure 7.8 p.175), Table 7.2 pp.177-183 and its notes, §7.7.2 pp.196-237 (Figures 7.23-7.73), §7.7.5 pp.239-242, appendix B pp.288-289
- [SH7604](../appendices/bibliography.md#sh7604): §7.11.2 access from the CPU, buses, write buffer; §8.1, §8.4.1 cache organisation and reads
- [D32XR](../appendices/bibliography.md#d32xr): sh2_draw.s, mars-ssf.ld, Makefile, r_local.h, p_maputl.c, r_phase6.c, r_phase9.c, r_cache.c, r_main.c, doomdef.h, at commit `957d3a8`
- [MARSDEV](../appendices/bibliography.md#marsdev): examples/32x-skeleton/sh_src/mars_start.s
- [MK2](../appendices/bibliography.md#mk2): SH-2 code at `0x060028C0`
- [AB32X](../appendices/bibliography.md#ab32x): SH-2 code at `0x060066B6`, `0x060067B4`-`0x0600684C`
- [VRD-NOTES](../appendices/bibliography.md#vrd-notes): OPTIMIZATION_PLAN.md S-6, commit `6232c88`, analysis/optimization/COORD_TRANSFORM_INLINING_INFEASIBILITY.md, analysis/POLYGON_TRANSFORMATION_ANALYSIS.md; third_party/picodrive pico/32x/vrd_timing.c at commit `dfe7c36`
- [AU-NOTES](../appendices/bibliography.md#au-notes): ROADMAP.md U-093
- [PICODRIVE](../appendices/bibliography.md#picodrive): cpu/sh2/mame/sh2.c, cpu/sh2/compiler.c
- [ARES](../appendices/bibliography.md#ares): component/processor/sh2/instruction.cpp, md/m32x/sh7604.cpp
- This book's test program: `src/howto/pipeline-test/` (run in ares 148 and PicoDrive only)
