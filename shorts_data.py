#!/usr/bin/env python3
"""Be6player Shorts: schedule, standings and team form. No changes to email workflow.

Usage: python shorts_data.py --date 2026-11-22 --output shorts_data.json
       python shorts_data.py --fixture sample_api.json --date 2026-11-22
Fixture format: {"schedule": {...}, "standings": {...}, "club_schedules": {"CAR": {...}}}
"""
import argparse
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import requests

PRAGUE = ZoneInfo('Europe/Prague')
API = 'https://api-web.nhle.com/v1'
HEADERS = {'User-Agent': 'Be6player-Shorts/1.0'}


def utc_datetime(value):
    return datetime.fromisoformat(value.replace('Z', '+00:00')).astimezone(timezone.utc)


def get_json(path, session=None):
    session = session or requests
    r = session.get(API + path, headers=HEADERS, timeout=30)
    r.raise_for_status()
    return r.json()


def last_five(games, team, before, venue=None):
    """Completed games strictly before cutoff, optionally H/R. Newest first."""
    selected = []
    for g in games:
        if g.get('gameState') not in ('OFF', 'FINAL'):
            continue
        if not g.get('startTimeUTC') or utc_datetime(g['startTimeUTC']) >= before:
            continue
        home = g.get('homeTeam') or {}
        away = g.get('awayTeam') or {}
        if home.get('abbrev') == team:
            side, us, them = 'H', home, away
        elif away.get('abbrev') == team:
            side, us, them = 'R', away, home
        else:
            continue
        if venue and venue != side:
            continue
        if not isinstance(us.get('score'), int) or not isinstance(them.get('score'), int):
            continue
        if us['score'] > them['score']:
            result = 'V'
        elif g.get('gameOutcome', {}).get('lastPeriodType') in ('OT', 'SO'):
            result = 'PP'
        else:
            result = 'P'
        selected.append((utc_datetime(g['startTimeUTC']), {'date': g.get('gameDate'), 'venue': side,
            'opponent': them.get('abbrev'), 'score': f"{us['score']}:{them['score']}", 'result': result}))
    selected.sort(key=lambda pair: pair[0], reverse=True)
    results = [item for _, item in selected[:5]]
    v = sum(x['result'] == 'V' for x in results)
    p = sum(x['result'] == 'P' for x in results)
    pp = sum(x['result'] == 'PP' for x in results)
    return {'V': v, 'P': p, 'PP': pp, 'games': results,
            'points_pct': round((2*v+pp)/(2*len(results))*100, 1) if results else None,
            'sample_size': len(results)}


def current_streak(games, team, before):
    form = last_five(games, team, before)
    # Need entire history, not just last five: reconstruct through helper using extended count.
    valid = []
    for g in games:
        if g.get('gameState') not in ('OFF','FINAL') or not g.get('startTimeUTC'):
            continue
        if utc_datetime(g['startTimeUTC']) >= before:
            continue
        h, a = g.get('homeTeam') or {}, g.get('awayTeam') or {}
        if team not in (h.get('abbrev'), a.get('abbrev')):
            continue
        us, them = (h,a) if h.get('abbrev') == team else (a,h)
        if not isinstance(us.get('score'),int) or not isinstance(them.get('score'),int):
            continue
        valid.append((utc_datetime(g['startTimeUTC']), us['score'] > them['score']))
    valid.sort(reverse=True)
    if not valid:
        return {'type': None, 'length': 0}
    first = valid[0][1]
    count = 0
    for _, won in valid:
        if won != first:
            break
        count += 1
    return {'type': 'vyhry' if first else 'bez_vyhry', 'length': count}


def standings_index(payload):
    return {t['teamAbbrev']['default']: t for t in payload.get('standings', [])
            if isinstance(t.get('teamAbbrev'), dict) and t['teamAbbrev'].get('default')}


