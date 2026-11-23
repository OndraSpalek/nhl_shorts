#!/usr/bin/env python3
"""Be6player V6.4: cinematic layered sample cards; never fabricates official crests."""
import json,argparse
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont,ImageFilter
ROOT=Path(__file__).parent
FONT='/usr/share/fonts/truetype/dejavu/DejaVuSansCondensed-Bold.ttf'
FONT2='/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'

def font(sz,bold=True):return ImageFont.truetype(FONT if bold else FONT2,sz)
def txt(d,s,xy,sz=45,fill='#fff',width=None,stroke=2):
 s=str(s); f=font(sz)
 while width and d.textbbox((0,0),s,font=f)[2]>width and sz>17:
  sz-=1;f=font(sz)
 d.text(xy,s,font=f,fill=fill,anchor='mm',stroke_width=stroke,stroke_fill='#06101f')
def render(data,dest):
 for key in ['home','away','title','rows','caption']:
  if key not in data:raise ValueError('Chybí '+key)
 if len(data['rows'])!=7:raise ValueError('Šablona má přesně 7 řádků')
 for row in data['rows']:
  for k in ['label','home','away']:
   if k not in row or not str(row[k]).strip():raise ValueError('Chybí údaj '+k)
 im=Image.open(ROOT/'assets/arena_master.png').convert('RGB').resize((1080,1920),Image.Resampling.LANCZOS)
 d=ImageDraw.Draw(im)
 txt(d,'BE6PLAYER  |  NHL SHORTS',(540,94),52,width=740)
 txt(d,data['title'],(540,160),38,fill='#f5d7d7',width=650)
 # team logos only when genuinely supplied. Otherwise explicit typography, not fake crest.
 for code,x in [(data['home'],205),(data['away'],875)]:
  p=ROOT/'assets/logos'/f'{code}.png'
  if p.exists():
   logo=Image.open(p).convert('RGBA');logo.thumbnail((245,235),Image.Resampling.LANCZOS)
   # keep crest inside existing metallic side shields
   im.paste(logo,(int(x-logo.width/2),int(475-logo.height/2)),logo)
  else:
   txt(d,code,(x,460),104,width=240)
   txt(d,'BEZ LOGA',(x,525),22,fill='#f5c4c4')
 txt(d,data.get('home_name',data['home']),(215,643),39,width=300)
 txt(d,data.get('away_name',data['away']),(860,643),39,width=300)
 txt(d,'VS',(540,515),49,fill='#12243c',stroke=0)
 # seven metallic bars, middle icon must remain unobscured
 centers=[724,823,923,1021,1120,1219,1318]
 for y,r in zip(centers,data['rows']):
  txt(d,r['home'],(216,y),46,width=275)
  txt(d,r['away'],(860,y),46,width=275)
  # stat name in black center column beneath silver icon, tight sizing
  txt(d,r['label'],(539,y+29),22,fill='#eaf4ff',width=245,stroke=2)
 txt(d,'ZÁPASOVÉ SROVNÁNÍ',(540,1414),36,fill='#d5eaff',width=600)
 words=data['caption'].split();lines=[];line=''
 for w in words:
  attempt=(line+' '+w).strip()
  if line and d.textbbox((0,0),attempt,font=font(36))[2]>860:
   lines.append(line);line=w
  else:line=attempt
 if line:lines.append(line)
 if len(lines)>3:raise ValueError('Příliš dlouhý komentář')
 for i,line in enumerate(lines):txt(d,line,(540,1514+i*48),36,width=880)
 txt(d,data.get('source_label','STATISTIKY NHL • PŘED ZÁPASEM'),(540,1803),27,fill='#edf4ff',width=850)
 dest=Path(dest);dest.parent.mkdir(parents=True,exist_ok=True);im.save(dest)
 return dest
if __name__=='__main__':
 a=argparse.ArgumentParser();a.add_argument('--data',required=True);a.add_argument('--out',required=True);v=a.parse_args();print(render(json.loads(Path(v.data).read_text(encoding='utf-8')),v.out))
