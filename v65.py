#!/usr/bin/env python3
"""V6.5: cinematic NHL video, music only. No voice code or YouTube publishing."""
import argparse,json,math,subprocess,tempfile,wave,array,shutil
from pathlib import Path
from datetime import datetime
from render import render,ROOT
from render_advanced import render_advanced
from animate_shorts import encode,FPS

CODES='ANA BOS BUF CAR CBJ CGY CHI COL DAL DET EDM FLA LAK MIN MTL NJD NSH NYI NYR OTT PHI PIT SEA SJS STL TBL TOR UTA VAN VGK WPG WSH'.split()
LOGO_URL='https://assets.nhle.com/logos/nhl/svg/{code}_light.svg'

def logos(codes, strict=True):
    import requests
    from io import BytesIO
    import cairosvg
    missing=[]
    for code in sorted(set(codes)):
        if code not in CODES: raise ValueError('Neznámý klub: '+code)
        target=ROOT/'assets/logos'/f'{code}.png'
        if target.exists(): continue
        try:
            r=requests.get(LOGO_URL.format(code=code),timeout=15,headers={'User-Agent':'Be6player/6.5'})
            r.raise_for_status()
            if b'<svg' not in r.content[:500]:raise ValueError('Odpověď není SVG')
            target.parent.mkdir(parents=True,exist_ok=True)
            target.write_bytes(cairosvg.svg2png(bytestring=r.content,output_width=420,output_height=420))
        except Exception as e: missing.append(f'{code}: {e}')
    if missing and strict: raise RuntimeError('Chybí loga; nevytvářím zavádějící výstup: '+'; '.join(missing))
    return missing

def form(t,venue=None):
    x=t.get('form_'+venue if venue else 'form_all') or {}
    return f"{x.get('V',0)}-{x.get('P',0)}-{x.get('PP',0)}" if x.get('sample_size') else 'N/D'

def pct(t, key):
    # Optional data from enriched pipeline: no fabricated percentages.
    for source in (t,t.get('advanced') or {},t.get('stats') or {}):
        v=source.get(key)
        if isinstance(v,(int,float)):return f'{v:.1f} %'.replace('.',',')
        if isinstance(v,str) and v.strip():return v
    return 'N/D'

def mapped(g):
    h,a=g['home'],g['away']
    def record(t):return '-'.join(str(t[k]) if t.get(k) is not None else '?' for k in ('wins','losses','ot_losses'))
    def streak(t):
        s=t.get('streak') or {}
        return f"{s.get('length')}× {'V' if s.get('type')=='vyhry' else 'bez V'}" if s.get('length') else 'N/D'
    def place(t):return str(t.get('conference_rank') or 'N/D')
    rows=[('BILANCE',record),('POSLEDNÍCH 5 (V-P-PP)',lambda t:form(t)),('DOMA/VENKU (POSL. 5)',lambda t:form(t,'home' if t is h else 'away')),('VHAZOVÁNÍ',lambda t:pct(t,'faceoff_pct')),('STŘELY / ZÁPAS',lambda t: str(t.get('advanced',{}).get('shots_per_game','N/D')).replace('.',',')),('PP%',lambda t:pct(t,'power_play_pct')),('PK%',lambda t:pct(t,'penalty_kill_pct'))]
    fact=(g.get('featured_fact') or {}).get('text') or 'Předzápasové srovnání týmů NHL.'
    return {'home':h['abbrev'],'away':a['abbrev'],'home_name':h['abbrev'],'away_name':a['abbrev'], 'title':'ZÁPAS DNE' if str(g.get('id'))==str(g.get('_game_of_day_id')) else 'PŘEDZÁPASOVÉ SROVNÁNÍ', 'rows':[{'label':label,'home':fn(h),'away':fn(a)} for label,fn in rows], 'caption':fact[:135], 'source_label': 'DEMO • ILUSTRAČNÍ DATA' if g.get('_demo') else 'NHL API • PŘEDZÁPASOVÁ DATA'}