def team_summary(abbrev, standings, schedules, before):
    t = standings.get(abbrev) or {}
    games = schedules.get(abbrev, {}).get('games', [])
    return {'abbrev': abbrev, 'wins': t.get('wins'), 'losses': t.get('losses'),
        'ot_losses': t.get('otLosses'), 'conference_rank': t.get('conferenceSequence'),
        'conference': t.get('conferenceAbbrev'), 'form_all': last_five(games, abbrev, before),
        'form_home': last_five(games, abbrev, before, 'H'),
        'form_away': last_five(games, abbrev, before, 'R'),
        'streak': current_streak(games, abbrev, before)}


def build(day, fetch=get_json, fixture=None):
    """Czech local day 10:00 -> next day 10:00; schedule may cross US date boundaries."""
    start = datetime.fromisoformat(day).replace(tzinfo=PRAGUE, hour=10)
    end = (start + timedelta(days=1)).replace(hour=10)
    schedule_dates = {(start + timedelta(days=d)).date().isoformat() for d in (-1,0,1)}
    schedule = fixture.get('schedule') if fixture else None
    def schedule_for(d):
        if fixture:
            if isinstance(schedule, dict) and 'gameWeek' in schedule:
                return schedule
            return (schedule or {}).get(d, {'gameWeek': []})
        return fetch(f'/schedule/{d}')
    games_by_id = {}
    for d in sorted(schedule_dates):
        for block in schedule_for(d).get('gameWeek', []):
            for g in block.get('games', []):
                if g.get('gameType') not in (2,3) or not g.get('startTimeUTC'):
                    continue
                at = utc_datetime(g['startTimeUTC']).astimezone(PRAGUE)
                if start <= at < end:
                    games_by_id[g['id']] = g
    standings_data = fixture.get('standings', {}) if fixture else fetch(f'/standings/{day}')
    standings = standings_index(standings_data)
    teams = {t.get('abbrev') for g in games_by_id.values() for t in (g['homeTeam'],g['awayTeam'])}
    schedules = {}
    for team in sorted(teams - {None}):
        schedules[team] = (fixture.get('club_schedules', {}).get(team, {'games': []}) if fixture
                           else fetch(f'/club-schedule-season/{team}/now'))
    output = []
    for g in sorted(games_by_id.values(), key=lambda g: g['startTimeUTC']):
        at = utc_datetime(g['startTimeUTC'])
        home, away = g['homeTeam']['abbrev'], g['awayTeam']['abbrev']
        cutoff=min(at,datetime.now(timezone.utc))
        scoped={k:{'games':[x for x in v.get('games',[]) if x.get('gameType',g['gameType'])==g['gameType']]} for k,v in schedules.items()}
        snapshot=standings if fixture or at>datetime.now(timezone.utc) else {}
        output.append({'id': g['id'], 'start_utc': at.isoformat(),
            'start_prague': at.astimezone(PRAGUE).isoformat(), 'game_type': g['gameType'],
            'home': team_summary(home, snapshot, scoped, cutoff),
            'away': team_summary(away, snapshot, scoped, cutoff)})
    return {'brand': 'Be6player', 'local_date': day, 'timezone': 'Europe/Prague',
        'window_start': start.isoformat(), 'window_end': end.isoformat(),
        'games': output, 'game_count': len(output),
        'note': 'Forma je pouze z dokoncenych zapasu pred zacatkem utkani. Sezonni tabulka je snapshot k datu API.'}


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--date', default=datetime.now(PRAGUE).date().isoformat())
    p.add_argument('--fixture', type=Path)
    p.add_argument('--output', type=Path, default=Path('shorts_data.json'))
    args = p.parse_args()
    fixture = json.loads(args.fixture.read_text(encoding='utf-8')) if args.fixture else None
    result = build(args.date, fixture=fixture)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f"Zapsano {result['game_count']} zapasu do {args.output}")


if __name__ == '__main__':
    main()
