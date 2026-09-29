"""Rolling (walk-forward) decision backtest: FreightSaarthi vs the 'daily spot' baseline.

Timeline per cargo block b (13-week quarter, start week s_b, nominal volume Q):
   s_b-13 ........ s_b-6 | s_b-5 ............................ s_b+12
   [ COA/TC ladder window ][ spot fixing windows [L-5, L-1] for each cargo laycan L ]
Every decision uses ONLY information available that week: walk-forward forecasts refitted every
13 weeks on data up to that week, market quotes of that week, climatology up to that week.

Strategies (same realised world, same cargo programme):
   B0  Daily spot (current practice): Panamax habit, each cargo fixed ~3 weeks before laycan
   B1  Spot + optimal vessel class (feasibility engine + forecast)
   B2  B1 + forecast-timed spot fixing (optimal-stopping rule)
   B3  'COA without a model': 70% COA locked at first window week, rest daily spot (control)
   FS  FreightSaarthi: vessel optimisation + CVaR charter ladder (COA/TC) + timed spot
   ORC Perfect-foresight oracle (upper bound on achievable savings)
"""
import math

import numpy as np
import pandas as pd

from .config import CLASSES, COMMERCIAL, DISCHARGE, VESSELS
from . import physics as PH
from .forecast import interp_quantiles, simulate_paths
from .optimizer import solve_block
from .synth import market_forward_log

BLOCK = 13
WIN0, WIN1 = 13, 6       # COA window: [s-13, s-6]
SPOT_EARLY, SPOT_LATE, BASE_FIX = 5, 1, 3


class Lane:
    def __init__(self, load="HAY_POINT", disch="PARADIP", Q=900_000):
        self.load, self.disch, self.Q = load, disch, Q
        self.coef, self.feas = {}, {}
        for c in CLASSES:
            f = PH.check(c, load, disch)
            self.feas[c] = f
            if not f.feasible:
                continue
            v = VESSELS[c]
            lp, dp = PH.LOAD[load], DISCHARGE[disch]
            la, ba, po = PH.voyage_days(c, f, load, disch, lp["base_wait_days"],
                                        PH.class_wait(c, disch, dp["base_wait_days"]))
            k = (1 + COMMERCIAL["commission"]) / f.cargo_t
            fuel = la * v["fuel_laden_tpd"] + ba * v["fuel_ballast_tpd"] + po * v["fuel_port_tpd"]
            self.coef[c] = dict(A=(la + ba + po) * k, B=fuel * k, C=2 * v["port_cost_usd"] * k,
                                q=f.cargo_t, laden_w=math.ceil(la / 7), days=la + ba + po,
                                inv=PH.inventory_per_t(f.cargo_t), extra=dp.get("lighterage_usd_t", 0.0))
        self.classes = list(self.coef)

    def freight(self, c, tce, bunker):
        k = self.coef[c]
        return k["A"] * tce + k["B"] * bunker + k["C"]

    def dem(self, c, wait, tce):
        dp = DISCHARGE[self.disch]
        normal = PH.class_wait(c, self.disch, dp["base_wait_days"]) + COMMERCIAL["laytime_allow_days"]
        return max(0.0, PH.class_wait(c, self.disch, wait) - normal) * tce * COMMERCIAL["dem_factor"] / self.coef[c]["q"]


