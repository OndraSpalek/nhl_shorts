"""Historical regular-season results, with explicit game IDs and bounded coverage."""
from datetime import datetime, timezone
from shorts_data import get_json, utc_datetime

def enrich(data, fetch=get_json, now=None):
    now=now or datetime.now(timezone.utc); cache={}; result={'games':{},'warnings':[],'sources':[]}
    for g in data['games']:
        out=result['games'][str(g['id'])]=[]; start=utc_datetime(g['start_utc']); cutoff=min(start,now); y=start.year-(start.month<7)
        h,a=(g[s]['abbrev'] for s in ('home','away')); rows={}; complete=True
        for year in range(y-9,y+1):
            path=f'/club-schedule-season/{h}/{year*10000+year+1}'
            if path not in cache:
                try:
                    p=fetch(path); cache[path]=p['games']; assert isinstance(cache[path],list)
                except Exception as e:
                    cache[path]=None; result['warnings'].append(f'{path}: {type(e).__name__}')
            if cache[path] is None: complete=False; continue
            for x in cache[path]:
                try:
                    if x['gameType']!=2 or x['gameState'] not in ('OFF','FINAL'): continue
                    t=utc_datetime(x['startTimeUTC']); u,v=x['homeTeam'],x['awayTeam']
                    if t>=cutoff or {u['abbrev'],v['abbrev']}!={h,a}: continue
                    if type(u['score'])!=int or type(v['score'])!=int or u['score']==v['score']: raise ValueError('score')
                    rows[x['id']]=(t,u['abbrev'] if u['score']>v['score'] else v['abbrev'],x['gameDate'],path)
                except (KeyError,TypeError,ValueError): complete=False
        ordered=sorted(rows.items(),key=lambda z:z[1][0],reverse=True)
        def add(text, sample, kind):
            out.append(dict(category='history_extended',text=text,verified=True,source='NHL API: '+', '.join(sorted({r[1][3] for r in sample})),evidence=dict(sample_size=len(sample),game_ids=[r[0] for r in sample],kind=kind)))
        if complete and len(ordered)>=10:
            sample=ordered[:10]; wins=sum(r[1][1]==h for r in sample)
            if max(wins,10-wins)>=8: add(f'{h if wins>=8 else a} vyhrál {max(wins,10-wins)} z posledních 10 vzájemných duelů základní části.',sample,'h2h10')
            leader=ordered[0][1][1]; streak=[]
            for r in ordered:
                if r[1][1]!=leader: break
                streak.append(r)
            if len(streak)>=6: add(f'{leader} vyhrál posledních {len(streak)} vzájemných duelů v základní části (sledovaných 10 sezon).',streak,'streak')
        for r in ordered:
            date=r[1][2]
            if date[5:]==start.date().isoformat()[5:] and int(date[:4])<start.year:
                add(f'V tento den roku {date[:4]} vyhrál {r[1][1]} vzájemný duel {h}–{a}.',[r],'anniversary'); break
    result['sources']=list(cache); return result
