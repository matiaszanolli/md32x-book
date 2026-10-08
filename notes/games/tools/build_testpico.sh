#!/bin/sh
# usage: build_testpico.sh WORKDIR
# Builds notaz's testpico (github.com/notaz/megadrive, testpico/) for a console
# and for PicoDrive (-for-pd), with the marsdev toolchain in /opt/toolchains/mars.
# testpico wants sjasm 0.42; marsdev has 0.39j, which lacks its macro syntax, so
# the two macros used (ld_a, save_hvcount) are expanded first.
# Run the result headless with the frontend (see README):
#   frontend WORKDIR/testpico/testpico--for-pd.bin (console build in WORKDIR/hw) 1200 with VRD_VIDEO_DUMP_*
# and read the results screen from the last frame. Bibliography key: TESTPICO.
set -e
W=${1:?usage: $0 WORKDIR}
mkdir -p "$W" && cd "$W"
[ -d megadrive ] || git clone -q https://github.com/notaz/megadrive
rm -rf testpico && cp -r megadrive/testpico testpico && cd testpico
python3 - <<'EOF'
import re
src = open('z80_test.s80').read().split('\n')
out, skip, n = [], False, 0
for l in src:
    s = l.split(';')[0].strip()
    if s.startswith('macro '):
        skip = True; continue
    if skip:
        skip = s != 'endmacro'; continue
    m = re.match(r'\s+ld_a\s+(\S+),\s*(\S+)', l)
    if m:
        out += ['  ld  a, ' + m.group(2), '  ld  %s, a' % m.group(1)]; continue
    m = re.match(r'\s+save_hvcount\s+(\S+)', l)
    if m:
        n += 1
        out += ['  ld  hl, $7f08', 'shv%d' % n, '  ld  a, (hl)', '  cp  a, (hl)',
                '  jp  nz,shv%d' % n, '  ld  (%s), a' % m.group(1)]; continue
    out.append(l)
open('z80_test.s80', 'w').write('\n'.join(out))
EOF
export PATH=/opt/toolchains/mars/m68k-elf/bin:/opt/toolchains/mars/sh-elf/bin:$PATH
make >/dev/null 2>&1
mkdir -p ../hw && mv testpico-*.bin ../hw/
make clean >/dev/null && make PICO=1 >/dev/null 2>&1
ls -la ../hw/testpico-*.bin testpico-*.bin
