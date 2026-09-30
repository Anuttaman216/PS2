# CLAUDE.md: project context for FreightSaarthi (SIH 2026 · PS 26006)

This file gives an AI coding assistant, or a new developer, everything needed to understand, run and extend this project without the original conversation.

## 1. What this is

**FreightSaarthi** is an intelligent freight-forecasting and charter decision-support system built for **Smart India Hackathon 2026, problem statement 26006** (Ministry of Steel / SAIL). The full problem statement is in [docs/PROBLEM_STATEMENT.md](docs/PROBLEM_STATEMENT.md).

SAIL imports coking coal from Australia, the US, Mozambique, Russia and Indonesia into India's East Coast ports: Paradip, Dhamra, Vizag, Gangavaram, Gopalpur, Haldia and Sagar/Sandheads. Today it books many single **spot** charters after daily market exploration. The system moves it to **short/medium-term multi-voyage contracts** (COA and period time charter) by:
1. forecasting class freight rates (Handysize/Supramax/Panamax/Capesize TCE, $/day) probabilistically for 1-26 weeks;
2. recommending vessel class and parcel size from port and vessel physics (draft, LOA, beam, berth DWT, stockyard, chokepoints, monsoon);
3. optimising the **contract mix and timing** with a two-stage stochastic LP (mean + λ·CVaR), the "Charter Ladder";
4. managing idle time and deadheading (triangulation, relets, JIT slow-steaming, laycan spacing);
5. raising early warnings (volatility, spike/crash odds, congestion, news events → impacted lanes);
6. proving value with an honest **walk-forward backtest** against today's daily-spot practice, including a placebo test.

**Status:** a working full-stack prototype. FastAPI backend with **35 REST endpoints**, SQLite persistence (programmes, decision ledger, events), real-data CSV upload with retraining, and an automated API test suite (`python tests/test_api.py`, 11/11 passing). Frontend: animated landing page plus a 12-page cockpit. The pilot lane is Hay Point (AU) → Paradip; every other origin × port works through the same code. The SIH demo script and judge Q&A are in [docs/DEMO.md](docs/DEMO.md).
**Data:** all market data is **SYNTHETIC** (Baltic indices etc. are licensed), and port/vessel limits are **assumptions** tagged with a `confidence` and a `verify_with` source. Never present the backtest numbers as SAIL's real savings.

The long-form design (candidate approaches, architecture, models, optimiser math, data sources, backtest protocol, phased plan, assumptions and limitations) is in **[docs/DESIGN.md](docs/DESIGN.md)**. Read it before making modelling changes.

## 2. Quick start

```bash
pip install -r requirements.txt          # numpy pandas scipy scikit-learn lightgbm plotly fastapi uvicorn
python run_pipeline.py                   # rebuilds outputs/results.json (~15 min cold; cached afterwards). Optional: results.json is committed.
python serve.py                          # web app on http://localhost:8000  (PORT env var overrides)
python tests/test_api.py                 # end-to-end API tests (temp DB + temp data dir; pytest optional)
python run_pipeline.py --source uploaded # retrain on data/uploaded_market.csv (normally triggered from the Data Hub)
```
* `/` animated landing page · `/app` cockpit SPA · `/api` endpoint catalogue · `/docs` Swagger.
* `python run_pipeline.py --fast` does coarser refits and a smaller tuning grid.
* On Windows, prefix with `PYTHONIOENCODING=utf-8` if a console print fails on unicode (→, ≈).
* `.claude/launch.json` defines the preview config `freightsaarthi` (`python serve.py`, autoPort).
* Python 3.10+ (developed on 3.14). No Node or build step is needed; the frontend is vanilla JS.

## 3. Repository map

