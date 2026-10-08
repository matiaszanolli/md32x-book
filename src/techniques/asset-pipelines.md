# Asset pipelines and porting

A 32X has 256 KB of SDRAM and two 23 MHz CPUs. It should not parse PC file formats, convert colours, decode scripts or work out trigonometry at run time when a tool on a modern computer can do it once, at build time. This chapter is about that division of labour: what to convert before the ROM is built, the shapes data should take in the cartridge, and how ports from other machines move whole engines into the build. Its sources are the shipped ROMs, the Aerobiz Ultimate port's converters, and the homebrew practice collected in S32X-SKILL. The ports S32X-SKILL describes were checked in PicoDrive, so claims from it are tagged <span class="tag emulator">emulator</span>.

## Shape the data for its reader

The rule behind every section below: the cartridge should hold data in the form the code reads, at the address it reads it from.

| Do at build time | So that at run time |
|------------------|---------------------|
| Decompress the original's own containers, and recompress in a format chosen for the reader | One known decoder runs, at a known cost ([Choosing a format](compression.md#choosing-a-format)) |
| Swap byte order, align fields | Structures are read in place from ROM |
| Convert pixels to the 32X's layout and colours to its palette | Drawing is a copy |
| Precompute tables, matrices, glyph widths | The CPU does no trigonometry or measuring |
| Compile scripts to a small bytecode | A short interpreter runs only what the game uses |
| Resolve references, inheritance, defaults | The runtime never walks a tree |

## Read-in-place ROM archives

