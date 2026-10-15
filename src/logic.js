// FPL Assistant logic: pure functions over the embedded data D. No DOM access here.
const POSN=['GK','DEF','MID','FWD'],QUOTA=[2,5,5,3],DISC=[1,.95,.9,.85,.8,.75],BW=.12,HIT=4;
const FORMS=[];for(let d=3;d<=5;d++)for(let m=2;m<=5;m++){const f=10-d-m;if(f>=1&&f<=3)FORMS.push([d,m,f])}
const P=D.players,NG=D.H,GW0=D.gw0,TM=D.teams;
const BY=new Map(P.map(p=>[p.i,p]));
P.forEach(p=>{p.v=0;for(let g=0;g<NG;g++)p.v+=DISC[g]*p.x[g];p.v6=p.v});
const sumTop=(l,n)=>{let s=0;for(let k=0;k<n&&k<l.length;k++)s+=l[k];return s};
// total expected points over the horizon for a squad: best XI each gameweek, captain = best XI player, bench weighted BW
const PI=[];P.forEach(p=>{PI[p.i]=p});
const AB=[new Float64Array(6),new Float64Array(6),new Float64Array(6),new Float64Array(6)];
const PRE=[new Float64Array(7),new Float64Array(7),new Float64Array(7),new Float64Array(7)];
function scoreSquad(ids,hz){
  let tot=0;
  for(let g=0;g<hz;g++){
    const n=[0,0,0,0];let all=0;
    for(let k=0;k<4;k++)AB[k].fill(0);
    for(let q=0;q<ids.length;q++){
      const p=PI[ids[q]],k=p.p,v=p.x[g],a=AB[k];let j=n[k]++;
      while(j>0&&a[j-1]<v){a[j]=a[j-1];j--}a[j]=v;all+=v;
    }
    for(let k=1;k<4;k++){const a=AB[k],pr=PRE[k];pr[0]=0;for(let m=0;m<6;m++)pr[m+1]=pr[m]+a[m]}
    let best=-1;const gk=AB[0][0];
    for(let f=0;f<FORMS.length;f++){const fm=FORMS[f];const s=gk+PRE[1][fm[0]]+PRE[2][fm[1]]+PRE[3][fm[2]];if(s>best)best=s}
    const cap=Math.max(gk,AB[1][0],AB[2][0],AB[3][0]);
    tot+=DISC[g]*(best+cap+BW*(all-best));
  }
  return tot;
}
// detailed lineup for one gameweek index g (0 = next gameweek)
function lineup(ids,g){
  const by=[[],[],[],[]];ids.forEach(i=>{const p=BY.get(i);if(p)by[p.p].push(p)});
  by.forEach(l=>l.sort((u,v)=>v.x[g]-u.x[g]||v.v-u.v));
  let best=-1,bf=null;
  for(const f of FORMS){const s=(by[0][0]?by[0][0].x[g]:0)+[1,2,3].reduce((t,k)=>t+sumTop(by[k].map(p=>p.x[g]),f[k-1]),0);if(s>best){best=s;bf=f}}
  if(!bf)return null;
  const xi=[];if(by[0][0])xi.push(by[0][0]);
  for(let k=1;k<=3;k++)xi.push(...by[k].slice(0,bf[k-1]));
  const inXI=new Set(xi.map(p=>p.i));
  const ranked=xi.slice().sort((u,v)=>v.x[g]-u.x[g]);
  const bench=[];
  if(by[0][1])bench.push(by[0][1]);   // reserve GK is always the first bench slot
  const outf=[].concat(by[1],by[2],by[3]).filter(p=>!inXI.has(p.i)).sort((u,v)=>v.x[g]-u.x[g]);
  bench.push(...outf);
  return{xi,bench,form:bf,cap:ranked[0],vc:ranked[1],xp:best,total:best+ranked[0].x[g]};
}
function teamCount(ids){const c={};ids.forEach(i=>{const t=BY.get(i).t;c[t]=(c[t]||0)+1});return c}
function validSquad(ids){
  if(ids.length!==15)return false;
  const q=[0,0,0,0];ids.forEach(i=>q[BY.get(i).p]++);
  if(q.some((n,k)=>n!==QUOTA[k]))return false;
  return Object.values(teamCount(ids)).every(n=>n<=3);
}
function sellOf(st,id){const s=st.sell&&st.sell[id];return s!=null&&s!==''?+s:BY.get(id).c}
function usable(p){return p.s!=='u'&&p.s!=='n'&&p.s!=='s'&&p.v>0}
// single and double transfer search. Returns {base,one:[...],two:[...]}
function searchTransfers(st,hz){
  const ids=st.squad.slice();if(ids.length!==15)return null;
  const base=scoreSquad(ids,hz),tc=teamCount(ids),inSq=new Set(ids);
  const mk=(outs,ins,sc)=>{
    const n=outs.length,hit=Math.max(0,n-st.ft)*HIT;
    const bank=st.bank+outs.reduce((s,o)=>s+sellOf(st,o),0)-ins.reduce((s,i)=>s+BY.get(i).c,0);
    return{outs,ins,gain:sc-base,hit,net:sc-base-hit,bank:Math.round(bank*10)/10};
  };
  const pool=P.filter(p=>!inSq.has(p.i)&&usable(p));
  const one=[];
  for(const o of ids){
    const po=BY.get(o);
    for(const c of pool){
      if(c.p!==po.p)continue;
      if(st.bank+sellOf(st,o)-c.c<-1e-9)continue;
      const cnt=(tc[c.t]||0)-(c.t===po.t?1:0)+1;if(cnt>3)continue;
      const nid=ids.map(x=>x===o?c.i:x);
      one.push(mk([o],[c.i],scoreSquad(nid,hz)));
    }
  }
  one.sort((a,b)=>b.net-a.net);
  // two transfers: restrict candidate pool to strong options plus cheap enablers
  const cand=[[],[],[],[]];
  for(let k=0;k<4;k++){
    const l=pool.filter(p=>p.p===k);
    const top=l.slice().sort((a,b)=>b.v-a.v).slice(0,16);
    const val=l.filter(p=>p.v>=(k===0?6:8)).sort((a,b)=>b.v/b.c-a.v/a.c).slice(0,8);
    cand[k]=[...new Set([...top,...val])];
  }
  const two=[];
  for(let a=0;a<15;a++)for(let b=a+1;b<15;b++){
    const o1=ids[a],o2=ids[b],p1=BY.get(o1),p2=BY.get(o2);
    const money=st.bank+sellOf(st,o1)+sellOf(st,o2);
    for(const c1 of cand[p1.p])for(const c2 of cand[p2.p]){
      if(c1.i===c2.i)continue;
      if(money-c1.c-c2.c<-1e-9)continue;
      const nid=ids.map(x=>x===o1?c1.i:x===o2?c2.i:x);
      const cnt=teamCount(nid);if(Object.values(cnt).some(n=>n>3))continue;
      two.push(mk([o1,o2],[c1.i,c2.i],scoreSquad(nid,hz)));
    }
  }
  two.sort((a,b)=>b.net-a.net);
  return{base,one:one.slice(0,10),two:two.slice(0,10),oneAll:one.length};
}
// build a whole squad (Wildcard / Free Hit / fresh start) within a budget by local search with several starts
function buildSquad(budget,hz,fixed){
  fixed=fixed||[];
  const pool=P.filter(usable),fx=new Set(fixed);
  const starts=[(a,b)=>a.c-b.c||b.v-a.v,(a,b)=>b.v/b.c-a.v/a.c];
  let best=null;
  for(const order of starts){const r=searchFrom(order,budget,hz,fixed,fx,pool);if(r&&(!best||r.score>best.score))best=r}
  return best;
}
function searchFrom(order,budget,hz,fixed,fx,pool){
  const sq=fixed.slice(),cnt=[0,0,0,0],tc={};
  fixed.forEach(i=>{const p=PI[i];cnt[p.p]++;tc[p.t]=(tc[p.t]||0)+1});
  let cost=sq.reduce((s,i)=>s+PI[i].c,0);
  const sorted=pool.slice().sort(order),cheap=pool.slice().sort((a,b)=>a.c-b.c);
  const cheapestLeft=()=>{let need=0;const c2=cnt.slice();for(let k=0;k<4;k++)for(const p of cheap){if(c2[k]>=QUOTA[k])break;if(p.p===k&&!sq.includes(p.i)){need+=p.c;c2[k]++}}return need};
  for(let k=0;k<4;k++)for(const p of sorted){
    if(cnt[k]>=QUOTA[k])break;
    if(p.p!==k||sq.includes(p.i)||(tc[p.t]||0)>=3)continue;
    sq.push(p.i);cnt[k]++;tc[p.t]=(tc[p.t]||0)+1;cost+=p.c;
    if(cost+cheapestLeft()>budget+1e-9){sq.pop();cnt[k]--;tc[p.t]--;cost-=p.c}
  }
  for(let k=0;k<4;k++)for(const p of cheap){if(cnt[k]>=QUOTA[k])break;if(p.p!==k||sq.includes(p.i)||(tc[p.t]||0)>=3)continue;sq.push(p.i);cnt[k]++;tc[p.t]=(tc[p.t]||0)+1;cost+=p.c}
  if(sq.length!==15)return null;
  let cur=scoreSquad(sq,hz);
  const inSq=new Set(sq);
  const byPos=[0,1,2,3].map(k=>pool.filter(p=>p.p===k));
  for(let it=0;it<60;it++){
    let bestS=cur,bm=null;
    for(let a=0;a<15;a++){
      const o=sq[a];if(fx.has(o))continue;const po=PI[o];
      for(const c of byPos[po.p]){
        if(inSq.has(c.i))continue;
        if(cost-po.c+c.c>budget+1e-9)continue;
        if((tc[c.t]||0)-(c.t===po.t?1:0)>=3)continue;
        sq[a]=c.i;const sc=scoreSquad(sq,hz);sq[a]=o;
        if(sc>bestS+1e-9){bestS=sc;bm=[a,c]}
      }
    }
    if(bm){const o=sq[bm[0]],po=PI[o],c=bm[1];
      inSq.delete(o);inSq.add(c.i);tc[po.t]--;tc[c.t]=(tc[c.t]||0)+1;cost+=c.c-po.c;sq[bm[0]]=c.i;cur=bestS;continue}
    // no single swap helps: best pair swap among the strongest candidates
    const cand=byPos.map(l=>l.filter(p=>!inSq.has(p.i)).sort((x,y)=>y.v-x.v).slice(0,16));
    let pb=null,pbs=cur;
    for(let a=0;a<15;a++)for(let b=a+1;b<15;b++){
      const o1=sq[a],o2=sq[b];if(fx.has(o1)||fx.has(o2))continue;
      const p1=PI[o1],p2=PI[o2],room=budget-(cost-p1.c-p2.c);
      for(const c1 of cand[p1.p])for(const c2 of cand[p2.p]){
        if(c1.i===c2.i||c1.c+c2.c>room+1e-9)continue;
        // team limit check on the counts after both swaps
        let ok=true;const chg={};
        chg[p1.t]=(chg[p1.t]||0)-1;chg[p2.t]=(chg[p2.t]||0)-1;chg[c1.t]=(chg[c1.t]||0)+1;chg[c2.t]=(chg[c2.t]||0)+1;
        for(const t in chg)if((tc[t]||0)+chg[t]>3){ok=false;break}
        if(!ok)continue;
        sq[a]=c1.i;sq[b]=c2.i;const sc=scoreSquad(sq,hz);sq[a]=o1;sq[b]=o2;
        if(sc>pbs+1e-6){pbs=sc;pb=[a,b,c1,c2]}
      }
    }
    if(!pb)break;
    const [a,b,c1,c2]=pb,o1=sq[a],o2=sq[b],p1=PI[o1],p2=PI[o2];
    inSq.delete(o1);inSq.delete(o2);inSq.add(c1.i);inSq.add(c2.i);
    tc[p1.t]--;tc[p2.t]--;tc[c1.t]=(tc[c1.t]||0)+1;tc[c2.t]=(tc[c2.t]||0)+1;
    cost=cost-p1.c-p2.c+c1.c+c2.c;sq[a]=c1.i;sq[b]=c2.i;cur=pbs;
  }
  return{ids:sq.slice(),cost:Math.round(cost*10)/10,score:cur};
}
// ---- mini league ----
const erf=x=>{const s=Math.sign(x);x=Math.abs(x);const t=1/(1+0.3275911*x);const y=1-(((((1.061405429*t-1.453152027)*t)+1.421413741)*t-0.284496736)*t+0.254829592)*t*Math.exp(-x*x);return s*y};
const Phi=x=>0.5*(1+erf(x/Math.SQRT2));
const ptVar=xp=>4+2.2*xp;
function compare(mine,theirs,hz,lead){
  let mean=0,variance=0,mean1=0,var1=0;
  for(let g=0;g<hz;g++){
    const a=lineup(mine,g),b=lineup(theirs,g);if(!a||!b)continue;
    const coef=new Map();
    a.xi.forEach(p=>coef.set(p.i,(coef.get(p.i)||0)+(p===a.cap?2:1)));
    b.xi.forEach(p=>coef.set(p.i,(coef.get(p.i)||0)-(p===b.cap?2:1)));
    let m=0,v=0;
    coef.forEach((c,i)=>{if(!c)return;const xp=BY.get(i).x[g];m+=c*xp;v+=c*c*ptVar(xp)});
    mean+=m;variance+=v;if(g===0){mean1=m;var1=v}
  }
  const sd=Math.sqrt(variance||1),sd1=Math.sqrt(var1||1);
  const sm=new Set(mine),st=new Set(theirs);
  return{mean,sd,mean1,sd1,pNext:Phi((lead+mean1)/sd1),pHz:Phi((lead+mean)/sd),
    shared:mine.filter(i=>st.has(i)),onlyMine:mine.filter(i=>!st.has(i)),onlyTheirs:theirs.filter(i=>!sm.has(i))};
}