```
config/
  vessels.json        4 standard ships (DWT, design draft, LOA, beam, TPC, speeds, fuel, port cost, geared)
  ports.json          7 discharge + 10 load ports + chokepoints; draft/LOA/beam/DWT/rate/waits/monsoon deltas; confidence + verify_with
  routes.json         nm distances load port -> Paradip (+ port offset_nm), routings, alt routings (Cape), _backhaul legs
saarthi/              core models (pure Python)
  config.py           loads JSON (keys starting "_" are stripped; BACKHAUL loaded separately), COMMERCIAL assumptions, PHI_MKT
  synth.py            synthetic worlds: "structured" (regimes, seasonality, leading ballaster/coal signals, episodes) and
                      "martingale" placebo (LEVEL martingale: log-steps carry -var/2 drift); market_forward_log() = owners' consensus forward
  forecast.py         causal features, members GBM-quantile (LightGBM, pooled over classes) + structural ridge + random walk,
                      walk_forward() with online inverse-pinball weights + online CQR conformal bands, interp_quantiles, simulate_paths (Gaussian copula)
  physics.py          check() feasibility (LOA/beam, min draft over load/discharge/chokepoints, stockyard, stem, Torres routing, lighterage),
                      voyage_days, freight_per_t = A*TCE + B*bunker + C, demurrage, inventory, landed_freight, two_port_discharge
  optimizer.py        solve_block(): Charter-Ladder LP (HiGHS via scipy.linprog), entry_timing()
  backtest.py         Lane, Backtest (strategies B0,B1,B2,B3,FS + oracle), summarise() with block-bootstrap CIs
  alerts.py           market + congestion alerts, congestion_outlook (climatology + AR anomaly)
  events.py           news -> typed events (rule extractor; optional Claude structured extraction, model claude-opus-5-5) -> impacted lanes
  idle.py             idle/ballast options (triangulation, relet, JIT slow-steam) + laycan spacing
  data.py             real-data ingestion: validate uploaded weekly CSV (date + tce_<Class> required, drivers optional),
                      proxy-fill missing columns from the synthetic world (reported), estimate market meta, template_csv(), windows() split
run_pipeline.py       end-to-end: worlds -> walk-forward forecasts -> accuracy report (DM test) -> decision-focused tuning (validation)
                      -> test backtest -> ablations (RW forecasts, placebo) -> today's recommendation -> outputs/results.json (+ dashboard.html)
build_dashboard.py    older single-file offline dashboard (outputs/dashboard.html, plotly inlined)
serve.py              uvicorn launcher (PORT env)
webapp/
  server.py           FastAPI: pages (/, /app), /vendor/plotly.min.js (served from the python plotly package = offline), REST API
  planner.py          Planner: server-side plan for ANY lane using results.json scenario paths + physics + the real LP
  ops.py              APIRouter: programmes CRUD + plan, decision ledger (+ HTML charter note, CSV export), event ingestion, compare, data upload
  store.py            SQLite (outputs/freightsaarthi.db; env FREIGHTSAARTHI_DB overrides; auto-created + seeded with 4 demo programmes)
tests/test_api.py     end-to-end tests for every endpoint (sets FREIGHTSAARTHI_DB / FREIGHTSAARTHI_DATA to temp paths)
  static/index.html   landing page;  static/app.html  cockpit shell
  static/css/         base.css (design tokens), landing.css (+ landing-fix.css), app.css
  static/js/          landing.js (preloader, split text, typewriter, scrollytelling, fit scene, counters, endpoint pings), app.js (SPA)
  static/shared/      seamap.js (window.SeaMap: dot-matrix Indian Ocean canvas map, lanes, animated ships, ports, chokepoints),
                      fitscene.js (window.FitScene: SVG ship-vs-port draft simulator)
docs/DESIGN.md        full design & results;  docs/PROBLEM_STATEMENT.md  original PS + task brief;  docs/DEMO.md  SIH demo script + judge Q&A
data/                 (gitignored) uploaded_market.csv from POST /api/data/upload; env FREIGHTSAARTHI_DATA overrides
outputs/              results.json (committed, the app needs it), backtest_blocks.csv, forecast_accuracy.csv, dashboard.html
                      cache/ (pickles, gitignored; delete when model/backtest code changes)
```

