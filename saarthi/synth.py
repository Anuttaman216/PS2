"""Synthetic-but-structured market world (clearly labelled SYNTHETIC).

Why synthetic: Baltic Exchange indices (BCI/BPI/BSI/BHSI, route C5/P3A etc.) and broker fixture
lists are licensed. The generator reproduces the *stylised facts* of dry-bulk freight so the whole
pipeline can be built and backtested end-to-end; swapping in real data only changes `load_world`.

Stylised facts embedded:
  * one common market factor, class betas (Cape most volatile, Handy least)
  * regime switching (normal / boom / bust), fat tails, stylised historical episodes
  * seasonality: Chinese New Year dip, Q4 strength, northern summer lull
  * leading indicators with plausible (not overwhelming) lead: ballaster count (supply, ~3w),
    coal price / PMI (demand, ~2w)
  * port congestion at East Coast India with SW-monsoon and cyclone seasonality
Two worlds:
  * 'structured' - the above
  * 'martingale' - PLACEBO: unpredictable random-walk rates, uninformative drivers.
    A correct system must show ~zero timing savings here (no fake edge).
"""
import numpy as np
import pandas as pd

from .config import CLASSES, DISCHARGE

MU = {"Handysize": 11000, "Supramax": 13500, "Panamax": 14000, "Capesize": 17000}
BETA = {"Handysize": 0.70, "Supramax": 0.85, "Panamax": 1.0, "Capesize": 1.45}
IDIO = {"Handysize": 0.025, "Supramax": 0.030, "Panamax": 0.040, "Capesize": 0.075}

# stylised episodes (start, end, common log-bump, {class: extra})
EVENTS = [
    ("2016-01-01", "2016-06-15", -0.45, {}),
    ("2020-02-01", "2020-06-20", -0.35, {"Capesize": -0.2}),
    ("2021-03-01", "2021-11-20", +0.50, {"Capesize": +0.25}),
    ("2022-03-01", "2022-06-10", +0.20, {"Capesize": -0.15}),
    ("2024-01-15", "2024-04-30", +0.12, {}),  # Red Sea re-routing tonne-mile shock
]


def _bump(dates, start, end):
    """raised-cosine window 0..1 between start and end"""
    t = (dates - pd.Timestamp(start)) / (pd.Timestamp(end) - pd.Timestamp(start))
    t = np.asarray(t, float)
    w = np.where((t >= 0) & (t <= 1), 0.5 - 0.5 * np.cos(2 * np.pi * t), 0.0)
    return w


def seasonal(woy):
    """log seasonal component of the common market factor (week of year 1..53)"""
    woy = np.asarray(woy, float)
    cny = -0.10 * np.exp(-0.5 * ((woy - 6.5) / 1.8) ** 2)
    q4 = 0.06 * np.exp(-0.5 * ((woy - 44) / 4.0) ** 2)
    summer = -0.03 * np.exp(-0.5 * ((woy - 29) / 3.0) ** 2)
    return cny + q4 + summer


def monsoon_shape(woy):
    woy = np.asarray(woy, float)
    return np.where((woy >= 23) & (woy <= 39), np.sin(np.pi * (woy - 23) / 16) ** 1.0, 0.0)


def _ar(rng, n, phi, sd):
    x = np.zeros(n)
    e = rng.normal(0, sd, n)
    for t in range(1, n):
        x[t] = phi * x[t - 1] + e[t]
    return x


