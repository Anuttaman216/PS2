"""Probabilistic freight forecaster.

Ensemble of three members, all forecasting log-TCE *returns* y(t+h)-y(t) for h in HORIZONS:
  1. GBM   - global LightGBM quantile regression (one model per horizon x quantile, pooled over
             the 4 classes -> transfers to new classes/routes, 4x more data)
  2. STRUCT- ridge 'structural' model: mean reversion + supply (ballasters) + demand (coal, PMI)
             + seasonality, Gaussian residuals
  3. RW    - random walk with empirical volatility (the honest benchmark)
Combination: quantile averaging with weights ~ 1 / trailing pinball loss per horizon.
Calibration: online conformalised quantile regression (CQR) - the 80% band is widened/narrowed
by the empirical quantile of past out-of-sample non-conformity scores, only using targets already
realised at the forecast date (no leakage).
Optional member: a time-series foundation model (Chronos-Bolt / TimesFM) plugs in via
`FoundationMember` if the package is installed (not required for the prototype).
"""
import warnings

import numpy as np
import pandas as pd
import lightgbm as lgb
from scipy.stats import norm

from .config import CLASSES
from .synth import seasonal

warnings.filterwarnings("ignore")
HORIZONS = [1, 2, 4, 8, 12, 16, 20, 26]
QS = [0.1, 0.5, 0.9]
Z90 = norm.ppf(0.9)


def build_features(df):
    """Long panel (week x class) of features known at week t (publication lags applied)."""
    rows = []
    cape = np.log(df["tce_Capesize"])
    for ci, c in enumerate(CLASSES):
        y = np.log(df[f"tce_{c}"])
        r1 = y.diff()
        bal = df["ballast_cape"] if c == "Capesize" else df["ballast_pmx"]
        f = pd.DataFrame({
            "date": df.index, "cls": ci, "y": y.values,
            "r1": r1.values, "r4": y.diff(4).values, "r12": y.diff(12).values, "r26": y.diff(26).values,
            "dev52": (y - y.rolling(52, min_periods=26).mean()).values,
            "dev_exp": (y - y.expanding(52).mean()).values,
            "vol8": r1.rolling(8).std().values,
            "cape_spread": (cape - y).values, "cape_r4": cape.diff(4).values,
            "bal": bal.values, "bal_d4": bal.diff(4).values,
            "bal_z": ((bal - bal.rolling(104, min_periods=26).mean()) / bal.rolling(104, min_periods=26).std()).values,
            "coal_r4": np.log(df["coal_usd_t"]).diff(4).shift(1).values,     # 1-week publication lag
            "coal_r12": np.log(df["coal_usd_t"]).diff(12).shift(1).values,
            "pmi": df["china_pmi"].shift(2).values,                           # monthly, ~2-week lag
            "bunker_r4": np.log(df["bunker_usd_t"]).diff(4).values,
            "woy_s": np.sin(2 * np.pi * df["woy"] / 52).values, "woy_c": np.cos(2 * np.pi * df["woy"] / 52).values,
            "seas_now": seasonal(df["woy"].values),
        })
        rows.append(f)
    return pd.concat(rows, ignore_index=True)


FEATS = ["cls", "r1", "r4", "r12", "r26", "dev52", "dev_exp", "vol8", "cape_spread", "cape_r4",
         "bal", "bal_d4", "bal_z", "coal_r4", "coal_r12", "pmi", "bunker_r4", "woy_s", "woy_c", "seas_now",
         "seas_tgt", "h_woy_s", "h_woy_c"]
STRUCT_FEATS = ["dev_exp", "dev52", "r4", "bal_z", "bal_d4", "coal_r4", "pmi", "seas_tgt", "seas_now"]


def with_target(panel, df, h):
    p = panel.copy()
    woy = np.tile(df["woy"].values, len(CLASSES))
    tgt_woy = ((woy - 1 + h) % 52) + 1
    p["seas_tgt"] = seasonal(tgt_woy)
    p["h_woy_s"] = np.sin(2 * np.pi * tgt_woy / 52)
    p["h_woy_c"] = np.cos(2 * np.pi * tgt_woy / 52)
    p["target"] = p.groupby("cls")["y"].shift(-h) - p["y"]
    return p


