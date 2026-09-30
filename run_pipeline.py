"""FreightSaarthi end-to-end pipeline (Australia/Hay Point -> Paradip pilot lane, SYNTHETIC data).

  1. generate structured synthetic world (+ martingale placebo world)
  2. walk-forward probabilistic forecasts (refit every 13 weeks, strictly causal)
  3. forecast accuracy report (test period) incl. Diebold-Mariano vs random walk
  4. decision-focused calibration of optimiser knobs on the VALIDATION period (2018H2-2020)
  5. rolling decision backtest on the TEST period (2021-2026H1): B0..FS + oracle
  6. ablations: forecast value (FS with random-walk forecasts), placebo world
  7. today's recommendation + dashboard data -> outputs/dashboard.html

Run:  python run_pipeline.py            (~4-6 min on a laptop)
      python run_pipeline.py --fast     (coarser refits, for demos)
"""
import argparse
import json
import time

import numpy as np
import pandas as pd
from scipy.stats import norm

from saarthi.config import CLASSES, OUT, VESSELS, DISCHARGE, LOAD, ROUTES, CHOKEPOINTS, COMMERCIAL
from saarthi.synth import generate, seasonal, market_forward_log
from saarthi.forecast import walk_forward, simulate_paths, HORIZONS
from saarthi.backtest import Backtest, Lane, summarise, BLOCK, BASE_FIX
from saarthi.optimizer import solve_block, entry_timing
from saarthi import physics as PH, alerts as AL, idle as IDLE, events as EV

VAL = ("2018-07-01", "2020-12-31")
TEST = ("2021-01-01", "2026-06-30")
FC_START = "2017-06-01"


import pickle
CACHE = OUT / "cache"
CACHE.mkdir(exist_ok=True)


PROGRESS = None          # optional callback(str) set by the web server to report stages


def log(msg):
    print(msg, flush=True)
    if PROGRESS:
        PROGRESS(msg.strip())


def cached(name, fn, use=True):
    f = CACHE / f"{name}.pkl"
    if use and f.exists():
        return pickle.loads(f.read_bytes())
    r = fn()
    f.write_bytes(pickle.dumps(r))
    return r


def forecast_report(fc, start):
    t0 = fc["date"] >= pd.Timestamp(start)
    rows = []
    for c_i, c in enumerate(CLASSES):
        for h in [1, 4, 8, 12, 26]:
            g = fc[t0 & (fc.h == h) & (fc.cls == c_i) & fc.target.notna()]
            e_ens = g.q50 - g.target
            e_rw = g.rw_q50 - g.target
            d = np.abs(e_rw) - np.abs(e_ens)
            # Diebold-Mariano with Newey-West variance (lag h-1)
            dc = d - d.mean()
            var = np.mean(dc ** 2) + 2 * sum((1 - l / h) * np.mean(dc.values[l:] * dc.values[:-l]) for l in range(1, h))
            dm = d.mean() / np.sqrt(max(var, 1e-12) / len(d))
            rows.append({"class": c, "h": h, "n": len(g),
                         "MAPE_pct": float(np.mean(np.abs(np.exp(e_ens) - 1)) * 100),
                         "MAPE_rw_pct": float(np.mean(np.abs(np.exp(e_rw) - 1)) * 100),
                         "skill_vs_rw_pct": float((1 - np.abs(e_ens).mean() / np.abs(e_rw).mean()) * 100),
                         "coverage80_pct": float(((g.target >= g.q10) & (g.target <= g.q90)).mean() * 100),
                         "directional_acc_pct": float((np.sign(g.q50) == np.sign(g.target)).mean() * 100),
                         "DM_stat": float(dm), "DM_p": float(2 * (1 - norm.cdf(abs(dm))))})
    return rows


def tune(bt, grid, val=VAL):
    best, tlog = None, []
    for lam in grid["lam"]:
        for delta in grid["delta"]:
            for step in grid["step"]:
                r = bt.run(*val, lam=lam, delta=delta, step_cap=step, strategies=("FS",))
                c = r["FS_cost_t"].values
                T = r["FS_tonnes"].values
                q = np.quantile(c, 0.9)
                score = (c * T).sum() / T.sum() + 0.25 * c[c >= q].mean()
                tlog.append({"lam": lam, "delta": delta, "step": step, "avg": float((c * T).sum() / T.sum()),
                            "cvar90": float(c[c >= q].mean()), "score": float(score)})
                if best is None or score < best["score"]:
                    best = tlog[-1]
                log(f"   tune lam={lam} delta={delta} step={step}: score {score:.3f}")
    return best, tlog


