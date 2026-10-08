# usage: python3 render32x.py DEBUG_OUT PREFIX
# Renders 32X frame-buffer dumps from the frontend's --debug-script output.
# The script must read the bitmap mode register (0x20004100), the palette
# (0x20004200, 512 bytes) and the frame buffer (0x24000000, 4096 bytes per
# read) after each "status". Packed-pixel mode only. Writes PREFIX_<frame>.png
# and PREFIX_all.png (picture beside a mask of pixels whose colour has the
# through bit), and prints the line table and palette summary.
import re,struct,sys
from PIL import Image
src,prefix=sys.argv[1],sys.argv[2]
txt=open(src).read().split('Session frame: ')[1:]
imgs=[]
for blk in txt:
    fr=int(blk.split()[0])
    mem={}
    for m in re.finditer(r'^([0-9A-F]{8}):((?: [0-9A-F]{2})+)',blk,re.M):
        a=int(m.group(1),16)
        for i,b in enumerate(m.group(2).split()): mem[a+i]=int(b,16)
    if 0x20004200 not in mem: continue
    pal=[(mem[0x20004200+2*i]<<8)|mem[0x20004201+2*i] for i in range(256)]
    mode=(mem.get(0x20004100,0)<<8)|mem.get(0x20004101,0)
    fb=bytes(mem.get(0x24000000+i,0) for i in range(0x20000))
    lt=struct.unpack('>256H',fb[:512])
    im=Image.new('RGB',(320,224)); thr=Image.new('L',(320,224))
    used=set()
    for y in range(224):
        base=lt[y]*2
        for x in range(320):
            c=fb[base+x] if base+x<len(fb) else 0; used.add(c)
            p=pal[c]
            im.putpixel((x,y),((p&31)*8,((p>>5)&31)*8,((p>>10)&31)*8))
            thr.putpixel((x,y),255 if p&0x8000 else 0)
    print(fr,'mode %04x'%mode,'line0 %04x line1 %04x line223 %04x'%(lt[0],lt[1],lt[223]),
          'colours used',len(used),'pal0 %04x'%pal[0],'through entries',sum(1 for p in pal if p&0x8000))
    im.save('%s_%d.png'%(prefix,fr)); imgs.append((im,thr))
if imgs:
    W=Image.new('RGB',(640,224*len(imgs)))
    for i,(im,thr) in enumerate(imgs):
        W.paste(im,(0,224*i)); W.paste(thr.convert('RGB'),(320,224*i))
    W.save(prefix+'_all.png')