class Forecaster:
    def __init__(self, df, gbm_params=None, use_members=("gbm", "struct", "rw")):
        self.df = df
        self.panel = build_features(df)
        self.dates = df.index
        self.n = len(df)
        self.members = use_members
        self.gbm_params = gbm_params or dict(objective="quantile", n_estimators=180, learning_rate=0.05,
                                             num_leaves=15, min_child_samples=25, subsample=0.8,
                                             subsample_freq=1, colsample_bytree=0.8, verbose=-1)
        self.tp = {h: with_target(self.panel, df, h) for h in HORIZONS}

    # ---------- fitting on data available up to week index t_end (inclusive) ----------
    def fit(self, t_end):
        self.models = {}
        for h in HORIZONS:
            p = self.tp[h]
            week = np.tile(np.arange(self.n), len(CLASSES))
            m = (week + h <= t_end) & p["target"].notna() & p["dev52"].notna()
            tr = p[m]
            mods = {}
            if "gbm" in self.members:
                for q in QS:
                    mdl = lgb.LGBMRegressor(alpha=q, **self.gbm_params)
                    mdl.fit(tr[FEATS], tr["target"])
                    mods[("gbm", q)] = mdl
            if "struct" in self.members:
                X = np.c_[np.ones(len(tr)), tr[STRUCT_FEATS].fillna(0).values,
                          np.eye(len(CLASSES))[tr["cls"].values.astype(int)][:, 1:]]
                lam = 1.0
                beta = np.linalg.solve(X.T @ X + lam * np.eye(X.shape[1]), X.T @ tr["target"].values)
                resid = tr["target"].values - X @ beta
                sd = pd.Series(resid).groupby(tr["cls"].values).std().reindex(range(len(CLASSES))).values
                mods["struct"] = (beta, sd)
            if "rw" in self.members:
                sd = tr.groupby("cls")["target"].std().reindex(range(len(CLASSES))).values
                mods["rw"] = sd
            self.models[h] = mods
        self.fitted_at = t_end

    def _member_quantiles(self, h, rows):
        out = {}
        mods = self.models[h]
        cls = rows["cls"].values.astype(int)
        if "gbm" in self.members:
            q = np.column_stack([mods[("gbm", qq)].predict(rows[FEATS]) for qq in QS])
            q.sort(axis=1)
            out["gbm"] = q
        if "struct" in self.members:
            beta, sd = mods["struct"]
            X = np.c_[np.ones(len(rows)), rows[STRUCT_FEATS].fillna(0).values,
                      np.eye(len(CLASSES))[cls][:, 1:]]
            mu = X @ beta
            s = sd[cls]
            out["struct"] = np.column_stack([mu - Z90 * s, mu, mu + Z90 * s])
        if "rw" in self.members:
            s = mods["rw"][cls]
            out["rw"] = np.column_stack([-Z90 * s, np.zeros(len(rows)), Z90 * s])
        return out

    def predict_members(self, t_idx_list):
        """Member quantiles for weeks t (list) -> {h: {member: array (len(t)*4, 3)}}, rows ordered class-major."""
        res = {}
        for h in HORIZONS:
            p = self.tp[h]
            idx = np.concatenate([np.asarray(t_idx_list) + ci * self.n for ci in range(len(CLASSES))])
            rows = p.iloc[idx]
            res[h] = (rows[["date", "cls", "y", "target"]].reset_index(drop=True), self._member_quantiles(h, rows))
        return res


def pinball(y, q, taus=QS):
    loss = 0
    for j, t in enumerate(taus):
        d = y - q[:, j]
        loss += np.maximum(t * d, (t - 1) * d)
    return loss / len(taus)


