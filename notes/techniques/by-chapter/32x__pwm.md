# Harvested techniques: 32x/pwm.md

Target: `32x/pwm.md`. 10 entries. Raw reports and source caveats: [../raw/](../raw/) (paths relative to by-chapter/).

Evidence and licence notes are per entry. Describe in the book's own words; never copy code.

<!-- from S32X-SKILL -->
### PWM registers, cycle and sample rate
- Source: S32X-SKILL, references/audio.md:11-21, 233-236
- What it does and why it is clever: Control at 0x20004030, cycle at 0x20004032, L/R/mono FIFOs at 0x20004034/36/38. `cycle = SH2_clock / rate`. My arithmetic: 23.011 MHz / 11025 ≈ 2087; `NTSC_SH2 / 1045` ≈ 22.02 kHz.
- Key numbers: 11,025 Hz is the robust choice; about 22 kHz for streaming.
- Target chapter: 32x/pwm.md
- Evidence: tracker-player-32x (PCM-capture verified).

<!-- from S32X-SKILL -->
### Safe amplitude range
- Source: S32X-SKILL, references/architecture.md:70-74; references/audio.md:21
- What it does and why it is clever: Sample values must stay inside about 2..1032. My inference: the value range is bounded by the cycle count (about 1045 at 22 kHz, so roughly 10 bits). Clamp after mixing.
- Key numbers: 2..1032. The skill also says "~12-bit" elsewhere, which is inconsistent.
- Target chapter: 32x/pwm.md
- Evidence: d32xr (described).

<!-- from S32X-SKILL -->
### Keep the tiny FIFO fed: polling or DMA
- Source: S32X-SKILL, references/audio.md:40-48
- What it does and why it is clever: The FIFO holds only a few entries. Either poll-fill at the sample rate (deterministic, emulator-friendly) or stream through SH-2 DMA with half/full refill interrupts.
- Key numbers: —
- Target chapter: 32x/pwm.md
- Evidence: Tracker polls.

<!-- from S32X-SKILL -->
### Framebuffer redraw starves the FIFO into buzz
- Source: S32X-SKILL, references/audio.md:50-60
- What it does and why it is clever: A long full-framebuffer write blocks refills and the output becomes a frame-rate buzz. Initialise both framebuffers before starting PWM, redraw only on change, or move audio to the slave, a timer or DMA.
- Key numbers: —
- Target chapter: 32x/pwm.md
- Evidence: tracker-player-32x.

<!-- from S32X-SKILL -->
### Timing-critical mixer at fixed -O2 without LTO
- Source: S32X-SKILL, references/optimization.md:77-80; assets/Makefile:37-38
- What it does and why it is clever: The mixer must meet a per-sample deadline, so its object is pinned to `-O2 -fno-lto` (d32xr uses `-O1 -fno-lto` for `marshw.c`) so whole-program LTO cannot reshape it. This conflicts with the mixed-`-O` miscompile trap (problem 4).
- Key numbers: 1/22050 s deadline.
- Target chapter: 32x/pwm.md
- Evidence: d32xr.

---

<!-- from D32XR -->
### Volume maths sized to land directly in PWM range
- Source: D32XR, sh2_mixer.s:46-102, marssound.c:8-15, 1170-1194 (licence: MIT for the mixer; id limited-use for marssound.c)
- What it does and why it is clever: Per channel, `left = (255-pan)·vol·scale >> 10` and `right = pan·vol·scale >> 10` (vol and scale each up to 64, so up to 1020). An 8-bit sample becomes `(s-128)<<8`, and `(sample·vol)>>16` is then about ±510, the half-range of a 10-bit PWM cycle. The final pass only adds the centre (515) and clamps to [2, 1032]; no division or renormalising.
- Key numbers: 22050 Hz; SAMPLE_MIN 2, MAX 1032, CENTER 515. The RoQ path maps a 16-bit accumulator to PWM with `>>6`.
- Target chapter: 32x/pwm.md
- Evidence: code only

---

