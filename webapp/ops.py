"""Operational endpoints: cargo programmes (CRUD), decision ledger + charter notes, live event ingestion,
multi-lane comparison, real-data upload. Mounted by webapp/server.py via app.include_router(router)."""
import csv
import io
import json
import time
from typing import Optional

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import HTMLResponse, PlainTextResponse
from pydantic import BaseModel, Field

from saarthi import data as DATA, events as EV
from saarthi.config import DISCHARGE, LOAD, ROUTES
from . import store

router = APIRouter()


def _state():
    from .server import STATE, need  # lazy: avoids a circular import at module load
    return STATE, need


def _ports_ok(load_, disch_):
    if load_ is not None and load_ not in LOAD:
        raise HTTPException(400, f"unknown load port '{load_}' - see /api/meta")
    if disch_ is not None and disch_ not in DISCHARGE:
        raise HTTPException(400, f"unknown discharge port '{disch_}' - see /api/meta")


def _esc(x):
    return "" if x is None else str(x).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


# ------------------------------------------------------------------ programmes
STATUS = "^(open|planned|contracted|closed)$"


class Programme(BaseModel):
    name: str = Field(..., min_length=2, description="e.g. 'Q4 coking coal - Bokaro'")
    load: str = "HAY_POINT"
    disch: str = "PARADIP"
    volume: float = Field(900000, gt=0)
    duration: int = Field(13, ge=4, le=48)
    lead: int = Field(3, ge=2, le=12)
    stem: float = Field(0, ge=0)
    risk_lambda: float = Field(0.5, ge=0, le=5)
    monsoon: bool = False
    avoid_suez: bool = False
    plant: Optional[str] = None
    notes: Optional[str] = None
    status: Optional[str] = Field(None, pattern=STATUS)


class ProgrammePatch(BaseModel):
    name: Optional[str] = None
    load: Optional[str] = None
    disch: Optional[str] = None
    volume: Optional[float] = Field(None, gt=0)
    duration: Optional[int] = Field(None, ge=4, le=48)
    lead: Optional[int] = Field(None, ge=2, le=12)
    stem: Optional[float] = Field(None, ge=0)
    risk_lambda: Optional[float] = Field(None, ge=0, le=5)
    monsoon: Optional[bool] = None
    avoid_suez: Optional[bool] = None
    plant: Optional[str] = None
    notes: Optional[str] = None
    status: Optional[str] = Field(None, pattern=STATUS)


@router.get("/api/programmes", tags=["operations"], summary="List cargo programmes (requirements)")
def programmes_list():
    return store.list_programmes()


@router.post("/api/programmes", tags=["operations"], summary="Create a cargo programme", status_code=201)
def programmes_create(p: Programme):
    _ports_ok(p.load, p.disch)
    return store.create_programme(p.model_dump())


@router.get("/api/programmes/{pid}", tags=["operations"], summary="Get one programme with its plan history")
def programmes_get(pid: int):
    p = store.get_programme(pid)
    if not p:
        raise HTTPException(404, "programme not found")
    return {**p, "plans": store.list_ledger(programme_id=pid)}


@router.put("/api/programmes/{pid}", tags=["operations"], summary="Update a programme (partial)")
def programmes_update(pid: int, p: ProgrammePatch):
    if not store.get_programme(pid):
        raise HTTPException(404, "programme not found")
    _ports_ok(p.load, p.disch)
    return store.update_programme(pid, p.model_dump(exclude_none=True))


@router.delete("/api/programmes/{pid}", tags=["operations"], summary="Delete a programme")
def programmes_delete(pid: int):
    if not store.delete_programme(pid):
        raise HTTPException(404, "programme not found")
    return {"deleted": pid}


@router.post("/api/programmes/{pid}/plan", tags=["operations"],
             summary="Run the planner for a stored programme and record the recommendation in the ledger")
def programmes_plan(pid: int, freight_shock: float = 0.0, bunker_change: float = 0.0, congestion_add: float = 0.0):
    STATE, need = _state()
    R, P = need()
    p = store.get_programme(pid)
    if not p:
        raise HTTPException(404, "programme not found")
    req = {k: p[k] for k in ("load", "disch", "volume", "duration", "lead", "stem", "risk_lambda", "monsoon", "avoid_suez")}
    req.update(stem=req["stem"] or 0, freight_shock=freight_shock, bunker_change=bunker_change,
               congestion_add=congestion_add, broker_quote=None)
    out = P.plan(req)
    if not out.get("ok"):
        raise HTTPException(400, out.get("message"))
    out["ledger_id"] = store.add_ledger(req, out, R["meta"], programme_id=pid)
    if p["status"] == "open":
        store.update_programme(pid, {"status": "planned"})
    return out


