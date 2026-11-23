#!/usr/bin/env python3
"""Import season-snapshot CSV from goalsbyperiod.py and nhl_prubeh_zapasu.py.

Only verifiable comparisons enter shorts_rank. The files must be generated on the
preview date BEFORE the featured games; do not use current exports for backfills.
"""
import argparse
import csv
import json
from datetime import date
from pathlib import Path


def rows(path, required):
    if not path.is_file():
        return []
    with path.open(encoding='utf-8-sig', newline='') as stream:
        reader = csv.DictReader(stream, delimiter=';')
        if not reader.fieldnames or not set(required).issubset(reader.fieldnames):
            raise ValueError(f'Neplatné CSV sloupce: {path.name}; požadováno {required}')
        return list(reader)


def number(row, key):
    try:
        value = float(row[key].strip().replace(',', '.'))
        return value if value >= 0 else None
    except (KeyError, ValueError, TypeError, AttributeError):
        return None


def fact(category, text, sample, source, **evidence):
    return {'category': category, 'text': text, 'evidence': {'sample_size': sample, **evidence},
            'source': source, 'verified': True}


def generate(data, csv_dir):
    day = data['local_date']
    periods_file = csv_dir / f'goalsbyperiod_data_{day}.csv'
    flow_file = csv_dir / f'prubeh_data_{day}.csv'
    period_rows = rows(periods_file, ['varianta','zkratka','zapasu','g1','g2','g3','obdrzene_g1','obdrzene_g2','obdrzene_g3'])
    flow_rows = rows(flow_file, ['modul','zkratka','vyber','obdobi','situace','varianta','V','P','PP','zapasu'])
    periods = {r['zkratka']:r for r in period_rows if r['varianta']=='celkem' and r['zkratka']}
    flow = {}
    target=date.fromisoformat(day)
    season_year=target.year if target.month>=9 else target.year-1
    season_label=f'{season_year}/{str(season_year+1)[2:]}'
    for r in flow_rows:
        if r['varianta']!='celkem' or r['modul'] not in ('prvni_gol','zvraty'):
            continue
        if r['vyber'] != 'Základní část' or r['obdobi'] != season_label:
            continue
        key=(r['zkratka'],r['modul'],r['situace'])
        if key in flow:
            raise ValueError(f'Duplicitní situace: {key}')
        flow[key]=r
    out={'games':{},'sources':{'period_goals':periods_file.name if period_rows else None,
                              'first_goal_comebacks':flow_file.name if flow_rows else None},'warnings':[]}
    if not period_rows: out['warnings'].append(f'Chybí {periods_file.name}; góly po třetinách vynechány.')
    if not flow_rows: out['warnings'].append(f'Chybí {flow_file.name}; první gól a obraty vynechány.')
    for g in data.get('games',[]):
        home,away=g['home']['abbrev'],g['away']['abbrev']
        found=[]
        h,a=periods.get(home),periods.get(away)
        if h and a:
            hg,ag=number(h,'zapasu'),number(a,'zapasu')
            if hg and ag and min(hg,ag)>=10:
                for i in (1,2,3):
                    hs,as_=number(h,f'g{i}'),number(a,f'g{i}')
                    hc,ac=number(h,f'obdrzene_g{i}'),number(a,f'obdrzene_g{i}')
                    if None in (hs,as_,hc,ac): continue
                    # goal differential per game, measured within the period only
                    hd,ad=(hs-hc)/hg,(as_-ac)/ag
                    if abs(hd-ad)>=0.5:
                        leader=home if hd>ad else away
                        found.append(fact('period_goals',f'{leader} má výrazně lepší {i}. třetiny: {home} {hd:+.2f}, {away} {ad:+.2f} gólu na zápas',
                                          int(min(hg,ag)),periods_file.name,period=i,home_goal_diff_per_game=round(hd,3),away_goal_diff_per_game=round(ad,3)))
        # Winning rate after conceding first goal: meaningful 'comeback' proxy,
        # but never describe it as number of in-game comebacks.
        rh=flow.get((home,'prvni_gol','Dostal první gól'))
        ra=flow.get((away,'prvni_gol','Dostal první gól'))
        if rh and ra:
            nh,na=number(rh,'zapasu'),number(ra,'zapasu')
            wh,wa=number(rh,'V'),number(ra,'V')
            if None not in (nh,na,wh,wa) and min(nh,na)>=10:
                hp,ap=100*wh/nh,100*wa/na
                if abs(hp-ap)>=20:
                    leader=home if hp>ap else away
                    found.append(fact('first_goal_comebacks',f'{leader} častěji vyhrává i po inkasování prvního gólu: {home} {hp:.1f} %, {away} {ap:.1f} %',
                                      int(min(nh,na)),flow_file.name,home_pct=round(hp,2),away_pct=round(ap,2),situation='Dostal první gól'))
        out['games'][str(g['id'])]=found
    out['warnings'].append('Statistiky z CSV jsou sezonní snapshoty. Při zpětném generování je nutný archivní export pořízený před zápasy.')
    return out


def merge(*sources):
    result={'games':{},'sources':{},'warnings':[]}
    for source in sources:
        for key,facts in source.get('games',{}).items():
            result['games'].setdefault(key,[]).extend(facts)
        result['sources'].update(source.get('sources',{}))
        result['warnings'].extend(source.get('warnings',[]))
    return result


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--input',required=True,type=Path)
    parser.add_argument('--csv-dir',type=Path,default=Path('.'))
    parser.add_argument('--base-facts',type=Path)
    parser.add_argument('--output',type=Path,default=Path('shorts_facts_v4.json'))
    args=parser.parse_args()
    data=json.loads(args.input.read_text(encoding='utf-8'))
    advanced=generate(data,args.csv_dir)
    base=json.loads(args.base_facts.read_text(encoding='utf-8')) if args.base_facts else {'games':{}}
    output=merge(base,advanced)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(output,ensure_ascii=False,indent=2),encoding='utf-8')
    print(f'Zpracováno {len(output["games"])} zápasů, {sum(len(x) for x in output["games"].values())} zajímavostí')
    for warning in output['warnings']: print('UPOZORNĚNÍ:',warning)

if __name__=='__main__': main()
