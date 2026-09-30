/* FreightSaarthi landing page - motion, scrollytelling and live data */
(() => {
  const $ = s => document.querySelector(s), $$ = s => [...document.querySelectorAll(s)];
  const api = (p, o) => fetch(p, o).then(r => { if (!r.ok) throw new Error(r.status); return r.json(); });
  const reduced = matchMedia("(prefers-reduced-motion: reduce)").matches;
  const fmt = (x, d = 0) => Number(x).toLocaleString("en-IN", {minimumFractionDigits: d, maximumFractionDigits: d});
  document.body.classList.add("loading");
  let SUM = null, META = null, TICK = null;

  /* ---------- split headings into animated words ---------- */
  function split(el) {
    let w = 0;
    const walk = node => {
      [...node.childNodes].forEach(ch => {
        if (ch.nodeType === 3) {
          const frag = document.createDocumentFragment();
          ch.textContent.split(/(\s+)/).forEach(tok => {
            if (!tok) return;
            if (/^\s+$/.test(tok)) { frag.appendChild(document.createTextNode(" ")); return; }
            const o = document.createElement("span"); o.className = "split-w";
            const i = document.createElement("span"); i.textContent = tok; i.style.setProperty("--w", w++);
            o.appendChild(i); frag.appendChild(o);
          });
          ch.replaceWith(frag);
        } else if (ch.nodeType === 1 && ch.tagName !== "BR") walk(ch);
      });
    };
    walk(el);
  }
  $$("[data-split]").forEach(split);

  /* ---------- preloader ---------- */
  const msgs = ["Charting the course", "Loading port drafts", "Reading the freight tape", "Plotting coal lanes", "Setting sail"];
  let prog = 0, mi = 0;
  const bump = v => { prog = Math.max(prog, v); $("#plBar").style.width = prog + "%"; };
  const msgT = setInterval(() => { mi = (mi + 1) % msgs.length; $("#plMsg").textContent = msgs[mi]; }, 520);
  const t0 = performance.now();
  const loads = [
    api("/api/summary").then(d => { SUM = d; bump(45); }).catch(() => bump(45)),
    api("/api/meta").then(d => { META = d; bump(75); }).catch(() => bump(75)),
    api("/api/ticker").then(d => { TICK = d; bump(90); }).catch(() => bump(90)),
  ];
  Promise.all(loads).then(() => {
    bump(100);
    setTimeout(() => {
      clearInterval(msgT); $("#preloader").classList.add("done"); document.body.classList.remove("loading");
      $(".hero-title").classList.add("split-in"); startTyping(); fillLive(); fillTicker(); initFit(); fillResults(); buildModules();
    }, Math.max(0, 1300 - (performance.now() - t0)));
  });

  /* ---------- typing subtitle ---------- */
  const phrases = ["coking coal from Queensland.", "Capesize, Panamax, Supramax & Handysize.", "Paradip, Dhamra, Vizag & Haldia.",
    "multi-voyage contracts, not daily spot.", "draft-aware vessel choices.", "cargo from the US, Mozambique, Russia & Indonesia."];
  function startTyping() {
    const el = $("#typed"); let p = 0, i = 0, del = false;
    const step = () => {
      const s = phrases[p];
      el.textContent = s.slice(0, i);
      if (!del && i < s.length) { i++; setTimeout(step, 38 + Math.random() * 40); }
      else if (!del) { del = true; setTimeout(step, 1700); }
      else if (i > 0) { i--; setTimeout(step, 18); }
      else { del = false; p = (p + 1) % phrases.length; setTimeout(step, 260); }
    };
    step();
  }

  /* ---------- hero map ---------- */
  const tip = $("#mapTip");
  const map = new SeaMap($("#heroMap"), {fit: "zoom", zoom: innerWidth > 900 ? 0.97 : 1.6, focus: [98, 1], anchor: innerWidth > 900 ? [0.6, 0.47] : [0.5, 0.35],
    tooltip: (code, x, y) => {
      if (!code || !META) { tip.classList.remove("on"); return; }
      const P = META.discharge[code], L = META.load[code];
      let h = "";
      if (P) h = `<b>${P.name}</b><div class="r"><span>max arrival draft</span><span class="mono">${P.max_draft_m} m</span></div><div class="r"><span>LOA / beam</span><span class="mono">${P.max_loa_m} / ${P.max_beam_m} m</span></div><div class="r"><span>handling</span><span class="mono">${fmt(P.rate_tpd)} t/d</span></div><div class="r"><span>confidence</span><span class="mono">${P.confidence}</span></div>`;
      else if (L) h = `<b>${L.name}</b><div class="r"><span>country</span><span>${L.country}</span></div><div class="r"><span>sailing draft</span><span class="mono">${L.max_draft_m} m</span></div><div class="r"><span>to Paradip</span><span class="mono">${fmt(META.routes[code].nm)} nm</span></div><div class="r"><span>loading</span><span class="mono">${fmt(L.rate_tpd)} t/d</span></div>`;
      else { tip.classList.remove("on"); return; }
      tip.innerHTML = h; tip.style.left = Math.min(x + 16, innerWidth - 230) + "px"; tip.style.top = (y + 14) + "px"; tip.classList.add("on");
    }
  });
  map.start();
  const heroObs = new IntersectionObserver(es => es.forEach(e => e.isIntersecting ? map.start() : map.stop()));
  heroObs.observe($(".hero"));

  function fillLive() {
    if (!SUM || !TICK) return;
    const cape = TICK.find(t => t.label.startsWith("CAPESIZE")), par = TICK.find(t => t.label.startsWith("PARADIP"));
    $("#heroLive").innerHTML = `<span class="chip"><span class="dot"></span>as of <b>${SUM.asof}</b></span>
      <span class="chip">Capesize <b>${cape.value}</b> <span class="${cape.change >= 0 ? "up" : "down"} mono">${cape.change >= 0 ? "▲" : "▼"}${Math.abs(cape.change)}% 4w</span></span>
      <span class="chip">Paradip wait <b>${par.value}</b></span><span class="chip">pilot pick <b>${SUM.recommendation.class}</b></span>`;
  }
  function fillTicker() {
    if (!TICK) return;
    const one = TICK.map(t => `<span>${t.label}<b>${t.value}</b>${t.change == null ? "" : `<i class="${t.change >= 0 ? "up" : "down"}">${t.change >= 0 ? "▲" : "▼"} ${Math.abs(t.change)}${t.note.includes("days") ? "d" : "%"}</i> <small class="mut">${t.note}</small>`}</span>`).join("");
    $("#ticker").innerHTML = one + one;
  }

  /* ---------- scroll-linked effects ---------- */
  const nav = $("#topnav"), links = $$(".navlinks a"), compass = $("#compass"), heroC = $("#heroMap"), heroT = $(".hero-content");
  const tickG = compass.querySelector(".ticks");
  for (let a = 0; a < 360; a += 15) { const r1 = a % 90 ? 86 : 80, x1 = 100 + r1 * Math.sin(a * Math.PI / 180), y1 = 100 - r1 * Math.cos(a * Math.PI / 180), x2 = 100 + 92 * Math.sin(a * Math.PI / 180), y2 = 100 - 92 * Math.cos(a * Math.PI / 180); tickG.insertAdjacentHTML("beforeend", `<line x1="${x1}" y1="${y1}" x2="${x2}" y2="${y2}"/>`); }
  const secs = ["challenge", "why", "fit", "how", "results", "modules"].map(id => document.getElementById(id));
  let ticking = false;
  function onScroll() {
    const y = scrollY, H = innerHeight, D = document.documentElement.scrollHeight - H;
    const f = Math.min(1, y / D);
    $("#vFill").style.width = f * 100 + "%"; $("#vShip").style.left = f * 100 + "%";
    nav.classList.toggle("scrolled", y > 40);
    if (y < H * 1.2 && !reduced) {
      const k = y / H;
      heroC.style.transform = `scale(${1 + k * 0.18}) translateY(${k * 60}px)`; heroC.style.opacity = 1 - k * 0.85;
      heroT.style.transform = `translateY(${k * -90}px)`; heroT.style.opacity = 1 - k * 1.3;
    }
    compass.style.transform = `rotate(${y * 0.12}deg)`;
    let cur = null; secs.forEach(s => { if (s.getBoundingClientRect().top < H * 0.45) cur = s.id; });
    links.forEach(a => a.classList.toggle("on", a.getAttribute("href") === "#" + cur));
    pipeProgress(); ticking = false;
  }
  addEventListener("scroll", () => { if (!ticking) { ticking = true; requestAnimationFrame(onScroll); } }, {passive: true});

  /* ---------- reveal on scroll ---------- */
  const rev = new IntersectionObserver(es => es.forEach(e => {
    if (e.isIntersecting) { e.target.classList.add("in"); e.target.querySelectorAll("[data-split]").forEach(x => x.classList.add("split-in")); if (e.target.id === "results" || e.target.closest("#results")) runCounters(); rev.unobserve(e.target); }
  }), {threshold: 0.18});
  $$("[data-reveal]").forEach(el => rev.observe(el));

  /* ---------- tilt + spotlight ---------- */
  function spotlight(el, tilt) {
    el.addEventListener("mousemove", e => {
      const r = el.getBoundingClientRect(), x = (e.clientX - r.left) / r.width, y = (e.clientY - r.top) / r.height;
      el.style.setProperty("--mx", x * 100 + "%"); el.style.setProperty("--my", y * 100 + "%");
      if (tilt && !reduced) el.style.transform = `perspective(900px) rotateX(${(0.5 - y) * 8}deg) rotateY(${(x - 0.5) * 10}deg) translateY(-4px)`;
    });
    el.addEventListener("mouseleave", () => { if (tilt) el.style.transform = ""; });
  }
  $$(".tilt").forEach(el => spotlight(el, true));

  /* ---------- story chart (sticky scrollytelling) ---------- */
  const sc = $("#storyChart"), sg = sc.getContext("2d");
  let step = 0, A = {line: 0, ticks: 0, band: 0, drafts: 0, ladder: 0, dim: 0}, T = {line: 1, ticks: 1, band: 0, drafts: 0, ladder: 0, dim: 0}, storyOn = false;
  const bigs = ["Daily", "", "8.0-19.5 m", ""], tags = ["CAPESIZE TCE · 104 WEEKS · $/day", "CAPESIZE TCE · TROUGH TO PEAK", "EAST-COAST MAX ARRIVAL DRAFT · m", "SPOT FIXTURES → CHARTER LADDER"];
  const foots = ["each red tick = a single spot fixture negotiated from scratch", "shaded band = the trough-to-peak range of one vessel class",
    "the draft sets the ship: from Handysize-only Haldia to full-Capesize Gangavaram", "teal = contracted cost via the CVaR charter ladder: smoother, cheaper, fewer fixtures"];
  function setStep(s) {
    step = s;
    T = [{line: 1, ticks: 1, band: 0, drafts: 0, ladder: 0, dim: 0}, {line: 1, ticks: 0.3, band: 1, drafts: 0, ladder: 0, dim: 0},
         {line: 1, ticks: 0, band: 0, drafts: 1, ladder: 0, dim: 1}, {line: 1, ticks: 0.6, band: 0, drafts: 0, ladder: 1, dim: 0}][s];
    $$(".step").forEach(x => x.classList.toggle("active", +x.dataset.step === s));
    const big = $("#storyBig"); big.style.opacity = 0;
    setTimeout(() => {
      big.textContent = s === 1 ? `+${SUM ? SUM.cape_swing_pct : 100}%` : s === 3 ? `${SUM ? SUM.spot_fixtures_before : 268} → ${SUM ? SUM.spot_fixtures_after : 54}` : bigs[s];
      big.style.opacity = 1; $("#storyTag").textContent = tags[s]; $("#storyFoot").textContent = foots[s];
    }, 220);
  }
  const stepObs = new IntersectionObserver(es => es.forEach(e => { if (e.isIntersecting) setStep(+e.target.dataset.step); }), {rootMargin: "-45% 0px -45% 0px"});
  $$(".step").forEach(s => stepObs.observe(s));
  new IntersectionObserver(es => es.forEach(e => { storyOn = e.isIntersecting; if (storyOn) requestAnimationFrame(drawStory); })).observe($("#challenge"));
  function sizeStory() { const d = Math.min(devicePixelRatio || 1, 2), r = sc.getBoundingClientRect(); sc.width = r.width * d; sc.height = r.height * d; sg.setTransform(d, 0, 0, d, 0, 0); }
  addEventListener("resize", sizeStory); sizeStory();
  function drawStory(now) {
    if (!storyOn) return;
    for (const k in A) A[k] += (T[k] - A[k]) * (k === "line" ? 0.03 : 0.08);
    const W = sc.clientWidth, H = sc.clientHeight, g = sg; g.clearRect(0, 0, W, H);
    const ys = SUM ? SUM.cape_hist : [], n = ys.length;
    if (n) {
      const lo = Math.min(...ys) * 0.9, hi = Math.max(...ys) * 1.05, pl = 46, pr = 10, pt = 14, pb = 26;
      const X = i => pl + (W - pl - pr) * i / (n - 1), Y = v => pt + (H - pt - pb) * (1 - (v - lo) / (hi - lo));
      g.strokeStyle = `rgba(125,180,255,${.08 * (1 - A.drafts)})`; g.fillStyle = `rgba(160,190,230,${.5 * (1 - A.drafts)})`; g.font = "10px 'JetBrains Mono',monospace";
      for (let k = 0; k <= 4; k++) { const v = lo + (hi - lo) * k / 4, y = Y(v); g.beginPath(); g.moveTo(pl, y); g.lineTo(W - pr, y); g.stroke(); g.fillText("$" + Math.round(v / 1000) + "k", 4, y + 3); }
      if (A.band > 0.01) {
        const mx = Math.max(...ys), mn = Math.min(...ys);
        g.fillStyle = `rgba(251,191,36,${0.10 * A.band})`; g.fillRect(pl, Y(mx), W - pl - pr, Y(mn) - Y(mx));
        g.setLineDash([4, 4]); g.strokeStyle = `rgba(251,191,36,${0.8 * A.band})`;
        [mx, mn].forEach(v => { g.beginPath(); g.moveTo(pl, Y(v)); g.lineTo(W - pr, Y(v)); g.stroke(); });
        g.setLineDash([]); g.fillStyle = `rgba(253,230,138,${A.band})`; g.fillText(`peak $${fmt(mx)}`, W - 120, Y(mx) - 6); g.fillText(`trough $${fmt(mn)}`, W - 128, Y(mn) + 14);
      }
      const upto = Math.max(2, Math.floor(n * Math.min(1, A.line)));
      const grd = g.createLinearGradient(0, 0, W, 0); grd.addColorStop(0, "#7dd3fc"); grd.addColorStop(1, "#38bdf8");
      g.strokeStyle = grd; g.globalAlpha = 1 - A.dim * 0.95; g.lineWidth = 2; g.beginPath();
      for (let i = 0; i < upto; i++) i ? g.lineTo(X(i), Y(ys[i])) : g.moveTo(X(i), Y(ys[i])); g.stroke();
      g.lineTo(X(upto - 1), H - pb); g.lineTo(X(0), H - pb); g.closePath(); const fg = g.createLinearGradient(0, pt, 0, H); fg.addColorStop(0, "rgba(56,189,248,.25)"); fg.addColorStop(1, "rgba(56,189,248,0)"); g.fillStyle = fg; g.fill();
      if (A.ticks > 0.01) for (let i = 2; i < upto; i += 2) { const a = A.ticks * (0.6 + 0.4 * Math.sin(now / 300 + i)); g.fillStyle = `rgba(251,113,133,${a})`; g.fillRect(X(i) - 1, H - pb - 8, 2, 8); g.beginPath(); g.arc(X(i), Y(ys[i]), 2.2, 0, 6.28); g.fill(); }
      if (A.ladder > 0.01) {
        const sm = ys.map((_, i) => { const a = ys.slice(Math.max(0, i - 12), i + 1); return a.reduce((s, v) => s + v, 0) / a.length * 0.93; });
        g.strokeStyle = `rgba(45,212,191,${A.ladder})`; g.lineWidth = 3; g.shadowColor = "#2dd4bf"; g.shadowBlur = 12 * A.ladder; g.beginPath();
        sm.forEach((v, i) => i ? g.lineTo(X(i), Y(v)) : g.moveTo(X(i), Y(v))); g.stroke(); g.shadowBlur = 0;
      }
      g.globalAlpha = 1;
      if (A.drafts > 0.01 && META) {
        const P = Object.values(META.discharge).sort((a, b) => a.max_draft_m - b.max_draft_m), bh = (H - 40) / P.length;
        P.forEach((p, i) => {
          const w = (W - 190) * (p.max_draft_m / 20) * Math.min(1, A.drafts * 1.2 - i * 0.05);
          const y = 18 + i * bh; g.fillStyle = `rgba(186,230,253,${A.drafts})`; g.font = "12px 'Space Grotesk',sans-serif"; g.fillText(p.name.split(" (")[0].replace(" anchorage", "").slice(0, 20), 6, y + bh * 0.55);
          const gr = g.createLinearGradient(150, 0, 150 + w, 0); gr.addColorStop(0, "rgba(56,189,248,.25)"); gr.addColorStop(1, p.max_draft_m < 10 ? "#fb7185" : p.max_draft_m < 16 ? "#fbbf24" : "#2dd4bf");
          g.globalAlpha = A.drafts; g.fillStyle = gr; g.fillRect(150, y + 4, Math.max(0, w), bh - 12); g.globalAlpha = 1;
          g.fillStyle = `rgba(230,241,255,${A.drafts})`; g.font = "12px 'JetBrains Mono',monospace"; g.fillText(p.max_draft_m.toFixed(1) + " m", 156 + Math.max(0, w), y + bh * 0.55);
        });
      }
    }
    requestAnimationFrame(drawStory);
  }

  /* ---------- will it fit ---------- */
  let FS = null;
  function initFit() {
    if (!META) return;
    FS = new FitScene($("#fitStage"), META);
    const order = Object.entries(META.discharge).sort((a, b) => a[1].max_draft_m - b[1].max_draft_m);
    $("#fitPorts").innerHTML = order.map(([k, p]) => `<button data-p="${k}" class="${k === "PARADIP" ? "on" : ""}">${p.name.split(" (")[0].replace(" anchorage", "").replace("Visakhapatnam Outer Harbour", "Vizag")}<small>${p.max_draft_m}m</small></button>`).join("");
    $$("#fitPorts button").forEach(b => b.onclick = () => { $$("#fitPorts button").forEach(x => x.classList.remove("on")); b.classList.add("on"); FS.set(b.dataset.p, $("#fitMonsoon").checked); readFit(); });
    $("#fitMonsoon").onchange = () => { FS.set(FS.port, $("#fitMonsoon").checked); readFit(); };
    readFit();
    // gentle auto-tour until the user interacts
    let auto = setInterval(() => {
      const r = $("#fit").getBoundingClientRect(); if (r.top > innerHeight || r.bottom < 0) return;
      const bs = $$("#fitPorts button"), i = bs.findIndex(b => b.classList.contains("on")); bs[(i + 1) % bs.length].click();
    }, 3800);
    $("#fitPorts").addEventListener("pointerdown", () => clearInterval(auto), {once: true});
  }
  function readFit() {
    $("#fitRead").innerHTML = FS.results().map(r => {
      const c = r.ok ? (r.part ? "part" : "ok") : "no";
      return `<div class="r ${c}"><b>${r.cls}<span class="pill ${c}">${r.ok ? (r.part ? "PART-LADEN" : "FULL") : "CANNOT CALL"}</span></b><div class="v">${r.ok ? fmt(r.cargo) + " t" : "-"}</div><small>${r.why}</small></div>`;
    }).join("");
  }

  /* ---------- pipeline ---------- */
  function pipeProgress() {
    const s = $("#how"); if (!s) return; const r = s.getBoundingClientRect(), H = innerHeight;
    const p = Math.max(0, Math.min(1, (H * 0.8 - r.top) / (r.height * 0.8)));
    $("#pipeGlow").style.strokeDashoffset = 1160 * (1 - p);
    $$(".node").forEach(n => n.classList.toggle("on", p >= (+n.dataset.n) / 5 - 0.02));
    $("#pipe").classList.toggle("flow", p > 0.98);
  }

  /* ---------- results ---------- */
  let countersDone = false;
  function runCounters() {
    if (countersDone || !SUM) return; countersDone = true;
    $$("[data-count]").forEach(el => {
      const target = +SUM[el.dataset.count], dec = +(el.dataset.dec || 0), dur = 1800, st = performance.now();
      const tick = now => { const k = Math.min(1, (now - st) / dur), e = 1 - Math.pow(1 - k, 3); el.textContent = fmt(target * e, dec); if (k < 1) requestAnimationFrame(tick); };
      requestAnimationFrame(tick);
    });
  }
  function fillResults() {
    if (!SUM) return;
    $("#ciTxt").textContent = `90% CI ${SUM.saving_ci[0].toFixed(1)}-${SUM.saving_ci[1].toFixed(1)}% · oracle capture ${SUM.oracle_capture_pct.toFixed(0)}%`;
    $("#swingTxt").textContent = `~${SUM.cape_swing_pct}%`; $("#fixTxt").textContent = SUM.spot_fixtures_before;
    const C = SUM.cost, items = [["B0", "Daily spot (today)", "#fb7185"], ["B1", "+ vessel optimisation", "#fbbf24"], ["B2", "+ timed spot", "#7dd3fc"], ["FS", "FreightSaarthi", "#2dd4bf"], ["ORC", "Perfect foresight", "rgba(148,163,184,.5)"]];
    const base = 10, mx = Math.max(...Object.values(C));
    $("#wfBars").innerHTML = items.map(([k, n, col]) => `<div class="wf-bar"><div class="val" style="color:${col}">$${C[k].toFixed(2)}</div><div class="col" data-h="${(C[k] - base) / (mx - base) * 100}" style="background:linear-gradient(180deg,${col},rgba(6,18,34,.2));${k === "ORC" ? "border:1px dashed rgba(148,163,184,.6)" : ""}"></div><div class="nm">${n}</div></div>`).join("");
    const wf = $(".wf"); new IntersectionObserver((es, o) => es.forEach(e => { if (e.isIntersecting) { $$(".wf .col").forEach((c, i) => setTimeout(() => c.style.height = c.dataset.h * 0.92 + "%", i * 160)); runCounters(); o.disconnect(); } }), {threshold: .3}).observe(wf);
  }

  /* ---------- modules & live endpoint pings ---------- */
  const PLAN_BODY = {load: "HAY_POINT", disch: "PARADIP", volume: 900000, duration: 13, lead: 3};
  const MODS = [
    {ico: "⛴", t: "Plan a Charter", d: "Enter cargo, origin, port and duration. Get the vessel, parcel, COA/TC/spot mix, charter ladder, entry timing and a broker-quote X-ray.", m: "POST", ep: "/api/plan", href: "/app#/plan", body: PLAN_BODY},
    {ico: "⇄", t: "Compare Lanes", d: "Rank every origin into a port, or every port from an origin, by landed $/t with P10-P90. This gives the freight-adjusted FOB break-even for procurement.", m: "POST", ep: "/api/compare", href: "/app#/compare",
      body: {lanes: [{load: "HAY_POINT", disch: "PARADIP"}, {load: "NACALA", disch: "PARADIP"}]}},
    {ico: "▤", t: "Programmes & Ledger", d: "Store SAIL cargo requirements, plan them, and record accept or reject decisions in an audit ledger with printable charter notes and CSV export.", m: "GET", ep: "/api/programmes", href: "/app#/ops"},
    {ico: "⛁", t: "Data Hub", d: "Download the template, upload real weekly freight history, and retrain the forecaster and backtest on it with live progress.", m: "GET", ep: "/api/data/status", href: "/app#/data"},
    {ico: "∿", t: "Market Forecast", d: "P10-P90 fans for 4 vessel classes over 1-26 weeks, with ensemble weights, accuracy vs random walk and explainability.", m: "GET", ep: "/api/forecast/Capesize", href: "/app#/forecast"},
    {ico: "⚓", t: "Port-Vessel Feasibility", d: "Draft, LOA, beam, stockyard and chokepoint checks for every class, plus the all-port matrix and two-port discharge.", m: "GET", ep: "/api/feasibility", href: "/app#/feasibility"},
    {ico: "⚠", t: "Risk & Early Warnings", d: "Volatility regime, spike/crash odds, turning points, congestion outlook and news events mapped to lanes.", m: "GET", ep: "/api/risk", href: "/app#/risk"},
    {ico: "⟲", t: "Idle & Deadheading", d: "Triangulation backhauls, relets, JIT slow-steaming and laycan spacing for period tonnage.", m: "GET", ep: "/api/idle", href: "/app#/idle"},
    {ico: "✓", t: "Backtest Proof", d: "Walk-forward savings vs daily spot, oracle capture, ablations, placebo world and decision-focused tuning.", m: "GET", ep: "/api/backtest", href: "/app#/backtest"},
    {ico: "◎", t: "Network View", d: "Best class and landed $/t for every origin × East-Coast port, shown on the live lane map.", m: "GET", ep: "/api/network", href: "/app#/network"},
    {ico: "{ }", t: "API Explorer", d: "Every endpoint in one place. Try requests live and inspect the JSON.", m: "GET", ep: "/api", href: "/app#/api"},
    {ico: "⌘", t: "Swagger / OpenAPI", d: "Auto-generated interactive documentation with request schemas.", m: "GET", ep: "/openapi.json", href: "/docs"},
  ];
  function buildModules() {
    $("#modGrid").innerHTML = MODS.map((m, i) => `<a class="mod" href="${m.href}" data-reveal style="--i:${i % 3}"><div class="top"><span class="ico">${m.ico}</span><span class="lat" id="lat${i}"><span class="dot warn"></span>pinging…</span></div>
      <h3>${m.t}</h3><p>${m.d}</p><div class="ep"><span class="m ${m.m === "POST" ? "post" : ""}">${m.m}</span>${m.ep}</div><span class="go">Open →</span></a>`).join("");
    $$(".mod").forEach(el => { spotlight(el, false); rev.observe(el); });
    MODS.forEach((m, i) => {
      const st = performance.now();
      fetch(m.ep, m.body ? {method: "POST", headers: {"Content-Type": "application/json"}, body: JSON.stringify(m.body)} : {})
        .then(r => { const ms = Math.round(performance.now() - st); $("#lat" + i).innerHTML = `<span class="dot ${r.ok ? "" : "bad"}"></span>${r.ok ? "live" : "HTTP " + r.status} · ${ms} ms`; })
        .catch(() => { $("#lat" + i).innerHTML = `<span class="dot bad"></span>offline`; });
    });
  }
  addEventListener("keydown", e => { if (e.key === "Enter" && !["INPUT", "BUTTON", "A"].includes(document.activeElement.tagName)) location.href = "/app"; });
  onScroll();
})();
