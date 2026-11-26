#!/usr/bin/env python3
"""V6.6 orchestration: real API or explicitly marked offline fixture, evidence audit, music-only render."""
import argparse, json, hashlib, sys
from pathlib import Path
from datetime import datetime, timezone
from shorts_data import build
from shorts_rank import rank
from shorts_import_stats import generate as csv_basic
from shorts_import_advanced import generate as csv_advanced
from v65 import build as make_video
from shorts_live_stats import enrich
from shorts_match_facts import enrich as match_facts
from shorts_player_history import enrich as player_history
from shorts_game_flow import enrich as game_flow
from shorts_milestones import enrich as milestones


def merge_facts(data, csv_dir, enable_csv):
    result={'games':{}, 'warnings':[], 'sources':{}}
    if not enable_csv: return result
    for label, fn in [('basic',csv_basic),('advanced',csv_advanced)]:
        try: block=fn(data,csv_dir)
        except Exception as exc:
            result['warnings'].append(f'{label}: import odmítnut: {exc}')
            continue
        result['warnings'].extend(block.get('warnings',[]))
        result['sources'][label]=block.get('sources',{})
        for key, facts in block.get('games',{}).items():
            result['games'].setdefault(str(key),[]).extend(facts)
    return result


def validate(data):
    ids=set(); starts=[]
    for game in data.get('games',[]):
        if game['id'] in ids: raise ValueError('Duplicitní game ID')
        ids.add(game['id'])
        for side in ('home','away'):
            t=game[side]
            if not t.get('abbrev') or len(t['abbrev'])!=3: raise ValueError('Chybný klub')
            for key in ('form_all','form_home','form_away'):
                f=t[key]
                if f['sample_size']>5 or f['sample_size'] != len(f['games']): raise ValueError('Nekonzistentní forma')
                if f['V']+f['P']+f['PP'] != f['sample_size']: raise ValueError('Nekonzistentní V/P/PP')
        starts.append(datetime.fromisoformat(game['start_utc']))
    if starts != sorted(starts): raise ValueError('Zápasy nejsou chronologické')
    if data['game_count'] != len(ids): raise ValueError('Nesouhlasí počet zápasů')
    return True


def execute(day, outdir, fixture_path=None, csv_dir=None, render=False, allow_demo_logos=False, seconds=8):
    outdir=Path(outdir);outdir.mkdir(parents=True,exist_ok=True)
    fixture=json.loads(Path(fixture_path).read_text(encoding='utf-8')) if fixture_path else None
    data=build(day,fixture=fixture)
    validate(data)
    data['data_mode']='OFFLINE_FIXTURE_NOT_LIVE' if fixture is not None else 'NHL_API'
    data['generated_utc']=datetime.now(timezone.utc).isoformat()
    data['data_endpoints']=['/v1/schedule/{date}','/v1/standings/{date}','/v1/club-schedule-season/{team}/now'] if fixture is None else []
    facts=enrich(data) if fixture is None else {'games':{},'warnings':['Offline demo: bez živých statistik'],'sources':{}}
    if fixture is None:
        extra=match_facts(data)
        for key, rows in extra['games'].items(): facts['games'].setdefault(key,[]).extend(rows)
        facts['warnings'].extend(extra['warnings'])
        facts['sources']['match_facts']=extra['sources']
        for g in data['games']: g['match_metrics']=extra['metrics'].get(str(g['id']),{})
        data['data_endpoints'].extend(['/v1/club-schedule-season/{team}/{season}','/v1/gamecenter/{id}/landing'])
        extra=player_history(data)
        for key, rows in extra['games'].items(): facts['games'].setdefault(key,[]).extend(rows)
        facts['warnings'].extend(extra['warnings'])
        facts['sources']['player_history']=extra['sources']
        (outdir/'player_history.json').write_text(json.dumps(extra,ensure_ascii=False,indent=2),encoding='utf-8')
        achievements=milestones(data,extra)
        for key, rows in achievements['games'].items(): facts['games'].setdefault(key,[]).extend(rows)
        facts['warnings'].extend(achievements['warnings'])
        facts['sources']['milestones']=achievements['sources']
        (outdir/'milestones.json').write_text(json.dumps(achievements,ensure_ascii=False,indent=2),encoding='utf-8')
        flow=game_flow(data)
        for key, rows in flow['games'].items(): facts['games'].setdefault(key,[]).extend(rows)
        facts['warnings'].extend(flow['warnings'])
        facts['sources']['game_flow']=flow['sources']
        (outdir/'game_flow.json').write_text(json.dumps(flow,ensure_ascii=False,indent=2),encoding='utf-8')
    (outdir/'data.json').write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
    (outdir/'facts.json').write_text(json.dumps(facts,ensure_ascii=False,indent=2),encoding='utf-8')
    ranked=rank(data,facts)
    (outdir/'ranked.json').write_text(json.dumps(ranked,ensure_ascii=False,indent=2),encoding='utf-8')
    audit={'version':'7.5.5','date':day,'mode':data['data_mode'],'game_count':len(data['games']),
           'game_of_day_id':ranked['game_of_day_id'],'csv_warnings':facts['warnings'],
           'metrics':{},'source':data['data_endpoints'],'voice':False,'youtube_upload':False,
           'note':'Pokročilé týmové statistiky vyžadují ověřené zdroje; chybějící hodnoty se nedopočítávají odhadem.'}
    for g in ranked['games']:
        audit['metrics'][str(g['id'])]={'teams':[g['away']['abbrev'],g['home']['abbrev']],
            'last5_samples':{side:{k:g[side][k]['sample_size'] for k in ('form_all','form_home','form_away')} for side in ('home','away')},
            'verified_facts':len(facts['games'].get(str(g['id']),[])), 'generated_candidates':len(g.get('all_candidates',[])), 'featured_fact':g['featured_fact']['text'], 'interest_score':g['interest_score']}
    (outdir/'audit.json').write_text(json.dumps(audit,ensure_ascii=False,indent=2),encoding='utf-8')
    if render:
        if not data['games']:
            (outdir/'NO_GAMES.txt').write_text('Ve zvoleném časovém okně nebyl žádný zápas NHL. Video se nevytvořilo.\n',encoding='utf-8')
        else:
            make_video(ranked,outdir/'video',strict_logos=not allow_demo_logos,seconds_per_card=seconds)
    return audit

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--date',required=True);p.add_argument('--outdir',required=True)
    p.add_argument('--fixture');p.add_argument('--csv-dir');p.add_argument('--render',action='store_true')
    p.add_argument('--allow-demo-logos',action='store_true');p.add_argument('--seconds',type=float,default=8)
    a=p.parse_args()
    if a.allow_demo_logos and not a.fixture: p.error('--allow-demo-logos je povoleno pouze s --fixture')
    print(json.dumps(execute(a.date,a.outdir,a.fixture,a.csv_dir,a.render,a.allow_demo_logos,a.seconds),ensure_ascii=False,indent=2))