## 4. Data flow

```
synth.generate() --df weekly 2014-2026--> forecast.walk_forward() --fc (t,cls,h,q10/q50/q90)-->
   backtest.Backtest.run() --blocks--> summarise()          \
   run_pipeline.todays_recommendation() --paths (300x52x4)--> outputs/results.json --> webapp/server.py load()
                                                                                        -> Planner(R) for /api/plan etc.
```
* `results.json` always holds the **active dataset** (synthetic or uploaded; see `meta.source` / `meta.data_label`). `POST /api/pipeline/run?source=uploaded` retrains on the upload. `source=synthetic&fast=false` restores the canonical demo from cache in about 1 s (fast=true for synthetic would recompute a different, uncached configuration).
* Pipeline caches are keyed per dataset: synthetic uses plain names (`fc_13.pkl` ...), uploads use `up_<sha1>_...`. The placebo world is always synthetic.
* Operational state (programmes, ledger, events) lives in SQLite and is independent of results.json. Ledger rows snapshot the data version they were computed on.
* The **server only reads `outputs/results.json`** at startup (and after `POST /api/pipeline/run`). Python changes need a server restart; static files are served live.
* `results.json` top-level keys: `meta` (asof, data_label, selected_params, tune_log), `vessels`, `discharge`, `load`, `routes`, `chokepoints`, `commercial`, `market` (mu, phi, beta, season[53], woy_now, bunker_now, tce_now), `paths` (150 scenario paths × 52 weeks per class, ints), `congestion` (52-week outlook per port), `fan`, `explain`, `forecast_report`, `forecast_report_placebo`, `backtest` (summary, summary_rw_ablation, summary_placebo, blocks), `recommendation`, `alerts`, `events`, `generalisation`.

## 5. Core formulas

* **Cargo at draft:** `cargo = DWT − TPC·100·max(0, T_design − T_allowed) − constants`, where `T_allowed = min(load sailing draft, discharge arrival draft (+monsoon delta), chokepoint drafts)`. Uneconomic if < 45% of capacity. Stockyard cap is 50% of the yard.
* **Physics translator:** `freight $/t = (TCE·days + fuel·bunker + 2·port_cost)/cargo·(1+commission) = A·TCE + B·bunker + C`. Only class TCEs are forecast; any lane is derived from them.
* **Landed cost** = freight + excess-wait demurrage (class wait multipliers, e.g. Capesize ×1.4 at Paradip) + stockyard carrying cost + lighterage + inland differential.
* **Charter-Ladder LP** (`optimizer.solve_block`): first stage `a` (new COA share @ quote P) and `b` (new TC share). Recourse per scenario: liftings within ±10% (MOLCHOPT), dead-freight at 60% below tolerance, spot remainder. Objective `E[cost] + λ·CVaR_0.9` (Rockafellar-Uryasev). Constraints: total lock ≤ 0.85, weekly step ≤ step_cap, TC ≤ 0.4·min(v). Re-solved weekly in the backtest.
* **COA/TC quotes** come from a *semi-efficient* market forward (mean reversion + public seasonality, **not** our leading signals) with a +1% owner premium. No COA discount is assumed.
* **Spot timing** (optimal stopping): fix at week f in [L−5, L−1] if `TCE_f ≤ (1+δ)·min(median forecast of remaining weeks)`; forced at L−1.
* **Forecast calibration:** online CQR. The band is widened by the empirical 80% quantile of past non-conformity scores, using only targets already realised.

## 6. Current headline results (synthetic world; test 2021-2026H1, 22 quarters, ~20 Mt)

