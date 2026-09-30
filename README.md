# FreightSaarthi: SIH 2026 PS 26006 (Ministry of Steel / SAIL)

An intelligent freight forecasting and charter decision system for bulk coal imports to India's East Coast. It forecasts class freight rates probabilistically, checks port and vessel feasibility, recommends the vessel class and parcel size, and recommends the contract mix (spot / COA / period TC) and its timing through a CVaR "Charter Ladder". It also manages idle time and ballast legs, and raises early warnings. A walk-forward backtest against SAIL's daily-spot practice measures the savings. It is delivered as a **full-stack web application**: a FastAPI backend with 35 REST endpoints, SQLite persistence and an automated test suite, plus an animated landing page and a decision cockpit.

* **Design document (the full answer):** [docs/DESIGN.md](docs/DESIGN.md)
* **SIH demo script + judge Q&A:** [docs/DEMO.md](docs/DEMO.md)
* **Video voiceover script (PPT + prototype, ~7-8 min):** [docs/VIDEO_SCRIPT.md](docs/VIDEO_SCRIPT.md)
* **Idea presentation (PDF / PPTX):** [docs/presentation/](docs/presentation/)
* **Problem statement:** [docs/PROBLEM_STATEMENT.md](docs/PROBLEM_STATEMENT.md)
* **Working with Claude / AI assistants:** [CLAUDE.md](CLAUDE.md) holds the full project context (architecture, formulas, API, conventions, decision log)
* **Pilot lane:** Hay Point (Australia) → Paradip, on clearly labelled **synthetic** data. Every other origin and port works through the same code, and real data can be uploaded in the Data Hub.

## Run it

```bash
pip install -r requirements.txt
python serve.py               # http://localhost:8000   (set PORT=xxxx to change the port)
python tests/test_api.py      # 11 test groups covering all 35 endpoints (temp DB, never touches your data)
python run_pipeline.py        # optional: rebuilds outputs/results.json (~15 min cold; results.json is already included)
```

| URL | What it is |
|---|---|
| `/` | Animated landing page: live lane map, market ticker, scroll-driven story, a "Will it fit?" port-vessel simulator, backtest proof, and a module hub that pings every endpoint live |
| `/app` | Decision cockpit: Overview · Plan a Charter · Compare Lanes · Market Forecast · Port Feasibility · Risk & Alerts · Idle Manager · **Programmes & Ledger** · **Data Hub** · Backtest Proof · Network View · API Explorer |
| `/api` | Catalogue of all endpoints |
| `/docs` | Swagger / OpenAPI explorer |

## Backend: what the server actually does

| Area | Endpoints | Behaviour |
|---|---|---|
| Decisions | `POST /api/plan[?save=true]`, `POST /api/compare`, `POST /api/quote-xray`, `GET /api/feasibility`, `GET /api/idle` | Live computation per request: port/vessel physics, 150-scenario landed cost, **CVaR stochastic LP** (HiGHS), entry timing, broker-quote percentile |
| Operations | `GET/POST /api/programmes`, `GET/PUT/DELETE /api/programmes/{id}`, `POST /api/programmes/{id}/plan` | SAIL cargo requirements stored in SQLite; planning a programme writes to the ledger and moves its status open → planned → contracted |
| Audit ledger | `GET /api/ledger`, `GET /api/ledger/{id}`, `POST /api/ledger/{id}/decision`, `GET /api/ledger/{id}/note`, `GET /api/ledger/export.csv` | Every recommendation stored with an input hash, data version and full snapshot; officer decisions; printable charter note (print to PDF); CSV export |
| Risk | `GET /api/risk`, `POST /api/events/ingest`, `GET /api/events`, `DELETE /api/events/{id}` | Alerts, congestion outlook, spike odds; news or port notices are turned into typed events mapped to impacted lanes (rules, or Claude if configured) and persisted |
| Data | `GET /api/data/template`, `POST /api/data/upload`, `GET /api/data/status`, `DELETE /api/data/upload` | Upload real weekly history as CSV; validated (columns, dates, gaps, length); missing drivers proxy-filled and labelled |
| Pipeline | `POST /api/pipeline/run?source=synthetic\|uploaded&fast=`, `GET /api/pipeline/status` | Background retrain: walk-forward forecasts, decision-focused tuning, backtest, ablations, placebo; live stage log |
| Market & evidence | `GET /api/summary`, `/api/ticker`, `/api/meta`, `/api/forecast`, `/api/forecast/{cls}`, `/api/backtest`, `/api/network`, `/api/health`, `/api` | Forecast fans, accuracy, backtest, network-wide landed cost |

The app runs fully offline: plotly.js is served from the installed Python package. Google Fonts are optional and fall back to system fonts.

## Layout

```
config/            port / vessel / route constraint register (assumptions flagged)
saarthi/           models: synthetic world, data ingestion, forecaster, physics, optimiser, backtest, alerts, events, idle
run_pipeline.py    forecasting + tuning + backtest + ablations -> outputs/results.json   (--source synthetic|uploaded)
webapp/server.py   FastAPI app: pages, market/decision/evidence/pipeline endpoints
webapp/ops.py      programmes, ledger + charter notes, events, compare, data upload
webapp/store.py    SQLite persistence (outputs/freightsaarthi.db, auto-created + seeded)
webapp/planner.py  server-side charter planner for any lane
webapp/static/     landing page, cockpit SPA, shared sea-map and fit-scene engines
tests/test_api.py  end-to-end API tests
docs/              DESIGN.md, DEMO.md, PROBLEM_STATEMENT.md
```

Every port and vessel figure in `config/` is an **assumption** with a confidence tag and a `verify_with` source. Verify these figures before any operational use. If you change model or backtest code, delete `outputs/cache/` so results are recomputed.
