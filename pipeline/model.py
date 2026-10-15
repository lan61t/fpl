"""Model A: points-per-90 rate x minutes x fixture adjustment. Writes data/raw/players_model.pkl (columns xp0..xp{H-1})."""
import json, numpy as np, pandas as pd, warnings
warnings.filterwarnings('ignore')
from fplcfg import *
b=json.loads((RAW/'bootstrap.json').read_text(encoding='utf8')); fx=json.loads((RAW/'fixtures.json').read_text(encoding='utf8'))
CUR,GW0=state(b)
els=pd.DataFrame(b['elements']); teams=pd.DataFrame(b['teams']).set_index('id')
els['pos']=els.element_type.map({1:'GK',2:'DEF',3:'MID',4:'FWD'}); els['price']=els.now_cost/10
rows=[]
for g in range(1,CUR+1):
    for e in json.loads((LIVE/f'gw{g}.json').read_text(encoding='utf8'))['elements']:
        s=e['stats']; rows.append((e['id'],g,s['minutes'],s['total_points']))
cur=pd.DataFrame(rows,columns=['id','gw','min','pts'])
c=cur.groupby('id').agg(min26=('min','sum'),pts26=('pts','sum'))
rec=cur[cur.gw>=CUR-2].groupby('id')['min'].mean().rename('recmin')
lp=pd.read_csv(HIST/f'{PREV}_players_raw.csv',encoding='latin-1',low_memory=False)[['code','minutes','total_points']].rename(columns={'minutes':'min25','total_points':'pts25'})
els=els.merge(lp,on='code',how='left').merge(c,left_on='id',right_index=True,how='left').merge(rec,left_on='id',right_index=True,how='left')
for k in ['min25','pts25','min26','pts26','recmin']: els[k]=els[k].fillna(0)
PBND=[0,4.5,5.5,6.5,7.5,9,10.5,16]
lp2=els[els.min25>=900].copy(); lp2['pb']=pd.cut(lp2.price,PBND); els['pb']=pd.cut(els.price,PBND)
prior=(lp2.groupby(['pos','pb'],observed=True).apply(lambda d:d.pts25.sum()/d.min25.sum()*90)).rename('prior').reset_index()
els=els.merge(prior,on=['pos','pb'],how='left'); els['prior']=els.prior.fillna(els.groupby('pos').prior.transform('mean')).fillna(3.0)
PM=450; w25=0.6
els['rate90']=(els.pts25*w25+els.pts26*1.5+els.prior/90*PM)/(els.min25*w25+els.min26*1.5+PM)*90
base=np.where(els.min26>0,0.5*els.recmin/90+0.5*els.min26/(max(CUR,1)*90),np.minimum(els.min25/(38*90)*1.3,0.7))
avail=els.chance_of_playing_next_round.fillna(100)/100
avail=np.where(els.status.isin(['u','n','s']),0,np.where(els.status=='i',np.minimum(avail,0.3),avail))
els['mins_exp']=np.clip(base,0,0.95)*90; els['avail']=avail
# team strength from results: this season blended with last season's goal rates (promoted sides get a weaker prior)
lt=pd.read_csv(HIST/f'{PREV}_teams.csv',encoding='latin-1')[['id','name']]; lf=pd.read_csv(HIST/f'{PREV}_fixtures.csv',encoding='latin-1')
lf=lf[lf.finished==True] if 'finished' in lf else lf
gf={};ga={};gp={}
for r in lf.itertuples():
    for t,f,a in((r.team_h,r.team_h_score,r.team_a_score),(r.team_a,r.team_a_score,r.team_h_score)):
        gf[t]=gf.get(t,0)+f;ga[t]=ga.get(t,0)+a;gp[t]=gp.get(t,0)+1
nm=dict(zip(lt.id,lt.name)); last={nm[t]:(gf[t]/gp[t],ga[t]/gp[t]) for t in gp}
LG=np.mean([v[0] for v in last.values()])
cf={t:0 for t in teams.index};ca=dict(cf);cg=dict(cf)
for f in fx:
    if f['finished'] and f['event'] and f['event']<=CUR:
        for t,g,o in((f['team_h'],f['team_h_score'],f['team_a_score']),(f['team_a'],f['team_a_score'],f['team_h_score'])):
            cf[t]+=g;ca[t]+=o;cg[t]+=1
ATT={};DEF={};K=30
for t in teams.index:
    pf,pa=last.get(teams.loc[t,'name'],(LG*0.85,LG*1.15))
    ATT[t]=((cf[t]+pf*K)/(cg[t]+K))/LG; DEF[t]=((ca[t]+pa*K)/(cg[t]+K))/LG
teams['att']=pd.Series(ATT);teams['dfc']=pd.Series(DEF)
fl={}
for f in fx:
    if f['event'] and GW0<=f['event']<GW0+H:
        fl.setdefault((f['team_h'],f['event']),[]).append((f['team_a'],True)); fl.setdefault((f['team_a'],f['event']),[]).append((f['team_h'],False))
def mult(team,gw,p):
    m=0
    for opp,home in fl.get((team,gw),[]):
        x=teams.loc[opp,'dfc']**0.6 if p in('MID','FWD') else 1/teams.loc[opp,'att']**0.6
        m+=x*(1.08 if home else 0.92)
    return m
for i in range(H):
    els[f'xp{i}']=[(r.mins_exp/90)*r.rate90*mult(r.team,GW0+i,r.pos)*r.avail for r in els.itertuples()]
els.to_pickle(RAW/'players_model.pkl')
print('model A done: data through GW',CUR,'| predicting from GW',GW0)
