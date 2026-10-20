"""Model B (component model) + 75/25 blend with Model A + per-position calibration. Rewrites data/raw/players_model.pkl."""
import json, numpy as np, pandas as pd, warnings
warnings.filterwarnings('ignore')
from fplcfg import *
import minutes_lib as ml
PMIN=450
b=json.loads((RAW/'bootstrap.json').read_text(encoding='utf8')); fx=json.loads((RAW/'fixtures.json').read_text(encoding='utf8'))
CUR,GW0=state(b,fx)
els=pd.read_pickle(RAW/'players_model.pkl'); teams=pd.DataFrame(b['teams']).set_index('id')
W=json.loads((DATA/'minutes_weights.json').read_text()); w60=np.array(W['w60']); wan=np.array(W['wan'])
rows=[]
for g in range(1,CUR+1):
    for e in json.loads((LIVE/f'gw{g}.json').read_text(encoding='utf8'))['elements']:
        s=e['stats']
        rows.append(dict(id=e['id'],gw=g,min=s['minutes'],xg=float(s['expected_goals']),xa=float(s['expected_assists']),xgc=float(s['expected_goals_conceded']),
            bon=s['bonus'],yc=s['yellow_cards'],sv=s['saves'],dc=s['defensive_contribution'],pts=s['total_points']))
cur=pd.DataFrame(rows)
E=els.set_index('id'); E['pos']=E.element_type-1; E['pb']=pd.cut(E.price,ml.PB)
cs=cur.groupby('id').agg(min=('min','sum'),xg=('xg','sum'),xa=('xa','sum'),bon=('bon','sum'),yc=('yc','sum'),sv=('sv','sum'),pts=('pts','sum'))
cur=cur.merge(E[['pos','team']],left_on='id',right_index=True)
cur['hit']=((cur.dc>=np.where(cur.pos==1,10,12))&(cur.pos!=0)).astype(float)
X=E[['pos','team','pb']].join(cs).fillna(0); X['hits']=cur.groupby('id').hit.sum().reindex(X.index).fillna(0)
d25,p25=ml.load(PREV)
d25['hit']=((d25.defensive_contribution>=np.where(d25.pos==1,10,12))&(d25.pos!=0)).astype(float)
pv=d25.groupby('code').agg(min=('minutes','sum'),xg=('expected_goals','sum'),xa=('expected_assists','sum'),bon=('bonus','sum'),yc=('yellow_cards','sum'),
    sv=('saves','sum'),pts=('total_points','sum'),hits=('hit','sum'))
pv=pv.join(p25.set_index('code')[['element_type','now_cost']]); pv['pb']=pd.cut(pv.now_cost/10,ml.PB); pv['pos']=pv.element_type-1
big=pv[pv['min']>=900]; STATS=['xg','xa','bon','yc','sv','pts','hits']
prior90={c:(big.groupby(['pos','pb'],observed=True)[c].sum()/big.groupby(['pos','pb'],observed=True)['min'].sum()*90) for c in STATS}
posmean={c:(big.groupby('pos')[c].sum()/big.groupby('pos')['min'].sum()*90) for c in STATS}
pvc=pv.reindex(E.code.values); rates={}
for c in STATS:
    pri=np.array([prior90[c].get((p,bd),np.nan) for p,bd in zip(X.pos,X.pb)]); pri=np.where(np.isnan(pri),X.pos.map(posmean[c]).values,pri)
    rates[c]=pd.Series((pvc[c].fillna(0).values*0.6+X[c].values*1.5+pri/90*PMIN)/((pvc['min'].fillna(0).values*0.6+X['min'].values*1.5+PMIN)/90),index=X.index)
