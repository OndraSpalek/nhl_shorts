"""Immutable completed-game detail cache; atomic writes, no secrets."""
import json, os
from pathlib import Path

def completed_detail(fetch, gid, endpoint):
    root=Path(os.getenv('NHL_CACHE_DIR','prediction_cache')); root.mkdir(parents=True,exist_ok=True)
    p=root/f'{int(gid)}-{endpoint}.json'
    try:
        data=json.loads(p.read_text()); assert isinstance(data,dict) and data
        return data
    except (OSError,ValueError,AssertionError): pass
    data=fetch(f'/gamecenter/{gid}/{endpoint}')
    if not isinstance(data,dict) or not data: raise ValueError('empty detail')
    tmp=p.with_suffix('.tmp');tmp.write_text(json.dumps(data));tmp.replace(p)
    return data
