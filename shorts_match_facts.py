"""Pregame facts from completed NHL games; evidence retains game IDs and raw scores."""
from datetime import datetime, timezone
from shorts_data import get_json, utc_datetime


def enrich(data, fetch=get_json, now=None):
    now=now or datetime.now(timezone.utc)
    result={'games':{},'warnings':[],'sources':{},'metrics':{}}
    cache={}; boxes={}
    def load(path, store):
        if path not in store:
            try: store[path]=fetch(path)
            except Exception as exc:
                store[path]=None; result['warnings'].append(f'{path}: {exc}')
        return store[path]
    for g in data['games']:
        start=utc_datetime(g['start_utc']); cutoff=min(start,now); gt=2; year=start.year-(start.month<7); season=year*10000+year+1
        h,a=(g[s]['abbrev'] for s in ('home','away')); out=[]
        def add(cat,text,rows,**extra):
            out.append({'category':cat,'text':text,'verified':True,'source':'https://api-web.nhle.com/v1/club-schedule-season + /gamecenter/{id}/landing (where applicable)','evidence':{'sample_size':len(rows),'games':rows,**extra}})
        histories={}; metrics={}; result['metrics'][str(g['id'])]=metrics
        for code in (h,a):
            path=f'/club-schedule-season/{code}/{season}'; payload=load(path,cache)
            if not isinstance(payload,dict) or not isinstance(payload.get('games'),list):
                result['warnings'].append(f'{code}: chybí rozpis sezony'); continue
            rows={}
            for x in payload.get('games',[]):
                try:
                    if x['gameType']!=gt or x['gameState'] not in ('OFF','FINAL') or utc_datetime(x['startTimeUTC'])>=cutoff or x['id']==g['id']: continue
                    home,away=x['homeTeam'],x['awayTeam']; us,them=(home,away) if home['abbrev']==code else (away,home)
                    if us['abbrev']!=code or not all(type(t['score']) is int and t['score']>=0 for t in (us,them)):continue
                    rows[x['id']]={'id':x['id'],'start':x['startTimeUTC'],'opponent':them['abbrev'],'gf':us['score'],'ga':them['score'],'home':us is home,'shootout':x.get('gameOutcome',{}).get('lastPeriodType')=='SO'}
                except (KeyError,ValueError,TypeError):continue
            rows=sorted(rows.values(),key=lambda x:utc_datetime(x['start']),reverse=True); histories[code]=rows
            m=metrics[code]={'history_count':len(rows),'recent_games':rows[:10]}; mutual=[x for x in rows if x['opponent']==(a if code==h else h)]; m['h2h']=[sum(x['gf']>x['ga'] for x in mutual),sum(x['gf']<x['ga'] for x in mutual)]
            if rows:
                hours=(start-utc_datetime(rows[0]['start'])).total_seconds()/3600
                m['rest_hours']=hours
                if 0<hours<=30:add('rest',f'{code} čeká další zápas po {round(hours)} hodinách od začátku předchozího.',rows[:1],hours=hours)
            recent=rows[:10]
            if len(recent)<10:continue
            gf=sum(x['gf'] for x in recent)/10; ga=sum(x['ga'] for x in recent)/10
            m.update(gf=gf,ga=ga)
            if gf>=3.8 or ga>=3.8 or ga<=2:
                add('scoring',f'{code}: za posledních 10 utkání průměr {gf:.1f} vstřelených a {ga:.1f} inkasovaných gólů.'.replace('.',','),recent,gf=gf,ga=ga)
            goals=[]
            for row in recent:
                p=load(f"/gamecenter/{row['id']}/landing",boxes)
                if not p:continue
                try:
                    periods=p['summary']['scoring']; events=[(q['periodDescriptor']['number'],z['teamAbbrev']['default']) for q in periods if q['periodDescriptor']['periodType']!='SO' for z in q['goals']]
                    if not events or len(events) != row['gf']+row['ga']-int(row['shootout']):continue
                    if any(c not in (code,row['opponent']) for _,c in events):continue
                    if sum(c==code for _,c in events)!=row['gf']-int(row['shootout'] and row['gf']>row['ga']):continue
                    goals.append({**row,'first':events[0][1],'period_goals':[sum(n==i and c==code for n,c in events) for i in (1,2,3)]})
                except (KeyError,TypeError):continue
            m['landing_sample']=len(goals); m['goal_evidence']=goals
            if len(goals)==10:
                first=sum(x['first']==code for x in goals)
                m['first_pct']=first*10
                if first>=8 or first<=2:add('first_goal_comebacks',f'{code} vstřelil první gól v {first} z posledních 10 utkání.',goals,first_goals=first)
                totals=[sum(x['period_goals'][i] for x in goals) for i in range(3)]; total=sum(totals)
                m['period_totals']=totals
                if total>=15 and max(totals)/total>=.45:
                    i=totals.index(max(totals));add('period_goals',f'{code}: {totals[i]} z {total} gólů v základní hrací době padlo ve {i+1}. třetině (posl. 10).',goals,period_totals=totals)
        mutual=[x for x in histories.get(h,[]) if x['opponent']==a]
        if h in metrics and a in metrics and metrics[h]['h2h']!=metrics[a]['h2h'][::-1]:
            metrics[h].pop('h2h'); metrics[a].pop('h2h'); result['warnings'].append('Nesoulad vzájemných zápasů')
        if len(mutual)>=5:
            wins=sum(x['gf']>x['ga'] for x in mutual); leader=h if wins>=4 else a if wins<=len(mutual)-4 else None
            if leader:add('h2h',f'{leader} vyhrál {max(wins,len(mutual)-wins)} z {len(mutual)} vzájemných utkání v této sezoně.',mutual,wins=max(wins,len(mutual)-wins))
        result['games'][str(g['id'])]=out
    result['sources']={'schedule_paths':list(cache),'landing_paths':list(boxes),'retrieved_utc':now.isoformat()}
    return result
