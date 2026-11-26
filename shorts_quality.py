"""Measure captions with the exact approved renderer font and line widths."""
from functools import lru_cache
from PIL import ImageFont
FONT='/usr/share/fonts/truetype/dejavu/DejaVuSansCondensed-Bold.ttf'
@lru_cache(maxsize=2)
def font(size): return ImageFont.truetype(FONT,size)
def fits(text, page):
    size,width=(34,850) if page==1 else (30,820)
    f=font(size); lines=[]; line=''
    for word in text.split():
        if f.getlength(word)>width: return False
        trial=(line+' '+word).strip()
        if line and f.getlength(trial)>width: lines.append(line); line=word
        else: line=trial
    if line: lines.append(line)
    return bool(lines) and len(lines)<=3
