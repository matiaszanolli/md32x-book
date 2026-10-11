"""Repack Mortal Kombat II's ProPack files with the other method, with a modern packer.

usage: python3 -I rnc_repack.py ROM PROPACK_DIR [LIMIT]

PROPACK_DIR is the directory holding the unpacked `propack` wheel (PyPI propack 0.2.0, pure Python,
bibliography PROPACK-PY). For every RNC file in the ROM it
  1. unpacks it with notes/games/mk2/rnc_check.py's decoders (the ones checked against the SH-2 routine),
  2. packs the result again with the file's own method and with the other method,
  3. unpacks each new file with the rnc_check decoder and with propack's, and checks it equals the data.
Sizes are the header's packed-size field, as rnc_check.py prints them (the 18-byte header is not counted).
"""
import sys, os, struct, time, importlib.util
here = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location('rc', os.path.join(here, 'rnc_check.py'))
rc = importlib.util.module_from_spec(spec); spec.loader.exec_module(rc)
sys.path.insert(0, sys.argv[2])
import propack
d = open(sys.argv[1], 'rb').read()
limit = int(sys.argv[3]) if len(sys.argv) > 3 else 10 ** 9

files = []
for m, fn in ((1, rc.unpack1), (2, rc.unpack2)):
    i = d.find(b'RNC' + bytes([m]))
    while i != -1:
        u, pk, ucrc, pcrc = struct.unpack('>IIHH', d[i + 4:i + 16])
        if 0 < u < 1 << 20 and 0 < pk <= u + 64:
            try:
                o = fn(d, i + 18, u)
                if len(o) == u and rc.crc16(o) == ucrc:
                    files.append((m, i, u, pk, o))
            except Exception:
                pass
        i = d.find(b'RNC' + bytes([m]), i + 1)

tot = {}
t0 = time.time()
for n, (m, off, u, pk, data) in enumerate(files[:limit]):
    row = tot.setdefault(m, {'files': 0, 'raw': 0, 'orig': 0, 'same': 0, 'other': 0, 'bad': 0})
    row['files'] += 1; row['raw'] += u; row['orig'] += pk
    for target in (m, 3 - m):
        p = propack.pack(data, method=target)
        h = propack.parse_header(p)
        ok = propack.unpack(p) == data
        # the book's decoders read the same bytes (method 2: the SH-2 routine's format)
        fn = rc.unpack1 if target == 1 else rc.unpack2
        try:
            ok = ok and fn(p, 18, u) == data
        except Exception:
            ok = False
        if not ok: row['bad'] += 1
        row['same' if target == m else 'other'] += h.packed_size
    if n % 10 == 0: print('...', n, 'files, %.0f s' % (time.time() - t0), flush=True)
for m, r in sorted(tot.items()):
    print('method %d files: %d, unpacked %d bytes; original packer %d (%.1f%%); propack method %d %d (%.1f%%); propack method %d %d (%.1f%%); failed round trips %d' %
          (m, r['files'], r['raw'], r['orig'], 100 * r['orig'] / r['raw'], m, r['same'], 100 * r['same'] / r['raw'],
           3 - m, r['other'], 100 * r['other'] / r['raw'], r['bad']))