<!-- from VRD/AU/MARSDEV -->
### Keeping PWM fed inside long SH-2 jobs
- Source: VRD-NOTES, analysis/sh2-analysis/SH2_COMMAND_HANDLER_REFERENCE.md:57-79, 107-176, 204-225
- What it does and why it is clever: Every heavy Master handler calls `pwm_fifo_fill` (192 samples) between DMAC setup and the render work. The bulk track loader (`$06004228`) interleaves PWM output with the copy, so audio keeps playing through scene loads without interrupts.
- Key numbers: 192 samples per call; track copy 56,208 B.
- Target chapter: 32x/pwm.md
- Evidence: code only

<!-- from VRD/AU/MARSDEV -->
### PWM versus DMA restrictions
- Source: AU-NOTES, KNOWN_ISSUES.md:197-201; PORT_ARCHITECTURE.md:412-416
- What it does and why it is clever: A CPU that drives PWM, or touches the VDP in an H interrupt, cannot use auto-request DMA. If both SH-2s run auto-request DMA, one crawls. The plan streams PCM over DMA channel 1 accordingly.
- Key numbers: PWM is 2 channels of 11-bit PCM.
- Target chapter: 32x/pwm.md
- Evidence: manual (M6 unbuilt)

---

<!-- from D32XR (hardware survey) -->
### d32xr hardware survey: Audio
- `Mars_InitPWM` (marshw.c:317-344): MONO=1 written three times (unexplained); CYCLE = (((clock<<1)/rate + 1)>>1) + 1 with clocks 23011361 (NTSC) and 22801467 (PAL), giving 1045 / 1035 at 22050 Hz; PWM_CTRL=0x0185 "TM = 1, RTP, RMD = right, LMD = left"; ramps from minimum to centre while polling FIFO full, "to avoid click in audio (real 32X)".
- Range MIN 2, MAX 1032, centre (MAX-MIN)/2 at 22050 Hz (marssound.c:12-15); no comment on why.
- Formats: 8-bit unsigned PCM (sh2_mixer.s:82-84), 4-bit IMA ADPCM with 2x upsampler (marssound.c:1012-1024; sh2_mixer.s:143-329), WAV parsing (marssound.c:1347-1390). Channel position 18.14 fixed, (freq<<14)/22050 (marssound.c:1388; sh2_mixer.s:60-63). Pan/volume with mulu.w/muls.w (sh2_mixer.s:46-102). s16 to u16 with clamping (marssound.c:1184-1194); comment :1175-1176 on GCC reloading constants.
- Optional DMA mixer on the slave: DMA channel 1 to the PWM stereo register (one long sets both channels, marssound.c:1464); CHCR1=0x18E5 (fixed destination, incrementing source, longs, external DREQ paced by RTP, cycle steal, interrupt) (:1209-1211); double buffer of 2x316 stereo longs, MAX_SAMPLES 316 "70Hz" (:8, 70); completion interrupt restarts DMA on the filled half and mixes the other (marshw.c:1136-1142; marssound.c:1197-1218); commands from the master through a cache-through ring buffer (marssound.c:1411-1451). PWM interrupt unused (crt0.s:695-712).
- Default build: SFX to the Mega CD driver if present (marssound.c:53-54, 185-220); the 68000 plays VGM DAC samples by polling the PWM FIFO in its main loop (src-md/crt0.s:419-444; src-md/vgm.c:250-280).
- RoQ audio on slave DMA 1 at 632 samples "35Hz" (marsroq.c:43, 293-316); comment :178 prefers mulu.w over mul.l for latency.


<!-- from AB32X -->
### 16-voice interpolating mixer, both channels in one store (After Burner Complete)
- Source: AB32X, SH-2 code at `0x060003C0`-`0x0600046E`, `0x06000390`
- What it does and why it is clever: Slave mixes 16 voices: position = (sample count − start) × step, linear interpolation between 8-bit samples, two `muls.w` for L/R volume, scale by `dmuls.l` (keep MACH), add 737, clamp 1-1,474, into a 64-entry ring. The PWM interrupt (TM 1) writes L and R with one `mov.l` to `0x20004034`. Ring indices live in UBC registers `0xFFFFFF40`/`42`.
- Key numbers: Cycle `$5C3` ≈ 15.6 kHz; control `$0105`.
- Target chapter: 32x/pwm
- Evidence: ROM