| | $/t | vs B0 | spot fixtures | CVaR90 |
|---|---|---|---|---|
| B0 daily spot, Panamax habit | 17.50 | - | 268 | 20.59 |
| B1 + optimal vessel | 15.54 | −11.2% | 161 | 19.77 |
| B2 + timed spot | 15.29 | −12.6% | 161 | 19.50 |
| B3 70% COA, no model | 17.48 | −0.1% (n.s.) | 101 | 19.79 |
| **FS FreightSaarthi** | **15.06** | **−13.9% (CI 11.4-16.3)** | **54** | **17.73** |
| Oracle | 13.87 | −20.8% | - | 16.17 |

* Most of the saving is **vessel choice** (part-laden Capesize at the assumed Paradip 15.0 m draft). That rests on an assumption and is the first thing to verify with real berth data.
* The placebo (level-martingale) world gives FS vs B1 ≈ −0.3% and timed spot ≈ −0.2%, i.e. no fake edge. FS driven by random-walk forecasts costs $15.51/t.
* Forecast skill vs random walk is +3 to +13% at 1-12 weeks, and 80% coverage is 79-85%.
* Validation tuning selected λ=0, δ=0.03, step 0.35.

## 7. API (35 endpoints; `webapp/server.py` + `webapp/ops.py`)

* **System:** `GET /api` (catalogue) · `/api/health` · `/api/summary` · `POST /api/pipeline/run?source=synthetic|uploaded&fast=bool` (background thread, stage log) · `GET /api/pipeline/status`
* **Market:** `GET /api/ticker` · `/api/meta` · `/api/forecast` · `/api/forecast/{cls}`
* **Decisions:** `POST /api/plan[?save=true]` (body: load, disch, volume, duration 4-48, lead 2-12, stem, risk_lambda, freight_shock, bunker_change, congestion_add, monsoon, avoid_suez, broker_quote) · `POST /api/compare` ({lanes:[{load,disch,volume?}], volume, duration, lead, risk_lambda, monsoon, avoid_suez}) · `POST /api/quote-xray` · `GET /api/feasibility?load&disch&monsoon&stem&avoid_suez` · `GET /api/idle?cls&load&disch&idle_days`
* **Operations:** `GET/POST /api/programmes` · `GET/PUT/DELETE /api/programmes/{id}` · `POST /api/programmes/{id}/plan` (→ ledger, status open→planned) · `GET /api/ledger` · `GET /api/ledger/{id}` · `POST /api/ledger/{id}/decision` ({decision: accepted|rejected|modified|pending, note, decided_by, actual_rate}; accepted → programme contracted) · `GET /api/ledger/{id}/note` (printable HTML) · `GET /api/ledger/export.csv`
* **Risk:** `GET /api/risk` (ingested events first, flagged `live`) · `POST /api/events/ingest` ({text, date?, source?, use_llm?}) · `GET /api/events` · `DELETE /api/events/{id}`
* **Evidence:** `GET /api/backtest` · `GET /api/network`
* **Data:** `GET /api/data/template` (CSV) · `POST /api/data/upload` (raw text/csv body or JSON {csv}; 422 with a readable reason on invalid data) · `GET /api/data/status` · `DELETE /api/data/upload`

Port codes are the keys in `config/ports.json`. Validation errors return 400 (unknown port) or 422 (schema).

## 8. Frontend conventions

