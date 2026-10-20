// Paper-trading manager: follows exactly the advice the app gives, so its record shows what the advice is worth.
// Each run (hourly): lock the previous gameweek's picks once its deadline has passed, then decide the next gameweek's
// picks from the locked squad (re-done every run until the deadline, so the final picks use the latest data).
// Reads data.json and log/paper_state.json; writes log/paper_gwNN.json and log/paper_state.json.
const fs=require('fs'),path=require('path');
const ROOT=path.resolve(__dirname,'..');const LOG=path.join(ROOT,'log');fs.mkdirSync(LOG,{recursive:true});
const D=JSON.parse(fs.readFileSync(path.join(ROOT,'data.json'),'utf8'));
const stPath=path.join(LOG,'paper_state.json');
let S=fs.existsSync(stPath)?JSON.parse(fs.readFileSync(stPath,'utf8')):null;
const now=process.env.FPL_NOW?Date.parse(process.env.FPL_NOW):Date.now();   // FPL_NOW lets tests fake the clock
const G=D.gw0;
// 1. lock the previous pick once its deadline has passed
if(S&&S.pending&&now>=Date.parse(S.pending.deadline)){
  S.squad=S.pending.squad;S.bp=S.pending.bp;S.bank=S.pending.bank;S.ft=S.pending.ft_after;S.locked_gw=S.pending.gw;
  const f=path.join(LOG,`paper_gw${String(S.pending.gw).padStart(2,'0')}.json`);
  if(fs.existsSync(f)){const p=JSON.parse(fs.readFileSync(f,'utf8'));p.pending=false;fs.writeFileSync(f,JSON.stringify(p))}
  S.pending=null;
}
const persist=()=>{if(S)fs.writeFileSync(stPath,JSON.stringify(S))};
if(S&&S.locked_gw>=G){persist();console.log('GW',G,'already locked; nothing to do');process.exit(0)}
if(Date.parse(D.deadline)<=now){persist();console.log('deadline for GW',G,'has passed; waiting for the next gameweek');process.exit(0)}
// players that left the data (unavailable, no minutes) must still exist for the logic: add zero-xP stubs
const meta=(S&&S.meta)||{};
if(S)for(const id of S.squad){if(!D.players.find(p=>p.i===id)){const m=meta[id]||{n:'?',p:1,t:1};D.players.push({i:id,n:m.n,t:m.t,p:m.p,c:(S.bp[id]||50)/10,o:0,s:'u',ch:0,nw:'',pts:0,mn:0,f:0,x:[0,0,0,0,0,0]})}}
global.D=D;
const L=require('./../src/logic.js');
const HZ=4,BAR_PER_GW=2.5;
const W=[1,.95,.9,.85,.8,.75].slice(0,HZ).reduce((a,b)=>a+b,0),BAR=BAR_PER_GW*W;
const price=id=>Math.round(L.BY.get(id).c*10);
let pick;
// no locked squad yet (first gameweek still pending): keep rebuilding the initial squad until its deadline passes
if(!S||!S.squad||S.squad.length!==15){
  // first gameweek: build the best squad for 100.0m
  const b=L.buildSquad(100,HZ);const bp={};b.ids.forEach(i=>bp[i]=price(i));
  const bank=1000-b.ids.reduce((s,i)=>s+price(i),0);
  const li=L.lineup(b.ids,0);
  pick={gw:G,rule:'initial squad (100.0m)',moves:[],hits:0,ft_before:0,ft_after:1,bank:bank,net:0,bar:BAR,squad:b.ids,bp,li};
}else{
  const ft=Math.min(5,S.ft+1);
  const sell={};for(const id of S.squad){const cp=price(id),bp=S.bp[id];sell[id]=(cp<=bp?cp:bp+Math.floor((cp-bp)/2))/10}
  const st={squad:S.squad.slice(),sell,bank:S.bank/10,ft,chips:{},hz:HZ};
  const r=L.searchTransfers(st,HZ);
  const all=[...r.one,...r.two];
  const best=all.slice().sort((a,b)=>b.net-a.net)[0];
  const bestFree=all.filter(m=>m.hit===0).sort((a,b)=>b.net-a.net)[0];
  let mv=null,rule='roll (no move clears the bar of '+BAR.toFixed(1)+' xP)';
  if(best&&best.net>=BAR){mv=best;rule='clear gain'}
  else if(ft>=5&&bestFree&&bestFree.net>0){mv=bestFree;rule='free move at the 5-transfer cap'}
  let squad=S.squad.slice(),bank=S.bank,bp=Object.assign({},S.bp),hits=0,moves=[];
  if(mv){
    for(let k=0;k<mv.outs.length;k++){
      const o=mv.outs[k],i=mv.ins[k];
      bank+=Math.round(sell[o]*10)-price(i);squad[squad.indexOf(o)]=i;delete bp[o];bp[i]=price(i);
      moves.push({out:{id:o,n:L.BY.get(o).n},in:{id:i,n:L.BY.get(i).n}});
    }
    hits=Math.max(0,mv.outs.length-ft)*4;
  }
  const used=mv?mv.outs.length:0;
  const li=L.lineup(squad,0);
  pick={gw:G,rule,moves,hits,ft_before:ft,ft_after:Math.max(ft-used,0),bank,net:mv?mv.net:(best?best.net:0),bar:BAR,squad,bp,li};
}
const li=pick.li;
const metaNew=Object.assign({},meta);
for(const id of pick.squad){const p=L.BY.get(id);metaNew[id]={n:p.n,p:p.p,t:p.t}}
const out={gw:G,saved:D.generated,deadline:D.deadline,pending:true,rule:pick.rule,hz:HZ,bar:+pick.bar.toFixed(2),net:+pick.net.toFixed(2),
  moves:pick.moves,hits:pick.hits,ft_before:pick.ft_before,ft_after:pick.ft_after,bank:pick.bank/10,
  formation:li.form.join('-'),xi:li.xi.map(p=>p.i),bench:li.bench.map(p=>p.i),cap:li.cap.i,vc:li.vc.i,
  squad:pick.squad,meta:Object.fromEntries(pick.squad.map(id=>[id,metaNew[id]])),xp_xi:+li.xp.toFixed(2)};
fs.writeFileSync(path.join(LOG,`paper_gw${String(G).padStart(2,'0')}.json`),JSON.stringify(out));
if(!S)S={squad:[],bp:{},bank:0,ft:0,locked_gw:0,pending:null,meta:{}};
S.meta=metaNew;
S.pending={gw:G,deadline:D.deadline,squad:pick.squad,bp:pick.bp,bank:pick.bank,ft_after:pick.ft_after};
fs.writeFileSync(stPath,JSON.stringify(S));
console.log(`paper manager GW${G}: ${pick.rule}; moves ${pick.moves.length}, hits -${pick.hits}; formation ${out.formation}; captain ${L.BY.get(out.cap).n}`);
