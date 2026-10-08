# Summary

[Introduction](introduction.md)
[How to read this book](conventions.md)

# Part I: The Mega Drive

- [System architecture](megadrive/architecture.md)
- [The 68000 for Mega Drive work](megadrive/m68k.md)
- [The VDP](megadrive/vdp.md)
  - [Registers and access](megadrive/vdp-registers.md)
  - [Planes and scrolling](megadrive/vdp-planes.md)
  - [Sprites](megadrive/vdp-sprites.md)
  - [Color, shadow/highlight and interlace](megadrive/vdp-color.md)
  - [DMA](megadrive/vdp-dma.md)
  - [Timing, interrupts and counters](megadrive/vdp-timing.md)
- [The Z80 and sound](megadrive/sound.md)
  - [Z80 bus control](megadrive/z80.md)
  - [YM2612 FM synthesis](megadrive/ym2612.md)
  - [PSG (SN76489)](megadrive/psg.md)
  - [Sega's Sound Driver V3](megadrive/sound-driver-v3.md)
- [Controllers and I/O ports](megadrive/io.md)
- [Cartridge hardware](megadrive/cartridge.md)
- [Sega's technical bulletins](megadrive/errata.md)

# Part II: The SH-2 (SH7604)

- [The SH7604 at a glance](sh2/overview.md)
- [Registers and instruction set](sh2/isa.md)
- [Pipeline and cycle counting](sh2/pipeline.md)
- [Cache](sh2/cache.md)
- [Bus controller and memory timing](sh2/bsc.md)
- [DMA controller](sh2/dmac.md)
- [Division unit](sh2/divu.md)
- [Timers (FRT and WDT)](sh2/timers.md)
- [Interrupt controller](sh2/intc.md)
- [Serial port (SCI)](sh2/sci.md)

# Part III: The 32X

- [Architecture and memory maps](32x/architecture.md)
- [System registers](32x/registers.md)
- [The 32X VDP](32x/vdp.md)
- [Mixing 32X and Mega Drive graphics](32x/compositing.md)
- [68000 and SH-2 communication](32x/communication.md)
- [DREQ and the FIFO](32x/fifo.md)
- [PWM audio](32x/pwm.md)
- [Boot, security code and initial program](32x/boot.md)
- [Access timing per CPU](32x/timing.md)
- [Hardware bugs and workarounds](32x/bugs.md)

# Part IV: How-tos

- [Setting up a toolchain](howto/toolchain.md)
- [Mega Drive ROM header and checksum](howto/md-header.md)
- [32X header and security code](howto/32x-header.md)
- [Hello world on the Mega Drive](howto/md-hello.md)
- [Hello world on the 32X, all CPUs running](howto/32x-hello.md)
- [Using more cartridge space](howto/large-cartridges.md)
- [Profiling and finding where time goes](howto/profiling.md)
- [Automated testing in an emulator](howto/emulator-testing.md)
- [Disassembling and annotating a commercial game](howto/reverse-engineering.md)
- [Testing on real hardware](howto/real-hardware.md)

# Part V: Getting the full potential

- [Splitting work across three CPUs](patterns/cpu-split.md)
- [Cache discipline](patterns/cache.md)
- [Living with bus contention](patterns/bus.md)
- [Holding 60 frames per second](patterns/60fps.md)
- [Using both video chips at once](patterns/layering.md)
- [Audio across PWM, FM and PSG](patterns/audio.md)
- [Moving data: DMA, FIFO and ROM](patterns/streaming.md)
- [Case study: Virtua Racing Deluxe](patterns/case-study-vr.md)
- [Case study: porting Aerobiz Supersonic](patterns/case-study-aerobiz.md)
- [Case study: After Burner Complete](patterns/case-study-afterburner.md)
- [Case study: Star Wars Arcade](patterns/case-study-starwars.md)

# Part VI: Techniques

- [Fixed-point maths and fast division](techniques/fixed-point.md)
- [Software 3D on the SH-2](techniques/software-3d.md)
- [First-person engines: raycasting and BSP](techniques/first-person.md)
- [Pseudo-3D roads and Mode 7](techniques/roads-mode7.md)
- [Voxel landscapes](techniques/voxel.md)
- [2D drawing and effects](techniques/2d-effects.md)
- [Text, menus and UI on tile planes](techniques/text-menus.md)
- [Compression and decompression](techniques/compression.md)
- [Memory on a 256 KB machine](techniques/memory.md)
- [Collision, physics and game logic](techniques/game-logic.md)
- [Asset pipelines and porting](techniques/asset-pipelines.md)

# Appendices

- [Memory maps](appendices/memory-maps.md)
- [Register quick reference](appendices/registers.md)
- [Timing tables](appendices/timing.md)
- [Where the docs disagree](appendices/discrepancies.md)
- [Sega's sample code in the games](appendices/sample-code.md)
- [Historical development systems](appendices/dev-systems.md)
- [Glossary](appendices/glossary.md)
- [Sources](appendices/bibliography.md)
