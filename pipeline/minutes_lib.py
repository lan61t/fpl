"""Minutes model: logistic regression for P(play 60+) and P(play at all), plus shared loaders and constants."""
import json, numpy as np, pandas as pd, warnings
from fplcfg import *
warnings.filterwarnings('ignore')
S=HIST_SEASONS
PB=[0,4.5,5.5,6.5,7.5,9,10.5,16]
GPTS={0:6,1:6,2:5,3:4}; CSPTS={0:4,1:4,2:1,3:0}
def load(s):
    d=pd.read_csv(HIST/f'{s}_merged_gw.csv',encoding='latin-1',low_memory=False)
    p=pd.read_csv(HIST/f'{s}_players_raw.csv',encoding='latin-1',low_memory=False)
    d=d.merge(p[['id','code','element_type','team','now_cost']].rename(columns={'id':'element','team':'team_id'}),on='element',how='left')
    if 'GW' not in d: d['GW']=d['round']
    d=d.dropna(subset=['code','team_id']); d=d[d.element_type.isin([1,2,3,4])]; d['team_id']=d.team_id.astype(int); d['pos']=d.element_type-1
    d['opp']=d.opponent_team.astype(int)
    for c in ['expected_goals','expected_assists','expected_goals_conceded','bonus','yellow_cards','red_cards','saves','defensive_contribution','starts']:
        if c not in d: d[c]=np.nan
    return d,p
def team_names(s):
    try: return pd.read_csv(HIST/f'{s}_teams.csv',encoding='latin-1').set_index('id').name
    except Exception: return None
def minute_matrix(d):
    M=np.zeros((d.element.max()+1,60)); g=d.groupby(['element','GW']).minutes.sum()
    for (e,w),v in g.items(): M[e,w]=v
    return M
def min_features(M,t,prevshare,pos):
    """features for predicting GW t for every element row of M (uses minutes before t only)"""
    m1=M[:,t-1]/90; m3=M[:,max(t-3,1):t].mean(1)/90; m5=M[:,max(t-5,1):t].mean(1)/90
    share=M[:,1:t].sum(1)/((t-1)*90)
    L5=M[:,max(t-5,1):t]; L3=M[:,max(t-3,1):t]; L10=M[:,max(t-10,1):t]
    cols=[np.ones(len(M)),m1,m3,m5,share,prevshare,pos==0,pos==1,pos==2,m1*m3,(share>0),
          (L5>=60).mean(1),(L5==0).mean(1),L3.min(1)/90,M[:,max(t-2,1):t].mean(1)/90,L10.mean(1)/90,
          ((L5>0)&(L5<60)).mean(1),(L5>=60).mean(1)*(pos==1),(L5>=60).mean(1)*(pos==2),(L5>=60).mean(1)*(pos==3),
          np.minimum(t-1,10)/10*np.ones(len(M))*(share>0)]
    return np.column_stack(cols).astype(float)
def fit_logit(X,y,l2=1.0,it=25):
    w=np.zeros(X.shape[1])
    for _ in range(it):
        p=1/(1+np.exp(-(X@w))); W=p*(1-p)+1e-6
        w+=np.linalg.solve((X*W[:,None]).T@X+l2*np.eye(len(w)),X.T@(y-p)-l2*w)
    return w
sig=lambda z:1/(1+np.exp(-z))
def prev_share(prev_players,codes):
    if prev_players is None: return np.zeros(len(codes))
    return codes.map(prev_players.set_index('code').minutes).fillna(0).values/(38*90)
def train(n_seasons=None):
    """fit on every season in HIST_SEASONS except the first (needs last-season minutes as a feature)"""
    Xs=[];y60=[];yan=[]
    for si in range(1,len(S) if n_seasons is None else n_seasons):
        d,_=load(S[si]); _,pp=load(S[si-1]); M=minute_matrix(d)
        el=d.groupby('element').agg(code=('code','first'),pos=('pos','first'))
        codes=pd.Series(np.nan,index=range(M.shape[0])); codes.loc[el.index]=el.code
        pos=np.full(M.shape[0],-1); pos[el.index]=el.pos.values
        psh=prev_share(pp,codes.fillna(-1))
        for t in range(4,39):
            X=min_features(M,t,psh,pos); pool=(M[:,max(t-3,1):t].sum(1)>0)&(pos>=0)
            Xs.append(X[pool]);y60.append((M[:,t]>=60)[pool]);yan.append((M[:,t]>0)[pool])
    X=np.vstack(Xs)
    return fit_logit(X,np.concatenate(y60).astype(float)),fit_logit(X,np.concatenate(yan).astype(float)),len(X)
