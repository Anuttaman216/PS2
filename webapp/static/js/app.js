/* FreightSaarthi cockpit - single-page app driven entirely by the FastAPI endpoints */
(() => {
  const $ = s => document.querySelector(s), $$ = s => [...document.querySelectorAll(s)];
  const CL = ["Handysize", "Supramax", "Panamax", "Capesize"];
  const COL = {Capesize: "#38bdf8", Panamax: "#2dd4bf", Supramax: "#fbbf24", Handysize: "#c4b5fd"};
  const fmt = (x, d = 0) => x == null || isNaN(x) ? "-" : Number(x).toLocaleString("en-IN", {minimumFractionDigits: d, maximumFractionDigits: d});
  const pct = (x, d = 0) => x == null ? "-" : (x * 100).toFixed(d) + "%";
  const api = async (p, o) => { const r = await fetch(p, o); if (!r.ok) { let m = r.status; try { m = (await r.json()).detail || m; } catch (e) {} throw new Error(m); } return r.json(); };
  const post = (p, b) => api(p, {method: "POST", headers: {"Content-Type": "application/json"}, body: JSON.stringify(b)});
  const cache = {};
  const get = (p, fresh) => (!fresh && cache[p]) ? Promise.resolve(cache[p]) : api(p).then(d => (cache[p] = d));
  const toast = (m, ms = 3500) => { const d = document.createElement("div"); d.innerHTML = m; $("#toast").appendChild(d); setTimeout(() => d.remove(), ms); };
  const debounce = (f, ms) => { let t; return (...a) => { clearTimeout(t); t = setTimeout(() => f(...a), ms); }; };
  const ICON = {
    home: '<path d="M3 11l9-7 9 7v9a1 1 0 0 1-1 1h-5v-6H9v6H4a1 1 0 0 1-1-1z"/>',
    plan: '<path d="M2 17h20l-3 4H5z"/><path d="M6 17V8h8v9"/><path d="M14 11h4v6"/><path d="M9 8V4"/>',
    fc: '<path d="M3 17l5-6 4 3 7-9"/><path d="M3 21h18"/>',
    feas: '<circle cx="12" cy="5" r="2"/><path d="M12 7v14M5 13a7 7 0 0 0 14 0M5 13H3m18 0h-2"/>',
    risk: '<path d="M12 3l10 18H2z"/><path d="M12 10v5"/><circle cx="12" cy="18" r=".5"/>',
    idle: '<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/>',
    bt: '<path d="M4 20V10M10 20V4M16 20v-7M22 20H2"/>',
    net: '<circle cx="12" cy="12" r="9"/><path d="M3 12h18M12 3a14 14 0 0 1 0 18M12 3a14 14 0 0 0 0 18"/>',
    api: '<path d="M8 6l-6 6 6 6M16 6l6 6-6 6"/>',
    ops: '<rect x="5" y="3" width="14" height="18" rx="2"/><path d="M9 3v3h6V3M8 11h8M8 15h5"/>',
    data: '<ellipse cx="12" cy="5" rx="8" ry="3"/><path d="M4 5v14c0 1.7 3.6 3 8 3s8-1.3 8-3V5M4 12c0 1.7 3.6 3 8 3s8-1.3 8-3"/>',
    cmp: '<path d="M4 20V9M10 20V4M16 20v-8M22 20H2"/><path d="M3 7l6-4 6 5 6-4"/>',
  };
  const ROUTES = [
    ["", "Overview", "home", overview, "Today's position at a glance"], ["plan", "Plan a Charter", "plan", plan, "POST /api/plan"],
    ["compare", "Compare Lanes", "cmp", compareP, "POST /api/compare"],
    ["forecast", "Market Forecast", "fc", forecast, "GET /api/forecast/{cls}"], ["feasibility", "Port Feasibility", "feas", feasibility, "GET /api/feasibility"],
    ["risk", "Risk & Alerts", "risk", risk, "GET /api/risk · POST /api/events/ingest"], ["idle", "Idle Manager", "idle", idleP, "GET /api/idle"],
    ["ops", "Programmes & Ledger", "ops", ops, "/api/programmes · /api/ledger"], ["data", "Data Hub", "data", dataHub, "/api/data/* · /api/pipeline/run"],
    ["backtest", "Backtest Proof", "bt", backtest, "GET /api/backtest"], ["network", "Network View", "net", network, "GET /api/network"],
    ["api", "API Explorer", "api", apiP, "GET /api"],
  ];
  $("#nav").innerHTML = ROUTES.map(([k, n, ic], i) => (i === 1 ? '<div class="sep">Decide</div>' : i === 7 ? '<div class="sep">Operate</div>' : i === 9 ? '<div class="sep">Evidence</div>' : "") +
    `<a href="#/${k}" data-k="${k}"><svg viewBox="0 0 24 24">${ICON[ic]}</svg>${n}</a>`).join("");
  $("#burger").onclick = () => $("#side").classList.toggle("open");

  /* ---------- plot theme ---------- */
  const PL = (id, data, lay = {}, extra = {}) => {
    const el = typeof id === "string" ? document.getElementById(id) : id; if (!el || !window.Plotly) return;
    const base = {margin: {l: 52, r: 16, t: 10, b: 40}, paper_bgcolor: "rgba(0,0,0,0)", plot_bgcolor: "rgba(0,0,0,0)",
      font: {family: "Inter, system-ui, sans-serif", color: "#b7c9df", size: 12}, hoverlabel: {bgcolor: "#0a1d33", bordercolor: "#38bdf8", font: {family: "JetBrains Mono, monospace", color: "#e6f1ff"}},
      xaxis: {gridcolor: "rgba(125,180,255,.08)", zerolinecolor: "rgba(125,180,255,.15)", linecolor: "rgba(125,180,255,.15)"},
      yaxis: {gridcolor: "rgba(125,180,255,.08)", zerolinecolor: "rgba(125,180,255,.15)", linecolor: "rgba(125,180,255,.15)"},
      legend: {orientation: "h", y: -0.2, font: {size: 11}}, colorway: ["#38bdf8", "#2dd4bf", "#fbbf24", "#c4b5fd", "#fb7185", "#34d399", "#f472b6"]};
    const L = {...base, ...lay, xaxis: {...base.xaxis, ...(lay.xaxis || {})}, yaxis: {...base.yaxis, ...(lay.yaxis || {})}};
    Plotly.react(el, data, L, {displayModeBar: false, responsive: true, ...extra});
  };
  // ?shot=1 -> screenshot/print mode: no animations, final values immediately (used for slide/PDF captures)
  const SHOT = /[?&]shot=1/.test(location.search);
  if (SHOT) document.documentElement.classList.add("shot");
  const countUp = (root = document) => SHOT ? null : root.querySelectorAll("[data-num]").forEach(el => {
    const t = +el.dataset.num, d = +(el.dataset.dec || 0), pre = el.dataset.pre || "", suf = el.dataset.suf || "", st = performance.now();
    const f = now => { const k = Math.min(1, (now - st) / 1100), e = 1 - Math.pow(1 - k, 3); el.textContent = pre + fmt(t * e, d) + suf; if (k < 1) requestAnimationFrame(f); };
    requestAnimationFrame(f);
  });
  const N = (v, d = 0, pre = "", suf = "") => `<span data-num="${v}" data-dec="${d}" data-pre="${pre}" data-suf="${suf}">${pre}${fmt(v, d)}${suf}</span>`;
  document.addEventListener("mousemove", e => { const c = e.target.closest && e.target.closest(".card"); if (!c) return; const r = c.getBoundingClientRect(); c.style.setProperty("--mx", e.clientX - r.left + "px"); c.style.setProperty("--my", e.clientY - r.top + "px"); });
  const rangeFill = el => { const p = (el.value - el.min) / (el.max - el.min) * 100; el.style.setProperty("--p", p + "%"); };

  /* ---------- router ---------- */
  let cleanup = [];
  async function route() {
    const k = (location.hash.replace(/^#\/?/, "") || "").split("?")[0];
    const r = ROUTES.find(x => x[0] === k) || ROUTES[0];
    $$("#nav a").forEach(a => a.classList.toggle("on", a.dataset.k === r[0]));
    $("#side").classList.remove("open");
    const v = $("#view"); v.classList.add("leave");
    cleanup.forEach(f => f()); cleanup = [];
    await new Promise(res => setTimeout(res, 170));
    $("#pageTitle").textContent = r[1]; $("#crumb").textContent = r[4];
    v.innerHTML = `<div class="card"><div class="skel" style="height:22px;width:40%"></div><div class="skel" style="height:180px;margin-top:14px"></div></div>`;
    v.classList.remove("leave", "enter"); scrollTo({top: 0});
    try { await r[3](v); } catch (e) { v.innerHTML = `<div class="card"><h3>Could not load this page</h3><p class="no">${e.message}</p><p class="mut">If results are missing, press <b>Re-run pipeline</b> in the top bar.</p></div>`; }
    void v.offsetWidth; v.classList.add("enter"); countUp(v);
    v.querySelectorAll('input[type=range]').forEach(el => { rangeFill(el); el.addEventListener("input", () => rangeFill(el)); });
  }
  addEventListener("hashchange", route);

  /* ---------- top bar: health, tape, pipeline ---------- */
  async function header() {
    try {
      const h = await api("/api/health");
      const upl = (h.data_label || "").startsWith("UPLOADED");
      $("#srcChip").textContent = upl ? "UPLOADED DATA" : "SYNTHETIC DATA"; $("#srcChip").style.color = upl ? "#34d399" : "#fcd34d"; $("#srcChip").title = h.data_label || "";
      $("#asofChip").innerHTML = h.data_loaded ? `<span class="dot"></span>API live · data as of <b class="mono">${h.asof}</b>` : `<span class="dot bad"></span>no results - run pipeline`;
      const t = await api("/api/ticker"); const one = t.map(x => `<span>${x.label}<b>${x.value}</b>${x.change == null ? "" : `<i class="${x.change >= 0 ? "up" : "down"}">${x.change >= 0 ? "▲" : "▼"}${Math.abs(x.change)}${x.note.includes("days") ? "d" : "%"}</i> <small class="mut">${x.note}</small>`}</span>`).join("");
      $("#tape").innerHTML = one + one;
    } catch (e) { $("#asofChip").innerHTML = `<span class="dot bad"></span>API offline`; }
  }
  $("#runBtn").onclick = async () => {
    const src = (await api("/api/data/status")).active_source || "synthetic";
    const r = await post(`/api/pipeline/run?fast=${src === "uploaded"}&source=${src}`, {}); toast(`Pipeline ${r.status}. This takes seconds with the cache, or minutes from scratch.`);
    $("#runBtn").disabled = true; $("#runBtn").textContent = "⟳ running…";
    const poll = setInterval(async () => {
      const s = await api("/api/pipeline/status");
      if (s.status !== "running") { clearInterval(poll); $("#runBtn").disabled = false; $("#runBtn").textContent = "⟳ Re-run pipeline"; Object.keys(cache).forEach(k => delete cache[k]);
        toast(s.status === "done" ? "✓ Pipeline finished, data reloaded" : "✕ Pipeline error: " + s.error, 6000); header(); route(); }
    }, 2500);
  };

  /* ================================================================ pages */
  async function overview(v) {
    const [S, risk, fcAll] = await Promise.all([get("/api/summary"), get("/api/risk"), get("/api/forecast")]);
    const P = await post("/api/plan", {load: "HAY_POINT", disch: "PARADIP", volume: 900000, duration: 13, lead: 3});
    v.innerHTML = `
    <div class="card hero-card"><div class="txt"><span class="pill">PILOT LANE · HAY POINT → PARADIP</span>
      <h2>Next quarter: <span class="grad-text">${P.voyages} × ${P.best_class}</span> of ${fmt(P.parcel_t)} t</h2>
      <p class="mut">${P.action}</p>
      <div class="mixbar" id="ovMix"></div>
      <div class="kpis" style="margin-top:12px"><div class="kpi hl"><b>${N(P.cost.mean, 2, "$")}</b><span>expected landed $/t</span></div><div class="kpi"><b>${N(P.saving_vs_habit_pct, 1, "", "%")}</b><span>vs daily-spot ${P.habit_class}</span></div></div>
      <div class="row" style="margin-top:16px"><a class="btn primary xs" href="#/plan">Plan a charter →</a><a class="btn ghost xs" href="#/backtest">See the proof</a></div></div>
      <canvas id="ovMap"></canvas></div>
    <div class="kpis">
      <div class="kpi hl"><b>${N(S.saving_pct, 1, "", "%")}</b><span>backtest saving vs daily spot</span></div>
      <div class="kpi"><b>${N(S.saving_musd, 1, "$", "M")}</b><span>saved over 22 quarters</span></div>
      <div class="kpi"><b>${S.spot_fixtures_before} → ${N(S.spot_fixtures_after)}</b><span>spot fixtures</span></div>
      <div class="kpi"><b>${N(S.contracted_pct, 0, "", "%")}</b><span>volume under COA/TC</span></div>
      <div class="kpi"><b>$${fmt(S.cvar_before, 2)} → ${N(S.cvar_after, 2, "$")}</b><span>bad-case (CVaR90) $/t</span></div></div>
    <div class="grid g4">${CL.map(c => { const F = fcAll.fan[c], now = F.hist[F.hist.length - 1], m4 = F.p50[3], ch = (m4 / now - 1) * 100;
      return `<a class="card cls-card" href="#/forecast?${c}"><h3><span class="h-l"><i style="background:${COL[c]}"></i>${c}</span><span class="ch ${ch >= 0 ? "up" : "down"}">${ch >= 0 ? "▲" : "▼"} ${Math.abs(ch).toFixed(1)}% 4w</span></h3><div class="big">${N(now, 0, "$", "/d")}</div><svg class="spark" data-c="${c}" viewBox="0 0 300 56" preserveAspectRatio="none"></svg></a>`; }).join("")}</div>
    <div class="grid g2"><div class="card"><h3><span class="h-l"><i></i>Early warnings</span><a class="small" href="#/risk" style="color:var(--cyan)">all →</a></h3>${risk.alerts.slice(0, 4).map(alertHTML).join("") || "<p class='mut'>No active alerts.</p>"}</div>
      <div class="card"><h3><span class="h-l"><i></i>Modules</span></h3><div class="mod-links">${ROUTES.slice(1).map(([k, n, ic]) => `<a href="#/${k}"><svg viewBox="0 0 24 24">${ICON[ic]}</svg>${n}</a>`).join("")}</div></div></div>`;
    mixBar($("#ovMix"), P.mix);
    $$(".spark").forEach(s => spark(s, fcAll.fan[s.dataset.c]));
    const m = new SeaMap($("#ovMap"), {fit: "zoom", zoom: 1.25, focus: [100, 0], anchor: [0.5, 0.5], labels: false, graticule: false, shipsPerLane: 2, parallax: true});
    m.start(); cleanup.push(() => m.destroy());
  }
  function spark(svg, F) {
    const h = F.hist.slice(-39), f = F.p50.slice(0, 13), lo = F.p10.slice(0, 13), hi = F.p90.slice(0, 13), all = [...h, ...lo, ...hi];
    const mn = Math.min(...all), mx = Math.max(...all), n = h.length + f.length, X = i => i / (n - 1) * 300, Y = v => 52 - (v - mn) / (mx - mn) * 48;
    const hp = h.map((v, i) => `${X(i)},${Y(v)}`).join(" "), fp = [h[h.length - 1], ...f].map((v, i) => `${X(h.length - 1 + i)},${Y(v)}`).join(" ");
    const band = [h[h.length - 1], ...hi].map((v, i) => `${X(h.length - 1 + i)},${Y(v)}`).concat([h[h.length - 1], ...lo].map((v, i) => `${X(h.length - 1 + i)},${Y(v)}`).reverse()).join(" ");
    svg.innerHTML = `<polygon points="${band}" fill="rgba(56,189,248,.14)"/><polyline points="${hp}" fill="none" stroke="#b7c9df" stroke-width="1.5"/><polyline points="${fp}" fill="none" stroke="#38bdf8" stroke-width="2" stroke-dasharray="4 3"/>`;
  }
  function mixBar(el, mix) {
    const segs = [[mix.coa, "COA", "linear-gradient(90deg,#0ea5e9,#38bdf8)"], [mix.tc, "TC", "linear-gradient(90deg,#14b8a6,#2dd4bf)"], [mix.spot, "Spot", "linear-gradient(90deg,#f59e0b,#fbbf24)"]];
    el.innerHTML = segs.map(([v, l, g]) => `<div data-w="${v * 100}" style="background:${g}">${v > 0.07 ? l + " " + pct(v) : ""}</div>`).join("");
    requestAnimationFrame(() => setTimeout(() => el.querySelectorAll("div").forEach(d => d.style.width = d.dataset.w + "%"), 60));
  }
  const alertHTML = a => `<div class="alert ${a.level === "high" ? "high" : ""}"><span class="k">${a.kind.replace("_", " ")}</span>${a.msg}</div>`;

  /* ---------- PLAN ---------- */
  const PRESETS = [["Pilot · Hay Point → Paradip", {load: "HAY_POINT", disch: "PARADIP", volume: 900000, duration: 13}], ["US → Haldia (avoid Suez)", {load: "HAMPTON_RDS", disch: "HALDIA", avoid_suez: true, volume: 300000, duration: 13}],
    ["Indonesia → Vizag", {load: "MUARA_BERAU", disch: "VIZAG", volume: 600000, duration: 13}], ["Mozambique → Dhamra", {load: "NACALA", disch: "DHAMRA", volume: 700000, duration: 26}], ["Monsoon stress", {load: "HAY_POINT", disch: "PARADIP", monsoon: true, congestion_add: 3}]];
  let lastPlanReq = null;
  async function plan(v) {
    const M = await get("/api/meta");
    const byC = {}; Object.entries(M.load).forEach(([k, p]) => (byC[p.country] = byC[p.country] || []).push([k, p]));
    const q = lastPlanReq || {load: "HAY_POINT", disch: "PARADIP", volume: 900000, duration: 13, lead: 3, stem: 0, risk_lambda: 0.5, freight_shock: 0, bunker_change: 0, congestion_add: 0, monsoon: false, avoid_suez: false, broker_quote: null};
    v.innerHTML = `<div class="plan-grid"><div class="card form" id="pForm"><h3><span class="h-l"><i></i>Cargo requirement</span></h3>
      <div class="presets">${PRESETS.map((p, i) => `<button data-i="${i}">${p[0]}</button>`).join("")}</div>
      <label>Origin (load port)</label><select id="f-load">${Object.entries(byC).map(([c, ps]) => `<optgroup label="${c}">${ps.map(([k, p]) => `<option value="${k}">${p.name}</option>`).join("")}</optgroup>`).join("")}</select>
      <label>Destination (East Coast port)</label><select id="f-disch">${Object.entries(M.discharge).map(([k, p]) => `<option value="${k}">${p.name}</option>`).join("")}</select>
      <label>Programme volume <span class="v" id="v-vol"></span></label><input type="range" id="f-vol" min="100000" max="3000000" step="50000">
      <div class="two"><div><label>Duration <span class="v" id="v-dur"></span></label><input type="range" id="f-dur" min="4" max="48" step="1"></div><div><label>First laycan <span class="v" id="v-lead"></span></label><input type="range" id="f-lead" min="2" max="12" step="1"></div></div>
      <label>Max parcel / stem (t, 0 = none)</label><input type="number" id="f-stem" step="5000" min="0">
      <label>Risk aversion λ (CVaR weight) <span class="v" id="v-lam"></span></label><input type="range" id="f-lam" min="0" max="3" step="0.1">
      <h3 style="margin-top:18px"><span class="h-l"><i></i>What-if levers</span></h3>
      <label>Freight shock on forecast <span class="v" id="v-shock"></span></label><input type="range" id="f-shock" min="-30" max="50" step="5">
      <label>Bunker price change <span class="v" id="v-bunk"></span></label><input type="range" id="f-bunk" min="-30" max="40" step="5">
      <label>Extra congestion at discharge <span class="v" id="v-cong"></span></label><input type="range" id="f-cong" min="0" max="8" step="0.5">
      <label class="toggle"><input type="checkbox" id="f-mon"><span></span>SW-monsoon draft &amp; wait restrictions</label>
      <label class="toggle"><input type="checkbox" id="f-suez"><span></span>Avoid Suez / Red Sea (via Cape)</label>
      <label>Broker quote to X-ray ($/t)</label><input type="number" id="f-quote" step="0.25" min="0" placeholder="e.g. 15.50">
      </div><div class="grid" id="pOut" style="position:relative"></div></div>`;
    const set = r => { $("#f-load").value = r.load; $("#f-disch").value = r.disch; $("#f-vol").value = r.volume; $("#f-dur").value = r.duration; $("#f-lead").value = r.lead; $("#f-stem").value = r.stem || 0;
      $("#f-lam").value = r.risk_lambda; $("#f-shock").value = r.freight_shock * 100; $("#f-bunk").value = r.bunker_change * 100; $("#f-cong").value = r.congestion_add; $("#f-mon").checked = r.monsoon; $("#f-suez").checked = r.avoid_suez; $("#f-quote").value = r.broker_quote || "";
      $$("#pForm input[type=range]").forEach(rangeFill); };
    const read = () => ({load: $("#f-load").value, disch: $("#f-disch").value, volume: +$("#f-vol").value, duration: +$("#f-dur").value, lead: +$("#f-lead").value, stem: +$("#f-stem").value || 0,
      risk_lambda: +$("#f-lam").value, freight_shock: +$("#f-shock").value / 100, bunker_change: +$("#f-bunk").value / 100, congestion_add: +$("#f-cong").value,
      monsoon: $("#f-mon").checked, avoid_suez: $("#f-suez").checked, broker_quote: +$("#f-quote").value || null});
    const labels = r => { $("#v-vol").textContent = fmt(r.volume) + " t"; $("#v-dur").textContent = r.duration + " wk"; $("#v-lead").textContent = r.lead + " wk"; $("#v-lam").textContent = r.risk_lambda.toFixed(1);
      $("#v-shock").textContent = (r.freight_shock >= 0 ? "+" : "") + Math.round(r.freight_shock * 100) + "%"; $("#v-bunk").textContent = (r.bunker_change >= 0 ? "+" : "") + Math.round(r.bunker_change * 100) + "%"; $("#v-cong").textContent = r.congestion_add + " d"; };
    set(q);
    const run = debounce(async () => { if (!$("#f-load")) return; const r = read(); labels(r); lastPlanReq = r; const out = $("#pOut"); out.classList.add("busy"); try { const res = await post("/api/plan", r); if ($("#pOut")) renderPlan(res, r); } catch (e) { out.innerHTML = `<div class="card"><p class="no">${e.message}</p></div>`; } if (out) out.classList.remove("busy"); }, 250);
    $$("#pForm input, #pForm select").forEach(el => el.addEventListener(el.type === "range" ? "input" : "change", run));
    $$("#pForm .presets button").forEach(b => b.onclick = () => { set({...q, stem: 0, risk_lambda: 0.5, freight_shock: 0, bunker_change: 0, congestion_add: 0, monsoon: false, avoid_suez: false, broker_quote: null, lead: 3, ...PRESETS[+b.dataset.i][1]}); run(); });
    labels(read()); $("#pOut").innerHTML = `<div class="card"><div class="skel" style="height:140px"></div></div>`; run();
  }
  function renderPlan(P, rq) {
    const out = $("#pOut");
    if (!P.ok) { out.innerHTML = `<div class="card"><h3>No feasible vessel</h3><p class="no">${P.message}</p><div class="tw">${P.classes.map(c => `<div>${c.cls}: ${c.binding}</div>`).join("")}</div></div>`; return; }
    const M = cache["/api/meta"];
    out.innerHTML = `<div class="loading-veil"><div class="spinner"></div></div>
     <div class="card"><h3><span class="h-l"><i></i>Recommendation</span><span class="row" style="gap:8px"><span class="pill ok">LP ${P.lp.status}</span><button class="btn primary xs" id="saveLed">Save to ledger</button></span></h3>
      <div class="rec">Charter <b>${P.voyages} × ${P.best_class}</b> voyages of <b>${fmt(P.parcel_t)} t</b> from <b>${M.load[rq.load].name}</b> to <b>${M.discharge[rq.disch].name}</b>.
      COA fixed at <b>$${fmt(P.coa_quote, 2)}/t</b>, period TC hire ≈ <b>$${fmt(P.tc_hire)}/day</b>.<br><span class="act">${P.action}</span></div>
      <div class="mixbar" id="pMix"></div>
      ${P.alternate_port ? `<div class="callout" style="margin-top:10px">⚓ Cheaper alternative: <b>${P.alternate_port.name}</b> by ${P.alternate_port.cls} at ~$${fmt(P.alternate_port.landed_p50, 2)}/t landed. This is worth it if the inland/rail differential is below $${fmt(P.alternate_port.max_inland_diff, 2)}/t.</div>` : ""}
      ${P.notes.length ? `<p class="small mut" style="margin:10px 0 0">Notes: ${P.notes.join(" · ")}</p>` : ""}</div>
     <div class="kpis"><div class="kpi hl"><b>${N(P.cost.mean, 2, "$")}</b><span>expected landed $/t</span></div><div class="kpi"><b>$${fmt(P.cost.p10, 2)}-${fmt(P.cost.p90, 2)}</b><span>P10-P90 $/t</span></div>
      <div class="kpi"><b>${N(P.cost.cvar90, 2, "$")}</b><span>CVaR90 (bad case)</span></div><div class="kpi"><b>${N(P.programme_musd, 2, "$", "M")}</b><span>programme freight</span></div>
      <div class="kpi"><b class="${P.saving_vs_habit_musd >= 0 ? "up" : "down"}">${N(P.saving_vs_habit_musd, 2, "$", "M")}</b><span>vs daily-spot ${P.habit_class} (${fmt(P.saving_vs_habit_pct, 1)}%)</span></div><div class="kpi"><b>${N(P.freight_per_t_hot_metal, 2, "$")}</b><span>freight per t hot metal</span></div></div>
     <div class="grid g2"><div class="card"><h3><span class="h-l"><i></i>Why this recommendation</span></h3><ul class="why">${P.why.map(w => `<li>${w}</li>`).join("")}</ul></div>
      <div class="card"><h3><span class="h-l"><i></i>Charter ladder</span><span class="small mut">≤35% per tranche · re-solved weekly</span></h3><div class="ladder" id="pLad"></div>
       <h3 style="margin-top:14px"><span class="h-l"><i></i>Broker quote X-ray</span></h3><div id="pX"></div></div></div>
     <div class="grid g2"><div class="card"><h3><span class="h-l"><i></i>Vessel options · landed $/t (P10-P50-P90)</span></h3><div id="pCls" class="plot short"></div><div class="tw">${clsTable(P)}</div></div>
      <div class="card"><h3><span class="h-l"><i></i>Entry timing · COA quote if you wait</span></h3><div id="pTim" class="plot"></div></div></div>
     <div class="grid g2"><div class="card"><h3><span class="h-l"><i></i>Cost distribution over ${P.hist.mix.length} scenarios</span></h3><div id="pDist" class="plot"></div></div>
      <div class="card"><h3><span class="h-l"><i></i>Turnaround &amp; utilisation</span></h3>${utilTable(P.utilisation)}
      ${(P.alerts.length || P.events.length) ? `<h3 style="margin-top:14px"><span class="h-l"><i></i>Lane warnings</span></h3>${P.alerts.map(alertHTML).join("")}${P.events.slice(0, 3).map(e => `<div class="alert ${e.severity >= 3 ? "high" : ""}"><span class="k">${e.event_type}</span>${e.summary}</div>`).join("")}` : ""}</div></div>`;
    mixBar($("#pMix"), P.mix);
    $("#saveLed").onclick = async () => { const s2 = await post("/api/plan?save=true", rq); toast(`✓ Saved as ledger #${s2.ledger_id} · <a href="/api/ledger/${s2.ledger_id}/note" target="_blank" style="color:#2dd4bf">open charter note ↗</a> · <a href="#/ops" style="color:#2dd4bf">ledger</a>`, 7000); };
    const T = P.tranches, maxW = Math.max(8, ...T.map(t => t.week + 2));
    $("#pLad").innerHTML = `<div class="track"></div>` + (T.length ? T.map((t, i) => `<div class="tr" style="left:${6 + t.week / maxW * 86}%;animation-delay:${i * .15}s">wk +${t.week}<i></i><b>${pct(t.share)}</b></div>`).join("") : `<div class="tr" style="left:50%">no lock-in this week<i style="background:#475569;box-shadow:none"></i>stay spot</div>`);
    gauge($("#pX"), P.xray);
    const feas = P.classes.filter(c => c.feasible);
    PL("pCls", [{type: "bar", orientation: "h", y: feas.map(c => c.cls), x: feas.map(c => c.p50), marker: {color: feas.map(c => c.cls === P.best_class ? COL[c.cls] : "rgba(125,180,255,.25)")},
      error_x: {type: "data", symmetric: false, array: feas.map(c => c.p90 - c.p50), arrayminus: feas.map(c => c.p50 - c.p10), color: "#e6f1ff", thickness: 1.2}, text: feas.map(c => "$" + c.p50.toFixed(2)), textposition: "inside", hovertemplate: "%{y}: $%{x:.2f}/t<extra></extra>"}],
      {margin: {l: 86, r: 16, t: 6, b: 30}, xaxis: {title: "$/t"}});
    const tm = P.timing;
    PL("pTim", tm.length ? [{x: tm.map(t => t.w), y: tm.map(t => t.p90), line: {width: 0}, showlegend: false, hoverinfo: "skip"}, {x: tm.map(t => t.w), y: tm.map(t => t.p10), fill: "tonexty", fillcolor: "rgba(56,189,248,.15)", line: {width: 0}, name: "P10-P90"},
      {x: tm.map(t => t.w), y: tm.map(t => t.p50), name: "median re-quote", line: {color: "#38bdf8", width: 2.5}}, {x: [0, tm.length], y: [P.coa_quote, P.coa_quote], name: "quote today", line: {dash: "dot", color: "#fb7185"}},
      {x: tm.map(t => t.w), y: tm.map(t => t.p_cheaper * 100), name: "P(cheaper) %", yaxis: "y2", line: {color: "#2dd4bf", dash: "dash"}}] : [],
      {xaxis: {title: "weeks waited"}, yaxis: {title: "$/t"}, yaxis2: {overlaying: "y", side: "right", range: [0, 100], showgrid: false, title: "%"}, margin: {l: 52, r: 44, t: 10, b: 40}});
    PL("pDist", [{x: P.hist.mix, type: "histogram", name: "Recommended mix", opacity: .75, marker: {color: "#2dd4bf"}}, {x: P.hist.all_spot, type: "histogram", name: `All-spot ${P.best_class}`, opacity: .5, marker: {color: "#fbbf24"}},
      {x: P.hist.habit, type: "histogram", name: `Daily-spot ${P.habit_class}`, opacity: .45, marker: {color: "#fb7185"}}], {barmode: "overlay", xaxis: {title: "$/t"}});
  }
  const clsTable = P => `<table><thead><tr><th>Class</th><th>Parcel t</th><th class="l">Binding constraint</th><th>Voy</th><th>RV d</th><th>P50</th></tr></thead><tbody>${P.classes.map(c => c.feasible ?
    `<tr${c.cls === P.best_class ? ' style="font-weight:600;color:#fff"' : ""}><td>${c.cls}${c.cls === P.best_class ? " ★" : ""}</td><td>${fmt(c.cargo_t)}</td><td class="l">${c.binding}</td><td>${c.voyages}</td><td>${fmt(c.round_voyage_days, 1)}</td><td>$${fmt(c.p50, 2)}</td></tr>` :
    `<tr><td>${c.cls}</td><td class="no">✕</td><td class="l no" colspan="4">${c.binding}</td></tr>`).join("")}</tbody></table>`;
  const utilTable = u => `<table><tbody><tr><td>Round voyage</td><td>${u.round_voyage_days} d</td></tr><tr><td>laden / ballast / port</td><td>${u.laden_days} / ${u.ballast_days} / ${u.port_days} d</td></tr>
    <tr><td>Voyages per ship in programme</td><td>${u.voyages_per_ship}</td></tr><tr><td>Unutilised days per ship</td><td>${u.idle_days_per_ship} d</td></tr><tr><td>Ships needed on period TC</td><td>${u.ships_on_tc}</td></tr>
    <tr><td>Ballast share of voyage</td><td>${pct(u.ballast_share)}</td></tr><tr><td>Min laycan spacing (no self-queuing)</td><td>${u.laycan_spacing_days} d</td></tr></tbody></table>`;
  function gauge(el, x) {
    const pr = x.percentile != null ? x.percentile : 50, ang = -90 + pr * 1.8;
    el.innerHTML = `<div class="row" style="align-items:center;flex-wrap:nowrap"><svg class="gauge" viewBox="0 0 300 170" style="width:220px;flex:none">
      <defs><linearGradient id="gg"><stop offset="0" stop-color="#34d399"/><stop offset=".5" stop-color="#fbbf24"/><stop offset="1" stop-color="#fb7185"/></linearGradient></defs>
      <path d="M30 150 A120 120 0 0 1 270 150" fill="none" stroke="url(#gg)" stroke-width="16" stroke-linecap="round" opacity=".85"/>
      <g class="needle" style="transform:rotate(-90deg)"><line x1="150" y1="150" x2="150" y2="44" stroke="#e6f1ff" stroke-width="3"/><circle cx="150" cy="150" r="8" fill="#e6f1ff"/></g>
      <text x="30" y="168">P0</text><text x="140" y="24">P50</text><text x="252" y="168">P100</text></svg>
      <div><div class="mono small mut">fair-value band (spot)</div><div class="mono" style="font-size:18px">$${fmt(x.p10, 2)} · <b>$${fmt(x.p50, 2)}</b> · $${fmt(x.p90, 2)}</div>
      ${x.quote ? `<div style="margin-top:8px">Quote <b class="mono">$${fmt(x.quote, 2)}</b> is at the <b>${x.percentile}th</b> percentile: <span class="${x.percentile > 70 ? "no" : x.percentile < 30 ? "ok" : "warn"}">${x.verdict}</span></div>` : `<div class="mut small" style="margin-top:8px">Enter a broker quote in the form to X-ray it.</div>`}</div></div>`;
    setTimeout(() => { const n = el.querySelector(".needle"); if (n) n.style.transform = `rotate(${x.quote ? ang : 0}deg)`; }, 80);
  }

  /* ---------- FORECAST ---------- */
  async function forecast(v) {
    const pick = (location.hash.split("?")[1] || "Capesize");
    v.innerHTML = `<div class="row"><div class="seg" id="clsSeg">${CL.map(c => `<button data-c="${c}" class="${c === pick ? "on" : ""}">${c}</button>`).join("")}</div><span class="mut small">Walk-forward, strictly causal forecasts · conformal 80% bands</span></div><div id="fOut" class="grid"></div>`;
    const draw = async c => {
      $$("#clsSeg button").forEach(b => b.classList.toggle("on", b.dataset.c === c));
      const d = await get("/api/forecast/" + c), F = d.fan, last = F.hist_dates[F.hist_dates.length - 1];
      const fut = F.p50.map((_, i) => { const t = new Date(last); t.setDate(t.getDate() + 7 * (i + 1)); return t.toISOString().slice(0, 10); });
      const now = F.hist[F.hist.length - 1];
      $("#fOut").innerHTML = `<div class="kpis"><div class="kpi hl"><b>${N(now, 0, "$", "/d")}</b><span>${c} TCE now</span></div>${[4, 12, 26].map(h => `<div class="kpi"><b class="${F.p50[h - 1] >= now ? "up" : "down"}">${N(F.p50[h - 1], 0, "$")}</b><span>median in ${h} w (${((F.p50[h - 1] / now - 1) * 100).toFixed(1)}%)</span></div>`).join("")}<div class="kpi"><b>$${fmt(F.p10[11])}-${fmt(F.p90[11])}</b><span>12-week P10-P90</span></div></div>
        <div class="card"><h3><span class="h-l"><i></i>${c} time-charter equivalent · history &amp; 52-week fan</span></h3><div id="fFan" class="plot tall"></div></div>
        <div class="grid g3"><div class="card"><h3><span class="h-l"><i></i>Ensemble weights</span></h3><div id="fW" class="plot short"></div></div>
          <div class="card"><h3><span class="h-l"><i></i>Skill vs random walk by horizon</span></h3><div id="fSk" class="plot short"></div></div>
          <div class="card"><h3><span class="h-l"><i></i>What drives the 4-week view</span></h3><div id="fEx" class="plot short"></div></div></div>
        <div class="card"><h3><span class="h-l"><i></i>Out-of-sample accuracy (test 2021-2026) vs placebo world</span></h3><div class="tw"><table><thead><tr><th>h (wk)</th><th>MAPE %</th><th>RW MAPE %</th><th>Skill %</th><th>Cover 80 %</th><th>Direction %</th><th>DM p</th><th>Placebo skill %</th></tr></thead><tbody>
        ${d.accuracy.map((r, i) => `<tr><td>${r.h}</td><td>${fmt(r.MAPE_pct, 1)}</td><td>${fmt(r.MAPE_rw_pct, 1)}</td><td class="${r.skill_vs_rw_pct > 0 ? "ok" : "no"}">${fmt(r.skill_vs_rw_pct, 1)}</td><td>${fmt(r.coverage80_pct, 0)}</td><td>${fmt(r.directional_acc_pct, 0)}</td><td class="${r.DM_p < .05 ? "ok" : ""}">${fmt(r.DM_p, 3)}</td><td class="mut">${fmt(d.accuracy_placebo[i].skill_vs_rw_pct, 1)}</td></tr>`).join("")}</tbody></table></div>
        <p class="small mut">Placebo = a world where rates are unpredictable. Near-zero skill there shows the model is not overfitting.</p></div>`;
      PL("fFan", [{x: F.hist_dates, y: F.hist, name: "actual", line: {color: "#e6f1ff", width: 1.6}},
        {x: fut, y: F.p90, line: {width: 0}, showlegend: false, hoverinfo: "skip"}, {x: fut, y: F.p10, fill: "tonexty", fillcolor: "rgba(56,189,248,.16)", line: {width: 0}, name: "P10-P90"},
        {x: fut, y: F.p50, name: "median", line: {color: COL[c], width: 2.5}}],
        {yaxis: {title: "$/day"}, shapes: [{type: "rect", xref: "x", yref: "paper", x0: fut[26], x1: fut[fut.length - 1], y0: 0, y1: 1, fillcolor: "rgba(125,180,255,.05)", line: {width: 0}}, {type: "line", xref: "x", yref: "paper", x0: last, x1: last, y0: 0, y1: 1, line: {color: "#fbbf24", dash: "dot", width: 1}}],
         annotations: [{x: fut[38], y: 1, yref: "paper", text: "extrapolated · low confidence", showarrow: false, font: {size: 10, color: "#7f93ab"}}, {x: last, y: 1, yref: "paper", text: "today", showarrow: false, font: {size: 10, color: "#fbbf24"}, yshift: 8}]});
      PL("fW", [{type: "pie", hole: .62, labels: ["GBM quantile", "Structural", "Random walk"], values: [F.weights.gbm, F.weights.struct, F.weights.rw], marker: {colors: ["#38bdf8", "#2dd4bf", "#475569"]}, textinfo: "percent", sort: false}], {margin: {l: 10, r: 10, t: 10, b: 10}, showlegend: true, legend: {orientation: "v", x: 1, y: .5}});
      PL("fSk", [{type: "bar", x: d.accuracy.map(r => r.h + "w"), y: d.accuracy.map(r => r.skill_vs_rw_pct), name: "skill %", marker: {color: d.accuracy.map(r => r.skill_vs_rw_pct > 0 ? "#2dd4bf" : "#fb7185")}},
        {type: "scatter", x: d.accuracy.map(r => r.h + "w"), y: d.accuracy.map(r => r.coverage80_pct), name: "coverage %", yaxis: "y2", line: {color: "#fbbf24"}}], {yaxis: {title: "skill %"}, yaxis2: {overlaying: "y", side: "right", range: [60, 100], showgrid: false}, margin: {l: 44, r: 34, t: 10, b: 30}});
      const ex = d.explain.h4.gbm_gain_pct.slice(0, 8).reverse();
      PL("fEx", [{type: "bar", orientation: "h", y: ex.map(e => e[0]), x: ex.map(e => e[1]), marker: {color: "#38bdf8"}}], {margin: {l: 90, r: 10, t: 6, b: 30}, xaxis: {title: "GBM gain %"}});
      countUp($("#fOut"));
    };
    $$("#clsSeg button").forEach(b => b.onclick = () => { history.replaceState(null, "", "#/forecast?" + b.dataset.c); draw(b.dataset.c); });
    await draw(pick);
  }

  /* ---------- FEASIBILITY ---------- */
  async function feasibility(v) {
    const M = await get("/api/meta");
    v.innerHTML = `<div class="card"><div class="row"><div style="min-width:230px"><label class="small mut">Origin</label><select id="q-load">${Object.entries(M.load).map(([k, p]) => `<option value="${k}">${p.name}</option>`).join("")}</select></div>
      <div style="min-width:230px"><label class="small mut">Destination</label><select id="q-disch">${Object.entries(M.discharge).map(([k, p]) => `<option value="${k}">${p.name}</option>`).join("")}</select></div>
      <div style="width:150px"><label class="small mut">Max stem (t)</label><input type="number" id="q-stem" value="0" step="5000"></div>
      <label class="toggle"><input type="checkbox" id="q-mon"><span></span>SW monsoon</label><label class="toggle"><input type="checkbox" id="q-suez"><span></span>Avoid Suez</label></div></div>
      <div class="card"><h3><span class="h-l"><i></i>Will it fit? Discharge-port view</span><span class="small mut">green = full · amber = part-laden · red = cannot call</span></h3><div id="qScene"></div></div>
      <div class="grid g2"><div class="card"><h3><span class="h-l"><i></i>Lane feasibility (load + chokepoints + discharge)</span></h3><div class="tw" id="qLane"></div></div>
      <div class="card"><h3><span class="h-l"><i></i>Max cargo at every East-Coast port</span></h3><div class="tw" id="qMat"></div></div></div>
      <div class="grid g2"><div class="card"><h3><span class="h-l"><i></i>Draft-staged two-port discharge</span></h3><div id="qTwo"></div></div>
      <div class="card"><h3><span class="h-l"><i></i>Port constraint register</span><span class="pill part">ASSUMPTIONS · verify</span></h3><div class="tw">${portReg(M)}</div></div></div>`;
    $("#q-load").value = "HAY_POINT"; $("#q-disch").value = "PARADIP";
    const scene = new FitScene($("#qScene"), M);
    const run = async () => {
      const qs = new URLSearchParams({load: $("#q-load").value, disch: $("#q-disch").value, monsoon: $("#q-mon").checked, stem: +$("#q-stem").value || 0, avoid_suez: $("#q-suez").checked});
      const d = await api("/api/feasibility?" + qs); scene.set(d.disch, $("#q-mon").checked);
      $("#qLane").innerHTML = `<table><thead><tr><th>Class</th><th>Fit</th><th>Cargo t</th><th>Laden draft</th><th>nm</th><th class="l">Binding constraint / notes</th></tr></thead><tbody>${d.lane.map(r => `<tr><td>${r.cls}</td><td><span class="pill ${r.feasible ? (r.utilisation < .999 ? "part" : "ok") : "no"}">${r.feasible ? (r.utilisation < .999 ? "PART" : "FULL") : "NO"}</span></td><td>${fmt(r.cargo_t)}</td><td>${r.feasible ? r.laden_draft_m + " m" : "-"}</td><td>${fmt(r.nm)}</td><td class="l">${r.binding}${r.notes.length ? `<br><span class="small mut">${r.notes.join(" · ")}</span>` : ""}</td></tr>`).join("")}</tbody></table>`;
      $("#qMat").innerHTML = `<table class="heat"><thead><tr><th>Port</th>${CL.map(c => `<th>${c.slice(0, 5)}</th>`).join("")}</tr></thead><tbody>${Object.entries(d.matrix).map(([p, row]) => `<tr><td style="text-align:left">${M.discharge[p].name.split(" (")[0].replace(" anchorage", "")}</td>${CL.map(c => { const r = row[c], cap = M.vessels[c].dwt - M.vessels[c].constants_t, u = r.cargo_t / cap;
        return `<td title="${r.binding}" style="background:${r.feasible ? `rgba(45,212,191,${.08 + .35 * u})` : "rgba(251,113,133,.08)"};color:${r.feasible ? "#e6f1ff" : "#fb7185"}">${r.feasible ? fmt(r.cargo_t / 1000, 0) + "k" : "✕"}</td>`; }).join("")}</tr>`).join("")}</tbody></table>`;
      $("#qTwo").innerHTML = d.two_port ? `<p>A Capesize loads <b class="mono">${fmt(d.two_port.total_cargo_t)} t</b>, discharges <b class="mono">${fmt(d.two_port.discharge_at_first_t)} t</b> at <b>Dhamra</b> (18 m), then carries the balance (≤ ${fmt(d.two_port.max_at_second_t)} t) into <b>Paradip</b> within its 15 m draft.</p>
        <div class="mixbar"><div data-w="${d.two_port.discharge_at_first_t / d.two_port.total_cargo_t * 100}" style="background:linear-gradient(90deg,#0ea5e9,#38bdf8)">Dhamra</div><div data-w="${100 - d.two_port.discharge_at_first_t / d.two_port.total_cargo_t * 100}" style="background:linear-gradient(90deg,#14b8a6,#2dd4bf)">Paradip</div></div>
        <p class="small mut">Extra call ≈ ${d.two_port.extra_port_call_days} d and $${fmt(d.two_port.extra_cost_usd)}. Useful when one plant's port cannot take a full Capesize but two SAIL-served ports can share it.</p>` : "<p class='mut'>A Capesize cannot load at this origin.</p>";
      setTimeout(() => $$("#qTwo .mixbar div").forEach(x => x.style.width = x.dataset.w + "%"), 60);
    };
    $$("#view select, #view input").forEach(el => el.addEventListener("change", run));
    await run();
  }
  const portReg = M => `<table><thead><tr><th>Port</th><th>Draft m</th><th>LOA</th><th>Beam</th><th>t/day</th><th>Conf.</th></tr></thead><tbody>${Object.values(M.discharge).map(p => `<tr><td>${p.name}</td><td>${p.max_draft_m}</td><td>${p.max_loa_m}</td><td>${p.max_beam_m}</td><td>${fmt(p.rate_tpd)}</td><td><span class="pill ${p.confidence === "medium" ? "ok" : "part"}">${p.confidence}</span></td></tr>`).join("")}</tbody></table>`;

  /* ---------- RISK ---------- */
  async function risk(v) {
    const d = await api("/api/risk");
    const SAMPLES = ["IMD: cyclonic storm likely to cross north Odisha coast; Paradip and Dhamra port operations may be suspended for 48 hours.",
      "Dock workers strike at Haldia dock complex enters second day; cargo handling suspended.",
      "Several bulk carriers divert via Cape of Good Hope after renewed attacks in the Red Sea near Bab-el-Mandeb.",
      "Heavy rain in Bowen Basin disrupts coal rail to Hay Point; terminal queue rising."];
    v.innerHTML = `<div class="card"><h3><span class="h-l"><i></i>Ingest a news item / port notice / IMD bulletin</span><span class="small mut">POST /api/events/ingest → typed event → impacted SAIL lanes (stored)</span></h3>
      <div class="presets">${SAMPLES.map((t, i) => `<button data-s="${i}">${["Cyclone · Odisha", "Strike · Haldia", "Red Sea diversion", "QLD rail flood"][i]}</button>`).join("")}</div>
      <div class="row" style="align-items:stretch"><textarea id="evText" rows="2" style="flex:1;min-width:260px;padding:10px;border-radius:10px;border:1px solid var(--line2);background:rgba(3,10,20,.6);color:var(--ink);font:14px var(--f-body)" placeholder="Paste a headline or port circular…"></textarea>
      <button class="btn primary xs" id="evGo">Analyse &amp; store ▶</button></div><div id="evOut"></div></div>
      <div class="grid g2"><div class="card"><h3><span class="h-l"><i></i>Early warnings</span><span class="pill">${d.alerts.length} active</span></h3>${d.alerts.map(alertHTML).join("") || "<p class='mut'>No active alerts.</p>"}</div>
      <div class="card"><h3><span class="h-l"><i></i>Event intelligence · news → typed event → impacted lanes</span></h3><div class="timeline">${d.events.map(e => `<div class="tl s${e.severity}"><span class="d">${e.live ? `<span class="pill ok">LIVE #${e.id}</span> <a href="#" data-evdel="${e.id}" style="color:var(--coral)">delete</a> · ` : ""}${e.date} · ${e.event_type.replace("_", " ")} · severity ${e.severity} · ~${e.expected_duration_days} d · freight ${e.freight_direction}</span><p>${e.summary}</p><span class="small mut">Impacted: ${(e.impacted_lanes || []).slice(0, 5).join(", ")}${(e.impacted_lanes || []).length > 5 ? ` +${e.impacted_lanes.length - 5} more` : ""}</span></div>`).join("")}</div></div></div>
      <div class="card"><h3><span class="h-l"><i></i>Port congestion outlook · expected waiting days</span><div class="seg" id="pSeg"></div></h3><div id="rCong" class="plot"></div></div>
      <div class="grid g2"><div class="card"><h3><span class="h-l"><i></i>Spike vs crash odds · next 4 weeks</span></h3><div id="rSp" class="plot short"></div></div>
      <div class="card"><h3><span class="h-l"><i></i>Rate-move table</span></h3><table><thead><tr><th>Class</th><th>Now $/d</th><th>4w median</th><th>P(+20%)</th><th>P(-20%)</th></tr></thead><tbody>${d.spikes.map(s => `<tr><td>${s.cls}</td><td>${fmt(s.now)}</td><td>${fmt(s.median_4w)}</td><td class="${s.p_up20 > .2 ? "no" : ""}">${pct(s.p_up20)}</td><td class="${s.p_dn20 > .2 ? "warn" : ""}">${pct(s.p_dn20)}</td></tr>`).join("")}</tbody></table>
      <p class="small mut">Probabilities are computed from the calibrated scenario paths, not from point forecasts.</p></div></div>`;
    $$("[data-s]").forEach(b => b.onclick = () => $("#evText").value = SAMPLES[+b.dataset.s]);
    $("#evGo").onclick = async () => {
      const t = $("#evText").value.trim(); if (t.length < 10) return toast("Enter at least a sentence");
      try { const e = await post("/api/events/ingest", {text: t});
        $("#evOut").innerHTML = `<div class="alert ${e.severity >= 3 ? "high" : ""}" style="margin-top:12px"><span class="k">${e.event_type.replace("_", " ")}</span>severity ${e.severity} · ~${e.expected_duration_days} d · freight ${e.freight_direction} · locations: <b>${e.locations.join(", ") || "-"}</b><br>
          <span class="small">Impacted lanes (${e.impacted_lanes.length}): ${e.impacted_lanes.slice(0, 10).join(", ")}${e.impacted_lanes.length > 10 ? " …" : ""}</span></div>`;
        toast(`✓ Event #${e.id} stored`); setTimeout(route, 2200);
      } catch (err) { toast("✕ " + err.message); }
    };
    $$("[data-evdel]").forEach(a => a.onclick = async ev => { ev.preventDefault(); await api(`/api/events/${a.dataset.evdel}`, {method: "DELETE"}); route(); });
    const ports = Object.keys(d.congestion); let sel = new Set(["PARADIP", "DHAMRA", "HALDIA", "VIZAG"]);
    const drawC = () => PL("rCong", ports.filter(p => sel.has(p)).map(p => ({x: d.congestion[p].map(r => r.h), y: d.congestion[p].map(r => r.mean), name: p, line: {width: 2.2, shape: "spline"}})), {xaxis: {title: "weeks ahead"}, yaxis: {title: "days"}});
    $("#pSeg").innerHTML = ports.map(p => `<button data-p="${p}" class="${sel.has(p) ? "on" : ""}">${p.slice(0, 6)}</button>`).join("");
    $$("#pSeg button").forEach(b => b.onclick = () => { sel.has(b.dataset.p) ? sel.delete(b.dataset.p) : sel.add(b.dataset.p); b.classList.toggle("on"); drawC(); });
    drawC();
    PL("rSp", [{type: "bar", x: d.spikes.map(s => s.cls), y: d.spikes.map(s => s.p_up20 * 100), name: "P(+20%)", marker: {color: "#fb7185"}}, {type: "bar", x: d.spikes.map(s => s.cls), y: d.spikes.map(s => -s.p_dn20 * 100), name: "P(-20%)", marker: {color: "#38bdf8"}}], {barmode: "relative", yaxis: {title: "%"}});
  }

  /* ---------- IDLE ---------- */
  async function idleP(v) {
    const M = await get("/api/meta");
    v.innerHTML = `<div class="card"><div class="row"><div class="seg" id="iCls">${CL.map(c => `<button data-c="${c}" class="${c === "Capesize" ? "on" : ""}">${c}</button>`).join("")}</div>
      <div style="min-width:200px"><select id="i-load">${Object.entries(M.load).filter(([k]) => !["HAMPTON_RDS", "UST_LUGA", "VOSTOCHNY", "NACALA", "BEIRA", "MUARA_BERAU", "TANJUNG_BARA"].includes(k)).map(([k, p]) => `<option value="${k}">${p.name}</option>`).join("")}</select></div>
      <div style="min-width:200px"><select id="i-disch">${Object.entries(M.discharge).map(([k, p]) => `<option value="${k}">${p.name}</option>`).join("")}</select></div>
      <div style="flex:1;min-width:200px"><label class="small mut">Idle days in rotation <span class="mono" id="iDv">6</span></label><input type="range" id="i-days" min="0" max="30" step="1" value="6"></div></div></div>
      <div class="grid g2"><div class="card"><h3><span class="h-l"><i></i>Ranked options for the idle window / ballast leg</span></h3><div id="iOpts"></div></div>
      <div class="card"><h3><span class="h-l"><i></i>How the idle manager thinks</span></h3><div id="iInfo"></div>
      <ul class="why" style="margin-top:12px"><li><b>Triangulation:</b> backhaul East-Coast iron ore or pellets to China, then ballast China → Australia, instead of a full ballast leg home.</li><li><b>Short relet:</b> sublet the gap at forecast spot TCE less a 10% haircut (e.g. an Indonesia-India coal round).</li><li><b>JIT slow-steaming:</b> absorb the idle time at sea at ≥ 9 kn. Fuel falls with the cube of speed, and CII emissions fall too.</li><li><b>Laycan spacing:</b> keep at least the discharge time plus a buffer between SAIL arrivals so they never queue behind each other.</li></ul></div></div>`;
    $("#i-load").value = "HAY_POINT"; $("#i-disch").value = "PARADIP";
    let cls = "Capesize";
    const run = async () => {
      $("#iDv").textContent = $("#i-days").value;
      const d = await api(`/api/idle?cls=${cls}&load=${$("#i-load").value}&disch=${$("#i-disch").value}&idle_days=${$("#i-days").value}`);
      if (!d.ok) { $("#iOpts").innerHTML = `<p class="no">${d.message}</p>`; $("#iInfo").innerHTML = ""; return; }
      const mx = Math.max(1, ...d.options.map(o => Math.abs(o.net_usd)));
      $("#iOpts").innerHTML = d.options.map((o, i) => `<div class="opt ${i === 0 && o.net_usd > 0 ? "best" : ""}"><div><b>${o.option}</b><div class="small mut">${o.detail}${o.extra_days ? ` · +${o.extra_days} d` : ""}</div></div><div class="val ${o.net_usd > 0 ? "ok" : o.net_usd < 0 ? "no" : ""}">${o.net_usd >= 0 ? "+" : "-"}$${fmt(Math.abs(o.net_usd))}</div><div class="barw"><i data-w="${Math.abs(o.net_usd) / mx * 100}" style="background:${o.net_usd >= 0 ? "linear-gradient(90deg,#14b8a6,#2dd4bf)" : "linear-gradient(90deg,#e11d48,#fb7185)"}"></i></div></div>`).join("");
      setTimeout(() => $$("#iOpts .barw i").forEach(x => x.style.width = x.dataset.w + "%"), 50);
      $("#iInfo").innerHTML = `<div class="kpis"><div class="kpi"><b>$${fmt(d.hire)}</b><span>period hire $/day</span></div><div class="kpi"><b>$${fmt(d.tce_forecast)}</b><span>5-week forecast TCE</span></div><div class="kpi hl"><b>${d.laycan_spacing_days} d</b><span>min laycan spacing</span></div></div>`;
    };
    $$("#iCls button").forEach(b => b.onclick = () => { cls = b.dataset.c; $$("#iCls button").forEach(x => x.classList.toggle("on", x === b)); run(); });
    $$("#view select, #view input").forEach(el => el.addEventListener(el.type === "range" ? "input" : "change", debounce(run, 150)));
    await run();
  }

  /* ---------- BACKTEST ---------- */
  async function backtest(v) {
    const d = await get("/api/backtest"), S = d.summary, fs = S.FS, b1 = S.B1, b0 = S.B0, P = d.placebo, R = d.rw_ablation;
    const NM = {B0: "Daily spot · Panamax habit (today)", B1: "+ optimal vessel", B2: "+ forecast-timed spot", B3: "70% COA, no model (control)", FS: "FreightSaarthi", ORC: "Perfect foresight (oracle)"};
    v.innerHTML = `<div class="callout">Hay Point → Paradip, 900 kt/quarter, 22 test quarters (2021 to mid-2026), walk-forward. The market data is <b>synthetic</b>, so this demonstrates the method, not SAIL's realised savings.</div>
      <div class="kpis"><div class="kpi hl"><b>${N(fs.saving_vs_base_pct, 1, "", "%")}</b><span>saving vs daily spot · CI ${fmt(fs.saving_ci90_pct[0], 1)}-${fmt(fs.saving_ci90_pct[1], 1)}%</span></div>
      <div class="kpi"><b>${N(fs.saving_musd, 1, "$", "M")}</b><span>saved in test period</span></div><div class="kpi"><b>${N(fs.oracle_capture_pct, 0, "", "%")}</b><span>of oracle savings captured</span></div>
      <div class="kpi"><b>${b0.spot_fixtures} → ${N(fs.spot_fixtures)}</b><span>spot fixtures</span></div><div class="kpi"><b>${N(fs.win_rate_vs_base * 100, 0, "", "%")}</b><span>quarters cheaper than today</span></div>
      <div class="kpi"><b>$${fmt(b1.cvar90_block_cost, 2)} → ${N(fs.cvar90_block_cost, 2, "$")}</b><span>CVaR90 vs spot + optimal vessel</span></div></div>
      <div class="grid g2"><div class="card"><h3><span class="h-l"><i></i>Where the savings come from ($/t)</span></h3><div id="bWf" class="plot"></div></div>
      <div class="card"><h3><span class="h-l"><i></i>Realised landed cost per quarter</span></h3><div id="bQ" class="plot"></div></div></div>
      <div class="card"><h3><span class="h-l"><i></i>Strategy scorecard</span></h3><div class="tw"><table><thead><tr><th>Strategy</th><th>avg $/t</th><th>saving</th><th>90% CI</th><th>$M</th><th>std</th><th>CVaR90</th><th>worst Q</th><th>win-rate</th><th>oracle cap.</th><th>spot fix.</th><th>contracted</th></tr></thead><tbody>
      ${Object.keys(NM).map(k => { const s = S[k]; return `<tr${k === "FS" ? ' style="font-weight:600;color:#fff;background:rgba(45,212,191,.07)"' : ""}><td>${NM[k]}</td><td>${fmt(s.avg_cost_usd_t, 2)}</td><td>${fmt(s.saving_vs_base_pct, 1)}%</td><td>${fmt(s.saving_ci90_pct[0], 1)} / ${fmt(s.saving_ci90_pct[1], 1)}</td><td>${fmt(s.saving_musd, 1)}</td><td>${fmt(s.std_block_cost, 2)}</td><td>${fmt(s.cvar90_block_cost, 2)}</td><td>${fmt(s.worst_block_cost, 2)}</td><td>${pct(s.win_rate_vs_base)}</td><td>${s.oracle_capture_pct != null ? fmt(s.oracle_capture_pct, 0) + "%" : "-"}</td><td>${s.spot_fixtures ?? "-"}</td><td>${s.contracted_share_pct != null ? fmt(s.contracted_share_pct, 0) + "%" : "-"}</td></tr>`; }).join("")}</tbody></table></div></div>
      <div class="grid g3"><div class="card"><h3><span class="h-l"><i></i>Honesty check · placebo world</span></h3><p class="mut small">When rates are unpredictable, timing and contracting should add nothing.</p>
        <div class="kpis"><div class="kpi"><b>${fmt((P.B1.avg_cost_usd_t - P.FS.avg_cost_usd_t) / P.B1.avg_cost_usd_t * 100, 1)}%</b><span>FS vs B1 (≈ 0 ✓)</span></div><div class="kpi"><b>${fmt((P.B1.avg_cost_usd_t - P.B2.avg_cost_usd_t) / P.B1.avg_cost_usd_t * 100, 1)}%</b><span>timed spot vs B1 (≈ 0 ✓)</span></div></div></div>
       <div class="card"><h3><span class="h-l"><i></i>Value of forecasting</span></h3><p class="mut small">The same optimiser fed random-walk forecasts:</p><div class="kpis"><div class="kpi"><b>$${fmt(R.FS.avg_cost_usd_t, 2)}</b><span>FS with RW forecasts</span></div><div class="kpi hl"><b>$${fmt(fs.avg_cost_usd_t, 2)}</b><span>FS with ensemble</span></div></div></div>
       <div class="card"><h3><span class="h-l"><i></i>Contracts alone don't save</span></h3><p class="mut small">70% COA signed mechanically, without a model:</p><div class="kpis"><div class="kpi"><b>${fmt(S.B3.saving_vs_base_pct, 1)}%</b><span>CI ${fmt(S.B3.saving_ci90_pct[0], 1)} / ${fmt(S.B3.saving_ci90_pct[1], 1)}%</span></div></div></div></div>
      <div class="card"><h3><span class="h-l"><i></i>Decision-focused calibration (validation 2018H2-2020)</span><span class="small mut">knobs chosen by realised cost, never on test</span></h3><div class="tw"><table><thead><tr><th>λ (CVaR)</th><th>δ (stopping)</th><th>ladder step</th><th>avg $/t</th><th>CVaR90</th><th>score</th></tr></thead><tbody>${d.tune_log.map(t => `<tr${t.score === d.selected.score ? ' style="color:#2dd4bf;font-weight:600"' : ""}><td>${t.lam}</td><td>${t.delta}</td><td>${t.step}</td><td>${fmt(t.avg, 3)}</td><td>${fmt(t.cvar90, 3)}</td><td>${fmt(t.score, 3)}${t.score === d.selected.score ? " ★" : ""}</td></tr>`).join("")}</tbody></table></div></div>`;
    const st = [["Daily spot", b0.avg_cost_usd_t, "absolute"], ["Vessel optimisation", b1.avg_cost_usd_t - b0.avg_cost_usd_t, "relative"], ["Timed spot", S.B2.avg_cost_usd_t - b1.avg_cost_usd_t, "relative"], ["Charter ladder", fs.avg_cost_usd_t - S.B2.avg_cost_usd_t, "relative"], ["FreightSaarthi", fs.avg_cost_usd_t, "total"]];
    PL("bWf", [{type: "waterfall", x: st.map(s => s[0]), y: st.map(s => s[1]), measure: st.map(s => s[2]), text: st.map(s => (s[2] === "relative" ? "" : "$") + s[1].toFixed(2)), textposition: "outside",
      decreasing: {marker: {color: "#2dd4bf"}}, increasing: {marker: {color: "#fb7185"}}, totals: {marker: {color: "#38bdf8"}}, connector: {line: {color: "rgba(125,180,255,.3)"}}}], {yaxis: {range: [S.ORC.avg_cost_usd_t * 0.85, b0.avg_cost_usd_t * 1.05], title: "$/t"}, showlegend: false});
    const B = d.blocks; PL("bQ", [["B0", "#fb7185", "Daily spot"], ["B1", "#fbbf24", "+ vessel"], ["FS", "#2dd4bf", "FreightSaarthi"], ["ORC", "#64748b", "Oracle"]].map(([k, c, n]) => ({x: B.map(b => b.block_start), y: B.map(b => b[k + "_cost_t"]), name: n, line: {color: c, width: k === "FS" ? 3 : 1.6, dash: k === "ORC" ? "dot" : "solid", shape: "spline"}})), {yaxis: {title: "$/t"}});
  }

  /* ---------- NETWORK ---------- */
  async function network(v) {
    const [G, M] = await Promise.all([get("/api/network"), get("/api/meta")]);
    const ports = Object.keys(M.discharge), loads = Object.keys(M.load);
    const best = (l, p) => { const r = G.filter(g => g.load === l && g.disch === p && g.feasible); return r.length ? r.reduce((a, x) => x.landed_usd_t < a.landed_usd_t ? x : a) : null; };
    v.innerHTML = `<div class="card"><h3><span class="h-l"><i></i>Lane map · landed freight to <span id="nDestN"></span></span><div class="seg" id="nSeg">${ports.map(p => `<button data-p="${p}" class="${p === "PARADIP" ? "on" : ""}">${p.slice(0, 7)}</button>`).join("")}</div></h3>
      <canvas class="netmap" id="nMap"></canvas><p class="small mut">Lane colour and width show landed $/t for the best feasible class (teal = cheapest, coral = most expensive). Click a row to highlight its lane.</p></div>
      <div class="grid g2"><div class="card"><h3><span class="h-l"><i></i>Origin ranking for this port</span></h3><div class="tw" id="nRank"></div></div>
      <div class="card"><h3><span class="h-l"><i></i>All origins × all ports ($/t, best class)</span></h3><div class="tw" id="nHeat"></div></div></div>`;
    let dest = "PARADIP", hl = null;
    const all = G.filter(g => g.feasible).map(g => g.landed_usd_t), gmin = Math.min(...all), gmax = Math.max(...all);
    const colr = x => { const t = Math.min(1, (x - gmin) / (Math.min(gmax, gmin * 3) - gmin)); const a = [45, 212, 191], b = [251, 191, 36], c = [251, 113, 133]; const m = t < .5 ? a.map((v, i) => v + (b[i] - v) * t * 2) : b.map((v, i) => v + (c[i] - v) * (t - .5) * 2); return `rgba(${m.map(Math.round).join(",")},0.85)`; };
    const map = new SeaMap($("#nMap"), {fit: "zoom", zoom: 1.02, focus: [98, 1], anchor: [0.5, 0.5], dest, shipsPerLane: 2, parallax: false, capeAlt: false,
      laneColor: l => { const b = best(l.org, dest); return b ? colr(b.landed_usd_t) : "rgba(251,113,133,.15)"; }, laneWidth: l => { const b = best(l.org, dest); return b ? 1 + 3 * (1 - Math.min(1, (b.landed_usd_t - gmin) / (gmax - gmin))) : .6; }});
    map.start(); cleanup.push(() => map.destroy());
    const draw = () => {
      $("#nDestN").textContent = M.discharge[dest].name; map.setOptions({dest, highlight: hl});
      const rows = loads.map(l => ({l, b: best(l, dest)})).sort((a, b) => (a.b ? a.b.landed_usd_t : 1e9) - (b.b ? b.b.landed_usd_t : 1e9));
      const mn = rows[0].b ? rows[0].b.landed_usd_t : 0, mx = Math.max(...rows.filter(r => r.b).map(r => r.b.landed_usd_t));
      $("#nRank").innerHTML = `<table><thead><tr><th>Origin</th><th>Class</th><th>Parcel</th><th>$/t</th><th>vs best</th><th class="l"></th></tr></thead><tbody>${rows.map(({l, b}) => b ? `<tr data-l="${l}" style="cursor:pointer${hl === l ? ";background:rgba(56,189,248,.1)" : ""}"><td>${M.load[l].name}</td><td><span class="pill" style="color:${COL[b.cls]}">${b.cls}</span></td><td>${fmt(b.cargo_t / 1000)}k</td><td class="mono">$${fmt(b.landed_usd_t, 2)}</td><td class="mono ${b.landed_usd_t - mn > 0 ? "warn" : "ok"}">+$${fmt(b.landed_usd_t - mn, 2)}</td><td class="l"><span class="bar-i" style="width:${10 + 110 * (b.landed_usd_t - mn) / Math.max(1e-6, mx - mn)}px;background:${colr(b.landed_usd_t)}"></span></td></tr>` : `<tr><td>${M.load[l].name}</td><td class="no" colspan="5">no feasible class</td></tr>`).join("")}</tbody></table>
        <p class="small mut">"vs best" is the <b>freight-adjusted FOB break-even</b>: an origin must be at least this much cheaper FOB to compete.</p>`;
      $$("#nRank tr[data-l]").forEach(tr => tr.onclick = () => { hl = hl === tr.dataset.l ? null : tr.dataset.l; draw(); });
      $("#nHeat").innerHTML = `<table class="heat"><thead><tr><th>Origin</th>${ports.map(p => `<th>${p.slice(0, 5)}</th>`).join("")}</tr></thead><tbody>${loads.map(l => `<tr><td style="text-align:left">${M.load[l].name.split(" (")[0]}</td>${ports.map(p => { const b = best(l, p); return b ? `<td style="background:${colr(b.landed_usd_t).replace("0.85", "0.22")}${p === dest ? ";outline:1px solid rgba(56,189,248,.5)" : ""}">${b.landed_usd_t.toFixed(1)}</td>` : `<td class="no">✕</td>`; }).join("")}</tr>`).join("")}</tbody></table>`;
    };
    $$("#nSeg button").forEach(b => b.onclick = () => { dest = b.dataset.p; $$("#nSeg button").forEach(x => x.classList.toggle("on", x === b)); draw(); });
    draw();
  }

  /* ---------- API EXPLORER ---------- */
  const SAMPLE = {"/api/plan": {load: "HAY_POINT", disch: "PARADIP", volume: 900000, duration: 13, lead: 3, risk_lambda: 0.5, broker_quote: 15.5}, "/api/quote-xray": {load: "HAY_POINT", disch: "PARADIP", quote: 15.5}};
  async function apiP(v) {
    const c = await get("/api");
    v.innerHTML = `<div class="grid g2"><div class="card"><h3><span class="h-l"><i></i>Available endpoints</span><span class="row"><a class="btn ghost xs" href="/docs" target="_blank">Swagger ↗</a><a class="btn ghost xs" href="/openapi.json" target="_blank">openapi.json ↗</a></span></h3>
      <p class="small mut">Pages: ${c.pages.map(p => `<a href="${p.path}" style="color:var(--cyan)">${p.path}</a> (${p.summary})`).join(" · ")}</p>
      ${c.endpoints.map((e, i) => `<div class="endpoint"><span class="pill ${e.methods.includes("POST") ? "post" : "get"}">${e.methods.join("/")}</span><div><code>${e.path}</code><small>${e.summary}</small></div>${e.path.includes("{") || e.path.includes("pipeline/run") ? `<button class="btn ghost xs" data-i="${i}" data-alt="${e.path.includes("{") ? e.path.replace("{cls}", "Capesize") : ""}">Try</button>` : `<button class="btn ghost xs" data-i="${i}">Try</button>`}</div>`).join("")}</div>
      <div class="card" style="position:sticky;top:86px;align-self:start"><h3><span class="h-l"><i></i>Response</span><span class="mono small" id="aMeta"></span></h3><div id="aReq" class="mono small mut" style="margin-bottom:8px">Pick an endpoint → Try</div><pre class="json" id="aOut">{ }</pre></div></div>`;
    $$(".endpoint button").forEach(b => b.onclick = async () => {
      const e = c.endpoints[+b.dataset.i], path = b.dataset.alt || e.path, isPost = e.methods.includes("POST");
      if (path.includes("pipeline/run") && !confirm("Re-run the pipeline now?")) return;
      const body = SAMPLE[path] || {};
      $("#aReq").textContent = `${isPost ? "POST" : "GET"} ${path}` + (isPost ? "  " + JSON.stringify(body) : "");
      const st = performance.now(); let res, txt;
      try { res = await fetch(path, isPost ? {method: "POST", headers: {"Content-Type": "application/json"}, body: JSON.stringify(body)} : {}); txt = await res.text(); } catch (err) { txt = String(err); }
      $("#aMeta").innerHTML = res ? `<span class="${res.ok ? "ok" : "no"}">${res.status}</span> · ${Math.round(performance.now() - st)} ms · ${fmt(txt.length / 1024, 1)} kB` : "error";
      let pretty = txt; try { pretty = JSON.stringify(JSON.parse(txt), null, 2); } catch (e2) {}
      if (pretty.length > 30000) pretty = pretty.slice(0, 30000) + "\n… (truncated)";
      $("#aOut").innerHTML = pretty.replace(/[&<>]/g, ch => ({"&": "&amp;", "<": "&lt;", ">": "&gt;"}[ch]))
        .replace(/("(?:\\.|[^"\\])*")(\s*:)?|\b(-?\d+(?:\.\d+)?(?:e[+-]?\d+)?)\b|\b(true|false|null)\b/g, (m, s, colon, n, b2) => s ? (colon ? `<span class="k">${s}</span>${colon}` : `<span class="s">${s}</span>`) : n ? `<span class="n">${n}</span>` : `<span class="b">${b2}</span>`);
    });
  }

  /* ---------- OPERATIONS: programmes + decision ledger ---------- */
  const STATUS_PILL = {open: "", planned: "part", contracted: "ok", closed: "", pending: "part", accepted: "ok", rejected: "no", modified: "part"};
  let lastOpsPlan = null;
  const opsPlanHTML = P => `<div class="callout teal" style="margin-top:14px"><b>Ledger #${P.ledger_id}</b>: ${P.voyages} × ${P.best_class} of ${fmt(P.parcel_t)} t · expected $${fmt(P.cost.mean, 2)}/t (P10-P90 ${fmt(P.cost.p10, 2)}-${fmt(P.cost.p90, 2)}) · ${P.action}
    <div class="mixbar" id="opMix"></div><div class="row"><a class="btn primary xs" href="/api/ledger/${P.ledger_id}/note" target="_blank">Open charter note ↗</a><button class="btn ghost xs" data-dec="${P.ledger_id}">Record decision</button></div></div>`;
  async function ops(v) {
    const [M, progs, led] = await Promise.all([get("/api/meta"), api("/api/programmes"), api("/api/ledger?limit=100")]);
    const st = led.stats, cnt = s => progs.filter(p => p.status === s).length;
    const opt = (obj, sel) => Object.entries(obj).map(([k, p]) => `<option value="${k}" ${k === sel ? "selected" : ""}>${p.name}</option>`).join("");
    v.innerHTML = `<div class="kpis"><div class="kpi hl"><b>${N(progs.length)}</b><span>cargo programmes</span></div><div class="kpi"><b>${N(cnt("open"))}</b><span>open</span></div>
      <div class="kpi"><b>${N(cnt("planned"))}</b><span>planned</span></div><div class="kpi"><b>${N(cnt("contracted"))}</b><span>contracted</span></div>
      <div class="kpi"><b>${N(st.n || 0)}</b><span>recommendations logged</span></div><div class="kpi"><b>${N(st.acc || 0)} / ${N(st.pend || 0)}</b><span>accepted / pending</span></div></div>
      <div class="card"><h3><span class="h-l"><i></i>Cargo programmes (SAIL requirements)</span><button class="btn primary xs" id="newProg">+ New programme</button></h3>
      <form id="progForm" class="form" style="display:none;margin-bottom:14px"><input type="hidden" id="pg-id"><div class="grid g4">
        <div><label>Name</label><input type="text" id="pg-name" required placeholder="Q1 coking coal - Bhilai"></div><div><label>Plant</label><input type="text" id="pg-plant" placeholder="Bhilai"></div>
        <div><label>Origin</label><select id="pg-load">${opt(M.load, "HAY_POINT")}</select></div><div><label>Destination</label><select id="pg-disch">${opt(M.discharge, "PARADIP")}</select></div>
        <div><label>Volume (t)</label><input type="number" id="pg-vol" value="900000" step="any" min="10000"></div><div><label>Duration (weeks)</label><input type="number" id="pg-dur" value="13" min="4" max="48"></div>
        <div><label>First laycan (weeks)</label><input type="number" id="pg-lead" value="3" min="2" max="12"></div><div><label>Risk λ</label><input type="number" id="pg-lam" value="0.5" step="any" min="0" max="5"></div></div>
        <div class="row" style="margin-top:6px"><label class="toggle"><input type="checkbox" id="pg-mon"><span></span>Monsoon</label><label class="toggle"><input type="checkbox" id="pg-suez"><span></span>Avoid Suez</label>
        <div style="flex:1;min-width:220px"><label>Notes</label><input type="text" id="pg-notes"></div></div>
        <div class="row" style="margin-top:12px"><button class="btn primary xs" type="submit" id="pg-save">Save programme</button><button class="btn ghost xs" type="button" id="pg-cancel">Cancel</button></div></form>
      <div class="tw"><table><thead><tr><th>#</th><th class="l">Programme</th><th class="l">Lane</th><th>Volume t</th><th>Weeks</th><th>Status</th><th>Plans</th><th></th></tr></thead><tbody>
      ${progs.map(p => `<tr><td>${p.id}</td><td class="l"><b>${p.name}</b><br><span class="small mut">${p.plant || ""} ${p.notes ? "· " + p.notes : ""}</span></td><td class="l">${M.load[p.load] ? M.load[p.load].name.split(" (")[0] : p.load} → ${M.discharge[p.disch] ? M.discharge[p.disch].name.split(" (")[0] : p.disch}</td>
        <td>${fmt(p.volume)}</td><td>${p.duration}</td><td><span class="pill ${STATUS_PILL[p.status] || ""}">${p.status}</span></td><td>${p.n_plans}</td>
        <td><div class="row" style="flex-wrap:nowrap;gap:6px"><button class="btn primary xs" data-plan="${p.id}">Plan ▶</button><button class="btn ghost xs" data-edit="${p.id}">Edit</button><button class="btn ghost xs" data-del="${p.id}">✕</button></div></td></tr>`).join("") || `<tr><td colspan="8" class="mut">No programmes yet.</td></tr>`}</tbody></table></div>
      <div id="planOut">${lastOpsPlan ? opsPlanHTML(lastOpsPlan) : ""}</div></div>
      <div class="card"><h3><span class="h-l"><i></i>Decision ledger · audit trail of every recommendation</span><a class="btn ghost xs" href="/api/ledger/export.csv">⭳ Export CSV</a></h3>
      <div class="tw"><table><thead><tr><th>#</th><th>Time</th><th class="l">Lane</th><th>Class</th><th>COA/TC/Spot</th><th>Exp $/t</th><th>CVaR</th><th>Decision</th><th class="l">By · note</th><th></th></tr></thead><tbody>
      ${led.rows.map(r => `<tr><td>${r.id}</td><td class="mono small">${r.created_at.slice(5, 16)}</td><td class="l">${r.load} → ${r.disch}<br><span class="small mut">${fmt(r.volume)} t · hash ${r.input_hash}</span></td><td>${r.best_class}</td>
        <td class="mono">${pct(r.mix_coa)}/${pct(r.mix_tc)}/${pct(r.mix_spot)}</td><td class="mono">$${fmt(r.exp_cost, 2)}</td><td class="mono">$${fmt(r.cvar90, 2)}</td><td><span class="pill ${STATUS_PILL[r.decision]}">${r.decision}</span></td>
        <td class="l small">${r.decided_by || ""}${r.decision_note ? " · " + r.decision_note : ""}${r.actual_rate ? ` · actual $${r.actual_rate}` : ""}</td>
        <td><div class="row" style="flex-wrap:nowrap;gap:6px"><a class="btn ghost xs" href="/api/ledger/${r.id}/note" target="_blank">Note ↗</a><button class="btn ghost xs" data-dec="${r.id}">Decide</button></div></td></tr>`).join("") || `<tr><td colspan="10" class="mut">No recommendations logged yet. Plan a programme, or use "Save to ledger" on the planner.</td></tr>`}</tbody></table></div></div>
      <dialog id="decDlg" class="card" style="color:var(--ink);max-width:420px;width:92%"><form method="dialog" class="form"><h3>Record decision · ledger #<span id="dl-id"></span></h3>
        <label>Decision</label><select id="dl-dec"><option value="accepted">Accepted</option><option value="modified">Modified</option><option value="rejected">Rejected</option><option value="pending">Pending</option></select>
        <label>Decided by</label><input type="text" id="dl-by" placeholder="e.g. GM (Shipping)"><label>Note</label><input type="text" id="dl-note" placeholder="e.g. COA tender floated">
        <label>Actual fixed rate $/t (optional)</label><input type="number" id="dl-rate" step="0.01">
        <div class="row" style="margin-top:14px"><button class="btn primary xs" type="button" id="dl-save">Save decision</button><button class="btn ghost xs" type="button" id="dl-cancel">Cancel</button></div></form></dialog>`;
    const form = $("#progForm"), show = p => { form.style.display = "block"; $("#pg-id").value = p ? p.id : ""; $("#pg-name").value = p ? p.name : ""; $("#pg-plant").value = p ? (p.plant || "") : "";
      $("#pg-load").value = p ? p.load : "HAY_POINT"; $("#pg-disch").value = p ? p.disch : "PARADIP"; $("#pg-vol").value = p ? p.volume : 900000; $("#pg-dur").value = p ? p.duration : 13;
      $("#pg-lead").value = p ? p.lead : 3; $("#pg-lam").value = p ? p.risk_lambda : 0.5; $("#pg-mon").checked = p ? p.monsoon : false; $("#pg-suez").checked = p ? p.avoid_suez : false; $("#pg-notes").value = p ? (p.notes || "") : "";
      $("#pg-save").textContent = p ? "Update programme" : "Save programme"; $("#pg-name").focus(); };
    $("#newProg").onclick = () => show(null); $("#pg-cancel").onclick = () => form.style.display = "none";
    form.onsubmit = async e => { e.preventDefault(); const id = $("#pg-id").value;
      const body = {name: $("#pg-name").value, plant: $("#pg-plant").value || null, load: $("#pg-load").value, disch: $("#pg-disch").value, volume: +$("#pg-vol").value, duration: +$("#pg-dur").value,
        lead: +$("#pg-lead").value, risk_lambda: +$("#pg-lam").value, monsoon: $("#pg-mon").checked, avoid_suez: $("#pg-suez").checked, notes: $("#pg-notes").value || null};
      try { await api(id ? `/api/programmes/${id}` : "/api/programmes", {method: id ? "PUT" : "POST", headers: {"Content-Type": "application/json"}, body: JSON.stringify(body)}); toast(id ? "✓ Programme updated" : "✓ Programme created"); route(); }
      catch (err) { toast("✕ " + err.message); } };
    $$("[data-edit]").forEach(b => b.onclick = () => show(progs.find(p => p.id === +b.dataset.edit)));
    $$("[data-del]").forEach(b => b.onclick = async () => { if (!confirm("Delete this programme?")) return; await api(`/api/programmes/${b.dataset.del}`, {method: "DELETE"}); toast("Programme deleted"); route(); });
    $$("[data-plan]").forEach(b => b.onclick = async () => {
      b.disabled = true; b.textContent = "…";
      try {
        const P = await post(`/api/programmes/${b.dataset.plan}/plan`, {});
        lastOpsPlan = P; toast(`✓ Planned & logged as ledger #${P.ledger_id}`); route(); return;
      } catch (err) { toast("✕ " + err.message); }
      b.disabled = false; b.textContent = "Plan ▶";
    });
    if (lastOpsPlan && $("#opMix")) mixBar($("#opMix"), lastOpsPlan.mix);
    const dlg = $("#decDlg");
    $$("[data-dec]").forEach(b => b.onclick = () => { $("#dl-id").textContent = b.dataset.dec; dlg.showModal(); });
    $("#dl-cancel").onclick = () => dlg.close();
    $("#dl-save").onclick = async () => {
      dlg.close();
      const body = {decision: $("#dl-dec").value, decided_by: $("#dl-by").value || null, note: $("#dl-note").value || null, actual_rate: +$("#dl-rate").value || null};
      try { await post(`/api/ledger/${$("#dl-id").textContent}/decision`, body); toast("✓ Decision recorded"); route(); } catch (err) { toast("✕ " + err.message); }
    };
  }

  /* ---------- DATA HUB: template -> upload -> retrain ---------- */
  async function dataHub(v) {
    const d = await api("/api/data/status"), up = d.uploaded;
    const uploadedActive = d.active_source === "uploaded";
    v.innerHTML = `<div class="card"><h3><span class="h-l"><i></i>Active data</span><span class="pill ${uploadedActive ? "ok" : "part"}">${uploadedActive ? "UPLOADED DATA" : "SYNTHETIC DEMO DATA"}</span></h3>
      <p class="mono small">${d.active_label} · as of ${d.asof}</p><p class="small mut">Every page, the planner and the backtest read this dataset. Replace it with SAIL's real weekly history in three steps.</p></div>
      <div class="grid g3"><div class="card"><h3><span class="h-l"><i></i>① Download template</span></h3><p class="small mut">Weekly rows. Required: <span class="mono">${d.required_columns.join(", ")}</span> ($/day TCE per class, e.g. Baltic 5TC/82/63/38 or broker assessments). Optional drivers (bunker, coal, PMI, ballaster counts, port waiting days) are proxy-filled when missing, and the fill is labelled. Minimum ${d.min_weeks} weeks.</p>
        <a class="btn primary xs" href="/api/data/template">⭳ freightsaarthi_market_template.csv</a></div>
      <div class="card"><h3><span class="h-l"><i></i>② Upload CSV</span></h3><label class="drop" id="drop" style="display:block;border:1.5px dashed var(--line2);border-radius:12px;padding:22px;text-align:center;cursor:pointer">
        <input type="file" id="csvFile" accept=".csv,text/csv" style="display:none"><b>Drop a CSV here</b><br><span class="small mut">or click to choose a file</span></label><div id="upRep" style="margin-top:12px">${up.uploaded ? repHTML(up) : ""}</div></div>
      <div class="card"><h3><span class="h-l"><i></i>③ Retrain &amp; backtest</span></h3><p class="small mut">Re-runs walk-forward forecasting, decision-focused tuning, the backtest, ablations and the placebo on the chosen data. Uploaded data is split automatically into train, validation and test periods.</p>
        <div class="row"><button class="btn primary xs" id="runUp" ${up.uploaded && !up.error ? "" : "disabled"}>▶ Run on uploaded data</button><button class="btn ghost xs" id="runSyn">↺ Restore synthetic demo</button>${up.uploaded ? `<button class="btn ghost xs" id="delUp">Remove upload</button>` : ""}</div>
        <div id="pipeBox" style="margin-top:12px"></div></div></div>`;
    const drop = $("#drop"), fileIn = $("#csvFile");
    const send = async file => {
      const text = await file.text(); $("#upRep").innerHTML = `<div class="skel" style="height:60px"></div>`;
      const r = await fetch("/api/data/upload", {method: "POST", headers: {"Content-Type": "text/csv"}, body: text}); const j = await r.json();
      if (!r.ok) { $("#upRep").innerHTML = `<div class="alert high"><span class="k">rejected</span>${j.detail}</div>`; return; }
      toast("✓ CSV validated and stored"); route();
    };
    fileIn.onchange = () => fileIn.files[0] && send(fileIn.files[0]);
    ["dragover", "dragenter"].forEach(ev => drop.addEventListener(ev, e => { e.preventDefault(); drop.style.borderColor = "var(--cyan)"; }));
    drop.addEventListener("dragleave", () => drop.style.borderColor = "");
    drop.addEventListener("drop", e => { e.preventDefault(); drop.style.borderColor = ""; if (e.dataTransfer.files[0]) send(e.dataTransfer.files[0]); });
    if ($("#delUp")) $("#delUp").onclick = async () => { await api("/api/data/upload", {method: "DELETE"}); toast("Upload removed"); route(); };
    const runPipe = async source => {
      try { await post(`/api/pipeline/run?fast=${source === "uploaded"}&source=${source}`, {}); } catch (e) { toast("✕ " + e.message); return; }
      $$("#runUp, #runSyn").forEach(b => b.disabled = true);
      const poll = setInterval(async () => {
        const s = await api("/api/pipeline/status");
        if (!$("#pipeBox")) { clearInterval(poll); return; }
        $("#pipeBox").innerHTML = `<div class="row"><span class="spinner" style="width:18px;height:18px;border-width:2px;${s.status === "running" ? "" : "display:none"}"></span><b>${s.status}</b> <span class="small mut">${s.source} · ${s.stage || ""}</span></div><pre class="json" style="max-height:180px;margin-top:8px">${(s.log || []).join("\n")}</pre>`;
        if (s.status !== "running") { clearInterval(poll); Object.keys(cache).forEach(k => delete cache[k]); header(); toast(s.status === "done" ? "✓ Pipeline finished, every page now uses this data" : "✕ " + s.error, 7000); setTimeout(route, 1200); }
      }, 1500);
    };
    $("#runUp").onclick = () => runPipe("uploaded"); $("#runSyn").onclick = () => runPipe("synthetic");
  }
  const repHTML = u => u.error ? `<div class="alert high"><span class="k">invalid</span>${u.error}</div>` :
    `<table><tbody><tr><td>Rows</td><td>${u.rows} weeks</td></tr><tr><td>Range</td><td>${u.start} → ${u.end}</td></tr><tr><td>Provided optional</td><td class="l small">${u.provided_optional.join(", ") || "-"}</td></tr>
     <tr><td>Proxy-filled</td><td class="l small warn">${u.filled_from_proxy.join(", ") || "none"}</td></tr>${u.warnings.length ? `<tr><td>Warnings</td><td class="l small warn">${u.warnings.join("; ")}</td></tr>` : ""}<tr><td>Fingerprint</td><td class="mono">${u.sha1}</td></tr></tbody></table>`;

  /* ---------- COMPARE LANES ---------- */
  async function compareP(v) {
    const M = await get("/api/meta");
    v.innerHTML = `<div class="card"><div class="row"><div class="seg" id="cmMode"><button data-m="dest" class="on">Many origins → one port</button><button data-m="orig">One origin → many ports</button></div>
      <div style="min-width:230px" id="cmPick"></div><div style="width:150px"><label class="small mut">Volume (t)</label><input type="number" id="cm-vol" value="900000" step="any" min="10000"></div>
      <div style="width:120px"><label class="small mut">Weeks</label><input type="number" id="cm-dur" value="13" min="4" max="48"></div><label class="toggle"><input type="checkbox" id="cm-suez"><span></span>Avoid Suez</label></div>
      <div class="presets" id="cmChips" style="margin-top:12px"></div><button class="btn primary xs" id="cmRun" style="margin-top:6px">Compare ▶</button></div>
      <div id="cmOut" class="grid"></div>`;
    let mode = "dest";
    const pickers = () => {
      $("#cmPick").innerHTML = mode === "dest" ? `<label class="small mut">Destination</label><select id="cm-one">${Object.entries(M.discharge).map(([k, p]) => `<option value="${k}">${p.name}</option>`).join("")}</select>`
        : `<label class="small mut">Origin</label><select id="cm-one">${Object.entries(M.load).map(([k, p]) => `<option value="${k}">${p.name}</option>`).join("")}</select>`;
      const many = mode === "dest" ? M.load : M.discharge;
      $("#cmChips").innerHTML = Object.entries(many).map(([k, p]) => `<button data-k="${k}" class="on" style="border-color:var(--teal);color:#fff">${p.name.split(" (")[0].replace(" anchorage", "")}</button>`).join("");
      $$("#cmChips button").forEach(b => b.onclick = () => { b.classList.toggle("on"); b.style.borderColor = b.classList.contains("on") ? "var(--teal)" : ""; b.style.color = b.classList.contains("on") ? "#fff" : ""; });
    };
    $$("#cmMode button").forEach(b => b.onclick = () => { mode = b.dataset.m; $$("#cmMode button").forEach(x => x.classList.toggle("on", x === b)); pickers(); });
    pickers();
    $("#cmRun").onclick = async () => {
      const one = $("#cm-one").value, sel = $$("#cmChips button.on").map(b => b.dataset.k);
      if (!sel.length) return toast("Select at least one lane");
      const lanes = sel.map(k => mode === "dest" ? {load: k, disch: one} : {load: one, disch: k});
      $("#cmOut").innerHTML = `<div class="card"><div class="skel" style="height:200px"></div></div>`;
      const r = await post("/api/compare", {lanes, volume: +$("#cm-vol").value, duration: +$("#cm-dur").value, avoid_suez: $("#cm-suez").checked});
      const ok = r.rows.filter(x => x.ok), lbl = x => mode === "dest" ? M.load[x.load].name.split(" (")[0] : M.discharge[x.disch].name.split(" (")[0];
      $("#cmOut").innerHTML = `${r.best ? `<div class="callout teal">Cheapest: <b>${M.load[r.best.load].name} → ${M.discharge[r.best.disch].name}</b> by ${r.best.best_class} at <b>$${fmt(r.best.landed_mean, 2)}/t</b> landed. "Premium" is the freight-adjusted FOB break-even: another origin must be at least this much cheaper FOB to compete.</div>` : ""}
        <div class="card"><h3><span class="h-l"><i></i>Landed $/t (P10-P90) by lane</span></h3><div id="cmPlot" class="plot"></div></div>
        <div class="card"><div class="tw"><table><thead><tr><th class="l">Lane</th><th>Class</th><th>Parcel t</th><th>Voy</th><th>Landed $/t</th><th>P10-P90</th><th>CVaR90</th><th>Premium</th><th>COA/TC/Spot</th><th>$M</th></tr></thead><tbody>
        ${r.rows.map(x => x.ok ? `<tr><td class="l">${M.load[x.load].name.split(" (")[0]} → ${M.discharge[x.disch].name.split(" (")[0]}</td><td><span class="pill" style="color:${COL[x.best_class]}">${x.best_class}</span></td><td>${fmt(x.parcel_t)}</td><td>${x.voyages}</td>
          <td class="mono"><b>$${fmt(x.landed_mean, 2)}</b></td><td class="mono">${fmt(x.landed_p10, 2)}-${fmt(x.landed_p90, 2)}</td><td class="mono">$${fmt(x.cvar90, 2)}</td><td class="mono ${x.premium_vs_best ? "warn" : "ok"}">+$${fmt(x.premium_vs_best, 2)}</td>
          <td class="mono">${pct(x.mix.coa)}/${pct(x.mix.tc)}/${pct(x.mix.spot)}</td><td class="mono">${fmt(x.programme_musd, 1)}</td></tr>`
          : `<tr><td class="l">${x.load} → ${x.disch}</td><td class="no" colspan="9">${x.message}</td></tr>`).join("")}</tbody></table></div></div>`;
      PL("cmPlot", [{type: "bar", x: ok.map(lbl), y: ok.map(x => x.landed_mean), marker: {color: ok.map(x => COL[x.best_class])},
        error_y: {type: "data", symmetric: false, array: ok.map(x => x.landed_p90 - x.landed_mean), arrayminus: ok.map(x => x.landed_mean - x.landed_p10), color: "#e6f1ff"},
        text: ok.map(x => x.best_class), hovertemplate: "%{x}: $%{y:.2f}/t<extra>%{text}</extra>"}], {yaxis: {title: "$/t landed"}});
    };
    $("#cmRun").click();
  }

  header(); route();
})();
