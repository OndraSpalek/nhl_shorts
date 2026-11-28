"""Current roster and explicitly identified previous NHL clubs; no injury inference."""
from datetime import datetime, timezone
from shorts_data import get_json, utc_datetime

TEAM_NAMES={'CAR':('Carolina Hurricanes',),'NYR':('New York Rangers',),'ANA':('Anaheim Ducks','Mighty Ducks of Anaheim'),'BOS':('Boston Bruins',),'BUF':('Buffalo Sabres',),'CGY':('Calgary Flames',),'CHI':('Chicago Blackhawks',),'COL':('Colorado Avalanche',),'CBJ':('Columbus Blue Jackets',),'DAL':('Dallas Stars',),'DET':('Detroit Red Wings',),'EDM':('Edmonton Oilers',),'FLA':('Florida Panthers',),'LAK':('Los Angeles Kings',),'MIN':('Minnesota Wild',),'MTL':('Montréal Canadiens','Montreal Canadiens'),'NSH':('Nashville Predators',),'NJD':('New Jersey Devils',),'NYI':('New York Islanders',),'OTT':('Ottawa Senators',),'PHI':('Philadelphia Flyers',),'PIT':('Pittsburgh Penguins',),'SJS':('San Jose Sharks',),'SEA':('Seattle Kraken',),'STL':('St. Louis Blues',),'TBL':('Tampa Bay Lightning',),'TOR':('Toronto Maple Leafs',),'UTA':('Utah Hockey Club','Utah Mammoth'),'VAN':('Vancouver Canucks',),'VGK':('Vegas Golden Knights',),'WSH':('Washington Capitals',),'WPG':('Winnipeg Jets',)}

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
    from shorts_status_feed import load as load_status, for_game
    try: statuses=load_status(now)
    except (ValueError,OSError,TypeError): statuses=[]; result['warnings'].append('Invalid status feed')
    for g in data['games']:
        gid=str(g['id']); out=result['games'][gid]=[]; m=result['metrics'][gid]={'starting_goalies':'not_verified','injuries':'not_verified','returns':'not_verified','transfers':'not_verified','former_team':[]}
        if utc_datetime(g['start_utc'])<=now: continue
        m['reported_statuses']=for_game(statuses,g)
        for side,other in [('home','away'),('away','home')]:
            code,opp=g[side]['abbrev'],g[other]['abbrev']; rp=f'/roster/{code}/current'; roster=load(rp)
            for group in ('forwards','defensemen','goalies'):
                for p in roster.get(group,[]) or []:
                    pid=p.get('id')
                    if type(pid)!=int: continue
                    path=f'/player/{pid}/landing'; profile=load(path)
                    if profile.get('playerId')!=pid or profile.get('currentTeamAbbrev')!=code: continue
                    rows=[r for r in profile.get('seasonTotals',[]) if r.get('leagueAbbrev')=='NHL' and r.get('gameTypeId')==2 and (r.get('teamAbbrev')==opp or (r.get('teamName') or {}).get('default') in TEAM_NAMES.get(opp,())) and type(r.get('gamesPlayed'))==int and r['gamesPlayed']>0]
                    if not rows: continue
                    name=' '.join(p.get(k,{}).get('default','') for k in ('firstName','lastName')).strip()
                    if not name: continue
                    gp=sum(r['gamesPlayed'] for r in rows); e=dict(sample_size=gp,player_id=pid,former_team=opp,current_team=code,season_rows=rows,roster_source=rp)
                    m['former_team'].append(e); out.append(dict(category='former_team',text=f'{code}: {name} dříve odehrál za {opp} {gp} utkání základní části NHL.',verified=True,source='NHL API: '+path,evidence=e))
    result['sources']=list(cache); return result
