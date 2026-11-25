from render import ROOT,txt,font
from PIL import Image,ImageDraw
from pathlib import Path

def values(m):
    def fmt(k,pattern):
        return pattern.format(m[k]).replace('.',',') if k in m else '–'
    return [('-'.join(map(str,m['h2h'])) if 'h2h' in m else '–'),fmt('first_pct','{:.0f} %'),fmt('gf','{:.2f}'),fmt('ga','{:.2f}'),*[str(x) for x in m.get('period_totals',['–']*3)],fmt('rest_hours','{:.0f} h')]

def render_advanced(g,dest):
    im=Image.open(ROOT/'assets/arena_v701.png').convert('RGB');d=ImageDraw.Draw(im)
    metrics=g.get('match_metrics',{})
    for side,x in [('home',220),('away',865)]:
        code=g[side]['abbrev'];p=ROOT/'assets/logos'/f'{code}.png'
        if p.exists():
            logo=Image.open(p).convert('RGBA');logo=logo.crop(logo.getchannel('A').getbbox());logo.thumbnail((200,200));im.paste(logo,(round(x-logo.width/2),round(490-logo.height/2)),logo)
        else:txt(d,'BEZ LOGA',(x,490),30,190)
        txt(d,code,(x,645),46,230)
        m=metrics.get(code,{})
        label=('DOMA' if side=='home' else 'VENKU')+' – SEZONA'
        if 'venue_sample' in m: label+=f" ({m['venue_sample']})"
        txt(d,label,(x,710),23,310)
        for y,v in zip([774,873,974,1075,1174,1263,1353,1444],values(metrics.get(code,{}))):txt(d,v,(x,y),48,260)
    secondary=g.get('secondary_fact')
    caption=secondary['text'] if secondary else 'Produktivita a první gól: celá sezona doma/venku.'
    words=caption.split();lines=[];line=''
    for w in words:
        trial=(line+' '+w).strip()
        if line and d.textlength(trial,font=font(30))>820:lines.append(line);line=w
        else:line=trial
    if line:lines.append(line)
    for i,line in enumerate(lines):txt(d,line,(540,1630+(i-(len(lines)-1)/2)*34),30,840)
    txt(d,'DEMO • OFFLINE DATA' if g.get('_demo') else 'NHL API • PŘEDZÁPASOVÁ DATA',(540,1840),27,850)
    im.save(dest)