def generate(world="structured", start="2014-01-03", end="2026-09-25", seed=11):
    rng = np.random.default_rng(seed)
    dates = pd.date_range(start, end, freq="W-FRI")
    n = len(dates)
    woy = dates.isocalendar().week.values.astype(int)
    df = pd.DataFrame(index=dates)
    df["woy"] = woy

    if world == "structured":
        # demand factor with regime switching
        P = np.array([[0.985, 0.008, 0.007], [0.035, 0.96, 0.005], [0.035, 0.005, 0.96]])
        drift = np.array([0.0, 0.018, -0.018])
        reg = np.zeros(n, int)
        D = np.zeros(n)
        eps = rng.standard_t(5, n) * 0.03
        for t in range(1, n):
            reg[t] = rng.choice(3, p=P[reg[t - 1]])
            D[t] = 0.96 * D[t - 1] + drift[reg[t]] + eps[t]
        S = _ar(rng, n, 0.90, 0.06)                           # supply tightness (+ = tight)
        X = 0.8 * np.r_[np.zeros(2), D[:-2]] + 0.9 * np.r_[np.zeros(3), S[:-3]]
        season = seasonal(woy)
        ev_common = np.zeros(n)
        ev_cls = {c: np.zeros(n) for c in CLASSES}
        for s, e, amp, extra in EVENTS:
            b = _bump(dates, s, e)
            ev_common += amp * b
            for c, a in extra.items():
                ev_cls[c] += a * b
        for c in CLASSES:
            idio = _ar(rng, n, 0.8, IDIO[c]) + rng.standard_t(4, n) * IDIO[c] * 0.3
            df[f"tce_{c}"] = np.exp(np.log(MU[c]) + BETA[c] * (X + season + ev_common) + ev_cls[c] + idio)
        df["ballast_cape"] = 100 - 55 * S + rng.normal(0, 4, n)
        df["ballast_pmx"] = 100 - 45 * S + rng.normal(0, 5, n)
        coal_ev = sum(amp * 1.6 * _bump(dates, s, e) for s, e, amp, _ in EVENTS)
        df["coal_usd_t"] = np.exp(np.log(200) + 0.9 * D + coal_ev + _ar(rng, n, 0.9, 0.03))
        pmi = 50 + 8 * D + rng.normal(0, 0.6, n)
        df["china_pmi"] = pd.Series(pmi, index=dates).resample("MS").transform("mean").values
        df["bunker_usd_t"] = np.exp(np.log(560) + _ar(rng, n, 0.985, 0.03)
                                    + 0.40 * _bump(dates, "2022-02-15", "2022-12-31")
                                    - 0.25 * _bump(dates, "2020-02-15", "2020-09-30"))
        df["regime"] = reg
        demand = D
        phi_mkt = 0.975
        season_known = True
    elif world == "martingale":
        common = rng.normal(0, 0.05, n)
        for c in CLASSES:
            sd_idio = IDIO[c] * 0.6
            var = (BETA[c] * 0.05) ** 2 + sd_idio ** 2
            steps = BETA[c] * common + rng.normal(0, sd_idio, n) - var / 2   # martingale in LEVELS
            df[f"tce_{c}"] = np.exp(np.log(MU[c]) + np.cumsum(steps))
        df["ballast_cape"] = 100 + rng.normal(0, 8, n)
        df["ballast_pmx"] = 100 + rng.normal(0, 8, n)
        df["coal_usd_t"] = np.exp(np.log(200) + np.cumsum(rng.normal(0, 0.03, n)))
        df["china_pmi"] = 50 + rng.normal(0, 1.0, n)
        df["bunker_usd_t"] = np.exp(np.log(560) + np.cumsum(rng.normal(0, 0.02, n) - 0.0002))
        df["regime"] = 0
        demand = np.zeros(n)
        phi_mkt = 1.0
        season_known = False
    else:
        raise ValueError(world)

    # East-coast port waiting days (congestion) - structural in both worlds (it is physical)
    ms = monsoon_shape(woy)
    for p, spec in DISCHARGE.items():
        base = spec["base_wait_days"] + spec["monsoon_wait_add"] * ms + 1.2 * np.clip(demand, 0, None)
        noise = _ar(rng, n, 0.75, 0.35)
        cyc = np.zeros(n)
        season_cyc = np.isin(woy, list(range(18, 23)) + list(range(40, 48)))
        hits = np.where(season_cyc & (rng.random(n) < 0.05))[0]
        for h in hits:
            cyc[h:h + 2] += rng.uniform(2.5, 6.0)
        df[f"wait_{p}"] = np.clip(base + noise + cyc, 0.3, None)

    meta = {"world": world, "phi_mkt": phi_mkt, "season_known": season_known,
            "mu": {c: float(np.log(MU[c])) for c in CLASSES}, "beta": BETA}
    return df, meta


def market_forward_log(df, meta, c, t_idx, horizons):
    """Owner/broker consensus forward for class c at week t_idx for given horizons (weeks).
    Semi-efficient market: knows mean reversion + public seasonality, NOT leading indicators."""
    y = np.log(df[f"tce_{c}"].values[t_idx])
    mu = meta["mu"][c]
    woy = df["woy"].values
    if meta["season_known"]:
        s_now = meta["beta"][c] * seasonal(woy[t_idx])
        tgt_woy = ((woy[t_idx] - 1 + np.asarray(horizons)) % 52) + 1
        s_h = meta["beta"][c] * seasonal(tgt_woy)
    else:
        s_now, s_h = 0.0, 0.0
    phi = meta["phi_mkt"] ** np.asarray(horizons, float)
    return mu + phi * (y - mu - s_now) + s_h
