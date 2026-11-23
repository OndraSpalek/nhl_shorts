#!/usr/bin/env python3
"""Layered Be6player renderer. Never mislabel logos or invent statistics."""
import argparse,json
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont,ImageFilter
ROOT=Path(__file__).resolve().parent
CODES='ANA BOS BUF CAR CBJ CGY CHI COL DAL DET EDM FLA LAK MIN MTL NJD NSH NYI NYR OTT PHI PIT SEA SJS STL TBL TOR UTA VAN VGK WPG WSH'.split()
NAMES=dict(zip(CODES,['ANAHEIM','BOSTON','BUFFALO','CAROLINA','COLUMBUS','CALGARY','CHICAGO','COLORADO','DALLAS','DETROIT','EDMONTON','FLORIDA','LOS ANGELES','MINNESOTA','MONTRÉAL','NEW JERSEY','NASHVILLE','NY ISLANDERS','NY RANGERS','OTTAWA','PHILADELPHIA','PITTSBURGH','SEATTLE','SAN JOSE','ST. LOUIS','TAMPA BAY','TORONTO','UTAH','VANCOUVER','VEGAS','WINNIPEG','WASHINGTON']))
FONT='/usr/share/fonts/truetype/dejavu/DejaVuSansCondensed-Bold.ttf'
def f(size):return ImageFont.truetype(FONT,size)
def label(d,x,y,s,size=38,fill='white',maxw=None):
    s=str(s);size0=size
    while maxw and d.textbbox((0,0),s,font=f(size))[2]>maxw and size>16:size-=2
    bb=d.textbbox((0,0),s,font=f(size));d.text((x-(bb[2]-bb[0])/2+2,y-(bb[3]-bb[1])/2-bb[1]+3),s,font=f(size),fill='#020915',stroke_width=2,stroke_fill='#020915');d.text((x-(bb[2]-bb[0])/2,y-(bb[3]-bb[1])/2-bb[1]),s,font=f(size),fill=fill,stroke_width=1,stroke_fill='#172337')
def logo_path(code,logos):
    if code in logos:return Path(logos[code]).expanduser().resolve()
    for ext in ('png','webp'):
        p=ROOT/'assets'/'logos'/f'{code}.{ext}'
        if p.is_file():return p
    raise FileNotFoundError(f'Chybí skutečné logo {code}: vložte assets/logos/{code}.png (průhledné PNG) nebo zadejte --logos JSON. Žádná náhradní zkratka se nevykreslí.')
def paste_logo(canvas,path,xy,box=(220,175)):
    if not path.is_file():raise FileNotFoundError(str(path))
    im=Image.open(path).convert('RGBA');im.thumbnail(box,Image.Resampling.LANCZOS)
    canvas.paste(im,(int(xy[0]-im.width/2),int(xy[1]-im.height/2)),im)
