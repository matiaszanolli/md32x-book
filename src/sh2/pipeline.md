# Pipeline and cycle counting

The SH-2 finishes most instructions in one clock, but only when nothing gets in the way. This chapter covers what does get in the way: slow fetches, data accesses that collide with fetches, loads whose result is used too soon, the multiplier, and branches. It ends with a count of a real inner loop. The rules here are Hitachi's. Neither emulator we use models them, and nothing in this chapter has been timed on a console.

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

Hitachi's own advice is to put instructions with a memory access on longword boundaries wherever possible [SH-PM §7.6 p.176].

### Using a load's result too soon

A load writes its register in WB, at the very end. If the next instruction reads that register, it waits one slot, which costs one clock from the cache [SH-PM §7.5 pp.175-176]. One unrelated instruction in between removes the wait. Two cases do not wait: when the next instruction is another load into the same register, and when it is a `MAC` that reads through the same register. The same rule applies to `STS MACH`/`MACL` into a register, to `LDS.L @Rm+,PR` and to `LDC.L` [SH-PM Table 7.2 pp.182-183].

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
| `MAC.W` | 3 (2 next to other multiplier instructions) |
| `MAC.L` | 3 (2 to 4 next to other multiplier instructions) |
| `STC.L` to memory | 2 |
| `LDC.L` from memory | 3 |
| `AND.B`, `OR.B`, `TST.B`, `XOR.B` `#imm,@(R0,GBR)` | 3 |
| `TAS.B` | 4 |
| `RTE` | 4 |
| `TRAPA` | 8 |
| `SLEEP` | 3 |

