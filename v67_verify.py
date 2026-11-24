#!/usr/bin/env python3
"""Verify generated Shorts artifacts, media streams, and data provenance. Fail closed."""
import argparse
import json
import subprocess
from pathlib import Path


def probe_media(path):
    p = subprocess.run(['ffprobe','-v','error','-show_entries','stream=codec_type,width,height,codec_name:format=duration', '-of','json',str(path)], capture_output=True,text=True,check=True)
    return json.loads(p.stdout)


def verify(outdir, require_live=False):
    root=Path(outdir)
    issues=[]
    def load(name):
        try:return json.loads((root/name).read_text(encoding='utf-8'))
        except (OSError,ValueError) as exc:
            issues.append(f'{name}: {exc}');return {}
    data=load('data.json');audit=load('audit.json');ranked=load('ranked.json')
    mode=data.get('data_mode')
    if mode not in ('NHL_API','OFFLINE_FIXTURE_NOT_LIVE'): issues.append('Neznámý režim zdrojových dat')
    if require_live and mode!='NHL_API': issues.append('Požadována živá data, ale režim není NHL_API')
    games=data.get('games',[])
    if not isinstance(games,list):issues.append('games není seznam');games=[]
    if data.get('game_count')!=len(games):issues.append('Počet zápasů neodpovídá data.json')
    if audit.get('game_count')!=len(games):issues.append('Počet zápasů neodpovídá audit.json')
    if ranked.get('game_of_day_id')!=audit.get('game_of_day_id'):issues.append('Nesouhlasí zápas dne')
    if audit.get('voice') is not False or audit.get('youtube_upload') is not False:issues.append('Neplatná konfigurace hlasu/publikace')
    video=root/'video'/'be6player_shorts.mp4'
    manifest=root/'video'/'manifest.json'
    if games:
        m=load('video/manifest.json')
        if m.get('games')!=len(games):issues.append('Počet karet ve videu nesouhlasí')
        if m.get('voice') is not False or m.get('youtube_upload') is not False:issues.append('Manifest požaduje hlas nebo publikaci')
        if require_live and m.get('missing_logos'):issues.append('Chybějící loga v produkčním výstupu')
        cards=list((root/'video'/'cards').glob('game_*.png'))
        if len(cards)!=2*len(games):issues.append(f'Počet grafických karet {len(cards)} != {2*len(games)}')
        if not video.exists() or video.stat().st_size<1000:issues.append('Video chybí nebo je prázdné')
        else:
            try:
                media=probe_media(video)
                streams=media.get('streams',[])
                vs=[s for s in streams if s.get('codec_type')=='video']
                aud=[s for s in streams if s.get('codec_type')=='audio']
                if len(vs)!=1 or vs[0].get('width')!=1080 or vs[0].get('height')!=1920:issues.append('Video není 1080×1920')
                if len(aud)!=1:issues.append('Chybí jedna hudební zvuková stopa')
                if float(media.get('format',{}).get('duration',0))<=0:issues.append('Neplatná délka videa')
            except (OSError,subprocess.CalledProcessError,ValueError,KeyError) as exc:issues.append(f'ffprobe: {exc}')
        for name in ('nahled.png','titulek.txt','popis.txt'):
            if not (root/'video'/name).exists():issues.append(f'Chybí {name}')
    else:
        if not (root/'NO_GAMES.txt').exists():issues.append('Chybí NO_GAMES.txt')
        if video.exists():issues.append('Video vytvořeno bez zápasů')
    result={'version':'6.7','status':'PASS' if not issues else 'FAIL','data_mode':mode,'date':data.get('local_date'),'game_count':len(games),'game_of_day_id':audit.get('game_of_day_id'),'video_exists':video.exists(),'issues':issues,'live_required':require_live}
    (root/'verification.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    lines=['# Be6player V6.7 – kontrola výstupu',f"**Výsledek:** {result['status']}",f"**Datum:** {result['date']}",f"**Režim:** {mode}",f"**Zápasy:** {len(games)}",f"**Zápas dne:** {result['game_of_day_id']}",f"**Video:** {'ano' if video.exists() else 'ne'}",'','## Problémy']
    lines.extend('- '+x for x in issues) if issues else lines.append('Žádné chyby při automatických kontrolách. Nejde o potvrzení přesnosti živých statistik ani práv k hudbě.')
    (root/'verification.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    return result

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--outdir',required=True);p.add_argument('--require-live',action='store_true');a=p.parse_args()
    r=verify(a.outdir,a.require_live);print(json.dumps(r,ensure_ascii=False,indent=2));raise SystemExit(0 if r['status']=='PASS' else 1)
