"""Conservative comparison of like-for-like displayed metrics."""
import math
from PIL import Image, ImageDraw

def number(v):
    if isinstance(v,bool): return None
    try: n=float(str(v).replace('%','').replace(',','.').strip())
    except (ValueError,TypeError): return None
    return n if math.isfinite(n) and n>=0 else None

def winner(a,b,threshold,lower=False):
    a,b=number(a),number(b)
    if a is None or b is None or abs(a-b)<threshold or a==b:return None
    return 'home' if (a<b if lower else a>b) else 'away'

def plan(g,page):
    result=[]
    def add(key,a,b,threshold,y,lower=False,player=False):
        side=winner(a,b,threshold,lower)
        if side:
            x=(350 if side=='home' else 725) if player else (220 if side=='home' else 860)
            result.append(dict(metric=key,side=side,box=[x-165,y-36,x+165,y+36],values=[number(a),number(b)]))
    h,a=g['home'],g['away']
    if page==1:
        for k,t,y in [('faceoff_pct',7,1080),('shots_per_game',5,1182),('power_play_pct',8,1281),('penalty_kill_pct',8,1383)]:
            add(k,h.get('advanced',{}).get(k),a.get('advanced',{}).get(k),t,y)
    elif page==2:
        m=g.get('match_metrics',{});h,a=[m.get(t['abbrev'],{}) for t in (h,a)]
        if all(isinstance(t.get('venue_sample'),int) and t['venue_sample']>=10 for t in (h,a)):
            for k,t,y,low in [('first_pct',20,873,False),('gf',.8,974,False),('ga',.8,1075,True)]:add(k,h.get(k),a.get(k),t,y,low)
    elif page==3:
        rows=g.get('player_cards',{});h,a=[rows.get(t['abbrev'],[]) for t in (h,a)]
        for i,k,t in [(0,'points',10),(1,'goals',5),(2,'last5_points',4)]:
            if len(h)>i and len(a)>i and h[i] and a[i]:add(k,h[i].get(k),a[i].get(k),t,898+i*195,player=True)
        # Goalie row has two metrics with different directions; avoid ambiguous whole-row highlight.
    return result

def pulse(final,items,strength):
    im=final.copy();d=ImageDraw.Draw(im)
    color=tuple(round(a*strength+b*(1-strength)) for a,b in zip((255,211,95),(145,115,65)))
    for item in items:d.rounded_rectangle(tuple(item['box']),radius=12,outline=color,width=3)
    return im