* Vanilla JS in IIFEs, no framework and no build. Shared engines expose globals `SeaMap`, `GEO`, `FitScene`, `FIT`.
* Theme: dark nautical. Tokens are in `css/base.css` (`--cyan #38bdf8`, `--teal #2dd4bf`, `--amber #fbbf24`, `--coral #fb7185`; fonts Space Grotesk / Inter / JetBrains Mono via Google Fonts with system fallbacks). Class colours: Capesize cyan, Panamax teal, Supramax amber, Handysize violet.
* Landing sections: hero (SeaMap + ticker) → `#challenge` sticky scrollytelling (canvas, 4 steps) → `#why` tilt cards → `#fit` FitScene → `#how` pipeline (scroll-drawn line) → `#results` counters + waterfall → `#modules` live endpoint cards. Elements with `[data-reveal]` animate via IntersectionObserver, and `[data-split]` headings are split into animated words.
* The cockpit SPA uses hash routes `#/`, `#/plan`, `#/compare`, `#/forecast`, `#/feasibility`, `#/risk`, `#/idle`, `#/ops`, `#/data`, `#/backtest`, `#/network`, `#/api`. Each page is an async function in `app.js` that renders into `#view`. `PL()` wraps Plotly with the theme, and `N()` / `countUp()` animate numbers. Pages must register teardown in `cleanup` (e.g. `SeaMap.destroy()`).
* SeaMap coastlines are deliberately coarse polygons. Lanes are hand-routed waypoints (Torres, Bass Strait, Mozambique Channel, Malacca, Luzon, Red Sea/Suez, Cape alternative).
* `prefers-reduced-motion` is respected.

## 9. Decisions & gotchas (history)

* **Placebo bug found and fixed:** the first placebo world was a martingale in *log* rates, so levels drifted up by σ²/2 per week and locking COA looked falsely ~2% cheaper. `synth.py` now subtracts var/2 per step (a level martingale). Keep this. It is part of the honesty story in DESIGN.md §8.4.
* `config._load` strips keys starting with `_`, so `routes.json["_backhaul"]` is loaded separately as `BACKHAUL`.
* `run_pipeline.py` caches heavy steps in `outputs/cache/*.pkl` keyed by name only. **Delete the cache after changing forecasting or backtest code**, or you will get stale results.
* LP shares can come back as `-0.0`; the planner normalises them with `+ 0.0`.
* CSS: `.kpi>span` and `.stat>span` must be child selectors, otherwise the animated number spans inherit the small label font.
* `body{overflow-x:clip}` (not `hidden`): `hidden` broke scroll capture and sticky behaviour.
* `build_dashboard.py` inlines plotly.js (~5 MB) so `outputs/dashboard.html` works fully offline. The web app instead serves plotly from the installed python package at `/vendor/plotly.min.js`.
* The browser-preview tooling was flaky with smooth scrolling (`scroll-behavior:smooth`). Use `scrollTo({behavior:'instant'})` when testing programmatically.
* A port can be in use (default 8000); `serve.py` honours `PORT`.
* SeaMap port pulse phase must stay in [0,1) even for off-canvas ports (negative x). A negative `%` result gave a negative arc radius and froze the canvas loop.
* HTML number inputs: `step` is anchored at `min`, so a value off the grid silently blocks form submission. Use `step="any"` for free numbers.
* `<dialog>` `close` events are deferred while the page is hidden. Wire dialog actions to button clicks, not to the `close` event.
* In `run_pipeline.tune()` the local list is `tlog` because `log()` is the progress function.
* The Bash tool breaks on heredocs with unbalanced quotes. Write patch scripts to files (e.g. `scratch/`) and run them.

## 10. Guardrails when extending

* Keep every new port/vessel number in `config/*.json` with `confidence` and `verify_with`. Do not invent real-looking specs silently.
* Keep the data label "SYNTHETIC" visible in the UI until real data is wired in.
* Preserve the honesty checks (placebo, RW ablation, B3 control, oracle capture, bootstrap CIs, no tuning on test).
* To plug in real data, replace `synth.generate()` with a loader that returns the same columns: `tce_<Class>`, `ballast_cape`, `ballast_pmx`, `coal_usd_t`, `china_pmi`, `bunker_usd_t`, `wait_<PORT>`, `woy`, plus the `meta` dict.

## 11. Next steps (see DESIGN.md §10)

Real data: Baltic history, SAIL fixtures, IMF PortWatch, World Bank coal. Then calibrate the route basis, add an FFA hedge variable, a stress-scenario library, a Chronos/TimesFM member, end-to-end decision-focused learning (SPO+/cvxpylayers), a recommendation ledger (audit trail), role-based login and ERP stem integration.
