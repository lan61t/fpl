"""Download FPL data (live API) and last season's files (open vaastav dataset)."""
import json, time, urllib.request, urllib.error
from fplcfg import *
UA={'User-Agent':'Mozilla/5.0 (compatible; fpl-assistant-data-refresh)'}
def get(url,dest,tries=4,optional=False):
    for k in range(tries):
        try:
            req=urllib.request.Request(url,headers=UA)
            with urllib.request.urlopen(req,timeout=60) as r: data=r.read()
            dest.write_bytes(data); return True
        except urllib.error.HTTPError as e:
            if e.code==404 and optional: return False
            err=e
        except Exception as e: err=e
        time.sleep(2*(k+1))
    if optional: return False
    raise RuntimeError(f'download failed: {url}: {err}')
def fetch_live():
    get(FPL+'bootstrap-static/',RAW/'bootstrap.json'); get(FPL+'fixtures/',RAW/'fixtures.json')
    b=json.loads((RAW/'bootstrap.json').read_text(encoding='utf8')); fx=json.loads((RAW/'fixtures.json').read_text(encoding='utf8')); cur,gw0=state(b,fx)
    for g in range(1,cur+1):
        f=LIVE/f'gw{g}.json'
        if not f.exists() or g>=cur-1: get(FPL+f'event/{g}/live/',f)   # recent gameweeks can still be corrected
    return cur,gw0
def fetch_season(s,files=('players_raw.csv','teams.csv','fixtures.csv','gws/merged_gw.csv')):
    for f in files:
        dest=HIST/f'{s}_{f.split("/")[-1]}'
        if not dest.exists(): get(f'{VAASTAV}{s}/{f}',dest,optional=True)
if __name__=='__main__':
    import sys
    if 'hist' in sys.argv:
        for s in HIST_SEASONS: fetch_season(s)
    else:
        print(fetch_live()); fetch_season(PREV)
