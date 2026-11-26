"""Verified season game-flow facts, with complete scoring reconciliation."""
from datetime import datetime, timezone
import time
from shorts_data import get_json, utc_datetime

def parse(row, payload, code):
    events=[]
    for period in payload['summary']['scoring']:
        desc=period['periodDescriptor']; n=desc['number']
        if desc['periodType']=='SO': continue
        for goal in period['goals']:
            team=goal['teamAbbrev']['default']
            if team not in (code,row['opponent']) or n not in (1,2,3,4): raise ValueError('invalid goal')
            mm,ss=map(int,goal['timeInPeriod'].split(':'))
            events.append((n,mm*60+ss,team))
    return reconcile(row,events,code)

def parse_pbp(row,payload,code):
    teams={payload[k]['id']:payload[k]['abbrev'] for k in ('homeTeam','awayTeam')}
    if set(teams.values())!={code,row['opponent']} or payload['id']!=row['id']: raise ValueError('wrong game or teams')
    events=[]; seen=set()
    for play in payload['plays']:
        if play.get('typeDescKey')!='goal': continue
        desc=play['periodDescriptor']; n=desc['number']
        if desc['periodType']=='SO': continue
        if n not in (1,2,3,4) or play['eventId'] in seen: raise ValueError('invalid goal event')
        seen.add(play['eventId']); mm,ss=map(int,play['timeInPeriod'].split(':'))
        events.append((n,mm*60+ss,teams[play['details']['eventOwnerTeamId']]))
    return reconcile(row,events,code)

def reconcile(row,events,code):
    events.sort(key=lambda e: (e[0], e[1])); win=row['gf']>row['ga']; so=row['shootout']
    if not events or sum(t==code for _,_,t in events)!=row['gf']-int(so and win) or sum(t!=code for _,_,t in events)!=row['ga']-int(so and not win): raise ValueError('score mismatch')
    diff=0; led=False; trailed=False
    for _,_,t in events:
        diff+=1 if t==code else -1; led |= diff>0; trailed |= diff<0
    return dict(row,win=win,led=led,trailed=trailed,first_against=events[0][2]!=code,after1=sum(1 if t==code else -1 for n,_,t in events if n<=1),after2=sum(1 if t==code else -1 for n,_,t in events if n<=2),events=events)

def enrich(data, fetch=get_json, now=None):
    now=now or datetime.now(timezone.utc); cache={}; result={'games':{},'metrics':{},'warnings':[],'sources':[],'diagnostics':{},'fallback_recovered':[]}
    def load(path):
        if path not in cache:
            for attempt in range(3):
                try:
                    cache[path]=fetch(path)
                    if not isinstance(cache[path],dict): raise ValueError('invalid response')
                    break
                except Exception as e:
                    cache[path]=None
                    if attempt==2: result['warnings'].append(f'{path}: {type(e).__name__}')
                    elif fetch is get_json: time.sleep(2**attempt)
        return cache[path]
    for g in data['games']:
        gid=str(g['id']); out=result['games'][gid]=[]; metrics=result['metrics'][gid]={}; start=utc_datetime(g['start_utc']); cutoff=min(start,now); y=start.year-(start.month<7); season=y*10000+y+1
        for side in ('home','away'):
            code=g[side]['abbrev']; rows={}; parsed=[]
            try:
                for x in load(f'/club-schedule-season/{code}/{season}')['games']:
                    if x['gameType']!=2 or x['gameState'] not in ('OFF','FINAL') or x['id']==g['id'] or utc_datetime(x['startTimeUTC'])>=cutoff: continue
                    h,a=x['homeTeam'],x['awayTeam']; u,v=(h,a) if h['abbrev']==code else (a,h)
                    if u['abbrev']!=code or type(u['score'])!=int or type(v['score'])!=int or u['score']==v['score']: raise ValueError('invalid schedule')
                    rows[x['id']]=dict(id=x['id'],start=x['startTimeUTC'],opponent=v['abbrev'],gf=u['score'],ga=v['score'],shootout=x['gameOutcome']['lastPeriodType']=='SO')
                for row in rows.values():
                    path=f"/gamecenter/{row['id']}/landing"
                    landing=load(path)
                    try:
                        parsed.append(dict(parse(row,landing,code),source=path))
                    except (KeyError,TypeError,ValueError,AttributeError) as e:
                        alternative=f"/gamecenter/{row['id']}/play-by-play"
                        pbp=load(alternative)
                        diagnostic={'schedule':row,'landing_error':str(e),'landing':landing,'play_by_play':pbp}
                        result['diagnostics'][f"{gid}:{code}:{row['id']}"]=diagnostic
                        try:
                            parsed.append(dict(parse_pbp(row,pbp,code),source=alternative))
                            diagnostic['status']='recovered'
                            result['fallback_recovered'].append(dict(game_id=row['id'],team=code))
                        except (KeyError,TypeError,ValueError,AttributeError) as err:
                            diagnostic.update(status='unresolved',fallback_error=str(err))
                            result['warnings'].append(f"{gid} {code} game {row['id']}: {e}; play-by-play: {err}")
            except (KeyError,TypeError,ValueError,AttributeError) as e:
                result['warnings'].append(f'{gid} {code}: neúplný průběh ({type(e).__name__})'); continue
            m=metrics[code]={'season':season,'sample_size':len(parsed),'expected_games':len(rows),'missing_game_ids':sorted(set(rows)-{r['id'] for r in parsed}),'complete':len(parsed)==len(rows),'games':parsed}
            if not m['complete']: continue
            streak=[]
            for r in sorted(parsed,key=lambda r:r['start'],reverse=True):
                if not r['win']: break
                streak.append(r)
            if len(streak)>=10:
                out.append(dict(category='historical_record',text=f'{code}: {len(streak)} výher v řadě. Pittsburgh v sezoně 1992/93 vyhrál 17 za sebou.',verified=True,source='https://records.nhl.com/records/team-records/winning-streaks',evidence=dict(sample_size=len(streak),games=streak,benchmark=17,benchmark_season='1992/93',checked='2026-11-25')))
            for key,label,pred in [('comeback','po předchozím prohrávání',lambda r:r['trailed']),('lost_lead','po předchozím vedení',lambda r:r['led']),('lead1','při vedení po 1. třetině',lambda r:r['after1']>0),('trail1','při prohrávání po 1. třetině',lambda r:r['after1']<0),('lead2','při vedení po 2. třetině',lambda r:r['after2']>0),('trail2','při prohrávání po 2. třetině',lambda r:r['after2']<0),('first_against','po inkasování prvního gólu',lambda r:r['first_against']),('close','v zápasech o jeden gól',lambda r:abs(r['gf']-r['ga'])==1)]:
                subset=[r for r in parsed if pred(r)]; n=len(subset); w=sum(r['win'] for r in subset); m[key]={'wins':w,'losses':n-w,'sample_size':n}
                if n>=5 and (w/n>=.75 or w/n<=.25 or key in ('comeback','lost_lead') and n>=8):
                    text=f'{code}: v sezoně {label} vyhrál {w} z {n} utkání.'
                    if key=='lost_lead': text=f'{code}: v sezoně prohrál {n-w} z {n} utkání, ve kterých vedl.'
                    out.append(dict(category='game_flow',text=text,verified=True,source='NHL API: /club-schedule-season + /gamecenter/{id}/landing or play-by-play',evidence=dict(sample_size=n,wins=w,kind=key,games=subset)))
    result['sources']=list(cache); return result
