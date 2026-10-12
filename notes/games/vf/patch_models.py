#!/usr/bin/env python3
"""patch_models.py ROM OUTDIR: write four copies of the Virtua Fighter ROM with models removed from the Master's draw list,
to find what they draw (run each in PicoDrive from power-on, dump the frame buffer with fbrender.py, compare):
  vf_ctrl.32x     unchanged
  vf_noplate.32x  the ground plate of each fighter disabled: `mov #1,r0` at 0x06019AB0 becomes `mov #0,r0`, so the plate's
                  descriptor is written with enable = 0 and the loop at 0x06007364 skips it
  vf_nostage.32x  the extra 56-vertex model dropped: the routine at 0x060199FC starts with `rts; nop`
  vf_neither.32x  both
Result (frames 1500, 2400, 2010; runs are deterministic): no stage model = the grey floor band vanishes; no plate = a dark
patch under each fighter's feet vanishes at frames 1500 and 2400 (1,332 and 2,768 of 71,680 pixels), no change at 2010."""
import sys, os
rom = bytearray(open(sys.argv[1], 'rb').read()); out = sys.argv[2]; base = 0x100000
assert rom[base + 0x19ab0:base + 0x19ab4] == bytes([0xe0, 0x01, 0x81, 0xe0]) and rom[base + 0x199fc:base + 0x19a00] == bytes([0xd1, 0x03, 0xe0, 0x01])
for name, plate, stage in (('ctrl', 0, 0), ('noplate', 1, 0), ('nostage', 0, 1), ('neither', 1, 1)):
    b = bytearray(rom)
    if plate: b[base + 0x19ab1] = 0x00
    if stage: b[base + 0x199fc:base + 0x19a00] = bytes([0x00, 0x0b, 0x00, 0x09])
    open(os.path.join(out, 'vf_%s.32x' % name), 'wb').write(b)
