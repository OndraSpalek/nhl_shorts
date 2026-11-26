"""Experimental chronological Elo model. No predictions for incomplete training data."""
from datetime import datetime, timezone
from math import log
from shorts_data import get_json, utc_datetime

K=20
HOME=35
MIN_GAMES=20

def probability(h,a):
    return 1/(1+10**((a-h-HOME)/400))

def evaluate(rows, targets):
    ratings={}; counts={}; results=[]; forecasts={}
    # Conservative daily batches: never learn from a game on the same UTC date.
    days={}
    for r in rows: days.setdefault(r[1].date(),[[],[]])[0].append(r)
    for r in targets: days.setdefault(r[1].date(),[[],[]])[1].append(r)
    for day,(games, upcoming) in sorted(days.items()):
        def p(h,a): return probability(ratings.get(h,1500),ratings.get(a,1500))
        for gid,t,h,a in upcoming:
            if min(counts.get(h,0),counts.get(a,0))>=MIN_GAMES:
                forecasts[str(gid)]={'home_probability':round(p(h,a),6),'away_probability':round(1-p(h,a),6),'home_games':counts[h],'away_games':counts[a]}
        changes={}
        for gid,t,h,a,y in games:
            pred=p(h,a)
            if min(counts.get(h,0),counts.get(a,0))>=MIN_GAMES: results.append((pred,y))
            delta=K*(y-pred)
            changes[h]=changes.get(h,0)+delta; changes[a]=changes.get(a,0)-delta
        for h,delta in changes.items(): ratings[h]=ratings.get(h,1500)+delta
        for _,_,h,a,_ in games:
            for team in (h,a): counts[team]=counts.get(team,0)+1
    n=len(results)
    metrics={'sample_size':n}
    if n:
        metrics.update(brier=sum((p-y)**2 for p,y in results)/n,log_loss=-sum(y*log(p)+(1-y)*log(1-p) for p,y in results)/n,accuracy=sum((p>=.5)==bool(y) for p,y in results)/n,baseline_brier=sum((probability(1500,1500)-y)**2 for p,y in results)/n)
    return forecasts,metrics

def enrich(data,fetch=get_json,now=None):
    now=now or datetime.now(timezone.utc)
    result={'model':'experimental_elo_v1','status':'not_validated','games':{},'warnings':[],'sources':[],'parameters':{'k':K,'home_elo':HOME,'minimum_team_games':MIN_GAMES}}
    if not data['games']: return result
    targets=[(g['id'],utc_datetime(g['start_utc']),g['home']['abbrev'],g['away']['abbrev']) for g in data['games']]
    cutoff=min(now,min(t[1] for t in targets)); year=cutoff.year-(cutoff.month<7)
    rows={}
    # League schedule by week, two completed seasons plus current season.
    from datetime import date,timedelta
    d=date(year-2,9,1)
    while d<=cutoff.date():
        path=f'/schedule/{d.isoformat()}'; result['sources'].append(path)
        try:
            payload=fetch(path); week=payload['gameWeek']; assert isinstance(week,list) and week
            for block in week:
                for g in block['games']:
                    if g['gameType']!=2 or g['gameState'] not in ('OFF','FINAL'): continue
                    t=utc_datetime(g['startTimeUTC'])
                    if t>=cutoff: continue
                    h,a=g['homeTeam'],g['awayTeam']; hs,as_=h['score'],a['score']
                    if type(hs)!=int or type(as_)!=int or hs==as_: raise ValueError('invalid final score')
                    row=(g['id'],t,h['abbrev'],a['abbrev'],int(hs>as_))
                    if g['id'] in rows and rows[g['id']]!=row: raise ValueError('conflicting game')
                    rows[g['id']]=row
            # API returns a seven-day window; use actual last day to avoid gaps.
            end=max(date.fromisoformat(b['date']) for b in week)
            if end<d: raise ValueError('invalid schedule window')
            d=end+timedelta(days=1)
        except Exception as exc:
            result['warnings'].append(f'{path}: {type(exc).__name__}: {exc}'); return result
    result['training_games']=len(rows); result['cutoff_utc']=cutoff.isoformat()
    result['games'],result['backtest']=evaluate(list(rows.values()),targets)
    result['status']='experimental_backtest_only'
    return result
