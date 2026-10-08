# Harvested techniques: Asset pipelines, data-driven engines and porting

Target: Part VI chapter in `src/techniques/` (or `src/howto/emulator-testing.md`). 16 entries. Raw reports and source caveats: [../raw/](../raw/) (paths relative to by-chapter/).

Evidence and licence notes are per entry. Describe in the book's own words; never copy code.

<!-- from S32X-SKILL -->
### Convert the cart, do not embed a PICO-8 interpreter
- Source: S32X-SKILL, references/pico8-porting.md:1-27
- What it does and why it is clever: Pull `__gfx__`, `__map__`, `__gff__`, `__sfx__` and Lua tables from the unmodified `.p8` with a build tool (`iconv -c` handles the non-UTF-8 sections). Emit C arrays and reimplement the logic in native C.
- Key numbers: gfx 128×128 at 1 byte per pixel, map 128×32-64, gff 256.
- Target chapter: NEW: PICO-8 compatibility layer
- Evidence: Five shipped PICO-8 ports.

<!-- from S32X-SKILL -->
### `pico8_api` shim: palette to CRAM, pal swaps, transparent 0
- Source: S32X-SKILL, references/pico8-porting.md:29-47
- What it does and why it is clever: Upload the fixed 16-colour PICO-8 palette to CRAM once. `pico_pal()` does palette remaps, `spr/sspr` blit from `gfx_data` with colour 0 transparent, and `print` uses a small bitmap font. Game code then reads almost like the Lua.
- Key numbers: 16 colours, RGB555.
- Target chapter: NEW: PICO-8 compatibility layer
- Evidence: apex-vector-60-32x and others.

<!-- from S32X-SKILL -->
### PICO-8 angle convention for atan2, sin and cos
- Source: S32X-SKILL, references/pico8-porting.md:42-46
- What it does and why it is clever: PICO-8 angles run 0..1 with 0 = right, 0.25 = up (dy < 0), 0.5 = left, 0.75 = down. Its `sin` is inverted to match screen-down y. Implement `pico_atan2(dx,dy)` and `pico_sin/cos` to match exactly, or everything spawns facing 180° wrong.
- Key numbers: —
- Target chapter: NEW: PICO-8 compatibility layer
- Evidence: Shipped ports.

<!-- from S32X-SKILL -->
### Resolution: native re-projection or logical doubling
- Source: S32X-SKILL, references/pico8-porting.md:49-58
- What it does and why it is clever: 3D and Mode-7 games re-project natively at 320×224. 2D games render a logical 160×112 surface and pixel-double it in `pico_present`. Doubling pairs well with 32-bit stores (two source pixels → one `aabb` word) and the line-table trick (two display lines pointing at one row).
- Key numbers: 160×112 → 320×224.
- Target chapter: NEW: PICO-8 compatibility layer
- Evidence: picohot-32x.

<!-- from S32X-SKILL -->
### Faithful down to silence
- Source: S32X-SKILL, references/pico8-porting.md:81-89
- What it does and why it is clever: If the cart ships sound data but never calls `sfx()` or `music()`, the port stays silent.
- Key numbers: —
- Target chapter: NEW: PICO-8 compatibility layer
- Evidence: hit8ox-32x.

---

<!-- from S32X-SKILL -->
### Build-time conversion to big-endian read-in-place ROM archives
- Source: S32X-SKILL, references/porting-workflow.md:83-97, 151-174
- What it does and why it is clever: Decompress, de-plane Mode-X/EGA planar art to chunky 8bpp, byte-swap 16/32-bit fields at pack time, and emit a header plus offset table. C code then reads structs straight from ROM with no runtime conversion. Regeneration sits behind a stamp file.
- Key numbers: —
- Target chapter: NEW: Asset pipelines and data-driven engines
- Evidence: God of Thunder, Hocus Pocus.

<!-- from S32X-SKILL -->
### Proprietary container decoding
- Source: S32X-SKILL, references/porting-workflow.md:325-345
- What it does and why it is clever: Implement the exact decompressor in the build tool (`DATA.WAR`: offset table plus a 4 KiB-window LZSS) and quantise everything into one 8-bit palette with index 0 transparent.
- Key numbers: 4 KiB LZSS window.
- Target chapter: NEW: Asset pipelines and data-driven engines
- Evidence: warcraft-32x, breakfree-32x.

<!-- from S32X-SKILL -->
### Global palette by median cut, then exact nearest mapping
- Source: S32X-SKILL, references/porting-workflow.md:400-403, 464-471
- What it does and why it is clever: Median-cut per asset group, merge into 256 entries, map every image to its nearest entry with index 0 transparent. Small games fit one palette; big ones need per-scene palettes decided up front.
- Key numbers: 256 entries. One game used about 364 source colours.
- Target chapter: NEW: Asset pipelines and data-driven engines
- Evidence: super-sonic-rpg-32x.

