"""FreightSaarthi web application (FastAPI).

    python -m uvicorn webapp.server:app --port 8000        (from the project root)
    or:  python serve.py

Pages:   /            animated landing page
         /app         decision cockpit (single-page app)
         /docs        interactive OpenAPI (Swagger) docs
API:     /api         catalogue of every endpoint
Modules: this file   - pages, health, market/forecast, plan, feasibility, idle, risk, backtest, network, pipeline
         ops.py      - programmes CRUD, decision ledger + charter notes + CSV, event ingestion, compare, data upload
         store.py    - SQLite persistence (outputs/freightsaarthi.db)
         planner.py  - server-side charter planner (physics + scenario paths + CVaR LP)
"""
import json
import threading
import time
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, PlainTextResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from saarthi.config import CLASSES, OUT, VESSELS, DISCHARGE, LOAD, ROUTES, CHOKEPOINTS, COMMERCIAL
from saarthi import data as DATA, events as EV
from .planner import Planner
from . import store

HERE = Path(__file__).resolve().parent
STATIC = HERE / "static"

app = FastAPI(title="FreightSaarthi API", version="1.0",
              description="Intelligent freight forecasting & charter decision support for bulk coal imports to "
                          "India's East Coast (SIH 2026 - PS 26006, Ministry of Steel / SAIL). "
                          "Market data in this build is SYNTHETIC; port limits are flagged assumptions.")
app.mount("/static", StaticFiles(directory=STATIC), name="static")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
store.init()

STATE = {"R": None, "planner": None, "loaded_at": None,
         "pipeline": {"status": "idle", "started": None, "finished": None, "error": None, "stage": None, "source": None, "log": []}}
LOCK = threading.Lock()


def load():
    f = OUT / "results.json"
    if not f.exists():
        STATE["R"], STATE["planner"] = None, None
        return False
    with open(f, encoding="utf-8") as fh:
        R = json.load(fh)
    STATE["R"], STATE["planner"], STATE["loaded_at"] = R, Planner(R), time.strftime("%Y-%m-%d %H:%M:%S")
    return True


load()


def need():
    if STATE["R"] is None:
        raise HTTPException(503, "No results yet - run the pipeline first: POST /api/pipeline/run (or `python run_pipeline.py`).")
    return STATE["R"], STATE["planner"]


# ------------------------------------------------------------------ pages
@app.get("/", include_in_schema=False)
def landing():
    return FileResponse(STATIC / "index.html")


@app.get("/app", include_in_schema=False)
def cockpit():
    return FileResponse(STATIC / "app.html")


_PLOTLY = {}


@app.get("/vendor/plotly.min.js", include_in_schema=False)
def plotly_js():
    """plotly.js served from the installed python package - no CDN needed (works offline)."""
    if "js" not in _PLOTLY:
        from plotly.offline import get_plotlyjs
        _PLOTLY["js"] = get_plotlyjs()
    return Response(_PLOTLY["js"], media_type="application/javascript", headers={"Cache-Control": "max-age=86400"})


# ------------------------------------------------------------------ catalogue & health
@app.get("/api", tags=["system"], summary="Catalogue of all available endpoints")
def catalogue():
    rows = []
    for r in app.routes:
        if getattr(r, "include_in_schema", False) and r.path.startswith("/api"):
            rows.append({"path": r.path, "methods": sorted(m for m in r.methods if m != "HEAD"),
                         "summary": r.summary or "", "tag": (r.tags or ["api"])[0]})
    pages = [{"path": "/", "summary": "Landing page"}, {"path": "/app", "summary": "Decision cockpit"},
             {"path": "/docs", "summary": "Swagger / OpenAPI explorer"}]
    return {"service": "FreightSaarthi", "pages": pages, "endpoints": rows}


@app.get("/api/health", tags=["system"], summary="Service health and data status")
def health():
    R = STATE["R"]
    return {"ok": True, "data_loaded": R is not None, "asof": R["meta"]["asof"] if R else None,
            "data_label": R["meta"]["data_label"] if R else None, "loaded_at": STATE["loaded_at"],
            "pipeline": STATE["pipeline"]}


