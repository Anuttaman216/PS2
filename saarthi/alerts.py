"""Early-warning engine: market volatility, spike/turning-point risk, supply signal, port congestion."""
import numpy as np
import pandas as pd

from .config import CLASSES, DISCHARGE


def congestion_outlook(df, port, horizon=26):
    """Week-of-year climatology (mean, p90) + decaying current anomaly (AR(1) fitted on history)."""
    w = df[f"wait_{port}"]
    clim = w.groupby(df["woy"]).mean()
    p90 = w.groupby(df["woy"]).quantile(0.9)
    anom = w - df["woy"].map(clim)
    phi = float(np.clip(anom.autocorr(1), 0, 0.95))
    last_woy = int(df["woy"].iloc[-1])
    a0 = float(anom.iloc[-1])
    out = []
    for h in range(1, horizon + 1):
        wk = ((last_woy - 1 + h) % 52) + 1
        mean = clim.get(wk, w.mean()) + a0 * phi ** h
        out.append({"h": h, "mean": round(float(mean), 2), "p90": round(float(p90.get(wk, w.quantile(0.9)) + a0 * phi ** h), 2)})
    return out


def market_alerts(df, fc_now, paths):
    alerts = []
    for ci, c in enumerate(CLASSES):
        r = np.log(df[f"tce_{c}"]).diff()
        vol8 = r.rolling(8).std()
        pct = float((vol8.dropna() < vol8.iloc[-1]).mean() * 100)
        if pct > 80:
            alerts.append({"level": "high" if pct > 92 else "medium", "kind": "volatility", "cls": c,
                           "msg": f"{c} 8-week volatility at {pct:.0f}th percentile of history - widen bands, ladder entries."})
        p0 = df[f"tce_{c}"].iloc[-1]
        p_up = float((paths[:, 3, ci] > 1.2 * p0).mean())
        p_dn = float((paths[:, 3, ci] < 0.8 * p0).mean())
        if p_up > 0.2:
            alerts.append({"level": "high" if p_up > 0.35 else "medium", "kind": "spike_risk", "cls": c,
                           "msg": f"P({c} +20% within 4 weeks) = {p_up:.0%} - consider locking cover early."})
        if p_dn > 0.2:
            alerts.append({"level": "medium", "kind": "softening", "cls": c,
                           "msg": f"P({c} -20% within 4 weeks) = {p_dn:.0%} - defer spot fixing / avoid long lock-ins."})
        g = fc_now[fc_now["cls"] == ci].set_index("h")
        m4, m12 = float(g.loc[4, "q50"]), float(g.loc[12, "q50"])
        if np.sign(m4) != np.sign(m12) and abs(m12 - m4) > 0.05:
            alerts.append({"level": "medium", "kind": "turning_point", "cls": c,
                           "msg": f"{c}: forecast turns ({m4:+.1%} at 4w vs {m12:+.1%} at 12w) - timing window matters."})
    for col, lab in (("ballast_cape", "Capesize"), ("ballast_pmx", "Panamax")):
        b = df[col]
        z = float((b.iloc[-1] - b.iloc[-104:].mean()) / b.iloc[-104:].std())
        if abs(z) > 1.3:
            alerts.append({"level": "medium", "kind": "supply_signal", "cls": lab,
                           "msg": f"{lab} ballaster count z={z:+.1f} vs 2y - {'tight supply ahead (bullish)' if z < 0 else 'tonnage surplus ahead (bearish)'}."})
    return alerts


def congestion_alerts(df, horizon=8):
    out = []
    for p in DISCHARGE:
        o = congestion_outlook(df, p, horizon)
        hist_p80 = df[f"wait_{p}"].quantile(0.8)
        peak = max(o, key=lambda x: x["mean"])
        if peak["mean"] > hist_p80:
            out.append({"level": "medium", "kind": "congestion", "port": p,
                        "msg": f"{DISCHARGE[p]['name']}: expected waiting {peak['mean']:.1f} d in week +{peak['h']} "
                               f"(> historical P80 {hist_p80:.1f} d) - spread laycans / consider alternate port."})
    return out
