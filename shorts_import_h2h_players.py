#!/usr/bin/env python3
"""H2H from NHL club schedules; optional verified player streak/milestone CSV.

Player CSV must be independently verified and contain a source URL; this module
never infers player streaks from season aggregates.
"""
import argparse
import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from shorts_data import get_json, utc_datetime


def _finished(g, cutoff):
    return (g.get('gameState') in ('OFF', 'FINAL') and g.get('gameType') == 2
            and g.get('startTimeUTC') and utc_datetime(g['startTimeUTC']) < cutoff
            and isinstance((g.get('homeTeam') or {}).get('score'), int)
            and isinstance((g.get('awayTeam') or {}).get('score'), int))


def _season_codes(day, count=4):
    y, m = map(int, day.split('-')[:2]); start = y if m >= 7 else y - 1
    return [f'{s}{s+1}' for s in range(start, start-count, -1)]


def _fetch_history(team, day, fetch):
    games = {}
    warnings = []
    for season in _season_codes(day):
        try:
            payload = fetch(f'/club-schedule-season/{team}/{season}')
            for g in payload.get('games', []):
                if g.get('id') is not None:
                    games[g['id']] = g
        except Exception as exc:
            warnings.append(f'H2H {team} {season}: {type(exc).__name__}: {exc}')
    return list(games.values()), warnings


def _h2h(game, history, cutoff):
    home, away = game['home']['abbrev'], game['away']['abbrev']
    matches = []
    for g in history:
        if not _finished(g, cutoff):
            continue
        h, a = g.get('homeTeam') or {}, g.get('awayTeam') or {}
        if {h.get('abbrev'), a.get('abbrev')} != {home, away}:
            continue
        winner = h['abbrev'] if h['score'] > a['score'] else a['abbrev']
        matches.append((utc_datetime(g['startTimeUTC']), str(g['id']), winner))
    matches.sort(reverse=True)
    last = matches[:5]
    if len(last) < 5:
        return None
    wins_home = sum(w == home for _, _, w in last)
    leader, wins = (home, wins_home) if wins_home >= 3 else (away, 5-wins_home)
    if wins < 4:
        return None
    return {'category': 'h2h', 'text': f'{leader} vyhrál {wins} z posledních 5 vzájemných zápasů',
            'evidence': {'wins': wins, 'sample_size': 5, 'game_ids': [gid for _, gid, _ in last]},
            'source': 'NHL API /club-schedule-season, základní část', 'verified': True}


def _player_facts(csv_file, games, cutoff):
    """Import optional audited player facts with exact game ID and source URL.

    Required: game_id, category, player, team, text, sample_size, source,
    verified, remaining, point_streak, goal_streak, checked_at_utc.
    """
    result = {str(g['id']): [] for g in games}
    warnings = []
    if not csv_file or not Path(csv_file).exists():
        return result, warnings
    with open(csv_file, encoding='utf-8-sig', newline='') as handle:
        for line, row in enumerate(csv.DictReader(handle), 2):
            try:
                gid = str(row['game_id']).strip()
                if gid not in result or row['verified'].strip().lower() != 'true':
                    continue
                cat = row['category'].strip()
                if cat not in ('milestone', 'player_streak'):
                    continue
                g = next(x for x in games if str(x['id']) == gid)
                if row['team'].strip() not in (g['home']['abbrev'], g['away']['abbrev']):
                    continue
                checked = utc_datetime(row['checked_at_utc'])
                if checked > cutoff or (cutoff - checked).total_seconds() > 48*3600:
                    continue
                source = row['source'].strip()
                if not source.startswith('https://'):
                    continue
                sample = int(row['sample_size'])
                if sample < 1 or not row['player'].strip() or not row['text'].strip():
                    continue
                ev = {'sample_size': sample, 'player': row['player'].strip(), 'team': row['team'].strip()}
                for field in ('remaining', 'point_streak', 'goal_streak'):
                    ev[field] = int(row.get(field) or 0)
                if cat == 'milestone' and not (1 <= ev['remaining'] <= 2):
                    continue
                if cat == 'player_streak' and ev['point_streak'] < 7 and ev['goal_streak'] < 4:
                    continue
                result[gid].append({'category': cat, 'text': row['text'].strip()[:180],
                                    'evidence': ev, 'source': source, 'verified': True})
            except (KeyError, ValueError, TypeError) as exc:
                warnings.append(f'Hráčské CSV řádek {line}: {exc}')
    return result, warnings


def generate(data, fetch=get_json, history=None, players_csv=None, now=None):
    now = now or datetime.now(timezone.utc)
    if now.tzinfo is None:
        raise ValueError('now must be timezone-aware')
    games = data.get('games', [])
    # At preview time, never include a result from a future game. Also restrict
    # each H2H candidate to its own match start.
    teams = sorted({g['home']['abbrev'] for g in games})
    cached, warnings = {}, []
    for team in teams:
        if history is not None:
            cached[team] = history.get(team, [])
        else:
            cached[team], w = _fetch_history(team, data['local_date'], fetch)
            warnings.extend(w)
    players, pw = _player_facts(players_csv, games, now)
    warnings.extend(pw)
    result = {}
    for g in games:
        gid = str(g['id'])
        cutoff = min(utc_datetime(g['start_utc']), now)
        fact = _h2h(g, cached[g['home']['abbrev']], cutoff)
        result[gid] = ([fact] if fact else []) + players[gid]
    return {'games': result, 'warnings': warnings, 'generated_at_utc': now.isoformat()}


def merge(base, extra):
    output = {'games': {str(k): list(v) for k, v in base.get('games', {}).items()},
              'warnings': list(base.get('warnings', [])) + list(extra.get('warnings', []))}
    for gid, facts in extra.get('games', {}).items():
        output['games'].setdefault(str(gid), []).extend(facts)
    return output


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--input', type=Path, required=True)
    p.add_argument('--base-facts', type=Path)
    p.add_argument('--players-csv', type=Path)
    p.add_argument('--output', type=Path, default=Path('shorts_facts.json'))
    a = p.parse_args()
    data = json.loads(a.input.read_text(encoding='utf-8'))
    base = json.loads(a.base_facts.read_text(encoding='utf-8')) if a.base_facts else {}
    out = merge(base, generate(data, players_csv=a.players_csv))
    a.output.parent.mkdir(parents=True, exist_ok=True)
    a.output.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f'Vytvořeno {sum(map(len, out["games"].values()))} ověřených zajímavostí; upozornění: {len(out["warnings"])}')


if __name__ == '__main__':
    main()