def instrumental(path,seconds,rate=16000):
    # Original procedural music, not a sample of a commercial recording.
    notes=[110,130.81,146.83,164.81,196,174.61,146.83,130.81]
    with wave.open(str(path),'wb') as f:
        f.setnchannels(1);f.setsampwidth(2);f.setframerate(rate)
        for start in range(0,int(seconds*rate),4096):
            buf=array.array('h')
            for i in range(start,min(int(seconds*rate),start+4096)):
                t=i/rate; beat=t*2.4; note=notes[int(beat//2)%len(notes)]
                fade=min(1,t/0.8,(seconds-t)/1.2)
                bass=math.sin(2*math.pi*note*t)*0.43
                harmony=math.sin(2*math.pi*note*1.5*t)*0.18
                kick=math.sin(2*math.pi*54*t)*math.exp(-12*(beat%1))*0.30
                hat=(math.sin(2*math.pi*4200*t)+math.sin(2*math.pi*6900*t))*math.exp(-24*((beat*2)%1))*0.06
                buf.append(int(max(-1,min(1,(bass+harmony+kick+hat)*fade))*10500))
            f.writeframes(buf.tobytes())

def build(data,out,strict_logos=True,seconds_per_card=4):
    if not shutil.which('ffmpeg'):raise RuntimeError('Chybí ffmpeg')
    games=data.get('games')
    if not isinstance(games,list):raise ValueError('Chybí games')
    if not games:raise ValueError('Žádné zápasy: nevytvářím fiktivní video')
    codes=[g[side]['abbrev'] for g in games for side in ('home','away')]
    missing=logos(codes,strict_logos)
    out=Path(out);out.mkdir(parents=True,exist_ok=True)
    cards=out/'cards';cards.mkdir(exist_ok=True)
    slides=[]
    highlights={}
    from shorts_highlight import plan
    from render_players import render_players
    pages=3 if len(games)<=10 or data.get('force_three_pages') else 2
    for i,g in enumerate(games,1):
        g=dict(g,_game_of_day_id=data.get('game_of_day_id'),_demo=data.get('data_mode')=='OFFLINE_FIXTURE_NOT_LIVE')
        p=cards/f'game_{i:02d}.png';render(mapped(g),p);slides.append(p)
        highlights[p.name]=plan(g,1)
        first=p
        p=cards/f'game_{i:02d}_advanced.png';render_advanced(g,p);slides.append(p);highlights[p.name]=plan(g,2)
        if pages==3:
            p=cards/f'game_{i:02d}_players.png';render_players(g,p,first);slides.append(p);highlights[p.name]=plan(g,3)
    shutil.copy2(slides[0],out/'nahled.png')
    if seconds_per_card <= 0: raise ValueError('Neplatná délka karty')
    frames_per_card=max(1,int(min(seconds_per_card,175/len(slides))*FPS))
    duration=frames_per_card*len(slides)/FPS
    with tempfile.TemporaryDirectory() as tmp:
        music=Path(tmp)/'original_music.wav'
        instrumental(music,duration)
        encode(slides,ROOT,music,out/'be6player_shorts.mp4',frames_per_card,highlights)
    (out/'highlights.json').write_text(json.dumps(highlights,ensure_ascii=False,indent=2),encoding='utf-8')
    (out/'titulek.txt').write_text('NHL dnes | Be6player – zápasy a statistiky\n',encoding='utf-8')
    (out/'popis.txt').write_text(f"Přehled NHL pro {data.get('local_date','zvolené datum')}. Statistiky týmů a zápas dne. #NHL #Hokej #Be6player #NHLShorts\n",encoding='utf-8')
    (out/'manifest.json').write_text(json.dumps({'games':len(games),'cards':len(slides),'pages_per_game':pages,'seconds':duration,'fps':FPS,'animation':'V7.7 reveal, crossfade and statistical highlight','audio':'original instrumental only','voice':False,'youtube_upload':False,'missing_logos':missing,'data_source':data.get('note','external JSON'),'status':'demo' if data.get('data_mode')=='OFFLINE_FIXTURE_NOT_LIVE' else 'rendered', 'data_mode':data.get('data_mode','UNSPECIFIED')},ensure_ascii=False,indent=2),encoding='utf-8')
    return out/'be6player_shorts.mp4'

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--input',required=True);ap.add_argument('--outdir',required=True);ap.add_argument('--allow-missing-logos',action='store_true',help='Pouze lokální demo, viditelně ukazuje BEZ LOGA');ap.add_argument('--seconds-per-card',type=float,default=4);a=ap.parse_args()
    print(build(json.loads(Path(a.input).read_text(encoding='utf-8')),a.outdir,not a.allow_missing_logos,a.seconds_per_card))
