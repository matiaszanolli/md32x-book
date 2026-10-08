# Harvested techniques: patterns/case-study-vr.md

Target: `patterns/case-study-vr.md`. 2 entries. Raw reports and source caveats: [../raw/](../raw/) (paths relative to by-chapter/).

Evidence and licence notes are per entry. Describe in the book's own words; never copy code.

<!-- from VRD/AU/MARSDEV -->
### The VR60 rework's staged plan and its current state
- Source: VRD-NOTES, VR60_STATUS.md:131-160, 449-461; VR60_ROADMAP.md:1231-1268, 1270-1292
- What it does and why it is clever:
  - **Target architecture:** the 68K becomes a thin I/O, sound and VDP coordinator. The Master SH-2 runs physics, AI and collision on entities moved to SDRAM (`$0600F20C`). It writes descriptors directly and triggers the Slave with one COMM write.
  - **Hard constraints:** a table of 13 (H-1 to H-13), for example sound must stay on the 68K.
  - **Order of work:** each stage is gated: transport, then shadow execution, then descriptor bridge, then equivalence, then authority, then cadence.
  - **Current state:** only cmd `$3E` mode 0 (a 320-byte player transfer) is in the default build. Cmd `$3F`, the SH-2 physics path and collision are built but dormant.
- Key numbers: per-frame budget about 128 K 68K cycles and 383 K SH-2 cycles.
- Target chapter: patterns/case-study-vr.md
- Evidence: emulator measured for gates passed; the architecture itself is unvalidated

<!-- from VRD/AU/MARSDEV -->
### SDRAM allocation and ownership lessons
- Source: VRD-NOTES, VR60_ROADMAP.md lessons 2026-03-17 / 2026-03-26; VR60_STATUS.md:224-233
- What it does and why it is clever: Grep all SH-2 code before allocating SDRAM: a gradient strip at `$060086D4` blocked `$06008000`. Re-staging a WRAM copy each frame overwrote SH-2 accumulated state, so an entity needs exactly one owner. One payload grew upward from `$06010000` while the Slave stack grows downward from it, and the region was later mutated by an unknown writer.
- Key numbers: see above.
- Target chapter: patterns/case-study-vr.md
- Evidence: emulator measured (PicoDrive)

---

