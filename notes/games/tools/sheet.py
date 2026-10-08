# usage: python3 sheet.py DUMP_DIR OUT.png [COLUMNS]
# Contact sheet of the frontend's RGB565 frame dumps (VRD_VIDEO_DUMP_DIR),
# using video-frames.csv for each frame's geometry, labelled with frame numbers.
import sys,csv,struct
from PIL import Image, ImageDraw
d=sys.argv[1]; out=sys.argv[2]; cols=int(sys.argv[3]) if len(sys.argv)>3 else 8
ims=[]
for r in csv.DictReader(open(d+'/video-frames.csv')):
    if r.get('captured')!='1': continue
    w,h,p=int(r['width']),int(r['height']),int(r['pitch'])
    raw=open(d+'/'+r['path'].split('/')[-1],'rb').read()
    px=[]
    for y in range(h):
        px+=[(((q>>11)&31)*255//31,((q>>5)&63)*255//63,(q&31)*255//31) for q in struct.unpack_from('<%dH'%w,raw,y*p)]
    im=Image.new('RGB',(w,h)); im.putdata(px)
    ImageDraw.Draw(im).text((4,4),r['frame'],fill=(255,255,0))
    ims.append(im.resize((160,112)))
rows=(len(ims)+cols-1)//cols
sh=Image.new('RGB',(160*cols,112*max(rows,1)))
for i,im in enumerate(ims): sh.paste(im,((i%cols)*160,(i//cols)*112))
sh.save(out); print(len(ims),'frames',sh.size)
