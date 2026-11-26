"""Read-only YouTube collection. No upload or modification of channel."""
import argparse, csv, datetime as dt, json, os, re, sqlite3, urllib.request, urllib.parse
from pathlib import Path
UTC=dt.timezone.utc
METRICS='views,engagedViews,estimatedMinutesWatched,averageViewDuration,averageViewPercentage,likes,comments,shares,subscribersGained,subscribersLost'
class API:
    def __init__(self):
        data=urllib.parse.urlencode({k:os.environ['YT_'+k.upper()] for k in ('client_id','client_secret','refresh_token') }|{'grant_type':'refresh_token'}).encode()
        with urllib.request.urlopen('https://oauth2.googleapis.com/token',data,timeout=30) as r: self.token=json.load(r)['access_token']
    def get(self,base,**params):
        req=urllib.request.Request(base+'?'+urllib.parse.urlencode(params),headers={'Authorization':'Bearer '+self.token})
        with urllib.request.urlopen(req,timeout=45) as r:return json.load(r)
    def report(self,**params):return self.get('https://youtubeanalytics.googleapis.com/v2/reports',ids='channel==MINE',**params)
    def video(self,id):return self.get('https://www.googleapis.com/youtube/v3/videos',part='snippet,contentDetails,statistics',id=id)

def rows(report):
    names=[x['name'] for x in report.get('columnHeaders',[])]
    return [dict(zip(names,r)) for r in report.get('rows',[])]
def collect(api,registry,db,today):
    db.execute('CREATE TABLE IF NOT EXISTS snapshots(video_id TEXT, day TEXT, kind TEXT, payload TEXT, PRIMARY KEY(video_id,day,kind))')
    errors=[]
    for item in registry:
        vid=item['video_id']; start=dt.date.fromisoformat(item['published_date']); end=today-dt.timedelta(days=1)
        if not re.fullmatch(r'[A-Za-z0-9_-]{11}',vid):raise ValueError('Invalid video ID')
        if start>end:continue
        params=dict(startDate=start.isoformat(),endDate=end.isoformat(),filters='video=='+vid)
        calls={'metadata':lambda:api.video(vid),'daily':lambda:api.report(**params,metrics=METRICS,dimensions='day',sort='day'),'retention':lambda:api.report(**params,metrics='audienceWatchRatio,relativeRetentionPerformance',dimensions='elapsedVideoTimeRatio',sort='elapsedVideoTimeRatio')}
        for kind,call in calls.items():
            try:
                result=call(); payload=result if kind=='metadata' else rows(result)
                db.execute('INSERT OR REPLACE INTO snapshots VALUES(?,?,?,?)',(vid,today.isoformat(),kind,json.dumps(payload,ensure_ascii=False)))
                db.commit()
            except Exception as e:errors.append({'video_id':vid,'kind':kind,'error':type(e).__name__,'http_status':getattr(e,'code',None)})
    return errors

def main():
    p=argparse.ArgumentParser();p.add_argument('--registry',default='youtube_registry.json');p.add_argument('--out',default='analytics_data');p.add_argument('--fixture',action='store_true');a=p.parse_args()
    registry=json.loads(Path(a.registry).read_text());out=Path(a.out);out.mkdir(parents=True,exist_ok=True)
    if a.fixture:
        from test_youtube import FakeAPI
        api=FakeAPI();registry=[{'video_id':'abcdefghijk','published_date':'2026-01-01'}]
    else:api=API() if registry else None
    with sqlite3.connect(out/'analytics.db') as db:
        errors=collect(api,registry,db,dt.datetime.now(UTC).date())
        records=db.execute('SELECT * FROM snapshots ORDER BY day,video_id,kind').fetchall()
    (out/'snapshots.json').write_text(json.dumps([dict(zip(('video_id','day','kind','payload'),(v,d,k,json.loads(s)))) for v,d,k,s in records],ensure_ascii=False,indent=2))
    (out/'status.json').write_text(json.dumps({'mode':'fixture' if a.fixture else 'live','registered':len(registry),'snapshots':len(records),'errors':errors},indent=2))
    if errors:raise SystemExit(1)
if __name__=='__main__':main()
