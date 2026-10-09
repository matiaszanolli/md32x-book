#!/usr/bin/env python3
"""Decode every ProPack (RNC) file in a ROM and check it against its header.

usage: rnc_check.py ROM

Method 2 follows Mortal Kombat II's SH-2 unpacker (0x06002DF4-0x06002F84):
flags and codes MSB first from a byte-wide bit buffer, the first two bits
skipped, literal blocks of (4-bit count + 3) * 4 bytes.  Method 1 is the usual
Huffman variant: LSB first from little-endian 16-bit words, three code tables
per chunk.  Each output is checked for the header's unpacked size and CRC-16
(poly 0xA001, the CRC ProPack stores at header offset 12).
"""
import struct, sys

def crc16(data):
    c = 0
    for b in data:
        c ^= b
        for _ in range(8):
            c = (c >> 1) ^ 0xA001 if c & 1 else c >> 1
    return c

def unpack2(d, p, size):
    out = bytearray()
    st = {'p': p, 'buf': d[p] << 2 & 0xFF, 'n': 6}
    st['p'] += 1
    def bit():
        if st['n'] == 0:
            st['buf'] = d[st['p']]; st['p'] += 1; st['n'] = 8
        st['n'] -= 1
        b = st['buf'] >> 7 & 1
        st['buf'] = st['buf'] << 1 & 0xFF
        return b
    def byte():
        v = d[st['p']]; st['p'] += 1; return v
    def offset():
        hi = 0
        if bit():
            hi = bit()
            if bit():
                hi = (hi << 1 | bit()) | 4
                if not bit():
                    hi = hi << 1 | bit()
            elif hi == 0:
                hi = 2 | bit()
        return (hi << 8 | byte()) + 1
    def copy(n, dist):
        for _ in range(n):
            out.append(out[-dist])
    while True:
        if not bit():
            out.append(byte()); continue
        if not bit():
            n = 4 + bit()
            if bit():
                n = ((n - 1) << 1) + bit()
            if n == 9:
                cnt = 0
                for _ in range(4):
                    cnt = cnt << 1 | bit()
                for _ in range((cnt + 3) * 4):
                    out.append(byte())
                continue
            copy(n, offset()); continue
        if not bit():
            copy(2, byte() + 1); continue
        if not bit():
            copy(3, offset()); continue
        n = byte()
        if n == 0:
            if not bit():
                break
            continue
        copy(n + 8, offset())
    return bytes(out)

def unpack1(d, p, size):
    out = bytearray()
    lw = lambda q: d[q] | d[q + 1] << 8 if q + 1 < len(d) else 0
    st = {'p': p, 'buf': lw(p), 'cnt': 16}
    def advance(n):
        st['buf'] >>= n; st['cnt'] -= n
        if st['cnt'] < 16:
            st['p'] += 2
            st['buf'] |= lw(st['p']) << st['cnt']; st['cnt'] += 16
    def read(n):
        v = st['buf'] & ((1 << n) - 1); advance(n); return v
    def fix():
        st['cnt'] -= 16
        st['buf'] &= (1 << st['cnt']) - 1
        st['buf'] |= lw(st['p']) << st['cnt']; st['cnt'] += 16
    def table():
        num = read(5)
        lens = [read(4) for _ in range(num)]
        t = []; code = 0
        for ln in range(1, 17):
            for v, l in enumerate(lens):
                if l == ln:
                    t.append((int(format(code, '0%db' % ln)[::-1], 2), ln, v)); code += 1
            code <<= 1
        return t
    def huf(t):
        for code, ln, v in t:
            if st['buf'] & ((1 << ln) - 1) == code:
                advance(ln)
                if v >= 2:
                    v = (1 << (v - 1)) | read(v - 1)
                return v
        raise ValueError('bad code')
    advance(2)
    while len(out) < size:
        raw, dist, ln = table(), table(), table()
        items = read(16)
        while True:
            n = huf(raw)
            if n:
                out += d[st['p']:st['p'] + n]; st['p'] += n; fix()
            items -= 1
            if items <= 0:
                break
            pos = huf(dist) + 1
            for _ in range(huf(ln) + 2):
                out.append(out[-pos])
    return bytes(out)

def main(path):
    d = open(path, 'rb').read()
    for m, fn in ((1, unpack1), (2, unpack2)):
        sig = b'RNC' + bytes([m]); i = d.find(sig); ok = bad = 0; tu = tp = 0
        while i != -1:
            u, pk, ucrc, pcrc = struct.unpack('>IIHH', d[i + 4:i + 16])
            if 0 < u < 1 << 20 and 0 < pk <= u + 64:
                try:
                    o = fn(d, i + 18, u)
                    good = len(o) == u and crc16(o) == ucrc
                except Exception:
                    good = False
                ok += good; bad += not good; tu += u; tp += pk
                if not good:
                    print('  FAIL method %d at $%06X' % (m, i))
            i = d.find(sig, i + 1)
        print('method %d: %d files decode to the header size and CRC, %d fail; '
              '%d bytes unpacked, %d packed (%.1f%%)' % (m, ok, bad, tu, tp, 100.0 * tp / tu))

if __name__ == '__main__':
    main(sys.argv[1])
