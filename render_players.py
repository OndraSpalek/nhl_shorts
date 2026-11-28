from render import ROOT,txt,font
from PIL import Image,ImageDraw
from io import BytesIO
from datetime import datetime,timezone
from shorts_data import get_json,utc_datetime

def select(metrics,ids):
    p=[q for q in metrics.get('players',[]) if q['player_id'] in ids]
    gs=[q for q in metrics.get('goalies',[]) if q.get('player_id') in ids and q.get('save_pct') is not None]
    return [max(p,key=lambda q:q['points'],default=None),max(p,key=lambda q:q['goals'],default=None),max((q for q in p if len(q['games'])>=5),key=lambda q:q['last5_points'],default=None),max(gs,key=lambda q:q['gp'],default=None)]

def prepare(data,history,fetch=get_json):
    if len(data['games'])>10 and not data.get('force_three_pages'):return
    for g in data['games']:
        g['player_cards']={}
        if utc_datetime(g['start_utc'])<=datetime.now(timezone.utc):continue
        for side in ('home','away'):
            code=g[side]['abbrev']
            try:
                roster=fetch(f'/roster/{code}/current'); ids={p['id']:p for k in ('forwards','defensemen','goalies') for p in roster[k]}
                rows=select(history['metrics'].get(str(g['id']),{}).get(code,{}),ids)
                g['player_cards'][code]=[dict(q,display_name=' '.join(ids[q['player_id']][k]['default'] for k in ('firstName','lastName')),headshot=ids[q['player_id']].get('headshot')) if q else None for q in rows]
            except Exception as e: history['warnings'].append(f'{code} player card: {type(e).__name__}')

def portrait(im,url,x,y):
    if not url or not url.startswith('https://assets.nhle.com/'):return
    try:
        import requests
        r=requests.get(url,timeout=10);r.raise_for_status();p=Image.open(BytesIO(r.content)).convert('RGBA');p.thumbnail((145,145));im.paste(p,(x,y+145-p.height),p)
    except Exception:pass

def render_players(g,dest,first):
    im=Image.open(first).convert('RGB');d=ImageDraw.Draw(im)
    # Preserve the exact existing header and team logos, replace only the body.
    d.rectangle((0,690,1080,1800),fill='#091321')
    txt(d,'HRÁČSKÉ SROVNÁNÍ',(540,725),42,980)
    labels=['NEJPRODUKTIVNĚJŠÍ HRÁČI','NEJLEPŠÍ STŘELCI','AKTUÁLNÍ FORMA • POSLEDNÍCH 5 UTKÁNÍ','BRANKÁŘI • NEJVÍCE UTKÁNÍ ZA TÝM']
    for i,label in enumerate(labels):
        y=770+i*195
        for side,x,color,bg in [('home',25,'#ff354d','#390d20'),('away',550,'#229cff','#082c50')]:
            d.rounded_rectangle((x,y+28,x+505,y+180),radius=15,fill=bg,outline=color,width=4)
            rows=g.get('player_cards',{}).get(g[side]['abbrev'],[]);q=rows[i] if len(rows)>i else None
            if not q:txt(d,'N/D',(x+250,y+105),40,400);continue
            portrait(im,q.get('headshot'),x+8 if side=='home' else x+350,y+32)
            cx=x+325 if side=='home' else x+175
            txt(d,q['display_name'],(cx,y+78),30,325)
            if i==0:s=f"{q['points']} B ({q['goals']}+{q['assists']})"
            elif i==1:s=f"{q['goals']} G"
            elif i==2:s=f"{q['last5_points']} B ({q['last5_goals']}+{q['last5_points']-q['last5_goals']})"
            else:s=f"{q['save_pct']:.1f} % | {q['gaa']:.2f}".replace('.',',')
            txt(d,s,(cx,y+128),39,325)
        d.rounded_rectangle((170,y,910,y+42),radius=8,fill='#152235',outline='#9aaabd',width=2);txt(d,label,(540,y+21),28,720)
    d.rounded_rectangle((35,1570,1045,1770),radius=16,fill='#101e31',outline='#799fc8',width=3)
    txt(d,'INDIVIDUÁLNÍ ZAJÍMAVOST',(540,1600),32,960)
    used={ (g.get(k) or {}).get('text') for k in ('featured_fact','secondary_fact')}
    from shorts_quality import fits
    fact=next((c['text'] for c in g.get('all_candidates',[]) if c['category'] in ('player_streak','milestone','goalie','player_leader','hat_trick','shutout','historical_record') and c['text'] not in used and fits(c['text'],2)),None)
    line='';lines=[]
    for w in (fact or 'Další ověřená individuální zajímavost není k dispozici.').split():
        t=(line+' '+w).strip()
        if line and d.textlength(t,font=font(30))>940:lines.append(line);line=w
        else:line=t
    if line:lines.append(line)
    for i,l in enumerate(lines):txt(d,l,(540,1660+i*35),30,940)
    im.save(dest)
