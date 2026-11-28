"""Explicit, timestamped status feed. No inferred injuries or starters."""
import json, os
from datetime import datetime, timezone, timedelta
from pathlib import Path

def load(now=None):
    now=now or datetime.now(timezone.utc)
    path=Path(os.getenv('NHL_STATUS_FILE','nhl_status.json'))
    if not path.exists(): return []
    rows=json.loads(path.read_text()); out=[]
    for r in rows:
        try:
            t=datetime.fromisoformat(r['observed_at'].replace('Z','+00:00'))
            if not now-timedelta(hours=24)<=t<=now: continue
            if r['status'] not in ('injured','ill','suspended','absent','returned','goalie_expected','goalie_confirmed','lineup_expected','lineup_confirmed'):continue
            if not r['source'].startswith('https://') or not r['player'] or not r['team']:continue
            out.append(r)
        except (KeyError,ValueError,TypeError):continue
    return out

def for_game(rows,g):
    return [r for r in rows if str(r.get('game_id'))==str(g['id']) and r['team'] in (g['home']['abbrev'],g['away']['abbrev'])]