// ---- paste import: find player names in text copied from the FPL site ----
const norm=t=>String(t).normalize('NFD').replace(/[\u0300-\u036f]/g,'').toLowerCase().replace(/ß/g,'ss').replace(/ø/g,'o').replace(/æ/g,'ae').replace(/đ/g,'d').replace(/ł/g,'l').replace(/[^a-z0-9]+/g,' ').trim();
const NAMEIDX=(()=>{const m=new Map();P.forEach(p=>{const k=norm(p.n);if(!k)return;if(!m.has(k))m.set(k,[]);m.get(k).push(p)});m.forEach(l=>l.sort((a,b)=>b.o-a.o));return m})();
const NAMEKEYS=[...NAMEIDX.keys()].sort((a,b)=>b.length-a.length);
// returns rows [{cands:[ids], sel:id}] in the order the names appear in the text
function parsePaste(text){
  let rest=' '+norm(text)+' ';
  const hits=[];
  for(const k of NAMEKEYS){
    const needle=' '+k+' ';let at=rest.indexOf(needle);
    while(at>=0){hits.push({at,k});rest=rest.slice(0,at)+' '.repeat(needle.length)+rest.slice(at+needle.length);at=rest.indexOf(needle)}
  }
  hits.sort((a,b)=>a.at-b.at);
  const used=new Set(),rows=[];
  for(const h of hits){
    const c=NAMEIDX.get(h.k).filter(p=>!used.has(p.i));
    if(!c.length)continue;
    used.add(c[0].i);rows.push({cands:NAMEIDX.get(h.k).map(p=>p.i),sel:c[0].i});
  }
  return rows;
}
if(typeof module!=='undefined')module.exports={parsePaste,norm,scoreSquad,lineup,searchTransfers,buildSquad,compare,validSquad,teamCount,BY,P,POSN,QUOTA,usable};
