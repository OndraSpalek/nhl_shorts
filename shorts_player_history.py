"""Auditable player and historical facts from completed regular-season games only."""
from datetime import datetime, timezone
from shorts_data import get_json, utc_datetime

def enrich(data, fetch=get_json, now=None):
    now=now or datetime.now(timezone.utc)
    result={'games':{},'metrics':{},'warnings':[],'sources':[]}; cache={}
    def load(path):
        if path not in cache:
            try:
                cache[path]=fetch(path)
                if not isinstance(cache[path],dict): raise ValueError('Invalid payload')
            except Exception as e:
                cache[path]=None; result['warnings'].append(f'{path}: {type(e).__name__}')
        return cache[path] or {}
    def history(code,season,cutoff):
        p=load(f'/club-schedule-season/{code}/{season}')
        if not isinstance(p.get('games'),list): return None
        rows={}
        for x in p['games']:
            try:
                if x['gameType']!=2 or x['gameState'] not in ('OFF','FINAL') or utc_datetime(x['startTimeUTC'])>=cutoff: continue
                h,a=x['homeTeam'],x['awayTeam']; side='homeTeam' if h['abbrev']==code else 'awayTeam'
                u,v=(h,a) if side=='homeTeam' else (a,h)
                if u['abbrev']!=code or type(u['score'])!=int or type(v['score'])!=int or u['score']==v['score']: continue
                rows[x['id']]={'id':x['id'],'start':x['startTimeUTC'],'side':side,'opponent':v['abbrev'],'win':u['score']>v['score'],'gf':u['score'],'ga':v['score']}
            except (KeyError,TypeError,ValueError): continue
        return sorted(rows.values(),key=lambda r:r['start'],reverse=True)
    for g in data['games']:
        cutoff=min(now,utc_datetime(g['start_utc'])); start=utc_datetime(g['start_utc']); y=start.year-(start.month<7); season=y*10000+y+1
        gid=str(g['id']); out=[]; result['games'][gid]=out; metrics={}; result['metrics'][gid]=metrics
        def add(cat,text,rows,**e):
            out.append({'category':cat,'text':text,'verified':True,'source':'NHL API: '+e.pop('endpoint','/gamecenter/{id}/boxscore'), 'evidence':{'sample_size':len(rows),'games':rows,**e}})
        h,a=[g[s]['abbrev'] for s in ('home','away')]
        for code in (h,a):
            rows=history(code,season,cutoff); m=metrics[code]={}
            if rows is None: continue
            players={}; goalies={}; appearances=[]; complete=True
            for r in rows:
                box=load(f"/gamecenter/{r['id']}/boxscore"); side=box.get('playerByGameStats',{}).get(r['side'],{})
                sk=side.get('forwards',[])+side.get('defense',[]); gs=side.get('goalies',[])
                if not sk or not gs or any(not all(type(p.get(k))==int for k in ('playerId','goals','assists','points')) for p in sk): complete=False; continue
                for p in sk:
                    pid=p['playerId']; name=p.get('name',{}).get('default',str(pid)); q=players.setdefault(pid,{'player_id':pid,'name':name,'games':[]})
                    q['games'].append({'id':r['id'],'goals':p['goals'],'assists':p['assists'],'points':p['points']})
                for p in gs:
                    try:
                        saves,shots=p['saves'],p['shotsAgainst']; toi=p['toi']; mm,ss=map(int,toi.split(':')); sec=mm*60+ss
                        if sec<=0: continue
                        if not (type(saves)==type(shots)==int and 0<=saves<=shots): raise ValueError()
                        q=goalies.setdefault(p['playerId'],{'name':p['name']['default'],'games':[]}); q['games'].append({'id':r['id'],'saves':saves,'shots':shots,'seconds':sec,'starter':p.get('starter')})
                    except (KeyError,TypeError,ValueError): complete=False
                appearances.append(r['id'])
            m['boxscore_sample']=len(appearances); m['schedule_sample']=len(rows)
            if complete and len(appearances)==len(rows):
                for q in players.values():
                    games=q['games']; q.update({k:sum(x[k] for x in games) for k in ('goals','assists','points')}); q['last5_points']=sum(x['points'] for x in games[:5]); q['last5_goals']=sum(x['goals'] for x in games[:5])
                    for k in ('points','goals'):
                        n=0
                        for x in games:
                            if not x[k]: break
                            n+=1
                        q[k+'_streak']=n
                    if games[0]['id']==rows[0]['id'] and (q['points_streak']>=7 or q['goals_streak']>=4):
                        k='goals' if q['goals_streak']>=4 else 'points'; n=q[k+'_streak']; add('player_streak',f"{code}: {q['name']} {'skóroval' if k=='goals' else 'bodoval'} v {n} svých utkáních v řadě.",games[:n],point_streak=q['points_streak'],goal_streak=q['goals_streak'])
                m['players']=sorted(players.values(),key=lambda q:-q['points'])
                for q in goalies.values():
                    games=q['games']; shots=sum(x['shots'] for x in games); saves=sum(x['saves'] for x in games); sec=sum(x['seconds'] for x in games); q.update(gp=len(games),starts=sum(x['starter'] is True for x in games) if all(type(x['starter'])==bool for x in games) else None,save_pct=100*saves/shots if shots else None,gaa=3600*(shots-saves)/sec)
                    if shots>=100 and q['save_pct']>=92:
                        add('goalie',f"{code}: {q['name']} má v sezoně úspěšnost zákroků {q['save_pct']:.1f} %.",games,shots=shots)
                m['goalies']=list(goalies.values())
                if players:
                    q=m['players'][0]; add('player_leader',f"{code}: {q['name']} nasbíral za tým {q['points']} bodů ({q['goals']}+{q['assists']}).",q['games'])
            # Historical head-to-head is separate from the current-season card.
            if code==h:
                prev=history(code,(y-1)*10000+y,cutoff)
                if prev is not None:
                    mutual=[r for r in rows+prev if r['opponent']==a][:5]
                    if len(mutual)==5:
                        w=sum(r['win'] for r in mutual); m['historical_h2h']=mutual
                        if max(w,5-w)>=4: add('historical_h2h',f'{h if w>=3 else a} vyhrál {max(w,5-w)} z posledních 5 vzájemných duelů (tato a minulá sezona).',mutual,wins=max(w,5-w),endpoint='/club-schedule-season/{team}/{season}')
    result['sources']=list(cache); return result
