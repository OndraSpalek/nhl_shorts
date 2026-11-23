#!/usr/bin/env python3
"""Import verified same-day CSV exports from existing Be6player scripts.

The importer does not guess player stats or fabricate missing metrics. Only complete
regular-season CSV exports with matching local date are accepted. Outputs facts
compatible with shorts_rank.py.
"""
import argparse
import csv
import json
from pathlib import Path


def read_csv(path):
    if not path.is_file():
        return {}
    with path.open(encoding='utf-8-sig', newline='') as f:
        rows = list(csv.DictReader(f, delimiter=';'))
    if not rows or not {'varianta','zkratka','zapasu'}.issubset(rows[0]):
        raise ValueError(f'Chybné sloupce CSV: {path}')
    result = {}
    for row in rows:
        if row['varianta'] == 'celkem' and row['zkratka']:
            if row['zkratka'] in result:
                raise ValueError(f'Duplicitní tým {row["zkratka"]} v {path}')
            result[row['zkratka']] = row
    return result


def num(row, key):
    try:
        v = float(row[key].replace(',', '.'))
        return v if v >= 0 else None
    except (KeyError, ValueError, TypeError, AttributeError):
        return None


def make_fact(category, text, evidence, source):
    return {'category':category,'text':text,'evidence':evidence,'source':source,'verified':True}


def generate(data, csv_dir):
    day = data['local_date']
    shots_path = csv_dir / f'strely_tymy_data_{day}.csv'
    pp_path = csv_dir / f'presilovky_data_{day}.csv'
    shots = read_csv(shots_path)
    pp = read_csv(pp_path)
    out = {'games':{}, 'sources':{}, 'warnings':[]}
    if not shots: out['warnings'].append(f'Chybí {shots_path.name}; střely a vhazování přeskočeny.')
    if not pp: out['warnings'].append(f'Chybí {pp_path.name}; přesilovky a oslabení přeskočeny.')
    for game in data.get('games', []):
        home, away = game['home']['abbrev'], game['away']['abbrev']
        facts = []
        sh, sa = shots.get(home), shots.get(away)
        if sh and sa:
            gh, ga = num(sh,'zapasu'), num(sa,'zapasu')
            hh, aa = num(sh,'sog'), num(sa,'sog')
            if gh and ga and min(gh,ga)>=10 and hh is not None and aa is not None:
                hp, ap = hh/gh, aa/ga
                if abs(hp-ap)>=5:
                    leader = home if hp>ap else away
                    facts.append(make_fact('shots', f'{leader} střílí výrazně častěji: {home} {hp:.1f}, {away} {ap:.1f} střel na zápas',
                        {'sample_size':int(min(gh,ga)),'shots_per_game_home':round(hp,2),'shots_per_game_away':round(ap,2)},shots_path.name))
            wh,lh,wa,la=(num(sh,'fo_w'),num(sh,'fo_l'),num(sa,'fo_w'),num(sa,'fo_l'))
            if min(gh or 0,ga or 0)>=10 and all(x is not None for x in (wh,lh,wa,la)) and wh+lh>=100 and wa+la>=100:
                ph,pa=100*wh/(wh+lh),100*wa/(wa+la)
                if abs(ph-pa)>=7:
                    leader=home if ph>pa else away
                    facts.append(make_fact('faceoffs',f'{leader} má výraznou převahu na vhazování: {home} {ph:.1f} %, {away} {pa:.1f} %',
                        {'sample_size':int(min(gh,ga)),'faceoffs_home_pct':round(ph,2),'faceoffs_away_pct':round(pa,2)},shots_path.name))
        ph,pa=pp.get(home),pp.get(away)
        if ph and pa:
            gh,ga=num(ph,'zapasu'),num(pa,'zapasu')
            if gh and ga and min(gh,ga)>=10:
                hpp,hppo,app,appo=(num(ph,'pp_goly'),num(ph,'pp_prilezitosti'),num(pa,'pp_goly'),num(pa,'pp_prilezitosti'))
                if all(x is not None for x in (hpp,hppo,app,appo)) and hppo>=20 and appo>=20:
                    hp,ap=100*hpp/hppo,100*app/appo
                    if abs(hp-ap)>=8:
                        leader=home if hp>ap else away
                        facts.append(make_fact('special_teams',f'{leader} má účinnější přesilovky: {home} {hp:.1f} %, {away} {ap:.1f} %',
                            {'sample_size':int(min(gh,ga)),'pp_home_pct':round(hp,2),'pp_away_pct':round(ap,2)},pp_path.name))
                # PK: goals against while shorthanded / times shorthanded.
                hga,ht,aga,at=(num(ph,'inkasovane_v_oslabeni'),num(ph,'oslabeni'),num(pa,'inkasovane_v_oslabeni'),num(pa,'oslabeni'))
                if all(x is not None for x in (hga,ht,aga,at)) and ht>=20 and at>=20:
                    hp,ap=100*(1-hga/ht),100*(1-aga/at)
                    if abs(hp-ap)>=8 and 0<=hp<=100 and 0<=ap<=100:
                        leader=home if hp>ap else away
                        facts.append(make_fact('special_teams',f'{leader} má účinnější oslabení: {home} {hp:.1f} %, {away} {ap:.1f} %',
                            {'sample_size':int(min(gh,ga)),'pk_home_pct':round(hp,2),'pk_away_pct':round(ap,2)},pp_path.name))
        out['games'][str(game['id'])]=facts
    out['sources']={'shots':shots_path.name if shots else None,'special_teams':pp_path.name if pp else None}
    out['warnings'].append('CSV jsou sezonní snapshoty. Pro historické video použij archivní CSV pořízená před zápasy; nepoužívej později přepočtené reporty.')
    return out


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--input',type=Path,required=True)
    p.add_argument('--csv-dir',type=Path,default=Path('.'))
    p.add_argument('--output',type=Path,default=Path('shorts_facts.json'))
    a=p.parse_args()
    data=json.loads(a.input.read_text(encoding='utf-8'))
    facts=generate(data,a.csv_dir)
    a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(json.dumps(facts,ensure_ascii=False,indent=2),encoding='utf-8')
    print(f"Vygenerováno {sum(map(len,facts['games'].values()))} zajímavostí pro {len(facts['games'])} zápasů")
    for w in facts['warnings']: print('UPOZORNĚNÍ:',w)

if __name__=='__main__': main()
