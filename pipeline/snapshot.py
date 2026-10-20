"""Freeze the predictions for the next open gameweek. Re-saved on every run until the deadline passes, so the
file always holds the last version made before the deadline. Writes log/pred_gwNN.json."""
import json, datetime
import pandas as pd
from fplcfg import *
LOG=ROOT/'log'; LOG.mkdir(exist_ok=True)
d=json.loads((ROOT/'data.json').read_text(encoding='utf8'))
gw0=d['gw0']; deadline=d.get('deadline')
import os
now=datetime.datetime.fromisoformat(os.environ['FPL_NOW'].replace('Z','+00:00')) if os.environ.get('FPL_NOW') else datetime.datetime.now(datetime.timezone.utc)
if deadline and now>=datetime.datetime.fromisoformat(deadline.replace('Z','+00:00')):
    print('deadline already passed; keeping the saved snapshot for GW',gw0); raise SystemExit(0)
els=pd.read_pickle(RAW/'players_model.pkl').set_index('id')
rows=[]
for p in d['players']:
    r=els.loc[p['i']]
    rows.append(dict(i=p['i'],n=p['n'],p=p['p'],t=p['t'],c=p['c'],o=p['o'],s=p['s'],ch=p['ch'],x=p['x'],
        old=round(float(r.xp_old0),2),comp=round(float(r.xp_comp0),2),raw=round(float(r.xp_raw0),2)))
snap=dict(gw=gw0,saved=d['generated'],deadline=deadline,cur=d['cur'],players=rows)
dest=LOG/f'pred_gw{gw0:02d}.json'
def body(o): return json.dumps({k:v for k,v in o.items() if k!='saved'},sort_keys=True,separators=(',',':'))
if dest.exists() and body(json.loads(dest.read_text(encoding='utf8')))==body(snap):
    print('snapshot for GW',gw0,'unchanged')
else:
    dest.write_text(json.dumps(snap,ensure_ascii=False,separators=(',',':')),encoding='utf8'); print('snapshot saved for GW',gw0,'(',len(rows),'players )')
