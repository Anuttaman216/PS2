"""End-to-end API tests for every FreightSaarthi endpoint.

Run either way (pytest is optional):
    python tests/test_api.py
    python -m pytest tests -q
Uses a temporary SQLite DB and data folder, so your demo data is never touched.
Requires outputs/results.json (committed in the repo).
"""
import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
_TMP = tempfile.mkdtemp(prefix="fs_test_")
os.environ["FREIGHTSAARTHI_DB"] = os.path.join(_TMP, "test.db")
os.environ["FREIGHTSAARTHI_DATA"] = os.path.join(_TMP, "data")

from fastapi.testclient import TestClient  # noqa: E402
from webapp.server import app  # noqa: E402

c = TestClient(app)
PLAN = {"load": "HAY_POINT", "disch": "PARADIP", "volume": 900000, "duration": 13, "lead": 3}


def ok(r, code=200):
    assert r.status_code == code, f"{r.request.method} {r.request.url} -> {r.status_code}: {r.text[:300]}"
    return r.json() if "json" in r.headers.get("content-type", "") else r.text


# ---------------- pages & system ----------------
def test_pages():
    assert "FreightSaarthi" in ok(c.get("/"))
    assert "Cockpit" in ok(c.get("/app"))
    assert c.get("/docs").status_code == 200
    assert c.get("/vendor/plotly.min.js").status_code == 200


def test_catalogue_and_health():
    cat = ok(c.get("/api"))
    paths = {e["path"] for e in cat["endpoints"]}
    for p in ["/api/plan", "/api/programmes", "/api/ledger", "/api/events/ingest", "/api/compare", "/api/data/upload"]:
        assert p in paths, p
    h = ok(c.get("/api/health"))
    assert h["ok"] and h["data_loaded"]


def test_market_endpoints():
    s = ok(c.get("/api/summary"))
    assert s["spot_fixtures_after"] < s["spot_fixtures_before"]
    assert len(ok(c.get("/api/ticker"))) >= 5
    m = ok(c.get("/api/meta"))
    assert "PARADIP" in m["discharge"] and "HAY_POINT" in m["load"]
    f = ok(c.get("/api/forecast"))
    assert set(f["fan"]) == {"Handysize", "Supramax", "Panamax", "Capesize"}
    one = ok(c.get("/api/forecast/capesize"))
    assert one["cls"] == "Capesize" and len(one["fan"]["p50"]) == 52
    assert c.get("/api/forecast/tanker").status_code == 404


# ---------------- decisions ----------------
def test_plan_pilot_lane():
    p = ok(c.post("/api/plan", json={**PLAN, "broker_quote": 15.5}))
    assert p["ok"] and p["best_class"] in ("Capesize", "Panamax")
    mix = p["mix"]
    assert abs(mix["coa"] + mix["tc"] + mix["spot"] - 1) < 1e-6
    assert p["cost"]["p10"] <= p["cost"]["p50"] <= p["cost"]["p90"]
    assert 0 <= p["xray"]["percentile"] <= 100
    assert p["lp"]["status"] == "ok"


def test_plan_constraints_and_errors():
    h = ok(c.post("/api/plan", json={"load": "HAMPTON_RDS", "disch": "HALDIA", "volume": 250000, "avoid_suez": True}))
    assert h["best_class"] in ("Handysize", "Supramax")                 # 8 m Hooghly draft
    assert any("Cape" in n for n in h["notes"])                           # re-routed via Cape of Good Hope
    assert c.post("/api/plan", json={**PLAN, "load": "ATLANTIS"}).status_code == 400
    assert c.post("/api/plan", json={**PLAN, "duration": 99}).status_code == 422


def test_plan_save_to_ledger():
    p = ok(c.post("/api/plan?save=true", json=PLAN))
    assert isinstance(p["ledger_id"], int)
    e = ok(c.get(f"/api/ledger/{p['ledger_id']}"))
    assert e["best_class"] == p["best_class"] and e["request"]["load"] == "HAY_POINT"


def test_quote_feasibility_idle_compare():
    x = ok(c.post("/api/quote-xray", json={"quote": 13.0}))
    assert x["percentile"] < 50
    f = ok(c.get("/api/feasibility", params={"load": "HAY_POINT", "disch": "HALDIA"}))
    cape = next(r for r in f["lane"] if r["cls"] == "Capesize")
    assert not cape["feasible"]
    assert len(f["matrix"]) == 7
    i = ok(c.get("/api/idle", params={"cls": "Capesize", "idle_days": 6}))
    assert i["ok"] and len(i["options"]) >= 3
    cmp_ = ok(c.post("/api/compare", json={"lanes": [{"load": "HAY_POINT", "disch": "PARADIP"}, {"load": "NACALA", "disch": "DHAMRA"},
                                                      {"load": "MUARA_BERAU", "disch": "VIZAG"}]}))
    assert cmp_["best"]["premium_vs_best"] == 0 and len(cmp_["rows"]) == 3


