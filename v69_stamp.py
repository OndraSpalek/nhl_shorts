import os,sys,json,hashlib
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo
root=Path('shorts_preview'); day,mode=sys.argv[1:]; p=root/'audit.json'; audit=json.loads(p.read_text()); assert audit['date']==day and audit['mode']==('NHL_API' if mode=='live' else 'OFFLINE_FIXTURE_NOT_LIVE')
now=datetime.now(ZoneInfo('Europe/Prague')); run=os.getenv('GITHUB_RUN_ID','local'); attempt=os.getenv('GITHUB_RUN_ATTEMPT','1'); video=root/'video/be6player_shorts.mp4'; audit.update({'finished_prague':now.isoformat(),'run_id':run,'run_attempt':attempt})
if audit['game_count']:
 target=video.with_name(f'be6player_{day}_{now:%H%M%S}_{run}_{attempt}'+('_DEMO' if mode=='fixture' else '')+'.mp4'); video.rename(target); audit.update({'video_file':target.name,'video_sha256':hashlib.sha256(target.read_bytes()).hexdigest(),'video_bytes':target.stat().st_size})
p.write_text(json.dumps(audit,ensure_ascii=False,indent=2),encoding='utf-8');print(json.dumps(audit,ensure_ascii=False,indent=2))
