# Harvested techniques: patterns/audio.md

Target: `patterns/audio.md`. 24 entries. Raw reports and source caveats: [../raw/](../raw/) (paths relative to by-chapter/).

Evidence and licence notes are per entry. Describe in the book's own words; never copy code.

<!-- from S32X-SKILL -->
### Software voice mixer
- Source: S32X-SKILL, references/audio.md:23-30, 76-90
- What it does and why it is clever: Each voice has `{pos (fixed-point), loop_start/end, pitch_inc, vol, pan}`. Per output sample: `L = Σ s[pos>>F]·vol·(1−pan)`, `R = Σ …·pan`, clamp, push to FIFO, `pos += inc` with loop wrap. Eight voices fit on one SH-2. Row-0 with all 8 notes is the stress test.
- Key numbers: 8 voices at 11,025 Hz stereo.
- Target chapter: patterns/audio.md
- Evidence: tracker-player-32x, verified by PCM capture against an OpenMPT render.

<!-- from S32X-SKILL -->
### Voice stealing for priority SFX
- Source: S32X-SKILL, references/audio.md:32-34, 88-89
- What it does and why it is clever: An SFX takes over an existing voice (for example voice 8) instead of using a ninth, and the next music note on that lane reclaims it. The voice budget stays fixed and behaviour stays deterministic.
- Key numbers: —
- Target chapter: patterns/audio.md
- Evidence: tracker-player-32x.

<!-- from S32X-SKILL -->
### Validate sample formats in the converter
- Source: S32X-SKILL, references/audio.md:35-38
- What it does and why it is clever: The build tool rejects packed, 16-bit or stereo instruments instead of letting the runtime mis-decode them. One format (8-bit mono unpacked) keeps the mixer simple.
- Key numbers: —
- Target chapter: patterns/audio.md
- Evidence: Tracker converter.

<!-- from S32X-SKILL -->
### Compute gain once per block, not per sample
- Source: S32X-SKILL, references/audio.md:135-137
- What it does and why it is clever: Per-voice gain is computed once per output block, keeping multiplies by volume and pan out of the sample loop.
- Key numbers: —
- Target chapter: patterns/audio.md
- Evidence: wave-rider-gp.

<!-- from S32X-SKILL -->
### IMA-ADPCM sample banks decoded on the slave
- Source: S32X-SKILL, references/audio.md:124-140
- What it does and why it is clever: Store clips as 4-bit IMA ADPCM with each clip's starting predictor and step index in ROM. The slave runs the predictor/step-index state machine per voice (4 bits in, one 16-bit sample out), sums and clamps. The skill gives no decoder details. Standard IMA (my addition): 89-entry step table, `diff = step>>3 + (b2?step) + (b1?step>>1) + (b0?step>>2)`, sign from b3, index += {−1,−1,−1,−1,2,4,6,8}.
- Key numbers: About 4:1 compression. 26 sounds at 11,025 Hz mono.
- Target chapter: patterns/audio.md
- Evidence: wave-rider-gp-32x.

<!-- from S32X-SKILL -->
### Streaming BGM from ROM, played twice for 22 kHz, with concurrent SFX
- Source: S32X-SKILL, references/audio.md:224-238
- What it does and why it is clever: A ROM directory `(offset, num_samples, loop_flag)` indexes the tracks. One uninterrupted ADPCM stream plus a 2-voice PCM SFX layer runs on the slave. Each 11 kHz sample is output twice to reach about 22 kHz PWM, halving ROM and decode cost. Music uses zero SDRAM.
- Key numbers: 6 tracks, 11 kHz, 4-bit. 2 SFX voices. `PWM_CYCLE ≈ NTSC_SH2/1045`.
- Target chapter: patterns/audio.md
- Evidence: raintown-slickers-32x.

<!-- from S32X-SKILL -->
### BGM memorize/restore and fade
- Source: S32X-SKILL, references/audio.md:257-263
- What it does and why it is clever: RM2K-style `MemorizeBGM` before a battle and `PlayMemorizedBGM` after, plus loop and N-frame fade-out, hooked into the map loader and the battle/victory/return paths.
- Key numbers: —
- Target chapter: patterns/audio.md
- Evidence: raintown-slickers-32x.

<!-- from S32X-SKILL -->
### Genesis-side music (XGM/SGDK) with the UI on the SH-2
- Source: S32X-SKILL, references/audio.md:100-122
- What it does and why it is clever: An SGDK-built 68000 program linked at 0x880800 runs the XGM driver (Z80 + YM2612/PSG). The SH-2 draws the UI and sends play/pause/stop over COMM (SH-2 0x20004020 ↔ 68000 0xA15120). PWM stays free for SFX.
- Key numbers: 68000 ROM window 0x880800.
- Target chapter: patterns/audio.md
- Evidence: xgm-player-32x.

