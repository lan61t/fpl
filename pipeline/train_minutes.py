"""Fit the minutes model once per season and save data/minutes_weights.json (run locally: python pipeline/train_minutes.py)."""
import json
from fplcfg import *
import fetch, minutes_lib as ml
fetch.get  # noqa
for s in HIST_SEASONS: fetch.fetch_season(s,files=('players_raw.csv','gws/merged_gw.csv'))
w60,wan,n=ml.train()
json.dump(dict(w60=list(map(float,w60)),wan=list(map(float,wan)),rows=int(n),seasons=HIST_SEASONS),open(DATA/'minutes_weights.json','w'))
print('trained on',n,'rows; saved data/minutes_weights.json')
