#!/usr/bin/env python3
"""Be6player V6.9.2: approved layout, dynamic teams and statistics."""
import argparse,json
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
ROOT=Path(__file__).resolve().parent
FONT='/usr/share/fonts/truetype/dejavu/DejaVuSansCondensed-Bold.ttf'
def font(sz):return ImageFont.truetype(FONT,sz)
def txt(d,s,xy,sz,width,stroke=2):
    s=str(s); f=font(sz)
    while d.textlength(s,font=f)>width and sz>12:
        sz-=1;f=font(sz)
    d.text(xy,s,font=f,fill='white',anchor='mm',stroke_width=stroke,stroke_fill='#07101e')
def render(data,dest):
    for key in ('home','away','rows','caption'):
        if key not in data:raise ValueError('Chybí '+key)
    if len(data['rows'])!=7:raise ValueError('Šablona má přesně 7 řádků')
    for row in data['rows']:
        for k in ('label','home','away'):
            if k not in row or not str(row[k]).strip():raise ValueError('Chybí údaj '+k)
    with Image.open(ROOT/'assets/arena_v692.png') as src:im=src.convert('RGB')
    d=ImageDraw.Draw(im)
    for side,x in [('home',220),('away',860)]:
        code=data[side];p=ROOT/'assets/logos'/f'{code}.png'
        if p.exists():
            with Image.open(p) as src:logo=src.convert('RGBA')
            bbox=logo.getchannel('A').getbbox()
            if not bbox:raise ValueError('Prázdné logo '+code)
            logo=logo.crop(bbox);logo.thumbnail((195,195),Image.Resampling.LANCZOS)
            im.paste(logo,(round(x-logo.width/2),round(490-logo.height/2)),logo)
        else:txt(d,'BEZ LOGA',(x,490),32,190)
        txt(d,code,(x,646),46,230)
    for y,r in zip([772,873,978,1080,1182,1281,1383],data['rows']):
        txt(d,r['home'],(220,y),48,275);txt(d,r['away'],(860,y),48,275)
    words=str(data['caption']).split();lines=[];line=''
    for w in words:
        attempt=(line+' '+w).strip()
        if line and d.textlength(attempt,font=font(34))>850:lines.append(line);line=w
        else:line=attempt
    if line:lines.append(line)
    if len(lines)>3:raise ValueError('Příliš dlouhý komentář')
    for i,line in enumerate(lines):txt(d,line,(540,1600+(i-(len(lines)-1)/2)*38),34,870)
    txt(d,data.get('source_label','NHL API • PŘEDZÁPASOVÁ DATA'),(540,1841),27,850)
    dest=Path(dest);dest.parent.mkdir(parents=True,exist_ok=True);im.save(dest);return dest
if __name__=='__main__':
    a=argparse.ArgumentParser();a.add_argument('--data',required=True);a.add_argument('--out',required=True);v=a.parse_args();print(render(json.loads(Path(v.data).read_text(encoding='utf-8')),v.out))