def panel(data,logos):
    home,away=data['home'],data['away'];rows=data['rows']
    bg=Image.open(ROOT/'assets/arena.png').convert('RGB').resize((1650,925),Image.Resampling.LANCZOS).convert('RGBA')
    d=ImageDraw.Draw(bg,'RGBA')
    # Vivid sports broadcast header: luminous beveled bands and angled red headline.
    d.polygon([(0,80),(805,80),(760,185),(0,185)],fill=(77,5,17,220))
    d.polygon([(850,80),(1650,80),(1650,185),(900,185)],fill=(5,27,83,225))
    d.polygon([(345,198),(1330,198),(1280,311),(296,311)],fill=(163,3,22,242))
    d.line([(345,198),(1330,198)],fill='#ff7381',width=6)
    d.line([(296,311),(1280,311)],fill='#ff5d69',width=5)
    label(d,825,252,data.get('title','PŘESILOVKY A OSLABENÍ'),76,maxw=915)
    label(d,550,130,NAMES[home],62,maxw=430);label(d,1090,130,NAMES[away],62,maxw=430)
    label(d,820,140,'VS.',43)
    for i,r in enumerate(rows):
        y=340+i*174
        # Metallic rim, separate black category cell, bevelled red and blue trapezoids.
        d.rounded_rectangle((42,y,1608,y+160),radius=24,fill=(3,12,29,244),outline='#b4c4d7',width=5)
        d.polygon([(610,y+5),(1128,y+5),(1054,y+155),(610,y+155)],fill='#aa071d')
        d.polygon([(1164,y+5),(1600,y+5),(1600,y+155),(1092,y+155)],fill='#0751a0')
        d.line([(615,y+9),(1120,y+9)],fill='#fa5164',width=5)
        d.line([(1168,y+9),(1593,y+9)],fill='#75c8ff',width=5)
        d.line([(1055,y+153),(1092,y+5)],fill='#06132b',width=10)
        label(d,320,y+78,r['label'],39,maxw=475)
        label(d,870,y+50,NAMES[home],32,maxw=340);label(d,1345,y+50,NAMES[away],32,maxw=340)
        label(d,868,y+105,r['home'],64,maxw=345);label(d,1345,y+105,r['away'],64,maxw=345)
        if r.get('home_detail'):label(d,870,y+142,r['home_detail'],24,maxw=330)
        if r.get('away_detail'):label(d,1345,y+142,r['away_detail'],24,maxw=330)
    # Logos above header, with no hidden team substitution.
    paste_logo(bg,logo_path(home,logos),(150,130),(245,205))
    paste_logo(bg,logo_path(away,logos),(1495,130),(245,205))
    return bg.convert('RGB')
def render(data,out,logos=None):
    logos=logos or {};home=data['home'];away=data['away']
    if home not in CODES or away not in CODES or home==away:raise ValueError('Neplatná dvojice NHL')
    if len(data.get('rows',[]))!=3:raise ValueError('Jsou nutné přesně tři statistické řádky')
    for r in data['rows']:
        if not all(k in r and str(r[k]).strip() for k in ('label','home','away')):raise ValueError('Chybí štítek nebo statistika; hodnoty se nesmí domýšlet')
    # Resolve all logos before producing any output.
    logo_path(home,logos);logo_path(away,logos)
    p=panel(data,logos).resize((1019,575),Image.Resampling.LANCZOS)
    frame=Image.open(ROOT/'assets/frame.png').convert('RGB');d=ImageDraw.Draw(frame)
    d.rounded_rectangle((26,138,1053,379),radius=29,fill='#030d22')
    label(d,540,182,'BE6PLAYER • NHL 2026/27',37,'#c0cde5')
    label(d,540,280,data.get('title','PŘESILOVKY A OSLABENÍ'),50,maxw=940)
    frame.paste(p,(30,605));d=ImageDraw.Draw(frame)
    d.rectangle((29,604,1050,1181),outline='#edf2fb',width=3)
    d.rounded_rectangle((26,1270,1053,1525),radius=26,fill='#030d22')
    caption=data.get('caption','');words=caption.split();lines=[];line=''
    for word in words:
        candidate=(line+' '+word).strip()
        if line and d.textbbox((0,0),candidate,font=f(38))[2]>920:lines.append(line);line=word
        else:line=candidate
    if line:lines.append(line)
    if len(lines)>3:raise ValueError('Komentář je příliš dlouhý')
    for i,s in enumerate(lines):label(d,540,int(1393+(i-(len(lines)-1)/2)*53),s,38,maxw=920)
    d.rectangle((70,1680,1010,1790),fill='#08172e')
    label(d,540,1730,'BE6PLAYER  •  PŘEDZÁPASOVÉ STATISTIKY',30,'#c5d1e7')
    out=Path(out);out.parent.mkdir(parents=True,exist_ok=True);frame.save(out)
    return out
if __name__=='__main__':
    a=argparse.ArgumentParser();a.add_argument('--data',required=True);a.add_argument('--out',required=True);a.add_argument('--logos',help='JSON mapping code to real PNG path');args=a.parse_args()
    logos=json.loads(Path(args.logos).read_text(encoding='utf8')) if args.logos else {}
    print(render(json.loads(Path(args.data).read_text(encoding='utf8')),args.out,logos))
