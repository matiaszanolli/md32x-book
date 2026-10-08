#!/usr/bin/env python3
"""usage: frame2png.py DUMP_DIR OUT.png FRAME [FRAME ...]

Convert frames of the frontend's RGB565 dump (VRD_VIDEO_DUMP_DIR) to one PNG
at full size, side by side, each labelled with its frame number (sheet.py
makes small thumbnails instead). Uses video-frames.csv for the geometry.
"""
import csv, struct, sys
from PIL import Image, ImageDraw

d, out, want = sys.argv[1], sys.argv[2], [int(x) for x in sys.argv[3:]]
rows = {int(r['frame']): r for r in csv.DictReader(open(d + '/video-frames.csv')) if r.get('captured') == '1'}
ims = []
for f in want:
    r = rows[f]
    w, h, p = int(r['width']), int(r['height']), int(r['pitch'])
    raw = open(d + '/' + r['path'].split('/')[-1], 'rb').read()
    px = []
    for y in range(h):
        px += [(((q >> 11) & 31) * 255 // 31, ((q >> 5) & 63) * 255 // 63, (q & 31) * 255 // 31)
               for q in struct.unpack_from('<%dH' % w, raw, y * p)]
    im = Image.new('RGB', (w, h)); im.putdata(px)
    ImageDraw.Draw(im).text((4, h - 12), 'frame %d' % f, fill=(255, 255, 0))
    ims.append(im)
W = sum(i.size[0] for i in ims); H = max(i.size[1] for i in ims)
sheet = Image.new('RGB', (W, H)); x = 0
for im in ims:
    sheet.paste(im, (x, 0)); x += im.size[0]
sheet.save(out); print(out, sheet.size)
