#!/usr/bin/env python3
"""Edit real approved CAR–NYR artwork, preserving actual logos, arena, frame and icons.

This is a faithful dynamic STATISTICS proof for CAR–NYR, not a generic all-NHL
renderer. A different matchup requires original-quality team artwork/assets.
No API requests or fabricated values are made.
"""
import argparse, json
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageFilter
ROOT=Path(__file__).resolve().parent
FONT='/usr/share/fonts/truetype/noto/NotoSansDisplay-CondensedExtraBold.ttf'
if not Path(FONT).exists():FONT='/usr/share/fonts/truetype/dejavu/DejaVuSansCondensed-Bold.ttf'
REG='/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'

def center(draw,x,y,s,sz,fill='white',maxwidth=None,shadow=True):
    s=str(s); f=ImageFont.truetype(FONT,sz)
    if maxwidth:
        while draw.textbbox((0,0),s,font=f)[2]>maxwidth and sz>19:
            sz-=2;f=ImageFont.truetype(FONT,sz)
    bb=draw.textbbox((0,0),s,font=f)
    xy=(int(x-(bb[2]-bb[0])/2),int(y-(bb[3]-bb[1])/2-bb[1]))
    if shadow:draw.text((xy[0]+2,xy[1]+3),s,font=f,fill='#061126',stroke_width=2,stroke_fill='#061126')
    draw.text(xy,s,font=f,fill=fill,stroke_width=1,stroke_fill='#253149')

def replace_numbers(panel,values):
    # Keep the original branded header, logos, left-hand statistic labels, icons,
    # arena lights and metallic row frames. Only data cells are reconstructed.
    img=panel.convert('RGB'); d=ImageDraw.Draw(img)
    # Remove ALL baked-in CAR/NYR numerical cells before placing new values.
    # The original is a flattened JPG, so partial overlay would leave ghost numbers.
    d.rectangle((610,325,1611,870),fill='#061326')
    for row, item in enumerate(values):
        top=[333,520,699][row];bottom=[502,686,861][row]
        red=[(682,top+3),(1140,top+3),(1080,bottom-4),(617,bottom-4)]
        blue=[(1164,top+3),(1601,top+3),(1601,bottom-4),(1102,bottom-4)]
        d.polygon(red,fill='#ad0c22');d.polygon(blue,fill='#0755a7')
        d.line(red[:2],fill='#f73c52',width=5)
        d.line([red[2],red[3]],fill='#ef455b',width=4)
        d.line(blue[:2],fill='#63b6ff',width=5)
        d.line([blue[2],blue[3]],fill='#70b9ff',width=4)
        d.line([(1140,top+3),(1080,bottom-4)],fill='#09172b',width=12)
        d.line([(1164,top+3),(1102,bottom-4)],fill='#09172b',width=12)
        # Metallic horizontal separators connect to original source's left-hand bars.
        d.line([(615,bottom-3),(1604,bottom-3)],fill='#8ca6c7',width=3)
        for x,team,color in [(872,'CAROLINA','#ffedef'),(1363,'NY RANGERS','#e5f4ff')]:
            center(d,x,top+35,team,35,color,maxwidth=355)
        center(d,872,top+101,item['home'],69,maxwidth=390)
        center(d,1363,top+101,item['away'],69,maxwidth=390)
        if item.get('home_detail'):center(d,872,top+145,item['home_detail'],27,maxwidth=375)
        if item.get('away_detail'):center(d,1363,top+145,item['away_detail'],27,maxwidth=375)
    return img

def render(data,out):
    if data.get('home')!='CAR' or data.get('away')!='NYR':
        raise ValueError('Schválená rastrová grafika obsahuje loga CAR–NYR. Jiný zápas vyžaduje nové týmové grafické podklady; nevytvářím falešnou náhradu.')
    vals=data['rows']
    if len(vals)!=3 or any('home' not in r or 'away' not in r for r in vals):
        raise ValueError('Očekávám přesně tři řádky s hodnotami home a away')
    original=Image.open(ROOT/'assets/presilovky_original.jpg').resize((1650,925),Image.Resampling.LANCZOS)
    panel=replace_numbers(original,vals).resize((1019,575),Image.Resampling.LANCZOS)
    frame=Image.open(ROOT/'assets/reference_frame.png').convert('RGB')
    d=ImageDraw.Draw(frame)
    d.rounded_rectangle((26,138,1053,379),radius=29,fill='#030d22')
    center(d,540,182,'BE6PLAYER • NHL 2026/27',37,'#c0cde5',shadow=False)
    center(d,540,280,'PŘESILOVKY A OSLABENÍ',52,maxwidth=945)
    frame.paste(panel,(30,605));d=ImageDraw.Draw(frame)
    d.rectangle((29,604,1050,1181),outline='#edf2fb',width=3)
    d.rounded_rectangle((26,1270,1053,1525),radius=26,fill='#030d22')
    caption=data['caption']
    # Automatic line wrapping with the original commentary typography.
    words=caption.split();lines=[];line=''
    f=ImageFont.truetype(FONT,38)
    for word in words:
        attempt=(line+' '+word).strip()
        if line and d.textbbox((0,0),attempt,font=f)[2]>910:
            lines.append(line);line=word
        else:line=attempt
    if line:lines.append(line)
    if len(lines)>3:raise ValueError('Komentář je pro kartu příliš dlouhý')
    for i,s in enumerate(lines):center(d,540,1393+(i-(len(lines)-1)/2)*53,s,38,maxwidth=930)
    d.rectangle((70,1680,1010,1790),fill='#08172e')
    center(d,540,1730,'05 / 09  •  PŘEDZÁPASOVÉ STATISTIKY',30,'#c5d1e7',shadow=False)
    out=Path(out);out.parent.mkdir(parents=True,exist_ok=True);frame.save(out)
    return out

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--data',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
    a=p.parse_args();print(render(json.loads(a.data.read_text(encoding='utf8')),a.out))