def todays_recommendation(df, meta, fc, lane, params):
    n = len(df)
    t = n - 1
    rows = fc[fc.t == t]
    y0 = {ci: np.log(df[f"tce_{c}"].iloc[t]) for ci, c in enumerate(CLASSES)}
    paths = simulate_paths(rows, y0, n_paths=300, horizon=52, seed=42)
    bt = Backtest(df, meta, fc, lane)
    # next quarter block starting 13 weeks from now (decision window opens today)
    s = t + 13
    c = None
    best = 1e9
    per_class = {}
    for cc in lane.classes:
        k = lane.coef[cc]
        ci = CLASSES.index(cc)
        kk = np.arange(s - BASE_FIX, s + BLOCK - BASE_FIX) - t - 1
        spot = (k["A"] * paths[:, kk, ci] + k["B"] * df["bunker_usd_t"].iloc[t] + k["C"]).mean(axis=1)
        clim = AL.congestion_outlook(df, lane.disch, 26)
        dem = np.mean([lane.dem(cc, clim[min(L + k["laden_w"] - t, 26) - 1]["mean"], np.median(paths[:, min(L - t, 51), ci]))
                       for L in range(s, s + BLOCK, 3)])
        tot = spot + dem + k["inv"] + k["extra"]
        per_class[cc] = {"p10": float(np.quantile(tot, .1)), "p50": float(np.median(tot)), "p90": float(np.quantile(tot, .9)),
                         "cargo_t": k["q"], "voyages": int(np.ceil(lane.Q / k["q"]))}
        if np.median(tot) < best:
            best, c = np.median(tot), cc
    k = lane.coef[c]
    ci = CLASSES.index(c)
    kk = np.arange(s - BASE_FIX, s + BLOCK - BASE_FIX) - t - 1
    b0 = df["bunker_usd_t"].iloc[t]
    spot_s = (k["A"] * paths[:, kk, ci] + k["B"] * b0 + k["C"]).mean(axis=1)
    P_now, fwd = bt.coa_quote(t, c, s)
    H = bt.tc_hire(t, c, s)
    tc_s = k["A"] * H + k["B"] * b0 * np.exp(np.random.default_rng(1).normal(0, 0.05, 300)) + k["C"]
    v_s = np.exp(np.random.default_rng(2).normal(0, 0.08, 300))
    sol = solve_block(spot_s, tc_s, v_s, P_now, lam=params["lam"], step_cap=params["step"])
    # COA quote if we wait w weeks (scenario forward re-quoted from scenario levels)
    mu, phi, beta = meta["mu"][c], meta["phi_mkt"], meta["beta"][c]
    woy = df["woy"].values
    qpaths = np.zeros((300, 12))
    for w in range(1, 13):
        yw = np.log(paths[:, w - 1, ci])
        woy_w = ((woy[t] - 1 + w) % 52) + 1
        hs = np.arange(s - BASE_FIX, s + BLOCK - BASE_FIX) - (t + w)
        s_now = beta * seasonal(woy_w)
        s_h = beta * seasonal(((woy_w - 1 + hs) % 52) + 1)
        fwd_w = np.exp(mu + phi ** hs[None, :] * (yw[:, None] - mu - s_now) + s_h[None, :]).mean(axis=1)
        qpaths[:, w - 1] = lane.freight(c, fwd_w, b0) * (1 + COMMERCIAL["coa_premium"])
    timing = entry_timing(qpaths, P_now)
    return {"asof": str(df.index[t].date()), "block_start": str((df.index[t] + pd.Timedelta(weeks=13)).date()),
            "class": c, "per_class": per_class, "coa_quote": P_now, "tc_hire": H, "fwd_tce": fwd,
            "ladder_now": sol, "timing": timing, "spot_block_p10_p50_p90": [float(np.quantile(spot_s, q)) for q in (.1, .5, .9)],
            "idle_options": IDLE.options(c, H, float(np.median(paths[:, 4, ci])), b0, k["q"], idle_days=6),
            "laycan_spacing_days": IDLE.laycan_spacing(c, lane.disch, k["q"]),
            "two_port_example": PH.two_port_discharge("Capesize", "HAY_POINT", "DHAMRA", "PARADIP")}, paths


