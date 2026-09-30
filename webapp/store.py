"""SQLite persistence: cargo programmes, recommendation ledger (audit trail), ingested events.

DB file: outputs/freightsaarthi.db (created on first start, seeded with demo programmes).
Every recommendation stored in the ledger carries a hash of its inputs, the data version (as-of date +
data label) and the full response, so a charter decision can be reproduced and audited later
(CVC/CAG-friendly). The desk records its actual decision against it.
"""
import hashlib
import json
import os
import sqlite3
import threading
import time

from saarthi.config import OUT

DB = os.environ.get("FREIGHTSAARTHI_DB", str(OUT / "freightsaarthi.db"))   # env override used by tests
_LOCK = threading.Lock()

SCHEMA = """
CREATE TABLE IF NOT EXISTS programmes (
  id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, load TEXT NOT NULL, disch TEXT NOT NULL,
  volume REAL NOT NULL, duration INTEGER NOT NULL, lead INTEGER NOT NULL DEFAULT 3, stem REAL DEFAULT 0,
  risk_lambda REAL DEFAULT 0.5, monsoon INTEGER DEFAULT 0, avoid_suez INTEGER DEFAULT 0,
  plant TEXT, notes TEXT, status TEXT DEFAULT 'open', created_at TEXT, updated_at TEXT);
CREATE TABLE IF NOT EXISTS ledger (
  id INTEGER PRIMARY KEY AUTOINCREMENT, created_at TEXT, programme_id INTEGER, input_hash TEXT,
  data_asof TEXT, data_label TEXT, request_json TEXT, response_json TEXT,
  load TEXT, disch TEXT, volume REAL, best_class TEXT, parcel_t REAL, voyages INTEGER,
  mix_coa REAL, mix_tc REAL, mix_spot REAL, exp_cost REAL, cvar90 REAL, coa_quote REAL, action TEXT,
  decision TEXT DEFAULT 'pending', decision_note TEXT, decided_by TEXT, decided_at TEXT, actual_rate REAL);
CREATE TABLE IF NOT EXISTS events (
  id INTEGER PRIMARY KEY AUTOINCREMENT, created_at TEXT, date TEXT, source TEXT, text TEXT, extracted_json TEXT);
"""

DEMO = [
    ("Q4 coking coal - Bokaro/Rourkela", "HAY_POINT", "PARADIP", 900000, 13, 3, "Rourkela / Bokaro", "Pilot lane"),
    ("Mozambique PLV - Dhamra", "NACALA", "DHAMRA", 600000, 26, 4, "Rourkela", "Half-year programme"),
    ("Indonesian PCI coal - Vizag", "MUARA_BERAU", "VIZAG", 400000, 13, 2, "Bhilai", "Short haul"),
    ("US HV-A coal - Haldia", "HAMPTON_RDS", "HALDIA", 250000, 13, 6, "Durgapur / IISCO", "Draft-restricted river port"),
]


def now():
    return time.strftime("%Y-%m-%d %H:%M:%S")


def conn():
    c = sqlite3.connect(DB, check_same_thread=False)
    c.row_factory = sqlite3.Row
    return c


def init():
    with _LOCK, conn() as c:
        c.executescript(SCHEMA)
        if c.execute("SELECT COUNT(*) FROM programmes").fetchone()[0] == 0:
            for name, l, d, v, dur, lead, plant, notes in DEMO:
                c.execute("INSERT INTO programmes(name,load,disch,volume,duration,lead,plant,notes,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?)",
                          (name, l, d, v, dur, lead, plant, notes, now(), now()))


def _row(r):
    if r is None:
        return None
    d = dict(r)
    for k in ("monsoon", "avoid_suez"):
        if k in d:
            d[k] = bool(d[k])
    for k in ("request_json", "response_json", "extracted_json"):
        if k in d and d[k]:
            d[k.replace("_json", "")] = json.loads(d.pop(k))
    return d


# ---------------- programmes ----------------
PROG_FIELDS = ["name", "load", "disch", "volume", "duration", "lead", "stem", "risk_lambda", "monsoon", "avoid_suez", "plant", "notes", "status"]


def list_programmes():
    with conn() as c:
        rows = c.execute("""SELECT p.*, (SELECT COUNT(*) FROM ledger l WHERE l.programme_id=p.id) AS n_plans,
                            (SELECT id FROM ledger l WHERE l.programme_id=p.id ORDER BY id DESC LIMIT 1) AS last_ledger_id
                            FROM programmes p ORDER BY p.id DESC""").fetchall()
    return [_row(r) for r in rows]


