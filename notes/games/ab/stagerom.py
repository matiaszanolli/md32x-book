# usage: python3 stagerom.py ROM OUT STAGE
# Scratch copy of After Burner Complete that starts the game at STAGE (1-23):
# entry 0 of the stage descriptor table at $3D802 (23 longs) is replaced by
# entry STAGE-1, so input.py's play reaches that stage's script first.
# The header checksum is left alone (the game does not check it in PicoDrive).
import sys
d = bytearray(open(sys.argv[1], 'rb').read()); s = int(sys.argv[3])
d[0x3D802:0x3D806] = d[0x3D802 + 4 * (s - 1):0x3D806 + 4 * (s - 1)]
open(sys.argv[2], 'wb').write(d)