def main(fast=False, source="synthetic"):
    """source = 'synthetic' (default demo world) or 'uploaded' (data/uploaded_market.csv via POST /api/data/upload)."""
    T0 = time.time()
    refit = 26 if fast else 13
    log("[1] loading market data (" + source + ")")
    dfp, metap = generate("martingale", seed=23)          # placebo world is always synthetic
    if source == "uploaded":
        from saarthi.data import load_uploaded, windows
        df, meta, prov = load_uploaded()
        fc_start, val, test = windows(df)
        tag = f"up_{prov['sha1']}_"
        filled = ", ".join(prov["filled_from_proxy"][:4]) + (" ..." if len(prov["filled_from_proxy"]) > 4 else "")
        data_label = (f"UPLOADED DATA ({prov['rows']} weeks {prov['start']}..{prov['end']})"
                      + (f" - proxy-filled: {filled}" if prov["filled_from_proxy"] else ""))
    else:
        df, meta = generate("structured")
        fc_start, val, test, tag = FC_START, VAL, TEST, ""
        data_label = "SYNTHETIC (structured world, seed 11) - demo only"
    s0 = int(np.searchsorted(df.index, pd.Timestamp(fc_start)))
    s0p = int(np.searchsorted(dfp.index, pd.Timestamp(FC_START)))

    log("[2] walk-forward forecasts (ensemble)")
    fc, fobj = cached(f"{tag}fc_{refit}", lambda: walk_forward(df, s0, refit_every=refit, verbose=False))
    from saarthi.forecast import FEATS, STRUCT_FEATS
    explain = {}
    for h in (4, 12):
        gain = fobj.models[h][("gbm", 0.5)].booster_.feature_importance("gain")
        imp = sorted(zip(FEATS, (gain / gain.sum() * 100).round(1)), key=lambda x: -x[1])[:10]
        beta = fobj.models[h]["struct"][0]
        explain[f"h{h}"] = {"gbm_gain_pct": imp,
                            "struct_coef": list(zip(["const"] + STRUCT_FEATS, np.round(beta[:1 + len(STRUCT_FEATS)], 4).tolist()))}
    log("    ... random-walk-only forecasts (ablation)")
    fc_rw, _ = cached(f"{tag}fcrw_{refit}", lambda: walk_forward(df, s0, refit_every=refit, members=("rw",), verbose=False))
    log("    ... placebo world forecasts")
    fcp, _ = cached("fcp", lambda: walk_forward(dfp, s0p, refit_every=26, verbose=False))

    log("[3] forecast accuracy report")
    frep = forecast_report(fc, test[0])
    frep_p = forecast_report(fcp, TEST[0])

    lane = Lane("HAY_POINT", "PARADIP", Q=900_000)
    bt = Backtest(df, meta, fc, lane)
    log("[4] decision-focused calibration on validation period")
    grid = {"lam": [0.0, 0.5, 1.5], "delta": [0.0, 0.03], "step": [0.2, 0.35]}
    if fast:
        grid = {"lam": [0.0, 0.5], "delta": [0.0, 0.03], "step": [0.35]}
    best, tune_log = cached(f"{tag}tune_{fast}", lambda: tune(bt, grid, val))
    log(f"    selected: {best}")

    log("[5] test-period backtest")
    res = cached(f"{tag}res_{fast}", lambda: bt.run(*test, lam=best["lam"], delta=best["delta"], step_cap=best["step"]))
    summ = summarise(res)

    log("[6] ablations")
    res_rw = cached(f"{tag}resrw_{fast}", lambda: Backtest(df, meta, fc_rw, lane).run(*test, lam=best["lam"], delta=best["delta"], step_cap=best["step"],
                                                strategies=("B0", "B1", "B2", "FS")))
    summ_rw = summarise(res_rw, strategies=("B0", "B1", "B2", "FS"))
    res_p = cached(f"{tag}resp_{fast}", lambda: Backtest(dfp, metap, fcp, lane).run(*TEST, lam=best["lam"], delta=best["delta"], step_cap=best["step"]))
    summ_p = summarise(res_p)

    log("[7] today's recommendation, alerts, generalisation")
    rec, paths = todays_recommendation(df, meta, fc, lane, best)
    fc_now = fc[fc.t == len(df) - 1]
    alerts = AL.market_alerts(df, fc_now, paths) + AL.congestion_alerts(df)
    lanes = [{"load": l, "disch": d, "routing": ROUTES[l]["routing"]} for l in LOAD for d in DISCHARGE]
    events = EV.impacted(EV.extract_all(), lanes)
    # generalisation: every origin x East-Coast port x class, landed $/t at 8-week median forecast
    gen = []
    b0 = float(df["bunker_usd_t"].iloc[-1])
    for l in LOAD:
        for d in DISCHARGE:
            for c in CLASSES:
                f = PH.check(c, l, d)
                row = {"load": l, "country": LOAD[l]["country"], "disch": d, "cls": c, "feasible": f.feasible,
                       "cargo_t": round(f.cargo_t), "binding": f.binding, "nm": f.nm}
                if f.feasible:
                    tce8 = float(np.median(paths[:, 7, CLASSES.index(c)]))
                    row["landed_usd_t"] = round(PH.landed_freight(c, f, l, d, tce8, b0, DISCHARGE[d]["base_wait_days"] + 1), 2)
                gen.append(row)

    # dashboard payload
    hist = df.iloc[-104:]
    fan = {}
    for ci, c in enumerate(CLASSES):
        p = paths[:, :, ci]
        fan[c] = {"hist_dates": [str(x.date()) for x in hist.index], "hist": hist[f"tce_{c}"].round(0).tolist(),
                  "p10": np.quantile(p, .1, axis=0).round(0).tolist(), "p50": np.median(p, axis=0).round(0).tolist(),
                  "p90": np.quantile(p, .9, axis=0).round(0).tolist(),
                  "weights": {m: float(fc_now[fc_now.cls == ci][f"w_{m}"].mean()) for m in ("gbm", "struct", "rw")}}
    payload = {
        "meta": {"asof": rec["asof"], "data_label": data_label, "source": source, "test_window": test, "val_window": val,
                 "runtime_s": None, "selected_params": best, "tune_log": tune_log},
        "vessels": VESSELS, "discharge": DISCHARGE, "load": LOAD, "routes": {k: v for k, v in ROUTES.items() if not k.startswith("_")},
        "chokepoints": CHOKEPOINTS, "commercial": COMMERCIAL,
        "market": {"mu": meta["mu"], "phi": meta["phi_mkt"], "beta": meta["beta"],
                   "season": [float(seasonal(w)) for w in range(1, 54)], "woy_now": int(df["woy"].iloc[-1]),
                   "bunker_now": b0, "tce_now": {c: float(df[f"tce_{c}"].iloc[-1]) for c in CLASSES}},
        "paths": {c: np.round(paths[:150, :, ci]).astype(int).tolist() for ci, c in enumerate(CLASSES)},
        "congestion": {p: AL.congestion_outlook(df, p, 52) for p in DISCHARGE},
        "fan": fan, "explain": explain, "forecast_report": frep, "forecast_report_placebo": frep_p,
        "backtest": {"summary": summ, "summary_rw_ablation": summ_rw, "summary_placebo": summ_p,
                     "blocks": res[["block_start", "class_model", "B0_cost_t", "B1_cost_t", "B2_cost_t", "B3_cost_t",
                                    "FS_cost_t", "ORC_cost_t", "FS_coa_share", "FS_tc_share", "B0_tonnes"]]
                     .assign(block_start=lambda x: x.block_start.astype(str)).round(3).to_dict("records")},
        "recommendation": rec, "alerts": alerts, "events": events, "generalisation": gen,
    }
    payload["meta"]["runtime_s"] = round(time.time() - T0, 1)
    with open(OUT / "results.json", "w", encoding="utf-8") as f:
        json.dump(payload, f, default=lambda o: o.item() if hasattr(o, "item") else str(o), indent=1)
    res.to_csv(OUT / "backtest_blocks.csv", index=False)
    pd.DataFrame(frep).to_csv(OUT / "forecast_accuracy.csv", index=False)
    from build_dashboard import build
    build(payload)
    log(f"done in {time.time() - T0:.0f}s -> outputs/results.json, outputs/dashboard.html")
    print(json.dumps({k: {kk: (round(vv, 2) if isinstance(vv, float) else vv) for kk, vv in v.items()} for k, v in summ.items()}, indent=1))
    print("placebo FS vs B1:", round(summ_p["FS"]["avg_cost_usd_t"], 3), round(summ_p["B1"]["avg_cost_usd_t"], 3))
    print("RW-ablation FS:", round(summ_rw["FS"]["avg_cost_usd_t"], 3))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--fast", action="store_true")
    ap.add_argument("--source", choices=["synthetic", "uploaded"], default="synthetic")
    a = ap.parse_args()
    main(a.fast, a.source)