def get_programme(pid):
    with conn() as c:
        return _row(c.execute("SELECT * FROM programmes WHERE id=?", (pid,)).fetchone())


def create_programme(d):
    vals = {k: d.get(k) for k in PROG_FIELDS if d.get(k) is not None}
    vals.setdefault("status", "open")
    with _LOCK, conn() as c:
        cur = c.execute(f"INSERT INTO programmes({','.join(vals)},created_at,updated_at) VALUES({','.join('?' * len(vals))},?,?)",
                        [int(v) if isinstance(v, bool) else v for v in vals.values()] + [now(), now()])
        pid = cur.lastrowid
    return get_programme(pid)


def update_programme(pid, d):
    vals = {k: d[k] for k in PROG_FIELDS if k in d and d[k] is not None}
    if vals:
        with _LOCK, conn() as c:
            c.execute(f"UPDATE programmes SET {','.join(k + '=?' for k in vals)}, updated_at=? WHERE id=?",
                      [int(v) if isinstance(v, bool) else v for v in vals.values()] + [now(), pid])
    return get_programme(pid)


def delete_programme(pid):
    with _LOCK, conn() as c:
        return c.execute("DELETE FROM programmes WHERE id=?", (pid,)).rowcount > 0


# ---------------- ledger ----------------
def input_hash(req):
    return hashlib.sha256(json.dumps(req, sort_keys=True).encode()).hexdigest()[:16]


def add_ledger(req, plan, meta, programme_id=None):
    m = plan.get("mix", {})
    cost = plan.get("cost", {})
    with _LOCK, conn() as c:
        cur = c.execute("""INSERT INTO ledger(created_at,programme_id,input_hash,data_asof,data_label,request_json,response_json,load,disch,volume,
                         best_class,parcel_t,voyages,mix_coa,mix_tc,mix_spot,exp_cost,cvar90,coa_quote,action)
                         VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                        (now(), programme_id, input_hash(req), meta.get("asof"), meta.get("data_label"), json.dumps(req),
                         json.dumps({k: v for k, v in plan.items() if k != "hist"}), req["load"], req["disch"], req["volume"],
                         plan.get("best_class"), plan.get("parcel_t"), plan.get("voyages"), m.get("coa"), m.get("tc"), m.get("spot"),
                         cost.get("mean"), cost.get("cvar90"), plan.get("coa_quote"), plan.get("action")))
        return cur.lastrowid


def list_ledger(limit=200, programme_id=None):
    q = "SELECT id,created_at,programme_id,input_hash,data_asof,load,disch,volume,best_class,parcel_t,voyages,mix_coa,mix_tc,mix_spot,exp_cost,cvar90,coa_quote,action,decision,decision_note,decided_by,decided_at,actual_rate FROM ledger"
    args = []
    if programme_id:
        q += " WHERE programme_id=?"
        args.append(programme_id)
    q += " ORDER BY id DESC LIMIT ?"
    args.append(limit)
    with conn() as c:
        return [_row(r) for r in c.execute(q, args).fetchall()]


def get_ledger(lid):
    with conn() as c:
        return _row(c.execute("SELECT * FROM ledger WHERE id=?", (lid,)).fetchone())


def decide(lid, decision, note=None, by=None, actual_rate=None):
    with _LOCK, conn() as c:
        n = c.execute("UPDATE ledger SET decision=?, decision_note=?, decided_by=?, decided_at=?, actual_rate=? WHERE id=?",
                      (decision, note, by, now(), actual_rate, lid)).rowcount
    return get_ledger(lid) if n else None


def ledger_stats():
    with conn() as c:
        r = c.execute("""SELECT COUNT(*) n, SUM(decision='accepted') acc, SUM(decision='rejected') rej, SUM(decision='modified') modi,
                         SUM(decision='pending') pend, AVG(exp_cost) avg_cost, SUM(volume) vol FROM ledger""").fetchone()
    return dict(r)


# ---------------- events ----------------
def add_event(date, source, text, extracted):
    with _LOCK, conn() as c:
        return c.execute("INSERT INTO events(created_at,date,source,text,extracted_json) VALUES(?,?,?,?,?)",
                         (now(), date, source, text, json.dumps(extracted))).lastrowid


def list_events():
    with conn() as c:
        return [_row(r) for r in c.execute("SELECT * FROM events ORDER BY id DESC").fetchall()]


def delete_event(eid):
    with _LOCK, conn() as c:
        return c.execute("DELETE FROM events WHERE id=?", (eid,)).rowcount > 0
