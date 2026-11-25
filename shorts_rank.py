#!/usr/bin/env python3
"""Deterministic Be6player selection engine. Input: shorts_data.json; optional verified facts.

Optional facts JSON: {"games": {"GAME_ID": [{"category":"h2h", "text":"...",
"evidence": {"wins":4,"sample_size":5}, "source":"...", "verified":true}]}}
Only supported categories with checked evidence are eligible; no fabricated facts.
"""
import argparse
import json
from pathlib import Path

BASE = {'goalie':86,'player_leader':74,'historical_h2h':84,'rest':82,'scoring':76,'milestone':90,'player_streak':85,'team_streak':80,'venue_form':78,
        'overall_form':75,'h2h':70,'special_teams':65,'period_goals':60,
        'first_goal_comebacks':58,'shots':55,'faceoffs':45}

def form_points(form):
    if not form or form.get('sample_size') != 5: return None
    return 2*form['V']+form['PP']

def form_label(form):
    return f"{form['V']}–{form['P']}–{form['PP']}" if form and form.get('sample_size') else '—'

def candidate(category,text,score,details=None):
    return {'category':category,'text':text,'score':min(120,score),'details':details or {}}

def generated_candidates(game):
    h,a=game['home'],game['away']; out=[]
    for t in (h,a):
        s=t.get('streak') or {}; n=s.get('length',0)
        if n>=5:
            kind=s.get('type')
            if kind=='vyhry':
                out.append(candidate('team_streak',f"{t['abbrev']} vyhrál {n} zápasů v řadě",80+(15 if n>=10 else 0),{'team':t['abbrev'],'length':n}))
            elif kind=='bez_vyhry':
                out.append(candidate('team_streak',f"{t['abbrev']} nevyhrál {n} zápasů v řadě",80+(15 if n>=10 else 0),{'team':t['abbrev'],'length':n}))
    hf,af=h.get('form_home'),a.get('form_away')
    hp,ap=form_points(hf),form_points(af)
    if hp is not None and ap is not None:
        diff=abs(hp-ap)*10  # each point /10 available = 10 percentage points
        if diff>=40:
            leader=h if hp>ap else a
            out.append(candidate('venue_form',f"{leader['abbrev']} má výrazně lepší formu: {h['abbrev']} doma {form_label(hf)}, {a['abbrev']} venku {form_label(af)}",78+10+(10 if diff>=60 else 0),{'difference_pp':diff}))
    hp,ap=form_points(h.get('form_all')),form_points(a.get('form_all'))
    if hp is not None and ap is not None and abs(hp-ap)>=6:
        out.append(candidate('overall_form',f"Forma posledních 5: {h['abbrev']} {form_label(h['form_all'])}, {a['abbrev']} {form_label(a['form_all'])}",75+10,{'difference_pp':abs(hp-ap)*10}))
    # Záložní zajímavost z doložených výsledků, pokud neexistuje výraznější rozdíl.
    if not out:
        hf, af = h.get('form_all') or {}, a.get('form_all') or {}
        if hf.get('sample_size') == 5 and af.get('sample_size') == 5:
            out.append(candidate('form',
                f"Posledních 5 zápasů: {h['abbrev']} {form_label(hf)}, {a['abbrev']} {form_label(af)}",
                25, {'sample_size': 5, 'source': 'club-schedule-season'}))
    return out

def verified_external(game, facts):
    out=[]
    for f in facts:
        cat=f.get('category'); e=f.get('evidence') or {}
        if not f.get('verified') or not f.get('source') or cat not in BASE or cat in ('team_streak','venue_form','overall_form'):
            continue
        text=f.get('text','').strip()
        if not text or len(text)>180: continue
        # No unsupported statistical claims; evidence must be auditable.
        if not isinstance(e.get('sample_size'),int) or e['sample_size']<1: continue
        if cat=='h2h' and (e['sample_size']<5 or e.get('wins',0)<4): continue
        if cat=='player_streak' and not (e.get('point_streak',0)>=7 or e.get('goal_streak',0)>=4): continue
        if cat=='milestone' and not (0<e.get('remaining',999)<=2): continue
        if cat in ('first_goal_comebacks','period_goals','special_teams','shots','faceoffs') and e['sample_size']<10: continue
        if cat=='scoring' and e['sample_size']<10: continue
        if cat=='rest' and not 0<e.get('hours',999)<=30: continue
        bonus=min(15,max(0,int(f.get('bonus',0))))
        out.append(candidate(cat,text,BASE[cat]+bonus,e | {'source':f['source']}))
    return out

def rank(data, facts=None):
    facts=facts or {}; fact_games=facts.get('games') or {}
    ranked=[]
    for g in data.get('games',[]):
        candidates=generated_candidates(g)+verified_external(g,fact_games.get(str(g['id']),[]))
        candidates.sort(key=lambda x:(x['category'] not in ('rest','scoring','h2h','first_goal_comebacks','period_goals','player_streak','milestone','goalie','player_leader','historical_h2h'),-x['score'],x['category'],x['text']))
        first=candidates[0] if candidates else None
        second=next((c for c in candidates[1:] if c['category']!=first['category']),None) if first else None
        bonus=0
        hr=g['home'].get('conference_rank'); ar=g['away'].get('conference_rank')
        if isinstance(hr,int) and isinstance(ar,int) and hr<=4 and ar<=4: bonus+=10
        if isinstance(hr,int) and isinstance(ar,int) and 7<=hr<=10 and 7<=ar<=10: bonus+=10
        score=round((first['score'] if first else 0)+0.4*(second['score'] if second else 0)+min(bonus,20),1)
        ranked.append({**g,'interest_score':score,'featured_fact':first or candidate('form','Dnešní zápas NHL',0),
                       'secondary_fact':second,'all_candidates':candidates})
    # tie: strongest fact, then earliest start
    order=sorted(ranked,key=lambda g:(-g['interest_score'],-g['featured_fact']['score'],g['start_utc'],str(g['id'])))
    chosen=order[0]['id'] if order else None
    for g in ranked: g['game_of_day']=(g['id']==chosen)
    return {**data,'games':ranked,'game_of_day_id':chosen,'ranking_version':'1.0',
            'ranking_note':'Jen doložené zajímavosti; neověřené externí statistiky se ignorují.'}

def main():
    p=argparse.ArgumentParser();p.add_argument('--input',type=Path,required=True)
    p.add_argument('--facts',type=Path);p.add_argument('--output',type=Path,default=Path('shorts_ranked.json'))
    a=p.parse_args();data=json.loads(a.input.read_text(encoding='utf-8'))
    facts=json.loads(a.facts.read_text(encoding='utf-8')) if a.facts else None
    result=rank(data,facts);a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    print(f"Vyhodnoceno {len(result['games'])} zápasů; zápas dne: {result['game_of_day_id']}")
if __name__=='__main__':main()