class Backtest:
    def __init__(self, df, meta, fc_out, lane=None, seed=5, n_paths=200):
        self.df, self.meta, self.lane = df, meta, lane or Lane()
        self.n = len(df)
        self.tce = {c: df[f"tce_{c}"].values for c in CLASSES}
        self.bunker = df["bunker_usd_t"].values
        self.wait = df[f"wait_{self.lane.disch}"].values
        self.woy = df["woy"].values
        self.fc = {t: g for t, g in fc_out.groupby("t")}
        self.rng = np.random.default_rng(seed)
        self.n_paths = n_paths
        self.bvol = np.nanstd(np.diff(np.log(self.bunker)))
        self.first_fc = min(self.fc)

    # ---------------- helpers ----------------
    def blocks(self, start_date, end_date):
        s0 = int(np.searchsorted(self.df.index, pd.Timestamp(start_date)))
        e = int(np.searchsorted(self.df.index, pd.Timestamp(end_date)))
        out = []
        s = s0
        while s + BLOCK <= min(e, self.n - 1) and s - WIN0 >= self.first_fc:
            out.append(s)
            s += BLOCK
        return out

    def volume(self, s):
        return float(np.exp(np.random.default_rng(1000 + s).normal(0, 0.08)))

    def laycans(self, s, c, v):
        n = max(1, math.ceil(v * self.lane.Q / self.lane.coef[c]["q"]))
        return [s + int(round(i * BLOCK / n)) for i in range(n)]

    def median_tce_path(self, t, c, H):
        rows = self.fc[t]
        ci = CLASSES.index(c)
        med, _, _ = interp_quantiles(rows[rows["cls"] == ci], np.arange(1, H + 1))
        return np.exp(np.log(self.tce[c][t]) + med)

    def wait_clim(self, t, weeks):
        """expected waiting at future weeks: week-of-year climatology from history up to t"""
        hist = pd.Series(self.wait[:t + 1], index=self.woy[:t + 1])
        clim = hist.groupby(level=0).mean()
        return np.array([clim.get(self.woy[min(w, self.n - 1)], hist.mean()) for w in weeks])

    def choose_class(self, t, s, model=True):
        if not model:
            return "Panamax"
        best, bc = None, 1e9
        for c in self.lane.classes:
            k = self.lane.coef[c]
            H = s + BLOCK - t
            path = self.median_tce_path(t, c, H)
            tce_blk = path[s - BASE_FIX - t - 1: s + BLOCK - BASE_FIX - t].mean()
            fr = self.lane.freight(c, tce_blk, self.bunker[t])
            arr = [L + k["laden_w"] for L in self.laycans(s, c, 1.0)]
            dem = np.mean([self.lane.dem(c, w, tce_blk) for w in self.wait_clim(t, arr)])
            cost = fr + dem + k["inv"] + k["extra"]
            if cost < bc:
                best, bc = c, cost
        return best

    def coa_quote(self, t, c, s):
        """owner's fixed-price multi-voyage COA quote ($/t) for block s made at week t"""
        fix_weeks = np.arange(s - BASE_FIX, s + BLOCK - BASE_FIX) - t
        fwd = np.exp(market_forward_log(self.df, self.meta, c, t, fix_weeks)).mean()
        return self.lane.freight(c, fwd, self.bunker[t]) * (1 + COMMERCIAL["coa_premium"]), fwd

    def tc_hire(self, t, c, s):
        fix_weeks = np.arange(s, s + BLOCK) - t
        return np.exp(market_forward_log(self.df, self.meta, c, t, fix_weeks)).mean() * (1 + COMMERCIAL["tc_premium"])

    def timed_fix_week(self, L, c, delta):
        """optimal-stopping rule: fix at week f if current TCE <= (1+delta) x min forecast median of
        the remaining weeks in the window; otherwise wait; forced fix at L-1."""
        for f in range(L - SPOT_EARLY, L - SPOT_LATE):
            rem = (L - SPOT_LATE) - f
            if f not in self.fc:
                return L - BASE_FIX
            path = self.median_tce_path(f, c, rem)
            if self.tce[c][f] <= (1 + delta) * path.min():
                return f
        return L - SPOT_LATE

    # ---------------- realised cost of a block ----------------
    def realise(self, s, c, v, coa=(), tc=(), timed=False, delta=0.0):
        k = self.lane.coef[c]
        Ls = self.laycans(s, c, v)
        spot_costs, dems = [], []
        for L in Ls:
            f = self.timed_fix_week(L, c, delta) if timed else L - BASE_FIX
            spot_costs.append(self.lane.freight(c, self.tce[c][f], self.bunker[f]))
            arr = min(L + k["laden_w"], self.n - 1)
            dems.append(self.lane.dem(c, self.wait[arr], self.tce[c][arr]))
        spot_avg = float(np.mean(spot_costs))
        n_spot_fixtures = len(Ls)
        bt = sum(sh for sh, _ in tc)
        tc_cost = 0.0
        if bt > 0:
            b_real = np.mean(self.bunker[s:s + BLOCK])
            for sh, H in tc:
                tc_cost += sh * self.lane.freight(c, H, b_real)
            surplus = max(0.0, bt - v)
            tc_cost -= surplus * (1 - COMMERCIAL["relet_haircut"]) * self.lane.freight(c, np.mean(self.tce[c][s:s + BLOCK]), b_real)
        rem = v - min(bt, v)
        tol, dfr = COMMERCIAL["coa_tolerance"], COMMERCIAL["deadfreight_frac"]
        coa_cost, lifted = 0.0, 0.0
        for sh, P in sorted(coa, key=lambda x: x[1]):          # lift cheapest tranche first
            cap_hi, cap_lo = sh * (1 + tol), sh * (1 - tol)
            want = cap_hi if spot_avg > P else cap_lo
            lift = min(max(rem - lifted, 0.0), want)
            dead = max(0.0, cap_lo - lift)
            coa_cost += lift * P + dead * P * dfr
            lifted += lift
        spot_vol = max(0.0, rem - lifted)
        if coa or tc:
            n_spot_fixtures = math.ceil(spot_vol * self.lane.Q / k["q"] - 1e-9)
        total = (tc_cost + coa_cost + spot_vol * spot_avg) / v + np.mean(dems) + k["inv"] + k["extra"]
        return {"cost_t": total, "tonnes": v * self.lane.Q, "class": c, "coa_share": sum(x for x, _ in coa),
                "tc_share": bt, "spot_share": spot_vol / v, "n_spot_fixtures": n_spot_fixtures,
                "dem_t": float(np.mean(dems)), "n_cargo": len(Ls)}

    def oracle(self, s, v):
        best = 1e9
        for c in self.lane.classes:
            k = self.lane.coef[c]
            Ls = self.laycans(s, c, v)
            spot = np.mean([min(self.lane.freight(c, self.tce[c][f], self.bunker[f])
                                for f in range(L - SPOT_EARLY, L - SPOT_LATE + 1)) for L in Ls])
            coa = min(self.coa_quote(t, c, s)[0] for t in range(s - WIN0, s - WIN1 + 1))
            b_real = np.mean(self.bunker[s:s + BLOCK])
            tc = min(self.lane.freight(c, self.tc_hire(t, c, s), b_real) for t in range(s - WIN0, s - WIN1 + 1))
            dem = np.mean([self.lane.dem(c, self.wait[min(L + k["laden_w"], self.n - 1)],
                                         self.tce[c][min(L + k["laden_w"], self.n - 1)]) for L in Ls])
            best = min(best, min(spot, coa, tc) + dem + k["inv"] + k["extra"])
        return best

    # ---------------- the FreightSaarthi ladder for one block ----------------
    def ladder(self, s, c, lam, step_cap, max_lock=0.85, alpha=0.9):
        k = self.lane.coef[c]
        coa, tc, log = [], [], []
        Ls_nom = self.laycans(s, c, 1.0)
        for t in range(s - WIN0, s - WIN1 + 1):
            rows = self.fc[t]
            y0 = {ci: np.log(self.tce[cc][t]) for ci, cc in enumerate(CLASSES)}
            paths = simulate_paths(rows, y0, n_paths=self.n_paths, horizon=26, seed=t)
            ci = CLASSES.index(c)
            kk = np.clip(np.array([L - BASE_FIX - t for L in Ls_nom]) - 1, 0, 25)
            bpath = self.bunker[t] * np.exp(np.cumsum(self.rng.normal(0, self.bvol, (self.n_paths, 26)), axis=1))
            spot_s = (k["A"] * paths[:, kk, ci] + k["B"] * bpath[:, kk] + k["C"]).mean(axis=1)
            P_now, _ = self.coa_quote(t, c, s)
            H = self.tc_hire(t, c, s)
            blk = np.clip(np.arange(s, s + BLOCK) - t - 1, 0, 25)
            tc_s = k["A"] * H + k["B"] * bpath[:, blk].mean(axis=1) + k["C"]
            v_s = np.exp(self.rng.normal(0, 0.08, self.n_paths))
            a_prev = sum(x for x, _ in coa)
            P_prev = (sum(x * p for x, p in coa) / a_prev) if a_prev > 0 else 0.0
            b_prev = sum(x for x, _ in tc)
            H_prev = (sum(x * h for x, h in tc) / b_prev) if b_prev > 0 else 0.0
            tc_prev_s = k["A"] * H_prev + k["B"] * bpath[:, blk].mean(axis=1) + k["C"]
            sol = solve_block(spot_s, tc_s, v_s, P_now, a_prev, P_prev, b_prev, tc_prev_s,
                              lam=lam, alpha=alpha, max_lock=max_lock, step_cap=step_cap)
            if sol.get("a", 0) > 0.01:
                coa.append((round(sol["a"], 3), P_now))
            if sol.get("b", 0) > 0.01:
                tc.append((round(sol["b"], 3), H))
            log.append({"t": t, "a": sol.get("a", 0), "b": sol.get("b", 0), "P_now": P_now,
                        "spot_mean": float(spot_s.mean()), "exp_cost": sol.get("exp_cost")})
        return coa, tc, log

    # ---------------- run all strategies ----------------
    def run(self, start, end, lam=0.5, delta=0.02, step_cap=0.35, strategies=("B0", "B1", "B2", "B3", "FS", "ORC")):
        recs = []
        for s in self.blocks(start, end):
            v = self.volume(s)
            t0 = s - WIN0
            c_model = self.choose_class(t0, s, model=True)
            row = {"block_start": self.df.index[s], "v": v, "class_model": c_model}
            if "B0" in strategies:
                r = self.realise(s, "Panamax", v); row.update({f"B0_{k}": x for k, x in r.items()})
            if "B1" in strategies:
                r = self.realise(s, c_model, v); row.update({f"B1_{k}": x for k, x in r.items()})
            if "B2" in strategies:
                r = self.realise(s, c_model, v, timed=True, delta=delta); row.update({f"B2_{k}": x for k, x in r.items()})
            if "B3" in strategies:
                P, _ = self.coa_quote(t0, "Panamax", s)
                r = self.realise(s, "Panamax", v, coa=[(0.7, P)]); row.update({f"B3_{k}": x for k, x in r.items()})
            if "FS" in strategies:
                coa, tc, _ = self.ladder(s, c_model, lam, step_cap)
                r = self.realise(s, c_model, v, coa=coa, tc=tc, timed=True, delta=delta)
                row.update({f"FS_{k}": x for k, x in r.items()})
            if "ORC" in strategies:
                row["ORC_cost_t"] = self.oracle(s, v)
                row["ORC_tonnes"] = v * self.lane.Q
            recs.append(row)
        return pd.DataFrame(recs)


