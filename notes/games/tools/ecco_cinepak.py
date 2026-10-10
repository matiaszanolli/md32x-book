"""Reads the ECCO CinePak demo's movie and decodes it from the stream alone, with Sega's colour
conversion and with the usual one, to compare with the SH-2 run (eccosim.py) and with ffmpeg.

usage: python3 -I ecco_cinepak.py ROM [STAGING.bin [FFMPEG.rgb]]

  ROM          the ECCO dump (3,145,728 bytes, MD5 c2b642fd...)
  STAGING.bin  eccosim.py's staging.bin: compared bit for bit with the "sega" decode
  FFMPEG.rgb   `ffmpeg -i movie.film -map 0:v -f rawvideo -pix_fmt rgb24 FFMPEG.rgb`, where
               movie.film is ROM bytes $20000.. (header $B84 + 2,183,040 bytes); compared with the
               "usual" decode

Prints the container and chunk statistics, then the comparisons. Written from the format as
Ferguson describes it (bibliography CINEPAK-TD), not from the SH-2 code, so a match with the SH-2
run checks both.
"""
import struct, sys
import numpy as np

rom = open(sys.argv[1], 'rb').read()
base = 0x20000
assert rom[base:base + 4] == b'FILM'
hdr_len = struct.unpack('>I', rom[base + 4:base + 8])[0]
fdsc = base + 16
fdsc_len = struct.unpack('>I', rom[fdsc + 4:fdsc + 8])[0]
stab = fdsc + fdsc_len
freq, count = struct.unpack('>II', rom[stab + 8:stab + 16])
E = [struct.unpack('>IIII', rom[stab + 16 + i * 16:stab + 32 + i * 16]) for i in range(count)]
data = base + hdr_len                      # sample offsets count from the end of the header


def s8(b): return b - 256 if b > 127 else b
def clamp(x): return max(0, min(255, x))


def chunks(k):
    """-> (codebook chunk length, vector bytes, raw 256 codebook entries as the SH-2 reads them)"""
    off, ln = E[k][0], E[k][1]
    s = rom[data + off:data + off + ln]
    q = 16 + 12                             # 16-byte sample header, 12-byte strip header
    cb, vec = 0, b""
    while q < ln:
        cid, clen = struct.unpack('>HH', s[q:q + 4])
        if cid == 0x2000: cb = clen
        if cid == 0x3000: vec = s[q + 4:q + clen]
        q += clen
    # the SH-2 converts 256 entries whatever the chunk holds, reading on past it
    raw = rom[data + off + 16 + 12 + 4:data + off + 16 + 12 + 4 + 6 * 256]
    return cb, vec, raw


GREEN = {
    'sega':  lambda y, u, v: y - (u + (v >> 1)),     # what the ECCO code computes
    'usual': lambda y, u, v: y - int(u / 2) - v,     # Ferguson; matches ffmpeg exactly
}


def decode(k, which):
    vec, raw = chunks(k)[1:]
    g = GREEN[which]
    book = []
    for i in range(256):
        e = raw[i * 6:i * 6 + 6]
        u, v = s8(e[4]), s8(e[5])
        book.append([(clamp(y + 2 * v) >> 3, clamp(g(y, u, v)) >> 3, clamp(y + 2 * u) >> 3) for y in e[:4]])
    img = np.zeros((160, 256, 3), np.uint8)
    pos = flags = left = 0
    for by in range(40):
        for bx in range(64):
            if left == 0:
                flags = struct.unpack('>I', vec[pos:pos + 4])[0]; pos += 4; left = 32
            bit = flags >> 31; flags = (flags << 1) & 0xFFFFFFFF; left -= 1
            if not bit:
                raise Exception('V1 block in picture %d' % k)
            for qi, i in enumerate(vec[pos:pos + 4]):
                qy, qx = divmod(qi, 2)
                for pi, px in enumerate(book[i]):
                    py, pxx = divmod(pi, 2)
                    img[by * 4 + qy * 2 + py, bx * 4 + qx * 2 + pxx] = px
            pos += 4
    return img, pos, len(vec)


# container and chunk statistics ----------------------------------------------------------
print('FILM header %#x bytes, FDSC %d bytes, STAB %d ticks/s, %d samples' % (hdr_len, fdsc_len, freq, count))
print('audio-marked samples (info 1 = 0xFFFFFFFF):', sum(1 for e in E if e[2] == 0xFFFFFFFF))
print('samples contiguous:', all(E[i][0] + E[i][1] == E[i + 1][0] for i in range(count - 1)))
print('ticks per sample:', sorted({E[i + 1][2] - E[i][2] for i in range(count - 1)}), '(info 2:', sorted({e[3] for e in E}), ')')
sizes = [e[1] for e in E]
print('sample bytes: min %d max %d mean %.1f total %d' % (min(sizes), max(sizes), sum(sizes) / count, sum(sizes)))
print('bits per pixel: %.3f' % (sum(sizes) * 8 / count / (256 * 160)))
ents = [(chunks(k)[0] - 4) // 6 for k in range(count)]
print('V4 codebook entries in the chunk: min %d, 256 in %d pictures' % (min(ents), ents.count(256)))
v1 = 0
used = []
for k in range(count):
    cb, vec, raw = chunks(k)
    pos = flags = left = 0
    idx = set()
    for b in range(2560):
        if left == 0:
            flags = struct.unpack('>I', vec[pos:pos + 4])[0]; pos += 4; left = 32
        bit = flags >> 31; flags = (flags << 1) & 0xFFFFFFFF; left -= 1
        if bit:
            idx.update(vec[pos:pos + 4]); pos += 4
        else:
            v1 += 1; pos += 1
    used.append(len(idx))
print('V1 blocks in all pictures:', v1, '; codebook entries used per picture: min %d mean %.1f max %d' % (min(used), sum(used) / count, max(used)))

# comparisons -----------------------------------------------------------------------------
if len(sys.argv) > 2:
    st = np.fromfile(sys.argv[2], dtype='>u2').reshape(-1, 160, 256).astype(np.int32)
    S5 = np.stack([st & 31, (st >> 5) & 31, (st >> 10) & 31], -1)
    ok = sum(1 for k in range(min(count, len(S5))) if (decode(k, 'sega')[0] == S5[k]).all())
    print('sega-formula decode equals the SH-2 run in %d of %d pictures' % (ok, min(count, len(S5))))
if len(sys.argv) > 3:
    F = np.fromfile(sys.argv[3], dtype=np.uint8).reshape(count, 160, 256, 3).astype(np.int32)
    for which in ('usual', 'sega'):
        ex = np.zeros(3); n = 0
        for k in range(0, count, 15):
            a = decode(k, which)[0].astype(np.int32)
            ex += (a == (F[k] >> 3)).reshape(-1, 3).mean(0); n += 1
        print('%-5s decode vs ffmpeg, share of 5-bit channel values equal (R, G, B): %s' % (which, (ex / n).round(4)))
