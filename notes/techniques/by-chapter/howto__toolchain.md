# Harvested techniques: howto/toolchain.md

Target: `howto/toolchain.md`. 10 entries. Raw reports and source caveats: [../raw/](../raw/) (paths relative to by-chapter/).

Evidence and licence notes are per entry. Describe in the book's own words; never copy code.

<!-- from S32X-SKILL -->
### GCC 12.1 trap: 12-byte struct returns
- Source: S32X-SKILL, references/toolchain-and-build.md:173-181
- What it does and why it is clever: Returning a 3-word struct by value can be corrupted. Return through an out-pointer instead (note r3d's `to_camera` returns a 12-byte `vec3`).
- Key numbers: 12 bytes.
- Target chapter: howto/toolchain.md
- Evidence: beachy-beachy-ball-32x.

<!-- from S32X-SKILL -->
### GCC 12.1 trap: 64-bit multiply chains
- Source: S32X-SKILL, references/toolchain-and-build.md:182-185
- What it does and why it is clever: Chains of `long long` multiplies can miscompile. Use the SH-2 `dmuls.l` / MAC through tiny inline-asm macros for fixed-point multiplies.
- Key numbers: —
- Target chapter: howto/toolchain.md
- Evidence: beachy-beachy-ball-32x.

<!-- from S32X-SKILL -->
### GCC 12.1 trap: dropped stores
- Source: S32X-SKILL, references/toolchain-and-build.md:186-188
- What it does and why it is clever: The optimiser can wrongly decide a store is dead. If a value doesn't stick, make the target `volatile` or route the write through an opaque pointer.
- Key numbers: —
- Target chapter: howto/toolchain.md
- Evidence: beachy-beachy-ball-32x.

<!-- from S32X-SKILL -->
### GCC 12.1 trap: calls across mixed -O levels
- Source: S32X-SKILL, references/toolchain-and-build.md:189-198
- What it does and why it is clever: Build everything at one level (`-O2`). If a routine only breaks at `-O3` or with LTO, drop that routine to `-O2` before suspecting your own logic.
- Key numbers: —
- Target chapter: howto/toolchain.md
- Evidence: beachy-beachy-ball-32x.

<!-- from S32X-SKILL -->
### `--gc-sections` can strip the whole game; guard with live markers
- Source: S32X-SKILL, references/toolchain-and-build.md:64-68; references/testing.md:88-96, 152-157; assets/verify_rom.py:89-100
- What it does and why it is clever: If entry points are unreachable, the linker keeps only the header and the ROM boots black. verify_rom checks marker strings from different translation units, `.text` ≥ 64 KiB and at least 2048 non-zero bytes. Markers must be string literals passed to a call, or `volatile`, because a `const char[]` read only as `arr[0]` gets constant-folded away.
- Key numbers: `--min-text` = 0x10000.
- Target chapter: howto/toolchain.md
- Evidence: Static check in build.

<!-- from S32X-SKILL -->
### `.sdata @progbits` vector-copy invariant
- Source: S32X-SKILL, references/toolchain-and-build.md:210-234
- What it does and why it is clever: GAS can emit `.sdata` as non-loadable, so `objcopy -O binary` writes padding where the SH-2 vectors belong and the boot ROM copies zeros. Fix: `.section .sdata,"aw",@progbits`, and verify the reset vectors are present in the raw ROM payload, not just the ELF.
- Key numbers: —
- Target chapter: howto/toolchain.md
- Evidence: tyrian-32x.

<!-- from S32X-SKILL -->
### Linker map with split stacks and a BSS guard
- Source: S32X-SKILL, assets/mars.ld:1-87; references/toolchain-and-build.md:93-111; assets/verify_rom.py:25-28, 116-118
- What it does and why it is clever: `.text/.rodata` at 0x02000000 with LMA 0. `.data` is addressed at 0x06000000 but loaded after `.text`. Then `.bss`, with the heap above it. With one CPU the stack top is 0x0603FC00. Using the slave, master = 0x0603F800 and slave = 0x06040000. The check asserts `__bss_end < 0x0603C000`.
- Key numbers: RAM length 0x3FC00 (or 0x3F800 with the slave).
- Target chapter: howto/toolchain.md
- Evidence: d32xr CI assertion.

<!-- from S32X-SKILL -->
### Embedding the 68000 program in the SH-2 ROM
- Source: S32X-SKILL, references/toolchain-and-build.md:78-91; assets/Makefile:67-79
- What it does and why it is clever: Build a tiny m68k ELF, `objcopy -O binary`, and `.incbin` it in `mars_start.s`.
- Key numbers: —
- Target chapter: howto/toolchain.md
- Evidence: Template.

<!-- from S32X-SKILL -->
### Start from a known-good tree
- Source: S32X-SKILL, references/testing.md:182-196; references/porting-workflow.md:279-286
- What it does and why it is clever: A fresh scaffold produced different SH-2 vectors and code from byte-identical sources. Instead of debugging it, `cp -r` a booting tree and swap code in file by file, or start from an MIT boot foundation (hexgl-32x).
- Key numbers: —
- Target chapter: howto/toolchain.md
- Evidence: zepton32x.

<!-- from S32X-SKILL -->
### Workspace hygiene: neutral directory names and setup.sh
- Source: S32X-SKILL, references/toolchain-and-build.md:200-208, 147-171
- What it does and why it is clever: Some sandboxes discard `dist/` and `build/` between sessions, so write output to `rom/` and `obj/`. An idempotent `setup.sh` reinstalls the toolchain and PicoDrive; distro `gcc-sh-elf` packages work as a fallback. CI caches `/opt/toolchains`.
- Key numbers: —
- Target chapter: howto/toolchain.md
- Evidence: trial-of-the-sorcerer, God of Thunder.

---

