"""Charter-portfolio optimiser: 'Charter Ladder' two-stage stochastic LP with CVaR.

At decision week t for an upcoming cargo block (e.g. next quarter's Australia->Paradip programme):
  first stage (now):  a  = new COA share locked at today's COA quote P
                      b  = new period-TC share locked at today's TC-derived unit cost
  second stage (per scenario s, after rates and actual volume v_s are revealed):
                      lift_prev_s, lift_s  - COA liftings within +/-tol (MOLCHOPT)
                      dead_prev_s, dead_s  - dead-freight if liftings < (1-tol) x contracted
                      spot remainder = v_s - TC - liftings, paid at scenario spot cost
minimise  E[cost] + lambda * CVaR_alpha[cost]      (Rockafellar-Uryasev linearisation)
s.t.      total locked <= max_lock, weekly ladder step <= step_cap, TC <= tc_cap * min(v)
Solved with HiGHS via scipy.optimize.linprog (~1 ms-50 ms).
"""
import numpy as np
from scipy.optimize import linprog

from .config import COMMERCIAL


def solve_block(spot_s, tc_s, v_s, P_now, a_prev=0.0, P_prev=0.0, b_prev=0.0, tc_prev_s=None,
                lam=0.5, alpha=0.9, max_lock=0.85, step_cap=0.35, tc_cap=0.4, allow_tc=True):
    S = len(spot_s)
    tol = COMMERCIAL["coa_tolerance"]
    dfr = COMMERCIAL["deadfreight_frac"]
    tc_prev_s = np.zeros(S) if tc_prev_s is None else tc_prev_s
    # variable layout: [a, b, u, lift_prev(S), dead_prev(S), lift(S), dead(S), z(S)]
    nv = 3 + 5 * S
    ia, ib, iu = 0, 1, 2
    LP, DP, LN, DN, Z = (3 + k * S for k in range(5))
    c = np.zeros(nv)
    # cost_s = b_prev*tc_prev_s + b*tc_s + P_prev*(lift_prev + dfr*dead_prev) + P_now*(lift + dfr*dead)
    #          + spot_s*(v_s - b_prev - b - lift_prev - lift)
    # coefficient of each variable inside cost_s:
    coef_b = tc_s - spot_s
    coef_lp = P_prev - spot_s
    coef_dp = P_prev * dfr * np.ones(S)
    coef_ln = P_now - spot_s
    coef_dn = P_now * dfr * np.ones(S)
    const_s = b_prev * tc_prev_s + spot_s * (v_s - b_prev)
    w_mean = 1.0 / S
    c[ib] = w_mean * coef_b.sum()
    c[LP:LP + S] = w_mean * coef_lp
    c[DP:DP + S] = w_mean * coef_dp
    c[LN:LN + S] = w_mean * coef_ln
    c[DN:DN + S] = w_mean * coef_dn
    c[iu] = lam
    c[Z:Z + S] = lam / ((1 - alpha) * S)

    rows, rhs = [], []

    def row():
        return np.zeros(nv)
    for s in range(S):
        r = row(); r[LP + s] = 1; rows.append(r); rhs.append(a_prev * (1 + tol))            # lift_prev <= a_prev(1+tol)
        r = row(); r[LP + s] = -1; r[DP + s] = -1; rows.append(r); rhs.append(-a_prev * (1 - tol))  # dead_prev >= a_prev(1-tol)-lift_prev
        r = row(); r[LN + s] = 1; r[ia] = -(1 + tol); rows.append(r); rhs.append(0.0)        # lift <= a(1+tol)
        r = row(); r[LN + s] = -1; r[DN + s] = -1; r[ia] = (1 - tol); rows.append(r); rhs.append(0.0)
        r = row(); r[ib] = 1; r[LP + s] = 1; r[LN + s] = 1; rows.append(r); rhs.append(v_s[s] - b_prev)  # no negative spot
        # CVaR: cost_s - u - z_s <= 0
        r = row(); r[ib] = coef_b[s]; r[LP + s] = coef_lp[s]; r[DP + s] = coef_dp[s]
        r[LN + s] = coef_ln[s]; r[DN + s] = coef_dn[s]; r[iu] = -1; r[Z + s] = -1
        rows.append(r); rhs.append(-const_s[s])
    r = row(); r[ia] = 1; r[ib] = 1; rows.append(r); rhs.append(max(0.0, max_lock - a_prev - b_prev))
    r = row(); r[ia] = 1; r[ib] = 1; rows.append(r); rhs.append(step_cap)
    r = row(); r[ib] = 1; rows.append(r); rhs.append(max(0.0, tc_cap * v_s.min() - b_prev) if allow_tc else 0.0)
    bounds = [(0, None), (0, None), (None, None)] + [(0, None)] * (5 * S)
    res = linprog(c, A_ub=np.array(rows), b_ub=np.array(rhs), bounds=bounds, method="highs")
    if not res.success:
        return {"a": 0.0, "b": 0.0, "status": res.message}
    x = res.x
    a, b = float(x[ia]), float(x[ib])
    # evaluate scenario cost distribution for reporting
    cost = (const_s + coef_b * b + coef_lp * x[LP:LP + S] + coef_dp * x[DP:DP + S]
            + coef_ln * x[LN:LN + S] + coef_dn * x[DN:DN + S]) / v_s
    q = np.quantile(cost, alpha)
    return {"a": a, "b": b, "exp_cost": float(cost.mean()), "cvar": float(cost[cost >= q].mean()),
            "p10": float(np.quantile(cost, 0.1)), "p90": float(np.quantile(cost, 0.9)), "status": "ok"}


def entry_timing(quote_paths, quote_now, weeks=12):
    """For the dashboard: distribution of the COA quote if SAIL waits w weeks.
    quote_paths: (S, H) scenario COA quotes. Returns per-w P(cheaper), expected saving, P90 regret."""
    out = []
    for w in range(1, min(weeks, quote_paths.shape[1]) + 1):
        q = quote_paths[:, w - 1]
        out.append({"wait_weeks": w, "p_cheaper": float((q < quote_now).mean()),
                    "exp_saving_pct": float((quote_now - q.mean()) / quote_now * 100),
                    "p90_regret_pct": float((np.quantile(q, 0.9) - quote_now) / quote_now * 100),
                    "q10": float(np.quantile(q, 0.1)), "q50": float(np.median(q)), "q90": float(np.quantile(q, 0.9))})
    return out