<!-- from S32X-SKILL -->
### Compile scripts to bytecode plus a tiny VM instead of porting the interpreter
- Source: S32X-SKILL, references/porting-workflow.md:369-393, 434-439
- What it does and why it is clever: A build-time LCF reader (BER chunk streams) compiles RM2K event pages into compact bytecode `{code, indent, params[], string}` + sentinel. A runtime VM implements only the opcodes the game uses (page conditions, touch/action triggers, parallel pages). Move routes are flattened at build time.
- Key numbers: About 250-line VM, versus a ~30 MB EasyRPG player.
- Target chapter: NEW: Asset pipelines and data-driven engines
- Evidence: super-sonic-rpg-32x, raintown (complete game).

<!-- from S32X-SKILL -->
### Autotile to a deduplicated atlas with one-byte passability
- Source: S32X-SKILL, references/porting-workflow.md:440-444
- What it does and why it is clever: Evaluate the RM2K autotile rules (A/B/C/D, 47/50 subtile tables) at build time, deduplicate the resulting 16×16 tiles, and bake passability, wall and above-hero flags into one byte per cell.
- Key numbers: 13,025 cells → 243 tiles (Raintown). 597 tiles (Pail).
- Target chapter: NEW: Asset pipelines and data-driven engines
- Evidence: Shipped RM2K ports.

<!-- from S32X-SKILL -->
### Original data tables verbatim plus a level-event interpreter
- Source: S32X-SKILL, references/porting-workflow.md:288-323
- What it does and why it is clever: Ship the original's enemy, weapon and port records unchanged in ROM, so behaviour is read from data. A `switch(type)` VM walks a sorted event stream as the scroll position passes each trigger. Unused opcodes are explicit commented no-ops. `level_pos` and `event_index` double as test telemetry.
- Key numbers: 851 enemy / 781 weapon / 43 port records. 1,009 events over positions 0-8,100. About 559 KB asset bank in 19 sections.
- Target chapter: NEW: Asset pipelines and data-driven engines
- Evidence: tyrian-32x, 7 PicoDrive scenarios to LEVEL COMPLETE.

<!-- from S32X-SKILL -->
### Tiled TMX to a sorted ROM event stream
- Source: S32X-SKILL, references/porting-workflow.md:257-265
- What it does and why it is clever: The CSV tile layer becomes the tilemap. Objects become `(trigger_row, column, type, difficulty, gang)` sorted by trigger then group, in a `const LevelEvent[]`.
- Key numbers: 299 mission events (Raptor).
- Target chapter: NEW: Asset pipelines and data-driven engines
- Evidence: raptor32x.

<!-- from S32X-SKILL -->
### Content audit before writing the runtime
- Source: S32X-SKILL, references/porting-workflow.md:407-427
- What it does and why it is clever: Parse every map and count commands, opcode coverage by the existing VM, and the hard systems still missing. The result is a bounded backlog and an early answer to whether the game fits.
- Key numbers: 176 maps, 2,159 events, 2,716 pages, 15,580 commands, 45 opcodes, 86.88% already covered.
- Target chapter: NEW: Asset pipelines and data-driven engines
- Evidence: franzen-32x.

<!-- from S32X-SKILL -->
### Resolve map-tree inheritance at build time
- Source: S32X-SKILL, references/porting-workflow.md:468-471
- What it does and why it is clever: Music, background, permissions and encounters inherited down the RM2K map tree are flattened into each map so the runtime never walks the tree. Maps go into a banked directory with lazy activation.
- Key numbers: —
- Target chapter: NEW: Asset pipelines and data-driven engines
- Evidence: franzen-32x.

<!-- from S32X-SKILL -->
### Ship derived data, not source assets (mocap bake)
- Source: S32X-SKILL, references/porting-workflow.md:216-235
- What it does and why it is clever: Bake mocap into keyframes offline and ship only the keyframes, documenting the bake pipeline. For proprietary data, ship the converter and let the user build the ROM locally.
- Key numbers: —
- Target chapter: NEW: Asset pipelines and data-driven engines
- Evidence: fighting-game-3D-32X, tyrian-32x.

---

<!-- from MK2 -->
### An asset directory between the initial program and the SH-2 code (Mortal Kombat II)
- Source: MK2, ROM `$808`-`$977`
- What it does and why it is clever: A table of 92 longword pointers sits at cartridge `$808`, right after Sega's initial program and before the SH-2 program at `$978`. Both CPUs can find it at a fixed place. The pointers are SH-2 cartridge addresses (`0x02xxxxxx`); some point at further tables that hold 68000 bank-window addresses (`$9xxxxx`), which the SH-2 converts by adding `0x01700000`. Most data is RNC-packed.
- Key numbers: 92 entries; 81 RNC files in the ROM.
- Target chapter: techniques/asset-pipelines.md
- Evidence: ROM
