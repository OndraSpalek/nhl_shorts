"""Experimental chronological ensemble; missing historical inputs remain missing."""
from datetime import datetime, timezone, timedelta, date
from collections import defaultdict
from math import exp, log
import numpy as np
from shorts_data import get_json, utc_datetime
from shorts_elo import evaluate, probability

FEATURES=['elo','form5','form10','gf','ga','venue','rest','back_to_back','h2h','shots','faceoff','pp','pk','goalie_sv','goalie_gaa','player_points','player_form','injuries']

def mean(xs):
    xs=[x for x in xs if x is not None]; return sum(xs)/len(xs) if xs else None

def box_metrics(payload,side):
    team=payload.get(side+'Team',{}); stats=payload.get('playerByGameStats',{}).get(side+'Team',{})
    skaters=stats.get('forwards',[])+stats.get('defense',[])
    goalies=stats.get('goalies',[])
    def num(x):
        try: return float(x.strip('%')) if isinstance(x,str) else float(x)
        except (ValueError,TypeError): return None
    saves=sum(g.get('saves',0) or 0 for g in goalies); shots=sum(g.get('shotsAgainst',0) or 0 for g in goalies)
    mins=0
    for g in goalies:
        try: m,s=map(int,g['toi'].split(':')); mins+=m+s/60
        except (KeyError,ValueError,AttributeError): pass
    return {'shots':num(team.get('sog')),'faceoff':None,'pp':None,'pk':None,'goalie_sv':saves/shots if shots else None,'goalie_gaa':60*(shots-saves)/mins if shots and mins else None,'player_points':max((p.get('points',0) or 0 for p in skaters),default=None)}

def dataset(rows,targets):
    history=defaultdict(list); elo=defaultdict(lambda:1500.); pair=defaultdict(list); days=defaultdict(lambda:[[],[]]); X=[]; Y=[]; goals=[]; dates=[]; ids=[]; forecasts={}
    for r in rows: days[r['t'].date()][0].append(r)
    for r in targets: days[r['t'].date()][1].append(r)
    def features(r):
        h,a,t=r['h'],r['a'],r['t']; H,A=history[h],history[a]
        if min(len(H),len(A))<20:return None
        def side(hist,venue):
            last=hist[-10:]; rest=(t-hist[-1]['t']).total_seconds()/3600
            d={'form5':mean([q['win'] for q in last[-5:]]),'form10':mean([q['win'] for q in last]),'gf':mean([q['gf'] for q in last]),'ga':mean([q['ga'] for q in last]),'venue':mean([q['win'] for q in hist if q['home']==venue][-10:]),'rest':min(rest,168),'back_to_back':int(rest<=30),'player_form':mean([q.get('player_points') for q in last[-5:]])}
            for k in ('shots','faceoff','pp','pk','goalie_sv','goalie_gaa','player_points'):d[k]=mean([q.get(k) for q in last])
            return d
        u,v=side(H,True),side(A,False); x={'elo':elo[h]-elo[a],'h2h':mean(pair[h,a][-10:]),'injuries':None}
        if x['h2h'] is not None:x['h2h']-=.5
        for k in u:x[k]=u[k]-v[k] if u[k] is not None and v[k] is not None else None
        lam=(max(.2,(u['gf']+v['ga'])/2),max(.2,(v['gf']+u['ga'])/2))
        return [x.get(k) for k in FEATURES],lam
    for day,(games,upcoming) in sorted(days.items()):
        for r in upcoming:
            f=features(r)
            if f:forecasts[str(r['id'])]=f
        changes=defaultdict(float)
        for r in games:
            f=features(r); h,a=r['h'],r['a']; y=int(r['hs']>r['as']); p=probability(elo[h],elo[a]); changes[h]+=20*(y-p);changes[a]-=20*(y-p)
            if f:X.append(f[0]);goals.append(f[1]);Y.append(y);dates.append(day);ids.append(r['id'])
        for r in games:
            h,a=r['h'],r['a'];y=int(r['hs']>r['as']);pair[h,a].append(y);pair[a,h].append(1-y)
            for team,side,gf,ga,w in [(h,'home',r['hs'],r['as'],y),(a,'away',r['as'],r['hs'],1-y)]:history[team].append(dict(r.get(side,{}),t=r['t'],gf=gf,ga=ga,win=w,home=side=='home'))
        for k,v in changes.items():elo[k]+=v
    return X,np.array(Y),goals,dates,forecasts

def poisson(lam):
    from scipy.stats import poisson as dist
    h,a=lam; p=dist.pmf(np.arange(40),h);q=dist.pmf(np.arange(40),a); m=np.outer(p,q);return float(np.tril(m,-1).sum()+.5*np.trace(m))

def metrics(y,p):
    p=np.clip(p,1e-6,1-1e-6);return {'sample_size':len(y),'accuracy':float(np.mean((p>=.5)==y)),'brier':float(np.mean((p-y)**2)),'log_loss':float(-np.mean(y*np.log(p)+(1-y)*np.log(1-p)))}

