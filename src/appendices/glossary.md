# Glossary

Terms are explained in plain words. Add a term the first time a chapter uses it.

| Term | Meaning |
|------|---------|
| 68S | Bit 2 of the DREQ control register (`$A15106`). The 68000 sets it to start a FIFO transfer to the SH-2s; it clears itself when the length runs out. |
| A* | A path-finding search that always extends the path with the lowest cost so far plus an estimate of the cost remaining; with an estimate that never overestimates, it finds a shortest path. |
| Address checker | Sega's submission tool that watched a running game for access to prohibited areas and register misuse. It saw only executed code and found no other kind of bug. |
| ADEN | "Adapter enable": bit 0 of `$A15100`. Sega's initial program sets it to switch the 68000 over to the 32X memory map. Games never change it. |
| ADPCM | Adaptive differential PCM: sound stored as small steps from one sample to the next, with the step size growing and shrinking with the signal. The common IMA form takes 4 bits a sample, a quarter of 16-bit PCM. |
| Affine transform | A mapping that rotates, scales, shears and moves a picture, keeping straight lines straight. Drawn backwards: for each screen pixel, two fixed steps per pixel and two per row give the source pixel. |
| Algorithm (YM2612) | One of the eight ways a channel's four operators are wired: which modulate which, and which are summed as the output (the slots). Chosen in three bits of register `$B0`. |
| Associative purge | Throwing one line out of an SH-2's cache by writing to its address plus `0x40000000`. Used before reading data another CPU or a DMA transfer has changed. |
| Attenuation | How far below full volume a sound plays, in decibels. The PSG's volume registers hold an attenuation: 0 is loudest, each step is 2 dB quieter, 15 is off. |
| Auto fill | The 32X VDP's built-in fill: writes one value into up to 256 words of the back buffer while the CPUs do other work. |
| Auto-increment | VDP register 15: the number added to the VDP's address after every data port access. Usually 2. |
| Auto-request | An SH-2 DMA mode that starts copying as soon as the channel is enabled, without waiting for a request signal. Used for memory-to-memory copies. |
| Auto-vector | The SH-2's default way of picking a vector for an external interrupt: from its level alone, two levels per vector (64-71). The 32X uses it. |
| Back-reference | In LZ compression, an instruction to copy a number of bytes from a given distance back in the output already produced, instead of storing them again. |
| Backdrop | The single colour, chosen by VDP register 7, that shows wherever no plane or sprite pixel is drawn. |
| Backface culling | Dropping polygons that face away from the camera, found from the sign of their area after projection. On a closed object it removes about half the faces. |
| Bank set register | `$A15104`. Chooses which megabyte of the cartridge the 68000 sees at `$900000-$9FFFFF`. |
| Bank window | The Z80's 32 KB view of the 68000 address space at Z80 `$8000-$FFFF`. Which 32 KB it shows is set through the bank register at Z80 `$6000`. |
| Big-endian | Storing the most significant byte of a word at the lower address. The 68000 and the SH-2 are big-endian; PCs are little-endian, so data moved between them has its bytes swapped. |
| Billboard | An object drawn as a flat picture scaled to its distance, instead of as polygons. Doom's monsters and After Burner Complete's enemies are billboards. |
| Binary angle | An angle stored as a fraction of a turn, with one turn equal to a power of two (65,536 or 2<sup>32</sup>, for example), so adding wraps round by itself and the top bits index a table. |
| Bit plane | One bit of every pixel, stored together. Planar art keeps four or more planes separately; the 32X wants each pixel's bits together in one byte (chunky). |
| Blockmap | A grid laid over a level, listing which walls cross each cell, so collision tests only the walls near a moving object. |
| BSP tree | Binary space partition: a tree built from a level's walls that lists them in front-to-back order from any viewpoint. Doom draws walls in that order. |
| Bucket sort | Sorting by dropping each item into one of many lists, one per range of key, then reading the lists out in order. No item is compared with another. |
| Burst read | Reading several consecutive words from memory in one operation. The 32X's SDRAM always reads 16 bytes this way, even when the CPU wanted one byte. |
| Bus cycle | One access by a CPU to memory or a device: at least 4 clocks on the 68000 and 2 on the SH-2. Wait states are clocks added to it. |
| Bus contention | Two processors wanting the same memory at the same time. One gets it and the other waits, so a program can get slower because of what the *other* CPU is doing, not what it is doing itself. |
| Bus request | Asking another processor to get off a bus. On the Mega Drive, the 68000 writes `$0100` to `$A11100` to stop the Z80 before touching its memory. |
| Bus state controller (BSC) | The part of the SH-2 that turns accesses to outside memory into bus cycles: bus width, wait states, SDRAM control and sharing the bus with the other SH-2. Set by the 32X boot ROM; programs must not touch it. |
| Bytecode | A compact list of numbered instructions for a small interpreter written for the purpose, instead of machine code for the CPU. |
| Cache line | The unit an SH-2's cache works in: 16 bytes starting at a multiple of 16. A miss loads a whole line; a purge discards a whole line. |
| Cache-through address | An SH-2 address that reaches the same memory as a normal address but skips the cache. On the 32X it is the normal address plus `0x20000000`. Required for hardware registers. |
| CART | Bit 8 of the SH-2's interrupt mask register at `0x20004000`, read only: 0 when a cartridge is inserted. The Master's boot ROM uses it to choose between booting from the cartridge and from a Mega-CD. |
| Cell / tile | An 8 × 8 pixel pattern of 4-bit pixels, 32 bytes in VRAM. Planes and sprites are built from them. Sega's manuals say "cell" or "pattern". |
| CMD interrupt | The interrupt the 68000 sends to an SH-2 by writing to `$A15102` (bit 0 for the Master, bit 1 for the Slave). Level 8. There is no interrupt the other way. |
| Codebook | A table of short sample blocks or values that compressed data indexes into: each data byte stands for a whole block. Used by Star Wars Arcade's sound. |
| Colormap | In Doom, a 256-byte table that maps each palette colour to a darker one; 32 of them give 32 light levels. |
| Command word | The two-word value written to the VDP control port to choose a memory (VRAM, CRAM or VSRAM), a direction and an address, or to start a DMA. |
| Communication ports | Eight 16-bit registers at `$A15120-$A1512F` (SH-2 `0x20004020`) that the 68000 and both SH-2s can read and write. Also called COMM registers, with two different numbering schemes in use; see [68000 and SH-2 communication](../32x/communication.md#addresses-and-names). |
| Control code | A byte in a string that is not printed but tells the text engine to do something: move the cursor, change a margin, wait. |
| CRAM | Colour RAM inside the VDP: 64 words, four palettes of 16 colours. |
| Cross toolchain | A compiler, assembler and linker that run on one machine, such as a PC, and produce code for another, such as the SH-2 or the 68000. Named by target, as in `sh-elf-gcc`. |
| CSM | Composite sinusoidal modelling: the YM2612 mode in which every overflow of timer A keys channel 3's operators on and at once off again. Selected by writing `10` to register `$27`'s bits 7-6. |
| Cut | A revision of a chip's silicon, numbered like a version ("cut 2.3"). Sega's 32X bulletins name the SH-2 cuts that work on development boards and the one that fixed the interrupt flaw. |
| Cycle-steal | An SH-2 DMA mode that gives the bus back after every unit it moves, so the CPUs can get in between. The other mode, burst, keeps the bus until the transfer ends. |
| DAC (YM2612) | The YM2612's 8-bit sample output, which replaces FM channel 6 when enabled. A CPU must write every sample byte at the right moment. |
| DDA | Digital differential analyser: stepping along a line in fixed increments, here from grid cell to grid cell, testing each cell it enters. |
| Delay slot | The instruction right after an SH-2 branch. It runs before the branch takes effect. |
| Depth buffer | A per-pixel store of distance (also z-buffer), used to decide which surface is nearest. Too big and too slow for the 32X; its renderers sort instead. |
| Deterministic | Giving the same result every time from the same inputs. Replays, demos and automated tests depend on game logic being deterministic. |
| Development target | Sega's pre-production hardware for developers, issued in numbered versions. Several 32X faults and fixes in Sega's bulletins apply only to particular target versions, not to the consoles that were sold. |
| Direct colour | The 32X VDP mode with 16 bits per pixel, holding the colour itself instead of a palette number. A 320-pixel picture fits only 204 lines in one frame buffer. |
| Disassembly | Turning machine code back into assembly language. A rebuildable disassembly is source that assembles to exactly the original bytes. |
| DIVU | The SH-2's on-chip division unit: a signed 32/32 or 64/32 divide in 39 clocks, running alongside the CPU. Writing the dividend starts it; reading the result waits for it. |
| DMA (VDP) | The VDP copying data into its own memories by itself: from 68000 memory (the 68000 is stopped meanwhile), filling VRAM with one value, or copying within VRAM. |
| DMAC | The SH-2's DMA controller: two channels that copy data without the CPU. On the 32X, channel 0 takes the 68000's FIFO data and channel 1 can feed PWM. |
| Doorbell | A word whose change tells the other CPU "look now". It is written last, after the data it announces. |
| DREQ | "DMA request": the signal that tells the SH-2's DMA controller that the FIFO has data. |
| Duff's device | Unrolling a loop and entering it part-way through, so the first pass does the remainder of the count and every later pass does the full unrolled amount. |
| Dynamic recompiler | An emulator that translates blocks of the guest's machine code into host code and runs that, instead of decoding one instruction at a time as an interpreter does. Much faster, but it can skip details such as a cache model or the real program counter. |
| EDCLK | The pixel clock the Mega Drive puts on the cartridge slot. It always runs at the 320-pixel (H40) rate, and the 32X uses it as its own video clock. |
| ELF | The object and executable file format the GNU tools use. It holds code and data in named sections, with addresses and symbols; `objcopy -O binary` turns it into the raw bytes a cartridge needs. |
| Execute in place | Running code straight from the cartridge instead of copying it to RAM first. On the 32X, the SH-2 does it through its cached cartridge window at `0x02000000`. |
| FEN | Bit 1 of the 32X frame buffer control register, read only. It is 1 while an auto fill is running (and briefly during each DRAM refresh), when the frame buffer must not be touched. |
| Field of view | The angle the screen covers horizontally, from its left edge to its right, as seen from the viewer. |
| Fixed point | An integer that stands for itself divided by a fixed power of two. In 16.16 format a 32-bit value has 16 bits of whole number and 16 of fraction, so 1.0 is `$10000`. |
| Flash cartridge | A rewritable cartridge that loads a ROM image from a memory card, used to run homebrew and test builds on a console. How it maps the image is decided by its own firmware. |
| FM | Bit 15 of the 32X adapter control register. Decides whether the 68000 (0) or the SH-2s (1) may use the 32X VDP, palette and frame buffer. |
| FM synthesis | Making sounds by letting oscillators (operators) modulate each other's frequency. The YM2612 has six FM channels of four operators each. |
| Fog of war | Hiding the parts of a map no friendly unit can currently see, usually showing explored areas as they were last seen. |
| Frame | One refresh of the television picture, 1/60 of a second on NTSC and 1/50 on PAL. Not the same as a picture: a game drawing at 30 a second shows each picture for two frames. The frame rate is the number of pictures drawn a second. See [Frames and pictures](../conventions.md#frames-and-pictures). |
| Frame buffer | Memory holding the picture the 32X shows. There are two, and the program draws in one while the other is displayed. |
| FRT | The SH-2's 16-bit free-running timer. On the 32X it is reserved for Sega's interrupt workaround, which flips its output pin in every interrupt handler. |
| FS | Bit 0 of the 32X frame buffer control register. Chooses which of the two frame buffers is displayed. The swap happens at the next vertical blank. |
| Gamma code | A way of writing a number in bits where a run of zeros says how many value bits follow, so small numbers take few bits. Koei's LZ format uses one for match lengths. |
| Guard band | Memory around the visible area of a frame buffer that is never shown. Sprites that hang off the screen draw into it, so the blitter needs no clipping. |
| Headless | Run without a window or a person watching: an emulator driven by a program that feeds input and saves frames and memory. |
| H32 / H40 | The VDP's two screen widths: 32 tiles (256 pixels) or 40 tiles (320 pixels). |
| Headroom | How far below its maximum a sound is kept, so that adding another sound does not push the sum past the limit and distort. |
| Height map | A grid of numbers giving the height of the ground at each point; drawn in perspective, it becomes a landscape. |
| HEN | Bit 7 of the SH-2's interrupt mask register at `0x20004000`. When 1, H interrupts also arrive during vertical blank. One bit shared by both SH-2s. |
| Hitscan | An instant shot, resolved by tracing a line and taking the first thing it hits, rather than by moving a projectile. |
| Hook | A change to a program that diverts one call or jump to new code, which then usually carries on with what the original did. |
| Hot path | The code where a program spends most of its time, found by profiling. Moving or speeding up anything else changes little. |
| Huffman code | A code that gives common values short bit patterns and rare ones long ones, built from how often each value occurs. Decoding it needs a table, rebuilt from the data before use. |
| Initial program | Sega's fixed 1040-byte block at cartridge `$3F0-$7FF`. Every 32X game must carry it unchanged. It runs first on the 68000, enables the 32X, and reports its checks in the carry flag. |
| Interlace mode 2 | The VDP's double-resolution mode: 448 lines (480 on PAL) shown as alternate lines in alternate frames, with 8 × 16 tiles. |
| Jump table | A list of addresses, or of jump instructions, that a program indexes to choose a routine. The 32X cartridge has a fixed one at `$200` for the 68000's exceptions. |
| Keyframe | A stored pose or position at one moment of an animation; the frames between are worked out from the keyframes on either side. |
| Latch byte | A PSG write with bit 7 set. It chooses which of the eight PSG registers the following data bytes go to, and writes that register's low four bits. |
| Level of detail | Drawing a simpler model of an object when it is far away. |
| libgcc | GCC's library of helper routines, such as division, that compiled code calls when the CPU has no single instruction for the job. It must be built for the same CPU and byte order as the program. |
| Libretro | A plain C interface between an emulator (the "core") and the program that drives it (the "front end"). It lets a test harness load an emulator such as PicoDrive and run it frame by frame. |
| Line table | The first 256 words of each 32X frame buffer. Entry *n* is the word address where screen line *n*'s pixels start. |
| Linear congruential generator | A random-number generator that multiplies its state by a constant and adds another each time. Fast, but its low bits repeat with short periods. |
| Linear interpolation | Estimating a value between two known ones by moving along the straight line between them: *a* + (*b* − *a*) × *f* for a fraction *f*. Used to play samples at a pitch that falls between stored samples. |
| Linker script | The file that tells the linker where each section goes: its run address, and its load address in the image if that differs. |
| Literal pool | A table of constants placed after a piece of SH-2 code. The SH-2 has only 8-bit immediates, so larger constants and addresses are loaded from the pool with a PC-relative `MOV`. |
| Load address | Where a section's bytes sit in the image, as opposed to the address it runs at. On the 32X, `.data` is loaded in the cartridge and copied to SDRAM, where it runs. |
| Load-use stall | The clock an SH-2 loses when an instruction uses a register that the load just before it is still filling. One unrelated instruction in between avoids it. |
| Lump | A named block of data in a Doom WAD archive: a level's things, a texture, a sound. |
| LZSS | A family of LZ compression formats in which a flag bit before each item says whether it is a literal byte or a back-reference. |
| M_OK / S_OK | The four-character messages the Master and Slave SH-2 boot ROMs post at `$A15120` and `$A15124` just before starting the game's code. |
| Master / Slave | The two SH-2s in the 32X. The Master has priority on the bus. |
| Master clock | The crystal every other clock is divided from: 53.69 MHz on NTSC machines. The 68000 runs at a seventh of it, the Z80 at a fifteenth. |
| MD5 | A 128-bit fingerprint of a file. Two dumps with the same MD5 are the same bytes, so it identifies a known-good ROM. |
| Median cut | A way to choose a palette: split the image's colours repeatedly at the median of the channel with the widest range, then take one colour from each final group. |
| Mipmap | A smaller, pre-shrunk copy of a texture, used for distant surfaces so that fewer texels are skipped and less memory is read. |
| Mode 7 | A textured ground plane drawn one line at a time, each line at one distance from a table. Named after the Super Nintendo mode that does it in hardware; on the 32X it is done in software. |
| Name table | The VDP's map of which tile goes in each position of a plane. |
| Near plane | The distance in front of the camera below which points are not projected, because the divide by depth would blow up or change sign. |
| Operator | One sine-wave voice inside an FM channel: a frequency (phase), an envelope and an output. The YM2612 gives each channel four; a modulator's output bends the next operator's phase, a slot's output is the sound. |
| Operator sprite | In shadow/highlight mode, sprite pixels in palette 3 colours 14 and 15. They draw nothing; they brighten or darken whatever is underneath. |
| Oracle | In testing, a second trusted way of getting the right answer, such as the original game or a reference implementation, that results are compared against. |
| Ordered dither | Leaving out or changing pixels according to a fixed repeating pattern (such as a 4 × 4 table) to fake a level between two colours or between opaque and transparent. |
| Overdraw | Writing the same pixel more than once while drawing one picture. An overdraw of 1.36 means 36% more pixel writes than the screen has pixels. |
| Overwrite image | A second address range for the 32X frame buffer. Writes through it skip zero bytes, so those pixels keep their old value. |
| Packed pixel | The 32X VDP mode with one byte per pixel, each byte choosing one of 256 palette entries. |
| Painter's algorithm | Drawing surfaces from the farthest to the nearest, so that nearer ones cover farther ones. Needs a sort instead of a depth buffer. |
| Pan | Where a sound sits between the left and right speakers, set by giving it different volumes on each side. |
| PEN | A read-only bit of the 32X frame buffer control register. It is 1 while the palette may be accessed. |
| Peripheral ID | The four-bit code a device on a controller port reports through its direction lines, read once with TH at 1 and once at 0: `$D` a pad, `$3` a mouse, `$7` a Team Player, `$F` nothing connected. |
| Periodic noise | The PSG noise mode in which a single bit circles round the shift register, giving a buzzy tone one sixteenth of the noise rate. The other mode is white noise. |
| Picture | One complete image a program draws and shows, lasting one or more frames. Counted in pictures a second, the frame rate. See [Frames and pictures](../conventions.md#frames-and-pictures). |
| Pipeline | The SH-2 works on up to five instructions at once, each at a different stage (fetch, decode, execute, memory access, write back). That is how it finishes most instructions in one clock. |
| Plane | One of the VDP's scrolling tile layers, A or B, described by a name table in VRAM. |
| PRI | Bit 7 of the 32X bitmap mode register. 0 puts the Mega Drive picture in front of the 32X picture, 1 the reverse; a colour's through bit reverses it for that colour. |
| Priority bit | Bit 15 of a name table entry or a sprite's tile word. It lifts that tile or sprite above the low-priority layers. |
| Proportional font | A font whose characters have different widths, so an i takes less room than an m. Each glyph stores its own width and the distance to the next character (its advance). |
| PSG | Programmable sound generator: the SN76489-type chip inside the VDP, with three square-wave channels and one noise channel. |
| PWM | Pulse-width modulation: the 32X's two sound channels. Each sample sets how long a pulse stays high in one sample period; a filter turns the pulses into a waveform. |
| Quarter-wave table | A sine table holding only the first quarter turn; the other three quarters are read from it backwards or negated. |
| Raycasting | Drawing a 3D view by sending one ray per screen column through a 2D map until it hits a wall; the wall's distance gives its height on screen. |
| Read-modify-write | Changing some bits of a register by reading it, altering the value and writing it back. Safe only if nothing else changes the register between the read and the write. |
| Rebasing | Moving a program to a different address by changing every address it holds, in code and in data, by the same amount. A Mega Drive game moved into the 32X's `$900000` window needs it. |
| Reciprocal table | A table of 2<sup>n</sup> divided by each possible divisor, so a divide becomes a look-up and a multiply. |
| Refresh | Rereading the rows of a DRAM or SDRAM chip regularly so it keeps its contents. On the 32X the Master SH-2's bus controller refreshes the SDRAM every 356 clocks. |
| Reject table | In Doom, a precomputed bit table marking pairs of sectors that can never see each other, so most line-of-sight checks end with one bit test. |
| REN | Bit 7 of `$A15100`, read only, named "SH2 reset enable". Sega's initial program waits for it to read 1; no manual says what sets it. |
| RES | Bit 1 of `$A15100`. 0 holds both SH-2s in reset, 1 lets them run. Set by Sega's initial program and never changed by games. |
| Ring buffer | A buffer used in a circle: writing continues at the start after the end, and the oldest data is overwritten or dropped first. |
| Run-length encoding | Storing a run of identical values as one value and a count. Suits sprites, with their long transparent runs. |
| RV | Bit 0 of `$A15106`, "ROM to VRAM DMA". While it is 1, the cartridge is back at `$000000-$3FFFFF` for Mega Drive VDP DMA, and the SH-2s cannot read it. |
| Save state | A snapshot of an emulated machine's whole state (CPU registers, memories, chip registers) in a file, from which the emulator can carry on. Its format belongs to the emulator and often its version. |
| SCI | The SH-2's serial port. On the 32X the Master's and Slave's ports are wired to each other and to nothing else. |
| Section | A named part of an object file, such as `.text` for code or `.data` for initialised data. The linker script places sections; one it does not name may end up outside the image. |
| Sequencer | The part of a sound driver that reads music or effect data and decides, tick by tick, which notes start and stop and what to write to the sound hardware. |
| Shadow / highlight | A VDP mode (register 12 bit 3) that shows each pixel at normal, darker or brighter level depending on priority bits and operator sprites. |
| Shift register | A row of bits that moves one place at each clock tick. The PSG's noise channel outputs the bit that drops out; feeding some bits back into the other end makes white noise. |
| Short pointer | A pointer stored in 16 bits as an offset from the start of SDRAM in 4-byte units, which reaches all 256 KB. |
| Slot-illegal instruction | A branch, or an undefined code, placed in an SH-2 delay slot. The CPU does not run it and takes exception vector 6 instead. |
| Slot | One step of the SH-2 pipeline. It lasts as long as the slowest stage in it, so one slow memory access holds up every instruction in flight. |
| Sound driver | The program that plays a game's music and effects: it takes requests from the game, runs the sequencer and writes the sound chips or feeds the samples. |
| Sound RAM | The Z80's 8 KB of RAM, at Z80 `$0000-$1FFF` and 68000 `$A00000-$A01FFF`. Holds the sound program and its data. |
| Staging buffer | Memory a picture or a block of data is built in before it is copied, finished, to where it is used. |
| Supervisor mode | The 68000's privileged execution state, entered at reset and on every exception. Privileged instructions are legal only here; Mega Drive software never leaves it. |
| Span | A horizontal run of pixels on one row. Filled shapes are usually drawn as one span per row. |
| TAS.B | SH-2 test-and-set: reads a byte, sets its top bit and writes it back without letting go of the bus. Used for locks between the two SH-2s, though Sega's manual forbids it on the 32X. |
| TH | The select line of a controller port (DATA bit 6). The console drives it to choose which buttons the pad puts on the data lines, and a 6-button pad also counts its changes to reveal an extra set of buttons. |
| T bit | Bit 0 of the SH-2 status register, its only condition flag. Compares and tests set it, conditional branches read it, and carry arithmetic uses it as the carry. |
| Through bit | Bit 15 of a 32X colour. Decides whether that pixel is drawn in front of or behind the Mega Drive picture. |
| Thunk | A short routine that stands in for another one and forwards the call, for example to an SH-2. |
| Tick | One step of the game's logic. A fixed tick rate keeps the game's speed independent of how fast pictures are drawn. |
| TMSS | The check added to later Mega Drives: the game must write `SEGA` to `$A14000` on any console whose version number is not zero. |
| Trampoline | A jump left at a routine's old address after the routine has been moved, so that every existing caller still reaches it. |
| Two-way mode | An SH-2 cache setting (CCR bit TW) that keeps 2 KB as cache and turns the other 2 KB into on-chip RAM at `0xC0000000`. |
| UBC | The SH-2's user break controller: two hardware breakpoints that raise an interrupt when a chosen address or value is accessed. No 32X program in this book's sources uses it. |
| User header | 48 bytes at cartridge `$3C0` that tell the Master SH-2 boot ROM which SH-2 code to copy into SDRAM, and where each SH-2 starts. |
| VBR | Vector base register: where an SH-2's exception vector table starts. Vector *n* is read from VBR + 4*n*. Set from the user header at boot. |
| Vector ROM | The 32X's 256-byte ROM at 68000 address `$000000` once the 32X is switched on. It sends each exception to a jump table in the cartridge at `$880200`. |
| VGM | A file format that records the register writes sent to sound chips, with their timing, so a player can replay them. |
| Visplane | In Doom's renderer, one floor or ceiling area on screen: the columns it covers, each with a top and bottom row, sharing one height, texture and light. |
| Voice | One sound playing at a time: a sample with its own position, pitch and volume, or one channel of a sound chip. A software mixer adds several voices into one output. |
| Voxel landscape | A height map drawn as columns or blocks of colour scaled by distance, rather than as polygons. |
| VRAM | The VDP's 64 KB of video memory. Neither CPU can address it; everything goes through the VDP's ports. |
| VRES | The SH-2 interrupt (level 14) raised when the Mega Drive's reset button is pressed. The SH-2s are not reset. |
| VSRAM | Vertical scroll RAM inside the VDP: 40 words of vertical scroll values for planes A and B. |
| Wait state | An extra clock added to a bus cycle while slow memory gets ready. The SH-2's shortest bus cycle is 2 clocks, so an access with 1 wait state takes 3. |
| WDT | The SH-2's 8-bit watchdog timer. On the 32X it may not reset the chip, so programs use it as an interval timer. |
| Window plane | A non-scrolling tile layer that replaces plane A in an area set by VDP registers 17 and 18. Used for status bars. |
| Word wrap | Moving a word that would cross the right edge of a text area to the start of the next line. |
| Write buffer | A one-entry queue in the SH-2's bus controller. A store can still be in progress when the next instruction runs; reading the same address back waits for it to finish. |
| Write-through | A cache that sends every write straight on to memory. The SH-2's cache works this way, so its lines are never newer than memory. |
| Y-buffer | For each screen column, the highest row drawn so far. A renderer that works near to far fills only above it, so each pixel is drawn once. |
| YM2612 | Yamaha's FM sound chip in the Mega Drive: six FM channels, a sample DAC, two timers and an LFO. |
| Zone allocator | A memory allocator that manages one large block, the zone, as a chain of used and free blocks covering it exactly, each tagged with how long it should live. |
