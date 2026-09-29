# FreightSaarthi: SIH 2026 PS 26006 (Ministry of Steel / SAIL)

An intelligent freight forecasting and charter decision system for bulk coal imports to India's East Coast. It forecasts class freight rates probabilistically, checks port and vessel feasibility, recommends the vessel class and parcel size, and recommends the contract mix (spot / COA / period TC) and its timing through a CVaR "Charter Ladder". It also manages idle time and ballast legs, and raises early warnings. A walk-forward backtest against SAIL's daily-spot practice measures the savings.

* **Design document (the full answer):** [docs/DESIGN.md](docs/DESIGN.md)
* **Problem statement:** [docs/PROBLEM_STATEMENT.md](docs/PROBLEM_STATEMENT.md)
* **Working with Claude / AI assistants:** [CLAUDE.md](CLAUDE.md) holds the full project context (architecture, formulas, API, conventions, decision log)
* **Pilot lane:** Hay Point (Australia) → Paradip, on clearly labelled **synthetic** data. Other origins and ports work through the same code.

## Run the web application

```bash
pip install -r requirements.txt
python run_pipeline.py        # optional: outputs/results.json is already included; this rebuilds it (~15 min cold)
python serve.py               # http://localhost:8000   (set PORT=xxxx to change the port)
```

| URL | What it is |
|---|---|
| `/` | Animated landing page: live lane map, market ticker, scroll-driven story, a "Will it fit?" port-vessel simulator, backtest proof, and a module hub that pings every endpoint live |
| `/app` | Decision cockpit (single-page app): Overview, Plan a Charter, Market Forecast, Port Feasibility, Risk & Alerts, Idle Manager, Backtest Proof, Network View, API Explorer |
| `/api` | Catalogue of all endpoints |
| `/docs` | Swagger / OpenAPI explorer |

Key endpoints: `POST /api/plan` (vessel, parcel, COA/TC/spot mix, ladder, timing, X-ray; runs the real CVaR LP), `POST /api/quote-xray`, `GET /api/forecast/{cls}`, `GET /api/feasibility`, `GET /api/risk`, `GET /api/idle`, `GET /api/backtest`, `GET /api/network`, `GET /api/ticker`, `POST /api/pipeline/run`.

The app runs fully offline: plotly.js is served from the installed Python package. Google Fonts are optional and fall back to system fonts.

## Layout

```
config/            port / vessel / route constraint register (assumptions flagged)
saarthi/           models: synthetic world, forecaster, physics, optimiser, backtest, alerts, events, idle
run_pipeline.py    forecasting + tuning + backtest + ablations -> outputs/
webapp/server.py   FastAPI app (pages + REST API)
webapp/planner.py  server-side charter planner for any lane
webapp/static/     landing page, cockpit SPA, shared sea-map and fit-scene engines
outputs/dashboard.html   older single-file offline dashboard (still works on its own)
```

Every port and vessel figure in `config/` is an **assumption** with a confidence tag and a `verify_with` source. Verify these figures before any operational use. If you change model or backtest code, delete `outputs/cache/` so results are recomputed.
