/* "Will it fit?" - animated side-view of the 4 bulk-carrier classes against a port's draft/LOA/beam.
   Cargo at draft = DWT - TPC*100*(T_design - T_allowed) - constants  (same formula as saarthi/physics.py) */
(function () {
  const ORDER = ["Handysize", "Supramax", "Panamax", "Capesize"];
  const COLOR = {Capesize: "#38bdf8", Panamax: "#2dd4bf", Supramax: "#fbbf24", Handysize: "#c4b5fd"};
  const WL = 185, PX_M = 7.5, XS = 0.84;          // waterline y, px per metre of depth, px per metre of length

  function fit(v, port, monsoon) {
    if (v.loa_m > port.max_loa_m) return {ok: false, why: `LOA ${v.loa_m} m > ${port.max_loa_m} m`, draft: v.design_draft_m, cargo: 0};
    if (v.beam_m > port.max_beam_m) return {ok: false, why: `beam ${v.beam_m} m > ${port.max_beam_m} m`, draft: v.design_draft_m, cargo: 0};
    const allowed = port.max_draft_m + (monsoon ? (port.monsoon_draft_delta || 0) : 0);
    const draft = Math.min(v.design_draft_m, allowed);
    const cargo = v.dwt - v.tpc * 100 * Math.max(0, v.design_draft_m - allowed) - v.constants_t;
    const cap = v.dwt - v.constants_t, util = cargo / cap;
    if (util < 0.45) return {ok: false, why: `only ${Math.round(Math.max(cargo, 0) / 1000)}k t at ${allowed.toFixed(1)} m - uneconomic`, draft, cargo: Math.max(cargo, 0), util};
    return {ok: true, part: util < 0.999, draft, cargo, util, why: util < 0.999 ? `part-laden to ${allowed.toFixed(1)} m` : "full deadweight"};
  }

  function hull(len, draft, free, loadF, col, id) {
    // side profile: flat bottom, raked bow at right, transom at left; hatches with coal heaps
    const bow = len * 0.1, top = -free, bottom = draft * PX_M;
    const d = `M0 ${top} L${len - bow * 0.4} ${top} Q${len} ${top} ${len} ${top + 8} L${len - bow} ${bottom} L${bow * 0.35} ${bottom} Q0 ${bottom} 0 ${bottom - 10} Z`;
    let s = `<clipPath id="hc-${id}"><path d="${d}"/></clipPath><path d="${d}" fill="#0f1b2d"/>`;
    s += `<rect x="0" y="1" width="${len}" height="${bottom + 2}" fill="rgba(190,40,50,.42)" clip-path="url(#hc-${id})"/>`; // antifouling below waterline
    s += `<path d="${d}" fill="none" stroke="${col}" stroke-width="1.4"/>`;
    s += `<rect x="4" y="${top - 26}" width="${Math.min(34, len * 0.14)}" height="26" rx="2" fill="#e2e8f0" opacity=".9"/><rect x="${6}" y="${top - 34}" width="10" height="9" fill="#94a3b8"/>`;
    const nh = len > 250 ? 9 : len > 190 ? 7 : 5, x0 = len * 0.2, w = (len * 0.72) / nh;
    for (let i = 0; i < nh; i++) {
      const hx = x0 + i * w + 2;
      s += `<rect x="${hx}" y="${top - 6}" width="${w - 5}" height="6" fill="#1e293b" stroke="${col}" stroke-opacity=".5"/>`;
      const heap = 3 + 9 * loadF;
      s += `<path class="coal" d="M${hx + 1} ${top - 6} Q${hx + (w - 5) / 2} ${top - 6 - heap * 2} ${hx + w - 6} ${top - 6} Z" fill="#111" stroke="#334155" stroke-width=".6" opacity="${loadF > 0 ? 1 : 0}"/>`;
    }
    return s;
  }

  class FitScene {
    constructor(el, meta) { this.el = el; this.meta = meta; this.port = "PARADIP"; this.monsoon = false; this.build(); }
    build() {
      const V = this.meta.vessels;
      let x = 30, groups = "";
      ORDER.forEach(c => {
        const v = V[c], len = v.loa_m * XS;
        groups += `<g class="ship" id="fs-${c}" data-x="${x}" style="transform:translate(${x}px,${WL}px)"><g class="hull"></g>
          <text class="lbl" x="${len / 2}" y="-84" text-anchor="middle">${c}</text>
          <text class="sub" x="${len / 2}" y="-68" text-anchor="middle"></text>
          <line class="dline" x1="${len + 6}" x2="${len + 6}" y1="0" y2="0" stroke="${COLOR[c]}" stroke-dasharray="2 3"/></g>`;
        x += len + 26;
      });
      this.el.innerHTML = `<svg viewBox="0 0 1000 365" class="fit-svg" preserveAspectRatio="xMidYMid meet">
        <defs><linearGradient id="fsSea" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#0b3a5c" stop-opacity=".95"/><stop offset="1" stop-color="#041526"/></linearGradient>
        <linearGradient id="fsSand" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#8a6d3b"/><stop offset="1" stop-color="#3b2f1c"/></linearGradient>
        <pattern id="fsRip" width="40" height="8" patternUnits="userSpaceOnUse"><path d="M0 4 Q10 0 20 4 T40 4" stroke="rgba(255,255,255,.08)" fill="none"/></pattern></defs>
        <rect x="0" y="${WL}" width="1000" height="${365 - WL}" fill="url(#fsSea)"/>
        <rect x="0" y="${WL}" width="1000" height="${365 - WL}" fill="url(#fsRip)" class="rip"/>
        <path class="wave" d="M0 ${WL} Q25 ${WL - 4} 50 ${WL} T100 ${WL} T150 ${WL} T200 ${WL} T250 ${WL} T300 ${WL} T350 ${WL} T400 ${WL} T450 ${WL} T500 ${WL} T550 ${WL} T600 ${WL} T650 ${WL} T700 ${WL} T750 ${WL} T800 ${WL} T850 ${WL} T900 ${WL} T950 ${WL} T1000 ${WL} T1050 ${WL} T1100 ${WL}" stroke="#7dd3fc" stroke-opacity=".6" fill="none"/>
        <g class="depth-scale">${[0, 5, 10, 15, 20].map(m => `<text x="992" y="${WL + m * PX_M + 4}" text-anchor="end">${m} m</text><line x1="960" x2="1000" y1="${WL + m * PX_M}" y2="${WL + m * PX_M}"/>`).join("")}</g>
        ${groups}
        <g class="seabed" style="transform:translateY(${WL + 15 * PX_M}px)"><path d="M0 0 Q120 -6 250 2 T520 -2 T780 4 T1000 0 L1000 300 L0 300 Z" fill="url(#fsSand)"/>
          <line x1="0" x2="1000" y1="0" y2="0" stroke="#fbbf24" stroke-dasharray="6 5"/><text class="draftlbl" x="12" y="20"></text></g>
      </svg>`;
      this.update();
    }
    set(port, monsoon) { this.port = port; this.monsoon = !!monsoon; this.update(); }
    results() { const P = this.meta.discharge[this.port]; return ORDER.map(c => ({cls: c, ...fit(this.meta.vessels[c], P, this.monsoon)})); }
    update() {
      const P = this.meta.discharge[this.port], svg = this.el.querySelector("svg");
      const allowed = P.max_draft_m + (this.monsoon ? (P.monsoon_draft_delta || 0) : 0);
      const bed = svg.querySelector(".seabed"); bed.style.transform = `translateY(${WL + allowed * PX_M}px)`;
      bed.querySelector(".draftlbl").textContent = `${P.name.split(" (")[0]} · max arrival draft ${allowed.toFixed(1)} m · LOA ≤ ${P.max_loa_m} m · beam ≤ ${P.max_beam_m} m`;
      this.results().forEach(r => {
        const g = svg.querySelector("#fs-" + r.cls), v = this.meta.vessels[r.cls], len = v.loa_m * XS, col = r.ok ? (r.part ? "#fbbf24" : "#34d399") : "#fb7185";
        const loadF = r.ok ? r.util : 0, draft = r.ok ? r.draft : v.design_draft_m * 0.55, free = 12 + (v.design_draft_m - draft) * PX_M * 0.8;
        g.querySelector(".hull").innerHTML = hull(len, draft, free, loadF, COLOR[r.cls], r.cls + Math.random().toString(36).slice(2, 6));
        g.querySelector(".sub").textContent = r.ok ? `${Math.round(r.cargo).toLocaleString("en-IN")} t · ${r.why}` : `✕ ${r.why}`;
        g.querySelector(".sub").setAttribute("fill", col);
        const dl = g.querySelector(".dline"); dl.setAttribute("y2", draft * PX_M);
        g.classList.toggle("nofit", !r.ok);
        g.style.transform = `translate(${g.dataset.x}px, ${WL}px)`;
      });
    }
  }
  window.FitScene = FitScene; window.FIT = {fit, ORDER, COLOR};
})();
