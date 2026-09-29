"""Server-side charter planner: any origin x East-Coast port x volume x duration.

Uses the pipeline's forecast scenario paths (outputs/results.json) + the physics engine +
the real Charter-Ladder CVaR LP (saarthi.optimizer.solve_block).
"""
import math

import numpy as np

from saarthi import physics as PH
from saarthi import idle as IDLE
from saarthi.config import CLASSES, VESSELS, DISCHARGE, LOAD, COMMERCIAL
from saarthi.optimizer import solve_block


def _r(x, d=2):
    return None if x is None or (isinstance(x, float) and math.isnan(x)) else round(float(x), d)


class Planner:
    def __init__(self, R):
        self.R = R
        self.paths = np.stack([np.asarray(R["paths"][c], float) for c in CLASSES], axis=2)  # (S, 52, 4)
        self.S, self.H = self.paths.shape[:2]
        self.m = R["market"]
        self.season = np.asarray(self.m["season"], float)
        self.cong = {p: np.asarray([r["mean"] for r in o], float) for p, o in R["congestion"].items()}
        rng = np.random.default_rng(7)
        self.v_s = np.exp(rng.normal(0, 0.08, self.S))       # programme-volume uncertainty
        self.bnoise = np.exp(rng.normal(0, 0.06, self.S))    # bunker uncertainty over the contract

    # ---------------- market helpers ----------------
    def seas(self, w):
        return self.season[(np.asarray(w, int) - 1) % 52]

    def fwd_avg(self, c, y, woy, hs):
        """market consensus forward TCE averaged over horizons hs; y scalar or (S,)"""
        mu, b, phi = self.m["mu"][c], self.m["beta"][c], self.m["phi"]
        scalar = np.ndim(y) == 0
        hs = np.asarray(hs, float)
        y = np.asarray(y, float)[..., None]
        f = np.exp(mu + phi ** hs * (y - mu - b * self.seas(woy)) + b * self.seas(woy + hs))
        r = f.mean(axis=-1)
        return float(r.reshape(-1)[0]) if scalar else r

    # ---------------- lane economics ----------------
    @staticmethod
    def coef(c, f, load, disch):
        v, lp, dp = VESSELS[c], LOAD[load], DISCHARGE[disch]
        la, ba, po = PH.voyage_days(c, f, load, disch, lp["base_wait_days"], PH.class_wait(c, disch, dp["base_wait_days"]))
        k = (1 + COMMERCIAL["commission"]) / f.cargo_t
        fuel = la * v["fuel_laden_tpd"] + ba * v["fuel_ballast_tpd"] + po * v["fuel_port_tpd"]
        return dict(A=(la + ba + po) * k, B=fuel * k, C=2 * v["port_cost_usd"] * k, q=f.cargo_t,
                    laden_w=math.ceil(la / 7), days=la + ba + po, la=la, ba=ba, po=po,
                    inv=PH.inventory_per_t(f.cargo_t), extra=dp.get("lighterage_usd_t", 0.0),
                    disch_days=f.cargo_t / PH.handling_rate(dp, c))

    @staticmethod
    def dem(c, disch, wait, tce, q):
        dp = DISCHARGE[disch]
        normal = PH.class_wait(c, disch, dp["base_wait_days"]) + COMMERCIAL["laytime_allow_days"]
        return np.maximum(0.0, PH.class_wait(c, disch, wait) - normal) * tce * COMMERCIAL["dem_factor"] / q

    def evaluate(self, c, rq, disch=None):
        disch = disch or rq["disch"]
        f = PH.check(c, rq["load"], disch, rq["monsoon"], rq["stem"] or None,
                     avoid_chokepoints=("SUEZ",) if rq["avoid_suez"] else ())
        if not f.feasible:
            return {"cls": c, "feasible": False, "binding": f.binding, "notes": f.notes}
        k = self.coef(c, f, rq["load"], disch)
        n = max(1, math.ceil(rq["volume"] / k["q"]))
        lays = np.array([rq["lead"] + round(i * rq["duration"] / n) for i in range(n)])
        fixw = np.clip(lays - 3, 1, self.H)
        arrw = np.clip(lays + k["laden_w"], 1, self.H)
        waits = self.cong[disch][arrw - 1] + rq["congestion_add"] + (DISCHARGE[disch]["monsoon_wait_add"] * 0.5 if rq["monsoon"] else 0.0)
        ci = CLASSES.index(c)
        P = self.paths[:, fixw - 1, ci] * (1 + rq["freight_shock"])            # (S, n)
        bunker = self.m["bunker_now"] * (1 + rq["bunker_change"])
        spot = (k["A"] * P + k["B"] * bunker + k["C"]).mean(axis=1)
        dem = self.dem(c, disch, waits[None, :], P, k["q"]).mean(axis=1)
        land = spot + dem + k["inv"] + k["extra"]
        return {"cls": c, "feasible": True, "f": f, "k": k, "n": n, "lays": lays, "fixw": fixw, "waits": waits,
                "spot": spot, "dem": dem, "land": land, "bunker": bunker, "P": P,
                "binding": f.binding, "notes": f.notes}

    # ---------------- contract mix ----------------
    def mix_cost(self, E, a, b, Pcoa, tcu):
        tol, dfr = COMMERCIAL["coa_tolerance"], COMMERCIAL["deadfreight_frac"]
        v = self.v_s
        bt = np.minimum(b, v)
        rem = v - bt
        want = np.where(E["spot"] > Pcoa, a * (1 + tol), a * (1 - tol))
        lift = np.minimum(rem, want)
        dead = np.maximum(0, a * (1 - tol) - lift)
        extra = E["dem"] + E["k"]["inv"] + E["k"]["extra"]
        return (bt * tcu + lift * Pcoa + dead * Pcoa * dfr + (rem - lift) * E["spot"]) / v + extra

    def plan(self, rq):
        rq = dict(rq)
        rq["duration"] = int(min(max(rq["duration"], 4), 48))
        rq["lead"] = int(min(max(rq["lead"], 2), 12))
        evals = {c: self.evaluate(c, rq) for c in CLASSES}
        feas = [c for c in CLASSES if evals[c]["feasible"]]
        if not feas:
            return {"ok": False, "message": "No vessel class is feasible for this lane under the current constraints.",
                    "classes": [{"cls": c, "feasible": False, "binding": evals[c]["binding"]} for c in CLASSES]}
        best = min(feas, key=lambda c: np.median(evals[c]["land"]))
        E = evals[best]
        k, ci = E["k"], CLASSES.index(best)
        habit = "Panamax" if evals["Panamax"]["feasible"] else ([c for c in feas if c != "Capesize"] or [best])[-1]

        y0 = math.log(self.m["tce_now"][best])
        woy = self.m["woy_now"]
        Pcoa = float((k["A"] * self.fwd_avg(best, y0, woy, E["fixw"]) + k["B"] * self.m["bunker_now"] + k["C"]) * (1 + COMMERCIAL["coa_premium"]))
        hs_tc = np.arange(rq["lead"], rq["lead"] + rq["duration"])
        Hire = float(self.fwd_avg(best, y0, woy, hs_tc) * (1 + COMMERCIAL["tc_premium"]))
        tc_s = k["A"] * Hire + k["B"] * E["bunker"] * self.bnoise + k["C"]
        tcu = float(np.mean(tc_s))
        sol = solve_block(E["spot"], tc_s, self.v_s, Pcoa, lam=rq["risk_lambda"], max_lock=0.85, step_cap=0.85, tc_cap=0.4)
        a, b = max(float(sol.get("a", 0.0)), 0.0) + 0.0, max(float(sol.get("b", 0.0)), 0.0) + 0.0
        mix = self.mix_cost(E, a, b, Pcoa, tcu)
        allspot = self.mix_cost(E, 0.0, 0.0, Pcoa, tcu)
        habit_cost = evals[habit]["land"]

        # entry timing: re-quote of the COA if SAIL waits w weeks
        timing = []
        wmax = int(min(12, E["fixw"].min()))
        for w in range(1, wmax + 1):
            yw = np.log(self.paths[:, w - 1, ci] * (1 + rq["freight_shock"]))
            hs = np.maximum(E["fixw"] - w, 0)
            qs = (k["A"] * self.fwd_avg(best, yw, woy + w, hs) + k["B"] * E["bunker"] + k["C"]) * (1 + COMMERCIAL["coa_premium"])
            timing.append({"w": w, "p10": _r(np.quantile(qs, .1)), "p50": _r(np.median(qs)), "p90": _r(np.quantile(qs, .9)),
                           "p_cheaper": _r((qs < Pcoa).mean(), 3)})
        best_wait = min(timing, key=lambda t: t["p50"]) if timing else None
        defer = bool(best_wait and best_wait["p_cheaper"] > 0.6 and (Pcoa - best_wait["p50"]) / Pcoa > 0.02)

        lock = a + b
        tranches, left, wk = [], lock, 0
        while left > 1e-3:
            s = min(0.35, left)
            tranches.append({"week": wk, "share": _r(s, 3)})
            left -= s
            wk = best_wait["w"] if (defer and wk == 0) else wk + 2
        if lock < 0.05:
            action = "Stay spot for now - forecast and risk do not justify locking cover this week. Re-check weekly."
        elif defer:
            action = f"Lock the first tranche now, defer the rest ~{best_wait['w']} weeks (quote expected to soften)."
        else:
            action = "Lock the recommended cover now as a ladder of tranches."

        # alternate-port hint
        alt = None
        for p in DISCHARGE:
            if p == rq["disch"]:
                continue
            for c in CLASSES:
                e2 = self.evaluate(c, rq, disch=p)
                if e2["feasible"]:
                    med = float(np.median(e2["land"]))
                    if alt is None or med < alt["landed_p50"]:
                        alt = {"port": p, "name": DISCHARGE[p]["name"], "cls": c, "landed_p50": _r(med)}
        med_best = float(np.median(E["land"]))
        if alt and alt["landed_p50"] >= 0.9 * med_best:
            alt = None
        elif alt:
            alt["max_inland_diff"] = _r(med_best - alt["landed_p50"])

        # X-ray
        xray = {"p10": _r(np.quantile(E["spot"], .1)), "p50": _r(np.median(E["spot"])), "p90": _r(np.quantile(E["spot"], .9))}
        if rq.get("broker_quote"):
            pr = float((E["spot"] <= rq["broker_quote"]).mean())
            xray.update({"quote": rq["broker_quote"], "percentile": _r(pr * 100, 0),
                         "verdict": "expensive - counter near P50" if pr > 0.7 else ("attractive - consider fixing" if pr < 0.3 else "fair range")})

        days = rq["duration"] * 7
        nv = int(days // k["days"])
        util = {"round_voyage_days": _r(k["days"], 1), "laden_days": _r(k["la"], 1), "ballast_days": _r(k["ba"], 1),
                "port_days": _r(k["po"], 1), "voyages_per_ship": nv, "idle_days_per_ship": _r(days - nv * k["days"], 1),
                "ships_on_tc": _r(b * rq["volume"] / (k["q"] * max(nv, 1)), 1), "ballast_share": _r(k["ba"] / k["days"], 3),
                "laycan_spacing_days": _r(k["disch_days"] + 1.5, 1)}

        # explanation
        med4 = float(np.median(self.paths[:, 3, ci])) / self.m["tce_now"][best] - 1
        med12 = float(np.median(self.paths[:, 11, ci])) / self.m["tce_now"][best] - 1
        why = [f"{best} carries {E['f'].cargo_t:,.0f} t per voyage; binding constraint: {E['f'].binding}.",
               f"Forecast {best} TCE: {med4:+.1%} in 4 weeks, {med12:+.1%} in 12 weeks (median of {self.S} scenarios).",
               f"Recommended mix cuts the bad-case (CVaR90) cost from ${np.mean(np.sort(allspot)[int(.9 * self.S):]):.2f} to ${np.mean(np.sort(mix)[int(.9 * self.S):]):.2f}/t vs all-spot.",
               f"Expected waiting at {DISCHARGE[rq['disch']]['name']} on arrival: {E['waits'].mean():.1f} days (congestion forecast).",
               f"COA quote today ${Pcoa:.2f}/t vs expected spot ${np.mean(E['spot']):.2f}/t over the fixing windows."]
        for c in CLASSES:
            if not evals[c]["feasible"]:
                why.append(f"{c} excluded: {evals[c]['binding']}.")
        lane_alerts = [a_ for a_ in self.R["alerts"] if a_.get("cls") == best or a_.get("port") == rq["disch"]]
        lane_events = [e for e in self.R["events"] if any(rq["load"] in l or rq["disch"] in l or "ALL" in l for l in e.get("impacted_lanes", []))]

        def summ(x):
            s = np.sort(x)
            return {"mean": _r(x.mean()), "p10": _r(np.quantile(x, .1)), "p50": _r(np.median(x)), "p90": _r(np.quantile(x, .9)),
                    "cvar90": _r(s[int(.9 * len(s)):].mean())}

        classes = []
        for c in CLASSES:
            e = evals[c]
            if not e["feasible"]:
                classes.append({"cls": c, "feasible": False, "binding": e["binding"]})
                continue
            classes.append({"cls": c, "feasible": True, "cargo_t": round(e["k"]["q"]), "binding": e["binding"], "notes": e["notes"],
                            "voyages": e["n"], "round_voyage_days": _r(e["k"]["days"], 1), "laden_draft_m": e["f"].arrival_draft_m,
                            "nm": e["f"].nm, **summ(e["land"])})
        ms = summ(mix)
        return {
            "ok": True, "request": rq, "best_class": best, "habit_class": habit,
            "parcel_t": round(k["q"]), "voyages": E["n"], "binding": E["binding"], "notes": E["notes"],
            "mix": {"coa": _r(a, 3), "tc": _r(b, 3), "spot": _r(max(0.0, 1 - a - b), 3)},
            "coa_quote": _r(Pcoa), "tc_hire": _r(Hire, 0), "tc_unit_cost": _r(tcu),
            "cost": ms, "all_spot": summ(allspot), "habit": summ(habit_cost),
            "programme_musd": _r(ms["mean"] * rq["volume"] / 1e6, 2),
            "saving_vs_habit_musd": _r((np.median(habit_cost) - ms["mean"]) * rq["volume"] / 1e6, 2),
            "saving_vs_habit_pct": _r((np.median(habit_cost) - ms["mean"]) / np.median(habit_cost) * 100, 1),
            "freight_per_t_hot_metal": _r(ms["mean"] * COMMERCIAL["coal_per_thm"]),
            "action": action, "tranches": tranches, "timing": timing, "xray": xray, "alternate_port": alt,
            "utilisation": util, "why": why, "alerts": lane_alerts, "events": lane_events, "classes": classes,
            "hist": {"mix": np.round(mix, 3).tolist(), "all_spot": np.round(allspot, 3).tolist(), "habit": np.round(habit_cost, 3).tolist()},
            "lp": {k_: _r(v_, 4) if isinstance(v_, float) else v_ for k_, v_ in sol.items()},
        }

    # ---------------- other live computations ----------------
    def feasibility(self, load, disch, monsoon=False, stem=0, avoid_suez=False):
        av = ("SUEZ",) if avoid_suez else ()
        lane = []
        for c in CLASSES:
            f = PH.check(c, load, disch, monsoon, stem or None, av)
            lane.append({"cls": c, "feasible": f.feasible, "cargo_t": round(f.cargo_t), "binding": f.binding,
                         "laden_draft_m": f.arrival_draft_m, "notes": f.notes, "nm": f.nm, "utilisation": _r(f.utilisation, 3)})
        matrix = {p: {c: (lambda f: {"feasible": f.feasible, "cargo_t": round(f.cargo_t), "binding": f.binding})(
            PH.check(c, load, p, monsoon, stem or None, av)) for c in CLASSES} for p in DISCHARGE}
        two = PH.two_port_discharge("Capesize", load, "DHAMRA", "PARADIP") if PH.check("Capesize", load, "DHAMRA").feasible else None
        return {"load": load, "disch": disch, "lane": lane, "matrix": matrix, "two_port": two}

    def idle(self, cls="Capesize", load="HAY_POINT", disch="PARADIP", idle_days=6.0):
        f = PH.check(cls, load, disch)
        if not f.feasible:
            return {"ok": False, "message": f"{cls} not feasible on {load}->{disch}: {f.binding}"}
        ci = CLASSES.index(cls)
        tce5 = float(np.median(self.paths[:, 4, ci]))
        hire = float(self.fwd_avg(cls, math.log(self.m["tce_now"][cls]), self.m["woy_now"], np.arange(1, 14)))
        opts = IDLE.options(cls, hire, tce5, self.m["bunker_now"], f.cargo_t, idle_days, load, disch)
        return {"ok": True, "cls": cls, "hire": _r(hire, 0), "tce_forecast": _r(tce5, 0), "idle_days": idle_days,
                "options": opts, "laycan_spacing_days": IDLE.laycan_spacing(cls, disch, f.cargo_t)}

    def ticker(self):
        items = []
        for ci, c in enumerate(CLASSES):
            now = self.m["tce_now"][c]
            m4 = float(np.median(self.paths[:, 3, ci]))
            items.append({"label": f"{c.upper()} TCE", "value": f"${now:,.0f}/d", "change": _r((m4 / now - 1) * 100, 1), "note": "4w fcst"})
        items.append({"label": "VLSFO", "value": f"${self.m['bunker_now']:,.0f}/t", "change": None, "note": "bunker"})
        for p in ("PARADIP", "DHAMRA", "VIZAG", "HALDIA", "GANGAVARAM"):
            items.append({"label": f"{p} WAIT", "value": f"{self.cong[p][0]:.1f} d", "change": _r(self.cong[p][7] - self.cong[p][0], 1), "note": "8w Δ days"})
        return items
