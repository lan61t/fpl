"""Score every completed gameweek: (1) the frozen predictions in log/pred_gwNN.json against the real points, compared with
simple baselines; (2) the paper manager's locked picks in log/paper_gwNN.json. Writes log/track_record.json.
A gameweek is rescored on every run until FPL marks it finished, because bonus points can still change."""
import json, glob, numpy as np, pandas as pd
from scipy_free import spearman
from fplcfg import *
LOG=ROOT/'log'
b=json.loads((RAW/'bootstrap.json').read_text(encoding='utf8')); fx=json.loads((RAW/'fixtures.json').read_text(encoding='utf8'))
CUR,GW0=state(b,fx)
EV={e['id']:e for e in b['events']}
POS=['GK','DEF','MID','FWD']
def live(g):
    f=LIVE/f'gw{g}.json'
    if not f.exists(): return None
    return {e['id']:(e['stats']['total_points'],e['stats']['minutes']) for e in json.loads(f.read_text(encoding='utf8'))['elements']}
def metrics(d,col):
    d=d.dropna(subset=[col]); top=d.sort_values(col,ascending=False)
    return dict(sp=round(spearman(d[col].values,d.act.values),3),mae=round(float((d[col]-d.act).abs().mean()),2),bias=round(float((d[col]-d.act).mean()),2),
        top1=float(top.act.iloc[0]),top3=round(float(top.act.iloc[:3].mean()),2),top10=round(float(top.act.iloc[:10].mean()),2),top15=round(float(top.act.iloc[:15].mean()),2))
def review(g):
    f=LOG/f'pred_gw{g:02d}.json'
    if not f.exists() or g>CUR: return None
    act=live(g)
    if not act: return None
    snap=json.loads(f.read_text(encoding='utf8'))
    prev={}
    for k in (g-3,g-2,g-1):
        l=live(k) if k>=1 else None
        if not l: continue
        for i,(p,m) in l.items():
            q=prev.setdefault(i,{'pts':0,'min':0,'n':0}); q['pts']+=p; q['min']+=m; q['n']+=1
    rows=[]
    for p in snap['players']:
        a=act.get(p['i'],(0,0)); q=prev.get(p['i'],{'pts':0,'min':0,'n':0})
        rows.append(dict(id=p['i'],name=p['n'],pos=p['p'],model=p['x'][0],old=p.get('old'),comp=p.get('comp'),raw=p.get('raw'),own=p['o'],
            form=(q['pts']/max(q['n'],1)),pmin=q['min'],act=a[0],mins=a[1]))
    df=pd.DataFrame(rows); reg=df[df.pmin>0]
    if len(reg)<50: return None
    out=dict(gw=g,saved=snap['saved'],n=int(len(reg)),final=bool(EV[g]['finished']),avg=EV[g].get('average_entry_score'),highest=EV[g].get('highest_score'),
        model=metrics(reg,'model'),form=metrics(reg,'form'),own=metrics(reg,'own'))
    for c in ('old','comp','raw'):
        if reg[c].notna().all(): out[c]=metrics(reg,c)
    cap=df.sort_values('model',ascending=False).iloc[0]
    out['captain']=dict(name=cap['name'],pred=round(float(cap.model),2),pts=int(cap.act),rank=int((df.act>cap.act).sum()+1))
    # by position: predicted vs actual
    out['by_pos']={POS[p]:dict(n=int(len(x)),pred=round(float(x.model.mean()),2),act=round(float(x.act.mean()),2)) for p,x in reg.groupby('pos')}
    return out
def paper(g):
    f=LOG/f'paper_gw{g:02d}.json'
    if not f.exists() or g>CUR: return None
    pk=json.loads(f.read_text(encoding='utf8'))
    if pk.get('pending'): return None
    act=live(g)
    if not act: return None
    pos={int(i):m['p'] for i,m in pk['meta'].items()}
    xi=list(pk['xi']); bn=list(pk['bench'])
    for o in list(xi):                                  # automatic substitutions for players who did not play
        if act.get(o,(0,0))[1]>0: continue
        for x in bn:
            if act.get(x,(0,0))[1]<=0: continue
            if (pos[o]==0)!=(pos[x]==0): continue
            new=[i for i in xi if i!=o]+[x]; q=[sum(1 for i in new if pos[i]==k) for k in range(4)]
            if q[1]>=3 and q[2]>=2 and q[3]>=1: xi=new; bn.remove(x); break
    cap=pk['cap'] if act.get(pk['cap'],(0,0))[1]>0 else pk['vc']
    base=sum(act.get(i,(0,0))[0] for i in xi); cp=act.get(cap,(0,0))[0]
    return dict(points=int(base+cp),hits=int(pk['hits']),net=int(base+cp-pk['hits']),captain=pk['meta'][str(cap)]['n'],cap_pts=int(cp),
        moves=[f"{m['out']['n']} -> {m['in']['n']}" for m in pk['moves']],rule=pk['rule'],formation=pk['formation'])
entries=[]
gws=sorted({int(f.split('pred_gw')[1][:2]) for f in glob.glob(str(LOG/'pred_gw*.json'))})
for g in gws:
    r=review(g)
    if r is None: continue
    r['paper']=paper(g); entries.append(r)
def avg(path):
    v=[]
    for e in entries:
        x=e
        for k in path: x=x.get(k) if isinstance(x,dict) else None
        if x is not None: v.append(x)
    return round(float(np.mean(v)),3) if v else None
pp=[e['paper'] for e in entries if e.get('paper')]
summary=dict(weeks=len(entries),sp_model=avg(['model','sp']),sp_form=avg(['form','sp']),sp_own=avg(['own','sp']),
    mae_model=avg(['model','mae']),mae_form=avg(['form','mae']),top15_model=avg(['model','top15']),top15_form=avg(['form','top15']),
    captain_pts=avg(['captain','pts']),paper_weeks=len(pp),paper_net=sum(p['net'] for p in pp),paper_hits=sum(p['hits'] for p in pp),
    avg_manager=sum(e['avg'] for e in entries if e.get('paper') and e.get('avg')) if pp else 0)
(LOG/'track_record.json').write_text(json.dumps(dict(updated=__import__('datetime').datetime.now(__import__('datetime').timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),summary=summary,entries=entries),separators=(',',':')),encoding='utf8')
print('track record:',len(entries),'gameweeks scored; paper manager weeks:',len(pp))