@app.get("/api/summary", tags=["system"], summary="Headline numbers for the landing page")
def summary():
    R, P = need()
    S = R["backtest"]["summary"]
    fs, b0, b1 = S["FS"], S["B0"], S["B1"]
    cape = R["fan"]["Capesize"]["hist"]
    return {"asof": R["meta"]["asof"], "data_label": R["meta"]["data_label"],
            "origins": len(LOAD), "ports": len(DISCHARGE), "classes": len(CLASSES),
            "saving_pct": fs["saving_vs_base_pct"], "saving_ci": fs["saving_ci90_pct"], "saving_musd": fs["saving_musd"],
            "spot_fixtures_before": b0["spot_fixtures"], "spot_fixtures_after": fs["spot_fixtures"],
            "contracted_pct": fs["contracted_share_pct"], "cvar_before": b1["cvar90_block_cost"], "cvar_after": fs["cvar90_block_cost"],
            "oracle_capture_pct": fs["oracle_capture_pct"],
            "cost": {k: S[k]["avg_cost_usd_t"] for k in ("B0", "B1", "B2", "FS", "ORC")},
            "cape_hist": cape, "cape_dates": R["fan"]["Capesize"]["hist_dates"],
            "cape_swing_pct": round((max(cape) / min(cape) - 1) * 100, 0),
            "draft_min": min(p["max_draft_m"] for p in DISCHARGE.values()),
            "draft_max": max(p["max_draft_m"] for p in DISCHARGE.values()),
            "recommendation": {"class": R["recommendation"]["class"], "coa_quote": R["recommendation"]["coa_quote"]}}


@app.get("/api/ticker", tags=["market"], summary="Live-style market ticker (rates, bunker, port waits)")
def ticker():
    return need()[1].ticker()


@app.get("/api/meta", tags=["reference"], summary="Vessels, ports, routes, chokepoints, commercial assumptions")
def meta():
    return {"classes": CLASSES, "vessels": VESSELS, "discharge": DISCHARGE, "load": LOAD,
            "routes": ROUTES, "chokepoints": CHOKEPOINTS, "commercial": COMMERCIAL}


# ------------------------------------------------------------------ forecasting
@app.get("/api/forecast", tags=["market"], summary="Forecast fan (P10/P50/P90) for all vessel classes")
def forecast_all():
    R, _ = need()
    return {"asof": R["meta"]["asof"], "fan": R["fan"], "explain": R["explain"]}


@app.get("/api/forecast/{cls}", tags=["market"], summary="Forecast, accuracy and ensemble weights for one class")
def forecast_one(cls: str):
    R, _ = need()
    c = next((x for x in CLASSES if x.lower() == cls.lower()), None)
    if not c:
        raise HTTPException(404, f"class must be one of {CLASSES}")
    return {"cls": c, "fan": R["fan"][c], "accuracy": [r for r in R["forecast_report"] if r["class"] == c],
            "accuracy_placebo": [r for r in R["forecast_report_placebo"] if r["class"] == c], "explain": R["explain"]}


# ------------------------------------------------------------------ planning
class PlanRequest(BaseModel):
    load: str = Field("HAY_POINT", description="load port code, see /api/meta")
    disch: str = Field("PARADIP", description="East-Coast discharge port code")
    volume: float = Field(900000, gt=0, description="programme volume (t)")
    duration: int = Field(13, ge=4, le=48, description="programme duration (weeks)")
    lead: int = Field(3, ge=2, le=12, description="weeks until the first laycan")
    stem: float = Field(0, ge=0, description="max parcel size (t), 0 = no limit")
    risk_lambda: float = Field(0.5, ge=0, le=5, description="CVaR weight (risk aversion)")
    freight_shock: float = Field(0.0, ge=-0.5, le=1.0, description="what-if shock on forecast freight path (fraction)")
    bunker_change: float = Field(0.0, ge=-0.5, le=1.0, description="what-if bunker price change (fraction)")
    congestion_add: float = Field(0.0, ge=0, le=15, description="extra waiting days at discharge")
    monsoon: bool = False
    avoid_suez: bool = False
    broker_quote: Optional[float] = Field(None, description="broker's $/t quote to X-ray")


@app.post("/api/plan", tags=["decisions"], summary="Recommend vessel, parcel, contract mix, ladder & timing for a cargo programme")
def plan(req: PlanRequest, save: bool = Query(False, description="store the recommendation in the decision ledger")):
    R, P = need()
    if req.load not in LOAD or req.disch not in DISCHARGE:
        raise HTTPException(400, "unknown port code - see /api/meta")
    body = req.model_dump()
    out = P.plan(body)
    if save and out.get("ok"):
        out["ledger_id"] = store.add_ledger(body, out, R["meta"])
    return JSONResponse(out)


class QuoteRequest(BaseModel):
    load: str = "HAY_POINT"
    disch: str = "PARADIP"
    quote: float = Field(..., gt=0)
    volume: float = 900000
    lead: int = 3