rates['hits']=rates['hits'].where(X.pos!=0,0)
# team ratings from xG for/against, blended with last season by name, normalised to mean 1
txp=d25.groupby(['team_id','fixture']).agg(xg=('expected_goals','sum'),xgc=('expected_goals_conceded','max')).reset_index()
t25=ml.team_names(PREV); tprior=txp.groupby('team_id').agg(xg=('xg','mean'),xgc=('xgc','mean')); tprior.index=[t25.get(i) for i in tprior.index]
LGx=txp.xg.mean(); f25=d25.drop_duplicates('fixture'); LGg=(f25.team_h_score+f25.team_a_score).mean()/2
tg=cur.groupby(['team','gw']).agg(xg=('xg','sum'),xgc=('xgc','max')).reset_index().groupby('team').agg(xg=('xg','sum'),xgc=('xgc','sum'),n=('xg','size'))
att={};dfc={};k=10
for tid in teams.index:
    nm=teams.loc[tid,'name']; n=tg.n.get(tid,0)
    px,pc_=(tprior.loc[nm,'xg'],tprior.loc[nm,'xgc']) if nm in tprior.index else (LGx*0.85,LGx*1.15)
    att[tid]=((tg.xg.get(tid,0)+px*k)/(n+k))/LGx; dfc[tid]=((tg.xgc.get(tid,0)+pc_*k)/(n+k))/LGx
teams['att']=pd.Series(att); teams['dfc']=pd.Series(dfc); teams['att']/=teams.att.mean(); teams['dfc']/=teams.dfc.mean()
# minutes probabilities as of the last finished gameweek
M=np.zeros((E.index.max()+1,60))
for r in cur.itertuples(): M[r.id,r.gw]+=r.min
psh=np.zeros(M.shape[0]); psh[E.index.values]=pd.Series(E.code.values,index=E.index).map(pv['min']).fillna(0).values/(38*90)
posarr=np.full(M.shape[0],-1); posarr[E.index.values]=E.pos.values
MF=ml.min_features(M,max(CUR,1)+1,psh,posarr)
av=pd.Series(E.avail.values,index=E.index)
p60=pd.Series(ml.sig(MF@w60)[E.index.values],index=E.index)*av; pany=pd.Series(ml.sig(MF@wan)[E.index.values],index=E.index)*av
mexp=p60*0.93+(pany-p60).clip(lower=0)*0.35
fl={}
for f in fx:
    if f['event'] and GW0<=f['event']<GW0+H:
        fl.setdefault((f['team_h'],f['event']),[]).append((f['team_a'],True)); fl.setdefault((f['team_a'],f['event']),[]).append((f['team_h'],False))
GP=pd.Series(E.pos.map(ml.GPTS)); CP=pd.Series(E.pos.map(ml.CSPTS)); comp={}
for i in range(H):
    gw=GW0+i; tot=pd.Series(0.0,index=E.index)
    for tid in teams.index:
        idx=E.index[E.team==tid]
        for opp,home in fl.get((tid,gw),[]):
            ha=1.08 if home else 0.92; fxA=(teams.loc[opp,'dfc']**0.6)*ha
            lam=LGg*teams.loc[opp,'att']*teams.loc[tid,'dfc']*(0.9 if home else 1.1); pcs=np.exp(-lam)
            m=mexp[idx]; pos=E.pos[idx]
            xp=pany[idx]+p60[idx]+m*rates['xg'][idx]*fxA*GP[idx]+m*rates['xa'][idx]*fxA*3+p60[idx]*pcs*CP[idx]-0.5*lam*m*pos.isin([0,1])
            xp+=np.where(pos==0,m*rates['sv'][idx]*(teams.loc[opp,'att']**0.6)/ha/3,0)+m*rates['bon'][idx]-m*rates['yc'][idx]+2*m*rates['hits'][idx]
            tot[idx]+=xp
    comp[i]=tot
CAL={int(k):v for k,v in json.loads((DATA/'calib.json').read_text()).items()}
posser=els.element_type-1; a=posser.map(lambda p:CAL[p]['a']); bb=posser.map(lambda p:CAL[p]['b'])
disc=np.array([1,0.95,0.9,0.85,0.8,0.75])
for i in range(H):
    els[f'xp_old{i}']=els[f'xp{i}']; els[f'xp_comp{i}']=els.id.map(comp[i]).fillna(0)
    raw=0.25*els[f'xp_old{i}']+0.75*els[f'xp_comp{i}']; els[f'xp_raw{i}']=raw
    els[f'xp{i}']=(bb*raw+a*np.clip(raw/2,0,1)).clip(lower=0)    # calibrated per position; tiny raw values get no intercept
cols=[f'xp{i}' for i in range(H)]
els['xpH']=(els[cols].values*disc[:H]).sum(1); els['xp_next']=els['xp0']
els.to_pickle(RAW/'players_model.pkl')
print('model B + blend done')