# ---------------- evidence ----------------
def test_risk_backtest_network():
    r = ok(c.get("/api/risk"))
    assert "alerts" in r and len(r["spikes"]) == 4
    b = ok(c.get("/api/backtest"))
    assert b["summary"]["FS"]["spot_fixtures"] < b["summary"]["B0"]["spot_fixtures"]
    n = ok(c.get("/api/network"))
    assert len(n) == 10 * 7 * 4


# ---------------- operations: programmes + ledger ----------------
def test_programme_lifecycle():
    assert len(ok(c.get("/api/programmes"))) >= 4                                   # seeded demo programmes
    p = ok(c.post("/api/programmes", json={"name": "Test programme", "load": "NACALA", "disch": "DHAMRA", "volume": 500000}), 201)
    pid = p["id"]
    assert p["status"] == "open"
    assert ok(c.put(f"/api/programmes/{pid}", json={"volume": 550000, "notes": "edited"}))["volume"] == 550000
    plan = ok(c.post(f"/api/programmes/{pid}/plan"))
    lid = plan["ledger_id"]
    assert ok(c.get(f"/api/programmes/{pid}"))["status"] == "planned"
    d = ok(c.post(f"/api/ledger/{lid}/decision", json={"decision": "accepted", "decided_by": "GM Shipping", "note": "fix COA", "actual_rate": 13.9}))
    assert d["decision"] == "accepted"
    assert ok(c.get(f"/api/programmes/{pid}"))["status"] == "contracted"
    note = ok(c.get(f"/api/ledger/{lid}/note"))
    assert "Charter Recommendation Note" in note and "GM Shipping" in note
    led = ok(c.get("/api/ledger"))
    assert led["stats"]["acc"] >= 1 and led["rows"][0]["id"] >= lid
    csv_ = ok(c.get("/api/ledger/export.csv"))
    assert csv_.startswith("id,") and "HAY_POINT" in csv_ or "NACALA" in csv_
    assert c.post(f"/api/ledger/{lid}/decision", json={"decision": "maybe"}).status_code == 422
    assert c.post("/api/programmes", json={"name": "bad", "load": "XX"}).status_code == 400
    assert ok(c.delete(f"/api/programmes/{pid}"))["deleted"] == pid
    assert c.get(f"/api/programmes/{pid}").status_code == 404


# ---------------- events ----------------
def test_event_ingestion():
    e = ok(c.post("/api/events/ingest", json={"text": "Cyclone warning for north Odisha coast; Paradip port operations suspended for 48 hours."}), 201)
    assert e["event_type"] == "cyclone" and "PARADIP" in e["locations"]
    assert any("PARADIP" in l for l in e["impacted_lanes"])
    lst = ok(c.get("/api/events"))
    assert any(x["id"] == e["id"] for x in lst["ingested"])
    assert ok(c.get("/api/risk"))["events"][0].get("live")
    assert ok(c.delete(f"/api/events/{e['id']}"))["deleted"] == e["id"]


# ---------------- data upload ----------------
def test_data_upload_flow():
    tpl = ok(c.get("/api/data/template"))
    assert tpl.startswith("date,tce_Handysize")
    bad = c.post("/api/data/upload", content="date,tce_Capesize\n2020-01-03,15000\n", headers={"Content-Type": "text/csv"})
    assert bad.status_code == 422 and "missing required columns" in bad.text
    lines = tpl.strip().split("\n")
    head = lines[0].split(",")
    keep = [head.index(k) for k in ["date", "tce_Handysize", "tce_Supramax", "tce_Panamax", "tce_Capesize"]]
    small = "\n".join(",".join(r.split(",")[i] for i in keep) for r in lines)
    up = ok(c.post("/api/data/upload", content=small, headers={"Content-Type": "text/csv"}))
    assert up["stored"] and "bunker_usd_t" in up["report"]["filled_from_proxy"]
    st = ok(c.get("/api/data/status"))
    assert st["uploaded"]["uploaded"] and st["uploaded"]["rows"] >= 300
    ok(c.post("/api/data/upload", json={"csv": tpl}))
    assert ok(c.delete("/api/data/upload"))["uploaded"] is False
    assert c.post("/api/pipeline/run?source=uploaded").status_code == 400          # nothing uploaded any more
    assert c.post("/api/pipeline/run?source=bogus").status_code == 422
    assert "status" in ok(c.get("/api/pipeline/status"))


if __name__ == "__main__":
    fns = [(n, f) for n, f in sorted(globals().items()) if n.startswith("test_") and callable(f)]
    failed = 0
    for n, f in fns:
        try:
            f()
            print(f"PASS  {n}")
        except Exception as e:  # noqa
            failed += 1
            print(f"FAIL  {n}: {e}")
    print(f"\n{len(fns) - failed}/{len(fns)} passed")
    sys.exit(1 if failed else 0)
