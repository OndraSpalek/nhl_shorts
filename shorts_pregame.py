"""Conservative pregame context from NHL schedules and explicit official confirmations."""
from datetime import datetime, timezone
from shorts_data import get_json, utc_datetime

def enrich(data, fetch=get_json, now=None):
    now=now or datetime.now(timezone.utc)
    result={'games':{},'metrics':{},'warnings':[],'sources':[]}; cache={}
    def load(path):
        if path not in cache:
            try:
                value=fetch(path)
                if not isinstance(value,dict): raise ValueError('payload')
                cache[path]=value
            except Exception as exc:
                cache[path]={}; result['warnings'].append(f'{path}: {type(exc).__name__}')
        return cache[path]
    for g in data['games']:
        gid=str(g['id']); facts=result['games'][gid]=[]; metrics=result['metrics'][gid]={}
        start=utc_datetime(g['start_utc']); cutoff=min(start,now); y=start.year-(start.month<7); season=y*10000+y+1
        def add(text,source,**e):
            facts.append({'category':'pregame','text':text,'source':'NHL API: '+source,'verified':True,'evidence':e})
        for side in ('home','away'):
            code=g[side]['abbrev']; path=f'/club-schedule-season/{code}/{season}'; payload=load(path); m=metrics[code]={}
            rows={}; complete=isinstance(payload.get('games'),list)
            for x in payload.get('games') or []:
                try:
                    if x['gameType']!=2 or x['gameState'] not in ('OFF','FINAL'): continue
                    t=utc_datetime(x['startTimeUTC'])
                    if t>=cutoff: continue
                    h,a=x['homeTeam'],x['awayTeam']; u,v=(h,a) if h['abbrev']==code else (a,h)
                    if u['abbrev']!=code or type(u['score'])!=int or type(v['score'])!=int or u['score']==v['score']: raise ValueError('score')
                    rows[x['id']]=(t,u['score']>v['score'],x['id'])
                except (KeyError,ValueError,TypeError): complete=False
            ordered=sorted(rows.values()); m['complete']=complete; m['games']=len(ordered)
            if not complete or not ordered or start<=now: continue
            hours=(start-ordered[-1][0]).total_seconds()/3600; m['hours_between_starts']=hours
            if 0<hours<=30:
                add(f'{code}: druhý zápas během {round(hours)} hodin (mezi začátky utkání).',path,sample_size=1,game_ids=[ordered[-1][2]],hours=hours,kind='short_rest')
            groups={'short':[],'normal':[],'long':[]}
            for prev,cur in zip(ordered,ordered[1:]):
                gap=(cur[0]-prev[0]).total_seconds()/3600
                if gap<=0: continue
                groups['short' if gap<=30 else 'long' if gap>=72 else 'normal'].append(cur)
            m['rest_groups']={k:{'games':len(v),'wins':sum(r[1] for r in v),'game_ids':[r[2] for r in v]} for k,v in groups.items()}
            key='short' if hours<=30 else 'long' if hours>=72 else 'normal'; sample=groups[key]; wins=sum(r[1] for r in sample)
            if len(sample)>=5 and (wins/len(sample)>=.75 or wins/len(sample)<=.25):
                label={'short':'do 30 h','normal':'30–72 h','long':'od 72 h'}[key]
                add(f'{code}: {wins} výher z {len(sample)} utkání s odstupem začátků {label}.',path,sample_size=len(sample),wins=wins,game_ids=[r[2] for r in sample],kind='rest_record')
        metrics['availability']={'starting_goalies':'not_verified','injuries':'not_verified','returns':'not_verified','transfers':'not_verified','former_team':'not_verified'}
    result['sources']=list(cache); return result
