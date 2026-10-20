"""Paths and season settings shared by every pipeline script."""
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/'data'; RAW=DATA/'raw'; LIVE=RAW/'live'; HIST=DATA/'hist'
for _p in (RAW,LIVE,HIST): _p.mkdir(parents=True,exist_ok=True)
# Change these two lines at the start of a new season, then run pipeline/train_minutes.py once.
SEASON='2026-27'
PREV='2025-26'
HIST_SEASONS=['2016-17','2017-18','2018-19','2019-20','2020-21','2021-22','2022-23','2023-24','2024-25','2025-26']
H=6   # gameweeks predicted ahead
VAASTAV='https://raw.githubusercontent.com/vaastav/Fantasy-Premier-League/master/data/'
FPL='https://fantasy.premierleague.com/api/'

def state(bootstrap,fixtures=None):
    """cur = last completed gameweek (data cut-off); gw0 = first gameweek still open for transfers.
    A gameweek counts as completed as soon as every match is over (finished or provisionally finished), because FPL
    only sets its own 'finished' flag a day or so later, and the model should learn from those results straight away."""
    ev=bootstrap['events']
    done={e['id'] for e in ev if e['finished']}
    if fixtures:
        byev={}
        for f in fixtures:
            if f.get('event'): byev.setdefault(f['event'],[]).append(f)
        for g,fs in byev.items():
            if fs and all(x.get('finished') or x.get('finished_provisional') for x in fs): done.add(g)
    cur=0
    while cur+1 in done: cur+=1
    nxt=[e['id'] for e in ev if e.get('is_next')]
    return cur,(nxt[0] if nxt else cur+1)
