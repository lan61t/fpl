"""Turn data/raw/players_model.pkl into data.json (what the web page loads). Keeps the old file when nothing changed."""
import json, collections, datetime, numpy as np, pandas as pd
from fplcfg import *
b=json.loads((RAW/'bootstrap.json').read_text(encoding='utf8')); fx=json.loads((RAW/'fixtures.json').read_text(encoding='utf8'))
CUR,GW0=state(b,fx); els=pd.read_pickle(RAW/'players_model.pkl')
cols=[f'xp{i}' for i in range(H)]; tm={t['id']:t for t in b['teams']}; pos={1:0,2:1,3:2,4:3}
players=[]
for r in els.itertuples():
    x=[0 if (v is None or not np.isfinite(v)) else round(float(v),2) for v in [getattr(r,c) for c in cols]]
    if max(x)<=0 and r.minutes==0 and r.status in('u','n','s'): continue
    players.append(dict(i=int(r.id),n=r.web_name,t=int(r.team),p=pos[r.element_type],c=round(float(r.price),1),o=float(r.selected_by_percent),s=r.status,
        ch=(None if pd.isna(r.chance_of_playing_next_round) else int(r.chance_of_playing_next_round)),nw=(r.news or '')[:140],
        pts=int(r.total_points),mn=int(r.minutes),f=float(r.form),x=x))
fixt=collections.defaultdict(list); cnt=collections.defaultdict(lambda: collections.Counter())
for f in fx:
    if not f['event']: continue
    cnt[f['team_h']][f['event']]+=1; cnt[f['team_a']][f['event']]+=1
    if GW0<=f['event']<GW0+H:
        fixt[f['team_h']].append([f['event'],f['team_a'],1,f['team_h_difficulty']]); fixt[f['team_a']].append([f['event'],f['team_h'],0,f['team_a_difficulty']])
ev=[e for e in b['events'] if e['id']>=GW0]
now=datetime.datetime.now(datetime.timezone.utc)
out=dict(generated=now.strftime('%Y-%m-%dT%H:%M:%SZ'),asof=now.strftime('%Y-%m-%d'),cur=CUR,gw0=GW0,H=H,deadline=ev[0]['deadline_time'] if ev else None,
  teams={t:dict(s=v['short_name'],n=v['name']) for t,v in tm.items()},players=players,fx={t:v for t,v in fixt.items()},
  cnt={t:{g:c for g,c in v.items() if g>=GW0} for t,v in cnt.items()},deadlines={e['id']:e['deadline_time'] for e in ev})
def body(o): return json.dumps({k:v for k,v in o.items() if k not in('generated','asof')},ensure_ascii=False,separators=(',',':'),sort_keys=True)
dest=ROOT/'data.json'
if dest.exists() and body(json.loads(dest.read_text(encoding='utf8')))==body(out):
    print('data unchanged; keeping existing data.json')
else:
    dest.write_text(json.dumps(out,ensure_ascii=False,separators=(',',':')),encoding='utf8'); print('data.json written:',len(players),'players')