# ------------------------------------------------------------------ decision ledger (audit trail)
class Decision(BaseModel):
    decision: str = Field(..., pattern="^(accepted|rejected|modified|pending)$")
    note: Optional[str] = None
    decided_by: Optional[str] = Field(None, description="name / role of the approving officer")
    actual_rate: Optional[float] = Field(None, description="actual $/t fixed, for ex-post regret tracking")


@router.get("/api/ledger", tags=["operations"], summary="Recommendation ledger (latest first) with decision stats")
def ledger_list(limit: int = Query(200, ge=1, le=2000), programme_id: Optional[int] = None):
    return {"stats": store.ledger_stats(), "rows": store.list_ledger(limit, programme_id)}


@router.get("/api/ledger/export.csv", tags=["operations"], summary="Export the ledger as CSV")
def ledger_csv():
    rows = store.list_ledger(10000)
    buf = io.StringIO()
    if rows:
        w = csv.DictWriter(buf, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    return PlainTextResponse(buf.getvalue(), media_type="text/csv",
                             headers={"Content-Disposition": "attachment; filename=freightsaarthi_ledger.csv"})


@router.get("/api/ledger/{lid}", tags=["operations"], summary="Full ledger entry incl. request & response snapshot")
def ledger_get(lid: int):
    r = store.get_ledger(lid)
    if not r:
        raise HTTPException(404, "ledger entry not found")
    return r


@router.post("/api/ledger/{lid}/decision", tags=["operations"], summary="Record the desk's decision on a recommendation")
def ledger_decide(lid: int, d: Decision):
    r = store.decide(lid, d.decision, d.note, d.decided_by, d.actual_rate)
    if not r:
        raise HTTPException(404, "ledger entry not found")
    if d.decision == "accepted" and r.get("programme_id"):
        store.update_programme(r["programme_id"], {"status": "contracted"})
    return r


@router.get("/api/ledger/{lid}/note", tags=["operations"], response_class=HTMLResponse,
            summary="Printable charter recommendation note (HTML - print / save as PDF)")
def ledger_note(lid: int):
    r = store.get_ledger(lid)
    if not r:
        raise HTTPException(404, "ledger entry not found")
    q, o = r["request"], r["response"]
    lname, dname = LOAD[q["load"]]["name"], DISCHARGE[q["disch"]]["name"]
    rows = []
    for c in o["classes"]:
        if c["feasible"]:
            rows.append(f"<tr><td>{c['cls']}</td><td>yes</td><td>{c['cargo_t']:,}</td><td>{_esc(c['binding'])}</td><td>{c['p50']}</td></tr>")
        else:
            rows.append(f"<tr><td>{c['cls']}</td><td>no</td><td>-</td><td>{_esc(c['binding'])}</td><td>-</td></tr>")
    tr = ", ".join(f"week +{t['week']}: {t['share'] * 100:.0f}%" for t in o["tranches"]) or "no lock-in this week"
    why = "".join(f"<li>{_esc(w)}</li>" for w in o["why"])
    m, cost = o["mix"], o["cost"]
    return f"""<!doctype html><html><head><meta charset="utf-8"><title>Charter note #{lid}</title>
<style>body{{font:14px/1.5 Georgia,serif;max-width:820px;margin:30px auto;color:#111;padding:0 20px}}h1{{font-size:22px;margin:0}}h3{{margin:18px 0 6px}}
.hd{{display:flex;justify-content:space-between;gap:20px;border-bottom:2px solid #111;padding-bottom:8px;margin-bottom:14px}}
table{{border-collapse:collapse;width:100%;margin:6px 0 12px}}td,th{{border:1px solid #bbb;padding:5px 8px;text-align:left;font-size:13px}}
th{{background:#f1f1f1;width:22%}}.k{{color:#555;font-size:12px}}.box{{border:1px solid #111;padding:10px 12px;margin:8px 0}}
.warn{{background:#fff7d6;border:1px solid #d9b000;padding:6px 10px;font-size:12px}}button{{float:right;padding:6px 12px}}@media print{{button{{display:none}}}}</style></head><body>
<button onclick="print()">Print / Save PDF</button>
<div class="hd"><div><h1>Charter Recommendation Note</h1><div class="k">FreightSaarthi decision support &middot; Ledger #{lid}</div></div>
<div class="k">Generated {_esc(r['created_at'])}<br>Input hash {_esc(r['input_hash'])}<br>Data as of {_esc(r['data_asof'])}</div></div>
<div class="warn">Data basis: {_esc(r['data_label'])}. Port limits are planning assumptions - verify against the port's current draft notice before fixing.</div>
<h3>1. Requirement</h3><table><tr><th>Lane</th><td>{_esc(lname)} &rarr; {_esc(dname)}</td><th>Volume</th><td>{q['volume']:,.0f} t</td></tr>
<tr><th>Programme</th><td>{q['duration']} weeks, first laycan in {q['lead']} weeks</td><th>Risk weight &lambda;</th><td>{q['risk_lambda']}</td></tr>
<tr><th>Scenario</th><td colspan="3">freight shock {q['freight_shock'] * 100:+.0f}%, bunker {q['bunker_change'] * 100:+.0f}%, extra congestion {q['congestion_add']} d,
monsoon {q['monsoon']}, avoid Suez {q['avoid_suez']}</td></tr></table>
<h3>2. Recommendation</h3><div class="box"><b>{o['voyages']} &times; {o['best_class']}</b> voyages of <b>{o['parcel_t']:,} t</b> (binding: {_esc(o['binding'])}).<br>
Contract mix: <b>COA {m['coa'] * 100:.0f}%</b> at ${o['coa_quote']}/t &middot; <b>period TC {m['tc'] * 100:.0f}%</b> at ~${o['tc_hire']:,.0f}/day &middot;
<b>spot {m['spot'] * 100:.0f}%</b> (forecast-timed).<br>Charter ladder: {tr}.<br>Action: <b>{_esc(o['action'])}</b></div>
<table><tr><th>Expected landed $/t</th><td>{cost['mean']}</td><th>P10 - P90</th><td>{cost['p10']} - {cost['p90']}</td></tr>
<tr><th>CVaR90 $/t</th><td>{cost['cvar90']}</td><th>Programme freight</th><td>${o['programme_musd']} M</td></tr>
<tr><th>vs daily-spot {o['habit_class']}</th><td>{o['saving_vs_habit_pct']}% (${o['saving_vs_habit_musd']} M)</td><th>Freight / t hot metal</th><td>${o['freight_per_t_hot_metal']}</td></tr></table>
<h3>3. Vessel options considered</h3><table><tr><th>Class</th><th>Feasible</th><th>Parcel t</th><th>Binding constraint</th><th>P50 $/t</th></tr>{''.join(rows)}</table>
<h3>4. Rationale</h3><ul>{why}</ul>
<h3>5. Decision</h3><table><tr><th>Decision</th><td>{_esc(r['decision'])}</td><th>By</th><td>{_esc(r['decided_by'])}</td></tr>
<tr><th>Note</th><td colspan="3">{_esc(r['decision_note'])}</td></tr>
<tr><th>Decided at</th><td>{_esc(r['decided_at'])}</td><th>Actual $/t</th><td>{_esc(r['actual_rate'])}</td></tr></table>
<p class="k" style="margin-top:28px">Signature: ______________________ &nbsp;&nbsp; Designation: ______________________</p></body></html>"""


# ------------------------------------------------------------------ live event ingestion
class EventIn(BaseModel):
    text: str = Field(..., min_length=10, description="news item / port notice / IMD bulletin text")
    date: Optional[str] = None
    source: Optional[str] = "manual"
    use_llm: bool = Field(False, description="Claude structured extraction (needs `anthropic` + credentials); falls back to rules")


def _lanes():
    return [{"load": l, "disch": d, "routing": ROUTES[l]["routing"]} for l in LOAD for d in DISCHARGE]


@router.post("/api/events/ingest", tags=["risk"], status_code=201,
             summary="Ingest a news / port notice -> typed event -> impacted SAIL lanes (persisted)")
def events_ingest(e: EventIn):
    item = {"date": e.date or time.strftime("%Y-%m-%d"), "text": e.text, "source": e.source}
    ev = EV.impacted(EV.extract_all([item], use_llm=e.use_llm), _lanes())[0]
    ev["id"] = store.add_event(item["date"], e.source, e.text, ev)
    return ev


@router.get("/api/events", tags=["risk"], summary="Ingested events (persisted) + demo feed")
def events_list():
    STATE, _ = _state()
    R = STATE["R"]
    return {"ingested": [{**x["extracted"], "id": x["id"]} for x in store.list_events()], "feed": R["events"] if R else []}


@router.delete("/api/events/{eid}", tags=["risk"], summary="Delete an ingested event")
def events_delete(eid: int):
    if not store.delete_event(eid):
        raise HTTPException(404, "event not found")
    return {"deleted": eid}


# ------------------------------------------------------------------ multi-lane comparison
class CompareRequest(BaseModel):
    lanes: list[dict] = Field(..., description='[{"load":"HAY_POINT","disch":"PARADIP"}, ...]; optional per-lane "volume"')
    volume: float = Field(900000, gt=0)
    duration: int = Field(13, ge=4, le=48)
    lead: int = Field(3, ge=2, le=12)
    risk_lambda: float = Field(0.5, ge=0, le=5)
    monsoon: bool = False
    avoid_suez: bool = False


@router.post("/api/compare", tags=["decisions"], summary="Plan several origin/port lanes side by side (landed $/t, class, mix)")
def compare(c: CompareRequest):
    _, need = _state()
    _, P = need()
    if not 1 <= len(c.lanes) <= 20:
        raise HTTPException(400, "give 1-20 lanes")
    rows = []
    for ln in c.lanes:
        if "load" not in ln or "disch" not in ln:
            raise HTTPException(400, "each lane needs 'load' and 'disch'")
        _ports_ok(ln["load"], ln["disch"])
        req = {"load": ln["load"], "disch": ln["disch"], "volume": float(ln.get("volume", c.volume)), "duration": c.duration,
               "lead": c.lead, "stem": 0, "risk_lambda": c.risk_lambda, "freight_shock": 0, "bunker_change": 0,
               "congestion_add": 0, "monsoon": c.monsoon, "avoid_suez": c.avoid_suez, "broker_quote": None}
        o = P.plan(req)
        row = {"load": req["load"], "disch": req["disch"], "ok": o["ok"]}
        if o["ok"]:
            row.update(best_class=o["best_class"], parcel_t=o["parcel_t"], voyages=o["voyages"], landed_mean=o["cost"]["mean"],
                       landed_p10=o["cost"]["p10"], landed_p90=o["cost"]["p90"], cvar90=o["cost"]["cvar90"], mix=o["mix"],
                       programme_musd=o["programme_musd"], action=o["action"])
        else:
            row["message"] = o.get("message")
        rows.append(row)
    ok = [r for r in rows if r["ok"]]
    best = min(ok, key=lambda r: r["landed_mean"]) if ok else None
    for r in ok:
        r["premium_vs_best"] = round(r["landed_mean"] - best["landed_mean"], 2)
    return {"best": best, "rows": sorted(rows, key=lambda r: r.get("landed_mean", 1e9))}


# ------------------------------------------------------------------ real-data upload
@router.get("/api/data/status", tags=["data"], summary="Active data source + uploaded-file validation report")
def data_status():
    STATE, _ = _state()
    R = STATE["R"]
    return {"active_source": (R["meta"].get("source", "synthetic") if R else None),
            "active_label": R["meta"]["data_label"] if R else None, "asof": R["meta"]["asof"] if R else None,
            "uploaded": DATA.status(), "required_columns": ["date"] + DATA.REQUIRED, "optional_columns": DATA.OPTIONAL,
            "min_weeks": DATA.MIN_WEEKS}


@router.get("/api/data/template", tags=["data"], summary="CSV template in the exact upload format (synthetic example values)")
def data_template():
    return PlainTextResponse(DATA.template_csv(), media_type="text/csv",
                             headers={"Content-Disposition": "attachment; filename=freightsaarthi_market_template.csv"})


@router.post("/api/data/upload", tags=["data"], summary="Upload weekly market CSV (raw text/csv body, or JSON {\"csv\": ...})",
             openapi_extra={"requestBody": {"content": {"text/csv": {"schema": {"type": "string"}}}, "required": True}})
async def data_upload(request: Request):
    raw = (await request.body()).decode("utf-8-sig", errors="replace")
    if request.headers.get("content-type", "").startswith("application/json"):
        try:
            raw = json.loads(raw)["csv"]
        except Exception:  # noqa
            raise HTTPException(400, 'JSON body must be {"csv": "<csv text>"}')
    try:
        rep = DATA.save(raw)
    except DATA.DataError as e:
        raise HTTPException(422, str(e))
    return {"stored": True, "report": rep, "next": "POST /api/pipeline/run?source=uploaded"}


@router.delete("/api/data/upload", tags=["data"], summary="Remove the uploaded data file")
def data_reset():
    DATA.reset()
    return {"uploaded": False}