def fit(rows,targets):
    from sklearn.linear_model import LogisticRegression
    from sklearn.ensemble import HistGradientBoostingClassifier
    from sklearn.impute import SimpleImputer
    from sklearn.pipeline import make_pipeline
    from sklearn.preprocessing import StandardScaler
    X,y,g,d,forecasts=dataset(rows,targets); n=len(y)
    if n<300:return {'status':'insufficient_training','games':{},'sample_size':n}
    unique=sorted(set(d)); b,c,e=[unique[int(len(unique)*v)] for v in (.55,.7,.85)]; d=np.array(d); tr=d<b; val=(d>=b)&(d<c); cal=(d>=c)&(d<e); test=d>=e
    X=np.array(X,dtype=float); g=np.array(g); keep=np.isfinite(X[tr]).sum(axis=0)>=30
    if any(len(set(y[m]))<2 for m in (tr,val,cal,test)):return {'status':'insufficient_classes','games':{}}
    lr=make_pipeline(SimpleImputer(strategy='median',add_indicator=True),StandardScaler(),LogisticRegression(max_iter=1000)); gb=HistGradientBoostingClassifier(max_iter=80,max_leaf_nodes=15,random_state=42)
    lr.fit(X[tr][:,keep],y[tr]);gb.fit(X[tr][:,keep],y[tr])
    def predict(x,lam):return np.column_stack([[probability(1500+v,1500) for v in x[:,0]],[poisson(v) for v in lam],lr.predict_proba(x[:,keep])[:,1],gb.predict_proba(x[:,keep])[:,1]])
    p=predict(X,g); losses=np.mean((p[val]-y[val,None])**2,axis=0); weights=1/np.maximum(losses,1e-6);weights/=weights.sum(); raw=p@weights
    calibrator=LogisticRegression().fit(raw[cal,None],y[cal]); final=calibrator.predict_proba(raw[:,None])[:,1]
    names=['elo','poisson','logistic','boosting']; report={k:metrics(y[test],p[test,i]) for i,k in enumerate(names)};report['ensemble']=metrics(y[test],final[test]);report['baseline']=metrics(y[test],np.full(test.sum(),y[tr].mean()))
    out={}
    for gid,(x,lam) in forecasts.items():
        pp=predict(np.array([x],dtype=float),[lam])[0]; prob=float(calibrator.predict_proba([[pp@weights]])[0,1]);out[gid]={'home_probability':prob,'away_probability':1-prob,'expected_goals_home':lam[0],'expected_goals_away':lam[1],'models':dict(zip(names,map(float,pp))),'missing_features':[k for k,v in zip(FEATURES,x) if v is None]}
    return {'status':'experimental_backtest_only','games':out,'backtest':report,'weights':dict(zip(names,map(float,weights))),'feature_coverage':dict(zip(FEATURES,np.isfinite(X).sum(axis=0).tolist())),'training_features':[k for k,v in zip(FEATURES,keep) if v],'split_dates':list(map(str,(b,c,e))),'publish_enabled':False}

def enrich(data,fetch=get_json,now=None):
    now=now or datetime.now(timezone.utc); result={'status':'unavailable','games':{},'warnings':[],'sources':[],'model':'ensemble_v805','publish_enabled':False}
    targets=[{'id':g['id'],'t':utc_datetime(g['start_utc']),'h':g['home']['abbrev'],'a':g['away']['abbrev']} for g in data['games'] if utc_datetime(g['start_utc'])>now]
    if not targets:return result
    cutoff=min(now,min(r['t'] for r in targets));year=cutoff.year-(cutoff.month<7);d=date(year-9,9,1);rows={}
    try:
        while d<=cutoff.date():
            path=f'/schedule/{d}';result['sources'].append(path);week=fetch(path)['gameWeek'];end=max(date.fromisoformat(b['date']) for b in week)
            if end<d:raise ValueError('schedule window')
            for block in week:
                for g in block['games']:
                    if g['gameType']!=2 or g['gameState'] not in ('OFF','FINAL'):continue
                    t=utc_datetime(g['startTimeUTC']);h,a=g['homeTeam'],g['awayTeam']
                    if t.date()>=cutoff.date():continue
                    hs,as_=h['score'],a['score']
                    if type(hs)!=int or type(as_)!=int or hs==as_:raise ValueError('invalid score')
                    rows[g['id']]=dict(id=g['id'],t=t,h=h['abbrev'],a=a['abbrev'],hs=hs,**{'as':as_})
            d=end+timedelta(days=1)
        # Optional detailed historical inputs, bounded to avoid overwhelming daily workflow.
        import os
        budget=max(0,min(20000,int(os.getenv('NHL_PREDICTION_DETAIL_GAMES','0'))))
        for r in sorted(rows.values(),key=lambda r:r['t'])[-budget:] if budget else []:
            path=f"/gamecenter/{r['id']}/boxscore"
            try:
                payload=fetch(path); result['sources'].append(path)
                for side in ('home','away'):r[side]=box_metrics(payload,side)
            except Exception as exc:
                result['warnings'].append(f'{path}: {type(exc).__name__}')
        result.update(fit(sorted(rows.values(),key=lambda r:r['t']),targets));result['training_games']=len(rows)
    except Exception as exc:result['warnings'].append(f'{type(exc).__name__}: {exc}')
    return result