<!-- from S32X-SKILL -->
### 68000 VGM player paced by YM2612 Timer A with bounded waits
- Source: S32X-SKILL, references/architecture.md:75-83
- What it does and why it is clever: Convert the score to VGM 1.50 at build time and play it from a work-RAM 68000 player paced by YM2612 Timer A at the source tick rate. YM busy-waits and per-tick command batches are bounded so bad data can't stall pad/VBlank service. Leave a few dB of headroom on FM carriers so PWM SFX cut through.
- Key numbers: —
- Target chapter: patterns/audio.md
- Evidence: Described (ports).

<!-- from S32X-SKILL -->
### MIDI→VGM: routing per part, demand-driven
- Source: S32X-SKILL, references/audio.md:142-178
- What it does and why it is clever: The pipeline is Ingest (tempo map, CC64 sustain, CC7/CC11 loudness, pitch-bend cents, ch10 drums) → IR → Map/Allocate → Emit. Each part (not each note) is routed to FM or PSG so timbre never flips mid-phrase. Parts the PSG would ruin claim FM first, and the rest spills to PSG. Notes below the PSG floor (~C2) are folded up whole octaves and bass is penalised on PSG (clamping gave ~890-cent errors). Per-part mean cents error is used as a routing cost. Chords are thinned to root + top only when a pool is oversubscribed.
- Key numbers: 6 FM + 3 PSG tone + 1 noise + 1 DAC.
- Target chapter: patterns/audio.md
- Evidence: midi2vgm, verified against Nuked-OPN2.

<!-- from S32X-SKILL -->
### FM retrigger gap and role-based mixing
- Source: S32X-SKILL, references/audio.md:179-185
- What it does and why it is clever: Key-off and key-on at the same timestamp means the envelope never releases and the note goes silent; insert a gap. A 3-note pad carries about 3× the energy of one lead note, so offset levels by role and spread them across voice counts.
- Key numbers: KEY_GAP ≈ 1.5 ms. Lead −6 dB, pad +12 dB.
- Target chapter: patterns/audio.md
- Evidence: Found only with a cycle-accurate core.

<!-- from S32X-SKILL -->
### Polyphonic drums pre-mixed into the DAC, plus a PSG noise transient layer
- Source: S32X-SKILL, references/audio.md:187-201
- What it does and why it is clever: Overlapping drum hits are pre-mixed offline into one mono PCM stream on FM channel 6, so the DAC is effectively polyphonic. The 0x2B trap: an init write of `0x2B = 0` at t = 0 lands after DAC enable and kills the drums, and channel 6 must be excluded from key-off and allocation. The PSG noise channel layers a short decay over hats, snares and toms; hits within 20 ms collapse, loudest wins.
- Key numbers: DAC about 13.75 kHz, 8-bit. +44% energy in 6-15 kHz.
- Target chapter: patterns/audio.md
- Evidence: midi2vgm, regression-tested.

<!-- from S32X-SKILL -->
### VGM DAC-stream emission and calibration
- Source: S32X-SKILL, references/audio.md:203-215
- What it does and why it is clever: Command order: `0x67 0x66` data block → `0x90` (chip 0x02, port 0, reg 0x2A) → `0x91` → `0x92` → `0x2B = 0x80` → `0x93` → … → `0x94`, `0x2B = 0`. Calibrate the checker before trusting it: A4 → fnum 1083 at block 4, FM error under 1 cent for MIDI 24-107, SN76489 `f = clock/(32n)`, and an FFT round trip within about 0.1 semitone.
- Key numbers: VGM ≥ 1.61. NTSC clocks 7,670,453 / 3,579,545; PAL 7,600,489 / 3,546,895.
- Target chapter: patterns/audio.md
- Evidence: midi2vgm.

<!-- from S32X-SKILL -->
### Choosing a music path: streaming ADPCM or MIDI→VGM
- Source: S32X-SKILL, references/audio.md:265-281
- What it does and why it is clever: ADPCM plays the real recording, is simple, uses no SDRAM and mixes with SFX, but costs megabytes of ROM. VGM is tiny and authentic FM, but needs MIDI and a 68000 player.
- Key numbers: About 4 MB cart for a handful of ADPCM loops.
- Target chapter: patterns/audio.md
- Evidence: Comparison across ports.

---