def walk_forward(df, start_idx, refit_every=13, members=("gbm", "struct", "rw"), trail=104, verbose=True):
    """Out-of-sample walk-forward forecasts for every week >= start_idx.
    Returns long DataFrame: t, cls, h, y0, q10,q50,q90 (ensemble, conformalised) + member q50s + target."""
    fc = Forecaster(df, use_members=members)
    n = len(df)
    recs = []
    for t0 in range(start_idx, n, refit_every):
        fc.fit(t0)
        ts = list(range(t0, min(t0 + refit_every, n)))
        pm = fc.predict_members(ts)
        for h in HORIZONS:
            rows, mq = pm[h]
            base = rows.copy()
            base["t"] = np.tile(ts, len(CLASSES))
            base["h"] = h
            for m, q in mq.items():
                base[f"{m}_q10"], base[f"{m}_q50"], base[f"{m}_q90"] = q[:, 0], q[:, 1], q[:, 2]
            recs.append(base)
        if verbose:
            print(f"  walk-forward: fitted at {df.index[t0].date()} ({len(ts)} weeks)")
    out = pd.concat(recs, ignore_index=True).sort_values(["h", "cls", "t"]).reset_index(drop=True)

    # ---- online ensemble weighting + CQR calibration (strictly causal) ----
    ens = []
    for (h, c), g in out.groupby(["h", "cls"]):
        g = g.sort_values("t").copy()
        tgt = g["target"].values
        tt = g["t"].values
        M = {m: g[[f"{m}_q10", f"{m}_q50", f"{m}_q90"]].values for m in members}
        losses = {m: pinball(tgt, M[m]) for m in members}
        q_ens = np.zeros((len(g), 3))
        scores = np.full(len(g), np.nan)
        w_hist = []
        for i in range(len(g)):
            known = (tt + h <= tt[i]) & ~np.isnan(tgt)          # targets realised by week t_i
            known[i:] = False
            kidx = np.where(known)[0][-trail:]
            if len(kidx) >= 8:
                L = np.array([np.nanmean(losses[m][kidx]) for m in members])
                w = (1 / L) ** 2
                w /= w.sum()
            else:
                w = np.ones(len(members)) / len(members)
            w_hist.append(w)
            qi = sum(w[j] * M[m][i] for j, m in enumerate(members))
            # CQR: widen by empirical 80% quantile of past non-conformity scores
            if len(kidx) >= 20:
                E = scores[kidx]
                E = E[~np.isnan(E)]
                adj = np.quantile(E, 0.8 * (1 + 1 / len(E))) if len(E) >= 20 else 0.0
            else:
                adj = 0.0
            raw = qi.copy()
            qi = np.array([raw[0] - adj, raw[1], raw[2] + adj])
            if qi[0] > qi[1]:
                qi[0] = qi[1] - 1e-3
            if qi[2] < qi[1]:
                qi[2] = qi[1] + 1e-3
            q_ens[i] = qi
            if not np.isnan(tgt[i]):
                scores[i] = max(raw[0] - tgt[i], tgt[i] - raw[2])
        g["q10"], g["q50"], g["q90"] = q_ens[:, 0], q_ens[:, 1], q_ens[:, 2]
        W = np.array(w_hist)
        for j, m in enumerate(members):
            g[f"w_{m}"] = W[:, j]
        ens.append(g)
    return pd.concat(ens, ignore_index=True), fc


def interp_quantiles(fc_t, horizons_full):
    """fc_t: rows for one t & class across HORIZONS -> arrays (median, sig_lo, sig_hi) for every
    weekly horizon 1..max via linear interpolation (two-piece normal in log-return space)."""
    g = fc_t.sort_values("h")
    H = g["h"].values
    med = np.interp(horizons_full, H, g["q50"].values)
    lo = np.interp(horizons_full, H, ((g["q50"] - g["q10"]) / Z90).values)
    hi = np.interp(horizons_full, H, ((g["q90"] - g["q50"]) / Z90).values)
    # beyond the last modelled horizon: hold the median, grow spread ~sqrt(h) (capped) - low confidence
    ext = np.clip(np.sqrt(np.asarray(horizons_full, float) / H[-1]), 1.0, 1.5)
    lo, hi = lo * ext, hi * ext
    return med, np.maximum(lo, 1e-4), np.maximum(hi, 1e-4)


def simulate_paths(fc_t_all, y0, n_paths=300, horizon=26, rho=0.7, seed=0):
    """Gaussian-copula scenario paths consistent with the per-horizon marginal quantiles.
    Cross-horizon dependence: Brownian (corr(Z_h,Z_k)=sqrt(min/max)); cross-class: common factor rho.
    fc_t_all: rows for one t, all classes, all HORIZONS. y0: {cls_idx: log level at t}.
    Returns array (n_paths, horizon, n_classes) of TCE levels."""
    rng = np.random.default_rng(seed)
    hs = np.arange(1, horizon + 1)
    common = rng.standard_normal((n_paths, horizon)).cumsum(axis=1)
    out = np.zeros((n_paths, horizon, len(CLASSES)))
    for ci in range(len(CLASSES)):
        med, lo, hi = interp_quantiles(fc_t_all[fc_t_all["cls"] == ci], hs)
        idio = rng.standard_normal((n_paths, horizon)).cumsum(axis=1)
        W = np.sqrt(rho) * common + np.sqrt(1 - rho) * idio
        Z = W / np.sqrt(hs)
        ret = med + np.where(Z < 0, lo, hi) * Z
        out[:, :, ci] = np.exp(y0[ci] + ret)
    return out