Data that is only read can stay in the cartridge and cost no SDRAM at all ([Leave it in the cartridge](memory.md#leave-it-in-the-cartridge)). For that, the cartridge copy must already be in the right form:

- **Byte order.** The 68000 and the SH-2 are both big-endian: the high byte of a word is at the lower address ([Data and addressing](../sh2/isa.md#data-and-addressing)). Data from a PC is little-endian. Swap every 16- and 32-bit field when packing, and the code can read structures straight from ROM. A test on a little-endian PC will not show a missed swap; the console will <span class="tag emulator">emulator</span> [S32X-SKILL, porting-workflow.md]. Koei's compressed format avoids the question differently: it stores its 16-bit bit-words low byte first and reads them one byte at a time, which needs neither a swap nor alignment ([Koei's LZSS](compression.md#koeis-lzss-aerobiz-supersonic)).
- **Alignment.** An SH-2 reads a word only at an even address and a longword only at a multiple of 4; anything else is an address error. Pad fields so every one starts on its own size.
- **A directory.** Put a header and a table of offsets at a fixed place, so code can find any asset by number without searching <span class="tag emulator">emulator</span> [S32X-SKILL, porting-workflow.md].

Mortal Kombat II does exactly this. A table of 92 longword pointers sits at cartridge `$808`, between Sega's initial program and the SH-2 program at `$978`, where both CPUs can find it. The pointers are SH-2 cartridge addresses (`0x02xxxxxx`). Some lead to further tables that hold the 68000's banked-window addresses (`$9xxxxx`), which the SH-2 converts by adding `0x01700000`. Most of the files they point at are RNC-packed [MK2, ROM `$808`-`$977`; SH-2 code at `0x060006D0`]. See [After the 32X is switched on](../32x/architecture.md#after-the-32x-is-switched-on-aden--1) for why that constant works, and [ProPack on the SH-2](compression.md#propack-on-the-sh-2-mortal-kombat-ii) for the format.

## Pixels and palettes

### Converting pixels

The 32X's packed-pixel mode is one byte per pixel, left to right. Art in any other layout should be converted before it reaches the ROM:

- **Planar art** from DOS games, in four bit planes, becomes one byte per pixel, so drawing it is a straight copy <span class="tag emulator">emulator</span> [S32X-SKILL, porting-workflow.md].
- **Mega Drive tiles** become a bitmap. Aerobiz Ultimate's world map tool unpacks the game's 704 map tiles from cartridge `$088CF8`, 22,528 bytes, checked byte for byte against VRAM. It notices that the map's name table is simply tiles 1 to 704 in order, so the map is a plain 256 × 176 bitmap, and writes out exactly what the SH-2 needs: a 256-word 32X palette followed by 320 × 224 bytes of pixels <span class="tag emulator">emulator</span> [AU-NOTES, tools/make_map_asset.py].

### Building a palette

One 256-entry palette serves the whole 32X layer at any one time ([Colours and the palette](../32x/vdp.md#colours-and-the-palette)):

- **Small games: one palette.** Reduce each group of assets by median cut, merge the results into 256 entries, then map every image to its nearest entry. One port fitted a whole game's 364 source colours this way <span class="tag emulator">emulator</span> [S32X-SKILL, porting-workflow.md].
- **Larger games: a palette per scene**, or groups of assets that share a range of entries, decided before the art is converted [S32X-SKILL, porting-workflow.md]. Aerobiz Ultimate fixes the ranges in a written budget ([One palette, many users](../32x/compositing.md#one-palette-many-users)).
- **Keep reserved entries out of the art.** Aerobiz Ultimate's title-art tool fits the picture to 320 × 224, reduces it by median cut to 253 colours, and places them at entries 1-253. Entry 0 is left out because a byte write of 0 to the frame buffer is skipped ([The normal and overwrite images](../32x/vdp.md#the-normal-and-overwrite-images)), and 254-255 belong to the text engine <span class="tag emulator">emulator</span> [AU-NOTES, tools/make_project_logo.py].
- **Convert colours with the target's rule.** A Mega Drive colour becomes a 32X colour by widening each channel ([Following the Mega Drive's palette](../32x/compositing.md#following-the-mega-drives-palette)).

### Take colours from the data, not from a screenshot

Aerobiz Ultimate's map palette was at first a constant copied from a running game. The colours never matched any table in the ROM, so the project concluded the palette was computed at run time. It was not: the copy had been taken during a fade, one step down on every channel (`$0864` had become `$0642`), and a search for those values could never succeed. The real palette was in the ROM at `$07677E` all along, the 16 words the game loads for that screen <span class="tag emulator">emulator</span> [AU-NOTES, tools/make_map_asset.py; HISTORY 2026-09-16]. A value captured from a running game is the value at that moment, not necessarily the value in the data.

## Precompute what the CPU would compute

- **Animation.** Aerobiz Ultimate's spinning SEGA logo needs a rotation and a scale for every frame. The build tool works out each frame's inverse matrix in 16.16 fixed point, and the box on screen it can touch, so the SH-2 does no trigonometry and no division. The tool also checks that drawing the last picture the way the SH-2 will lands on the Mega Drive's logo pixel for pixel <span class="tag emulator">emulator</span> [AU-NOTES, tools/make_sega_logo.py]. See [The SEGA logo](2d-effects.md#the-sega-logo-every-frame-worked-out-in-advance).
- **Fonts.** Aerobiz Ultimate's text engine uses a desktop font rendered by a tool into 1-bit glyphs, with each glyph's width and advance stored beside it, so the SH-2 measures text with table look-ups <span class="tag emulator">emulator</span> [AU-NOTES, tools/make_text_font.py]. The [Mega Drive hello world](../howto/md-hello.md#a-palette-and-a-font) keeps its font at 1 bit per pixel and expands it while loading.
- **Motion.** One homebrew 3D fighter bakes motion capture into keyframes offline and ships only the keyframes <span class="tag emulator">emulator</span> [S32X-SKILL, porting-workflow.md].

## Scripts and levels as data

Many games are mostly data run by a small engine. Porting the data and a small interpreter is often both more faithful and smaller than porting the logic by hand. The homebrew ports in S32X-SKILL show the range <span class="tag emulator">emulator</span> [S32X-SKILL, porting-workflow.md]:

- **Compile scripts, don't port the interpreter.** An RPG made with RPG Maker 2000 runs on a C++ player of about 30 MB. One port instead reads the game's own data files in a build tool, compiles each page of event commands into a compact bytecode, and runs it on an interpreter of about 250 lines of C that implements only the commands the game uses.
- **Keep the original's tables and run them.** A shoot-'em-up port carries the original's records unchanged (851 enemies, 781 weapon patterns, 43 weapon ports) and plays each level as a sorted stream of 1,009 events keyed to the scroll position. Behaviour is read from the records, so adding a weapon means adding data. Events the port does not reproduce are explicit, commented no-ops rather than guesses. The interpreter's position and event index double as test telemetry: a headless run can check that the whole stream ran.
- **Convert editor maps to event streams.** A map made in the Tiled editor becomes a tile array and a list of `(row, column, type, difficulty, group)` records sorted by the row that triggers them.
- **Evaluate tile rules once.** RPG Maker's autotiles are built from sub-tiles by rules. Applying the rules at build time and removing duplicates turned one game's 13,025 map cells into 243 unique 16 × 16 tiles, with passability and drawing flags packed into one byte per cell.
- **Flatten inheritance.** Settings inherited down a tree of maps (music, background, permissions) are copied into each map at build time, so the runtime never walks the tree.

## Porting from other platforms

### PICO-8

PICO-8 cartridges are a common source of 32X ports. The approach that works is to convert the cartridge, not to emulate PICO-8 <span class="tag emulator">emulator</span> [S32X-SKILL, pico8-porting.md]:

- **Extract the data sections** (sprite sheet, map, sprite flags, sounds) from the unmodified cartridge with a build tool, and rewrite the Lua logic in C.
- **Put PICO-8's runtime behind a small layer**: its 16-colour palette loaded once, palette swaps, sprite drawing with colour 0 transparent, a bitmap font, and the buttons. The game code then reads much like the Lua.
- **Match its angle convention.** PICO-8 angles run from 0 to 1, with 0.25 pointing up the screen and its sine flipped to match. A port that uses ordinary maths has everything face the wrong way.
- **Choose a resolution strategy.** 3D and road games re-project at 320 × 224. 2D games draw a 160 × 112 picture and double it, which suits two-pixel word writes and two display lines sharing one row of the line table ([Scaling the whole layer](2d-effects.md#scaling-the-whole-layer-the-line-table-does-the-vertical-half)).
- **Keep what the original does, including what it does not.** One cartridge carried sound data it never played; the port stays silent too.

### DOS and other computers

Decode the original's archive in the build tool, using its exact decompressor; for example, an offset table and an LZSS with a 4 KB window. Then convert planar art, swap byte order and reduce everything to one 8-bit palette with entry 0 transparent <span class="tag emulator">emulator</span> [S32X-SKILL, porting-workflow.md].

### The Mega Drive

A Mega Drive game is a special case: its code runs unchanged on the 32X's 68000, so most of a port is about addresses, not data. See [Case study: porting Aerobiz Supersonic](../patterns/case-study-aerobiz.md).

## Measure the content before writing the engine

Before building the runtime for a large data-driven game, parse all of it and count. One port of a 176-map RPG found 2,159 events, 2,716 pages and 15,580 commands using 45 distinct command types. It then measured that its existing interpreter already covered 86.88% of them, and listed the large systems still missing (battles, shops, saving). That report turned "port this game" into a bounded list, and answered early whether the game would fit <span class="tag emulator">emulator</span> [S32X-SKILL, porting-workflow.md].

## Ship the converter, not the data

When the original data belongs to someone else, distribute the tools and code, and let each user build the ROM from their own copy <span class="tag emulator">emulator</span> [S32X-SKILL, porting-workflow.md]. Aerobiz Ultimate builds every asset from the user's own ROM of the original game, and copies Sega's initial program from a 32X cartridge the user supplies [AU-NOTES, README; tools/extract_mars_init.py]. This book's [32X hello world](../howto/32x-hello.md#building) does the same.

## Make the build repeatable

- **Generate assets in the build**, from the original data, behind a stamp file, so that a change to a tool rebuilds what depends on it <span class="tag emulator">emulator</span> [S32X-SKILL, porting-workflow.md].
- **Build from data, not from captures.** Aerobiz Ultimate's map asset is reproducible from the ROM alone, with no save state, which is what exposed the mid-fade palette above [AU-NOTES, tools/make_map_asset.py].
- **Record what was verified.** Two homebrew ports ship a report with the ROM's size and hash, its header checksum, the end of its data against the stack limit, the toolchain version, and the emulator scenarios that passed <span class="tag emulator">emulator</span> [S32X-SKILL, porting-workflow.md].

## What to take away

- Convert at build time: byte order, alignment, pixel layout, palettes, tables, scripts.
- Keep read-only data in the cartridge, in the form the code reads, with a directory at a fixed place.
- Build palettes from the source art with reserved entries left out, and take colours from the data, not from a running game.
- Precompute what the CPU would otherwise calculate: matrices, glyph metrics, keyframes.
- For data-driven games, port the data and write a small interpreter for only what the data uses.
- Count the content before designing the engine.
- Ship converters, not other people's data.

## Open questions

- What did Sega's and the outside studios' own build tools look like? The ROMs show their outputs (Mortal Kombat II's directory and RNC files, After Burner Complete's run-length sprites, Star Wars Arcade's sample codebooks), but not the tools.

## Sources

- [MK2](../appendices/bibliography.md#mk2): ROM `$808`-`$977`; SH-2 code at `0x060006D0`
- [AU-NOTES](../appendices/bibliography.md#au-notes): README; tools/make_map_asset.py, make_project_logo.py, make_sega_logo.py, make_text_font.py, extract_mars_init.py; HISTORY 2026-09-16
- [S32X-SKILL](../appendices/bibliography.md#s32x-skill): porting-workflow.md, pico8-porting.md
