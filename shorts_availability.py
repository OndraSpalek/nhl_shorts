"""Current roster and explicitly identified previous NHL clubs; no injury inference."""
from datetime import datetime, timezone
from shorts_data import get_json, utc_datetime

def enrich(data, fetch=get_json, now=None):
    now=now or datetime.now(timezone.utc); cache={}; result={'games':{},'metrics':{},'warnings':[],'sources':[]}
    def load(path):
        if path not in cache:
            try:
                p=fetch(path)
                if not isinstance(p,dict): raise ValueError('payload')
                cache[path]=p
            except Exception as e: cache[path]={}; result['warnings'].append(f'{path}: {type(e).__name__}')
        return cache[path]
    for g in data['games']:
        gid=str(g['id']); out=result['games'][gid]=[]; m=result['metrics'][gid]={'starting_goalies':'not_verified','injuries':'not_verified','returns':'not_verified','transfers':'not_verified','former_team':[]}
        if utc_datetime(g['start_utc'])<=now: continue
        for side,other in [('home','away'),('away','home')]:
            code,opp=g[side]['abbrev'],g[other]['abbrev']; rp=f'/roster/{code}/current'; roster=load(rp)
            for group in ('forwards','defensemen','goalies'):
                for p in roster.get(group,[]) or []:
                    pid=p.get('id')
                    if type(pid)!=int: continue
                    path=f'/player/{pid}/landing'; profile=load(path)
                    if profile.get('playerId')!=pid or profile.get('currentTeamAbbrev')!=code: continue
                    rows=[r for r in profile.get('seasonTotals',[]) if r.get('leagueAbbrev')=='NHL' and r.get('gameTypeId')==2 and r.get('teamAbbrev')==opp and type(r.get('gamesPlayed'))==int and r['gamesPlayed']>0]
                    if not rows: continue
                    name=' '.join(p.get(k,{}).get('default','') for k in ('firstName','lastName')).strip()
                    if not name: continue
                    gp=sum(r['gamesPlayed'] for r in rows); e=dict(sample_size=gp,player_id=pid,former_team=opp,current_team=code,season_rows=rows,roster_source=rp)
                    m['former_team'].append(e); out.append(dict(category='former_team',text=f'{code}: {name} dříve odehrál za {opp} {gp} utkání základní části NHL.',verified=True,source='NHL API: '+path,evidence=e))
    result['sources']=list(cache); return result
