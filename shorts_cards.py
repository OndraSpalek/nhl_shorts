#!/usr/bin/env python3
"""1080x1920 PNG cards matching original Be6player CAR-NYR video composition.
Header dark capsule, central red/blue match panel, lower commentary capsule, footer.
"""
import argparse,json,textwrap
from pathlib import Path
from datetime import datetime
from PIL import Image,ImageDraw,ImageFont,ImageFilter
W,H=1080,1920
FONT='/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'
BOLD='/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'
def font(n,bold=False):return ImageFont.truetype(BOLD if bold else FONT,n)
def centered(d,xy,text,ft,fill):
    box=d.textbbox((0,0),text,font=ft);d.text((xy[0]-(box[2]-box[0])/2,xy[1]),text,font=ft,fill=fill)
def rounded(d,box,r,fill):d.rounded_rectangle(box,radius=r,fill=fill)
def lines(d,text,top,width,ft,fill,spacing=12,maxlines=3):
    words=text.split();rows=[];line=''
    for word in words:
        test=(line+' '+word).strip()
        if d.textbbox((0,0),test,font=ft)[2]>width and line:
            rows.append(line);line=word
        else:line=test
    if line:rows.append(line)
    for i,line in enumerate(rows[:maxlines]):centered(d,(W//2,top+i*(ft.size+spacing)),line,ft,fill)
def draw_card(g,index,total,path):
    # Reuse visual architecture of the actual prototype, not generated alternative artwork.
    img=Image.new('RGB',(W,H));px=img.load()
    for y in range(H):
        for x in range(W):
            shade=int(6+14*(1-abs(y-H/2)/(H/2))+9*(1-abs(x-W/2)/(W/2)))
            px[x,y]=(shade,shade+10,shade+28)
    layer=Image.new('RGBA',(W,H),(0,0,0,0));ld=ImageDraw.Draw(layer)
    ld.ellipse((-350,290,500,1200),fill=(180,24,44,85));ld.ellipse((620,290,1450,1200),fill=(18,70,180,95))
    layer=layer.filter(ImageFilter.GaussianBlur(120));img=Image.alpha_composite(img.convert('RGBA'),layer)
    d=ImageDraw.Draw(img)
    rounded(d,(30,160,1050,430),32,(3,13,33,245))
    centered(d,(W//2,194),'BE6PLAYER  •  NHL SHORTS',font(37),(191,203,226))
    centered(d,(W//2,270),'ZÁPASY DNES',font(62,True),'white')
    # central red/blue panel
    d.rounded_rectangle((28,580,1052,1230),radius=12,fill=(5,16,39),outline=(211,222,244),width=4)
    d.polygon([(32,584),(520,584),(400,1226),(32,1226)],fill=(85,14,31))
    d.polygon([(550,584),(1048,584),(1048,1226),(675,1226)],fill=(10,42,98))
    centered(d,(W//2,615),'NHL  •  PŘEDZÁPASOVÉ STATISTIKY',font(29,True),'white')
    home,away=g['home'],g['away']
    centered(d,(280,755),home['abbrev'],font(110,True),'white')
    centered(d,(800,755),away['abbrev'],font(110,True),'white')
    centered(d,(540,805),'VS.',font(43,True),(225,227,238))
    dt=datetime.fromisoformat(g['start_prague'])
    centered(d,(W//2,915),dt.strftime('%d.%m.  %H:%M')+'  PRAHA',font(37,True),'white')
    centered(d,(W//2,1000),'SEZONA  •  POSTAVENÍ V KONFERENCI',font(24,True),(194,205,228))
    for x,t in [(275,home),(805,away)]:
        rec='–'.join(str(t.get(k)) if t.get(k) is not None else '?' for k in ('wins','losses','ot_losses'))
        centered(d,(x,1065),rec,font(37,True),'white')
        rank=t.get('conference_rank');centered(d,(x,1125),f"{rank}. MÍSTO" if rank else 'POŘADÍ NEDOSTUPNÉ',font(23),(207,219,237))
    rounded(d,(30,1330,1050,1585),28,(3,13,33,245))
    centered(d,(W//2,1365),'ZAJÍMAVOST ZÁPASU',font(29,True),(248,194,121))
    lines(d,g['featured_fact']['text'],1430,910,font(39,True),'white',12,3)
    centered(d,(W//2,1760),f'{index:02d} / {total:02d}   •   PŘEDZÁPASOVÉ STATISTIKY',font(28),(187,198,218))
    img.convert('RGB').save(path,quality=94)
def main():
    p=argparse.ArgumentParser();p.add_argument('--input',type=Path,required=True);p.add_argument('--outdir',type=Path,default=Path('shorts_cards'));a=p.parse_args()
    data=json.loads(a.input.read_text(encoding='utf-8'));a.outdir.mkdir(parents=True,exist_ok=True)
    for i,g in enumerate(data['games'],1):draw_card(g,i,len(data['games']),a.outdir/f'game_{i:02d}.png')
    print(f"Vykresleno {len(data['games'])} karet do {a.outdir}")
if __name__=='__main__':main()
