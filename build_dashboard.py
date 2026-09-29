"""Builds outputs/dashboard.html - a single self-contained decision cockpit.
All lane economics (feasibility, voyage cost, contract mix, entry timing, quote X-ray) are
re-computed in the browser from the embedded forecast scenario paths, so ANY origin x East-Coast
port x volume x duration the manager enters is evaluated live - no server needed (offline / on-prem).
"""
import json
import sys

from saarthi.config import OUT

HTML = r"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>FreightSaarthi Cockpit</title>
<script>__PLOTLY__</script>
<style>
:root{--bg:#f6f7f9;--card:#fff;--ink:#16202b;--mut:#5b6875;--line:#e2e6ea;--acc:#0b6bcb;--acc2:#0e9f6e;--warn:#c47f00;--bad:#c2372c;--chip:#eef3f9;--shade:rgba(11,107,203,.14)}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){--bg:#0f141a;--card:#161d25;--ink:#e6edf3;--mut:#9aa7b4;--line:#27313c;--acc:#4ea1f3;--acc2:#34c38f;--warn:#e0a526;--bad:#ef6a5e;--chip:#1d2733;--shade:rgba(78,161,243,.18)}}
:root[data-theme="dark"]{--bg:#0f141a;--card:#161d25;--ink:#e6edf3;--mut:#9aa7b4;--line:#27313c;--acc:#4ea1f3;--acc2:#34c38f;--warn:#e0a526;--bad:#ef6a5e;--chip:#1d2733;--shade:rgba(78,161,243,.18)}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:14px/1.45 system-ui,-apple-system,Segoe UI,Roboto,sans-serif}
header{padding:14px 20px;border-bottom:1px solid var(--line);display:flex;gap:14px;align-items:center;flex-wrap:wrap;background:var(--card)}
header h1{font-size:18px;margin:0}header .tag{font-size:12px;padding:3px 8px;border-radius:12px;background:var(--chip);color:var(--mut)}
.syn{background:#fff3cd;color:#7a5a00}@media (prefers-color-scheme:dark){:root:not([data-theme="light"]) .syn{background:#3a2f0b;color:#f3d27a}}
nav{display:flex;gap:4px;padding:8px 16px;flex-wrap:wrap;border-bottom:1px solid var(--line);background:var(--card);position:sticky;top:0;z-index:5}
nav button{border:0;background:none;color:var(--mut);padding:8px 12px;border-radius:8px;cursor:pointer;font:inherit}
nav button.on{background:var(--chip);color:var(--ink);font-weight:600}
main{padding:16px;max-width:1400px;margin:0 auto}.tab{display:none}.tab.on{display:block}
.grid{display:grid;gap:14px}.g2{grid-template-columns:repeat(auto-fit,minmax(340px,1fr))}.g3{grid-template-columns:repeat(auto-fit,minmax(260px,1fr))}
.side{grid-template-columns:320px 1fr}@media(max-width:900px){.side{grid-template-columns:1fr}}
.card{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:14px 16px;min-width:0}
.card h3{margin:0 0 10px;font-size:14px}.mut{color:var(--mut)}.small{font-size:12px}
label{display:block;font-size:12px;color:var(--mut);margin:8px 0 3px}select,input[type=number]{width:100%;padding:7px;border:1px solid var(--line);border-radius:8px;background:var(--bg);color:var(--ink);font:inherit}
input[type=range]{width:100%}.row{display:flex;gap:8px}.row>*{flex:1}
.kpis{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:10px}
.kpi{background:var(--chip);border-radius:10px;padding:10px 12px}.kpi b{display:block;font-size:20px}.kpi span{font-size:12px;color:var(--mut)}
table{border-collapse:collapse;width:100%;font-size:12.5px}th,td{padding:6px 8px;border-bottom:1px solid var(--line);text-align:right;white-space:nowrap}th:first-child,td:first-child{text-align:left}
th{color:var(--mut);font-weight:600}.tw{overflow-x:auto}
.pill{display:inline-block;padding:2px 8px;border-radius:10px;font-size:11.5px;background:var(--chip)}
.ok{color:var(--acc2)}.no{color:var(--bad)}.hi{border-left:4px solid var(--bad)}.me{border-left:4px solid var(--warn)}
.alert{padding:8px 10px;margin:6px 0;background:var(--chip);border-radius:8px}
.rec{font-size:15px;line-height:1.6}.rec b{color:var(--acc)}
.bar{display:flex;height:26px;border-radius:8px;overflow:hidden;margin:8px 0}.bar div{display:flex;align-items:center;justify-content:center;color:#fff;font-size:12px}
.plot{width:100%;height:320px}
</style></head><body>
<header><h1>FreightSaarthi</h1><span class="tag">Chartering &amp; freight-forecast cockpit (demo for SAIL, East Coast India)</span>
<span class="tag syn" id="lbl"></span><span class="tag" id="asof"></span></header>
<nav id="nav"></nav>
<main>
<section class="tab on" id="t-plan"><div class="grid side">
 <div class="card"><h3>Cargo requirement</h3>
  <label>Origin (load port)</label><select id="i-load"></select>
  <label>Destination (East Coast port)</label><select id="i-disch"></select>
  <div class="row"><div><label>Volume (t)</label><input type="number" id="i-vol" value="900000" step="50000"></div>
  <div><label>Duration (weeks)</label><input type="number" id="i-dur" value="13" min="4" max="48"></div></div>
  <div class="row"><div><label>First laycan in (weeks)</label><input type="number" id="i-lead" value="3" min="2" max="12"></div>
  <div><label>Max stem / parcel (t)</label><input type="number" id="i-stem" value="0" step="5000"></div></div>
  <label>Risk appetite: CVaR weight &lambda; = <span id="v-lam"></span></label><input type="range" id="i-lam" min="0" max="3" step="0.1" value="0.5">
  <h3 style="margin-top:14px">What-if levers</h3>
  <label>Freight shock on forecast path: <span id="v-shock"></span></label><input type="range" id="i-shock" min="-30" max="50" step="5" value="0">
  <label>Bunker price change: <span id="v-bunk"></span></label><input type="range" id="i-bunk" min="-30" max="40" step="5" value="0">
  <label>Extra port congestion (days): <span id="v-cong"></span></label><input type="range" id="i-cong" min="0" max="8" step="0.5" value="0">
  <label><input type="checkbox" id="i-mon"> SW-monsoon draft/wait restrictions</label>
  <label><input type="checkbox" id="i-suez"> Avoid Suez / Red Sea (re-route via Cape)</label>
  <label>Broker quote to X-ray ($/t, optional)</label><input type="number" id="i-quote" value="0" step="0.25">
 </div>
 <div class="grid">
  <div class="card"><h3>Recommendation</h3><div id="rec" class="rec"></div><div class="bar" id="mixbar"></div><div class="kpis" id="kpis"></div></div>
  <div class="grid g2">
   <div class="card"><h3>Vessel-type options (feasibility + landed cost P10-P50-P90, $/t)</h3><div class="tw" id="classtab"></div><div class="small mut" id="classnote"></div></div>
   <div class="card"><h3>Entry timing: COA quote if you wait <i>w</i> weeks</h3><div id="p-timing" class="plot"></div></div>
  </div>
  <div class="grid g2">
   <div class="card"><h3>Cost distribution: recommended mix vs all-spot vs daily-spot habit</h3><div id="p-dist" class="plot"></div></div>
   <div class="card"><h3>Broker Quote X-ray &amp; charter ladder</h3><div id="xray"></div><div id="ladder" style="margin-top:10px"></div></div>
  </div>
 </div></div></section>

<section class="tab" id="t-fc"><div class="grid g2">
 <div class="card"><h3>TCE forecast fan (P10-P50-P90, $/day) <select id="i-fcls" style="width:auto;display:inline"></select></h3><div id="p-fan" class="plot" style="height:360px"></div><div class="small mut" id="wts"></div></div>
 <div class="card"><h3>Out-of-sample accuracy (test period 2021-2026, walk-forward)</h3><div class="tw" id="acc"></div>
 <p class="small mut">Skill = MAE reduction vs random walk on log returns. DM = Diebold-Mariano (Newey-West) vs random walk; p&lt;0.05 = significant. Coverage target 80%.</p></div>
 <div class="card"><h3>Explainability: what drives the 4- and 12-week view</h3><div class="tw" id="expl"></div></div>
 <div class="card"><h3>Placebo check: accuracy in an unpredictable (martingale) world</h3><div class="tw" id="accp"></div><p class="small mut">If the model claimed skill here it would be overfitting. Near-zero skill = honest.</p></div>
</div></section>

<section class="tab" id="t-feas"><div class="grid g2">
 <div class="card"><h3>Port-vessel feasibility for selected lane</h3><div class="tw" id="feastab"></div></div>
 <div class="card"><h3>Max cargo by class at every East-Coast port (from selected origin)</h3><div class="tw" id="feasall"></div></div>
 <div class="card"><h3>Port constraint register (ASSUMPTIONS - verify before use)</h3><div class="tw" id="portreg"></div></div>
 <div class="card"><h3>Draft-staged two-port discharge (example)</h3><div id="twoport"></div></div>
</div></section>

<section class="tab" id="t-risk"><div class="grid g2">
 <div class="card"><h3>Early warnings</h3><div id="alerts"></div></div>
 <div class="card"><h3>Event intelligence (news &rarr; typed event &rarr; impacted lanes)</h3><div id="events"></div></div>
 <div class="card"><h3>Port congestion outlook (expected waiting days, 52 weeks)</h3><div id="p-cong" class="plot"></div></div>
 <div class="card"><h3>Spike / crash probabilities (4-week horizon)</h3><div class="tw" id="spike"></div></div>
</div></section>

<section class="tab" id="t-idle"><div class="grid g2">
 <div class="card"><h3>Idle &amp; ballast-leg options for period tonnage (pilot lane)</h3><div class="tw" id="idle"></div></div>
 <div class="card"><h3>Turnaround &amp; utilisation of a period-chartered ship (selected lane)</h3><div id="util"></div></div>
</div></section>

<section class="tab" id="t-bt"><div class="grid">
 <div class="card"><h3>Rolling backtest - Hay Point &rarr; Paradip, 900 kt/quarter, test period 2021 &ndash; 2026H1 (SYNTHETIC world)</h3><div class="kpis" id="btk"></div></div>
 <div class="grid g2">
  <div class="card"><h3>Savings waterfall vs daily-spot baseline ($/t)</h3><div id="p-wf" class="plot"></div></div>
  <div class="card"><h3>Realised cost per quarter ($/t)</h3><div id="p-blocks" class="plot"></div></div>
 </div>
 <div class="card"><h3>Strategy scorecard</h3><div class="tw" id="bttab"></div>
 <p class="small mut">B0 daily spot, Panamax habit, fixed ~3 weeks before laycan &middot; B1 + optimal vessel &middot; B2 + forecast-timed fixing &middot; B3 70% COA without a model (control) &middot; FS FreightSaarthi (CVaR ladder) &middot; ORC perfect foresight. CI = 90% block-bootstrap.</p></div>
 <div class="grid g2">
  <div class="card"><h3>Ablations &amp; honesty checks</h3><div class="tw" id="abl"></div></div>
  <div class="card"><h3>Decision-focused calibration (validation 2018H2-2020)</h3><div class="tw" id="tune"></div></div>
 </div>
</div></section>

<section class="tab" id="t-net"><div class="card"><h3>Network view: best class &amp; landed freight ($/t) for every origin &times; East-Coast port (8-week median forecast)</h3><div class="tw" id="net"></div><p class="small mut">Same forecaster + physics translator; no route-specific history needed. Freight-adjusted FOB break-even: an origin competes only if its FOB discount exceeds its freight premium over the cheapest origin.</p></div></section>

<section class="tab" id="t-ass"><div class="grid g2">
 <div class="card"><h3>Data provenance</h3><div id="prov"></div></div>
 <div class="card"><h3>Commercial assumptions</h3><div class="tw" id="comm"></div></div>
</div></section>
</main>
<script>
const D = __DATA__;
const CL = ["Handysize","Supramax","Panamax","Capesize"];
const COLORS = {Handysize:"#8e6cd8",Supramax:"#0e9f6e",Panamax:"#0b6bcb",Capesize:"#d9480f"};
const $ = id => document.getElementById(id);
const css = v => getComputedStyle(document.documentElement).getPropertyValue(v).trim();
const fmt = (x,d=2) => (x==null||isNaN(x))?"-":Number(x).toLocaleString("en-IN",{minimumFractionDigits:d,maximumFractionDigits:d});
const pct = x => (x*100).toFixed(0)+"%";
const q = (arr,p) => {const a=[...arr].sort((x,y)=>x-y);const i=(a.length-1)*p;const lo=Math.floor(i);return a[lo]+(a[Math.min(lo+1,a.length-1)]-a[lo])*(i-lo)};
const mean = a => a.reduce((s,x)=>s+x,0)/a.length;
const cvar = (a,al=0.9) => {const t=q(a,al);const t2=a.filter(x=>x>=t);return mean(t2)};
function layout(extra={}){return Object.assign({margin:{l:48,r:12,t:10,b:36},paper_bgcolor:"rgba(0,0,0,0)",plot_bgcolor:"rgba(0,0,0,0)",
  font:{color:css("--ink"),size:12},xaxis:{gridcolor:css("--line")},yaxis:{gridcolor:css("--line")},legend:{orientation:"h",y:-0.18}},extra)}
const CFG={displayModeBar:false,responsive:true};
const PL={react:(id,data,lay,cfg)=>{try{if(window.Plotly)Plotly.react(id,data,lay,cfg);else document.getElementById(id).innerHTML="<p class='mut small'>chart library unavailable</p>"}catch(e){console.error(e)}}};

// ---------------- tabs ----------------
const TABS=[["plan","Plan a charter"],["fc","Market forecast"],["feas","Feasibility & ports"],["risk","Risk & alerts"],["idle","Idle manager"],["bt","Backtest proof"],["net","Network view"],["ass","Assumptions"]];
TABS.forEach(([k,n],i)=>{const b=document.createElement("button");b.textContent=n;b.onclick=()=>show(k);b.id="b-"+k;if(!i)b.className="on";$("nav").appendChild(b)});
function show(k){document.querySelectorAll(".tab").forEach(t=>t.classList.remove("on"));document.querySelectorAll("nav button").forEach(t=>t.classList.remove("on"));
 $("t-"+k).classList.add("on");$("b-"+k).classList.add("on");window.dispatchEvent(new Event("resize"))}
$("lbl").textContent=D.meta.data_label;$("asof").textContent="As of "+D.meta.asof;

// ---------------- physics (mirrors saarthi/physics.py) ----------------
const RATECAP={Handysize:12000,Supramax:18000,Panamax:32000,Capesize:60000};
const WMULT={Handysize:0.75,Supramax:0.85,Panamax:1.0};
function classWait(c,dc,w){const dp=D.discharge[dc];return w*(c==="Capesize"?dp.cape_wait_mult:WMULT[c])}
function ladenDraft(v,cargo){return v.design_draft_m-Math.max(0,v.dwt-v.constants_t-cargo)/(v.tpc*100)}
function check(c,lc,dc,o){
 const v=D.vessels[c],lp=D.load[lc],dp=D.discharge[dc],notes=[];
 for(const [p,tag] of [[lp,"load"],[dp,"discharge"]]){
  if(v.loa_m>p.max_loa_m)return{cls:c,feasible:false,cargo:0,binding:`LOA ${v.loa_m} m > ${p.max_loa_m} m (${tag})`,notes};
  if(v.beam_m>p.max_beam_m)return{cls:c,feasible:false,cargo:0,binding:`beam ${v.beam_m} m > ${p.max_beam_m} m (${tag})`,notes};}
 const r=D.routes[lc];let nm=r.nm,routing=[...r.routing];
 if(o.suez&&routing.includes("SUEZ")&&r.alt){nm=r.alt.nm;routing=r.alt.routing;notes.push("re-routed via Cape of Good Hope")}
 nm+=dp.offset_nm;
 const dr={"load port":lp.max_draft_m,"discharge port":dp.max_draft_m+(o.monsoon?dp.monsoon_draft_delta:0)};
 routing.forEach(k=>{if(D.chokepoints[k])dr[D.chokepoints[k].name]=D.chokepoints[k].max_draft_m});
 const bp=Object.keys(dr).reduce((a,b)=>dr[a]<=dr[b]?a:b);const allowed=dr[bp];
 let cargo=v.dwt-v.tpc*100*Math.max(0,v.design_draft_m-allowed)-v.constants_t;
 let binding=allowed<v.design_draft_m?`draft ${allowed.toFixed(1)} m (${bp})`:"full deadweight";
 if(dp.max_dwt&&v.dwt>dp.max_dwt*1.02)notes.push(`berth DWT limit ${dp.max_dwt.toLocaleString()} t`);
 if(dp.stockyard_t&&cargo>dp.stockyard_t*0.5){cargo=dp.stockyard_t*0.5;binding="stockyard space"}
 if(o.stem>0&&cargo>o.stem){cargo=o.stem;binding="max stem size"}
 if(r.small_ship_nm&&ladenDraft(v,cargo)<=D.chokepoints.TORRES.max_draft_m){nm=r.small_ship_nm+dp.offset_nm;notes.push("Torres Strait routing")}
 if(dp.kind==="anchorage")notes.push(`lighterage +$${dp.lighterage_usd_t}/t`);
 const feasible=cargo>=0.45*(v.dwt-v.constants_t);
 if(!feasible)binding=`uneconomic part-cargo (${Math.round(cargo).toLocaleString()} t): ${binding}`;
 return{cls:c,feasible,cargo:Math.max(cargo,0),binding,notes,nm,draft:ladenDraft(v,Math.max(cargo,0))}}
function coef(c,f,lc,dc){
 const v=D.vessels[c],lp=D.load[lc],dp=D.discharge[dc],Q=f.cargo;
 const la=f.nm/(v.speed_laden_kn*24),ba=0.8*f.nm/(v.speed_ballast_kn*24);
 const rl=Math.min(lp.rate_tpd,RATECAP[c]),rd=Math.min(dp.rate_tpd,RATECAP[c]);
 const po=Q/rl+Q/rd+lp.base_wait_days+classWait(c,dc,dp.base_wait_days)+1;
 const fuel=la*v.fuel_laden_tpd+ba*v.fuel_ballast_tpd+po*v.fuel_port_tpd;
 const k=(1+D.commercial.commission)/Q;
 const inv=D.commercial.cargo_value_usd_t*D.commercial.wacc/365*(Q/D.commercial.plant_draw_tpd/2);
 return{A:(la+ba+po)*k,B:fuel*k,C:2*v.port_cost_usd*k,q:Q,laden_w:Math.ceil(la/7),days:la+ba+po,la,ba,po,inv,extra:dp.lighterage_usd_t||0,disch_days:Q/rd}}
function dem(c,dc,wait,tce,Q){const dp=D.discharge[dc];const normal=classWait(c,dc,dp.base_wait_days)+D.commercial.laytime_allow_days;
 return Math.max(0,classWait(c,dc,wait)-normal)*tce*D.commercial.dem_factor/Q}
function season(w){return D.market.season[((w-1)%52+52)%52]}
function fwdAvg(c,y,woy,hs){const m=D.market,mu=m.mu[c],b=m.beta[c];let s=0;
 hs.forEach(h=>{s+=Math.exp(mu+Math.pow(m.phi,h)*(y-mu-b*season(woy))+b*season(woy+h))});return s/hs.length}

// ---------------- the planner ----------------
const VS=(()=>{let s=7;const r=()=>{s=(s*16807)%2147483647;return s/2147483647};const out=[];for(let i=0;i<150;i++){const u=r(),u2=r();out.push(Math.exp(0.08*Math.sqrt(-2*Math.log(u))*Math.cos(2*Math.PI*u2)))}return out})();
function inputs(){return{lc:$("i-load").value,dc:$("i-disch").value,V:+$("i-vol").value,dur:Math.max(4,Math.min(48,+$("i-dur").value)),
 lead:Math.max(2,Math.min(12,+$("i-lead").value)),stem:+$("i-stem").value,lam:+$("i-lam").value,shock:+$("i-shock").value/100,
 bunk:+$("i-bunk").value/100,cong:+$("i-cong").value,monsoon:$("i-mon").checked,suez:$("i-suez").checked,quote:+$("i-quote").value}}
function evalClass(c,I){
 const f=check(c,I.lc,I.dc,{monsoon:I.monsoon,suez:I.suez,stem:I.stem});if(!f.feasible)return{f};
 const k=coef(c,f,I.lc,I.dc),P=D.paths[c],S=P.length,n=Math.max(1,Math.ceil(I.V/k.q));
 const bunker=D.market.bunker_now*(1+I.bunk);
 const lays=[...Array(n).keys()].map(i=>I.lead+Math.round(i*I.dur/n));
 const fixw=lays.map(L=>Math.max(1,L-3)),arrw=lays.map(L=>Math.min(52,L+k.laden_w));
 const cong=D.congestion[I.dc];
 const waits=arrw.map(h=>cong[h-1].mean+I.cong+(I.monsoon?D.discharge[I.dc].monsoon_wait_add*0.5:0));
 const spot=[],demv=[];
 for(let s=0;s<S;s++){let a=0,d=0;fixw.forEach((w,i)=>{const t=P[s][w-1]*(1+I.shock);a+=k.A*t+k.B*bunker+k.C;d+=dem(c,I.dc,waits[i],t,k.q)});
  spot.push(a/n);demv.push(d/n)}
 const land=spot.map((x,i)=>x+demv[i]+k.inv+k.extra);
 return{f,k,n,lays,fixw,spot,demv,land,bunker,waits}}
function mixSearch(R,c,I){
 const k=R.k,m=D.market,y=Math.log(m.tce_now[c]),woy=m.woy_now;
 const hsF=R.fixw,P=k.A*fwdAvg(c,y,woy,hsF)*1+k.B*D.market.bunker_now+k.C;const Pcoa=P*(1+D.commercial.coa_premium);
 const hsT=[...Array(I.dur).keys()].map(i=>I.lead+i),H=fwdAvg(c,y,woy,hsT)*(1+D.commercial.tc_premium);
 const tcu=k.A*H+k.B*R.bunker+k.C;const tol=D.commercial.coa_tolerance,dfr=D.commercial.deadfreight_frac;
 const extra=R.demv.map(d=>d+k.inv+k.extra);
 const cost=(a,b)=>R.spot.map((sp,i)=>{const v=VS[i%VS.length];const bt=Math.min(b,v);let rem=v-bt;
   const want=sp>Pcoa?a*(1+tol):a*(1-tol);const lift=Math.min(rem,want);const dead=Math.max(0,a*(1-tol)-lift);
   return (bt*tcu+lift*Pcoa+dead*Pcoa*dfr+(rem-lift)*sp)/v+extra[i]});
 let best=null;
 for(let a=0;a<=0.851;a+=0.05)for(let b=0;b<=0.401;b+=0.05){if(a+b>0.851)continue;const cs=cost(a,b);const obj=mean(cs)+I.lam*cvar(cs);
  if(!best||obj<best.obj)best={a,b,obj,cs,mean:mean(cs),cv:cvar(cs)}}
 const all=cost(0,0);
 return{best,all,Pcoa,H,tcu}}
function timing(R,c,I,Pcoa){const k=R.k,m=D.market,P=D.paths[c],out=[];
 for(let w=1;w<=Math.min(12,I.lead+4);w++){const qs=P.map(p=>{const y=Math.log(p[w-1]*(1+I.shock));const hs=R.fixw.map(h=>h-w).map(h=>Math.max(h,0));
   return (k.A*fwdAvg(c,y,m.woy_now+w,hs)+k.B*R.bunker+k.C)*(1+D.commercial.coa_premium)});
  out.push({w,p10:q(qs,.1),p50:q(qs,.5),p90:q(qs,.9),pc:qs.filter(x=>x<Pcoa).length/qs.length})}
 return out}
function run(){
 const I=inputs();$("v-lam").textContent=I.lam.toFixed(1);$("v-shock").textContent=(I.shock>=0?"+":"")+(I.shock*100)+"%";
 $("v-bunk").textContent=(I.bunk>=0?"+":"")+(I.bunk*100)+"%";$("v-cong").textContent=I.cong;
 const R={};CL.forEach(c=>R[c]=evalClass(c,I));
 const feas=CL.filter(c=>R[c].land);
 if(!feas.length){$("rec").innerHTML="<span class='no'>No vessel class is feasible for this lane under current constraints.</span>";return}
 const best=feas.reduce((a,b)=>q(R[a].land,.5)<=q(R[b].land,.5)?a:b);
 const habit=R.Panamax.land?"Panamax":feas.filter(c=>c!=="Capesize").slice(-1)[0]||best;
 const M=mixSearch(R[best],best,I),tm=timing(R[best],best,I,M.Pcoa);
 const b=R[best],mx=M.best,spotSh=Math.max(0,1-mx.a-mx.b);
 const habitCost=R[habit].land.map((x,i)=>x);const saveV=q(habitCost,.5)-mx.mean;
 const waitBest=tm.reduce((a,t)=>t.p50<a.p50?t:a,{p50:M.Pcoa,w:0,pc:0});
 const act=mx.a+mx.b<0.05?"Stay spot for now; re-check weekly":(waitBest.w>0&&waitBest.pc>0.6&&(M.Pcoa-waitBest.p50)/M.Pcoa>0.02?`Lock part now, defer rest ~${waitBest.w} wk`:"Lock the recommended cover now (ladder)");
 const turn=b.k.days;
 // alternate-port hint: cheapest landed $/t from the same origin at other East-Coast ports
 let alt=null;Object.keys(D.discharge).filter(p=>p!==I.dc).forEach(p=>{CL.forEach(c=>{const r=evalClass(c,Object.assign({},I,{dc:p}));
  if(r.land){const m=q(r.land,.5);if(!alt||m<alt.m)alt={p,c,m}}})});
 const altTxt=alt&&alt.m<q(b.land,.5)*0.9?`<br><span class='small'>Cheaper alternative: <b>${D.discharge[alt.p].name}</b> by ${alt.c} at ~$${fmt(alt.m)}/t landed (vs $${fmt(q(b.land,.5))}) &mdash; worth it if the inland/rail differential is below $${fmt(q(b.land,.5)-alt.m)}/t.</span>`:"";
 $("rec").innerHTML=`Charter <b>${b.n} &times; ${best}</b> voyages of <b>${fmt(b.k.q,0)} t</b> (${b.f.binding}) from <b>${D.load[I.lc].name}</b> to <b>${D.discharge[I.dc].name}</b>.<br>
 Contract mix: <b>${pct(mx.a)} COA</b> (fixed ~$${fmt(M.Pcoa)}/t), <b>${pct(mx.b)} period TC</b> (hire ~$${fmt(M.H,0)}/day), <b>${pct(spotSh)} spot</b> with forecast-timed fixing.
 <br>Action: <b>${act}</b>. Round voyage ${fmt(turn,1)} d; laycan spacing &ge; ${fmt(b.k.disch_days+1.5,1)} d to avoid self-queuing.`+altTxt+
 (b.f.notes.length?`<br><span class='small mut'>Notes: ${b.f.notes.join("; ")}</span>`:"");
 const tot=mx.mean*I.V/1e6;
 $("mixbar").innerHTML=[[mx.a,"COA",css("--acc")],[mx.b,"TC",css("--acc2")],[spotSh,"Spot",css("--warn")]].filter(x=>x[0]>0.001).map(([v,l,col])=>`<div style="width:${v*100}%;background:${col}">${l} ${pct(v)}</div>`).join("");
 const thm=mx.mean*D.commercial.coal_per_thm;
 $("kpis").innerHTML=[[`$${fmt(mx.mean)}`,"expected landed freight $/t"],[`$${fmt(q(mx.cs,.1))} - ${fmt(q(mx.cs,.9))}`,"P10-P90 $/t"],
  [`$${fmt(mx.cv)}`,"CVaR90 $/t (bad-case)"],[`$${fmt(tot,1)} M`,"programme freight"],
  [`${saveV>=0?"":"-"}$${fmt(Math.abs(saveV)*I.V/1e6,1)} M`,`vs daily-spot ${habit} habit (${fmt(saveV/q(habitCost,.5)*100,1)}%)`],
  [`$${fmt(q(M.all,.9)-q(mx.cs,.9))}/t`,"P90 risk cut vs all-spot"],[`$${fmt(thm)}`,"freight per t hot metal"]].map(([a,b])=>`<div class="kpi"><b>${a}</b><span>${b}</span></div>`).join("");
 // class table
 $("classtab").innerHTML="<table><tr><th>Class</th><th>Feasible</th><th>Parcel t</th><th>Binding constraint</th><th>Voyages</th><th>RV days</th><th>P10</th><th>P50</th><th>P90</th></tr>"+
  CL.map(c=>{const r=R[c];if(!r.land)return`<tr><td>${c}</td><td class="no">no</td><td>-</td><td style="text-align:left">${r.f.binding}</td><td colspan=5></td></tr>`;
   return`<tr${c===best?" style='font-weight:700'":""}><td>${c}${c===best?" &#9733;":""}</td><td class="ok">yes</td><td>${fmt(r.k.q,0)}</td><td style="text-align:left">${r.f.binding}</td><td>${r.n}</td><td>${fmt(r.k.days,1)}</td><td>${fmt(q(r.land,.1))}</td><td>${fmt(q(r.land,.5))}</td><td>${fmt(q(r.land,.9))}</td></tr>`}).join("")+"</table>";
 $("classnote").textContent="Landed = freight + expected demurrage (congestion forecast) + stockyard carrying cost + lighterage. ★ = recommended.";
 // timing chart
 PL.react("p-timing",[{x:tm.map(t=>t.w),y:tm.map(t=>t.p90),line:{width:0},showlegend:false,hoverinfo:"skip"},
  {x:tm.map(t=>t.w),y:tm.map(t=>t.p10),fill:"tonexty",fillcolor:css("--shade"),line:{width:0},name:"P10-P90"},
  {x:tm.map(t=>t.w),y:tm.map(t=>t.p50),name:"median quote",line:{color:css("--acc")}},
  {x:[0,tm.length],y:[M.Pcoa,M.Pcoa],name:"quote today",line:{dash:"dot",color:css("--bad")}},
  {x:tm.map(t=>t.w),y:tm.map(t=>t.pc*100),name:"P(cheaper than today) %",yaxis:"y2",line:{color:css("--acc2"),dash:"dash"}}],
  layout({xaxis:{title:"wait (weeks)",gridcolor:css("--line")},yaxis:{title:"$/t",gridcolor:css("--line")},yaxis2:{overlaying:"y",side:"right",range:[0,100],showgrid:false,title:"%"}}),CFG);
 // distribution
 PL.react("p-dist",[{x:mx.cs,type:"histogram",name:"Recommended mix",opacity:.65,marker:{color:css("--acc")}},
  {x:M.all,type:"histogram",name:`All-spot ${best}`,opacity:.5,marker:{color:css("--warn")}},
  {x:habitCost,type:"histogram",name:`Daily-spot ${habit}`,opacity:.45,marker:{color:css("--bad")}}],layout({barmode:"overlay",xaxis:{title:"$/t",gridcolor:css("--line")}}),CFG);
 // X-ray & ladder
 const fair=R[best].spot.map((x,i)=>x);const qv=I.quote;
 let xr=`Fair-value band for a ${best} spot fixture on this lane: <b>$${fmt(q(fair,.1))} - $${fmt(q(fair,.5))} - $${fmt(q(fair,.9))}/t</b> (P10-P50-P90).`;
 if(qv>0){const pr=fair.filter(x=>x<=qv).length/fair.length;xr+=`<br>Quote $${fmt(qv)}/t sits at the <b>${(pr*100).toFixed(0)}th percentile</b> - `+(pr>0.7?"<span class='no'>expensive: counter at ~$"+fmt(q(fair,.5))+"</span>":pr<0.3?"<span class='ok'>attractive: consider fixing</span>":"fair range")}
 $("xray").innerHTML=xr;
 const lock=mx.a+mx.b;let tr=[],left=lock,w=0;while(left>0.001){const s=Math.min(0.35,left);tr.push([w,s]);left-=s;w+=2}
 $("ladder").innerHTML="<b>Charter ladder</b> (&le;35% per tranche, re-optimised weekly):<br>"+(tr.length?tr.map(([w,s])=>`<span class='pill'>week +${w}: lock ${pct(s)}</span>`).join(" "):"<span class='pill'>no lock-in this week</span>")+
  `<br><span class='small mut'>Remaining ${pct(spotSh)} fixed spot inside [L-5, L-1] using the optimal-stopping rule.</span>`;
 util(R[best],best,I,M);
}
function util(r,c,I,M){const days=I.dur*7,rv=r.k.days,nv=Math.floor(days/rv),idle=days-nv*rv;
 $("util").innerHTML=`<table><tr><td>Round voyage (laden+ballast+port)</td><td>${fmt(rv,1)} d</td></tr><tr><td>&nbsp;laden / ballast / port</td><td>${fmt(r.k.la,1)} / ${fmt(r.k.ba,1)} / ${fmt(r.k.po,1)} d</td></tr>
 <tr><td>Voyages per ship in ${I.dur} weeks</td><td>${nv}</td></tr><tr><td>Unutilised days per ship</td><td>${fmt(idle,1)} d</td></tr>
 <tr><td>Ships needed on TC for ${pct(M.best.b)} share</td><td>${fmt(M.best.b*I.V/(r.k.q*Math.max(nv,1)),1)}</td></tr>
 <tr><td>Ballast share of voyage</td><td>${pct(r.k.ba/rv)}</td></tr></table><p class="small mut">Unutilised days feed the idle manager: relet, triangulate or slow-steam (JIT arrival).</p>`}

// ---------------- static panels ----------------
function init(){
 Object.entries(D.load).forEach(([k,v])=>$("i-load").add(new Option(`${v.name}`,k)));
 Object.entries(D.discharge).forEach(([k,v])=>$("i-disch").add(new Option(v.name,k)));
 $("i-load").value="HAY_POINT";$("i-disch").value="PARADIP";
 document.querySelectorAll("#t-plan input,#t-plan select").forEach(e=>e.addEventListener("input",()=>{run();feasPanels()}));
 CL.forEach(c=>$("i-fcls").add(new Option(c,c)));$("i-fcls").value="Capesize";$("i-fcls").onchange=fan;
 fan();accTables();expl();risk();idle();bt();net();prov();feasPanels();run()}
function fan(){const c=$("i-fcls").value,F=D.fan[c],last=F.hist_dates[F.hist_dates.length-1];
 const fut=[...Array(F.p50.length).keys()].map(i=>{const d=new Date(last);d.setDate(d.getDate()+7*(i+1));return d.toISOString().slice(0,10)});
 PL.react("p-fan",[{x:F.hist_dates,y:F.hist,name:"actual",line:{color:css("--ink")}},
  {x:fut,y:F.p90,line:{width:0},showlegend:false,hoverinfo:"skip"},{x:fut,y:F.p10,fill:"tonexty",fillcolor:css("--shade"),line:{width:0},name:"P10-P90"},
  {x:fut,y:F.p50,name:"median",line:{color:COLORS[c]}}],layout({yaxis:{title:"$/day",gridcolor:css("--line")},shapes:[{type:"rect",xref:"x",yref:"paper",x0:fut[26],x1:fut[fut.length-1],y0:0,y1:1,fillcolor:css("--line"),opacity:.35,line:{width:0}}]}),CFG);
 $("wts").innerHTML=`Current ensemble weights (inverse trailing pinball loss): GBM ${pct(F.weights.gbm)}, structural ${pct(F.weights.struct)}, random walk ${pct(F.weights.rw)}. Shaded region beyond 26 weeks = extrapolated, low confidence.`}
function accTable(rows){return "<table><tr><th>Class</th><th>h (wk)</th><th>MAPE %</th><th>RW MAPE %</th><th>Skill %</th><th>Cover80 %</th><th>Dir. acc %</th><th>DM p</th></tr>"+
 rows.filter(r=>[1,4,12,26].includes(r.h)).map(r=>`<tr><td>${r.class}</td><td>${r.h}</td><td>${fmt(r.MAPE_pct,1)}</td><td>${fmt(r.MAPE_rw_pct,1)}</td><td class="${r.skill_vs_rw_pct>0?"ok":"no"}">${fmt(r.skill_vs_rw_pct,1)}</td><td>${fmt(r.coverage80_pct,0)}</td><td>${fmt(r.directional_acc_pct,0)}</td><td>${fmt(r.DM_p,3)}</td></tr>`).join("")+"</table>"}
function accTables(){$("acc").innerHTML=accTable(D.forecast_report);$("accp").innerHTML=accTable(D.forecast_report_placebo)}
function expl(){let h="";["h4","h12"].forEach(k=>{const e=D.explain[k];h+=`<b>${k.slice(1)}-week horizon</b><table><tr><th>GBM feature</th><th>gain %</th><th>Structural driver</th><th>coef</th></tr>`;
 for(let i=0;i<8;i++){const g=e.gbm_gain_pct[i]||["",""],s=e.struct_coef[i+1]||["",""];h+=`<tr><td>${g[0]}</td><td>${g[1]}</td><td style="text-align:left">${s[0]}</td><td>${s[1]}</td></tr>`}h+="</table><br>"});
 $("expl").innerHTML=h+"<p class='small mut'>dev_exp = deviation from long-run mean (mean reversion), bal_z = ballaster count z-score (supply), coal_r4 = coal price momentum (demand), seas_tgt = seasonality of target week.</p>"}
function risk(){$("alerts").innerHTML=D.alerts.map(a=>`<div class="alert ${a.level==="high"?"hi":"me"}"><span class="pill">${a.kind}</span> ${a.msg}</div>`).join("")||"No active alerts.";
 $("events").innerHTML=D.events.map(e=>`<div class="alert ${e.severity>=3?"hi":"me"}"><span class="pill">${e.date}</span> <span class="pill">${e.event_type}</span> sev ${e.severity}, ~${e.expected_duration_days} d, freight ${e.freight_direction}<br><span class="small">${e.summary}</span><br><span class="small mut">Impacted: ${(e.impacted_lanes||[]).slice(0,6).join(", ")}${(e.impacted_lanes||[]).length>6?" ...":""} &middot; extractor: ${e.extractor}</span></div>`).join("");
 PL.react("p-cong",Object.entries(D.congestion).map(([p,o])=>({x:o.map(r=>r.h),y:o.map(r=>r.mean),name:p})),layout({xaxis:{title:"weeks ahead",gridcolor:css("--line")},yaxis:{title:"days",gridcolor:css("--line")}}),CFG);
 $("spike").innerHTML="<table><tr><th>Class</th><th>now $/d</th><th>P(+20%)</th><th>P(-20%)</th><th>4w median</th></tr>"+CL.map(c=>{const P=D.paths[c].map(p=>p[3]),n=D.market.tce_now[c];
  return`<tr><td>${c}</td><td>${fmt(n,0)}</td><td>${pct(P.filter(x=>x>1.2*n).length/P.length)}</td><td>${pct(P.filter(x=>x<0.8*n).length/P.length)}</td><td>${fmt(q(P,.5),0)}</td></tr>`}).join("")+"</table>"}
function idle(){const r=D.recommendation;$("idle").innerHTML=`<p class="small mut">Class ${r.class}, TC hire ~$${fmt(r.tc_hire,0)}/day, 6 idle days in rotation.</p><table><tr><th>Option</th><th>extra days</th><th>net value $</th></tr>`+
 r.idle_options.map(o=>`<tr><td style="text-align:left;white-space:normal">${o.option}<br><span class="small mut">${o.detail}</span></td><td>${o.extra_days}</td><td class="${o.net_usd>0?"ok":"no"}">${fmt(o.net_usd,0)}</td></tr>`).join("")+"</table>"+
 `<p>Minimum laycan spacing at ${r.class==="Capesize"?"Paradip":"port"}: <b>${r.laycan_spacing_days} days</b> (discharge time + buffer) to avoid SAIL ships queuing behind each other.</p>`}
function bt(){const S=D.backtest.summary,keys=["B0","B1","B2","B3","FS","ORC"],N={B0:"Daily spot (Panamax habit)",B1:"+ optimal vessel",B2:"+ timed spot",B3:"70% COA, no model",FS:"FreightSaarthi",ORC:"Oracle"};
 const fs=S.FS,b1=S.B1;
 $("btk").innerHTML=[[`${fmt(fs.saving_vs_base_pct,1)}%`,`saving vs daily spot (CI ${fmt(fs.saving_ci90_pct[0],1)}-${fmt(fs.saving_ci90_pct[1],1)}%)`],
  [`$${fmt(fs.saving_musd,1)} M`,"saved over test period"],[`${fmt(fs.oracle_capture_pct,0)}%`,"of perfect-foresight savings captured"],
  [`${S.B0.spot_fixtures} &rarr; ${fs.spot_fixtures}`,"spot fixtures (objective: move to multi-voyage)"],[`${fmt(fs.contracted_share_pct,0)}%`,"volume under COA/TC"],
  [`$${fmt(b1.cvar90_block_cost)} &rarr; $${fmt(fs.cvar90_block_cost)}`,"CVaR90 quarterly $/t vs spot+opt. vessel"]].map(([a,b])=>`<div class="kpi"><b>${a}</b><span>${b}</span></div>`).join("");
 const steps=[["Daily spot",S.B0.avg_cost_usd_t],["Vessel optim.",S.B1.avg_cost_usd_t-S.B0.avg_cost_usd_t],["Timed spot",S.B2.avg_cost_usd_t-S.B1.avg_cost_usd_t],["Charter ladder",S.FS.avg_cost_usd_t-S.B2.avg_cost_usd_t],["FreightSaarthi",S.FS.avg_cost_usd_t]];
 PL.react("p-wf",[{type:"waterfall",x:steps.map(s=>s[0]),y:steps.map(s=>s[1]),measure:["absolute","relative","relative","relative","total"],text:steps.map(s=>fmt(s[1])),textposition:"outside",
  connector:{line:{color:css("--line")}},decreasing:{marker:{color:css("--acc2")}},increasing:{marker:{color:css("--bad")}},totals:{marker:{color:css("--acc")}}}],layout({yaxis:{title:"$/t",gridcolor:css("--line"),range:[Math.min(S.ORC.avg_cost_usd_t,S.FS.avg_cost_usd_t)*0.85,S.B0.avg_cost_usd_t*1.05]},showlegend:false}),CFG);
 const B=D.backtest.blocks;PL.react("p-blocks",["B0","B1","FS","ORC"].map(k=>({x:B.map(b=>b.block_start),y:B.map(b=>b[k+"_cost_t"]),name:N[k],line:{dash:k==="ORC"?"dot":"solid"}})),layout({yaxis:{title:"$/t",gridcolor:css("--line")}}),CFG);
 $("bttab").innerHTML="<table><tr><th>Strategy</th><th>avg $/t</th><th>saving %</th><th>90% CI</th><th>$M saved</th><th>std</th><th>CVaR90</th><th>worst Q</th><th>win-rate</th><th>oracle capture</th><th>spot fixtures</th><th>contracted</th></tr>"+
  keys.map(k=>{const s=S[k];return`<tr${k==="FS"?" style='font-weight:700'":""}><td>${N[k]}</td><td>${fmt(s.avg_cost_usd_t)}</td><td>${fmt(s.saving_vs_base_pct,1)}</td><td>${fmt(s.saving_ci90_pct[0],1)} / ${fmt(s.saving_ci90_pct[1],1)}</td><td>${fmt(s.saving_musd,1)}</td><td>${fmt(s.std_block_cost)}</td><td>${fmt(s.cvar90_block_cost)}</td><td>${fmt(s.worst_block_cost)}</td><td>${pct(s.win_rate_vs_base)}</td><td>${s.oracle_capture_pct!=null?fmt(s.oracle_capture_pct,0)+"%":"-"}</td><td>${s.spot_fixtures??"-"}</td><td>${s.contracted_share_pct!=null?fmt(s.contracted_share_pct,0)+"%":"-"}</td></tr>`}).join("")+"</table>";
 const R=D.backtest.summary_rw_ablation,P=D.backtest.summary_placebo;
 $("abl").innerHTML=`<table><tr><th>Check</th><th>result</th></tr>
 <tr><td style="text-align:left">FS vs B1 (value beyond vessel choice)</td><td>${fmt((b1.avg_cost_usd_t-fs.avg_cost_usd_t)/b1.avg_cost_usd_t*100,1)}% cheaper, CVaR ${fmt(b1.cvar90_block_cost)}&rarr;${fmt(fs.cvar90_block_cost)}</td></tr>
 <tr><td style="text-align:left">FS with random-walk forecasts (value of forecasting)</td><td>$${fmt(R.FS.avg_cost_usd_t)} vs $${fmt(fs.avg_cost_usd_t)} /t</td></tr>
 <tr><td style="text-align:left">B3: COA without a model</td><td>${fmt(S.B3.saving_vs_base_pct,1)}% saving (CI ${fmt(S.B3.saving_ci90_pct[0],1)} / ${fmt(S.B3.saving_ci90_pct[1],1)})</td></tr>
 <tr><td style="text-align:left">Placebo world: FS vs B1 (should be ~0)</td><td>${fmt((P.B1.avg_cost_usd_t-P.FS.avg_cost_usd_t)/P.B1.avg_cost_usd_t*100,1)}%</td></tr>
 <tr><td style="text-align:left">Placebo world: timed spot B2 vs B1 (should be ~0)</td><td>${fmt((P.B1.avg_cost_usd_t-P.B2.avg_cost_usd_t)/P.B1.avg_cost_usd_t*100,1)}%</td></tr></table>`;
 $("tune").innerHTML="<table><tr><th>&lambda;</th><th>&delta;</th><th>step cap</th><th>avg $/t</th><th>CVaR90</th><th>score</th></tr>"+D.meta.tune_log.map(t=>`<tr${t.score===D.meta.selected_params.score?" style='font-weight:700'":""}><td>${t.lam}</td><td>${t.delta}</td><td>${t.step}</td><td>${fmt(t.avg)}</td><td>${fmt(t.cvar90)}</td><td>${fmt(t.score,3)}</td></tr>`).join("")+"</table><p class='small mut'>Knobs are chosen by realised decision cost (mean + 0.25&middot;CVaR) on validation, never on test.</p>"}
function net(){const G=D.generalisation,ports=Object.keys(D.discharge),loads=Object.keys(D.load);
 let h="<table><tr><th>Origin \\ Port</th>"+ports.map(p=>`<th>${p}</th>`).join("")+"</tr>";
 loads.forEach(l=>{h+=`<tr><td>${D.load[l].name}</td>`;ports.forEach(p=>{const rows=G.filter(g=>g.load===l&&g.disch===p&&g.feasible);
  if(!rows.length){h+="<td class='no'>-</td>";return}const b=rows.reduce((a,x)=>x.landed_usd_t<a.landed_usd_t?x:a);h+=`<td title="${b.binding}">${fmt(b.landed_usd_t)} <span class="pill" style="color:${COLORS[b.cls]}">${b.cls.slice(0,4)}</span></td>`});h+="</tr>"});
 $("net").innerHTML=h+"</table>"}
function prov(){$("prov").innerHTML=`<table>
<tr><td>Class TCE indices (Cape/Pmx/Supra/Handy)</td><td>SYNTHETIC here &rarr; Baltic Exchange (licensed) or broker assessments; public proxy: BDI</td></tr>
<tr><td>Route freight $/t</td><td>DERIVED via voyage physics; calibrated to SAIL's own fixtures (route basis)</td></tr>
<tr><td>Bunker VLSFO</td><td>SYNTHETIC &rarr; Ship &amp; Bunker / port bunker indices</td></tr>
<tr><td>Coal price, China PMI</td><td>SYNTHETIC &rarr; World Bank Pink Sheet (real, free), NBS/Caixin PMI</td></tr>
<tr><td>Ballaster counts</td><td>SYNTHETIC &rarr; AIS (Spire/MarineTraffic licensed; UN Global Platform AIS for govt)</td></tr>
<tr><td>Port waiting / congestion</td><td>SYNTHETIC &rarr; IMF PortWatch (free), Indian port authority vessel-waiting reports, AIS</td></tr>
<tr><td>Port limits (draft/LOA/beam/rates)</td><td>ASSUMPTIONS (config/ports.json, each with 'verify_with' source)</td></tr>
<tr><td>Vessel particulars</td><td>ASSUMPTIONS for a standard eco ship; real: Q88 / Equasis</td></tr>
<tr><td>Weather / cyclones</td><td>IMD RSMC bulletins (real, free) &mdash; demo uses synthetic events</td></tr></table>`;
 $("comm").innerHTML="<table>"+Object.entries(D.commercial).map(([k,v])=>`<tr><td>${k}</td><td>${v}</td></tr>`).join("")+"</table>";
 $("portreg").innerHTML="<table><tr><th>Port</th><th>draft m</th><th>LOA</th><th>beam</th><th>rate t/d</th><th>conf.</th></tr>"+Object.entries(D.discharge).map(([k,p])=>`<tr><td>${p.name}</td><td>${p.max_draft_m}</td><td>${p.max_loa_m}</td><td>${p.max_beam_m}</td><td>${fmt(p.rate_tpd,0)}</td><td>${p.confidence}</td></tr>`).join("")+
 Object.entries(D.load).map(([k,p])=>`<tr><td>${p.name}</td><td>${p.max_draft_m}</td><td>${p.max_loa_m}</td><td>${p.max_beam_m}</td><td>${fmt(p.rate_tpd,0)}</td><td>${p.confidence}</td></tr>`).join("")+"</table>";
 const t=D.recommendation.two_port_example;$("twoport").innerHTML=`${t.class} loads <b>${fmt(t.total_cargo_t,0)} t</b> at Hay Point, discharges <b>${fmt(t.discharge_at_first_t,0)} t</b> at Dhamra (deep), then the balance (&le; ${fmt(t.max_at_second_t,0)} t) at Paradip within its draft. Extra call ~${t.extra_port_call_days} d, ~$${fmt(t.extra_cost_usd,0)}. Useful when a single port cannot take a full Capesize but two SAIL-served ports can share it.`}
function feasPanels(){const I=inputs();const o={monsoon:I.monsoon,suez:I.suez,stem:I.stem};
 $("feastab").innerHTML="<table><tr><th>Class</th><th>ok</th><th>cargo t</th><th>laden draft m</th><th>binding</th><th>notes</th></tr>"+CL.map(c=>{const f=check(c,I.lc,I.dc,o);
  return`<tr><td>${c}</td><td class="${f.feasible?"ok":"no"}">${f.feasible?"yes":"no"}</td><td>${fmt(f.cargo,0)}</td><td>${f.draft?fmt(f.draft,1):"-"}</td><td style="text-align:left">${f.binding}</td><td style="text-align:left" class="small">${f.notes.join("; ")}</td></tr>`}).join("")+"</table>";
 $("feasall").innerHTML="<table><tr><th>Port</th>"+CL.map(c=>`<th>${c}</th>`).join("")+"</tr>"+Object.keys(D.discharge).map(p=>`<tr><td>${D.discharge[p].name}</td>`+CL.map(c=>{const f=check(c,I.lc,p,o);return`<td class="${f.feasible?"":"no"}" title="${f.binding}">${f.feasible?fmt(f.cargo,0):"&times;"}</td>`}).join("")+"</tr>").join("")+"</table>"}
init();
</script></body></html>"""


def build(payload=None):
    if payload is None:
        with open(OUT / "results.json", encoding="utf-8") as f:
            payload = json.load(f)
    from plotly.offline import get_plotlyjs
    html = HTML.replace("__PLOTLY__", get_plotlyjs()).replace("__DATA__", json.dumps(payload, default=lambda o: o.item() if hasattr(o, "item") else str(o)))
    with open(OUT / "dashboard.html", "w", encoding="utf-8") as f:
        f.write(html)
    return OUT / "dashboard.html"


if __name__ == "__main__":
    print(build())
