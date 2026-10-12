# Regenerates the input script used for the "played" run: python3 make_inp1.py > inp1.csv
# 5,000 rows (frame,mask). Libretro bits: B 1, Y 2, Select 4, Start 8, Up 16, Down 32, Left 64, Right 128, A 256, X 512.
import random
random.seed(3)
print("frame,mask")
for f in range(5000):
    m = 0
    if 600 <= f < 5000:
        if f % 90 < 4: m = 8
        elif f > 1500:
            if (f // 7) % 3 == 0: m |= random.choice([1, 2, 256, 16, 32, 64, 128])
    print("%d,%d" % (f, m))
