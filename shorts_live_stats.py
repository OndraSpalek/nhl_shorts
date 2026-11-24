"""Official NHL team reports; no guessed values or historical season leakage."""
import requests, math
from datetime import datetime, timezone
BASE='https://api.nhle.com/stats/rest/en/team'
REPORTS={'powerplay':('powerPlayGoalsFor','ppOpportunities'),'penaltykill':('ppGoalsAgainst','timesShorthanded'),'realtime':('shots','gamesPlayed'),'faceoffwins':('faceoffsWon','faceoffsLost')}
def fetch(report,params):
    r=requests.get(BASE+('/'+report if report else ''),params=params,timeout=30);r.raise_for_status();return r.json()['data']
def number(row,key):
    v=row.get(key)
    if isinstance(v,(int,float)) and not isinstance(v,bool) and math.isfinite(v) and v>=0:return v
    raise ValueError(key)
def calculate(report,row):
    a,b=(number(row,k) for k in REPORTS[report])
    if report=='realtime':return 'shots_per_game',round(a/b,2) if b else None,b
    if report=='faceoffwins':return 'faceoff_pct',round(100*a/(a+b),2) if a+b else None,a+b
    if a>b:raise ValueError('goals exceed opportunities')
    return ('power_play_pct' if report=='powerplay' else 'penalty_kill_pct'),round(100*(a if report=='powerplay' else b-a)/b,2) if b else None,b

def enrich(data,fetcher=fetch,now=None):
    now=now or datetime.now(timezone.utc); warnings=[]; facts={}; sources={}; cache={}
    if not data['games']:return {'games':facts,'warnings':warnings,'sources':sources}
    try: teams={r['id']:r.get('triCode') or r.get('rawTricode') for r in fetcher('',{})}
    except Exception as e:return {'games':facts,'warnings':[f'NHL team map: {e}'],'sources':sources}
    for g in data['games']:
        start=datetime.fromisoformat(g['start_utc']); gt=g['game_type']; year=start.year-(start.month<7); season=year*10000+year+1
        if start<=now:
            warnings.append(f"{g['id']}: sezonní snapshot po začátku zápasu odmítnut");continue
        key=(season,gt)
        if key not in cache:
            cache[key]={}; params={'isAggregate':'false','isGame':'false','start':0,'limit':-1,'cayenneExp':f'gameTypeId={gt} and seasonId={season}'}
            for report in REPORTS:
                try:
                    rows=fetcher(report,params); sources[f'{season}/{gt}/{report}']={'url':BASE+'/'+report,'params':params,'retrieved_utc':datetime.now(timezone.utc).isoformat(),'rows':rows}
                    for row in rows:
                        code=teams.get(row.get('teamId'))
                        if not code:continue
                        try:
                            metric,value,n=calculate(report,row)
                            if value is not None:cache[key].setdefault(code,{})[metric]={'value':value,'denominator':n,'source':BASE+'/'+report,'raw':{k:row[k] for k in REPORTS[report]}}
                        except (ValueError,KeyError):continue
                except Exception as e:warnings.append(f'{report}: {e}')
        for side in ('home','away'):
            t=g[side]; evidence=cache[key].get(t['abbrev'],{});t['advanced']={k:v['value'] for k,v in evidence.items()};t['advanced_evidence']=evidence
            for metric in ('power_play_pct','penalty_kill_pct','shots_per_game','faceoff_pct'):
                if metric not in evidence:warnings.append(f"{t['abbrev']}: {metric} nedostupné")
        h,a=g['home'],g['away']; samples=[t.get('advanced_evidence',{}).get('shots_per_game',{}).get('denominator',0) for t in (h,a)]
        for metric,cat,label,threshold,min_n in [('power_play_pct','special_teams','Přesilovky',8,20),('penalty_kill_pct','special_teams','Oslabení',8,20),('shots_per_game','shots','Střely na zápas',5,10),('faceoff_pct','faceoffs','Vhazování',7,100)]:
            x,y=[t.get('advanced_evidence',{}).get(metric,{}) for t in (h,a)]
            if not x or not y or min(samples)<10 or min(x['denominator'],y['denominator'])<min_n or abs(x['value']-y['value'])<threshold:continue
            unit='' if metric=='shots_per_game' else ' %'; text=f"{label}: {h['abbrev']} {x['value']:.1f}{unit}, {a['abbrev']} {y['value']:.1f}{unit}".replace('.',',')
            facts.setdefault(str(g['id']),[]).append({'category':cat,'verified':True,'source':x['source'],'text':text,'evidence':{'sample_size':int(min(samples)),'home':x,'away':y}})
    return {'games':facts,'warnings':warnings,'sources':sources}