<!-- from D32XR -->
### Packed-stereo resampling mixer (8-bit PCM)
- Source: D32XR, sh2_mixer.s:23-141, marssound.c:1007-1075, 1327-1409 (licence: MIT for the mixer; id limited-use for marssound.c)
- What it does and why it is clever: The mix buffer holds one 32-bit word per stereo frame, left in the high 16 bits and right in the low 16. Both scaled channel contributions are merged into one value and added with a single `add`, half the loads and stores of separate L/R buffers. Sample position is fixed point with 14 fractional bits, `increment = (freq<<14)/22050` capped at 1.0, and the sample index is `pos>>14`, computed as `shlr8, shll2, shlr8` (nearest-neighbour). Loop and end handling is a compare with optional `pos -= loop_length`.
- Key numbers: 316 frames per buffer (about 70 Hz at 22050).
- Target chapter: patterns/audio.md
- Evidence: code only

<!-- from D32XR -->
### IMA ADPCM decoded inside the mixer, with a merged index table
- Source: D32XR, sh2_mixer.s:143-620 (licence: MIT)
- What it does and why it is clever: The decoder emits a new sample only when the integer nibble position changes (`prev_pos`), so upsampling costs no extra decodes. It computes `diff = ((2n+1)·step)>>3` with one `muls.w` and three `shar`s, and clamps to int16. The step-index update and its 0..88 clamp are folded into one 2D byte table indexed `[index*8 + nibble]`, which stores the next index already doubled as a byte offset into step_table. A 2x variant, chosen when the increment is a power of two below 1.0 (11025 into 22050), writes each decoded sample to two output frames.
- Key numbers: step_table 89 words; merged index table 89x8 bytes.
- Target chapter: patterns/audio.md
- Evidence: code only

<!-- from D32XR -->
### Cheap 2D spatialisation at 15 Hz
- Source: D32XR, marssound.c:17-41, 355-522, 1131-1155 (licence: id limited-use)
- What it does and why it is clever:
  - **Distance.** Octagonal approximation `dx+dy-min(dx,dy)/2`.
  - **Volume.** `vol·(1224-d)/1024` between 200 and 1224 units.
  - **Pan.** `128 - 96·sin(angle to listener)`, clamped to [0, 255].
  - **Update rate.** Recomputed only every 1470 samples (about 15 Hz), not per buffer.
  - **Split screen.** Pan comes from the volume difference between the two listeners.
- Key numbers: S_CLIPPING_DIST 1224, S_CLOSE_DIST 200, S_STEREO_SWING 96.
- Target chapter: patterns/audio.md
- Evidence: code only

<!-- from D32XR -->
### Channel stealing and pitch-shifted sound reuse
- Source: D32XR, marssound.c:1229-1325, 524-600 (licence: id limited-use)
- What it does and why it is clever:
  - **Duplicate starts.** A second start of the same sound at the same instant only replaces the first if louder.
  - **Singular sounds** overlay their existing channel.
  - **One sound per source.** A new sound from the same mobj cuts that mobj's old one.
  - **Otherwise** it takes a dead channel, then any channel of lower or equal priority.
  - **Reuse for ROM space.** Missing sounds are mapped to existing samples at other playback rates (e.g. boss pain = imp pain at 5512 Hz, player-pod sounds at 7350 Hz).
- Key numbers: substitute rates 3675, 5512, 7350, 16500 Hz.
- Target chapter: patterns/audio.md
- Evidence: code only

<!-- from D32XR -->
### Double-buffered DMA mixing with idle detection
- Source: D32XR, marssound.c:1077-1124, 1197-1227 (licence: id limited-use)
- What it does and why it is clever: The DMA-complete handler on the slave starts DMA on the buffer it just filled, flips the index, drains the command queue and mixes the next buffer. A counter tracks consecutive buffers with nothing to mix. After more than 2 (both buffers silent and safe to leave playing) it stops clearing and mixing until a sound starts again.
- Key numbers: 2 x 316 longs.
- Target chapter: patterns/audio.md
- Evidence: code only

<!-- from D32XR -->
### RoQ square-law DPCM decode
- Source: D32XR, marsroq.c:87-291 (licence: MIT)
- What it does and why it is clever: Each byte is sign plus 7-bit magnitude m, and the delta is ±m². The accumulator is unsigned 16-bit, biased by 32768. Overflow above 65535 is caught by testing bit 16 with one AND against 0x10000 (`c_hi`) instead of a compare; the value is then clamped and `>>6` gives the 10-bit PWM value. Stereo channels interleave and the initial predictors come from the chunk header.
- Key numbers: 632 samples per buffer (35 Hz); 267 ms mix-ahead.
- Target chapter: patterns/audio.md
- Evidence: code only

---