@app.post("/api/quote-xray", tags=["decisions"], summary="Percentile of a broker freight quote in the fair-value band")
def quote_xray(q: QuoteRequest):
    _, P = need()
    r = P.plan({"load": q.load, "disch": q.disch, "volume": q.volume, "duration": 13, "lead": q.lead, "stem": 0,
                "risk_lambda": 0.5, "freight_shock": 0, "bunker_change": 0, "congestion_add": 0, "monsoon": False,
                "avoid_suez": False, "broker_quote": q.quote})
    if not r["ok"]:
        raise HTTPException(400, r["message"])
    return {"class": r["best_class"], **r["xray"]}


@app.get("/api/feasibility", tags=["decisions"], summary="Port-vessel feasibility for a lane + all-port matrix")
def feasibility(load: str = "HAY_POINT", disch: str = "PARADIP", monsoon: bool = False, stem: float = 0, avoid_suez: bool = False):
    _, P = need()
    if load not in LOAD or disch not in DISCHARGE:
        raise HTTPException(400, "unknown port code")
    return P.feasibility(load, disch, monsoon, stem, avoid_suez)


@app.get("/api/idle", tags=["decisions"], summary="Idle-time & ballast-leg options for period tonnage")
def idle(cls: str = "Capesize", load: str = "HAY_POINT", disch: str = "PARADIP", idle_days: float = Query(6, ge=0, le=60)):
    _, P = need()
    return P.idle(cls, load, disch, idle_days)


# ------------------------------------------------------------------ risk, backtest, network
@app.get("/api/risk", tags=["risk"], summary="Early warnings, event intelligence, congestion outlook, spike odds")
def risk():
    R, P = need()
    spikes = []
    for ci, c in enumerate(CLASSES):
        col = P.paths[:, 3, ci]
        now = P.m["tce_now"][c]
        spikes.append({"cls": c, "now": now, "p_up20": float((col > 1.2 * now).mean()), "p_dn20": float((col < 0.8 * now).mean()),
                       "median_4w": float(sorted(col)[len(col) // 2])})
    live = [{**e["extracted"], "id": e["id"], "live": True} for e in store.list_events()]
    return {"alerts": R["alerts"], "events": live + R["events"], "congestion": R["congestion"], "spikes": spikes}


@app.get("/api/backtest", tags=["evidence"], summary="Rolling backtest: strategies, savings, ablations, placebo, tuning")
def backtest():
    R, _ = need()
    return {"summary": R["backtest"]["summary"], "rw_ablation": R["backtest"]["summary_rw_ablation"],
            "placebo": R["backtest"]["summary_placebo"], "blocks": R["backtest"]["blocks"],
            "tune_log": R["meta"]["tune_log"], "selected": R["meta"]["selected_params"]}


@app.get("/api/network", tags=["evidence"], summary="Best class & landed $/t for every origin x East-Coast port")
def network():
    return need()[0]["generalisation"]


# ------------------------------------------------------------------ pipeline
def _progress(msg):
    st = STATE["pipeline"]
    st["stage"] = msg
    st["log"] = (st["log"] + [time.strftime("%H:%M:%S ") + msg])[-40:]


def _run(fast, source):
    try:
        import run_pipeline
        run_pipeline.PROGRESS = _progress
        run_pipeline.main(fast, source)
        load()
        STATE["pipeline"].update(status="done", finished=time.strftime("%H:%M:%S"), error=None)
    except Exception as e:  # noqa
        STATE["pipeline"].update(status="error", finished=time.strftime("%H:%M:%S"), error=repr(e))


@app.post("/api/pipeline/run", tags=["system"], summary="Re-run forecasting + tuning + backtest in the background (synthetic or uploaded data)")
def pipeline_run(fast: bool = True, source: str = Query("synthetic", pattern="^(synthetic|uploaded)$")):
    if source == "uploaded" and not DATA.UPLOAD.exists():
        raise HTTPException(400, "no uploaded data - POST a CSV to /api/data/upload first")
    with LOCK:
        if STATE["pipeline"]["status"] == "running":
            return {"status": "running"}
        STATE["pipeline"].update(status="running", started=time.strftime("%H:%M:%S"), finished=None, error=None,
                                 stage="starting", source=source, log=[])
    threading.Thread(target=_run, args=(fast, source), daemon=True).start()
    return {"status": "started", "source": source}


@app.get("/api/pipeline/status", tags=["system"], summary="Pipeline run status")
def pipeline_status():
    return STATE["pipeline"]


# ------------------------------------------------------------------ operations / data / events routers
from .ops import router as ops_router  # noqa: E402  (after STATE/need are defined)

app.include_router(ops_router)
