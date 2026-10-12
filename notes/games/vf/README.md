# Virtua Fighter (32X) working notes

Working material for `src/patterns/case-study-vf.md`; not part of the book. The retail cartridge is `Virtua Fighter (Japan, USA).32x` (bibliography key VF32X, MD5 `901e97c9...`).

| File | What |
|------|------|
| `SH2.md` | The SH-2 program, read by disassembly and instrumented PicoDrive runs: memory map, interrupts, command protocol, the four-stage renderer, memory and cache, PWM, a construct-by-construct comparison with Virtua Racing Deluxe retail, open questions, a routine table |
| `M68K.md` | The 68000 side: boot, the RAM-resident code, the picture states, communication, the HUD and Mega Drive layers, sound, the comparison with Virtua Racing Deluxe retail, routine table, how to reproduce the numbers |
| `data/` | Small text outputs of the scripts for the runs described |
| `build_vf_core.sh`, `vf_trace.patch` | The SH-2 tracing core |
| `build_vf68_core.sh`, `patch_m68klog.py`, `patch_vdplog.py`, `patch_z80log.py` | The 68000, VDP and Z80 logging core |
| `patch_models.py`, `picturetime_by_frame.py` | The first writes four ROM variants with the shadow plate and/or the floor model removed from the draw list; the second gives the 68000's first-look and done times per 100 frames (`data/picturetime_by_frame_attract.txt`) |
| `picstats.py` | Per-picture figures from the interpreter-run call and ring logs: overlay A calls, instructions per phase, ring slots, reject exits, the Slave's command 1 (output for the 11-picture window in `data/picstats_interpreter.txt`) |
| `vfa.py`, `dd.py`, `syms.txt`, `hexd.py`, `regmap.py`, `ctree.py`, `cagg.py`, `fprof.py`, `fprof2.py`, `summ.py`, `dumpmem.py`, `fbrender.py`, `modelparse.py` | SH-2 side helpers: code map, compact disassembly with names, executed-code map, call trees, histograms, polygon-stream parser |
| `vfdis.py`, `ramdump.py`, `framewatch.py`, `logsum.py`, `msgs.py`, `picturetime.py`, `mdplanes.py`, `hufftile.py`, `kosdec.py`, `blockmap.py`, `dd.py`, `dmasum.py`, `regmap.py`, `statetrace.py` | 68000 side helpers: disassembly by 68000 address, RAM dumps, log summaries, picture timing, plane renderer, Python ports of the game's two decompressors |

Pitfalls found on the way (also in `../tools/README.md`): a profile from power-on stalls this game after about 1,300 frames; interpreter-run durations are about 1.6 times too long. Evidence tags in the two notes files: ROM (read in the code), run (PicoDrive: no SH-2 wait states, so never a console timing), inference.
