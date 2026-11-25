"""Pregame achievements; suppress career totals for historical reruns."""
from datetime import datetime, timezone
from shorts_data import get_json, utc_datetime

def enrich(data, history, fetch=get_json, now=None):
    now=now or datetime.now(timezone.utc)
    result={'games':{},'warnings':[],'sources':[]}; cache={}
    def load(path):
        if path not in cache:
            try: cache[path]=fetch(path)
            except Exception as e:
                cache[path]={}; result['warnings'].append(f'{path}: {type(e).__name__}')
        return cache[path] if isinstance(cache[path],dict) else {}
    for g in data['games']:
        gid=str(g['id']); out=result['games'][gid]=[]
        def add(cat,text,rows,endpoint,**extra):
            out.append(dict(category=cat,text=text,verified=True,source='NHL API: '+endpoint,evidence=dict(sample_size=len(rows),games=rows,**extra)))
        for side in ('home','away'):
            code=g[side]['abbrev']; m=history.get('metrics',{}).get(gid,{}).get(code,{})
            for p in m.get('players',[]):
                games=p['games']; recent=games[:5]; name=p['name']
                hats=[x for x in recent if x['goals']>=3]
                if hats:
                    maximum=max(x['goals'] for x in hats)
                    add('hat_trick',f'{code}: {name} vstřelil {maximum} góly v jednom z posledních {len(recent)} svých utkání.' if maximum==4 else f'{code}: {name} vstřelil {maximum} gólů v jednom z posledních {len(recent)} svých utkání.',recent,'/gamecenter/{id}/boxscore',hat_tricks=len(hats),max_goals=maximum)
                for key, threshold, record, word, url in [('goals',70,92,'gólů','goals/skater-most-goals-one-season'),('points',160,215,'bodů','points/skater-most-points-one-season')]:
                    total=sum(x.get(key,0) for x in games)
                    if total>=threshold:
                        out.append(dict(category='historical_record',text=f'{code}: {name} má za tým {total} {word}. Gretzkyho historické maximum: {record} za sezonu.',verified=True,source='https://records.nhl.com/records/skater-records/'+url,evidence=dict(sample_size=len(games),games=games,benchmark=record,checked='2026-11-25')))
                if utc_datetime(g['start_utc'])<=now or not games: continue
                # Only current roster, never infer a career total from team-only totals.
                roster=load(f'/roster/{code}/current'); ids={x.get('id') for k in ('forwards','defensemen') for x in roster.get(k,[]) if isinstance(x,dict)}
                pid=p.get('player_id')
                if pid not in ids: continue
                path=f'/player/{pid}/landing'; profile=load(path)
                if profile.get('playerId')!=pid or profile.get('currentTeamAbbrev')!=code: continue
                totals=profile.get('careerTotals',{}).get('regularSeason',{})
                for key,word,targets in [('points','bodů',(100,200,300,400,500,600,700,800,900,1000,1500,2000)),('goals','gólů',(100,200,300,400,500,600,700,800,900))]:
                    value=totals.get(key)
                    if type(value)!=int or value<0: continue
                    for target in targets:
                        if 0<target-value<=2: add('milestone',f'{code}: {name}: do hranice {target} {word} v základní části NHL zbývá {target-value}.',games[:1],path,remaining=target-value,career_total=value,target=target,player_id=pid)
            for p in m.get('goalies',[]):
                for x in p['games'][:5]:
                    # Require explicit official shutout flag, not merely zero goals in relief.
                    box=load(f"/gamecenter/{x['id']}/boxscore")
                    groups=box.get('playerByGameStats',{})
                    matches=[q for s in ('homeTeam','awayTeam') for q in groups.get(s,{}).get('goalies',[]) if q.get('name',{}).get('default')==p['name']]
                    if len(matches)==1 and matches[0].get('shutouts')==1:
                        add('shutout',f"{code}: {p['name']} zaznamenal čisté konto v jednom z posledních {min(5,len(p['games']))} utkání.",[x],'/gamecenter/{id}/boxscore',shutouts=1); break
    result['sources']=list(cache); return result