<!-- from VRD/AU/MARSDEV -->
### 68K-resident FM/PSG sequencer with a tiny Z80 DAC player
- Source: VRD-NOTES, analysis/SOUND_DRIVER_ARCHITECTURE.md:1-118, 191-330
- What it does and why it is clever:
  - **CPU split:** the 68K synthesizes everything each tick; the Z80 runs only a 653-byte DAC loop with three mailbox bytes.
  - **Commands:** game code writes three priority mailboxes (music, SFX deduplicated, ambient) instead of calling the driver.
  - **SFX overlay:** six SFX channels overlay music FM channels, saving and restoring state.
  - **Volume:** a per-algorithm table scales only carrier operators.
  - **Sequences:** byte streams use call/return and loop counters.
  - **Fades:** separate DAC, FM and PSG fade rates.
- Key numbers: 18 channels × 48 B; 128-entry priority table; PSG table of 128 notes; 4 KB DAC samples.
- Target chapter: patterns/audio.md
- Evidence: code only

---

<!-- from D32XR (hardware survey) -->
### d32xr hardware survey: Audio
- `Mars_InitPWM` (marshw.c:317-344): MONO=1 written three times (unexplained); CYCLE = (((clock<<1)/rate + 1)>>1) + 1 with clocks 23011361 (NTSC) and 22801467 (PAL), giving 1045 / 1035 at 22050 Hz; PWM_CTRL=0x0185 "TM = 1, RTP, RMD = right, LMD = left"; ramps from minimum to centre while polling FIFO full, "to avoid click in audio (real 32X)".
- Range MIN 2, MAX 1032, centre (MAX-MIN)/2 at 22050 Hz (marssound.c:12-15); no comment on why.
- Formats: 8-bit unsigned PCM (sh2_mixer.s:82-84), 4-bit IMA ADPCM with 2x upsampler (marssound.c:1012-1024; sh2_mixer.s:143-329), WAV parsing (marssound.c:1347-1390). Channel position 18.14 fixed, (freq<<14)/22050 (marssound.c:1388; sh2_mixer.s:60-63). Pan/volume with mulu.w/muls.w (sh2_mixer.s:46-102). s16 to u16 with clamping (marssound.c:1184-1194); comment :1175-1176 on GCC reloading constants.
- Optional DMA mixer on the slave: DMA channel 1 to the PWM stereo register (one long sets both channels, marssound.c:1464); CHCR1=0x18E5 (fixed destination, incrementing source, longs, external DREQ paced by RTP, cycle steal, interrupt) (:1209-1211); double buffer of 2x316 stereo longs, MAX_SAMPLES 316 "70Hz" (:8, 70); completion interrupt restarts DMA on the filled half and mixes the other (marshw.c:1136-1142; marssound.c:1197-1218); commands from the master through a cache-through ring buffer (marssound.c:1411-1451). PWM interrupt unused (crt0.s:695-712).
- Default build: SFX to the Mega CD driver if present (marssound.c:53-54, 185-220); the 68000 plays VGM DAC samples by polling the PWM FIFO in its main loop (src-md/crt0.s:419-444; src-md/vgm.c:250-280).
- RoQ audio on slave DMA 1 at 632 samples "35Hz" (marsroq.c:43, 293-316); comment :178 prefers mulu.w over mul.l for latency.

<!-- from MK2 -->
### PWM effects on the Slave, requested through one port (Mortal Kombat II)
- Source: MK2, 68000 code at `$00E01A`; SH-2 code at `0x06005178`, `0x06004F4C`
- What it does and why it is clever: The 68000 writes a sample number with bit 8 set into `$A1512E`; the Slave, polling it, starts the sample on a free voice and clears the word. Fire and forget: no acknowledgement, so a second request in the same few microseconds replaces the first. Two voices, mixed so the silence level stays at about 512 with one voice or two and the sum never needs clamping. Voice choice: A if free, else B, else the one not started last.
- Key numbers: cycle 1,043 (22,084 Hz); 6-bit packed samples played at half rate.
- Target chapter: patterns/audio.md
- Evidence: ROM

<!-- from AB32X -->
### Sound path Z80 → 68000 H-interrupt → Slave sequencer (After Burner Complete)
- Source: AB32X, 68000 `$91E`; SH-2 `0x06000684`, `0x06000820`
- What it does and why it is clever: The 68000's H-interrupt handler reads a request the Z80 left in its RAM (`$A016FD`), sends it to the Slave with CMD (`$0203` in `$A15122`), then sends the `$0200` sequencer tick. The Slave runs a sequencer (39 tracks) on the tick and a 16-voice PWM mixer the rest of the time.
- Target chapter: patterns/audio
- Evidence: ROM
