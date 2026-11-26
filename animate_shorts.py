"""Approved V7.1 reveal, crossfade and entrance light sweep."""
from PIL import Image, ImageDraw, ImageFilter, ImageChops
import subprocess
import math
from shorts_highlight import pulse
from pathlib import Path

FPS=24

def regions(advanced):
    rows=[774,873,974,1075,1174,1263,1353,1444] if advanced else [772,873,978,1080,1182,1281,1383]
    return ([(x-115,375,x+115,605,.05,.65) for x in (220,860)] +
            [(x-140,y-32,x+140,y+32,.65+j*.15,.32) for j,y in enumerate(rows) for x in (220,860)] + [(90,1530,990,1710,2.05,.45)])

def frame(final,clean,rr,u,previous=None):
    if u>=2.6: return final
    im=clean.copy()
    for x,y,X,Y,start,dur in rr:
        a=max(0,min(1,(u-start)/dur));a=a*a*(3-2*a)
        if a: im.paste(Image.blend(clean.crop((x,y,X,Y)),final.crop((x,y,X,Y)),a),(x,y))
    if previous is not None and u<.45: im=Image.blend(previous,im,u/.45)
    if u<.7:
        glow=Image.new('RGB',im.size);d=ImageDraw.Draw(glow);xx=int(-250+1600*u/.7)
        d.polygon([(xx-80,0),(xx+20,0),(xx+350,1920),(xx+250,1920)],fill=(28,37,48))
        im=ImageChops.add(im,glow.filter(ImageFilter.GaussianBlur(45)))
    return im

def encode(slides,root,music,out,frames_per_card,highlights=None):
    bases=[Image.open(Path(root)/'assets'/name).convert('RGB') for name in ('arena_v692.png','arena_v701.png')]
    cmd=['ffmpeg','-y','-loglevel','error','-f','rawvideo','-pix_fmt','rgb24','-s','1080x1920','-r',str(FPS),'-i','-','-i',str(music),'-c:v','libx264','-preset','fast','-crf','20','-pix_fmt','yuv420p','-c:a','aac','-b:a','128k','-movflags','+faststart','-shortest',str(out)]
    p=subprocess.Popen(cmd,stdin=subprocess.PIPE)
    previous=None
    try:
        for i,path in enumerate(slides):
            with Image.open(path) as src: final=src.convert('RGB')
            advanced=path.stem.endswith("_advanced")
            player=path.stem.endswith("_players")
            rr=regions(advanced) if not player else [(25,798+j*195,1055,950+j*195,.3+j*.25,.4) for j in range(4)]+[(40,1630,1040,1760,1.5,.4)]
            clean=final.copy();base=bases[int(advanced)]
            if player:
                base=final.copy();d=ImageDraw.Draw(base)
                for x,y,X,Y,_,_ in rr:d.rectangle((x,y,X,Y),fill="#091321")
            for x,y,X,Y,_,_ in rr: clean.paste(base.crop((x,y,X,Y)),(x,y))
            # Short slates compress the reveal to preserve at least two thirds for reading.
            speed=max(1,2.6/(frames_per_card/FPS/3))
            final_bytes=final.tobytes()
            items=(highlights or {}).get(path.name,[])
            for n in range(frames_per_card):
                u=n/FPS*speed
                elapsed=n/FPS-2.6/speed
                if items and 0<=elapsed<1.2:
                    p.stdin.write(pulse(final,items,math.sin(math.pi*elapsed/1.2)).tobytes())
                else:
                    p.stdin.write(final_bytes if u>=2.6 else frame(final,clean,rr,u,previous).tobytes())
            previous=final
        p.stdin.close()
        if p.wait(): raise RuntimeError('FFmpeg animation failed')
    except BaseException:
        p.kill();p.wait();raise
