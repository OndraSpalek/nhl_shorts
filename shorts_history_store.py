"""Incremental archive, persisted by a separate workflow in a private repository."""
import json, os, time
from pathlib import Path
from datetime import date, timedelta, datetime, timezone
from shorts_data import get_json
from shorts_prediction_cache import completed_detail

def collect(fetch=get_json, limit=250):
    root=Path(os.environ.get('NHL_CACHE_DIR','prediction_cache'));root.mkdir(parents=True,exist_ok=True)
    today=datetime.now(timezone.utc).date(); year=today.year-(today.month<7)
    index=root/'schedule_index.json'; rows={}
    if index.exists(): rows=json.loads(index.read_text())
    d=date(year-9,9,1)
    while d<today:
        p=root/f'schedule-{d}.json'
        if p.exists(): week=json.loads(p.read_text())
        else:
            week=fetch(f'/schedule/{d}')['gameWeek']
            if max(date.fromisoformat(x['date']) for x in week)<today-timedelta(days=2): p.write_text(json.dumps(week))
        end=max(date.fromisoformat(x['date']) for x in week)
        if end<d: raise ValueError('schedule window')
        for block in week:
            for g in block['games']:
                if g.get('gameType')==2 and g.get('gameState') in ('OFF','FINAL') and date.fromisoformat(block['date'])<today: rows[str(g['id'])]=g['startTimeUTC']
        d=end+timedelta(days=1)
    index.write_text(json.dumps(rows))
    pending=[gid for gid in sorted(rows,key=rows.get,reverse=True) if any(not (root/f'{gid}-{e}.json').exists() for e in ('boxscore','landing'))]
    errors=[]
    for gid in pending[:limit]:
        for endpoint in ('boxscore','landing'):
            try: completed_detail(fetch,gid,endpoint);time.sleep(.15)
            except Exception as exc: errors.append(f'{gid}/{endpoint}: {type(exc).__name__}')
    report={'total':len(rows),'pending_before':len(pending),'attempted':min(limit,len(pending)),'errors':errors}
    print(json.dumps(report));return report
if __name__=='__main__': collect(limit=int(os.getenv('NHL_HISTORY_BATCH','250')))