def summarise(res, strategies=("B0", "B1", "B2", "B3", "FS"), base="B0", n_boot=2000, seed=0):
    """Headline decision metrics + block-bootstrap confidence intervals for savings."""
    rng = np.random.default_rng(seed)
    out = {}
    T = res[f"{base}_tonnes"].values
    base_cost = res[f"{base}_cost_t"].values
    orc = res["ORC_cost_t"].values if "ORC_cost_t" in res else None
    for st in list(strategies) + (["ORC"] if orc is not None else []):
        c = res[f"{st}_cost_t"].values
        tot = (c * T).sum()
        sav = (base_cost - c) * T
        boots = []
        for _ in range(n_boot):
            i = rng.integers(0, len(c), len(c))
            boots.append(sav[i].sum() / (base_cost[i] * T[i]).sum() * 100)
        q = np.quantile(c, 0.9)
        d = {"avg_cost_usd_t": tot / T.sum(), "total_cost_musd": tot / 1e6,
             "saving_vs_base_pct": sav.sum() / (base_cost * T).sum() * 100,
             "saving_ci90_pct": [float(np.quantile(boots, 0.05)), float(np.quantile(boots, 0.95))],
             "saving_musd": sav.sum() / 1e6, "std_block_cost": float(np.std(c)),
             "cvar90_block_cost": float(c[c >= q].mean()), "worst_block_cost": float(c.max()),
             "win_rate_vs_base": float((c < base_cost - 1e-9).mean())}
        if orc is not None and st != "ORC":
            gap = (base_cost - orc) * T
            d["oracle_capture_pct"] = sav.sum() / gap.sum() * 100 if gap.sum() > 0 else float("nan")
        if f"{st}_n_spot_fixtures" in res:
            d["spot_fixtures"] = int(res[f"{st}_n_spot_fixtures"].sum())
            d["contracted_share_pct"] = float(((res[f"{st}_coa_share"] + res[f"{st}_tc_share"]) / res["v"]).mean() * 100)
            d["avg_demurrage_usd_t"] = float(res[f"{st}_dem_t"].mean())
        out[st] = d
    return out