The ranges in the multiply rows depend on what comes next (see [below](#the-multiplier)).

### Branches

- **A taken `BT` or `BF` throws away the two instructions already fetched behind it** and starts fetching at the target. Hence 3 clocks [SH-PM §7.7.5 pp.239-240].
- **`BT/S` and `BF/S` run the instruction after them** (the [delay slot](isa.md#delayed-branches)) before the branch takes effect. Only one fetched instruction is wasted, so a taken branch costs 2 clocks, and the delay slot instruction does useful work [SH-PM §7.7.5 pp.240-241].
- **Unconditional branches, calls and returns cost 2,** plus whatever is in the delay slot. A call and return with useful work in both delay slots costs 4 clocks more than inline code [SH-PM §7.7.5 pp.241-242].

So a loop should end in `DT` and `BF/S`, with useful work in the delay slot: 3 clocks of loop overhead, and the delay slot instruction is not wasted. The SH-2 has no branch prediction. A taken branch always costs the same.

## The multiplier

Multiplies run in a separate unit that keeps working after the instruction has left the pipeline. Hitachi marks those extra clocks `mm` [SH-PM §7.7.2]:

| Instruction | Multiplier busy after its last MA | Delays the next instruction by |
|-------------|-----------------------------------|--------------------------------|
| `MULS.W`, `MULU.W` | 2 clocks | Nothing |
| `DMULS.L`, `DMULU.L`, `MUL.L` | 4 clocks | 1 clock (its second MA) |
| `MAC.W` | 2 clocks | 1 clock |
| `MAC.L` | 4 clocks | 1 clock |

Sources: [SH-PM §7.7.2 pp.196, 204, 222, 229].

While the multiplier is busy, any instruction that needs it waits until it is free. That covers another multiply, `STS` of MACH or MACL (reading the result), and `LDS` or `CLRMAC` (writing MACH or MACL). Instructions that do not touch the multiplier carry on. So the rule is the same as for the [division unit](divu.md#timing): start the multiply, do other work, and read the result last. Hitachi's own guidance is to keep multiplier instructions apart, and to keep a multiply apart from the `STS` that reads its result [SH-PM §7.6 p.176].

How much space is enough, from Hitachi's figures <span class="tag manual">manual</span>:

- **`MULS.W` then `MULS.W`**: one unrelated instruction in between, and the second does not wait [SH-PM p.224].
- **`DMULS.L` then `DMULS.L`, `MAC.W` or `MAC.L`**: two unrelated instructions [SH-PM pp.230-232].
- **`DMULS.L` then `MULS.W`**: three [SH-PM p.233].
- **`MAC.W` then `MAC.W`**: no wait. Back-to-back `MAC.W`s do not collide in the multiplier [SH-PM p.197].
- **Any multiply then `STS MACL`**: the `STS` waits until the multiplier is free, so give it the same spacing.

Use `MULS.W` or `MULU.W` when both numbers fit in 16 bits. The result is the same 32-bit product, and the multiplier is busy half as long as with `MUL.L` or `DMULS.L`.

**d32xr** uses both ideas in its side-of-line tests [D32XR, r_local.h, p_maputl.c]. A point is on one side of a line if `dy_line × dx ≤ dy × dx_line`. The coordinates are whole map units, so each product is a 16 × 16 `MULS.W` rather than a 32-bit multiply. The code issues the first `MULS.W`, then works out `dy` (a subtraction and a shift) while it runs, then reads MACL and starts the second. The second product is read straight away, so only the first multiply's time is hidden. Its floor-span setup does the same around two `DMULS.L`s, with two loads between each multiply and the `STS` that reads it [D32XR, sh2_draw.s].

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

Counting it with the rules above, assuming the code, the texture and the light table are all in the cache:

- **16 instructions:** 16 clocks.
- **Taken `BF/S`:** 1 more.
- **Load-use waits: none.** Each load is followed by an unrelated instruction before its result is used: *k* = 1 after the texel load, *k* = 3 after the colour load.
- **Frame-buffer stores: about free.** The write buffer takes each one, and the next access that needs the bus is the next store, eight instructions later. The frame buffer takes 3 to 5 clocks per write.
- **Data accesses meeting fetches: 6 more.** Assembled from d32xr's source, the loop starts at an address of the form 4*n* + 2 (its label is at offset `0x3A` in a 16-byte-aligned section, and the program runs from SDRAM through the cache). All six loads and stores are at even *k*, so they all sit at 4*n* + 2, and each one splits a slot.

That gives 23 clocks per two pixels, 11.5 a pixel <span class="tag manual">manual</span>. Moved by 2 bytes, for example with one `nop` before the loop label that runs once, every memory instruction would land on a multiple of 4. The prediction is then 17 clocks per two pixels, 8.5 a pixel, a quarter less. A frame at 23.01 MHz is about 384,000 clocks. A frame that drew 20,000 wall pixels would save 60,000 of them, about a sixth. This is a prediction from Hitachi's rules alone. It has not been measured, and the emulators cannot show it (see below).

The non-power-of-two variant, `I_DrawColumnNPo2A`, wraps the texture position by comparing and subtracting instead of masking [D32XR, sh2_draw.s]. That costs a compare and a conditional subtract per pixel, but lets the wall textures have any height.

### Other patterns in real code

- **Group the loads, then the stores.** marsdev's `word_8byte_copy` loads four words into four registers, then stores all four [MARSDEV, examples/32x-skeleton/sh_src/mars_start.s]. No store needs a value loaded by the instruction just before it. Its comments mark three "wasted" clocks between the loads. By Hitachi's rules, a load followed by a load into a different register does not wait, so any time lost there comes from memory or from fetches meeting data accesses, not from load-use.
- **Store backwards.** The SH-2 can step a pointer down as part of a store (`@-Rn`) but has no store that steps it up, so a loop that writes from the end saves an `ADD` per store. d32xr's span drawer moves its texture position to the end of the span with one `DMULS.L` (step × count), then draws right to left with `mov.b r10,@-r8` [D32XR, sh2_draw.s].
- **Unroll by two and enter halfway for an odd count.** Both d32xr drawers halve the count with `SHLR`, which leaves the odd bit in T, and branch into the second half when it is set [D32XR, sh2_draw.s].
- **Unroll for the common case of a decoder.** Mortal Kombat II's sprite format packs a run length of 1 to 3 into each data byte, with 0 meaning "the length is in the next byte". Its blitter handles the short runs with a straight chain of up to three stores, each followed by `DT` and a `BT/S` out, and keeps a counted loop only for the long runs [MK2, SH-2 code at `0x060028C0`]. Most runs in a fighter sprite are short, so most bytes never enter a loop.
- **Unroll by eight and jump into the middle.** After Burner Complete's sprite scaler repeats its four-instruction step eight times. It enters the run with a computed `JMP` that skips just enough steps for the first pass to cover the remainder (width mod 8, or a full eight), so one loop handles any width with one counter test per eight words. Each step puts an independent `ADDC` between the load and the store that uses it, so the load result is ready in time [AB32X, SH-2 code at `0x060067B4`-`0x0600684C`]. The same game's run-length decoder enters its 8-store loop the same way for runs of zeros [AB32X, SH-2 code at `0x060066B6`].
- **Inline small, hot leaf functions.** The Virtua Racing Deluxe project inlined a 34-byte coordinate routine that ran about 3,200 times a frame. It estimated the call and return at 6 clocks each time, about 19,200 clocks a frame or 5% of the Slave SH-2. Its PicoDrive profile then showed the routine's share fall from 17% to 12% <span class="tag emulator">emulator</span> [VRD-NOTES, OPTIMIZATION_PLAN.md, analysis/POLYGON_TRANSFORMATION_ANALYSIS.md]. By Hitachi's table the overhead is 4 clocks when both delay slots do useful work, and 6 when they hold `NOP`s.

## In emulators

- **PicoDrive** charges each instruction a fixed number of clocks, close to Hitachi's figures with nothing in the way: 1 for most, 2 for unconditional branches and the 32-bit multiplies, 2 or 3 for taken conditional branches, 3 for `MAC` <span class="tag emulator">emulator</span> [PICODRIVE, cpu/sh2/mame/sh2.c, cpu/sh2/compiler.c]. It has no cache, no wait for a load's result, no slot splits and no multiplier waits.
- **Ares** charges one clock for every instruction in its interpreter, whatever the instruction, plus the bus costs listed in [Bus controller and memory timing](bsc.md#emulators-do-not-show-this) and 12 clocks per cache line fill <span class="tag emulator">emulator</span> [ARES, component/processor/sh2/instruction.cpp, md/m32x/sh7604.cpp]. Branches, multiplies, load-use waits and slot splits all cost nothing extra.

So neither emulator can show any gain from the scheduling in this chapter. A loop that loses a quarter of its time to alignment runs at the same speed in both. Profiles from either emulator rank functions well enough, but the cycle counts inside a function have to be worked out by hand, or measured on a console with the watchdog timer as d32xr does (see [Keeping time on the 32X](timers.md#keeping-time-on-the-32x)).

## Open questions

- Do Hitachi's rules predict real 32X timings for code running from the cache, from SDRAM through the cache-through address, and from cartridge ROM?
- Does d32xr's column loop, moved by 2 bytes, really save about 6 clocks per two pixels on a console?
- How long does a store to the frame buffer hold the write buffer, and does a following cache miss wait for all of it?

## Sources

- [SH-PM](../appendices/bibliography.md#sh-pm): §7.1-7.6 pp.168-176, Table 7.2 pp.177-183, §7.7.2 pp.196-236, §7.7.5 pp.239-241, appendix B pp.288-289
- [SH7604](../appendices/bibliography.md#sh7604): §7.11.2 access from the CPU, write buffer
- [D32XR](../appendices/bibliography.md#d32xr): sh2_draw.s, r_local.h, p_maputl.c
- [MARSDEV](../appendices/bibliography.md#marsdev): examples/32x-skeleton/sh_src/mars_start.s
- [MK2](../appendices/bibliography.md#mk2): SH-2 code at `0x060028C0`
- [AB32X](../appendices/bibliography.md#ab32x): SH-2 code at `0x060066B6`, `0x060067B4`-`0x0600684C`
- [VRD-NOTES](../appendices/bibliography.md#vrd-notes): OPTIMIZATION_PLAN.md, analysis/POLYGON_TRANSFORMATION_ANALYSIS.md
- [PICODRIVE](../appendices/bibliography.md#picodrive): cpu/sh2/mame/sh2.c, cpu/sh2/compiler.c
- [ARES](../appendices/bibliography.md#ares): component/processor/sh2/instruction.cpp, md/m32x/sh7604.cpp
