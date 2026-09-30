/* FreightSaarthi SeaMap - dot-matrix nautical map of the Indian Ocean trade with animated coal lanes.
   Coastlines are deliberately coarse (stylised); lanes follow realistic routings (Torres, Bass Strait,
   Mozambique Channel, Malacca, Luzon, Red Sea/Suez, Cape of Good Hope). No external data needed. */
(function () {
  const LAND = [
    // Africa (stylised)
    [[-17,21],[-10,30],[10,37],[32,31.3],[33.2,28],[35,24],[38,17.5],[43.2,11.3],[51.2,11.2],[48,5],[45,2],[41,-3],[40,-10],[40.5,-15],[35.5,-23.5],[32.8,-28],[27,-34],[20,-35],[18,-30],[12,-18],[13,-6],[9,3],[-8,5],[-17,14]],
    // Arabia
    [[34.8,28.5],[35.5,33],[40,32],[48,30],[50,26],[51.5,24],[56.3,26.3],[59.8,22.5],[57.5,19],[52,16],[45,13.1],[43.2,13.3],[42,16.5],[39,21],[37,25]],
    // Asia mainland incl. India
    [[26,40],[30,46],[40,47],[50,47],[60,50],[70,50],[90,50],[110,50],[130,50],[142,50],[141,45],[135.5,43.5],[132,43],[129.5,41],[129.3,35.2],[126.3,34.5],[126.6,37.7],[124.5,39.8],[121,39],[122.2,37.4],[119,35],[121.9,31.5],[121.6,28.5],[119.5,25.5],[117,23.4],[113.5,22.2],[110.5,21],[109.6,18.2],[108.7,15.5],[109.2,12.2],[107,10.4],[105,8.7],[104.7,10.4],[102.5,12.2],[100.9,13.4],[99.3,10.8],[100.4,6.5],[101.3,2.8],[103.5,1.3],[104.3,1.4],[103.4,4],[102.2,6.2],[99.8,9],[98.4,8],[98.6,11],[97.6,16.5],[94.4,16],[94.2,19.5],[92.3,21],[91.8,22.5],[90.5,22],[89,21.8],[88.2,21.7],[87,21],[86.7,20.2],[85,19.2],[84,18.2],[82.3,16.9],[81,15.6],[80.2,13.6],[80.2,12.4],[79.8,10.3],[79,9.2],[78.1,8.1],[77.3,8.1],[76.3,9.8],[75.5,12],[74.4,14.5],[73.2,17],[72.8,19],[72.6,21.5],[70.8,20.8],[69,22.3],[68.4,23.5],[67,24.8],[62,25.2],[57.3,25.6],[56.4,27.1],[52,27.8],[49,30],[48,31],[44,37],[36,36.8],[30,36.6],[26,38]],
    [[79.8,9.8],[81.9,7.5],[81.2,6.1],[80,6],[79.8,8]],                                        // Sri Lanka
    [[95.3,5.6],[97.5,5.2],[100.3,2.5],[104,-1],[106,-3.5],[105.8,-5.9],[102.3,-4],[100,-1],[98.7,1.7],[95.5,4.5]], // Sumatra
    [[105.2,-6.8],[108,-6.3],[111,-6.4],[114.5,-7.7],[114.4,-8.7],[111,-8.2],[106.5,-7.4]],    // Java
    [[115.2,-8.1],[116.5,-8.3],[118.5,-8.5],[119,-8.8],[117,-9],[115.4,-8.8]],                 // Lesser Sunda
    [[119.5,-8.6],[124.5,-8.2],[127,-8.4],[125,-9.6],[120.5,-10.2]],
    [[109,1.5],[110,2],[113,3.2],[116,6.5],[119,5.2],[118,1],[117.9,-0.8],[116.5,-2.4],[116,-3.9],[114.5,-3.6],[111.5,-3],[110,-1.5]], // Borneo
    [[119,-1],[120.5,0.5],[124.8,1.5],[121,-1.5],[123,-4],[122,-5.5],[120.5,-5.5],[119.5,-3.5]], // Sulawesi
    [[131,-1],[135,-3.3],[141,-2.6],[145.5,-5],[150,-10.5],[147,-10.2],[143,-9],[141,-9.2],[138,-8.3],[137.5,-5.1],[132,-4]], // New Guinea
    [[120,18.5],[122.3,18.4],[122,14],[124,12.5],[126,7.5],[125,6],[122,7],[121,11],[120,14.5]], // Philippines
    [[130,31],[131.5,34],[135,35.5],[140,38],[141.5,41.5],[140,35.5],[137,34.5],[133,33.5]],   // Japan
    [[140,42],[143.5,42.5],[145.5,43.5],[142,45.5],[141.3,43.2]],
    [[120.2,22.8],[121,25.2],[121.9,24.8],[120.9,22]],                                         // Taiwan
    [[113.5,-22],[114,-26],[115,-34],[117.5,-35],[123,-33.8],[129,-31.6],[131,-31.5],[135,-34.5],[138,-35.5],[140,-38],[144,-38.5],[146.5,-39],[150,-37.5],[151,-34],[153.2,-30],[153.5,-28],[152.7,-25],[150.8,-22.5],[149.2,-21.1],[146,-18.5],[145.4,-14.8],[143.5,-14],[142.5,-10.7],[141.5,-13],[141.5,-16.8],[139.5,-17.4],[136.7,-15.9],[136.9,-12.2],[132.5,-11.3],[130,-13.3],[129.3,-15],[126.5,-13.9],[124,-16.5],[122.2,-18],[121,-19.5],[117,-20.7]], // Australia
    [[144.6,-40.7],[148.3,-40.9],[147.8,-43.2],[146,-43.6]],                                   // Tasmania
    [[49.3,-12],[50.4,-15.5],[47.1,-24.9],[45,-25.3],[43.3,-22],[44.2,-16.2],[47,-15]],        // Madagascar
    [[20,35],[28,36.2],[28,41],[23,40.5],[20,40]],                                             // Aegean-ish
  ];

  const PORTS = {
    PARADIP: {ll:[86.68,20.26], name:"Paradip", role:"dest"}, DHAMRA: {ll:[86.96,20.82], name:"Dhamra", role:"dest"},
    HALDIA: {ll:[88.06,22.03], name:"Haldia", role:"dest"}, SANDHEADS: {ll:[88.25,21.0], name:"Sandheads", role:"dest"},
    GOPALPUR: {ll:[84.97,19.28], name:"Gopalpur", role:"dest"}, VIZAG: {ll:[83.3,17.69], name:"Vizag", role:"dest"},
    GANGAVARAM: {ll:[83.23,17.5], name:"Gangavaram", role:"dest"},
    HAY_POINT: {ll:[149.3,-21.28], name:"Hay Point", role:"origin", country:"Australia"},
    GLADSTONE: {ll:[151.3,-23.85], name:"Gladstone", role:"origin", country:"Australia"},
    NEWCASTLE: {ll:[151.78,-32.92], name:"Newcastle", role:"origin", country:"Australia"},
    NACALA: {ll:[40.67,-14.54], name:"Nacala", role:"origin", country:"Mozambique"},
    BEIRA: {ll:[34.84,-19.83], name:"Beira", role:"origin", country:"Mozambique"},
    MUARA_BERAU: {ll:[117.6,-0.35], name:"Muara Berau", role:"origin", country:"Indonesia"},
    TANJUNG_BARA: {ll:[117.63,0.9], name:"Tanjung Bara", role:"origin", country:"Indonesia"},
    VOSTOCHNY: {ll:[133.06,42.75], name:"Vostochny", role:"origin", country:"Russia"},
    HAMPTON_RDS: {ll:[25,33.6], name:"US East Coast ▸ Suez", role:"origin", country:"USA", virtual:true},
    UST_LUGA: {ll:[26,34.4], name:"Baltic ▸ Suez", role:"origin", country:"Russia", virtual:true},
  };
  const CHOKE = {TORRES:{ll:[142.3,-10.6],name:"Torres Strait"}, SUEZ:{ll:[32.5,30.0],name:"Suez"}, BAB:{ll:[43.4,12.6],name:"Bab-el-Mandeb"},
    MALACCA:{ll:[100.8,2.9],name:"Malacca"}, LUZON:{ll:[121.2,20.5],name:"Luzon Str."}, BASS:{ll:[146,-39.6],name:"Bass Strait"}};

  const BAY = [85.6,12.5];
  const QLD = [[150.5,-17],[146.5,-13.5],[143.6,-10.9],[141,-10.2],[136,-10.3],[128,-11.9],[120,-12.6],[110,-11],[100,-5],[94.8,2],[90.5,7.5],BAY];
  const EAST_AFR = [[55,-5],[65,0],[75,4],[80.5,5.1],[84,8],BAY];
  const MALACCA_W = [[104.5,1.3],[101.6,2.7],[98.6,5],[95.5,6.9],[90,10],BAY];
  const SUEZ_R = [[32.4,31.2],[32.6,29.8],[33.9,27.4],[36.6,23.4],[39.6,18],[42.4,14.2],[43.5,12.4],[46,12.3],[51.5,12.7],[58,12],[68,8.5],[76,6],[80.5,5.1],[84,8],BAY];
  const LANES = {
    HAY_POINT: [PORTS.HAY_POINT.ll, ...QLD],
    GLADSTONE: [PORTS.GLADSTONE.ll, [153,-21], ...QLD],
    NEWCASTLE: [PORTS.NEWCASTLE.ll, [152.6,-36], [149,-38.9], [146,-39.6], [141,-39.2], [135,-36.8], [125,-35.6], [115,-36], [110.5,-31], [106,-20], [98,-8], [93,2], [89,8.5], BAY],
    NACALA: [PORTS.NACALA.ll, [45,-10.8], ...EAST_AFR],
    BEIRA: [PORTS.BEIRA.ll, [37.6,-19], [41,-15.6], [43,-12], [45,-10.8], ...EAST_AFR],
    MUARA_BERAU: [PORTS.MUARA_BERAU.ll, [118.9,-2.5], [118.4,-5], [113,-5.1], [108.4,-3.4], [106.6,0], ...MALACCA_W],
    TANJUNG_BARA: [PORTS.TANJUNG_BARA.ll, [118.9,-0.8], [118.9,-2.5], [118.4,-5], [113,-5.1], [108.4,-3.4], [106.6,0], ...MALACCA_W],
    VOSTOCHNY: [PORTS.VOSTOCHNY.ll, [131,38.5], [129.6,34.3], [126,31], [123.3,24.5], [121.2,20.5], [115,15], [109.8,10], [106,5], ...MALACCA_W],
    HAMPTON_RDS: [PORTS.HAMPTON_RDS.ll, ...SUEZ_R],
    UST_LUGA: [PORTS.UST_LUGA.ll, [29,33.2], ...SUEZ_R.slice(1)],
  };
  const CAPE_ALT = [[18,-40],[28,-37],[38,-32],[45,-27],[52,-18],[60,-8],[70,0],[78,4],[80.5,5.1],[84,8],BAY];
  const FINAL = {
    PARADIP: [[86.9,17],[86.68,20.26]], DHAMRA: [[87.2,17.5],[86.96,20.82]], HALDIA: [[87.9,18],[88.25,21.0],[88.06,22.03]],
    SANDHEADS: [[87.9,18],[88.25,21.0]], GOPALPUR: [[85.6,16.5],[84.97,19.28]], VIZAG: [[84.2,15.2],[83.3,17.69]],
    GANGAVARAM: [[84,15],[83.23,17.5]],
  };
  const CLASS_COLOR = {Capesize:"#38bdf8", Panamax:"#2dd4bf", Supramax:"#fbbf24", Handysize:"#c4b5fd"};
  const LANE_DEFAULT_DEST = {HAY_POINT:"PARADIP", GLADSTONE:"DHAMRA", NEWCASTLE:"GANGAVARAM", NACALA:"PARADIP", BEIRA:"HALDIA",
    MUARA_BERAU:"VIZAG", TANJUNG_BARA:"PARADIP", VOSTOCHNY:"DHAMRA", HAMPTON_RDS:"PARADIP", UST_LUGA:"GANGAVARAM"};
  const LANE_CLASS = {HAY_POINT:"Capesize", GLADSTONE:"Capesize", NEWCASTLE:"Panamax", NACALA:"Capesize", BEIRA:"Supramax",
    MUARA_BERAU:"Panamax", TANJUNG_BARA:"Supramax", VOSTOCHNY:"Panamax", HAMPTON_RDS:"Capesize", UST_LUGA:"Panamax"};

  function pip(pt, poly) {
    let x = pt[0], y = pt[1], inside = false;
    for (let i = 0, j = poly.length - 1; i < poly.length; j = i++) {
      const xi = poly[i][0], yi = poly[i][1], xj = poly[j][0], yj = poly[j][1];
      if (((yi > y) !== (yj > y)) && (x < (xj - xi) * (y - yi) / (yj - yi) + xi)) inside = !inside;
    }
    return inside;
  }
  function catmull(pts, seg = 10) {
    const out = [];
    for (let i = 0; i < pts.length - 1; i++) {
      const p0 = pts[i - 1] || pts[i], p1 = pts[i], p2 = pts[i + 1], p3 = pts[i + 2] || p2;
      for (let t = 0; t < seg; t++) {
        const s = t / seg, s2 = s * s, s3 = s2 * s;
        out.push([0.5 * ((2 * p1[0]) + (-p0[0] + p2[0]) * s + (2 * p0[0] - 5 * p1[0] + 4 * p2[0] - p3[0]) * s2 + (-p0[0] + 3 * p1[0] - 3 * p2[0] + p3[0]) * s3),
                  0.5 * ((2 * p1[1]) + (-p0[1] + p2[1]) * s + (2 * p0[1] - 5 * p1[1] + 4 * p2[1] - p3[1]) * s2 + (-p0[1] + 3 * p1[1] - 3 * p2[1] + p3[1]) * s3)]);
      }
    }
    out.push(pts[pts.length - 1]);
    return out;
  }

  class SeaMap {
    constructor(canvas, opts = {}) {
      this.c = canvas; this.ctx = canvas.getContext("2d");
      this.o = Object.assign({bounds: [25, 160, -44, 47], fit: "cover", focus: [96, 4], dotStep: 1.15, ships: true,
        shipsPerLane: 3, labels: true, graticule: true, parallax: true, capeAlt: true, laneColor: null, laneWidth: null,
        highlight: null, dest: null, speed: 1, tooltip: null}, opts);
      this.mouse = [0, 0]; this.par = [0, 0]; this.t0 = performance.now(); this.hover = null; this.running = false;
      this.reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
      this._onResize = () => this.resize(); window.addEventListener("resize", this._onResize);
      canvas.addEventListener("mousemove", e => { const r = canvas.getBoundingClientRect(); this.mouse = [(e.clientX - r.left) / r.width - .5, (e.clientY - r.top) / r.height - .5]; this.mx = e.clientX - r.left; this.my = e.clientY - r.top; });
      canvas.addEventListener("mouseleave", () => { this.mx = null; });
      canvas.addEventListener("click", () => { if (this.hover && this.o.onClick) this.o.onClick(this.hover); });
      this.resize();
    }
    setOptions(o) { Object.assign(this.o, o); this.buildLanes(); }
    proj(ll) { return [(ll[0] - this.lon0) * this.k + this.ox, (this.lat1 - ll[1]) * this.k + this.oy]; }
    resize() {
      const dpr = Math.min(window.devicePixelRatio || 1, 2), r = this.c.getBoundingClientRect();
      this.W = Math.max(r.width, 10); this.Hh = Math.max(r.height, 10);
      this.c.width = this.W * dpr; this.c.height = this.Hh * dpr; this.ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      const [lo0, lo1, la0, la1] = this.o.bounds; this.lon0 = lo0; this.lat1 = la1;
      const kx = this.W / (lo1 - lo0), ky = this.Hh / (la1 - la0);
      this.k = this.o.fit === "cover" ? Math.max(kx, ky) : Math.min(kx, ky) * (this.o.zoom || 1);
      const fx = (this.o.focus[0] - lo0) * this.k, fy = (la1 - this.o.focus[1]) * this.k;
      const anchor = this.o.anchor || [0.56, 0.5];
      if (this.o.fit === "contain") { this.ox = (this.W - (lo1 - lo0) * this.k) / 2; this.oy = (this.Hh - (la1 - la0) * this.k) / 2; }
      else { this.ox = this.W * anchor[0] - fx; this.oy = this.Hh * anchor[1] - fy; }
      this.buildDots(); this.buildLanes();
    }
    buildDots() {
      const off = document.createElement("canvas"), dpr = Math.min(window.devicePixelRatio || 1, 2);
      off.width = this.W * dpr; off.height = this.Hh * dpr; const g = off.getContext("2d"); g.setTransform(dpr, 0, 0, dpr, 0, 0);
      const [lo0, lo1, la0, la1] = this.o.bounds, s = this.o.dotStep;
      if (this.o.graticule) {
        g.strokeStyle = "rgba(125,180,255,0.06)"; g.lineWidth = 1; g.font = "10px 'JetBrains Mono', monospace"; g.fillStyle = "rgba(160,200,255,0.25)";
        for (let lon = Math.ceil(lo0 / 10) * 10; lon <= lo1; lon += 10) { const [x] = this.proj([lon, 0]); g.beginPath(); g.moveTo(x, 0); g.lineTo(x, this.Hh); g.stroke(); g.fillText(lon + "°E", x + 3, this.Hh - 8); }
        for (let lat = Math.ceil(la0 / 10) * 10; lat <= la1; lat += 10) { const [, y] = this.proj([0, lat]); g.beginPath(); g.moveTo(0, y); g.lineTo(this.W, y); g.stroke(); g.fillText((lat >= 0 ? lat + "°N" : -lat + "°S"), 6, y - 3); }
      }
      this.dots = [];
      for (let lon = lo0 - 10; lon <= lo1 + 10; lon += s) for (let lat = la0 - 10; lat <= la1 + 10; lat += s) {
        if (LAND.some(p => pip([lon, lat], p))) {
          const [x, y] = this.proj([lon, lat]);
          if (x < -10 || y < -10 || x > this.W + 10 || y > this.Hh + 10) continue;
          const india = lon > 68 && lon < 92 && lat > 7 && lat < 30;
          g.fillStyle = india ? "rgba(251,191,36,0.62)" : "rgba(125,180,255,0.40)";
          g.beginPath(); g.arc(x, y, Math.max(1.1, this.k * s * 0.21), 0, 6.283); g.fill();
          if (Math.random() < 0.03) this.dots.push([x, y, Math.random() * 6.28]);
        }
      }
      this.base = off;
    }
    buildLanes() {
      this.lanes = [];
      for (const [org, pts0] of Object.entries(LANES)) {
        const dest = this.o.dest || LANE_DEFAULT_DEST[org];
        const pts = catmull([...pts0, ...FINAL[dest]].map(ll => this.proj(ll)), 8);
        const L = [0]; for (let i = 1; i < pts.length; i++) L.push(L[i - 1] + Math.hypot(pts[i][0] - pts[i - 1][0], pts[i][1] - pts[i - 1][1]));
        const cls = LANE_CLASS[org];
        const ships = []; for (let i = 0; i < this.o.shipsPerLane; i++) ships.push({off: (i + Math.random() * 0.5) / this.o.shipsPerLane, v: 0.018 + Math.random() * 0.012});
        this.lanes.push({org, dest, pts, L, len: L[L.length - 1], cls, ships});
      }
      this.cape = catmull([...CAPE_ALT, ...FINAL.PARADIP].map(ll => this.proj(ll)), 8);
    }
    at(l, f) {
      const d = f * l.len; let i = 1; while (i < l.L.length - 1 && l.L[i] < d) i++;
      const a = l.pts[i - 1], b = l.pts[i], seg = (l.L[i] - l.L[i - 1]) || 1, u = (d - l.L[i - 1]) / seg;
      return [a[0] + (b[0] - a[0]) * u, a[1] + (b[1] - a[1]) * u, Math.atan2(b[1] - a[1], b[0] - a[0])];
    }
    start() { if (this.running) return; this.running = true; const loop = now => { if (!this.running) return; this.draw(now); this.raf = requestAnimationFrame(loop); }; this.raf = requestAnimationFrame(loop); }
    stop() { this.running = false; cancelAnimationFrame(this.raf); }
    destroy() { this.stop(); window.removeEventListener("resize", this._onResize); }
    draw(now) {
      const g = this.ctx, t = (now - this.t0) / 1000 * (this.reduced ? 0.15 : 1) * this.o.speed;
      if (this.o.parallax) { this.par[0] += (this.mouse[0] * -18 - this.par[0]) * 0.05; this.par[1] += (this.mouse[1] * -12 - this.par[1]) * 0.05; }
      g.clearRect(0, 0, this.W, this.Hh); g.save(); g.translate(this.par[0], this.par[1]);
      g.drawImage(this.base, 0, 0, this.W, this.Hh);
      for (const d of this.dots) { const a = 0.35 + 0.35 * Math.sin(t * 1.3 + d[2]); g.fillStyle = `rgba(186,230,253,${a})`; g.beginPath(); g.arc(d[0], d[1], 1.4, 0, 6.283); g.fill(); }
      // Cape of Good Hope alternative (Red Sea disruption)
      if (this.o.capeAlt) { g.setLineDash([3, 7]); g.lineDashOffset = -t * 12; g.strokeStyle = "rgba(251,113,133,0.35)"; g.lineWidth = 1.2; g.beginPath(); this.cape.forEach((p, i) => i ? g.lineTo(p[0], p[1]) : g.moveTo(p[0], p[1])); g.stroke(); g.setLineDash([]); }
      // lanes
      for (const l of this.lanes) {
        const hl = this.o.highlight, dim = hl && hl !== l.org;
        const col = this.o.laneColor ? this.o.laneColor(l) : "rgba(56,189,248,0.28)";
        if (!col) continue;
        g.setLineDash([6, 8]); g.lineDashOffset = -t * 20; g.strokeStyle = dim ? "rgba(148,163,184,0.10)" : col;
        g.lineWidth = (this.o.laneWidth ? this.o.laneWidth(l) : 1.3) * (hl === l.org ? 1.8 : 1);
        g.beginPath(); l.pts.forEach((p, i) => i ? g.lineTo(p[0], p[1]) : g.moveTo(p[0], p[1])); g.stroke(); g.setLineDash([]);
        if (!this.o.ships || dim) continue;
        for (const s of l.ships) {
          const f = (s.off + t * s.v * (900 / Math.max(l.len, 300))) % 1;
          const fade = Math.min(1, f * 12, (1 - f) * 12);
          // trail
          const tr = 14; g.lineWidth = 2;
          for (let k = 0; k < tr; k++) { const f2 = f - k * 0.004; if (f2 < 0) break; const p = this.at(l, f2), q = this.at(l, Math.max(0, f2 - 0.004)); g.strokeStyle = hexA(CLASS_COLOR[l.cls], (1 - k / tr) * 0.55 * fade); g.beginPath(); g.moveTo(p[0], p[1]); g.lineTo(q[0], q[1]); g.stroke(); }
          const [x, y, ang] = this.at(l, f);
          g.save(); g.translate(x, y); g.rotate(ang); g.shadowColor = CLASS_COLOR[l.cls]; g.shadowBlur = 12; g.fillStyle = hexA(CLASS_COLOR[l.cls], fade);
          g.beginPath(); g.moveTo(7, 0); g.lineTo(3, -2.8); g.lineTo(-6, -2.8); g.lineTo(-6, 2.8); g.lineTo(3, 2.8); g.closePath(); g.fill(); g.restore();
        }
      }
      // chokepoints
      g.font = "10px 'JetBrains Mono', monospace";
      for (const c of Object.values(CHOKE)) { const [x, y] = this.proj(c.ll); g.strokeStyle = "rgba(251,191,36,0.7)"; g.lineWidth = 1; g.beginPath(); g.moveTo(x, y - 4); g.lineTo(x + 4, y); g.lineTo(x, y + 4); g.lineTo(x - 4, y); g.closePath(); g.stroke(); if (this.o.labels) { g.fillStyle = "rgba(251,191,36,0.55)"; g.fillText(c.name, x + 7, y + 3); } }
      // ports
      this.hover = null;
      for (const [code, p] of Object.entries(PORTS)) {
        const [x, y] = this.proj(p.ll), dest = p.role === "dest";
        const ph = (((t * 0.8 + x * 0.01) % 1) + 1) % 1;   // keep in [0,1) even for off-canvas (negative x) ports
        g.strokeStyle = dest ? `rgba(251,191,36,${0.8 * (1 - ph)})` : `rgba(56,189,248,${0.7 * (1 - ph)})`; g.lineWidth = 1.2;
        g.beginPath(); g.arc(x, y, 3 + ph * (dest ? 16 : 12), 0, 6.283); g.stroke();
        g.fillStyle = dest ? "#fbbf24" : "#7dd3fc"; g.beginPath(); g.arc(x, y, dest ? 3.2 : 2.6, 0, 6.283); g.fill();
        const hov = this.mx != null && Math.hypot(this.mx - x - this.par[0], this.my - y - this.par[1]) < 12;
        if (hov) this.hover = code;
        if (this.o.labels && (!dest || ["PARADIP", "HALDIA", "VIZAG", "DHAMRA"].includes(code) || hov)) {
          g.fillStyle = hov ? "#fff" : (dest ? "rgba(253,230,138,0.85)" : "rgba(186,230,253,0.75)");
          g.font = (hov ? "600 12px" : "11px") + " 'Space Grotesk', system-ui, sans-serif";
          const lx = dest ? (code === "VIZAG" ? x - 44 : x + 9) : x + 8;
          g.fillText(p.name, lx, y + (code === "DHAMRA" ? -6 : code === "HALDIA" ? -4 : 4));
        }
      }
      g.restore();
      if (this.hover && this.o.tooltip) this.o.tooltip(this.hover, this.mx, this.my); else if (this.o.tooltip) this.o.tooltip(null);
    }
  }
  function hexA(hex, a) { const n = parseInt(hex.slice(1), 16); return `rgba(${n >> 16},${(n >> 8) & 255},${n & 255},${Math.max(0, Math.min(1, a))})`; }
  window.SeaMap = SeaMap; window.GEO = {PORTS, LANES, CLASS_COLOR, LANE_CLASS};
})();
